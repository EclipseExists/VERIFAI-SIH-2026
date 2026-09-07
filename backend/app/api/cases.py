"""
VERIFAI — Case API Endpoints
==============================

These endpoints handle the core screening workflow:
1. Create a case (officer starts a new screening)
2. List cases (dashboard overview)
3. Get case details (view all documents, signals, etc.)
4. Submit decision (officer's HUMAN-IN-THE-LOOP final call)

ENDPOINT DESIGN RATIONALE:
- POST /cases          → Create (officer starts screening)
- GET  /cases          → List   (dashboard table)
- GET  /cases/{id}     → Detail (full case view with documents)
- POST /cases/{id}/decision → Decide (officer's final call)

FUTURE ENDPOINTS (to be added by teammates):
- POST /cases/{id}/documents             → Upload a document
- POST /documents/{id}/ocr               → Run OCR on a document
- POST /documents/{id}/mrz               → Parse MRZ zone
- POST /documents/{id}/validation        → Run validation rules
- POST /documents/{id}/forensics         → Run ELA/noise analysis
- POST /cases/{id}/face-verification     → Compare faces
- POST /cases/{id}/consistency           → Cross-document check
- POST /cases/{id}/risk-assessment       → Compute risk score

Each of these will be in its own router file (api/documents.py, etc.)
and included in the main router. This keeps files small and prevents
merge conflicts when 6 people are working simultaneously.
"""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.case import Case, Document
from app.models.audit import AuditLog
from app.schemas.case import CaseCreate, CaseDecision, CaseOut, CaseSummary

router = APIRouter()

# ── TEMPORARY: Placeholder officer ID ─────────────────────────────
# This will be replaced by the actual authenticated user once we
# implement JWT auth. For Day 1, we use a fixed UUID so we can
# test case creation without an auth system.
PLACEHOLDER_OFFICER_ID = UUID("00000000-0000-0000-0000-000000000001")


@router.post(
    "/",
    response_model=CaseOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new screening case",
    description="Officer initiates a new document screening case for a traveller.",
)
async def create_case(
    case_in: CaseCreate,
    db: AsyncSession = Depends(get_db),
) -> CaseOut:
    """
    Create a new screening case.

    What happens:
    1. A new Case row is created with status='pending'
    2. An audit log entry is recorded
    3. The case ID is returned — the officer uses this to upload documents

    TODO: Replace PLACEHOLDER_OFFICER_ID with authenticated user from JWT.
    """
    # Create the case in the database
    new_case = Case(
        officer_id=PLACEHOLDER_OFFICER_ID,
        status="pending",
        subject_name=case_in.subject_name,
        notes=case_in.notes,
    )
    db.add(new_case)

    # Record the audit log
    audit_entry = AuditLog(
        user_id=PLACEHOLDER_OFFICER_ID,
        case_id=new_case.id,
        action="case_created",
        details=f"Subject: {case_in.subject_name or 'Unknown'}",
    )
    db.add(audit_entry)

    await db.commit()
    await db.refresh(new_case)

    return CaseOut.model_validate(new_case)


@router.get(
    "/",
    response_model=list[CaseSummary],
    summary="List all cases",
    description="Returns a paginated list of cases for the dashboard.",
)
async def list_cases(
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
) -> list[CaseSummary]:
    """
    List cases with pagination.

    Used by the frontend dashboard to show a table of all cases.
    Returns compact CaseSummary (no nested documents) for performance.

    Query params:
    - skip: how many cases to skip (for pagination)
    - limit: max cases to return (default 20)
    """
    query = (
        select(Case)
        .order_by(Case.created_at.desc())  # Newest first
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    cases = result.scalars().all()

    return [CaseSummary.model_validate(c) for c in cases]


@router.get(
    "/{case_id}",
    response_model=CaseOut,
    summary="Get case details",
    description="Returns full case details including all uploaded documents.",
)
async def get_case(
    case_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> CaseOut:
    """
    Get a single case with all its documents.

    Uses selectinload to eagerly fetch related documents in one query
    instead of making a separate query for each document (N+1 problem).
    """
    query = (
        select(Case)
        .where(Case.id == case_id)
        .options(selectinload(Case.documents))
    )
    result = await db.execute(query)
    case = result.scalar_one_or_none()

    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case {case_id} not found",
        )

    return CaseOut.model_validate(case)


@router.post(
    "/{case_id}/decision",
    response_model=CaseOut,
    summary="Submit officer decision",
    description=(
        "Officer submits their final decision on a case. "
        "This is the HUMAN-IN-THE-LOOP endpoint. "
        "The system recommends a risk band but NEVER auto-decides."
    ),
)
async def submit_decision(
    case_id: UUID,
    decision_in: CaseDecision,
    db: AsyncSession = Depends(get_db),
) -> CaseOut:
    """
    Record the officer's final decision on a case.

    HUMAN-IN-THE-LOOP: This is the only way a case gets a final decision.
    There is NO endpoint or background process that auto-decides.

    The officer can:
    - approve: Traveller cleared to proceed
    - reject: Traveller denied entry/passage
    - escalate: Needs supervisor review

    The officer can make a decision that DISAGREES with the AI risk band.
    That's by design — the AI is a tool, not the decision-maker.
    """
    # Fetch the case
    query = (
        select(Case)
        .where(Case.id == case_id)
        .options(selectinload(Case.documents))
    )
    result = await db.execute(query)
    case = result.scalar_one_or_none()

    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case {case_id} not found",
        )

    # Record the officer's decision
    case.decision = decision_in.decision
    case.decision_notes = decision_in.decision_notes
    case.decided_at = datetime.now(timezone.utc)
    case.status = "decided"

    # Audit log — this is the most important audit event
    audit_entry = AuditLog(
        user_id=PLACEHOLDER_OFFICER_ID,  # TODO: use authenticated user
        case_id=case_id,
        action="decision_made",
        details=f"Decision: {decision_in.decision}. Notes: {decision_in.decision_notes}",
    )
    db.add(audit_entry)

    await db.commit()
    await db.refresh(case)

    return CaseOut.model_validate(case)

