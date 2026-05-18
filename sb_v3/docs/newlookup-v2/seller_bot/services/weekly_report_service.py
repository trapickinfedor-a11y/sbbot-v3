from __future__ import annotations

"""Background service: sends weekly SELLER_WEEKLY_REPORT to all active sellers every Monday.
Also sends stale-product alerts (no sales in 30+ days) once per week.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import async_sessionmaker

from shared.database.models import Seller, SellerOrder, SellerBank

logger = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 3600  # Check every hour; send only on Monday 09:00


def _is_seller_quiet_hours(seller: "Seller") -> bool:
    """Return True if current UTC hour falls within seller's quiet hours window."""
    start = getattr(seller, "quiet_hours_start", None)
    end = getattr(seller, "quiet_hours_end", None)
    if start is None or end is None:
        return False
    current_hour = datetime.now(timezone.utc).hour
    if start < end:
        return start <= current_hour < end
    # Overnight window, e.g. 22–09
    return current_hour >= start or current_hour < end


async def run_weekly_report_service(
    stop_event: asyncio.Event,
    session_maker: async_sessionmaker,
    bot,
) -> None:
    """Weekly loop: sends report every Monday at 09:00 UTC."""
    last_sent_week: int | None = None  # ISO week number

    while not stop_event.is_set():
        try:
            now = datetime.now(timezone.utc)
            current_week = now.isocalendar()[1]
            # Monday = 0 in weekday(), send between 09:00 and 10:00
            if now.weekday() == 0 and 9 <= now.hour < 10 and current_week != last_sent_week:
                await _send_weekly_reports(session_maker, bot)
                last_sent_week = current_week
        except Exception as exc:
            logger.warning("Weekly report service error: %s", exc)

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=CHECK_INTERVAL_SECONDS)
        except asyncio.TimeoutError:
            continue


async def _send_weekly_reports(session_maker: async_sessionmaker, bot) -> None:
    """Generate and send weekly reports to all active sellers."""
    week_start = datetime.now(timezone.utc) - timedelta(days=7)

    async with session_maker() as session:
        result = await session.execute(
            select(Seller).where(
                Seller.is_active == True,
                Seller.access_status == "active",
            )
        )
        sellers = list(result.scalars().all())
        logger.info("Sending weekly reports to %d sellers", len(sellers))

        for seller in sellers:
            try:
                if _is_seller_quiet_hours(seller):
                    continue
                # Count sales this week
                sales_count = int(
                    await session.scalar(
                        select(func.count(SellerOrder.id)).where(
                            SellerOrder.seller_id == seller.id,
                            SellerOrder.status == "completed",
                            SellerOrder.created_at >= week_start,
                        )
                    ) or 0
                )
                # Revenue this week
                revenue = float(
                    await session.scalar(
                        select(func.coalesce(func.sum(SellerOrder.buyer_price), 0)).where(
                            SellerOrder.seller_id == seller.id,
                            SellerOrder.status == "completed",
                            SellerOrder.created_at >= week_start,
                        )
                    ) or 0
                )
                # Best selling product
                best_row = await session.execute(
                    select(SellerBank.bank_name, func.count(SellerOrder.id).label("cnt"))
                    .join(SellerOrder, SellerOrder.seller_bank_id == SellerBank.id)
                    .where(
                        SellerOrder.seller_id == seller.id,
                        SellerOrder.status == "completed",
                        SellerOrder.created_at >= week_start,
                    )
                    .group_by(SellerBank.bank_name)
                    .order_by(func.count(SellerOrder.id).desc())
                    .limit(1)
                )
                best_product_row = best_row.first()
                best_product = best_product_row[0] if best_product_row else "—"

                period_label = f"{week_start.strftime('%b %d')} – {datetime.now(timezone.utc).strftime('%b %d')}"

                await bot.send_message(
                    chat_id=seller.telegram_id,
                    text=(
                        f"📊 <b>Your Weekly Report</b>\n"
                        f"<i>{period_label}</i>\n\n"
                        f"✅ <b>Sales:</b> {sales_count}\n"
                        f"💰 <b>Revenue:</b> ${revenue:.2f}\n"
                        f"🏆 <b>Best Product:</b> {best_product}\n\n"
                        f"Keep up the great work! Open the Mini App for detailed analytics."
                    ),
                    parse_mode="HTML",
                )
                logger.info("Weekly report sent to seller %s", seller.telegram_id)

                # Stale product alerts: items not sold for 30+ days
                await _send_stale_product_alerts(session, bot, seller)

            except Exception as exc:
                logger.warning("Failed to send weekly report to seller %s: %s", seller.telegram_id, exc)


async def _send_stale_product_alerts(session, bot, seller: Seller) -> None:
    """Notify seller about listings that haven't sold in 30+ days."""
    threshold = datetime.now(timezone.utc) - timedelta(days=30)
    # Get active listings for seller
    listings_r = await session.execute(
        select(SellerBank).where(
            SellerBank.seller_id == seller.id,
            SellerBank.is_active == True,
            SellerBank.stock_count > 0,
        ).limit(200)
    )
    listings = list(listings_r.scalars().all())
    stale = []
    for listing in listings:
        # Check last sale date
        last_sale = await session.scalar(
            select(func.max(SellerOrder.created_at)).where(
                SellerOrder.seller_bank_id == listing.id,
                SellerOrder.status == "completed",
            )
        )
        if last_sale is None or last_sale < threshold:
            stale.append(listing)

    if not stale:
        return

    lines = [f"• {l.bank_name} (${float(l.buyer_price or l.seller_price or 0):.0f})" for l in stale[:10]]
    msg = (
        f"🤔 <b>Stale Listings Alert</b>\n\n"
        f"The following {len(stale)} item(s) haven't sold in 30+ days:\n"
        + "\n".join(lines)
        + "\n\n<i>Consider lowering the price or updating the description.</i>"
    )
    try:
        await bot.send_message(chat_id=seller.telegram_id, text=msg, parse_mode="HTML")
    except Exception as exc:
        logger.warning("Failed to send stale alert to seller %s: %s", seller.telegram_id, exc)
