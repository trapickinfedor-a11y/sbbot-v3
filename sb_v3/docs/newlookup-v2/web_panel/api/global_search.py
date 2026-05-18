"""
Global Search API — поиск по Telegram ID, username, order ID, seller, worker.
Один endpoint — ищет по всем сущностям параллельно.
"""

import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, or_, func, cast, String
from sqlalchemy.ext.asyncio import AsyncSession

from web_panel.auth import get_current_user
from web_panel.database import get_db
from shared.database.models import User, Order, Seller, Worker, MirrorBot, SupportTicket

router = APIRouter(prefix="/api/search", tags=["search"])
logger = logging.getLogger(__name__)

MAX_RESULTS_PER_TYPE = 10


class SearchResultItem(BaseModel):
    type: str  # user | order | seller | worker | bot | ticket
    id: int
    label: str
    subtitle: Optional[str] = None
    url: Optional[str] = None


class SearchResponse(BaseModel):
    query: str
    results: List[SearchResultItem]
    total: int


@router.get("", response_model=SearchResponse)
async def global_search(
    q: str = Query(..., min_length=1, max_length=200, description="Search query"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Глобальный поиск. Ищет по:
    - User: telegram_id, username
    - Order: id
    - Seller: telegram_id, username, display_name
    - Worker: telegram_id, username
    - MirrorBot: bot_username
    - SupportTicket: id, user_id
    """
    q_stripped = q.strip()
    results: List[SearchResultItem] = []

    is_numeric = q_stripped.isdigit()
    q_int = int(q_stripped) if is_numeric else None
    q_like = f"%{q_stripped.lower()}%"

    # ── Users ─────────────────────────────────────────────────────────────
    user_q = select(User)
    if is_numeric:
        user_q = user_q.where(or_(
            User.user_id == q_int,
            User.id == q_int,
        ))
    else:
        user_q = user_q.where(
            func.lower(User.username).like(q_like)
        )
    users = (await db.execute(user_q.limit(MAX_RESULTS_PER_TYPE))).scalars().all()
    for u in users:
        results.append(SearchResultItem(
            type="user",
            id=u.user_id,
            label=f"@{u.username}" if u.username else f"User #{u.user_id}",
            subtitle=f"TG: {u.user_id} | Balance: {float(u.balance):.2f}",
            url=f"/users?user_id={u.user_id}",
        ))

    # ── Orders ────────────────────────────────────────────────────────────
    if is_numeric:
        order_q = select(Order).where(or_(
            Order.id == q_int,
            Order.user_id == q_int,
        )).limit(MAX_RESULTS_PER_TYPE)
        orders = (await db.execute(order_q)).scalars().all()
        for o in orders:
            results.append(SearchResultItem(
                type="order",
                id=o.id,
                label=f"Order #{o.id}",
                subtitle=f"{o.category}/{o.service_name} — {o.status} — ${float(o.price):.2f}",
                url=f"/orders?order_id={o.id}",
            ))

    # ── Sellers ───────────────────────────────────────────────────────────
    seller_q = select(Seller)
    if is_numeric:
        seller_q = seller_q.where(or_(
            Seller.id == q_int,
            Seller.telegram_id == q_int,
        ))
    else:
        seller_q = seller_q.where(or_(
            func.lower(Seller.username).like(q_like),
            func.lower(Seller.display_name).like(q_like),
        ))
    sellers = (await db.execute(seller_q.limit(MAX_RESULTS_PER_TYPE))).scalars().all()
    for s in sellers:
        results.append(SearchResultItem(
            type="seller",
            id=s.id,
            label=s.display_name or s.username or f"Seller #{s.id}",
            subtitle=f"TG: {s.telegram_id} | Type: {s.seller_type} | Score: {s.seller_score}",
            url=f"/seller-crm?seller_id={s.id}",
        ))

    # ── Workers ───────────────────────────────────────────────────────────
    worker_q = select(Worker)
    if is_numeric:
        worker_q = worker_q.where(or_(
            Worker.id == q_int,
            Worker.telegram_id == q_int,
        ))
    else:
        worker_q = worker_q.where(
            func.lower(Worker.username).like(q_like)
        )
    workers = (await db.execute(worker_q.limit(MAX_RESULTS_PER_TYPE))).scalars().all()
    for w in workers:
        results.append(SearchResultItem(
            type="worker",
            id=w.id,
            label=w.username or f"Worker #{w.telegram_id}",
            subtitle=f"TG: {w.telegram_id} | Active: {w.is_active}",
            url=f"/workers?worker_id={w.id}",
        ))

    # ── Bots ──────────────────────────────────────────────────────────────
    if not is_numeric:
        bot_q = select(MirrorBot).where(
            func.lower(MirrorBot.bot_username).like(q_like)
        ).limit(MAX_RESULTS_PER_TYPE)
        bots = (await db.execute(bot_q)).scalars().all()
        for b in bots:
            results.append(SearchResultItem(
                type="bot",
                id=b.id,
                label=f"@{b.bot_username}" if b.bot_username else f"Bot #{b.id}",
                subtitle=f"Active: {b.is_active}",
                url=f"/bots?bot_id={b.id}",
            ))

    # ── Support Tickets ───────────────────────────────────────────────────
    if is_numeric:
        ticket_q = select(SupportTicket).where(or_(
            SupportTicket.id == q_int,
            SupportTicket.user_id == q_int,
        )).limit(MAX_RESULTS_PER_TYPE)
        tickets = (await db.execute(ticket_q)).scalars().all()
        for t in tickets:
            results.append(SearchResultItem(
                type="ticket",
                id=t.id,
                label=f"Ticket #{t.id}",
                subtitle=f"User: {t.user_id} | Status: {t.status}",
                url=f"/support?ticket_id={t.id}",
            ))

    return SearchResponse(query=q_stripped, results=results, total=len(results))
