"""Role-based permissions system.

This module defines the permission matrix for different roles (Owner, Receptionist, Staff)
and provides utilities to check user permissions for specific resources and actions.
"""

from enum import Enum
from typing import Dict, Any, List
from app.models.user import RoleEnum


class Permission(str, Enum):
    """Permission constants for the system.

    Format: resource.action
    """

    # Billing permissions
    CREATE_BILL = "billing.create"
    READ_BILL = "billing.read"
    UPDATE_BILL = "billing.update"
    REFUND_BILL = "billing.refund"
    APPLY_DISCOUNT = "billing.discount"
    VIEW_TOTALS = "billing.view_totals"

    # Appointment permissions
    CREATE_APPOINTMENT = "appointments.create"
    READ_APPOINTMENT = "appointments.read"
    UPDATE_APPOINTMENT = "appointments.update"
    DELETE_APPOINTMENT = "appointments.delete"
    ASSIGN_STAFF = "appointments.assign_staff"

    # Walk-in permissions
    CREATE_WALKIN = "walkins.create"
    READ_WALKIN = "walkins.read"
    START_SERVICE = "walkins.start"
    COMPLETE_SERVICE = "walkins.complete"

    # Inventory permissions
    CREATE_INVENTORY = "inventory.create"
    READ_INVENTORY = "inventory.read"
    UPDATE_INVENTORY = "inventory.update"
    APPROVE_INVENTORY_CHANGE = "inventory.approve"
    REQUEST_INVENTORY_CHANGE = "inventory.request"
    VIEW_COSTS = "inventory.view_costs"

    # Accounting permissions
    VIEW_DASHBOARD = "accounting.view_dashboard"
    VIEW_PROFIT = "accounting.view_profit"
    EXPORT_REPORTS = "accounting.export"
    MANAGE_DRAWER = "accounting.manage_drawer"

    # Staff/User management
    CREATE_USER = "users.create"
    READ_USER = "users.read"
    UPDATE_USER = "users.update"
    DELETE_USER = "users.delete"

    # Settings permissions
    READ_SETTINGS = "settings.read"
    UPDATE_SETTINGS = "settings.update"

    # Schedule permissions (for staff)
    VIEW_OWN_SCHEDULE = "schedule.view_own"
    VIEW_ALL_SCHEDULES = "schedule.view_all"
    MARK_SERVICE_COMPLETE = "services.mark_complete"
    ADD_SERVICE_NOTES = "services.add_notes"

    # Purchase permissions
    CREATE_PURCHASE = "purchases.create"
    READ_PURCHASE = "purchases.read"
    UPDATE_PURCHASE = "purchases.update"
    DELETE_PURCHASE = "purchases.delete"

    # Expense permissions
    CREATE_EXPENSE = "expenses.create"
    READ_EXPENSE = "expenses.read"
    UPDATE_EXPENSE = "expenses.update"
    DELETE_EXPENSE = "expenses.delete"
    APPROVE_EXPENSE = "expenses.approve"


class PermissionChecker:
    """Check if user has required permissions based on role."""

    # Role-based permission matrix
    ROLE_PERMISSIONS: Dict[RoleEnum, Dict[str, List[str]]] = {
        RoleEnum.OWNER: {
            "billing": ["create", "read", "update", "refund", "discount", "view_totals"],
            "appointments": ["create", "read", "update", "delete", "assign_staff"],
            "walkins": ["create", "read", "update", "delete", "start", "complete"],
            "inventory": ["create", "read", "update", "approve", "view_costs"],
            "accounting": ["view_dashboard", "view_profit", "export", "manage_drawer"],
            "users": ["create", "read", "update", "delete"],
            "settings": ["read", "update"],
            "schedule": ["view_all"],
            "services": ["mark_complete", "add_notes"],
            "purchases": ["create", "read", "update", "delete"],
            "expenses": ["create", "read", "update", "delete", "approve"]
        },
        RoleEnum.RECEPTIONIST: {
            "billing": ["create", "read", "discount", "view_totals"],
            "appointments": ["create", "read", "update", "assign_staff"],
            "walkins": ["create", "read", "update", "start", "complete"],
            "inventory": ["read", "request"],
            "accounting": ["view_dashboard", "manage_drawer"],
            "users": ["read"],
            "schedule": ["view_all"],
            "services": ["mark_complete", "add_notes"],
            "purchases": ["create", "read", "update"],
            "expenses": ["create", "read", "update"]
        },
        RoleEnum.STAFF: {
            "billing": ["create", "read"],
            "schedule": ["view_own", "view_all"],
            "services": ["mark_complete", "add_notes"],
            "walkins": ["create", "read", "start", "complete"]
        }
    }

    # PII (Personally Identifiable Information) restrictions for staff
    STAFF_PII_RESTRICTIONS = {
        "customer_name": "first_name_only",
        "phone": False,
        "email": False,
        "address": False,
        "view_totals": False
    }

    @classmethod
    def has_permission(
        cls,
        role: RoleEnum,
        resource: str,
        action: str
    ) -> bool:
        """Check if role has permission for resource.action.

        Args:
            role: The user's role enum.
            resource: The resource being accessed (e.g., "billing", "appointments").
            action: The action being performed (e.g., "create", "read").

        Returns:
            bool: True if role has permission, False otherwise.

        Example:
            >>> PermissionChecker.has_permission(RoleEnum.OWNER, "billing", "refund")
            True
            >>> PermissionChecker.has_permission(RoleEnum.RECEPTIONIST, "billing", "refund")
            False
        """
        role_perms = cls.ROLE_PERMISSIONS.get(role, {})
        resource_perms = role_perms.get(resource, [])
        return action in resource_perms

    @classmethod
    def get_role_permissions(cls, role: RoleEnum) -> Dict[str, List[str]]:
        """Get all permissions for a role.

        Args:
            role: The user's role enum.

        Returns:
            dict: Dictionary mapping resources to allowed actions.

        Example:
            >>> perms = PermissionChecker.get_role_permissions(RoleEnum.OWNER)
            >>> "billing" in perms
            True
        """
        return cls.ROLE_PERMISSIONS.get(role, {})

    @classmethod
    def can_view_customer_pii(cls, role: RoleEnum) -> bool:
        """Check if role can view full customer PII.

        Staff users have restricted access to customer information
        (first name only, no phone/email).

        Args:
            role: The user's role enum.

        Returns:
            bool: True if role can view full PII, False otherwise.

        Example:
            >>> PermissionChecker.can_view_customer_pii(RoleEnum.OWNER)
            True
            >>> PermissionChecker.can_view_customer_pii(RoleEnum.STAFF)
            False
        """
        return role in [RoleEnum.OWNER, RoleEnum.RECEPTIONIST]

    @classmethod
    def can_view_financials(cls, role: RoleEnum) -> bool:
        """Check if role can view financial totals and profit data.

        Staff users cannot see billing totals, profit margins, or
        financial dashboards.

        Args:
            role: The user's role enum.

        Returns:
            bool: True if role can view financials, False otherwise.

        Example:
            >>> PermissionChecker.can_view_financials(RoleEnum.OWNER)
            True
            >>> PermissionChecker.can_view_financials(RoleEnum.STAFF)
            False
        """
        return role in [RoleEnum.OWNER, RoleEnum.RECEPTIONIST]

    @classmethod
    def can_approve_inventory(cls, role: RoleEnum) -> bool:
        """Check if role can approve inventory changes.

        Only owners can approve stock changes to maintain
        inventory control.

        Args:
            role: The user's role enum.

        Returns:
            bool: True if role can approve inventory changes.

        Example:
            >>> PermissionChecker.can_approve_inventory(RoleEnum.OWNER)
            True
            >>> PermissionChecker.can_approve_inventory(RoleEnum.RECEPTIONIST)
            False
        """
        return role == RoleEnum.OWNER

    @classmethod
    def can_manage_users(cls, role: RoleEnum) -> bool:
        """Check if role can create/update/delete users.

        Only owners can manage user accounts.

        Args:
            role: The user's role enum.

        Returns:
            bool: True if role can manage users.

        Example:
            >>> PermissionChecker.can_manage_users(RoleEnum.OWNER)
            True
        """
        return role == RoleEnum.OWNER

    @classmethod
    def get_staff_pii_restrictions(cls) -> Dict[str, Any]:
        """Get PII restrictions for staff users.

        Returns:
            dict: Dictionary of PII field restrictions.

        Example:
            >>> restrictions = PermissionChecker.get_staff_pii_restrictions()
            >>> restrictions["customer_name"]
            'first_name_only'
        """
        return cls.STAFF_PII_RESTRICTIONS.copy()

    @classmethod
    def can_apply_discount(cls, role: RoleEnum, discount_amount: int) -> bool:
        """Check if role can apply discount of given amount.

        Receptionists and Owners can apply any discount.
        Staff cannot apply discounts.

        Args:
            role: The user's role enum.
            discount_amount: Discount amount in paise.

        Returns:
            bool: True if role can apply discount.

        Example:
            >>> # Receptionist can apply any discount
            >>> PermissionChecker.can_apply_discount(RoleEnum.RECEPTIONIST, 100000)
            True
            >>> # Staff cannot apply discount
            >>> PermissionChecker.can_apply_discount(RoleEnum.STAFF, 10000)
            False
        """
        if role == RoleEnum.OWNER:
            return True
        elif role == RoleEnum.RECEPTIONIST:
            # Receptionist can apply any discount
            return True
        else:
            return False
