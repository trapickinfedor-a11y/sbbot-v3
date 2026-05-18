"""
Shared catalog for CC - used by seller_bot and mirror_bot.
"""
from __future__ import annotations

from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_

from shared.utils.seller_product_meta import cc_item_badge
from shared.utils.seller_card_renderers import render_cc_description


async def get_cc_categories(session: AsyncSession) -> List[Dict]:
    """Get CC categories from CCCategory, fallback to default."""
    try:
        from shared.database.models import CCCategory
        result = await session.execute(
            select(CCCategory).where(CCCategory.is_active == True).order_by(CCCategory.position, CCCategory.id)
        )
        cats = result.scalars().all()
        if cats:
            return [{"code": c.code, "name": c.name} for c in cats]
    except Exception:
        pass
    return [
        {"code": "usa",   "name": "🇺🇸 USA CC"},
        {"code": "world", "name": "🌍 ALL WORLD CC"},
    ]


async def get_cc_types_for_category(session: AsyncSession, category_code: str) -> List[Dict]:
    """Get CC item types for a category - CCItem from DB."""
    try:
        from shared.database.models import CCItem
        result = await session.execute(
            select(CCItem).where(
                CCItem.category_code == category_code,
                CCItem.is_active == True
            ).order_by(CCItem.position, CCItem.id)
        )
        items = result.scalars().all()
        if items:
            return [{"id": c.cc_code, "name": c.name} for c in items]
    except Exception:
        pass
    return []


async def get_cc_items_for_category(
    session: AsyncSession,
    category_code: str,
    *,
    bin_prefix: str | None = None,
    zip_q: str | None = None,
    sort_price: str = "asc",
) -> List[Dict]:
    """Get CC items for client catalog — CCItem + SellerCCItem (approved only)."""
    items: List[Dict[str, Any]] = []
    bin_prefix = (bin_prefix or "").strip()[:6] or None
    zip_q = (zip_q or "").strip() or None
    try:
        from shared.database.models import CCItem, SellerCCItem, Seller
        r1 = await session.execute(
            select(CCItem).where(
                CCItem.category_code == category_code,
                CCItem.is_active == True
            ).order_by(CCItem.position, CCItem.id)
        )
        for c in r1.scalars().all():
            items.append({"id": c.cc_code, "name": c.name, "price": float(c.price), "source": "admin"})

        cond = [
            SellerCCItem.is_active == True,
            SellerCCItem.moderation_status == "approved",
            Seller.is_approved == True,
            Seller.is_active == True,
        ]
        if category_code == "non_vbv":
            cond.append(SellerCCItem.is_non_vbv == True)
        else:
            cond.append(SellerCCItem.category_code == category_code)

        if bin_prefix:
            cond.append(
                or_(
                    SellerCCItem.card_bin == bin_prefix,
                    SellerCCItem.number.startswith(bin_prefix),
                )
            )
        if zip_q:
            cond.append(SellerCCItem.zip.ilike(f"%{zip_q}%"))

        order_col = SellerCCItem.buyer_price
        order_dir = order_col.desc() if sort_price == "desc" else order_col.asc()

        r2 = await session.execute(
            select(SellerCCItem).join(Seller).where(
                and_(*cond)
            ).order_by(order_dir, SellerCCItem.item_name)
        )
        for s in r2.scalars().all():
            last4 = ""
            num = (s.number or "").replace(" ", "")
            if len(num) >= 4:
                last4 = num[-4:]
            bin_code = (s.card_bin or "")[:6]
            brand = (s.card_brand or "")[:16]
            zip_mark = " 📍" if s.zip else ""
            btn = f"{bin_code} {brand} ***{last4}{zip_mark} | ${float(s.buyer_price):.2f}"
            items.append({
                "id": str(s.id),
                "name": btn,
                "price": float(s.buyer_price),
                "source": "seller",
                "seller_item_id": s.id,
                "product_subtype": getattr(s, "product_subtype", "with_fullz"),
                "description": render_cc_description(s),
            })
    except Exception:
        pass
    return items


async def get_cc_item_name(session: AsyncSession, cc_code: str) -> str:
    """Get CC item display name by cc_code."""
    try:
        from shared.database.models import CCItem
        result = await session.execute(
            select(CCItem.name).where(CCItem.cc_code == cc_code)
        )
        row = result.scalar_one_or_none()
        if row:
            return row
    except Exception:
        pass
    return cc_code.replace("_", " ").title()
