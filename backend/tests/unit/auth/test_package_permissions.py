"""Verify the new packages.* permissions are wired into RBAC correctly."""

import pytest
from app.auth.permissions import PermissionChecker
from app.models.user import RoleEnum


@pytest.mark.parametrize("role,permission,allowed", [
    # packages:read — all roles
    (RoleEnum.OWNER, ("packages", "read"), True),
    (RoleEnum.RECEPTIONIST, ("packages", "read"), True),
    (RoleEnum.STAFF, ("packages", "read"), True),
    # packages:create/update/delete — Owner only
    (RoleEnum.OWNER, ("packages", "create"), True),
    (RoleEnum.RECEPTIONIST, ("packages", "create"), False),
    (RoleEnum.STAFF, ("packages", "create"), False),
    (RoleEnum.OWNER, ("packages", "update"), True),
    (RoleEnum.RECEPTIONIST, ("packages", "update"), False),
    (RoleEnum.OWNER, ("packages", "delete"), True),
    (RoleEnum.RECEPTIONIST, ("packages", "delete"), False),
    # packages:sell — Owner + Receptionist
    (RoleEnum.OWNER, ("packages", "sell"), True),
    (RoleEnum.RECEPTIONIST, ("packages", "sell"), True),
    (RoleEnum.STAFF, ("packages", "sell"), False),
    # packages:redeem — all roles
    (RoleEnum.OWNER, ("packages", "redeem"), True),
    (RoleEnum.RECEPTIONIST, ("packages", "redeem"), True),
    (RoleEnum.STAFF, ("packages", "redeem"), True),
    # packages:redeem_for_other — Owner + Receptionist
    (RoleEnum.OWNER, ("packages", "redeem_for_other"), True),
    (RoleEnum.RECEPTIONIST, ("packages", "redeem_for_other"), True),
    (RoleEnum.STAFF, ("packages", "redeem_for_other"), False),
    # packages:refund / extend_expiry / override_price — Owner only
    (RoleEnum.OWNER, ("packages", "refund"), True),
    (RoleEnum.RECEPTIONIST, ("packages", "refund"), False),
    (RoleEnum.OWNER, ("packages", "extend_expiry"), True),
    (RoleEnum.RECEPTIONIST, ("packages", "extend_expiry"), False),
    (RoleEnum.OWNER, ("packages", "override_price"), True),
    (RoleEnum.RECEPTIONIST, ("packages", "override_price"), False),
])
def test_package_permissions(role, permission, allowed):
    resource, action = permission
    assert PermissionChecker.has_permission(role, resource, action) is allowed
