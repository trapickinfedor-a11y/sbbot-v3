"""Bulk-discount tier service — reads/writes BulkDiscountTier from DB.

Default tiers (inserted on first run):
  banks  : ≥3 → 2%, ≥5 → 3%, ≥10 → 5%
  esim   : ≥3 → 5%, ≥5 → 10%, ≥10 → 15%
  fullz  : ≥3 → 5%, ≥5 → 10%, ≥10 → 15%
  cc     : ≥3 → 2%, ≥5 → 4%, ≥10 → 7%
  accounts: ≥3 → 2%, ≥5 → 3%, ≥10 → 5%
  docs   : ≥3 → 2%, ≥5 → 3%, ≥10 → 5%
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Dict, List, Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import BulkDiscountTier

logger = logging.getLogger(__name__)

_DEFAULTS: list[dict] = [
    # Banks / Accounts / Docs
    *[{"category": c, "min_qty": 3, "discount_percent": 2.0} for c in ("banks", "accounts", "docs")],
    *[{"category": c, "min_qty": 5, "discount_percent": 3.0} for c in ("banks", "accounts", "docs")],
    *[{"category": c, "min_qty": 10, "discount_percent": 5.0} for c in ("banks", "accounts", "docs")],
    # eSIM / FULLZ / CC
    *[{"category": c, "min_qty": 3, "discount_percent": 5.0} for c in ("esim", "fullz")],
    *[{"category": c, "min_qty": 5, "discount_percent": 10.0} for c in ("esim", "fullz")],
    *[{"category": c, "min_qty": 10, "discount_percent": 15.0} for c in ("esim", "fullz")],
    {"category": "cc", "min_qty": 3, "discount_percent": 2.0},
    {"category": "cc", "min_qty": 5, "discount_percent": 4.0},
    {"category": "cc", "min_qty": 10, "discount_percent": 7.0},
]

# Simple in-memory cache: {category: [(min_qty, discount_percent), ...]}
_CACHE: Dict[str, list] = {}
_CACHE_DIRTY = True


async def ensure_defaults(session: AsyncSession) -> None:
    """Insert default tiers if the table is empty."""
    count = await session.scalar(
        select(BulkDiscountTier).limit(1)
    )
    if count is not None:
        return
    for d in _DEFAULTS:
        session.add(BulkDiscountTier(**d))
    await session.commit()
    global _CACHE_DIRTY
    _CACHE_DIRTY = True


async def get_tiers(session: AsyncSession, category: str) -> List[BulkDiscountTier]:
    result = await session.execute(
        select(BulkDiscountTier)
        .where(BulkDiscountTier.category == category, BulkDiscountTier.is_active == True)
        .order_by(BulkDiscountTier.min_qty)
    )
    return list(result.scalars().all())


async def get_all_tiers(session: AsyncSession) -> List[BulkDiscountTier]:
    result = await session.execute(
        select(BulkDiscountTier).order_by(BulkDiscountTier.category, BulkDiscountTier.min_qty)
    )
    return list(result.scalars().all())


async def get_discount_percent(
    session: AsyncSession,
    category: str,
    quantity: int,
) -> float:
    """Return the highest applicable discount % for a given category + qty."""
    tiers = await get_tiers(session, category)
    best = 0.0
    for tier in tiers:
        if quantity >= tier.min_qty:
            best = max(best, tier.discount_percent)
    return best


async def get_discount_decimal(
    session: AsyncSession,
    category: str,
    quantity: int,
) -> Decimal:
    pct = await get_discount_percent(session, category, quantity)
    return Decimal(str(pct)) / Decimal("100")


async def upsert_tier(
    session: AsyncSession,
    category: str,
    min_qty: int,
    discount_percent: float,
    is_active: bool = True,
) -> BulkDiscountTier:
    existing = await session.scalar(
        select(BulkDiscountTier).where(
            BulkDiscountTier.category == category,
            BulkDiscountTier.min_qty == min_qty,
        )
    )
    if existing:
        existing.discount_percent = discount_percent
        existing.is_active = is_active
        await session.commit()
        return existing
    tier = BulkDiscountTier(
        category=category,
        min_qty=min_qty,
        discount_percent=discount_percent,
        is_active=is_active,
    )
    session.add(tier)
    await session.commit()
    return tier


async def delete_tier(session: AsyncSession, tier_id: int) -> bool:
    row = await session.scalar(select(BulkDiscountTier).where(BulkDiscountTier.id == tier_id))
    if not row:
        return False
    await session.delete(row)
    await session.commit()
    return True
