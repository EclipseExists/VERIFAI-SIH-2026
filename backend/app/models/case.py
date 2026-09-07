"""
VERIFAI — Case & Document Models
==================================

These are the CORE models of the entire system.

ARCHITECTURE FLOW:
1. Officer creates a Case (one screening session for one traveller)
2. Officer uploads one or more Documents (passport, visa, etc.) to the Case
3. AI modules process each Document and produce signals
4. Risk engine aggregates signals into a RiskAssessment
5. Officer reviews everything and submits a Decision

WHY CASES AND DOCUMENTS ARE SEPARATE:
- One traveller might have multiple documents (passport + visa + ID)
- Cross-document consistency checks compare fields BETWEEN documents
- Each document gets its own OCR, MRZ, forensic analysis
- But the final risk assessment is per-CASE (the whole person), not per-document

HUMAN-IN-THE-LOOP (CRITICAL):
- The 'decision' field is NULL until an officer explicitly sets it
- There is NO code path that auto-fills this field
- The risk_score/risk_band are the AI's RECOMMENDATION only
- The officer's decision may disagree with the AI — that's by design
"""

import uuid as uuid_module
from datetime import datetime

from sqlalchemy import Float, ForeignKey, String, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class Case(Base, TimestampMixin):
    """
    A screening case for one traveller at a checkpoint.

    This is the top-level entity. Everything else (documents, signals,
    risk assessments) hangs off a Case.
    """

    __tablename__ = "cases"

    # ── Primary Key ───────────────────────────────────────────────
    id: Mapped[uuid_module.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid_module.uuid4,
    )

    # ── Who created this case ─────────────────────────────────────
    # Foreign key to users.id — the officer who initiated the screening
    officer_id: Mapped[uuid_module.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )

    # ── Case Status ───────────────────────────────────────────────
    # Tracks where the case is in the workflow:
    #   pending    → just created, no processing yet
    #   processing → AI modules are running
    #   reviewed   → AI is done, waiting for officer decision
    #   decided    → officer has made a final decision
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending",
    )

    # ── Subject Info ──────────────────────────────────────────────
    # Optional because the officer might not know the name initially
    subject_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # ── Officer Decision (HUMAN-IN-THE-LOOP) ─────────────────────
    # These fields are NULL until the officer explicitly decides.
    # Valid decisions: "approve", "reject", "escalate"
    # The system NEVER fills these automatically.
    decision: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        default=None,
    )

    decision_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    decided_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
    )

    # ── Risk Assessment Cache ─────────────────────────────────────
    # These cache the LATEST risk engine output for quick display.
    # The full history is in the risk_assessments table.
    risk_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    risk_band: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        # "low", "medium", or "high" — this is the AI's RECOMMENDATION,
        # not the final decision
    )

    # ── Relationships ─────────────────────────────────────────────
    # One case has many documents (passport, visa, etc.)
    documents: Mapped[list["Document"]] = relationship(
        "Document",
        back_populates="case",
        lazy="selectin",  # Eagerly load documents when fetching a case
    )

    # Reference to the officer who created this case
    officer: Mapped["User"] = relationship(
        "User",
        lazy="joined",
    )

    def __repr__(self) -> str:
        return f"<Case {self.id} status={self.status}>"


# Import here to avoid circular import issues with type hints
from .user import User  # noqa: E402


class Document(Base, TimestampMixin):
    """
    A single identity document uploaded for a case.

    Examples: passport, visa, national ID card, travel permit.

    Each document gets independently processed by:
    - Quality gate (blur/resolution check)
    - OCR (text extraction)
    - MRZ parser (machine-readable zone)
    - Document validation (expiry, format rules)
    - Forensics (ELA, noise analysis)
    """

    __tablename__ = "documents"

    # ── Primary Key ───────────────────────────────────────────────
    id: Mapped[uuid_module.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid_module.uuid4,
    )

    # ── Which case does this belong to ────────────────────────────
    case_id: Mapped[uuid_module.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cases.id"),
        nullable=False,
    )

    # ── Document Type ─────────────────────────────────────────────
    # Must be one of: passport, visa, id_card, permit
    # Validation happens in the Pydantic schema layer
    doc_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    # ── File Storage ──────────────────────────────────────────────
    # Relative path to the uploaded image file
    image_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    # Original filename from the upload (for display purposes)
    original_filename: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # ── Quality Check Results ─────────────────────────────────────
    # Filled by the image quality gate module
    quality_passed: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
        # NULL means quality check hasn't run yet
        # True means image is good enough for processing
        # False means image is too blurry/low-res
    )

    blur_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    quality_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # ── Relationships ─────────────────────────────────────────────
    case: Mapped["Case"] = relationship(
        "Case",
        back_populates="documents",
    )

    def __repr__(self) -> str:
        return f"<Document {self.id} type={self.doc_type}>"

