"""API для управления админами."""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from typing import Optional, List

from web_panel.auth import require_role, get_current_user, get_password_hash, normalize_allowed_catalogs, pwd_context
from web_panel.database import get_db
from shared.database.models import Admin, AdminRole
from shared.services.admin_catalog_access import get_admin_allowed_catalogs, sync_admin_allowed_catalogs
from web_panel.services.audit_service import log_action

router = APIRouter()

ROLES = ["owner", "super_admin", "admin", "finance", "accountant", "moderator", "support", "uploader", "viewer", "custom"]


class AdminCreate(BaseModel):
    username: str
    password: str
    role: str = "admin"
    role_id: Optional[int] = None
    telegram_id: Optional[int] = None
    allowed_catalogs: List[str] = []

    @field_validator("username")
    @classmethod
    def username_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Username is required")
        return v.strip()

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        # SEC-3: Check password byte length for bcrypt compatibility
        if len(v.encode('utf-8')) > 72:
            raise ValueError("Password cannot exceed 72 bytes (bcrypt limit)")
        return v

    @field_validator("role")
    @classmethod
    def role_valid(cls, v: str) -> str:
        if v not in ROLES:
            raise ValueError(f"Role must be one of: {', '.join(ROLES)}")
        return v


class AdminUpdate(BaseModel):
    password: Optional[str] = None
    role: Optional[str] = None
    role_id: Optional[int] = None
    telegram_id: Optional[int] = None
    allowed_catalogs: Optional[List[str]] = None

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        # SEC-3: Check password byte length for bcrypt compatibility
        if v is not None and len(v.encode('utf-8')) > 72:
            raise ValueError("Password cannot exceed 72 bytes (bcrypt limit)")
        return v

    @field_validator("role")
    @classmethod
    def role_valid(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ROLES:
            raise ValueError(f"Role must be one of: {', '.join(ROLES)}")
        return v


class AdminResponse(BaseModel):
    id: int
    username: str
    role: str
    role_id: Optional[int] = None
    role_name: Optional[str] = None
    telegram_id: Optional[int]
    allowed_catalogs: List[str] = []
    is_active: bool
    created_at: str


@router.get("", response_model=List[AdminResponse])
async def list_admins(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("owner")),
):
    """Список админов"""
    result = await db.execute(
        select(Admin)
        .options(selectinload(Admin.role_obj))
        .options(selectinload(Admin.uploader_catalog_permissions))
        .order_by(Admin.id)
    )
    admins = result.scalars().all()
    return [
        AdminResponse(
            id=a.id,
            username=a.username,
            role=a.role,
            role_id=a.role_id,
            role_name=getattr(a.role_obj, "display_name", None),
            telegram_id=a.telegram_id,
            allowed_catalogs=get_admin_allowed_catalogs(a),
            is_active=a.is_active,
            created_at=a.created_at.isoformat() if a.created_at else "",
        )
        for a in admins
    ]


@router.post("", response_model=AdminResponse)
async def create_admin(
    data: AdminCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("owner")),
):
    """Создать админа"""
    existing = await db.execute(select(Admin).where(Admin.username == data.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already exists")
    role_obj = None
    role_id = None
    role_value = data.role
    if data.role_id is not None:
        role_obj = await db.scalar(select(AdminRole).where(AdminRole.id == data.role_id))
        if not role_obj:
            raise HTTPException(status_code=404, detail="Admin role not found")
        role_id = role_obj.id
        role_value = "custom"
    admin = Admin(
        username=data.username,
        password_hash=get_password_hash(data.password),
        role=role_value,
        role_id=role_id,
        telegram_id=data.telegram_id,
        is_active=True,
    )
    sync_admin_allowed_catalogs(admin, data.allowed_catalogs)
    db.add(admin)
    await db.commit()
    await db.refresh(admin)
    admin_id = current_user.get("admin_id")
    ip_address = request.client.host if request.client else None
    await log_action(
        db,
        admin_id,
        "admin_create",
        "admin",
        admin.id,
        {
            "username": admin.username,
            "role": admin.role,
            "role_id": admin.role_id,
            "allowed_catalogs": get_admin_allowed_catalogs(admin),
        },
        ip_address,
    )
    await db.commit()
    return AdminResponse(
        id=admin.id,
        username=admin.username,
        role=admin.role,
        role_id=admin.role_id,
        role_name=getattr(admin.role_obj, "display_name", None),
        telegram_id=admin.telegram_id,
        allowed_catalogs=get_admin_allowed_catalogs(admin),
        is_active=admin.is_active,
        created_at=admin.created_at.isoformat() if admin.created_at else "",
    )


@router.get("/{admin_id}", response_model=AdminResponse)
async def get_admin(
    admin_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("owner")),
):
    """Получить админа"""
    result = await db.execute(
        select(Admin)
        .options(selectinload(Admin.role_obj))
        .options(selectinload(Admin.uploader_catalog_permissions))
        .where(Admin.id == admin_id)
    )
    admin = result.scalar_one_or_none()
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")
    return AdminResponse(
        id=admin.id,
        username=admin.username,
        role=admin.role,
        role_id=admin.role_id,
        role_name=getattr(admin.role_obj, "display_name", None),
        telegram_id=admin.telegram_id,
        allowed_catalogs=get_admin_allowed_catalogs(admin),
        is_active=admin.is_active,
        created_at=admin.created_at.isoformat() if admin.created_at else "",
    )


@router.put("/{admin_id}", response_model=AdminResponse)
async def update_admin(
    admin_id: int,
    data: AdminUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("owner")),
):
    """Обновить админа"""
    result = await db.execute(
        select(Admin)
        .options(selectinload(Admin.role_obj))
        .options(selectinload(Admin.uploader_catalog_permissions))
        .where(Admin.id == admin_id)
    )
    admin = result.scalar_one_or_none()
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")
    if data.password is not None:
        admin.password_hash = get_password_hash(data.password)
    if data.role is not None or data.role_id is not None:
        next_role_id = None
        next_role = data.role or admin.role
        if data.role_id is not None:
            role_obj = await db.scalar(select(AdminRole).where(AdminRole.id == data.role_id))
            if not role_obj:
                raise HTTPException(status_code=404, detail="Admin role not found")
            next_role_id = role_obj.id
            next_role = "custom"
        admin.role = next_role
        admin.role_id = next_role_id
    if "telegram_id" in data.model_fields_set:
        admin.telegram_id = data.telegram_id
    if data.allowed_catalogs is not None:
        sync_admin_allowed_catalogs(admin, data.allowed_catalogs)
    await db.commit()
    await db.refresh(admin)
    admin_id_val = current_user.get("admin_id")
    ip_address = request.client.host if request.client else None
    await log_action(
        db,
        admin_id_val,
        "admin_update",
        "admin",
        admin.id,
        {
            "username": admin.username,
            "role": admin.role,
            "role_id": admin.role_id,
            "allowed_catalogs": get_admin_allowed_catalogs(admin),
        },
        ip_address,
    )
    await db.commit()
    return AdminResponse(
        id=admin.id,
        username=admin.username,
        role=admin.role,
        role_id=admin.role_id,
        role_name=getattr(admin.role_obj, "display_name", None),
        telegram_id=admin.telegram_id,
        allowed_catalogs=get_admin_allowed_catalogs(admin),
        is_active=admin.is_active,
        created_at=admin.created_at.isoformat() if admin.created_at else "",
    )


@router.post("/{admin_id}/deactivate")
async def deactivate_admin(
    admin_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("owner")),
):
    """Деактивировать админа"""
    if admin_id == current_user.get("admin_id"):
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself")
    result = await db.execute(select(Admin).where(Admin.id == admin_id))
    admin = result.scalar_one_or_none()
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")
    admin.is_active = False
    await db.commit()
    await db.refresh(admin)
    aid = current_user.get("admin_id")
    ip_address = request.client.host if request.client else None
    await log_action(db, aid, "admin_deactivate", "admin", admin.id, {"username": admin.username}, ip_address)
    await db.commit()
    return {"message": "Admin deactivated"}


@router.post("/{admin_id}/activate")
async def activate_admin(
    admin_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("owner")),
):
    """Активировать админа"""
    result = await db.execute(select(Admin).where(Admin.id == admin_id))
    admin = result.scalar_one_or_none()
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")
    admin.is_active = True
    await db.commit()
    await db.refresh(admin)
    aid = current_user.get("admin_id")
    ip_address = request.client.host if request.client else None
    await log_action(db, aid, "admin_activate", "admin", admin.id, {"username": admin.username}, ip_address)
    await db.commit()
    return {"message": "Admin activated"}


# ─── Self-service password change ────────────────────────────────────────────

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def new_password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("New password must be at least 8 characters")
        return v


@router.put("/me/password")
async def change_my_password(
    data: ChangePasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Смена пароля текущим администратором (без привилегий owner)."""
    admin_id = current_user.get("admin_id")
    result = await db.execute(select(Admin).where(Admin.id == admin_id))
    admin = result.scalar_one_or_none()
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")

    # Проверяем текущий пароль
    if not pwd_context.verify(data.current_password, admin.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    # Проверяем что новый пароль не совпадает со старым
    if data.current_password == data.new_password:
        raise HTTPException(status_code=400, detail="New password must differ from current password")

    admin.password_hash = get_password_hash(data.new_password)
    await db.commit()

    ip = request.client.host if request.client else None
    await log_action(db, admin_id, "admin_change_password", "admin", admin_id, {}, ip)
    await db.commit()

    return {"ok": True, "message": "Password changed successfully"}
