"""VERIFAI — Forensics Result Model"""
import uuid as uuid_module
from sqlalchemy import Boolean, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base, TimestampMixin


class ForensicsResult(Base, TimestampMixin):
    __tablename__ = "forensics_results"

    id: Mapped[uuid_module.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid_module.uuid4)
    document_id: Mapped[uuid_module.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False, index=True)
    case_id: Mapped[uuid_module.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False, index=True)

    # Error Level Analysis score (0.0-1.0, higher = more anomalous)
    ela_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    # List of bounding boxes where manipulation was detected
    # [{"x": 100, "y": 200, "w": 50, "h": 30, "label": "photo_region"}]
    suspicious_regions: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    noise_inconsistency_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    # 0.0 = definitely clean, 1.0 = definitely manipulated
    overall_manipulation_probability: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_stub: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    def __repr__(self) -> str:
        return f"<ForensicsResult doc={self.document_id} prob={self.overall_manipulation_probability}>"

