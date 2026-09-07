"""VERIFAI — MRZ Result Model"""
import uuid as uuid_module
from sqlalchemy import Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base, TimestampMixin


class MrzResult(Base, TimestampMixin):
    __tablename__ = "mrz_results"

    id: Mapped[uuid_module.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid_module.uuid4)
    document_id: Mapped[uuid_module.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False, index=True)
    case_id: Mapped[uuid_module.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False, index=True)

    mrz_present: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # parsed_fields: {"doc_number": "...", "nationality": "IND", ...}
    parsed_fields: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    # None = not yet validated, True = all checksums pass, False = at least one failed
    checksum_valid: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    # checksum_details: [{"field": "doc_number", "expected": 4, "computed": 4, "valid": True}, ...]
    checksum_details: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    is_stub: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    def __repr__(self) -> str:
        return f"<MrzResult doc={self.document_id} valid={self.checksum_valid}>"

