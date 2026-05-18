from __future__ import annotations

"""Background service: sends review request 24h after a successful purchase (ORDER_REVIEW_REQUEST)."""
import asyncio
import logging
from datetime import datetime, timedelt, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import async_sessionmaker

from shared.database.models import Order

logger = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 1800  # Check every 30 minutes
REVIEW_DELAY_HOURS = 24


async def run_review_request_service(
    stop_event: asyncio.Event,
    session_maker: async_sessionmaker,
    bot,
) -> None:
    """Loop: find completed orders where review hasn't been requested yet, send request after 24h."""
    while not stop_event.is_set():
        try:
            await _process_review_requests(session_maker, bot)
        except Exception as exc:
            logger.warning("Review request service error: %s", exc)

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=CHECK_INTERVAL_SECONDS)
        except asyncio.TimeoutError:
            continue


async def _process_review_requests(session_maker: async_sessionmaker, bot) -> None:
    threshold = datetime.now(timezone.utc) - timedelta(hours=REVIEW_DELAY_HOURS)

    async with session_maker() as session:
        # Find completed orders older than 24h where review_requested is False/None
        result = await session.execute(
            select(Order).where(
                Order.status == "completed",
                Order.created_at <= threshold,
                Order.review_requested.is_(False) | Order.review_requested.is_(None),
            ).limit(100)
        )
        orders = list(result.scalars().all())

        for order in orders:
            try:
                product_name = getattr(order, "product_name", None) or f"Order #{order.id}"
                msg = (
                    f"⭐ <b>How was your purchase?</b>\n\n"
                    f"You recently bought: <b>{product_name}</b>\n\n"
                    f"Please take 15 seconds to rate your experience — it helps other buyers!"
                )
                from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(text="⭐ 5", callback_data=f"review:{order.id}:5"),
                        InlineKeyboardButton(text="⭐ 4", callback_data=f"review:{order.id}:4"),
                        InlineKeyboardButton(text="⭐ 3", callback_data=f"review:{order.id}:3"),
                        InlineKeyboardButton(text="⭐ 2", callback_data=f"review:{order.id}:2"),
                        InlineKeyboardButton(text="⭐ 1", callback_data=f"review:{order.id}:1"),
                    ],
                    [InlineKeyboardButton(text="⏭ Skip", callback_data=f"review:{order.id}:skip")],
                ])
                await bot.send_message(
                    chat_id=order.user_id,
                    text=msg,
                    parse_mode="HTML",
                    reply_markup=keyboard,
                )

                # Mark as requested
                await session.execute(
                    update(Order).where(Order.id == order.id).values(review_requested=True)
                )
                await session.commit()
                logger.info("Review request sent for order %s to user %s", order.id, order.user_id)
            except Exception as exc:
                logger.warning("Failed to send review request for order %s: %s", order.id, exc)
