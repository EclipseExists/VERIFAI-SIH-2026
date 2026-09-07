"""
VERIFAI — Case Schemas (API Contracts)
=======================================

These Pydantic models define the shape of data flowing through the Case API.

WHY SCHEMAS ARE SEPARATE FROM MODELS:
- SQLAlchemy models define how data is STORED in the database
- Pydantic schemas define how data is SENT/RECEIVED through the API
- They are often different! For example:
  - CaseCreate doesn't include id (the DB generates it)
  - CaseOut includes nested documents (joined from another table)
  - CaseDecision only has the fields an officer needs to fill in

This separation is called "Data Transfer Objects" (DTOs) and it prevents:
- Accidentally exposing internal database fields
- Forcing clients to send fields that the server should set
- Tight coupling between API shape and database shape

HOW IT CONNECTS TO VERIFAI:
- Frontend sends CaseCreate to POST /api/v1/cases
- Backend returns CaseOut with all the case data + nested documents
- Officer sends CaseDecision to POST /api/v1/cases/{id}/decision
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


# ── Request Schemas (what the client SENDS) ───────────────────────


class CaseCreate(BaseModel):
    """
    Data needed to create a new screening case.

    Only optional fields — the backend generates the id, timestamp,
    and links the case to the logged-in officer automatically.
    """
    subject_name: str | None = None
    notes: str | None = None


class CaseDecision(BaseModel):
    """
    Officer's explicit human-in-the-loop decision.

    The system NEVER auto-decides. The risk engine recommends a risk band,
    but the officer must explicitly choose one of:
    - approve: traveller cleared
    - reject: traveller denied
    - escalate: needs supervisor review

    This is the most important endpoint in VERIFAI from a design perspective.
    """
    decision: Literal["approve", "reject", "escalate"]
    decision_notes: str | None = None


# ── Response Schemas (what the server RETURNS) ────────────────────


class DocumentOut(BaseModel):
    """A document within a case, returned in API responses."""
    id: UUID
    case_id: UUID
    doc_type: str
    image_path: str
    original_filename: str | None = None
    quality_passed: bool | None = None
    blur_score: float | None = None
    quality_notes: str | None = None
    created_at: datetime

    # from_attributes=True tells Pydantic to read data from
    # SQLAlchemy model attributes (e.g., document.id) instead of
    # expecting a dictionary. This is what makes CaseOut work
    # when we return a SQLAlchemy object directly.
    model_config = ConfigDict(from_attributes=True)


class CaseOut(BaseModel):
    """
    Full case detail returned by the API.

    Includes nested documents so the frontend can display
    everything about a case in one API call.
    """
    id: UUID
    officer_id: UUID
    status: str
    subject_name: str | None = None
    notes: str | None = None
    decision: str | None = None
    decision_notes: str | None = None
    decided_at: datetime | None = None
    risk_score: float | None = None
    risk_band: str | None = None
    created_at: datetime
    updated_at: datetime | None = None
    documents: list[DocumentOut] = []

    model_config = ConfigDict(from_attributes=True)


class CaseSummary(BaseModel):
    """
    Compact case listing for the dashboard table.

    Doesn't include documents or full notes — just enough
    for the officer to scan a list and click into one.
    """
    id: UUID
    status: str
    subject_name: str | None = None
    risk_band: str | None = None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

