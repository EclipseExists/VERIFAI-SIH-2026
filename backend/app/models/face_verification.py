"""
VERIFAI — Face Verification Model
====================================

Stores the result of a 1:1 face comparison between a document photo
and a live/probe photo of the traveller.

ARCHITECTURE:
- Face verification is per-CASE, not per-document
- The case may have multiple documents, but the face comparison is:
    document face (extracted from passport/ID) vs. probe face (live capture)
- Each comparison produces one FaceVerification row
- The row also stores which document the face was extracted from

IMPORTANT DESIGN DECISIONS:
- We store the raw similarity_score AND the band (match/uncertain/mismatch)
- The band is derived from thresholds in the AI module, NOT hardcoded here
- Thresholds may shift during tuning — the raw score is the ground truth
- We also store the image paths so results are reproducible/auditable

RISK SIGNAL GENERATION:
- A "mismatch" band → high-magnitude risk signal (increases_risk)
- An "uncertain" band → moderate-magnitude risk signal (increases_risk)
- A "match" band → signal that decreases_risk
- Face not detected → its own signal (increases_risk, moderate)
"""

import uuid as uuid_module
from datetime import datetime

from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class FaceVerification(Base, TimestampMixin):
    """
    Result of a 1:1 face comparison for a case.

    NOT face recognition (searching a population).
    NOT identification (who is this person?).
    Just: "does the face on the document match the face in front of me?"
    """

    __tablename__ = "face_verifications"

    id: Mapped[uuid_module.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid_module.uuid4,
    )

    # Which case this verification belongs to
    case_id: Mapped[uuid_module.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cases.id"),
        nullable=False,
        index=True,
    )

    # Which document the face was extracted from (e.g., passport photo)
    document_id: Mapped[uuid_module.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id"),
        nullable=False,
    )

    # Path to the document face image (extracted/cropped from the document)
    doc_face_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    # Path to the probe/live face image (photo of the traveller)
    probe_face_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    # ── Results from the AI module ────────────────────────────────

    # Raw similarity score (0.0 to 1.0) — always store this
    similarity_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    # Derived band: "match", "uncertain", or "mismatch"
    # Thresholds are set in the AI module, not here
    band: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    # If the AI module couldn't detect a face, this records why
    # NULL means face detection succeeded
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<FaceVerification case={self.case_id} score={self.similarity_score} band={self.band}>"

