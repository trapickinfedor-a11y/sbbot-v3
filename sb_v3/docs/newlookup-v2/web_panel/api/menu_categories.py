from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import MirrorMenuCategory
from shared.services.menu_category_service import MenuCategoryService
from web_panel.auth import require_catalog_read_access, require_catalog_write_access
from web_panel.database import get_db
from web_panel.services.audit_service import log_action

router = APIRouter(prefix="/api/menu-categories", tags=["menu-categories"])


class MenuCategoryCreate(BaseModel):
    code: str
    route_key: str
    count_key: Optional[str] = None
    label_en: str
    label_ru: Optional[str] = None
    label_zh: Optional[str] = None
    label_es: Optional[str] = None
    row_index: int = 0
    position: int = 0
    is_active: bool = True


class MenuCategoryUpdate(BaseModel):
    route_key: Optional[str] = None
    count_key: Optional[str] = None
    label_en: Optional[str] = None
    label_ru: Optional[str] = None
    label_zh: Optional[str] = None
    label_es: Optional[str] = None
    row_index: Optional[int] = None
    position: Optional[int] = None
    is_active: Optional[bool] = None


class MenuCategoryResponse(BaseModel):
    id: int
    code: str
    route_key: str
    count_key: Optional[str]
    label_en: str
    label_ru: Optional[str]
    label_zh: Optional[str]
    label_es: Optional[str]
    row_index: int
    position: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


@router.get("", response_model=List[MenuCategoryResponse])
async def list_menu_categories(
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_catalog_read_access("products")),
):
    return await MenuCategoryService.list_categories(db, active_only=False)


@router.get("/{category_id}", response_model=MenuCategoryResponse)
async def get_menu_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_catalog_read_access("products")),
):
    category = await db.scalar(select(MirrorMenuCategory).where(MirrorMenuCategory.id == category_id))
    if not category:
        raise HTTPException(status_code=404, detail="Menu category not found")
    return category


@router.post("", response_model=MenuCategoryResponse)
async def create_menu_category(
    data: MenuCategoryCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_catalog_write_access("products")),
):
    await MenuCategoryService.ensure_defaults(db)
    existing = await db.scalar(select(MirrorMenuCategory).where(MirrorMenuCategory.code == data.code))
    if existing:
        raise HTTPException(status_code=400, detail="Category code already exists")
    category = MirrorMenuCategory(**data.model_dump())
    db.add(category)
    await db.commit()
    await db.refresh(category)
    await log_action(
        db,
        current_user.get("admin_id"),
        "menu_category_create",
        "menu_category",
        category.id,
        data.model_dump(),
        request.client.host if request.client else None,
    )
    return category


@router.put("/{category_id}", response_model=MenuCategoryResponse)
async def update_menu_category(
    category_id: int,
    data: MenuCategoryUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_catalog_write_access("products")),
):
    category = await db.scalar(select(MirrorMenuCategory).where(MirrorMenuCategory.id == category_id))
    if not category:
        raise HTTPException(status_code=404, detail="Menu category not found")

    old_values = {
        "route_key": category.route_key,
        "count_key": category.count_key,
        "label_en": category.label_en,
        "label_ru": category.label_ru,
        "label_zh": category.label_zh,
        "label_es": category.label_es,
        "row_index": category.row_index,
        "position": category.position,
        "is_active": category.is_active,
    }
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(category, key, value)
    category.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(category)
    await log_action(
        db,
        current_user.get("admin_id"),
        "menu_category_update",
        "menu_category",
        category.id,
        {
            "old": old_values,
            "new": data.model_dump(exclude_unset=True),
        },
        request.client.host if request.client else None,
    )
    return category


@router.post("/{category_id}/toggle")
async def toggle_menu_category(
    category_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_catalog_write_access("products")),
):
    category = await db.scalar(select(MirrorMenuCategory).where(MirrorMenuCategory.id == category_id))
    if not category:
        raise HTTPException(status_code=404, detail="Menu category not found")
    category.is_active = not category.is_active
    category.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await log_action(
        db,
        current_user.get("admin_id"),
        "menu_category_toggle",
        "menu_category",
        category.id,
        {
            "code": category.code,
            "is_active": category.is_active,
        },
        request.client.host if request.client else None,
    )
    return {"ok": True, "is_active": category.is_active}
