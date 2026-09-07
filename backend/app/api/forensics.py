"""
VERIFAI — Forensics Integration Endpoint
==========================================

POST /api/v1/documents/{document_id}/forensics

Calls the forensics teammate's module to detect image manipulation.

HOW IT WORKS (non-technical):
- Error Level Analysis (ELA): Checks if parts of the image were edited
  separately (photo-editing software leaves "heat signatures")
- If the passport photo was swapped in Photoshop, ELA detects it
- Returns regions of suspicion with bounding boxes (where exactly is suspicious)
- This is a probabilistic signal — not proof, but a flag for the officer
"""

import sys
import os
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.case import Document
from app.models.audit import AuditLog
from app.schemas.forensics import ForensicsResultOut

router = APIRouter()
PLACEHOLDER_OFFICER_ID = UUID("00000000-0000-0000-0000-000000000001")

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def _call_forensics(image_path: str) -> dict:
    """
    Call the forensics teammate's module.
    Falls back to stub if not yet available.
    """
    try:
        from ai.forensics.analyze import analyze_document  # teammate's function
        return analyze_document(image_path)
    except ImportError:
        return {
            "ela_score": None,
            "suspicious_regions": [],
            "noise_inconsistency_score": None,
            "overall_manipulation_probability": None,
            "_stub": True,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Forensic analysis failed: {str(e)}",
        )


@router.post(
    "/{document_id}/forensics",
    response_model=ForensicsResultOut,
    status_code=status.HTTP_201_CREATED,
    summary="Run forensic analysis",
    description=(
        "Run Error Level Analysis (ELA) and noise inconsistency detection on a document image. "
        "Detects signs of digital manipulation (e.g., photo swap, text editing)."
    ),
)
async def run_forensics_on_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ForensicsResultOut:
    """Run forensic image analysis."""

    doc = await db.get(Document, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    result = _call_forensics(doc.image_path)

    from app.models.forensics_result import ForensicsResult
    forensics_record = ForensicsResult(
        document_id=document_id,
        case_id=doc.case_id,
        ela_score=result.get("ela_score"),
        suspicious_regions=result.get("suspicious_regions", []),
        noise_inconsistency_score=result.get("noise_inconsistency_score"),
        overall_manipulation_probability=result.get("overall_manipulation_probability"),
        is_stub=result.get("_stub", False),
    )
    db.add(forensics_record)

    db.add(AuditLog(
        user_id=PLACEHOLDER_OFFICER_ID,
        case_id=doc.case_id,
        action="forensics_completed",
        details=(
            f"Document: {document_id}, "
            f"manipulation_prob={result.get('overall_manipulation_probability')}"
        ),
    ))

    await db.commit()
    await db.refresh(forensics_record)
    return ForensicsResultOut.model_validate(forensics_record)

