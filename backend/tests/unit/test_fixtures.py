"""
  Test that our PostgreSQL fixtures work!
"""

def test_database_session_works(db_session):
    """Test that we can use the database session."""

    from sqlalchemy import text 

    result = db_session.execute(text("SELECT 1 AS test_value"))
    row = result.first()
    assert row is not None
    assert row[0] == 1
    print("✅ Database session works!")

def test_can_create_and_query_data(db_session):
    """Test that we can create data and query it back."""
    from app.models.user import Role, RoleEnum

    test_role = Role(
        name=RoleEnum.OWNER,
        description="Test role for testing",
        permissions={"test": ["read", "write"]}
    )

    db_session.add(test_role)
    db_session.flush()

    found = db_session.query(Role).filter(Role.name == RoleEnum.OWNER).first()

    assert found is not None
    assert found.description == "Test role for testing"
    assert found.permissions == {"test": ["read", "write"]}
    print("✅ Can create and query data!")

def test_transaction_rollback_works(db_session):
    """Test that changes rollback between tests."""
    from app.models.user import Role, RoleEnum

    # This test should see NO roles (previous test rolled back!)
    roles = db_session.query(Role).all()
    assert len(roles) == 0, f"Expected 0 roles, found {len(roles)}"
    print("✅ Transaction rollback works! Database is clean!")
