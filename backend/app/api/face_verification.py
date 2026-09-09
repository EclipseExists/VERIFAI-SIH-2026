"""
VERIFAI — Face Verification API Endpoint
==========================================

POST /api/v1/cases/{case_id}/face-verification

This endpoint wires together:
1. The frontend (sends the request)
2. Your teammate's verify_faces() function (does the AI work)
3. The database (stores the result)
4. The risk engine (receives a RiskSignal)

INTEGRATION PATTERN:
- The teammate built a PURE PYTHON FUNCTION: verify_faces(path1, path2) → dict
- This endpoint WRAPS that function with HTTP, validation, DB storage, and error handling
- If the teammate changes their model or thresholds, this file doesn't change
- If we change our API shape, the teammate's code doesn't change
- This separation is what lets 6 people work in parallel

ERROR HANDLING:
- The teammate's module raises FaceVerificationError if no face is detected
- We catch it and return 422 (Unprocessable Entity) with a clear message
- We do NOT let it become a 500 (Internal Server Error) — that looks broken
- We STILL store a record with error_message so the audit trail is complete
"""

import sys
import os
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.db.session import get_db
from app.models.case import Case, Document
from app.models.face_verification import FaceVerification
from app.models.audit import AuditLog
from app.schemas.face_verification import FaceVerificationRequest, FaceVerificationOut

router = APIRouter()

# ── TEMPORARY: Placeholder officer ID ─────────────────────────────
# Same as in cases.py — will be replaced by JWT auth
PLACEHOLDER_OFFICER_ID = UUID("00000000-0000-0000-0000-000000000001")

# ── Add the project root to Python path so we can import ai/ modules ─
# The ai/ directory is a sibling of backend/, so we need to go up one level
# In production, this would be a proper package install
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def _call_verify_faces(image_path_1: str, image_path_2: str) -> dict:
    """
    Wrapper that calls the teammate's verify_faces() function.

    WHY A WRAPPER:
    - Isolates the import so the backend can start even if the AI module
      isn't installed yet (graceful degradation)
    - Makes it easy to swap in a mock for testing
    - Catches the teammate's custom FaceVerificationError

    RETURNS:
        {"similarity_score": float, "band": str}

    RAISES:
        HTTPException(422) if no face detected
        HTTPException(503) if the AI module isn't available
    """
    try:
        from ai.face.verify import verify_faces
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Face verification module not available. "
                "Ensure ai/face/verify.py is present and dependencies are installed."
            ),
        )

    try:
        return verify_faces(image_path_1, image_path_2)
    except Exception as e:
        # Check if this is the teammate's custom FaceVerificationError
        # We check by class name (not isinstance) because the import path
        # might vary. This is pragmatic for a hackathon.
        if type(e).__name__ == "FaceVerificationError":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Face detection failed: {str(e)}",
            )
        # Unexpected error — re-raise as 500
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Face verification failed unexpectedly: {str(e)}",
        )


@router.post(
    "/{case_id}/face-verification",
    response_model=FaceVerificationOut,
    status_code=status.HTTP_201_CREATED,
    summary="Run face verification",
    description=(
        "Compare a face from a document against a probe/live face photo. "
        "Returns a similarity score (0.0-1.0) and a band (match/uncertain/mismatch). "
        "This is 1:1 comparison only — NOT face recognition against a population."
    ),
)
async def run_face_verification(
    case_id: UUID,
    request: FaceVerificationRequest,
    db: AsyncSession = Depends(get_db),
) -> FaceVerificationOut:
    """
    Run face verification for a case.

    WHAT HAPPENS:
    1. Validate that the case and document exist
    2. Call the teammate's verify_faces() with both image paths
    3. Store the result in face_verifications table
    4. Log the action in audit_logs
    5. Return the result to the frontend

    The frontend shows the score + band to the officer.
    The officer decides — the system does NOT auto-decide based on this.
    """

    # ── 1. Validate the case exists ───────────────────────────────
    case_query = select(Case).where(Case.id == case_id)
    case_result = await db.execute(case_query)
    case = case_result.scalar_one_or_none()

    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case {case_id} not found",
        )

    # ── 2. Validate the document exists and belongs to this case ──
    doc_query = select(Document).where(
        Document.id == request.document_id,
        Document.case_id == case_id,
    )
    doc_result = await db.execute(doc_query)
    document = doc_result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Document {request.document_id} not found in case {case_id}. "
                "Make sure the document belongs to this case."
            ),
        )

    # ── 3. Call the AI module ─────────────────────────────────────
    error_message = None
    try:
        result = await run_in_threadpool(
            _call_verify_faces, 
            document.image_path, 
            request.probe_face_path
        )
        similarity_score = result["similarity_score"]
        band = result["band"]
    except HTTPException as e:
        if e.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
            # Face not detected — store the error but don't crash
            # The officer needs to know this happened
            similarity_score = 0.0
            band = "error"
            error_message = e.detail
        else:
            raise

    # ── 4. Store the result ───────────────────────────────────────
    face_record = FaceVerification(
        case_id=case_id,
        document_id=request.document_id,
        doc_face_path=document.image_path,
        probe_face_path=request.probe_face_path,
        similarity_score=similarity_score,
        band=band,
        error_message=error_message,
    )
    db.add(face_record)

    # ── 5. Audit log ─────────────────────────────────────────────
    audit_entry = AuditLog(
        user_id=PLACEHOLDER_OFFICER_ID,
        case_id=case_id,
        action="face_verification_completed",
        details=(
            f"Document: {request.document_id}, "
            f"Score: {similarity_score:.3f}, Band: {band}"
            + (f", Error: {error_message}" if error_message else "")
        ),
    )
    db.add(audit_entry)

    await db.commit()
    await db.refresh(face_record)

    return FaceVerificationOut.model_validate(face_record)

