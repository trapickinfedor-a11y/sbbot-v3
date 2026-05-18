from __future__ import annotations

"""Background watcher: detects abandoned shopping carts and notifies users."""
import asyncio
import logging
from datetime import datetime, timedelt, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from shared.database.models import ShoppingCart, CartItem, User

logger = logging.getLogger(__name__)

CART_ABANDON_HOURS = 1  # cart is "abandoned" after 1 hour of inactivity
CHECK_INTERVAL_SECONDS = 600  # check every 10 minutes


async def run_abandoned_cart_watcher(
    stop_event: asyncio.Event,
    session_maker: async_sessionmaker,
    bot,
) -> None:
    """Long-running async loop that checks for abandoned carts every 10 minutes."""
    while not stop_event.is_set():
        try:
            await _process_abandoned_carts(session_maker, bot)
        except Exception as exc:
            logger.warning("Abandoned cart watcher error: %s", exc)

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=CHECK_INTERVAL_SECONDS)
        except asyncio.TimeoutError:
            continue


async def _process_abandoned_carts(session_maker: async_sessionmaker, bot) -> None:
    """Find active carts not updated for > 1 hour and send reminder."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=CART_ABANDON_HOURS)

    async with session_maker() as session:
        result = await session.execute(
            select(ShoppingCart).where(
                ShoppingCart.status == "active",
                ShoppingCart.abandoned_notified == False,
                ShoppingCart.updated_at <= cutoff,
            ).limit(100)
        )
        carts = list(result.scalars().all())
        if not carts:
            return

        for cart in carts:
            # Load items
            items_r = await session.execute(
                select(CartItem).where(CartItem.cart_id == cart.id)
            )
            items = list(items_r.scalars().all())
            if not items:
                # empty cart, just mark status
                cart.status = "abandoned"
                cart.abandoned_notified = True
                continue

            # Load user
            user = await session.get(User, cart.user_id)
            if not user or not user.user_id:
                cart.status = "abandoned"
                cart.abandoned_notified = True
                continue

            total = sum(float(i.price) for i in items)
            item_count = len(items)

            try:
                from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text=f"🛒 Go to Cart ({item_count} items · ${total:.2f})",
                        callback_data="cart_view"
                    )],
                ])
                await bot.send_message(
                    chat_id=user.user_id,
                    text=(
                        f"🛒 <b>You left something in your cart!</b>\n\n"
                        f"You have <b>{item_count} item(s)</b> worth <b>${total:.2f}</b> "
                        f"waiting in your cart. Complete your purchase before they run out!\n\n"
                        f"Tap below to continue:"
                    ),
                    parse_mode="HTML",
                    reply_markup=kb,
                )
                cart.abandoned_notified = True
                cart.status = "abandoned"
                logger.info("Sent ABANDONED_CART_1H to user %s, cart %s", user.user_id, cart.id)
            except Exception as exc:
                logger.warning("Failed to notify user %s for cart %s: %s", user.user_id, cart.id, exc)

        await session.commit()
