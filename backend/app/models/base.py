"""Base model classes and mixins for SalonOS."""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, DateTime, String, func
from sqlalchemy.orm import declared_attr
from app.utils import generate_ulid


class TimestampMixin:
    """
    Mixin that adds created_at and updated_at timestamp columns.

    - created_at: Set automatically on insert
    - updated_at: Set automatically on insert and updated on every update
    """

    @declared_attr
    def created_at(cls):
        return Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now()
        )

    @declared_attr
    def updated_at(cls):
        return Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
            onupdate=func.now()
        )


class SoftDeleteMixin:
    """
    Mixin that adds soft delete functionality via deleted_at column.

    - When deleted_at IS NULL, the record is active
    - When deleted_at has a timestamp, the record is soft-deleted

    Usage in queries:
        # Only active records
        query.filter(Model.deleted_at.is_(None))

        # Only deleted records
        query.filter(Model.deleted_at.isnot(None))
    """

    @declared_attr
    def deleted_at(cls):
        return Column(
            DateTime(timezone=True),
            nullable=True
        )

    @property
    def is_deleted(self) -> bool:
        """Check if this record is soft-deleted."""
        return self.deleted_at is not None

    def soft_delete(self) -> None:
        """Mark this record as deleted."""
        self.deleted_at = func.now()

    def restore(self) -> None:
        """Restore a soft-deleted record."""
        self.deleted_at = None


class ULIDMixin:
    """
    Mixin that adds a ULID primary key.

    ULIDs are:
    - 26 characters long
    - Lexicographically sortable
    - Timestamp-based (first 48 bits)
    - URL-safe

    Example: 01HXXX1234ABCD567890EFGH
    """

    @declared_attr
    def id(cls):
        return Column(
            String(26),
            primary_key=True,
            default=generate_ulid
        )
