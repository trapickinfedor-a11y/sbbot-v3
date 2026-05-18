from __future__ import annotations

from typing import Iterable, Sequence

from shared.database.models import Admin, UploaderCatalogPermission

VALID_UPLOADER_CATALOG_CODES = (
    "products",
    "banks",
    "brute_bank",
    "accounts",
    "esim",
    "cc",
    "education",
    "another-services",
)


def normalize_uploader_catalog_codes(value: Iterable[str] | None) -> list[str]:
    seen: set[str] = set()
    normalized: list[str] = []
    for item in value or []:
        if not item:
            continue
        catalog = str(item).strip()
        if catalog in VALID_UPLOADER_CATALOG_CODES and catalog not in seen:
            seen.add(catalog)
            normalized.append(catalog)
    return normalized


def get_admin_allowed_catalogs(admin: Admin | None) -> list[str]:
    if not admin:
        return []
    rel = getattr(admin, "uploader_catalog_permissions", None) or []
    if rel:
        return normalize_uploader_catalog_codes(row.catalog_code for row in rel)
    return normalize_uploader_catalog_codes(getattr(admin, "allowed_catalogs", None))


def sync_admin_allowed_catalogs(admin: Admin, catalog_codes: Sequence[str] | None) -> list[str]:
    normalized = normalize_uploader_catalog_codes(catalog_codes)
    admin.allowed_catalogs = normalized or None
    current = {
        row.catalog_code: row
        for row in (getattr(admin, "uploader_catalog_permissions", None) or [])
    }
    next_codes = set(normalized)

    for code, row in list(current.items()):
        if code not in next_codes:
            admin.uploader_catalog_permissions.remove(row)

    for code in normalized:
        if code not in current:
            admin.uploader_catalog_permissions.append(
                UploaderCatalogPermission(catalog_code=code)
            )

    return normalized
