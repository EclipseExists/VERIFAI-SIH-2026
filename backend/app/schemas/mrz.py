"""VERIFAI — MRZ Schemas"""
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class MrzResultOut(BaseModel):
    id: UUID
    document_id: UUID
    case_id: UUID
    mrz_present: bool
    parsed_fields: dict
    checksum_valid: bool | None = None
    checksum_details: list
    is_stub: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

