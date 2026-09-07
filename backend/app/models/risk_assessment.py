"""VERIFAI — Risk Assessment & Risk Signal Models"""
import uuid as uuid_module
from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin


class RiskAssessment(Base, TimestampMixin):
    """
    The aggregated risk assessment for a case.
    One case can have multiple assessments (as more AI modules complete).
    The latest one is what matters.
    """
    __tablename__ = "risk_assessments"

    id: Mapped[uuid_module.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid_module.uuid4)
    case_id: Mapped[uuid_module.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False, index=True)
    # 0.0 to 100.0 — the AI's overall risk recommendation
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    # "low", "medium", "high"
    risk_band: Mapped[str] = mapped_column(String(50), nullable=False)
    # Child signals that contributed to this assessment
    signals: Mapped[list["RiskSignal"]] = relationship("RiskSignal", back_populates="assessment", lazy="selectin")

    def __repr__(self) -> str:
        return f"<RiskAssessment case={self.case_id} score={self.overall_score} band={self.risk_band}>"


class RiskSignal(Base, TimestampMixin):
    """
    A single explainable signal that contributed to a RiskAssessment.
    The key unit of VERIFAI's explainability.
    """
    __tablename__ = "risk_signals"

    id: Mapped[uuid_module.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid_module.uuid4)
    assessment_id: Mapped[uuid_module.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("risk_assessments.id"), nullable=False, index=True)
    case_id: Mapped[uuid_module.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False)

    signal_name: Mapped[str] = mapped_column(String(100), nullable=False)
    # "increases_risk", "decreases_risk", "neutral"
    direction: Mapped[str] = mapped_column(String(50), nullable=False)
    # How much this signal contributed (0-100 scale)
    magnitude: Mapped[float] = mapped_column(Float, nullable=False)
    # What the officer sees — plain English
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    # Which module produced this signal
    source_module: Mapped[str] = mapped_column(String(50), nullable=False)

    assessment: Mapped["RiskAssessment"] = relationship("RiskAssessment", back_populates="signals")

    def __repr__(self) -> str:
        return f"<RiskSignal {self.signal_name} {self.direction} {self.magnitude}>"

