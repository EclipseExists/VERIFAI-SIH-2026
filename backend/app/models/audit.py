"""
VERIFAI — Audit Log Model
===========================

This model records every significant action in the system.

WHY AUDIT LOGGING IS CRITICAL:
- VERIFAI is an identity/security screening system
- Judges WILL ask: "Who accessed this data? When? What did they do?"
- Audit logs provide accountability and traceability
- In a real system, these logs would be legally required
- They're also useful for debugging ("what happened to case X?")

WHAT GETS LOGGED:
- case_created: Officer opened a new screening case
- document_uploaded: A document image was added to a case
- ocr_completed: OCR processing finished
- mrz_validated: MRZ checksum validation ran
- risk_assessed: Risk engine produced a new assessment
- decision_made: Officer submitted a final decision (THE key audit event)
- user_login: Someone logged into the system
- user_created: Admin created a new account

HOW IT CONNECTS TO VERIFAI:
- The audit service (services/audit.py) writes to this table
- API endpoints call the audit service after significant actions
- The admin dashboard can query this table to review activity
"""

import uuid as uuid_module

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class AuditLog(Base, TimestampMixin):
    """
    Immutable record of a system action.

    Audit logs should NEVER be updated or deleted.
    The updated_at field from TimestampMixin exists but should
    always remain NULL for audit records.
    """

    __tablename__ = "audit_logs"

    id: Mapped[uuid_module.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid_module.uuid4,
    )

    # Who performed the action (NULL for system-initiated actions)
    user_id: Mapped[uuid_module.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )

    # Which case was affected (NULL for non-case actions like login)
    case_id: Mapped[uuid_module.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cases.id"),
        nullable=True,
    )

    # What happened — a short action code
    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,  # Fast lookups by action type
    )

    # Additional context as a JSON string
    # Example: '{"document_type": "passport", "filename": "scan.jpg"}'
    details: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # IP address of the request (for security auditing)
    ip_address: Mapped[str | None] = mapped_column(
        String(45),  # IPv6 addresses can be up to 45 chars
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<AuditLog {self.action} at {self.created_at}>"

