"""
Alert Service — мониторинг пороговых значений и отправка уведомлений.
Вызывается из APScheduler job в main.py.
"""

import logging
import os
from datetime import datetime, timedelt, timezone

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import (
    Order,
    SellerOrderDispute,
    SellerWithdrawal,
    WorkerWithdrawal,
    MarketerWithdrawal,
    BotOwnerWithdrawal,
    SupportTicket,
)

logger = logging.getLogger(__name__)

ALERT_CHAT_ID = os.getenv("ALERT_CHAT_ID", "")
ALERT_BOT_TOKEN = os.getenv("ALERT_BOT_TOKEN", "") or os.getenv("SUPPORT_BOT_TOKEN", "")

# Пороги (можно переопределить через env)
THRESHOLD_STALE_ORDERS = int(os.getenv("ALERT_STALE_ORDERS", "5"))
THRESHOLD_OPEN_DISPUTES = int(os.getenv("ALERT_OPEN_DISPUTES", "10"))
THRESHOLD_PENDING_WITHDRAWALS = int(os.getenv("ALERT_PENDING_WITHDRAWALS", "15"))
THRESHOLD_OPEN_TICKETS = int(os.getenv("ALERT_OPEN_TICKETS", "20"))
THRESHOLD_5XX_PER_HOUR = int(os.getenv("ALERT_5XX_PER_HOUR", "50"))

_last_alerts: dict[str, datetime] = {}
_COOLDOWN_MINUTES = 30


async def check_alerts(session: AsyncSession) -> list[str]:
    """
    Проверяет все пороги. Возвращает список сработавших алертов.
    Отправляет в Telegram если настроен ALERT_CHAT_ID.
    """
    now = datetime.now(timezone.utc)
    fired: list[str] = []

    # 1. Зависшие заказы (processing > 2h)
    stale = await session.scalar(
        select(func.count(Order.id)).where(and_(
            Order.status == "processing",
            Order.taken_at < now - timedelta(hours=2),
        ))
    ) or 0
    if stale >= THRESHOLD_STALE_ORDERS:
        fired.append(f"🔴 Stale orders: {stale} orders stuck in processing >2h")

    # 2. Открытые споры
    open_disputes = await session.scalar(
        select(func.count(SellerOrderDispute.id)).where(SellerOrderDispute.status == "open")
    ) or 0
    if open_disputes >= THRESHOLD_OPEN_DISPUTES:
        fired.append(f"🟠 Open disputes: {open_disputes}")

    # 3. Просроченные споры (seller не ответил)
    overdue_disputes = await session.scalar(
        select(func.count(SellerOrderDispute.id)).where(and_(
            SellerOrderDispute.status == "open",
            SellerOrderDispute.seller_response_due_at < now,
            SellerOrderDispute.seller_responded_at.is_(None),
        ))
    ) or 0
    if overdue_disputes > 0:
        fired.append(f"🔴 Overdue disputes (seller no response): {overdue_disputes}")

    # 4. Ожидающие выводы
    total_pending_w = 0
    for model in [SellerWithdrawal, WorkerWithdrawal, MarketerWithdrawal, BotOwnerWithdrawal]:
        cnt = await session.scalar(
            select(func.count(model.id)).where(model.status == "pending")
        ) or 0
        total_pending_w += cnt
    if total_pending_w >= THRESHOLD_PENDING_WITHDRAWALS:
        fired.append(f"🟡 Pending withdrawals: {total_pending_w}")

    # 5. Открытые тикеты
    open_tickets = await session.scalar(
        select(func.count(SupportTicket.id)).where(SupportTicket.status == "open")
    ) or 0
    if open_tickets >= THRESHOLD_OPEN_TICKETS:
        fired.append(f"🟡 Open support tickets: {open_tickets}")

    # Отправляем если есть алерты и прошёл cooldown
    if fired:
        await _send_alerts(fired, now)

    return fired


async def _send_alerts(alerts: list[str], now: datetime):
    """Отправляет алерты в Telegram."""
    if not ALERT_CHAT_ID or not ALERT_BOT_TOKEN:
        logger.warning("Alert triggered but ALERT_CHAT_ID/ALERT_BOT_TOKEN not configured: %s", alerts)
        return

    key = "|".join(sorted(alerts))
    last = _last_alerts.get(key)
    if last and (now - last).total_seconds() < _COOLDOWN_MINUTES * 60:
        return

    try:
        from aiogram import Bot
        bot = Bot(token=ALERT_BOT_TOKEN)
        text = "⚠️ <b>Admin Panel Alerts</b>\n\n" + "\n".join(alerts)
        await bot.send_message(chat_id=int(ALERT_CHAT_ID), text=text, parse_mode="HTML")
        await bot.session.close()
        _last_alerts[key] = now
        logger.info("Alerts sent to %s: %s", ALERT_CHAT_ID, alerts)
    except Exception as e:
        logger.error("Failed to send alerts: %s", e)


async def get_alert_status(session: AsyncSession) -> dict:
    """Возвращает текущий статус всех метрик для отображения в UI."""
    now = datetime.now(timezone.utc)

    stale = await session.scalar(
        select(func.count(Order.id)).where(and_(
            Order.status == "processing",
            Order.taken_at < now - timedelta(hours=2),
        ))
    ) or 0

    open_disputes = await session.scalar(
        select(func.count(SellerOrderDispute.id)).where(SellerOrderDispute.status == "open")
    ) or 0

    overdue_disputes = await session.scalar(
        select(func.count(SellerOrderDispute.id)).where(and_(
            SellerOrderDispute.status == "open",
            SellerOrderDispute.seller_response_due_at < now,
            SellerOrderDispute.seller_responded_at.is_(None),
        ))
    ) or 0

    total_pending_w = 0
    for model in [SellerWithdrawal, WorkerWithdrawal, MarketerWithdrawal, BotOwnerWithdrawal]:
        total_pending_w += await session.scalar(
            select(func.count(model.id)).where(model.status == "pending")
        ) or 0

    open_tickets = await session.scalar(
        select(func.count(SupportTicket.id)).where(SupportTicket.status == "open")
    ) or 0

    return {
        "stale_orders": {"value": stale, "threshold": THRESHOLD_STALE_ORDERS, "alert": stale >= THRESHOLD_STALE_ORDERS},
        "open_disputes": {"value": open_disputes, "threshold": THRESHOLD_OPEN_DISPUTES, "alert": open_disputes >= THRESHOLD_OPEN_DISPUTES},
        "overdue_disputes": {"value": overdue_disputes, "threshold": 1, "alert": overdue_disputes > 0},
        "pending_withdrawals": {"value": total_pending_w, "threshold": THRESHOLD_PENDING_WITHDRAWALS, "alert": total_pending_w >= THRESHOLD_PENDING_WITHDRAWALS},
        "open_tickets": {"value": open_tickets, "threshold": THRESHOLD_OPEN_TICKETS, "alert": open_tickets >= THRESHOLD_OPEN_TICKETS},
        "has_alerts": any([
            stale >= THRESHOLD_STALE_ORDERS,
            open_disputes >= THRESHOLD_OPEN_DISPUTES,
            overdue_disputes > 0,
            total_pending_w >= THRESHOLD_PENDING_WITHDRAWALS,
            open_tickets >= THRESHOLD_OPEN_TICKETS,
        ]),
    }
