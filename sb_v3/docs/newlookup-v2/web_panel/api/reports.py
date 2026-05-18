"""
API для отчетов
"""

from datetime import datetime, timedelt, timezone
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from web_panel.auth import get_current_user
from web_panel.database import get_db
from shared.database.models import User, Order, MirrorBot

router = APIRouter()


def _resolve_date_range(
    start_date: Optional[str],
    end_date: Optional[str],
    period_days: int = 30,
):
    now = datetime.now(timezone.utc)

    if start_date:
        start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
    elif end_date:
        end_base = datetime.strptime(end_date, "%Y-%m-%d")
        start_datetime = end_base - timedelta(days=max(period_days - 1, 0))
    else:
        start_datetime = now - timedelta(days=period_days)

    if end_date:
        end_datetime = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
    else:
        end_datetime = now + timedelta(seconds=1)

    return start_datetime, end_datetime


@router.get("/revenue")
async def get_revenue_report(
    period_days: int = Query(30, description="Период в днях, если даты не заданы"),
    start_date: Optional[str] = Query(None, description="Дата начала (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Дата окончания (YYYY-MM-DD)"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Отчет по доходам
    """
    
    start_datetime, end_datetime = _resolve_date_range(start_date, end_date, period_days)
    
    # Общий доход
    total_revenue_result = await db.execute(
        select(func.sum(Order.price)).where(
            and_(
                Order.created_at >= start_datetime,
                Order.created_at < end_datetime,
                Order.status == 'completed'
            )
        )
    )
    total_revenue = float(total_revenue_result.scalar() or 0)
    
    # Количество заказов
    total_orders_result = await db.execute(
        select(func.count(Order.id)).where(
            and_(
                Order.created_at >= start_datetime,
                Order.created_at < end_datetime
            )
        )
    )
    total_orders = total_orders_result.scalar() or 0
    
    # Средний чек
    avg_order_value = total_revenue / total_orders if total_orders > 0 else 0
    
    return {
        "period": {
            "start_date": start_datetime.strftime("%Y-%m-%d"),
            "end_date": (end_datetime - timedelta(days=1)).strftime("%Y-%m-%d")
        },
        "total_revenue": total_revenue,
        "total_orders": total_orders,
        "avg_order_value": avg_order_value
    }


@router.get("/users")
async def get_users_report(
    period_days: int = Query(30, description="Период в днях, если даты не заданы"),
    start_date: Optional[str] = Query(None, description="Дата начала (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Дата окончания (YYYY-MM-DD)"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Отчет по пользователям
    """
    
    start_datetime, end_datetime = _resolve_date_range(start_date, end_date, period_days)
    
    # Новые пользователи
    new_users_result = await db.execute(
        select(func.count(User.id)).where(
            and_(
                User.created_at >= start_datetime,
                User.created_at < end_datetime
            )
        )
    )
    new_users = new_users_result.scalar() or 0
    
    # Общий баланс новых пользователей
    new_users_balance_result = await db.execute(
        select(func.sum(User.balance)).where(
            and_(
                User.created_at >= start_datetime,
                User.created_at < end_datetime
            )
        )
    )
    new_users_balance = float(new_users_balance_result.scalar() or 0)
    
    # Всего пользователей
    total_users_result = await db.execute(
        select(func.count(User.id))
    )
    total_users = total_users_result.scalar() or 0
    
    return {
        "period": {
            "start_date": start_datetime.strftime("%Y-%m-%d"),
            "end_date": (end_datetime - timedelta(days=1)).strftime("%Y-%m-%d")
        },
        "new_users": new_users,
        "new_users_balance": new_users_balance,
        "total_users": total_users
    }


@router.get("/bots")
async def get_bots_report(
    period_days: int = Query(30, description="Период в днях, если даты не заданы"),
    start_date: Optional[str] = Query(None, description="Дата начала (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Дата окончания (YYYY-MM-DD)"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Отчет по ботам
    """
    
    start_datetime, end_datetime = _resolve_date_range(start_date, end_date, period_days)

    # Статистика по ботам
    bots_result = await db.execute(
        select(
            MirrorBot.bot_username,
            MirrorBot.is_active,
            func.count(Order.id).label('orders_count'),
            func.sum(Order.price).label('revenue')
        )
        .outerjoin(
            Order,
            and_(
                Order.mirror_bot_id == MirrorBot.id,
                Order.created_at >= start_datetime,
                Order.created_at < end_datetime,
            )
        )
        .group_by(MirrorBot.id, MirrorBot.bot_username, MirrorBot.is_active)
    )
    
    bots_stats = []
    for bot_username, is_active, orders_count, revenue in bots_result.fetchall():
        bots_stats.append({
            "name": bot_username or "—",
            "is_active": is_active,
            "orders_count": orders_count or 0,
            "revenue": float(revenue or 0)
        })
    
    # Общая статистика
    total_bots = len(bots_stats)
    active_bots = sum(1 for bot in bots_stats if bot["is_active"])
    total_bot_revenue = sum(bot["revenue"] for bot in bots_stats)
    
    return {
        "period": {
            "start_date": start_datetime.strftime("%Y-%m-%d"),
            "end_date": (end_datetime - timedelta(days=1)).strftime("%Y-%m-%d")
        },
        "total_bots": total_bots,
        "active_bots": active_bots,
        "total_revenue": total_bot_revenue,
        "bots": bots_stats
    }