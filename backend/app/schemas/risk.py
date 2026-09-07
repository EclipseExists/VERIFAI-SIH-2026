"""VERIFAI — Risk Assessment Schemas"""
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class RiskSignalOut(BaseModel):
    id: UUID
    signal_name: str
    direction: str
    magnitude: float
    explanation: str
    source_module: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class RiskAssessmentOut(BaseModel):
    id: UUID
    case_id: UUID
    overall_score: float
    risk_band: str
    signals: list[RiskSignalOut] = []
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

