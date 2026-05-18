"""API для кастомных ролей администраторов"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List
from pydantic import BaseModel

from web_panel.database import get_db
from web_panel.auth import require_role, get_current_user
from shared.database.models import AdminRole, Admin

router = APIRouter(prefix="/api/admin-roles", tags=["admin-roles"])

DEFAULT_PERMISSIONS = ["users", "orders", "workers", "sellers", "marketers", "broadcasts", "analytics"]


class AdminRoleCreate(BaseModel):
    name: str
    display_name: str
    permissions: dict  # {"users": True, "orders": True, ...}


class AdminRoleUpdate(BaseModel):
    display_name: Optional[str] = None
    permissions: Optional[dict] = None


@router.get("")
async def list_roles(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("owner")),
):
    """Список ролей"""
    result = await db.execute(select(AdminRole).order_by(AdminRole.id))
    roles = result.scalars().all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "display_name": r.display_name,
            "permissions": r.permissions or {},
            "is_system": r.is_system,
        }
        for r in roles
    ]


@router.post("")
async def create_role(
    body: AdminRoleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("owner")),
):
    """Создать роль"""
    exists = await db.execute(select(AdminRole).where(AdminRole.name == body.name))
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Role with this name exists")
    role = AdminRole(
        name=body.name,
        display_name=body.display_name,
        permissions=body.permissions,
        is_system=False,
    )
    db.add(role)
    await db.commit()
    await db.refresh(role)
    return {"id": role.id, "name": role.name}


@router.patch("/{role_id}")
async def update_role(
    role_id: int,
    body: AdminRoleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("owner")),
):
    """Обновить роль"""
    result = await db.execute(select(AdminRole).where(AdminRole.id == role_id))
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=404, detail="Not found")
    if role.is_system:
        raise HTTPException(status_code=400, detail="Cannot edit system role")
    if body.display_name is not None:
        role.display_name = body.display_name
    if body.permissions is not None:
        role.permissions = body.permissions
    await db.commit()
    return {"ok": True}


@router.delete("/{role_id}")
async def delete_role(
    role_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("owner")),
):
    """Удалить роль"""
    result = await db.execute(select(AdminRole).where(AdminRole.id == role_id))
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=404, detail="Not found")
    if role.is_system:
        raise HTTPException(status_code=400, detail="Cannot delete system role")
    used = await db.execute(select(Admin).where(Admin.role_id == role_id))
    if used.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Role is in use")
    await db.delete(role)
    await db.commit()
    return {"ok": True}
