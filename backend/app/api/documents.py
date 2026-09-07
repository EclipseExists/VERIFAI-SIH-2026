"""
VERIFAI — Document Upload Endpoint
======================================

POST /api/v1/cases/{case_id}/documents

This endpoint allows an officer to upload a physical file (like a passport scan)
into a case. It handles:
1. Receiving the file upload via multipart/form-data
2. Saving it securely to the local disk (uploads/ directory)
3. Creating a Document record in the database
4. Generating an audit log

HOW IT CONNECTS:
You CANNOT run face verification or OCR until a document is uploaded.
This is the required first step for all AI processing.
"""

import os
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db
from app.models.case import Case, Document
from app.models.audit import AuditLog
from app.schemas.case import DocumentOut

router = APIRouter()
settings = get_settings()

PLACEHOLDER_OFFICER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


@router.post(
    "/{case_id}/documents",
    response_model=DocumentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a document",
    description="Upload a document image (passport, visa, ID) to a specific case.",
)
async def upload_document(
    case_id: uuid.UUID,
    doc_type: str = Form(..., description="E.g., passport, visa, id_card"),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> DocumentOut:
    """
    Upload a document image to a case.

    Unlike other endpoints that take JSON, this takes a multipart form upload
    so we can handle binary image data.
    """
    # 1. Verify the case exists
    case_query = select(Case).where(Case.id == case_id)
    case_result = await db.execute(case_query)
    case = case_result.scalar_one_or_none()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # 2. Validate file type (basic check)
    allowed_types = ["image/jpeg", "image/png", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {file.content_type}. Must be JPEG, PNG, or WEBP.",
        )

    # 3. Create upload directory if it doesn't exist
    upload_dir = Path(settings.UPLOAD_DIR) / str(case_id)
    upload_dir.mkdir(parents=True, exist_ok=True)

    # 4. Save the file securely (using a new UUID filename to prevent collisions/hacks)
    file_ext = os.path.splitext(file.filename)[1] if file.filename else ".jpg"
    safe_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = upload_dir / safe_filename

    # Read the file and write to disk
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 5. Create database record
    new_doc = Document(
        case_id=case_id,
        doc_type=doc_type,
        image_path=str(file_path),
        original_filename=file.filename,
    )
    db.add(new_doc)

    # 6. Audit log
    audit_entry = AuditLog(
        user_id=PLACEHOLDER_OFFICER_ID,
        case_id=case_id,
        action="document_uploaded",
        details=f"Type: {doc_type}, Original name: {file.filename}",
    )
    db.add(audit_entry)

    await db.commit()
    await db.refresh(new_doc)

    return DocumentOut.model_validate(new_doc)

