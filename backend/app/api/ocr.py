"""
VERIFAI — OCR Integration Endpoint
=====================================

POST /api/v1/documents/{document_id}/ocr

Calls the OCR teammate's module to extract text fields from a document image.
Stores the results in the database.

HOW IT WORKS (non-technical):
- Officer uploads a passport scan
- This endpoint runs text-reading AI on the image
- It extracts: name, date of birth, document number, nationality, expiry date
- Each field gets a confidence score (0.0 = guessed, 1.0 = certain)
- Results are stored and feed into the risk engine
"""

import sys
import os
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.case import Document
from app.models.audit import AuditLog
from app.schemas.ocr import OcrResultOut

router = APIRouter()
PLACEHOLDER_OFFICER_ID = UUID("00000000-0000-0000-0000-000000000001")

# Add project root so we can import ai/ modules
PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def _call_ocr(image_path: str) -> dict:
    """
    Call the OCR teammate's module.

    Returns a dict with structured_fields, field_confidence, raw_text.
    Falls back gracefully if the module isn't available yet.
    """
    try:
        from ai.ocr.extract import run_ocr  # teammate's function
        return run_ocr(image_path)
    except ImportError:
        # OCR module not pushed yet — return a stub so the rest of the pipeline
        # can still run. The stub produces a risk signal flagging missing OCR.
        return {
            "structured_fields": {},
            "field_confidence": {},
            "raw_text": "",
            "_stub": True,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OCR processing failed: {str(e)}",
        )


@router.post(
    "/{document_id}/ocr",
    response_model=OcrResultOut,
    status_code=status.HTTP_201_CREATED,
    summary="Run OCR on a document",
    description=(
        "Extract text fields from a document image using the OCR module. "
        "Returns structured fields (name, DOB, doc number, nationality, expiry) "
        "with confidence scores."
    ),
)
async def run_ocr_on_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> OcrResultOut:
    """Run OCR on a previously uploaded document."""

    # 1. Verify document exists
    doc = await db.get(Document, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # 2. Call OCR module
    result = _call_ocr(doc.image_path)

    # 3. Store result
    from app.models.ocr_result import OcrResult
    ocr_record = OcrResult(
        document_id=document_id,
        case_id=doc.case_id,
        structured_fields=result.get("structured_fields", {}),
        field_confidence=result.get("field_confidence", {}),
        raw_text=result.get("raw_text", ""),
        is_stub=result.get("_stub", False),
    )
    db.add(ocr_record)

    # 4. Audit log
    db.add(AuditLog(
        user_id=PLACEHOLDER_OFFICER_ID,
        case_id=doc.case_id,
        action="ocr_completed",
        details=f"Document: {document_id}, stub={result.get('_stub', False)}",
    ))

    await db.commit()
    await db.refresh(ocr_record)
    return OcrResultOut.model_validate(ocr_record)

