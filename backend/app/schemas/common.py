"""
VERIFAI — Canonical Shared Schemas (RiskSignal & RiskAssessment)
=================================================================

These are the MOST IMPORTANT data contracts in the entire system.

ARCHITECTURE PRINCIPLE:
Every AI module (OCR, MRZ, face, forensics, validation, consistency)
ultimately produces RiskSignal objects. The risk engine consumes
RiskSignal[] and produces one RiskAssessment. This separation is
the backbone of VERIFAI's explainability.

WHY THIS MATTERS FOR JUDGES:
- Each risk signal has a human-readable explanation
- The overall score is fully decomposable — you can show exactly
  WHY the score is 72, not just THAT it is 72
- This is what makes VERIFAI different from a black-box classifier

EXAMPLE:
    RiskSignal(
        signal_name="MRZ_CHECKSUM_FAILURE",
        direction="increases_risk",
        magnitude=30.0,
        explanation="MRZ checksum validation failed for passport number field",
        source_module="mrz"
    )

    RiskAssessment(
        overall_score=72.0,
        risk_band="high",
        contributing_signals=[...list of RiskSignals...]
    )

The officer sees the RiskAssessment, can expand each contributing signal,
and then makes their own decision. The system NEVER decides.
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RiskSignalIn(BaseModel):
    """
    The universal unit every AI module produces.
    The risk engine consumes a list of these.

    FIELDS EXPLAINED:
    - signal_name: Machine-readable identifier (e.g., "MRZ_CHECKSUM_FAILURE")
    - direction: Does this signal make things more risky, less risky, or neutral?
    - magnitude: How much does this signal contribute? (0 = no impact, 100 = critical)
    - explanation: Human-readable text shown to the officer
    - source_module: Which AI module produced this signal
    """
    signal_name: str
    direction: Literal["increases_risk", "decreases_risk", "neutral"]
    magnitude: float = Field(ge=0, le=100, description="0-100 scale of signal strength")
    explanation: str
    source_module: Literal["ocr", "mrz", "validation", "forensics", "face", "consistency"]


class RiskSignalOut(RiskSignalIn):
    """RiskSignal as stored in the database and returned by the API."""
    id: UUID
    case_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RiskAssessmentOut(BaseModel):
    """
    Final output of the risk engine for one case.

    The overall_score is computed from contributing_signals.
    The risk_band is derived from the score:
    - 0-39: low
    - 40-69: medium
    - 70-100: high

    This is the AI's RECOMMENDATION. The officer makes the final call.
    """
    id: UUID
    case_id: UUID
    overall_score: float
    risk_band: str
    contributing_signals: list[RiskSignalOut] = []
    computed_at: datetime

    model_config = ConfigDict(from_attributes=True)

