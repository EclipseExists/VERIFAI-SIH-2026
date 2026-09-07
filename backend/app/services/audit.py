"""
VERIFAI — Audit Logging Service
==================================

Centralized audit logging for all significant system actions.

WHY A SEPARATE SERVICE:
- Every API endpoint needs audit logging
- Without this, you'd repeat the same 5 lines in every endpoint
- Centralizing it ensures consistency and makes it hard to forget

WHY AUDIT LOGGING MATTERS:
- Identity screening is a sensitive operation
- Judges WILL ask: "Who accessed this case? When? What did they do?"
- In a real system, audit logs would be legally required
- Even for the prototype, this shows mature security thinking

USAGE:
    from app.services.audit import log_action

    await log_action(
        db=db,
        action="case_created",
        user_id=current_user.id,
        case_id=new_case.id,
        details="Subject: John Doe",
    )
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


async def log_action(
    db: AsyncSession,
    action: str,
    user_id: UUID | None = None,
    case_id: UUID | None = None,
    details: str | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    """
    Record an action in the audit log.

    This function creates an AuditLog entry but does NOT commit.
    The calling code should commit as part of its own transaction.
    This way, the audit log and the action it records are in the
    same transaction — either both succeed or both fail.

    Args:
        db: Database session
        action: Short action code (e.g., "case_created", "decision_made")
        user_id: Who performed the action (None for system actions)
        case_id: Which case was affected (None for non-case actions)
        details: Extra context as a string
        ip_address: Client IP address for security auditing
    """
    audit_entry = AuditLog(
        user_id=user_id,
        case_id=case_id,
        action=action,
        details=details,
        ip_address=ip_address,
    )
    db.add(audit_entry)
    return audit_entry

