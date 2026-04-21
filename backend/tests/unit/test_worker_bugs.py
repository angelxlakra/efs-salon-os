"""
Regression tests for two bugs found in worker startup logs.

Bug 1: SAWarning — Expense.recurring_instances relationship conflicts with
       Expense.parent_expense due to missing overlaps= and wrong remote_side.

Bug 2: ModuleNotFoundError for boto3 — BackupService._get_s3_client()
       raises ImportError instead of gracefully disabling cloud support
       when boto3 is not installed.

To run:
    uv run pytest tests/unit/test_worker_bugs.py -v
"""

import warnings
import pytest
from unittest.mock import patch, MagicMock
import sys


# ---------------------------------------------------------------------------
# Bug 1: SQLAlchemy SAWarning on Expense.recurring_instances
# ---------------------------------------------------------------------------

def test_expense_relationships_no_sqlalchemy_warning():
    """Regression: importing Expense model must not emit a SAWarning about
    overlapping relationships between recurring_instances and parent_expense.
    """
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")

        # Force SQLAlchemy mapper configuration by importing the model and
        # triggering configure_mappers via a relationship access pattern
        from sqlalchemy.orm import configure_mappers
        from app.models.expense import Expense  # noqa: F401
        configure_mappers()

    sa_warnings = [
        w for w in caught
        if issubclass(w.category, Exception.__class__)
        or "SAWarning" in str(w.category)
        or "relationship" in str(w.message).lower()
        and "overlaps" in str(w.message).lower()
    ]
    # The warning text we expect to be silenced after the fix
    overlap_warnings = [
        w for w in caught
        if "overlaps" in str(w.message).lower()
        and "recurring_instances" in str(w.message).lower()
    ]
    assert overlap_warnings == [], (
        f"Expected no SAWarning about recurring_instances overlaps, got: "
        f"{[str(w.message) for w in overlap_warnings]}"
    )


def test_expense_recurring_instances_relationship_direction():
    """Regression: recurring_instances should be a one-to-many (parent→children),
    not a reversed/malformed self-referential relationship.
    The relationship should NOT have remote_side pointing at parent_expense_id.
    """
    from app.models.expense import Expense
    from sqlalchemy import inspect as sa_inspect

    mapper = sa_inspect(Expense)
    rel = mapper.relationships["recurring_instances"]

    # remote_side should be the primary-key column (id), not parent_expense_id
    remote_cols = {col.key for col in rel.remote_side}
    assert "parent_expense_id" not in remote_cols, (
        "recurring_instances.remote_side incorrectly points at parent_expense_id; "
        "it should point at the primary key (id) for a parent→children relationship."
    )


# ---------------------------------------------------------------------------
# Bug 2: BackupService._get_s3_client raises ImportError (not RuntimeError)
#         when boto3 is absent from the environment.
# ---------------------------------------------------------------------------

def _make_import_raiser(real_import):
    """Return a side-effect for builtins.__import__ that raises ImportError for boto3."""
    def _import(name, *args, **kwargs):
        if name == "boto3":
            raise ImportError("No module named 'boto3'")
        return real_import(name, *args, **kwargs)
    return _import


def test_get_s3_client_raises_runtime_error_when_boto3_missing():
    """Regression: _get_s3_client must raise RuntimeError (not raw ImportError/
    ModuleNotFoundError) when boto3 is not installed, so callers can catch it
    cleanly and the ERROR log shows a meaningful message.
    """
    import builtins
    from app.services.backup_service import BackupService

    service = BackupService()
    service._s3_client = None  # force re-creation even if cached

    real_import = builtins.__import__
    with patch("builtins.__import__", side_effect=_make_import_raiser(real_import)):
        # After fix: RuntimeError, not ImportError / ModuleNotFoundError
        with pytest.raises(RuntimeError) as exc_info:
            service._get_s3_client()

    assert "boto3" in str(exc_info.value).lower(), (
        f"RuntimeError should mention 'boto3', got: {exc_info.value}"
    )


def test_get_s3_client_raw_import_error_is_current_broken_behavior():
    """Documents the CURRENT broken behaviour before the fix.
    _get_s3_client raises raw ImportError when boto3 is missing.
    This test should FAIL after the fix (proving the fix works).
    """
    import builtins
    from app.services.backup_service import BackupService

    service = BackupService()
    service._s3_client = None

    real_import = builtins.__import__
    with patch("builtins.__import__", side_effect=_make_import_raiser(real_import)):
        # Current broken behaviour: raises ImportError, not RuntimeError
        with pytest.raises(ImportError):
            service._get_s3_client()
