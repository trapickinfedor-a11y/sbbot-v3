from __future__ import annotations

"""Service to send WISHLIST_PRICE_DROP notifications when product prices decrease."""
import logging
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import WishlistItem, User

logger = logging.getLogger(__name__)


async def notify_wishlist_price_drop(
    bot,
    session: AsyncSession,
    product_type: str,
    product_id: int,
    product_name: str,
    new_price: float,
    old_price: float,
    min_drop_percent: float = 3.0,
) -> int:
    """
    Notify all users who have this product in their wishlist that the price dropped.
    Only sends notification if price dropped by at least min_drop_percent%.
    Returns count of notifications sent.
    """
    if old_price <= 0 or new_price >= old_price:
        return 0

    drop_pct = (old_price - new_price) / old_price * 100
    if drop_pct < min_drop_percent:
        return 0

    r = await session.execute(
        select(WishlistItem).where(
            and_(
                WishlistItem.product_type == product_type,
                WishlistItem.product_id == product_id,
            )
        )
    )
    items = list(r.scalars().all())
    if not items:
        return 0

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    sent = 0
    for item in items:
        user = await session.get(User, item.user_id)
        if not user or not user.user_id:
            continue
        try:
            await bot.send_message(
                chat_id=user.user_id,
                text=(
                    f"❤️ <b>Price Drop Alert!</b>\n\n"
                    f"An item in your Wishlist just got cheaper:\n"
                    f"<b>{product_name}</b>\n\n"
                    f"<s>${old_price:.2f}</s> → <b>${new_price:.2f}</b> "
                    f"(-{drop_pct:.1f}%)\n\n"
                    f"Tap below to buy it now!"
                ),
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🛒 Buy Now", callback_data=f"wishlist_buy:{product_type}:{product_id}")],
                    [InlineKeyboardButton(text="❤️ View Wishlist", callback_data="wishlist_view")],
                ]),
            )
            sent += 1
        except Exception as exc:
            logger.warning("Failed to notify user %s of price drop: %s", user.user_id, exc)

    logger.info("Sent WISHLIST_PRICE_DROP for product %s/%s to %d users", product_type, product_id, sent)
    return sent
