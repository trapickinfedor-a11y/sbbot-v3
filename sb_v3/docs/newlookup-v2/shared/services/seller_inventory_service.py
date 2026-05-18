from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import SellerBank


async def auto_unpublish_expired_seller_items(session: AsyncSession) -> int:
    now = datetime.now(timezone.utc)
    result = await session.execute(
        select(SellerBank).where(
            and_(
                SellerBank.is_active == True,
                SellerBank.auto_unpublish_enabled == True,
                SellerBank.auto_unpublish_at.is_not(None),
                SellerBank.auto_unpublish_at <= now,
            )
        )
    )
    items = list(result.scalars().all())
    for item in items:
        item.is_active = False
        item.is_in_stock = False
    if items:
        await session.commit()
    return len(items)
