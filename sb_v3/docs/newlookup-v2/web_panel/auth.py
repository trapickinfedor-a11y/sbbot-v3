from __future__ import annotations

"""
Авторизация для веб-панели
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shared.database.models import Admin
from shared.services.admin_catalog_access import normalize_uploader_catalog_codes
from web_panel.database import get_db
from web_panel.config import web_panel_config

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)

ROLE_VIEWER = "viewer"
ROLE_SUPPORT = "support"
ROLE_MODERATOR = "moderator"
ROLE_FINANCE = "finance"
ROLE_ACCOUNTANT = "accountant"
ROLE_UPLOADER = "uploader"
ROLE_ADMIN = "admin"
ROLE_OWNER = "owner"
ROLE_SUPER_ADMIN = "super_admin"
ROLE_CUSTOM = "custom"

ACTIVE_PAGE_PATHS = {
    "dashboard": "/dashboard",
    "finance": "/finance",
    "analytics": "/analytics",
    "reports": "/reports",
    "users": "/users",
    "bots": "/bots",
    "deposits": "/deposits",
    "workers": "/workers",
    "worker_crm": "/worker-crm",
    "sellers": "/sellers",
    "seller_moderation": "/seller-moderation",
    "seller_crm": "/seller-crm",
    "seller-deposits": "/seller-deposits",
    "marketers": "/marketers",
    "withdrawals": "/withdrawals",
    "orders": "/orders",
    "disputes": "/disputes",
    "complaints": "/complaints",
    "support": "/support",
    "products": "/products",
    "banks": "/banks",
    "brute_bank": "/brute-bank",
    "accounts": "/accounts",
    "esim": "/esim",
    "cc": "/cc",
    "education": "/education",
    "another-services": "/another-services",
    "automation": "/automation",
    "service-prices": "/service-prices",
    "pricing-config": "/pricing-config",
    "service-order-config": "/service-order-config",
    "bulk-discounts": "/bulk-discounts",
    "categories": "/categories",
    "broadcasts": "/broadcasts",
    "referrals": "/referrals",
    "checks": "/checks",
    "documents": "/documents",
    "instructions": "/instructions",
    "knowledge-base": "/knowledge-base",
    "admin-structure": "/admin-structure",
    "admins": "/admins",
    "admin_roles": "/admin-roles",
    "audit": "/audit",
    "ops": "/ops",
}

CATALOG_PAGE_KEYS = {
    "products",
    "categories",
    "seller_moderation",
    "banks",
    "brute_bank",
    "accounts",
    "esim",
    "cc",
    "education",
    "another-services",
    "documents",
}

ROLE_PAGE_ACCESS = {
    ROLE_VIEWER: {
        "products",
        "categories",
        "banks",
        "brute_bank",
        "accounts",
        "esim",
        "cc",
        "education",
        "another-services",
        "documents",
        "orders",
        "disputes",
        "complaints",
        "support",
    },
    ROLE_SUPPORT: {
        "users",
        "support",
        "service-prices",
        "orders",
        "seller_crm",
    },
    ROLE_MODERATOR: {
        "users",
        "orders",
        "complaints",
        "seller_moderation",
        "sellers",
        "service-prices",
    },
    ROLE_FINANCE: {
        "dashboard",
        "finance",
        "analytics",
        "reports",
        "ops",
        "automation",
        "users",
        "deposits",
        "sellers",
        "seller_crm",
        "seller-deposits",
        "marketers",
        "withdrawals",
        "disputes",
    },
    ROLE_ACCOUNTANT: {
        "dashboard",
        "finance",
        "analytics",
        "reports",
        "users",
        "deposits",
        "sellers",
        "seller_crm",
        "seller-deposits",
        "marketers",
        "withdrawals",
        "disputes",
    },
    ROLE_UPLOADER: set(CATALOG_PAGE_KEYS),
    ROLE_ADMIN: set(ACTIVE_PAGE_PATHS.keys()),
    ROLE_OWNER: set(ACTIVE_PAGE_PATHS.keys()),
    ROLE_SUPER_ADMIN: set(ACTIVE_PAGE_PATHS.keys()),
}

ROLE_DEFAULT_PAGES = {
    ROLE_VIEWER: "products",
    ROLE_SUPPORT: "users",
    ROLE_MODERATOR: "users",
    ROLE_FINANCE: "users",
    ROLE_ACCOUNTANT: "deposits",
    ROLE_UPLOADER: "products",
    ROLE_ADMIN: "dashboard",
    ROLE_OWNER: "dashboard",
    ROLE_SUPER_ADMIN: "dashboard",
}

SUPPORT_CHAT_ACCESS_ROLES = {
    ROLE_SUPPORT,
    ROLE_ADMIN,
    ROLE_OWNER,
    ROLE_SUPER_ADMIN,
}

COMPLAINTS_ACCESS_ROLES = {
    ROLE_MODERATOR,
    ROLE_ADMIN,
    ROLE_OWNER,
    ROLE_SUPER_ADMIN,
}

ORDERS_ACCESS_ROLES = {
    ROLE_SUPPORT,
    ROLE_MODERATOR,
    ROLE_ADMIN,
    ROLE_OWNER,
    ROLE_SUPER_ADMIN,
}

SELLER_MODERATION_ACCESS_ROLES = {
    ROLE_MODERATOR,
    ROLE_ADMIN,
    ROLE_OWNER,
    ROLE_SUPER_ADMIN,
}

FINANCE_ACCESS_ROLES = {
    ROLE_FINANCE,
    ROLE_ACCOUNTANT,
    ROLE_ADMIN,
    ROLE_OWNER,
    ROLE_SUPER_ADMIN,
}

SELLER_READ_ACCESS_ROLES = FINANCE_ACCESS_ROLES | SELLER_MODERATION_ACCESS_ROLES | {ROLE_SUPPORT}

CATALOG_READ_ACCESS_ROLES = {
    ROLE_VIEWER,
    ROLE_UPLOADER,
    ROLE_ADMIN,
    ROLE_OWNER,
    ROLE_SUPER_ADMIN,
}

CATALOG_WRITE_ACCESS_ROLES = {
    ROLE_UPLOADER,
    ROLE_ADMIN,
    ROLE_OWNER,
    ROLE_SUPER_ADMIN,
}

ADMIN_MANAGEMENT_ACCESS_ROLES = {
    ROLE_OWNER,
    ROLE_SUPER_ADMIN,
}

AUDIT_ACCESS_ROLES = {
    ROLE_ADMIN,
    ROLE_OWNER,
    ROLE_SUPER_ADMIN,
}


def _role_aliases(role: Optional[str]) -> set[str]:
    raw = role or ""
    aliases = {raw}
    if raw == ROLE_OWNER:
        aliases.add(ROLE_SUPER_ADMIN)
    elif raw == ROLE_SUPER_ADMIN:
        aliases.add(ROLE_OWNER)
    elif raw == ROLE_FINANCE:
        aliases.add(ROLE_ACCOUNTANT)
    elif raw == ROLE_ACCOUNTANT:
        aliases.add(ROLE_FINANCE)
    return aliases


def has_any_role(current_user: dict, *roles: str) -> bool:
    return bool(_role_aliases(current_user.get("role", "")) & set(roles))


def can_view_crm(current_user: dict) -> bool:
    return has_any_role(
        current_user,
        ROLE_SUPPORT,
        ROLE_FINANCE,
        ROLE_ACCOUNTANT,
        ROLE_MODERATOR,
        ROLE_ADMIN,
        ROLE_OWNER,
        ROLE_SUPER_ADMIN,
    ) or bool(_current_allowed_pages(current_user) & {"users", "orders", "support", "sellers", "seller_crm", "worker_crm"})


def can_edit_crm(current_user: dict) -> bool:
    return has_any_role(
        current_user,
        ROLE_MODERATOR,
        ROLE_ADMIN,
        ROLE_OWNER,
        ROLE_SUPER_ADMIN,
    ) or normalize_permissions(current_user.get("permissions")).get("crm_edit", False)


def can_ban_users(current_user: dict) -> bool:
    return has_any_role(
        current_user,
        ROLE_MODERATOR,
        ROLE_ADMIN,
        ROLE_OWNER,
        ROLE_SUPER_ADMIN,
    ) or normalize_permissions(current_user.get("permissions")).get("ban_users", False)


def can_view_finances(current_user: dict) -> bool:
    permissions = normalize_permissions(current_user.get("permissions"))
    return has_any_role(
        current_user,
        ROLE_FINANCE,
        ROLE_ACCOUNTANT,
        ROLE_ADMIN,
        ROLE_OWNER,
        ROLE_SUPER_ADMIN,
    ) or permissions.get("finance_access", False)


def can_manage_staff(current_user: dict) -> bool:
    return has_any_role(current_user, ROLE_OWNER, ROLE_SUPER_ADMIN)


def normalize_allowed_catalogs(value: Optional[list[str]]) -> list[str]:
    return normalize_uploader_catalog_codes(value)


def normalize_permissions(value: Optional[dict]) -> dict[str, bool]:
    if not isinstance(value, dict):
        return {}
    normalized: dict[str, bool] = {}
    for key, enabled in value.items():
        if not key:
            continue
        normalized[str(key).strip().lower().replace("-", "_")] = bool(enabled)
    return normalized


def _catalogs_set(value: Optional[list[str]]) -> set[str]:
    return set(normalize_allowed_catalogs(value))


def _permission_variants(key: str) -> set[str]:
    raw = (key or "").strip().lower()
    underscored = raw.replace("-", "_")
    hyphenated = underscored.replace("_", "-")
    return {raw, underscored, hyphenated}


def _resolve_allowed_pages(
    role: Optional[str],
    allowed_catalogs: Optional[list[str]] = None,
    permissions: Optional[dict] = None,
) -> set[str]:
    pages = set(ROLE_PAGE_ACCESS.get(role or "", set()))
    if role == ROLE_UPLOADER:
        pages &= _catalogs_set(allowed_catalogs)
    normalized_permissions = normalize_permissions(permissions)
    if normalized_permissions.get("finance_access", False):
        pages |= {"finance", "disputes", "deposits", "seller_crm", "seller-deposits", "marketers", "sellers", "withdrawals"}
    pages |= {
        page_key
        for page_key in ACTIVE_PAGE_PATHS
        if any(normalized_permissions.get(variant, False) for variant in _permission_variants(page_key))
    }
    return pages


def _current_allowed_pages(current_user: dict) -> set[str]:
    return get_allowed_pages_for_role(
        current_user.get("role"),
        current_user.get("allowed_catalogs"),
        current_user.get("permissions"),
    )


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверка пароля"""
    # bcrypt не поддерживает пароли длиннее 72 байт
    if len(plain_password.encode('utf-8')) > 72:
        plain_password = plain_password[:72]
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Хеширование пароля"""
    # bcrypt не поддерживает пароли длиннее 72 байт
    if len(password.encode('utf-8')) > 72:
        password = password[:72]
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Создание JWT токена"""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=web_panel_config.access_token_expire_minutes))
    to_encode.update({"exp": expire, "iat": now})
    return jwt.encode(
        to_encode,
        web_panel_config.secret_key,
        algorithm=web_panel_config.algorithm,
    )


def decode_token(token: str) -> dict:
    """Декодирование JWT токена"""
    try:
        payload = jwt.decode(
            token,
            web_panel_config.secret_key,
            algorithms=[web_panel_config.algorithm]
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )


async def _hydrate_admin_from_token_payload(db: AsyncSession, payload: dict) -> dict:
    username: str = payload.get("sub")
    admin_id = payload.get("admin_id")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )
    stmt = (
        select(Admin)
        .options(selectinload(Admin.role_obj))
        .options(selectinload(Admin.uploader_catalog_permissions))
    )
    if admin_id is not None:
        stmt = stmt.where(Admin.id == admin_id)
    else:
        stmt = stmt.where(Admin.username == username)
    admin = await db.scalar(stmt)
    if not admin or not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )
    return {
        "username": admin.username,
        "role": admin.role,
        "role_id": getattr(admin, "role_id", None),
        "role_name": getattr(getattr(admin, "role_obj", None), "display_name", None),
        "admin_id": admin.id,
        "allowed_catalogs": normalize_allowed_catalogs(getattr(admin, "allowed_catalogs", None)),
        "permissions": normalize_permissions(getattr(getattr(admin, "role_obj", None), "permissions", None)),
    }


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Получение текущего пользователя из токена"""
    token: Optional[str] = credentials.credentials if credentials else None
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )
    payload = decode_token(token)
    
    return await _hydrate_admin_from_token_payload(db, payload)


async def get_request_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Получение текущего пользователя из bearer token или auth cookie."""
    token: Optional[str] = credentials.credentials if credentials else None
    if not token:
        auth_header = request.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            token = auth_header.split(" ", 1)[1].strip()
    if not token:
        token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )
    payload = decode_token(token)

    return await _hydrate_admin_from_token_payload(db, payload)


def require_role(*allowed_roles: str):
    """Dependency: require current user to have one of the allowed roles"""
    def dep(current_user: dict = Depends(get_request_user)):
        role = current_user.get("role", "")
        if not (_role_aliases(role) & set(allowed_roles)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return current_user
    return dep


def _has_page_or_permission(current_user: dict, page: str, fallback_roles: set[str]) -> bool:
    role = current_user.get("role", "")
    if _role_aliases(role) & set(fallback_roles):
        return True
    allowed_pages = get_allowed_pages_for_role(
        role,
        current_user.get("allowed_catalogs"),
        current_user.get("permissions"),
    )
    if page in allowed_pages:
        return True
    return False


def require_support_access():
    """Support chat access."""
    def dep(current_user: dict = Depends(get_request_user)):
        if not _has_page_or_permission(current_user, "support", SUPPORT_CHAT_ACCESS_ROLES):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return current_user
    return dep


def require_complaints_access():
    """Complaints and reports workflow."""
    def dep(current_user: dict = Depends(get_request_user)):
        if not _has_page_or_permission(current_user, "complaints", COMPLAINTS_ACCESS_ROLES):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return current_user
    return dep


def require_orders_access():
    """Orders workflow access."""
    def dep(current_user: dict = Depends(get_request_user)):
        if not _has_page_or_permission(current_user, "orders", ORDERS_ACCESS_ROLES):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return current_user
    return dep


def require_seller_moderation_access():
    """Seller upload moderation access."""
    def dep(current_user: dict = Depends(get_request_user)):
        if not _has_page_or_permission(current_user, "seller_moderation", SELLER_MODERATION_ACCESS_ROLES):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return current_user
    return dep


def require_finance_access():
    """Financial routes: finance, admin, owner."""
    def dep(current_user: dict = Depends(get_request_user)):
        if has_any_role(current_user, *FINANCE_ACCESS_ROLES) or normalize_permissions(current_user.get("permissions")).get("finance_access", False):
            return current_user
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    return dep


def require_seller_read_access():
    """Seller list/detail access for finance and moderation staff."""
    def dep(current_user: dict = Depends(get_request_user)):
        if (
            _has_page_or_permission(current_user, "sellers", SELLER_READ_ACCESS_ROLES)
            or _has_page_or_permission(current_user, "seller_crm", SELLER_READ_ACCESS_ROLES)
            or _has_page_or_permission(current_user, "disputes", SELLER_READ_ACCESS_ROLES)
        ):
            return current_user
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    return dep


def require_audit_access():
    """Audit view access for operational staff."""
    def dep(current_user: dict = Depends(get_request_user)):
        if has_any_role(current_user, *AUDIT_ACCESS_ROLES) or "audit" in _current_allowed_pages(current_user):
            return current_user
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    return dep


def require_catalog_write_access(catalog: Optional[str] = None):
    """Catalog management access."""
    return require_catalog_access(catalog=catalog, write=True)


def require_catalog_read_access(catalog: Optional[str] = None):
    """Read-only catalog access."""
    return require_catalog_access(catalog=catalog, write=False)


def require_catalog_access(catalog: Optional[str] = None, write: bool = False):
    allowed_roles = CATALOG_WRITE_ACCESS_ROLES if write else CATALOG_READ_ACCESS_ROLES
    perm_key = "catalog_write" if write else "catalog_read"

    def dep(current_user: dict = Depends(get_request_user)):
        role = current_user.get("role", "")
        # Custom-role admins: check their permissions dict instead of role name
        if role == ROLE_CUSTOM:
            perms = normalize_permissions(current_user.get("permissions"))
            if not (perms.get(perm_key) or perms.get("finance_access") or
                    (not write and _has_page_or_permission(current_user, "catalog", CATALOG_READ_ACCESS_ROLES))):
                # Also allow if they have any catalog page in allowed_pages
                if catalog and catalog not in _current_allowed_pages(current_user):
                    # check generic catalog access via pages
                    pass
                # Fall through to role check only if no catalog permission at all
                if not any(perms.get(p) for p in ("catalog_read", "catalog_write", "finance_access")):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Insufficient permissions"
                    )
        elif role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        if role == ROLE_UPLOADER and catalog:
            allowed_catalogs = _catalogs_set(current_user.get("allowed_catalogs"))
            if catalog not in allowed_catalogs:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"No access to catalog '{catalog}'"
                )
        return current_user

    return dep


def require_admin_management_access():
    """Restricted management actions for admin roles only."""
    def dep(current_user: dict = Depends(get_request_user)):
        if has_any_role(current_user, *ADMIN_MANAGEMENT_ACCESS_ROLES) or bool(
            _current_allowed_pages(current_user) & {"admins", "admin_roles"}
        ):
            return current_user
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    return dep


def require_page_access(page: str):
    """Template/page access using request auth context."""
    def dep(current_user: dict = Depends(get_request_user)):
        if can_access_page(
            current_user.get("role", ""),
            page,
            current_user.get("allowed_catalogs"),
            current_user.get("permissions"),
        ):
            return current_user
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    return dep


def get_allowed_pages_for_role(
    role: Optional[str],
    allowed_catalogs: Optional[list[str]] = None,
    permissions: Optional[dict] = None,
) -> set[str]:
    return _resolve_allowed_pages(role, allowed_catalogs, permissions)


def can_access_page(
    role: Optional[str],
    page: str,
    allowed_catalogs: Optional[list[str]] = None,
    permissions: Optional[dict] = None,
) -> bool:
    return page in get_allowed_pages_for_role(role, allowed_catalogs, permissions)


def get_default_page(
    role: Optional[str],
    allowed_catalogs: Optional[list[str]] = None,
    permissions: Optional[dict] = None,
) -> str:
    allowed_pages = get_allowed_pages_for_role(role, allowed_catalogs, permissions)
    if role == ROLE_UPLOADER and allowed_pages:
        page = sorted(allowed_pages)[0]
        return ACTIVE_PAGE_PATHS.get(page, "/dashboard")
    page = ROLE_DEFAULT_PAGES.get(role or "", "dashboard")
    if allowed_pages and page not in allowed_pages:
        page = sorted(allowed_pages)[0]
    return ACTIVE_PAGE_PATHS.get(page, "/dashboard")


def build_access_profile(
    role: Optional[str],
    allowed_catalogs: Optional[list[str]] = None,
    permissions: Optional[dict] = None,
) -> dict:
    normalized_catalogs = normalize_allowed_catalogs(allowed_catalogs)
    normalized_permissions = normalize_permissions(permissions)
    allowed_pages = sorted(get_allowed_pages_for_role(role, normalized_catalogs, normalized_permissions))
    default_page = ROLE_DEFAULT_PAGES.get(role or "", "dashboard")
    if role == ROLE_UPLOADER and allowed_pages:
        default_page = allowed_pages[0]
    elif allowed_pages and default_page not in allowed_pages:
        default_page = allowed_pages[0]
    return {
        "allowed_pages": allowed_pages,
        "allowed_paths": [ACTIVE_PAGE_PATHS[page] for page in allowed_pages if page in ACTIVE_PAGE_PATHS],
        "default_page": default_page,
        "default_path": get_default_page(role, normalized_catalogs, normalized_permissions),
        "allowed_catalogs": normalized_catalogs,
        "permissions": normalized_permissions,
        "capabilities": {
            "catalog_read": role in CATALOG_READ_ACCESS_ROLES,
            "catalog_write": role in CATALOG_WRITE_ACCESS_ROLES,
            "catalog_scopes": normalized_catalogs,
            "support_chat": role in SUPPORT_CHAT_ACCESS_ROLES or "support" in allowed_pages,
            "complaints": role in COMPLAINTS_ACCESS_ROLES or "complaints" in allowed_pages,
            "orders": role in ORDERS_ACCESS_ROLES or "orders" in allowed_pages,
            "seller_moderation": role in SELLER_MODERATION_ACCESS_ROLES or "seller_moderation" in allowed_pages,
            "finance": can_view_finances({"role": role, "permissions": normalized_permissions}),
            "audit": role in AUDIT_ACCESS_ROLES or normalized_permissions.get("audit", False),
            "admin_management": role in ADMIN_MANAGEMENT_ACCESS_ROLES or normalized_permissions.get("admins", False),
            "crm_view": can_view_crm({"role": role, "permissions": normalized_permissions}),
            "crm_edit": can_edit_crm({"role": role, "permissions": normalized_permissions}),
            "ban_users": can_ban_users({"role": role, "permissions": normalized_permissions}),
        },
    }



