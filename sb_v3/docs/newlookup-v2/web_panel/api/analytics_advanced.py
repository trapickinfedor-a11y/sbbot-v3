"""
Advanced Analytics API — временные ряды, срезы, маркетплейс, воронки, когорты.
"""

import logging
from datetime import datetime, timedelta, dat, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, and_, case, extract, text, cast, Date
from sqlalchemy.ext.asyncio import AsyncSession

from web_panel.auth import require_finance_access, get_current_user, can_view_finances
from web_panel.database import get_db
from shared.database.models import (
    User,
    Order,
    MirrorBot,
    Seller,
    SellerOrder,
    SellerOrderDispute,
    Transaction,
    ProductPurchase,
    Product,
)

router = APIRouter(prefix="/api/analytics-v2", tags=["analytics-v2"])
logger = logging.getLogger(__name__)


def _date_range(days: int, start: Optional[str], end: Optional[str]):
    now = datetime.now(timezone.utc)
    end_dt = datetime.strptime(end, "%Y-%m-%d") + timedelta(days=1) if end else now + timedelta(seconds=1)
    start_dt = datetime.strptime(start, "%Y-%m-%d") if start else end_dt - timedelta(days=days)
    return start_dt, end_dt


# ═══════════════════════════════════════════════════════════════════════════════
# P2: Временные ряды по дням
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/timeseries/orders")
async def timeseries_orders(
    days: int = Query(30, le=365),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    bot_id: Optional[int] = None,
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_finance_access()),
):
    """Заказы по дням — count и revenue."""
    start_dt, end_dt = _date_range(days, start_date, end_date)
    q = (
        select(
            cast(Order.created_at, Date).label("day"),
            func.count(Order.id).label("count"),
            func.coalesce(func.sum(
                case((Order.status == "completed", Order.price), else_=0)
            ), 0).label("revenue"),
        )
        .where(Order.created_at >= start_dt, Order.created_at < end_dt)
    )
    if bot_id:
        q = q.where(Order.mirror_bot_id == bot_id)
    if category:
        q = q.where(Order.category == category)
    q = q.group_by("day").order_by("day")

    rows = (await db.execute(q)).all()
    return {
        "period": {"start": start_dt.strftime("%Y-%m-%d"), "end": (end_dt - timedelta(days=1)).strftime("%Y-%m-%d")},
        "data": [{"date": str(r.day), "count": r.count, "revenue": float(r.revenue)} for r in rows],
    }


@router.get("/timeseries/users")
async def timeseries_users(
    days: int = Query(30, le=365),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    bot_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Регистрации по дням."""
    start_dt, end_dt = _date_range(days, start_date, end_date)
    q = (
        select(
            cast(User.created_at, Date).label("day"),
            func.count(User.id).label("count"),
        )
        .where(User.created_at >= start_dt, User.created_at < end_dt)
    )
    if bot_id:
        q = q.where(User.mirror_bot_id == bot_id)
    q = q.group_by("day").order_by("day")

    rows = (await db.execute(q)).all()
    return {
        "period": {"start": start_dt.strftime("%Y-%m-%d"), "end": (end_dt - timedelta(days=1)).strftime("%Y-%m-%d")},
        "data": [{"date": str(r.day), "count": r.count} for r in rows],
    }


@router.get("/timeseries/deposits")
async def timeseries_deposits(
    days: int = Query(30, le=365),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_finance_access()),
):
    """Пополнения по дням."""
    start_dt, end_dt = _date_range(days, start_date, end_date)
    q = (
        select(
            cast(Transaction.created_at, Date).label("day"),
            func.count(Transaction.id).label("count"),
            func.coalesce(func.sum(Transaction.amount), 0).label("total"),
        )
        .where(
            Transaction.created_at >= start_dt,
            Transaction.created_at < end_dt,
            Transaction.type == "deposit",
        )
        .group_by("day").order_by("day")
    )
    rows = (await db.execute(q)).all()
    return {
        "data": [{"date": str(r.day), "count": r.count, "total": float(r.total)} for r in rows],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# P2: Срезы по боту / категории / селлеру
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/breakdown/by-bot")
async def breakdown_by_bot(
    days: int = Query(30, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_finance_access()),
):
    """Заказы и выручка в разрезе ботов."""
    start_dt = datetime.now(timezone.utc) - timedelta(days=days)
    q = (
        select(
            Order.mirror_bot_id,
            MirrorBot.bot_username,
            func.count(Order.id).label("orders"),
            func.coalesce(func.sum(
                case((Order.status == "completed", Order.price), else_=0)
            ), 0).label("revenue"),
            func.count(func.distinct(Order.user_id)).label("unique_buyers"),
        )
        .outerjoin(MirrorBot, MirrorBot.id == Order.mirror_bot_id)
        .where(Order.created_at >= start_dt)
        .group_by(Order.mirror_bot_id, MirrorBot.bot_username)
        .order_by(text("revenue DESC"))
    )
    rows = (await db.execute(q)).all()
    return {
        "data": [{
            "bot_id": r.mirror_bot_id,
            "bot_username": r.bot_username,
            "orders": r.orders,
            "revenue": float(r.revenue),
            "unique_buyers": r.unique_buyers,
        } for r in rows],
    }


@router.get("/breakdown/by-category")
async def breakdown_by_category(
    days: int = Query(30, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_finance_access()),
):
    """Заказы и выручка в разрезе категорий."""
    start_dt = datetime.now(timezone.utc) - timedelta(days=days)
    q = (
        select(
            Order.category,
            func.count(Order.id).label("orders"),
            func.coalesce(func.sum(
                case((Order.status == "completed", Order.price), else_=0)
            ), 0).label("revenue"),
            func.avg(Order.price).label("avg_price"),
        )
        .where(Order.created_at >= start_dt)
        .group_by(Order.category)
        .order_by(text("revenue DESC"))
    )
    rows = (await db.execute(q)).all()
    return {
        "data": [{
            "category": r.category,
            "orders": r.orders,
            "revenue": float(r.revenue),
            "avg_price": round(float(r.avg_price or 0), 2),
        } for r in rows],
    }


@router.get("/breakdown/by-seller")
async def breakdown_by_seller(
    days: int = Query(30, le=365),
    limit: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_finance_access()),
):
    """Топ селлеров по GMV."""
    start_dt = datetime.now(timezone.utc) - timedelta(days=days)
    q = (
        select(
            SellerOrder.seller_id,
            Seller.display_name,
            Seller.username,
            func.count(SellerOrder.id).label("orders"),
            func.coalesce(func.sum(SellerOrder.price_for_buyer), 0).label("gmv"),
            func.coalesce(func.sum(SellerOrder.price_for_seller), 0).label("seller_revenue"),
        )
        .outerjoin(Seller, Seller.id == SellerOrder.seller_id)
        .where(SellerOrder.created_at >= start_dt)
        .group_by(SellerOrder.seller_id, Seller.display_name, Seller.username)
        .order_by(text("gmv DESC"))
        .limit(limit)
    )
    rows = (await db.execute(q)).all()
    return {
        "data": [{
            "seller_id": r.seller_id,
            "name": r.display_name or r.username or f"#{r.seller_id}",
            "orders": r.orders,
            "gmv": float(r.gmv),
            "seller_revenue": float(r.seller_revenue),
            "margin": float(r.gmv - r.seller_revenue) if r.gmv else 0,
        } for r in rows],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# P2: Маркетплейс аналитика
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/marketplace")
async def marketplace_analytics(
    days: int = Query(30, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_finance_access()),
):
    """GMV, маржа, dispute rate, среднее время выдачи."""
    start_dt = datetime.now(timezone.utc) - timedelta(days=days)

    # GMV и маржа
    gmv_q = await db.execute(
        select(
            func.coalesce(func.sum(SellerOrder.price_for_buyer), 0).label("gmv"),
            func.coalesce(func.sum(SellerOrder.price_for_seller), 0).label("cogs"),
            func.count(SellerOrder.id).label("total_orders"),
        ).where(SellerOrder.created_at >= start_dt)
    )
    gmv_row = gmv_q.first()
    gmv = float(gmv_row.gmv)
    cogs = float(gmv_row.cogs)
    total_seller_orders = gmv_row.total_orders

    # Completed
    completed = await db.scalar(
        select(func.count(SellerOrder.id)).where(and_(
            SellerOrder.created_at >= start_dt,
            SellerOrder.status == "completed",
        ))
    ) or 0

    # Cancelled
    cancelled = await db.scalar(
        select(func.count(SellerOrder.id)).where(and_(
            SellerOrder.created_at >= start_dt,
            SellerOrder.status == "cancelled",
        ))
    ) or 0

    # Disputes
    disputes_count = await db.scalar(
        select(func.count(SellerOrderDispute.id)).where(
            SellerOrderDispute.created_at >= start_dt
        )
    ) or 0

    # Среднее время выдачи (completed orders: completed_at - created_at)
    avg_delivery_q = await db.execute(
        select(
            func.avg(
                extract("epoch", SellerOrder.completed_at) - extract("epoch", SellerOrder.created_at)
            ).label("avg_seconds")
        ).where(and_(
            SellerOrder.created_at >= start_dt,
            SellerOrder.status == "completed",
            SellerOrder.completed_at.isnot(None),
        ))
    )
    avg_delivery_seconds = avg_delivery_q.scalar() or 0
    avg_delivery_hours = round(avg_delivery_seconds / 3600, 1) if avg_delivery_seconds else 0

    dispute_rate = round(disputes_count / total_seller_orders * 100, 2) if total_seller_orders else 0
    cancel_rate = round(cancelled / total_seller_orders * 100, 2) if total_seller_orders else 0
    completion_rate = round(completed / total_seller_orders * 100, 2) if total_seller_orders else 0

    return {
        "period_days": days,
        "gmv": gmv,
        "cogs": cogs,
        "margin": gmv - cogs,
        "margin_percent": round((gmv - cogs) / gmv * 100, 2) if gmv else 0,
        "total_orders": total_seller_orders,
        "completed": completed,
        "cancelled": cancelled,
        "disputes": disputes_count,
        "dispute_rate": dispute_rate,
        "cancel_rate": cancel_rate,
        "completion_rate": completion_rate,
        "avg_delivery_hours": avg_delivery_hours,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# P2: Воронки и когорты
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/funnel")
async def conversion_funnel(
    days: int = Query(30, le=365),
    bot_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Воронка: регистрация → первый заказ → повторный заказ."""
    start_dt = datetime.now(timezone.utc) - timedelta(days=days)

    # Зарегистрированные
    reg_q = select(func.count(User.id)).where(User.created_at >= start_dt)
    if bot_id:
        reg_q = reg_q.where(User.mirror_bot_id == bot_id)
    registered = await db.scalar(reg_q) or 0

    # Сделали хотя бы 1 заказ
    first_order_subq = (
        select(Order.user_id)
        .where(Order.created_at >= start_dt)
    )
    if bot_id:
        first_order_subq = first_order_subq.where(Order.mirror_bot_id == bot_id)
    first_order_subq = first_order_subq.group_by(Order.user_id).subquery()

    with_order = await db.scalar(
        select(func.count()).select_from(first_order_subq)
    ) or 0

    # Сделали 2+ заказа
    repeat_subq = (
        select(Order.user_id)
        .where(Order.created_at >= start_dt)
    )
    if bot_id:
        repeat_subq = repeat_subq.where(Order.mirror_bot_id == bot_id)
    repeat_subq = (
        repeat_subq
        .group_by(Order.user_id)
        .having(func.count(Order.id) >= 2)
        .subquery()
    )
    repeat_buyers = await db.scalar(
        select(func.count()).select_from(repeat_subq)
    ) or 0

    return {
        "period_days": days,
        "registered": registered,
        "first_order": with_order,
        "repeat_order": repeat_buyers,
        "conversion_to_first": round(with_order / registered * 100, 2) if registered else 0,
        "conversion_to_repeat": round(repeat_buyers / with_order * 100, 2) if with_order else 0,
    }


@router.get("/cohorts")
async def weekly_cohorts(
    weeks: int = Query(8, le=24),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Недельные когорты: для каждой недели регистрации показываем
    % пользователей, сделавших заказ на неделе 0, 1, 2, ...
    """
    now = datetime.now(timezone.utc)
    start_dt = now - timedelta(weeks=weeks)

    # Получаем пользователей с неделей регистрации
    users_q = (
        select(
            User.user_id,
            extract("week", User.created_at).label("reg_week"),
            extract("year", User.created_at).label("reg_year"),
        )
        .where(User.created_at >= start_dt)
    )
    user_rows = (await db.execute(users_q)).all()

    if not user_rows:
        return {"weeks": weeks, "cohorts": []}

    user_ids = [r.user_id for r in user_rows]
    user_reg_week = {r.user_id: (int(r.reg_year), int(r.reg_week)) for r in user_rows}

    # Получаем заказы этих пользователей
    orders_q = (
        select(
            Order.user_id,
            extract("week", Order.created_at).label("order_week"),
            extract("year", Order.created_at).label("order_year"),
        )
        .where(Order.user_id.in_(user_ids), Order.created_at >= start_dt)
    )
    order_rows = (await db.execute(orders_q)).all()

    # Группируем по когортам
    from collections import defaultdict
    cohort_sizes: dict[tuple, int] = defaultdict(int)
    cohort_activity: dict[tuple, dict[int, set]] = defaultdict(lambda: defaultdict(set))

    for uid, (ry, rw) in user_reg_week.items():
        cohort_sizes[(ry, rw)] += 1

    for r in order_rows:
        uid = r.user_id
        if uid not in user_reg_week:
            continue
        ry, rw = user_reg_week[uid]
        ow, oy = int(r.order_week), int(r.order_year)
        week_diff = (oy - ry) * 52 + (ow - rw)
        if 0 <= week_diff < weeks:
            cohort_activity[(ry, rw)][week_diff].add(uid)

    cohorts = []
    for key in sorted(cohort_sizes.keys()):
        size = cohort_sizes[key]
        retention = {}
        for w in range(min(weeks, 12)):
            active = len(cohort_activity[key].get(w, set()))
            retention[f"week_{w}"] = round(active / size * 100, 1) if size else 0
        cohorts.append({
            "cohort": f"{key[0]}-W{key[1]:02d}",
            "size": size,
            **retention,
        })

    return {"weeks": weeks, "cohorts": cohorts[-weeks:]}
