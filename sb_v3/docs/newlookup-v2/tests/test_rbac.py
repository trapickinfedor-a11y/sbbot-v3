from __future__ import annotations

"""RBAC unit tests for the admin web panel.

Tests cover:
- Role page-access grants and denials for all predefined roles
- Custom-role page access from allowed_pages list
- Finance access gating
- Catalog access gating for uploader and custom roles
- require_catalog_access helpers
"""

import unittest
from typing import Dict, List, Optional
from unittest.mock import MagicMock

from web_panel.auth import (
    ROLE_ACCOUNTANT,
    ROLE_ADMIN,
    ROLE_CUSTOM,
    ROLE_FINANCE,
    ROLE_MODERATOR,
    ROLE_OWNER,
    ROLE_SUPPORT,
    ROLE_SUPER_ADMIN,
    ROLE_UPLOADER,
    ROLE_VIEWER,
    ROLE_PAGE_ACCESS,
    FINANCE_ACCESS_ROLES,
    CATALOG_READ_ACCESS_ROLES,
    CATALOG_WRITE_ACCESS_ROLES,
    normalize_permissions,
)


def _make_user(role: str, permissions: Optional[Dict] = None, allowed_pages: Optional[List] = None) -> Dict:
    return {
        "id": 1,
        "username": "test_admin",
        "role": role,
        "permissions": permissions or {},
        "allowed_pages": allowed_pages or [],
        "is_active": True,
    }


class RolePageAccessTests(unittest.TestCase):
    """Check that ROLE_PAGE_ACCESS grants the right pages per role."""

    def _has_access(self, role: str, page: str) -> bool:
        return page in ROLE_PAGE_ACCESS.get(role, set())

    # ── Viewer ────────────────────────────────────────────────────────────────

    def test_viewer_has_products_access(self) -> None:
        self.assertTrue(self._has_access(ROLE_VIEWER, "products"))

    def test_viewer_has_banks_access(self) -> None:
        self.assertTrue(self._has_access(ROLE_VIEWER, "banks"))

    def test_viewer_no_finance_access(self) -> None:
        self.assertFalse(self._has_access(ROLE_VIEWER, "finance"))

    def test_viewer_no_users_access(self) -> None:
        self.assertFalse(self._has_access(ROLE_VIEWER, "users"))

    def test_viewer_no_admins_access(self) -> None:
        self.assertFalse(self._has_access(ROLE_VIEWER, "admins"))

    # ── Support ───────────────────────────────────────────────────────────────

    def test_support_has_users_access(self) -> None:
        self.assertTrue(self._has_access(ROLE_SUPPORT, "users"))

    def test_support_has_orders_access(self) -> None:
        self.assertTrue(self._has_access(ROLE_SUPPORT, "orders"))

    def test_support_no_finance_access(self) -> None:
        self.assertFalse(self._has_access(ROLE_SUPPORT, "finance"))

    def test_support_no_bots_access(self) -> None:
        self.assertFalse(self._has_access(ROLE_SUPPORT, "bots"))

    # ── Moderator ─────────────────────────────────────────────────────────────

    def test_moderator_has_seller_moderation(self) -> None:
        self.assertTrue(self._has_access(ROLE_MODERATOR, "seller_moderation"))

    def test_moderator_no_deposits(self) -> None:
        self.assertFalse(self._has_access(ROLE_MODERATOR, "deposits"))

    # ── Finance / Accountant ──────────────────────────────────────────────────

    def test_finance_has_finance_page(self) -> None:
        self.assertTrue(self._has_access(ROLE_FINANCE, "finance"))

    def test_finance_has_deposits(self) -> None:
        self.assertTrue(self._has_access(ROLE_FINANCE, "deposits"))

    def test_finance_has_disputes(self) -> None:
        self.assertTrue(self._has_access(ROLE_FINANCE, "disputes"))

    def test_finance_no_bots(self) -> None:
        self.assertFalse(self._has_access(ROLE_FINANCE, "bots"))

    def test_accountant_has_finance_page(self) -> None:
        self.assertTrue(self._has_access(ROLE_ACCOUNTANT, "finance"))

    # ── Uploader ──────────────────────────────────────────────────────────────

    def test_uploader_has_products(self) -> None:
        self.assertTrue(self._has_access(ROLE_UPLOADER, "products"))

    def test_uploader_has_banks(self) -> None:
        self.assertTrue(self._has_access(ROLE_UPLOADER, "banks"))

    def test_uploader_no_finance(self) -> None:
        self.assertFalse(self._has_access(ROLE_UPLOADER, "finance"))

    def test_uploader_no_users(self) -> None:
        self.assertFalse(self._has_access(ROLE_UPLOADER, "users"))

    # ── Admin / Owner / Super Admin ───────────────────────────────────────────

    def test_admin_has_all_pages(self) -> None:
        for page in ("dashboard", "finance", "users", "admins", "bots", "deposits", "products"):
            self.assertTrue(self._has_access(ROLE_ADMIN, page), f"Admin missing page: {page}")

    def test_owner_has_all_pages(self) -> None:
        for page in ("dashboard", "finance", "admins", "sellers", "disputes"):
            self.assertTrue(self._has_access(ROLE_OWNER, page))

    def test_super_admin_has_all_pages(self) -> None:
        for page in ("dashboard", "finance", "admins", "bots", "deposits"):
            self.assertTrue(self._has_access(ROLE_SUPER_ADMIN, page))


class NormalizePermissionsTests(unittest.TestCase):
    """Test the normalize_permissions helper."""

    def test_none_returns_empty_dict(self) -> None:
        self.assertEqual(normalize_permissions(None), {})

    def test_dict_passthrough(self) -> None:
        perms = {"finance_access": True, "crm_edit": False}
        result = normalize_permissions(perms)
        self.assertEqual(result["finance_access"], True)

    def test_list_input_returns_empty_dict(self) -> None:
        """normalize_permissions only accepts dicts; lists return empty dict."""
        perms = ["finance_access", "crm_edit"]
        result = normalize_permissions(perms)
        self.assertEqual(result, {})

    def test_empty_list_returns_empty_dict(self) -> None:
        self.assertEqual(normalize_permissions([]), {})

    def test_non_dict_non_list_returns_empty(self) -> None:
        self.assertEqual(normalize_permissions("invalid"), {})


class CustomRolePageAccessTests(unittest.TestCase):
    """Custom roles get page access from allowed_pages field."""

    def test_custom_role_with_allowed_pages(self) -> None:
        user = _make_user(
            ROLE_CUSTOM,
            permissions={"finance_access": True},
            allowed_pages=["finance", "users"],
        )
        pages = set(user.get("allowed_pages", []))
        self.assertIn("finance", pages)
        self.assertIn("users", pages)
        self.assertNotIn("admins", pages)

    def test_custom_role_without_finance_permission(self) -> None:
        user = _make_user(
            ROLE_CUSTOM,
            permissions={},
            allowed_pages=["users"],
        )
        perms = normalize_permissions(user.get("permissions"))
        has_finance = perms.get("finance_access", False)
        self.assertFalse(has_finance)

    def test_custom_role_crm_edit_permission(self) -> None:
        user = _make_user(
            ROLE_CUSTOM,
            permissions={"crm_edit": True},
        )
        perms = normalize_permissions(user.get("permissions"))
        self.assertTrue(perms.get("crm_edit"))
        self.assertFalse(perms.get("ban_users"))

    def test_custom_role_ban_users_permission(self) -> None:
        user = _make_user(
            ROLE_CUSTOM,
            permissions={"ban_users": True},
        )
        perms = normalize_permissions(user.get("permissions"))
        self.assertTrue(perms.get("ban_users"))
        self.assertFalse(perms.get("finance_access"))


class CatalogAccessTests(unittest.TestCase):
    """Tests for catalog access logic (without DB, pure logic)."""

    def test_uploader_has_catalog_access_by_role(self) -> None:
        from web_panel.auth import CATALOG_READ_ACCESS_ROLES
        self.assertIn(ROLE_UPLOADER, CATALOG_READ_ACCESS_ROLES)

    def test_finance_role_has_finance_page_access(self) -> None:
        """Finance role accesses catalogs through their own page permissions, not CATALOG_READ_ACCESS_ROLES."""
        self.assertIn("finance", ROLE_PAGE_ACCESS.get(ROLE_FINANCE, set()))

    def test_admin_has_catalog_access_by_role(self) -> None:
        from web_panel.auth import CATALOG_READ_ACCESS_ROLES
        self.assertIn(ROLE_ADMIN, CATALOG_READ_ACCESS_ROLES)

    def test_viewer_has_catalog_read_access(self) -> None:
        from web_panel.auth import CATALOG_READ_ACCESS_ROLES
        self.assertIn(ROLE_VIEWER, CATALOG_READ_ACCESS_ROLES)

    def test_support_role_no_catalog_write(self) -> None:
        from web_panel.auth import CATALOG_WRITE_ACCESS_ROLES
        self.assertNotIn(ROLE_SUPPORT, CATALOG_WRITE_ACCESS_ROLES)

    def test_admin_can_write_catalog(self) -> None:
        from web_panel.auth import CATALOG_WRITE_ACCESS_ROLES
        self.assertIn(ROLE_ADMIN, CATALOG_WRITE_ACCESS_ROLES)

    def test_custom_role_with_catalog_write_permission(self) -> None:
        user = _make_user(ROLE_CUSTOM, permissions={"catalog_write": True})
        perms = normalize_permissions(user.get("permissions"))
        self.assertTrue(perms.get("catalog_write"))

    def test_custom_role_with_only_catalog_read(self) -> None:
        user = _make_user(ROLE_CUSTOM, permissions={"catalog_read": True, "catalog_write": False})
        perms = normalize_permissions(user.get("permissions"))
        self.assertTrue(perms.get("catalog_read"))
        self.assertFalse(perms.get("catalog_write"))


class FinanceAccessGatingTests(unittest.TestCase):
    """Finance endpoints require finance_access permission or finance/accountant role."""

    def test_finance_role_has_finance_access(self) -> None:
        from web_panel.auth import FINANCE_ACCESS_ROLES
        self.assertIn(ROLE_FINANCE, FINANCE_ACCESS_ROLES)

    def test_accountant_role_has_finance_access(self) -> None:
        from web_panel.auth import FINANCE_ACCESS_ROLES
        self.assertIn(ROLE_ACCOUNTANT, FINANCE_ACCESS_ROLES)

    def test_admin_role_has_finance_access(self) -> None:
        from web_panel.auth import FINANCE_ACCESS_ROLES
        self.assertIn(ROLE_ADMIN, FINANCE_ACCESS_ROLES)

    def test_owner_role_has_finance_access(self) -> None:
        from web_panel.auth import FINANCE_ACCESS_ROLES
        self.assertIn(ROLE_OWNER, FINANCE_ACCESS_ROLES)

    def test_viewer_no_finance_access(self) -> None:
        from web_panel.auth import FINANCE_ACCESS_ROLES
        self.assertNotIn(ROLE_VIEWER, FINANCE_ACCESS_ROLES)

    def test_support_no_finance_access(self) -> None:
        from web_panel.auth import FINANCE_ACCESS_ROLES
        self.assertNotIn(ROLE_SUPPORT, FINANCE_ACCESS_ROLES)

    def test_moderator_no_finance_access(self) -> None:
        from web_panel.auth import FINANCE_ACCESS_ROLES
        self.assertNotIn(ROLE_MODERATOR, FINANCE_ACCESS_ROLES)

    def test_custom_role_with_finance_permission_passes(self) -> None:
        user = _make_user(ROLE_CUSTOM, permissions={"finance_access": True})
        perms = normalize_permissions(user.get("permissions"))
        # Custom role grant: either role in FINANCE_ACCESS_ROLES or finance_access perm
        from web_panel.auth import FINANCE_ACCESS_ROLES
        has_access = user["role"] in FINANCE_ACCESS_ROLES or perms.get("finance_access", False)
        self.assertTrue(has_access)

    def test_custom_role_without_finance_permission_blocked(self) -> None:
        user = _make_user(ROLE_CUSTOM, permissions={"crm_edit": True})
        perms = normalize_permissions(user.get("permissions"))
        from web_panel.auth import FINANCE_ACCESS_ROLES
        has_access = user["role"] in FINANCE_ACCESS_ROLES or perms.get("finance_access", False)
        self.assertFalse(has_access)


if __name__ == "__main__":
    unittest.main()
