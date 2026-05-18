"""
API for CCCategory and CCItem CRUD - used by seller catalog and mirror bot
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List
from pydantic import BaseModel
from decimal import Decimal

from web_panel.database import get_db
from web_panel.auth import require_catalog_read_access, require_catalog_write_access
from shared.database.models import CCCategory, CCItem

router = APIRouter(prefix="/api/cc-catalog", tags=["cc-catalog"])


class CCCategoryCreate(BaseModel):
    code: str
    name: str
    position: int = 0
    is_active: bool = True


class CCCategoryUpdate(BaseModel):
    name: Optional[str] = None
    position: Optional[int] = None
    is_active: Optional[bool] = None


class CCItemCreate(BaseModel):
    cc_code: str
    name: str
    category_code: str
    price: float
    description: Optional[str] = None
    is_active: bool = True
    position: int = 0


class CCItemUpdate(BaseModel):
    name: Optional[str] = None
    category_code: Optional[str] = None
    price: Optional[float] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    position: Optional[int] = None


@router.get("/categories")
async def list_cc_categories(
    active_only: bool = False,
    db: AsyncSession = Depends(get_db),
    _ = Depends(require_catalog_read_access("cc"))
):
    stmt = select(CCCategory).order_by(CCCategory.position, CCCategory.id)
    if active_only:
        stmt = stmt.where(CCCategory.is_active == True)
    result = await db.execute(stmt)
    cats = result.scalars().all()
    return [{"id": c.id, "code": c.code, "name": c.name, "position": c.position, "is_active": c.is_active} for c in cats]


@router.post("/categories")
async def create_cc_category(
    data: CCCategoryCreate,
    db: AsyncSession = Depends(get_db),
    _ = Depends(require_catalog_write_access("cc"))
):
    existing = await db.execute(select(CCCategory).where(CCCategory.code == data.code))
    if existing.scalar_one_or_none():
        raise HTTPException(400, "Category code exists")
    cat = CCCategory(code=data.code, name=data.name, position=data.position, is_active=data.is_active)
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    return {"id": cat.id, "code": cat.code, "name": cat.name}


@router.put("/categories/{cat_id}")
async def update_cc_category(
    cat_id: int,
    data: CCCategoryUpdate,
    db: AsyncSession = Depends(get_db),
    _ = Depends(require_catalog_write_access("cc"))
):
    result = await db.execute(select(CCCategory).where(CCCategory.id == cat_id))
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(404, "Not found")
    if data.name is not None:
        cat.name = data.name
    if data.position is not None:
        cat.position = data.position
    if data.is_active is not None:
        cat.is_active = data.is_active
    await db.commit()
    return {"ok": True}


@router.delete("/categories/{cat_id}")
async def delete_cc_category(
    cat_id: int,
    db: AsyncSession = Depends(get_db),
    _ = Depends(require_catalog_write_access("cc"))
):
    result = await db.execute(select(CCCategory).where(CCCategory.id == cat_id))
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(404, "Not found")
    await db.delete(cat)
    await db.commit()
    return {"ok": True}


@router.get("/items")
async def list_cc_items(
    category_code: Optional[str] = None,
    active_only: bool = False,
    db: AsyncSession = Depends(get_db),
    _ = Depends(require_catalog_read_access("cc"))
):
    stmt = select(CCItem).order_by(CCItem.category_code, CCItem.position, CCItem.id)
    if category_code:
        stmt = stmt.where(CCItem.category_code == category_code)
    if active_only:
        stmt = stmt.where(CCItem.is_active == True)
    result = await db.execute(stmt)
    items = result.scalars().all()
    return [{"id": i.id, "cc_code": i.cc_code, "name": i.name, "category_code": i.category_code, "price": float(i.price), "description": i.description, "is_active": i.is_active, "position": i.position} for i in items]


@router.post("/items")
async def create_cc_item(
    data: CCItemCreate,
    db: AsyncSession = Depends(get_db),
    _ = Depends(require_catalog_write_access("cc"))
):
    existing = await db.execute(select(CCItem).where(CCItem.cc_code == data.cc_code))
    if existing.scalar_one_or_none():
        raise HTTPException(400, "CC code exists")
    item = CCItem(cc_code=data.cc_code, name=data.name, category_code=data.category_code, price=Decimal(str(data.price)), description=data.description, is_active=data.is_active, position=data.position)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return {"id": item.id, "cc_code": item.cc_code, "name": item.name}


@router.put("/items/{item_id}")
async def update_cc_item(
    item_id: int,
    data: CCItemUpdate,
    db: AsyncSession = Depends(get_db),
    _ = Depends(require_catalog_write_access("cc"))
):
    result = await db.execute(select(CCItem).where(CCItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(404, "Not found")
    if data.name is not None:
        item.name = data.name
    if data.category_code is not None:
        item.category_code = data.category_code
    if data.price is not None:
        item.price = Decimal(str(data.price))
    if data.description is not None:
        item.description = data.description
    if data.is_active is not None:
        item.is_active = data.is_active
    if data.position is not None:
        item.position = data.position
    await db.commit()
    return {"ok": True}


@router.delete("/items/{item_id}")
async def delete_cc_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    _ = Depends(require_catalog_write_access("cc"))
):
    result = await db.execute(select(CCItem).where(CCItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(404, "Not found")
    await db.delete(item)
    await db.commit()
    return {"ok": True}
