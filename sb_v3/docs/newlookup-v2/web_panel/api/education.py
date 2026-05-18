from __future__ import annotations

"""
API for Education section — categories, subscriptions, manuals
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List
from pydantic import BaseModel
from decimal import Decimal
from datetime import datetime

from web_panel.database import get_db
from web_panel.auth import require_catalog_read_access, require_catalog_write_access
from shared.database.models import EducationCategory, EducationSubscription, EducationManual

router = APIRouter(prefix="/api/education", tags=["education"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class CategoryCreate(BaseModel):
    code: str
    name: str
    item_type: str = "subscription"  # subscription | manual
    position: int = 0
    is_active: bool = True


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    item_type: Optional[str] = None
    position: Optional[int] = None
    is_active: Optional[bool] = None


class SubscriptionCreate(BaseModel):
    code: str
    name: str
    category_code: str
    price: float
    duration_days: int
    description: Optional[str] = None
    is_active: bool = True
    position: int = 0


class SubscriptionUpdate(BaseModel):
    name: Optional[str] = None
    category_code: Optional[str] = None
    price: Optional[float] = None
    duration_days: Optional[int] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    position: Optional[int] = None


class ManualCreate(BaseModel):
    code: str
    name: str
    category_code: str
    price: float
    file_path: str
    file_name: str
    file_type: str = "pdf"
    description: Optional[str] = None
    is_available: bool = True
    position: int = 0


class ManualUpdate(BaseModel):
    name: Optional[str] = None
    category_code: Optional[str] = None
    price: Optional[float] = None
    file_path: Optional[str] = None
    file_name: Optional[str] = None
    file_type: Optional[str] = None
    description: Optional[str] = None
    is_available: Optional[bool] = None
    position: Optional[int] = None


# ── Categories ────────────────────────────────────────────────────────────────

@router.get("/categories")
async def list_categories(
    item_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_catalog_read_access("education"))
):
    stmt = select(EducationCategory).order_by(EducationCategory.position, EducationCategory.id)
    if item_type:
        stmt = stmt.where(EducationCategory.item_type == item_type)
    result = await db.execute(stmt)
    cats = result.scalars().all()
    return [
        {"id": c.id, "code": c.code, "name": c.name, "item_type": c.item_type,
         "position": c.position, "is_active": c.is_active}
        for c in cats
    ]


@router.post("/categories")
async def create_category(
    data: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_catalog_write_access("education"))
):
    existing = await db.execute(select(EducationCategory).where(EducationCategory.code == data.code))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Code already exists")
    cat = EducationCategory(**data.model_dump())
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    return {"id": cat.id, "code": cat.code}


@router.put("/categories/{cat_id}")
async def update_category(
    cat_id: int, data: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_catalog_write_access("education"))
):
    result = await db.execute(select(EducationCategory).where(EducationCategory.id == cat_id))
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=404, detail="Not found")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(cat, k, v)
    await db.commit()
    return {"ok": True}


@router.delete("/categories/{cat_id}")
async def delete_category(
    cat_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_catalog_write_access("education"))
):
    result = await db.execute(select(EducationCategory).where(EducationCategory.id == cat_id))
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=404, detail="Not found")
    await db.delete(cat)
    await db.commit()
    return {"ok": True}


# ── Subscriptions ─────────────────────────────────────────────────────────────

@router.get("/subscriptions")
async def list_subscriptions(
    category_code: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_catalog_read_access("education"))
):
    stmt = select(EducationSubscription).order_by(EducationSubscription.category_code, EducationSubscription.position)
    if category_code:
        stmt = stmt.where(EducationSubscription.category_code == category_code)
    result = await db.execute(stmt)
    subs = result.scalars().all()
    return [
        {"id": s.id, "code": s.code, "name": s.name, "category_code": s.category_code,
         "price": float(s.price), "duration_days": s.duration_days,
         "description": s.description, "is_active": s.is_active, "position": s.position}
        for s in subs
    ]


@router.post("/subscriptions")
async def create_subscription(
    data: SubscriptionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_catalog_write_access("education"))
):
    existing = await db.execute(select(EducationSubscription).where(EducationSubscription.code == data.code))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Code already exists")
    sub = EducationSubscription(**data.model_dump())
    db.add(sub)
    await db.commit()
    await db.refresh(sub)
    return {"id": sub.id, "code": sub.code}


@router.put("/subscriptions/{sub_id}")
async def update_subscription(
    sub_id: int, data: SubscriptionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_catalog_write_access("education"))
):
    result = await db.execute(select(EducationSubscription).where(EducationSubscription.id == sub_id))
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Not found")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(sub, k, v)
    await db.commit()
    return {"ok": True}


@router.delete("/subscriptions/{sub_id}")
async def delete_subscription(
    sub_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_catalog_write_access("education"))
):
    result = await db.execute(select(EducationSubscription).where(EducationSubscription.id == sub_id))
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Not found")
    await db.delete(sub)
    await db.commit()
    return {"ok": True}


# ── Manuals ───────────────────────────────────────────────────────────────────

@router.get("/manuals")
async def list_manuals(
    category_code: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_catalog_read_access("education"))
):
    stmt = select(EducationManual).order_by(EducationManual.category_code, EducationManual.position)
    if category_code:
        stmt = stmt.where(EducationManual.category_code == category_code)
    result = await db.execute(stmt)
    manuals = result.scalars().all()
    return [
        {"id": m.id, "code": m.code, "name": m.name, "category_code": m.category_code,
         "price": float(m.price), "file_name": m.file_name, "file_type": m.file_type,
         "description": m.description, "is_available": m.is_available, "position": m.position}
        for m in manuals
    ]


@router.post("/manuals")
async def create_manual(
    data: ManualCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_catalog_write_access("education"))
):
    existing = await db.execute(select(EducationManual).where(EducationManual.code == data.code))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Code already exists")
    manual = EducationManual(**data.model_dump())
    db.add(manual)
    await db.commit()
    await db.refresh(manual)
    return {"id": manual.id, "code": manual.code}


@router.put("/manuals/{manual_id}")
async def update_manual(
    manual_id: int, data: ManualUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_catalog_write_access("education"))
):
    result = await db.execute(select(EducationManual).where(EducationManual.id == manual_id))
    manual = result.scalar_one_or_none()
    if not manual:
        raise HTTPException(status_code=404, detail="Not found")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(manual, k, v)
    await db.commit()
    return {"ok": True}


@router.delete("/manuals/{manual_id}")
async def delete_manual(
    manual_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_catalog_write_access("education"))
):
    result = await db.execute(select(EducationManual).where(EducationManual.id == manual_id))
    manual = result.scalar_one_or_none()
    if not manual:
        raise HTTPException(status_code=404, detail="Not found")
    await db.delete(manual)
    await db.commit()
    return {"ok": True}


@router.post("/seed")
async def seed_education(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_catalog_write_access("education"))
):
    """Создать пример категорий и товаров если Education пустой."""
    existing = await db.execute(select(EducationCategory))
    if existing.scalars().first():
        return {"ok": True, "message": "Already seeded"}

    sub_cat = EducationCategory(code="credit_basics", name="Credit Basics", item_type="subscription", position=0)
    man_cat = EducationCategory(code="guides", name="Guides & How-To", item_type="manual", position=0)
    db.add_all([sub_cat, man_cat])
    await db.flush()

    subs = [
        EducationSubscription(code="credit_basics_30", name="Credit Basics — 30 days", category_code="credit_basics", price=Decimal("29.99"), duration_days=30, description="Access to all Credit Basics materials for 30 days.", position=0),
        EducationSubscription(code="credit_basics_90", name="Credit Basics — 90 days", category_code="credit_basics", price=Decimal("79.99"), duration_days=90, description="Access to all Credit Basics materials for 90 days.", position=1),
    ]
    db.add_all(subs)
    await db.commit()
    return {"ok": True, "message": "Seeded default education content"}
