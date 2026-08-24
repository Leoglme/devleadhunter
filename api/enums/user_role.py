"""
User role enumeration for authorization.
"""

from enum import Enum


class UserRole(str, Enum):
    """
    User role enumeration.

    Attributes:
        USER: Standard user role
        ADMIN: Platform operator — unlimited credits, monitoring/storage access
        SUPER_ADMIN: Platform owner — full administration (users, billing, accounting)
    """

    USER = "USER"
    ADMIN = "ADMIN"
    SUPER_ADMIN = "SUPER_ADMIN"


_PLATFORM_ADMIN_ROLES: frozenset[str] = frozenset({UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value})
_UNLIMITED_CREDIT_ROLES: frozenset[str] = _PLATFORM_ADMIN_ROLES


def is_super_admin(role: str | None) -> bool:
    """Return whether *role* is the platform-owner super-admin role."""
    return role == UserRole.SUPER_ADMIN.value


def is_platform_admin(role: str | None) -> bool:
    """Return whether *role* grants operator-level access (admin or super-admin)."""
    return role in _PLATFORM_ADMIN_ROLES


def has_unlimited_credits(role: str | None) -> bool:
    """Return whether *role* bypasses credit consumption and balance limits."""
    return role in _UNLIMITED_CREDIT_ROLES
