"""seller_bot/services/daily_report_service.py

Background service that sends a daily product/revenue summary to every
active seller.

Design:
- Loop wakes up every SLEEP_SECONDS (default 300 = 5 min).
- Sends a report when the UTC hour matches REPORT_UTC_HOUR (default 9).
- Each seller can override their preferred hour via the seller.report_hour
  column (falls back to REPORT_UTC_HOUR if the column doesn't exist).
- Tracks the last date a report was sent per-seller to avoid duplicates.
- Python 3.9-compatible (no walrus-operator, no match/case, no X | Y unions).

Usage in bot.py:
    from seller_bot.services.daily_report_service import run_daily_report_service
    daily_task = asyncio.create_task(run_daily_report_service(stop_event, session_maker, bot))
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Set

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from shared.database.models import (
    Seller,
    SellerBank,
    SellerCCItem,
    SellerOrder,
    SellerUploadBatch,
)
from shared.i18n import t

logger = logging.getLogger(__name__)

# How often (seconds) to poll whether it's time to send reports
SLEEP_SECONDS = 300
# Default UTC hour to send reports (09:00 UTC)
DEFAULT_REPORT_UTC_HOUR = 9


def _seller_report_hour(seller: "Seller") -> int:
    """Return the hour (UTC) at which this seller wants their daily report."""
    hour = getattr(seller, "report_hour", None)
    if hour is None:
        return DEFAULT_REPORT_UTC_HOUR
    try:
        return int(hour) % 24
    except (TypeError, ValueError):
        return DEFAULT_REPORT_UTC_HOUR


async def run_daily_report_service(
    stop_event: asyncio.Event,
    session_maker: async_sessionmaker,
    bot,
) -> None:
    """Main loop: fires daily reports for sellers at their configured hour."""
    # seller_id -> date when last report was sent
    sent_today: dict[int, date] = {}

    while not stop_event.is_set():
        try:
            now = datetime.now(timezone.utc)
            await _check_and_send(session_maker, bot, now, sent_today)
        except Exception as exc:
            logger.warning("Daily report service error: %s", exc)

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=SLEEP_SECONDS)
        except asyncio.TimeoutError:
            continue


async def _check_and_send(
    session_maker: async_sessionmaker,
    bot,
    now: datetime,
    sent_today: dict,
) -> None:
    async with session_maker() as session:
        result = await session.execute(
            select(Seller).where(
                Seller.is_active == True,
                Seller.access_status == "active",
            )
        )
        sellers = list(result.scalars().all())

    for seller in sellers:
        target_hour = _seller_report_hour(seller)
        if now.hour != target_hour:
            continue

        today = now.date()
        if sent_today.get(seller.id) == today:
            continue  # Already sent today

        try:
            await _send_daily_report(session_maker, bot, seller)
            sent_today[seller.id] = today
        except Exception as exc:
            logger.warning(
                "Failed to send daily report to seller %s: %s",
                seller.telegram_id,
                exc,
            )


async def _send_daily_report(
    session_maker: async_sessionmaker,
    bot,
    seller: "Seller",
) -> None:
    """Build and send the daily report to a single seller."""
    lang = getattr(seller, "language", None) or "en"
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    async with session_maker() as session:
        # Count items by moderation state across all upload batches
        uploaded_count = int(
            await session.scalar(
                select(func.count(SellerBank.id)).where(
                    SellerBank.seller_id == seller.id,
                )
            ) or 0
        )
        in_moderation_count = int(
            await session.scalar(
                select(func.count(SellerBank.id)).where(
                    SellerBank.seller_id == seller.id,
                    SellerBank.moderation_status == "pending_moderation",
                )
            ) or 0
        )
        approved_count = int(
            await session.scalar(
                select(func.count(SellerBank.id)).where(
                    SellerBank.seller_id == seller.id,
                    SellerBank.moderation_status == "approved",
                )
            ) or 0
        )

        # Sales & revenue today
        sold_today = int(
            await session.scalar(
                select(func.count(SellerOrder.id)).where(
                    SellerOrder.seller_id == seller.id,
                    SellerOrder.status == "completed",
                    SellerOrder.created_at >= today_start,
                )
            ) or 0
        )
        revenue_today = float(
            await session.scalar(
                select(func.coalesce(func.sum(SellerOrder.buyer_price), 0)).where(
                    SellerOrder.seller_id == seller.id,
                    SellerOrder.status == "completed",
                    SellerOrder.created_at >= today_start,
                )
            ) or 0
        )

    withdrawable = float(getattr(seller, "withdrawable_balance", Decimal("0")) or 0)
    rating = float(getattr(seller, "seller_score", 5.0) or 5.0)

    text = t(
        "seller.daily_report",
        lang,
        date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        uploaded=uploaded_count,
        in_moderation=in_moderation_count,
        approved=approved_count,
        sold_today=sold_today,
        revenue_today=revenue_today,
        withdrawable=withdrawable,
        rating=rating,
    )

    await bot.send_message(
        chat_id=seller.telegram_id,
        text=text,
        parse_mode="HTML",
    )
    logger.info("Daily report sent to seller %s", seller.telegram_id)
