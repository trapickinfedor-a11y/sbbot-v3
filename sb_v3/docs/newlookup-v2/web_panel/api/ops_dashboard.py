"""
Operational Dashboard — единый API для всех «горящих» очередей.
Показывает: pending заказы, открытые споры, ожидающие выводы,
открытые тикеты, модерация селлеров, просроченные задачи.
"""

import logging
from datetime import datetime, timedelt, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from web_panel.auth import get_current_user, can_view_finances
from web_panel.database import get_db
from shared.database.models import (
    Order,
    SupportTicket,
    SellerOrder,
    SellerOrderDispute,
    SellerWithdrawal,
    WorkerWithdrawal,
    MarketerWithdrawal,
    BotOwnerWithdrawal,
    Seller,
    Worker,
)

router = APIRouter(prefix="/api/ops", tags=["ops-dashboard"])
logger = logging.getLogger(__name__)


@router.get("/queues")
async def get_operational_queues(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Единый endpoint — все очереди, требующие внимания.
    Возвращает счётчики по каждой категории.
    """
    finance = can_view_finances(current_user)
    now = datetime.now(timezone.utc)

    # ── Orders ────────────────────────────────────────────────────────────
    pending_orders = await db.scalar(
        select(func.count(Order.id)).where(Order.status == "pending")
    ) or 0
    processing_orders = await db.scalar(
        select(func.count(Order.id)).where(Order.status == "processing")
    ) or 0
    # Заказы, зависшие > 2 часов в processing
    stale_orders = await db.scalar(
        select(func.count(Order.id)).where(and_(
            Order.status == "processing",
            Order.taken_at < now - timedelta(hours=2),
        ))
    ) or 0

    # ── Seller Orders ─────────────────────────────────────────────────────
    seller_pending = await db.scalar(
        select(func.count(SellerOrder.id)).where(SellerOrder.status == "pending_admin")
    ) or 0

    # ── Disputes ──────────────────────────────────────────────────────────
    open_disputes = await db.scalar(
        select(func.count(SellerOrderDispute.id)).where(SellerOrderDispute.status == "open")
    ) or 0
    overdue_disputes = await db.scalar(
        select(func.count(SellerOrderDispute.id)).where(and_(
            SellerOrderDispute.status == "open",
            SellerOrderDispute.seller_response_due_at < now,
            SellerOrderDispute.seller_responded_at.is_(None),
        ))
    ) or 0
    pending_appeals = await db.scalar(
        select(func.count(SellerOrderDispute.id)).where(
            SellerOrderDispute.appeal_status == "requested"
        )
    ) or 0

    # ── Support Tickets ───────────────────────────────────────────────────
    open_tickets = await db.scalar(
        select(func.count(SupportTicket.id)).where(SupportTicket.status == "open")
    ) or 0

    # ── Seller Moderation ─────────────────────────────────────────────────
    pending_sellers = await db.scalar(
        select(func.count(Seller.id)).where(and_(
            Seller.is_approved == False,
            Seller.is_active == True,
        ))
    ) or 0

    # ── Workers ───────────────────────────────────────────────────────────
    active_workers = await db.scalar(
        select(func.count(Worker.id)).where(Worker.is_active == True)
    ) or 0

    # ── Withdrawals (finance only) ────────────────────────────────────────
    withdrawals = None
    if finance:
        pending_w = {}
        for label, model in [
            ("seller", SellerWithdrawal),
            ("worker", WorkerWithdrawal),
            ("marketer", MarketerWithdrawal),
            ("bot_owner", BotOwnerWithdrawal),
        ]:
            cnt = await db.scalar(
                select(func.count(model.id)).where(model.status == "pending")
            ) or 0
            amt = float(await db.scalar(
                select(func.coalesce(func.sum(model.amount), 0)).where(model.status == "pending")
            ) or 0)
            pending_w[label] = {"count": cnt, "amount": amt}

        withdrawals = {
            **pending_w,
            "total_count": sum(v["count"] for v in pending_w.values()),
            "total_amount": sum(v["amount"] for v in pending_w.values()),
        }

    # ── Urgency score (для сортировки на фронте) ──────────────────────────
    urgency = (
        stale_orders * 3
        + overdue_disputes * 3
        + pending_appeals * 2
        + open_disputes
        + pending_orders
        + seller_pending
        + open_tickets
        + pending_sellers
    )

    return {
        "orders": {
            "pending": pending_orders,
            "processing": processing_orders,
            "stale": stale_orders,
        },
        "seller_orders": {
            "pending_admin": seller_pending,
        },
        "disputes": {
            "open": open_disputes,
            "overdue": overdue_disputes,
            "pending_appeals": pending_appeals,
        },
        "support": {
            "open_tickets": open_tickets,
        },
        "moderation": {
            "pending_sellers": pending_sellers,
        },
        "workers": {
            "active": active_workers,
        },
        "withdrawals": withdrawals,
        "urgency_score": urgency,
        "finance_visible": finance,
    }
