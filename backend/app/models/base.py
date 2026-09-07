"""
VERIFAI — SQLAlchemy Declarative Base & Mixins
===============================================

This file defines the foundation that ALL database models inherit from.

WHY THIS FILE EXISTS:
- SQLAlchemy needs a single "Base" class that tracks all your models
- When you do Base.metadata.create_all(), it creates tables for every model
  that inherits from Base
- The TimestampMixin adds created_at/updated_at to every table automatically

HOW IT CONNECTS TO VERIFAI:
- Every model (User, Case, Document, AuditLog, etc.) inherits Base + TimestampMixin
- This ensures consistent timestamp tracking across the entire system
- Audit trail depends on these timestamps
"""

from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """
    The root class for all VERIFAI database models.

    SQLAlchemy 2.0 uses DeclarativeBase instead of the old
    declarative_base() function. Every model class that inherits
    from this will automatically become a database table.
    """
    pass


class TimestampMixin:
    """
    Adds created_at and updated_at columns to any model that inherits this.

    WHY A MIXIN:
    - DRY (Don't Repeat Yourself) — instead of adding these two columns
      to every single model, we define them once here
    - Every table in VERIFAI needs timestamps for audit/accountability

    HOW IT WORKS:
    - created_at: Set automatically by PostgreSQL when the row is inserted
    - updated_at: Set automatically when the row is modified
    """

    created_at: Mapped[datetime] = mapped_column(
        # server_default=func.now() means PostgreSQL itself sets the time,
        # not Python. This is more reliable because:
        # 1. It uses the DB server's clock (consistent across app instances)
        # 2. It works even if you insert rows via raw SQL
        server_default=func.now(),
    )

    updated_at: Mapped[datetime | None] = mapped_column(
        # onupdate=func.now() means SQLAlchemy will set this column
        # every time the row is updated via the ORM.
        # It's nullable because new rows haven't been updated yet.
        default=None,
        onupdate=func.now(),
    )

