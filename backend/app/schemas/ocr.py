"""VERIFAI — OCR Schemas"""
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class OcrResultOut(BaseModel):
    id: UUID
    document_id: UUID
    case_id: UUID
    structured_fields: dict
    field_confidence: dict
    raw_text: str | None = None
    is_stub: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

