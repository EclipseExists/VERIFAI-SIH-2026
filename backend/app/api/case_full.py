"""
VERIFAI — Case Summary / Full Results Endpoint
================================================

GET /api/v1/cases/{case_id}/full

Returns EVERYTHING about a case in a single response:
- Case details
- All documents
- Latest OCR, MRZ, forensics, face verification results
- Latest risk assessment with signals
- Audit trail

The frontend uses this to render the complete officer dashboard for one case.
No need to make 6 separate API calls.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.case import Case
from app.models.audit import AuditLog
from app.models.ocr_result import OcrResult
from app.models.mrz_result import MrzResult
from app.models.forensics_result import ForensicsResult
from app.models.face_verification import FaceVerification
from app.models.risk_assessment import RiskAssessment

router = APIRouter()


@router.get(
    "/{case_id}/full",
    summary="Get full case results",
    description=(
        "Returns the case details plus the latest result from every AI module: "
        "OCR, MRZ, forensics, face verification, and risk assessment. "
        "This is the primary endpoint the frontend dashboard uses."
    ),
)
async def get_full_case(
    case_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Return all data about a case in one response."""

    case_result = await db.execute(
        select(Case)
        .where(Case.id == case_id)
        .options(selectinload(Case.documents))
    )
    case = case_result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Latest result from each module
    async def latest(model, case_field="case_id"):
        q = await db.execute(
            select(model)
            .where(getattr(model, case_field) == case_id)
            .order_by(model.created_at.desc())
            .limit(1)
        )
        return q.scalar_one_or_none()

    ocr = await latest(OcrResult)
    mrz = await latest(MrzResult)
    forensics = await latest(ForensicsResult)
    face = await latest(FaceVerification)

    # Latest risk assessment with signals
    ra_result = await db.execute(
        select(RiskAssessment)
        .where(RiskAssessment.case_id == case_id)
        .options(selectinload(RiskAssessment.signals))
        .order_by(RiskAssessment.created_at.desc())
        .limit(1)
    )
    risk = ra_result.scalar_one_or_none()

    # Last 20 audit events
    audit_result = await db.execute(
        select(AuditLog)
        .where(AuditLog.case_id == case_id)
        .order_by(AuditLog.created_at.desc())
        .limit(20)
    )
    audit_entries = audit_result.scalars().all()

    def _model_to_dict(obj):
        if obj is None:
            return None
        result = {}
        for col in obj.__table__.columns:
            val = getattr(obj, col.name)
            result[col.name] = str(val) if hasattr(val, 'hex') else val
        return result

    return {
        "case": {
            "id": str(case.id),
            "status": case.status,
            "subject_name": case.subject_name,
            "notes": case.notes,
            "decision": case.decision,
            "decision_notes": case.decision_notes,
            "decided_at": case.decided_at.isoformat() if case.decided_at else None,
            "risk_score": case.risk_score,
            "risk_band": case.risk_band,
            "created_at": case.created_at.isoformat(),
        },
        "documents": [
            {
                "id": str(d.id),
                "doc_type": d.doc_type,
                "image_path": d.image_path,
                "original_filename": d.original_filename,
                "quality_passed": d.quality_passed,
            }
            for d in case.documents
        ],
        "ocr": _model_to_dict(ocr),
        "mrz": _model_to_dict(mrz),
        "forensics": _model_to_dict(forensics),
        "face_verification": {
            "id": str(face.id),
            "similarity_score": face.similarity_score,
            "band": face.band,
            "error_message": face.error_message,
            "doc_face_path": face.doc_face_path,
            "probe_face_path": face.probe_face_path,
            "created_at": face.created_at.isoformat(),
        } if face else None,
        "risk_assessment": {
            "id": str(risk.id),
            "overall_score": risk.overall_score,
            "risk_band": risk.risk_band,
            "computed_at": risk.created_at.isoformat(),
            "signals": [
                {
                    "signal_name": s.signal_name,
                    "direction": s.direction,
                    "magnitude": s.magnitude,
                    "explanation": s.explanation,
                    "source_module": s.source_module,
                }
                for s in risk.signals
            ],
        } if risk else None,
        "audit_trail": [
            {
                "action": a.action,
                "details": a.details,
                "timestamp": a.created_at.isoformat(),
            }
            for a in audit_entries
        ],
    }

