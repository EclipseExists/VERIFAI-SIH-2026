"""
VERIFAI — MRZ Integration Endpoint
=====================================

POST /api/v1/documents/{document_id}/mrz

Calls the MRZ teammate's module to parse the Machine-Readable Zone
at the bottom of passports/IDs.

HOW IT WORKS (non-technical):
- The MRZ is the two rows of text at the bottom of a passport (all caps + <<)
- It encodes: name, nationality, DOB, expiry, document number
- Each field has a checksum digit — like a checkcode for validation
- If any checksum fails, the document has been altered or is fake
- This is the most legally defensible signal in the whole system
"""

import sys
import os
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.case import Document
from app.models.audit import AuditLog
from app.schemas.mrz import MrzResultOut

router = APIRouter()
PLACEHOLDER_OFFICER_ID = UUID("00000000-0000-0000-0000-000000000001")

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def _call_mrz(image_path: str) -> dict:
    """
    Call the MRZ teammate's module.
    Falls back to stub if not yet available.
    """
    try:
        from ai.mrz.parse import parse_mrz  # teammate's function
        return parse_mrz(image_path)
    except ImportError:
        return {
            "mrz_present": False,
            "parsed_fields": {},
            "checksum_valid": None,
            "checksum_details": [],
            "_stub": True,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"MRZ parsing failed: {str(e)}",
        )


@router.post(
    "/{document_id}/mrz",
    response_model=MrzResultOut,
    status_code=status.HTTP_201_CREATED,
    summary="Parse MRZ zone",
    description=(
        "Parse the Machine-Readable Zone (MRZ) at the bottom of a passport/ID. "
        "Validates ICAO 9303 checksums. A checksum failure is a strong tamper signal."
    ),
)
async def run_mrz_on_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> MrzResultOut:
    """Parse the MRZ zone and validate checksums."""

    doc = await db.get(Document, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    result = _call_mrz(doc.image_path)

    from app.models.mrz_result import MrzResult
    mrz_record = MrzResult(
        document_id=document_id,
        case_id=doc.case_id,
        mrz_present=result.get("mrz_present", False),
        parsed_fields=result.get("parsed_fields", {}),
        checksum_valid=result.get("checksum_valid"),
        checksum_details=result.get("checksum_details", []),
        is_stub=result.get("_stub", False),
    )
    db.add(mrz_record)

    db.add(AuditLog(
        user_id=PLACEHOLDER_OFFICER_ID,
        case_id=doc.case_id,
        action="mrz_parsed",
        details=(
            f"Document: {document_id}, "
            f"mrz_present={result.get('mrz_present')}, "
            f"checksum_valid={result.get('checksum_valid')}"
        ),
    ))

    await db.commit()
    await db.refresh(mrz_record)
    return MrzResultOut.model_validate(mrz_record)

