"""VERIFAI — Forensics Schemas"""
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class ForensicsResultOut(BaseModel):
    id: UUID
    document_id: UUID
    case_id: UUID
    ela_score: float | None = None
    suspicious_regions: list
    noise_inconsistency_score: float | None = None
    overall_manipulation_probability: float | None = None
    is_stub: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

