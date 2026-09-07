"""
VERIFAI — Face Verification Schemas
=====================================

Pydantic models for the face verification API.

REQUEST FLOW:
1. Frontend sends FaceVerificationRequest with document_id + probe_face_path
2. Backend finds the document's image, calls the AI module
3. AI module returns similarity_score + band (or raises FaceVerificationError)
4. Backend stores the result and generates a RiskSignal
5. Backend returns FaceVerificationOut to the frontend
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class FaceVerificationRequest(BaseModel):
    """
    Request to run face verification on a case.

    The officer provides:
    - document_id: which document contains the face to compare against
    - probe_face_path: path to the live/probe photo of the traveller

    The backend extracts the document's image_path automatically.
    """
    document_id: UUID
    probe_face_path: str = Field(
        description="Path to the probe/live face image of the traveller"
    )


class FaceVerificationOut(BaseModel):
    """
    Face verification result returned by the API.

    Always includes the raw score AND the band — never just a boolean.
    A judge will ask "what's your threshold?" and we need the score visible.
    """
    id: UUID
    case_id: UUID
    document_id: UUID
    doc_face_path: str
    probe_face_path: str
    similarity_score: float
    band: str  # "match" | "uncertain" | "mismatch"
    error_message: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

