"""VERIFAI — OCR Result Model"""
import uuid as uuid_module
from sqlalchemy import Boolean, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base, TimestampMixin


class OcrResult(Base, TimestampMixin):
    __tablename__ = "ocr_results"

    id: Mapped[uuid_module.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid_module.uuid4)
    document_id: Mapped[uuid_module.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False, index=True)
    case_id: Mapped[uuid_module.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False, index=True)

    # structured_fields: {"name": "JOHN DOE", "dob": "1990-01-15", ...}
    structured_fields: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    # field_confidence: {"name": 0.95, "dob": 0.88, ...}
    field_confidence: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    # True when OCR module wasn't available and we used a stub
    is_stub: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    def __repr__(self) -> str:
        return f"<OcrResult doc={self.document_id} stub={self.is_stub}>"

