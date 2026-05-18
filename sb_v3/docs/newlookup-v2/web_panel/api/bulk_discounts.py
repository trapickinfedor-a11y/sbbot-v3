"""Admin API — bulk discount tiers management."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from shared.services.bulk_discount_service import (
    ensure_defaults,
    get_all_tiers,
    upsert_tier,
    delete_tier,
)
from web_panel.auth import require_page_access
from web_panel.database import get_db
from web_panel.services.audit_service import log_action

router = APIRouter()


class TierCreate(BaseModel):
    category: str = Field(..., description="banks | esim | fullz | cc | accounts | docs")
    min_qty: int = Field(..., ge=1)
    discount_percent: float = Field(..., ge=0, le=100)
    is_active: bool = True


class TierUpdate(BaseModel):
    discount_percent: float = Field(..., ge=0, le=100)
    is_active: bool = True


@router.get("/")
async def list_tiers(
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_page_access("pricing-config")),
):
    await ensure_defaults(db)
    rows = await get_all_tiers(db)
    return [
        {
            "id": r.id,
            "category": r.category,
            "min_qty": r.min_qty,
            "discount_percent": r.discount_percent,
            "is_active": r.is_active,
        }
        for r in rows
    ]


@router.post("/")
async def create_tier(
    payload: TierCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_page_access("pricing-config")),
):
    tier = await upsert_tier(
        db,
        category=payload.category,
        min_qty=payload.min_qty,
        discount_percent=payload.discount_percent,
        is_active=payload.is_active,
    )
    await log_action(
        db, current_user.get("admin_id"), "bulk_discount_upsert",
        "bulk_discount_tiers", tier.id,
        {"category": tier.category, "min_qty": tier.min_qty, "pct": tier.discount_percent},
        request.client.host if request.client else None,
    )
    return {"id": tier.id, "category": tier.category, "min_qty": tier.min_qty,
            "discount_percent": tier.discount_percent, "is_active": tier.is_active}


@router.put("/{tier_id}")
async def update_tier(
    tier_id: int,
    payload: TierUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_page_access("pricing-config")),
):
    from sqlalchemy import select
    from shared.database.models import BulkDiscountTier
    row = await db.scalar(select(BulkDiscountTier).where(BulkDiscountTier.id == tier_id))
    if not row:
        raise HTTPException(status_code=404, detail="Tier not found")
    row.discount_percent = payload.discount_percent
    row.is_active = payload.is_active
    await db.commit()
    await log_action(
        db, current_user.get("admin_id"), "bulk_discount_update",
        "bulk_discount_tiers", tier_id,
        {"pct": payload.discount_percent, "active": payload.is_active},
        request.client.host if request.client else None,
    )
    return {"id": row.id, "category": row.category, "min_qty": row.min_qty,
            "discount_percent": row.discount_percent, "is_active": row.is_active}


@router.delete("/{tier_id}")
async def remove_tier(
    tier_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_page_access("pricing-config")),
):
    deleted = await delete_tier(db, tier_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Tier not found")
    await log_action(
        db, current_user.get("admin_id"), "bulk_discount_delete",
        "bulk_discount_tiers", tier_id, {}, request.client.host if request.client else None,
    )
    return {"ok": True}
