"""
API для главной панели управления
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelt, timezone
from typing import Dict, Any, Optional

from web_panel.auth import get_current_user, can_view_finances
from web_panel.database import get_db
from shared.database.models import (
    User, Order, Transaction, MirrorBot, SupportTicket, ProductPurchase, Product, Worker,
    SellerBank, SellerCCItem,
    SellerWithdrawal, WorkerWithdrawal, BotOwnerWithdrawal, SellerOrderDispute
)

router = APIRouter()


def _resolve_date_range(
    date_from: Optional[str],
    date_to: Optional[str],
    default_days: int = 1,
):
    now = datetime.now(timezone.utc)

    if date_from:
        start_dt = datetime.strptime(date_from, "%Y-%m-%d")
    elif date_to:
        end_base = datetime.strptime(date_to, "%Y-%m-%d")
        start_dt = end_base - timedelta(days=max(default_days - 1, 0))
    else:
        start_dt = now - timedelta(days=default_days)

    if date_to:
        end_dt = datetime.strptime(date_to, "%Y-%m-%d") + timedelta(days=1)
    else:
        end_dt = now + timedelta(seconds=1)

    return start_dt, end_dt


@router.get("/stats")
async def get_dashboard_stats(
    date_from: Optional[str] = Query(None, description="Дата начала YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="Дата окончания YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Получить основную статистику для дашборда"""
    start_dt, end_dt = _resolve_date_range(date_from, date_to, default_days=1)
    finance_visible = can_view_finances(current_user)

    # Общее количество пользователей
    users_result = await db.execute(select(func.count(User.id)))
    total_users = users_result.scalar() or 0
    
    # Пользователи за диапазон
    new_users_result = await db.execute(
        select(func.count(User.id)).where(User.created_at >= start_dt, User.created_at < end_dt)
    )
    users_in_range = new_users_result.scalar() or 0
    
    # Общее количество заказов
    orders_result = await db.execute(select(func.count(Order.id)))
    total_orders = orders_result.scalar() or 0
    
    # Заказы за диапазон
    new_orders_result = await db.execute(
        select(func.count(Order.id)).where(Order.created_at >= start_dt, Order.created_at < end_dt)
    )
    orders_in_range = new_orders_result.scalar() or 0
    
    # Заказы по статусам
    pending_orders_result = await db.execute(
        select(func.count(Order.id)).where(Order.status == "pending")
    )
    pending_orders = pending_orders_result.scalar() or 0
    
    processing_orders_result = await db.execute(
        select(func.count(Order.id)).where(Order.status == "processing")
    )
    processing_orders = processing_orders_result.scalar() or 0
    
    completed_orders_result = await db.execute(
        select(func.count(Order.id)).where(Order.status == "completed")
    )
    completed_orders = completed_orders_result.scalar() or 0
    
    # Общая сумма заказов
    total_revenue_result = await db.execute(
        select(func.sum(Order.price)).where(Order.status == "completed")
    )
    total_revenue = float(total_revenue_result.scalar() or 0)

    # Доход от товаров
    product_revenue_result = await db.execute(
        select(func.sum(Product.price))
        .join(ProductPurchase, ProductPurchase.product_id == Product.id)
    )
    product_revenue = float(product_revenue_result.scalar() or 0)

    # Покупки товаров за диапазон
    product_purchases_24h_result = await db.execute(
        select(func.count(ProductPurchase.id)).where(
            ProductPurchase.purchased_at >= start_dt,
            ProductPurchase.purchased_at < end_dt,
        )
    )
    product_purchases_in_range = product_purchases_24h_result.scalar() or 0

    # Доход от товаров за диапазон
    product_revenue_24h_result = await db.execute(
        select(func.sum(Product.price))
        .join(ProductPurchase, ProductPurchase.product_id == Product.id)
        .where(ProductPurchase.purchased_at >= start_dt, ProductPurchase.purchased_at < end_dt)
    )
    product_revenue_in_range = float(product_revenue_24h_result.scalar() or 0)
    
    # Доход за диапазон
    revenue_24h_result = await db.execute(
        select(func.sum(Order.price)).where(
            Order.status == "completed",
            Order.completed_at >= start_dt,
            Order.completed_at < end_dt,
        )
    )
    revenue_in_range = float(revenue_24h_result.scalar() or 0)
    
    # Открытые тикеты поддержки
    open_tickets_result = await db.execute(
        select(func.count(SupportTicket.id)).where(SupportTicket.status == "open")
    )
    open_tickets = open_tickets_result.scalar() or 0
    
    # Активные боты
    active_bots_result = await db.execute(
        select(func.count(MirrorBot.id)).where(MirrorBot.is_active == True)
    )
    active_bots = active_bots_result.scalar() or 0
    
    # Общий баланс всех пользователей
    total_balance_result = await db.execute(
        select(func.sum(User.balance))
    )
    total_balance = float(total_balance_result.scalar() or 0)
    
    # Количество активных воркеров
    total_workers_result = await db.execute(
        select(func.count(Worker.id)).where(Worker.is_active == True)
    )
    total_workers = total_workers_result.scalar() or 0
    
    # Pending moderation items
    pending_banks = (await db.execute(select(func.count(SellerBank.id)).where(SellerBank.moderation_status == "pending_moderation"))).scalar() or 0
    pending_cc = (await db.execute(select(func.count(SellerCCItem.id)).where(SellerCCItem.moderation_status == "pending_moderation"))).scalar() or 0
    # Models NFCItem, OTPItem, SelfregCCItem, CheckItem don't exist - using 0
    pending_nfc = 0
    pending_otp = 0
    pending_selfreg_cc = 0
    pending_checks = 0
    total_pending_moderation = pending_banks + pending_cc + pending_nfc + pending_otp + pending_selfreg_cc + pending_checks
    
    # Open disputes (using SellerOrderDispute model)
    open_disputes_result = await db.execute(
        select(func.count(SellerOrderDispute.id)).where(SellerOrderDispute.status.in_(["open", "in_moderation", "waiting_for_seller_response", "waiting_for_buyer_response", "appealed"]))
    )
    open_disputes = open_disputes_result.scalar() or 0
    
    # Pending withdrawals
    pending_seller_wd = (await db.execute(select(func.count(SellerWithdrawal.id)).where(SellerWithdrawal.status == "pending"))).scalar() or 0
    pending_worker_wd = (await db.execute(select(func.count(WorkerWithdrawal.id)).where(WorkerWithdrawal.status == "pending"))).scalar() or 0
    pending_owner_wd = (await db.execute(select(func.count(BotOwnerWithdrawal.id)).where(BotOwnerWithdrawal.status == "pending"))).scalar() or 0
    total_pending_withdrawals = pending_seller_wd + pending_worker_wd + pending_owner_wd
    
    data = {
        "total_users": total_users,
        "new_users_24h": users_in_range,
        "total_balance": total_balance if finance_visible else None,
        "active_bots": active_bots,
        "total_orders": total_orders,
        "new_orders_24h": orders_in_range,
        "pending_orders": pending_orders,
        "processing_orders": processing_orders,
        "completed_orders": completed_orders,
        "total_revenue": (total_revenue + product_revenue) if finance_visible else None,
        "revenue_24h": (revenue_in_range + product_revenue_in_range) if finance_visible else None,
        "product_purchases_24h": product_purchases_in_range,
        "product_revenue": product_revenue if finance_visible else None,
        "total_workers": total_workers,
        "open_tickets": open_tickets,
        "period": {
            "date_from": start_dt.strftime("%Y-%m-%d"),
            "date_to": (end_dt - timedelta(days=1)).strftime("%Y-%m-%d"),
        },
        "users": {
            "total": total_users,
            "new_24h": users_in_range,
        },
        "orders": {
            "total": total_orders,
            "new_24h": orders_in_range,
            "pending": pending_orders,
            "processing": processing_orders,
            "completed": completed_orders,
        },
        "revenue": {
            "total": total_revenue if finance_visible else None,
            "last_24h": revenue_in_range if finance_visible else None,
        },
        "support": {
            "open_tickets": open_tickets,
        },
        "bots": {
            "active": active_bots,
        },
        "moderation": {
            "pending_total": total_pending_moderation,
            "pending_banks": pending_banks,
            "pending_cc": pending_cc,
            "pending_nfc": pending_nfc,
            "pending_otp": pending_otp,
            "pending_selfreg_cc": pending_selfreg_cc,
            "pending_checks": pending_checks,
        },
        "disputes": {
            "open": open_disputes,
        },
        "withdrawals": {
            "pending_total": total_pending_withdrawals,
            "pending_sellers": pending_seller_wd,
            "pending_workers": pending_worker_wd,
            "pending_owners": pending_owner_wd,
        },
        "finance_visible": finance_visible,
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }
    return data


@router.get("/recent-orders")
async def get_recent_orders(
    limit: int = 10,
    date_from: Optional[str] = Query(None, description="Дата начала YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="Дата окончания YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Получить последние заказы"""
    start_dt, end_dt = _resolve_date_range(date_from, date_to, default_days=30)

    stmt = (
        select(Order)
        .where(Order.created_at >= start_dt, Order.created_at < end_dt)
        .order_by(Order.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    orders = result.scalars().all()
    
    return [
        {
            "id": order.id,
            "user_id": order.user_id,
            "category": order.category,
            "service_name": order.service_name,
            "price": float(order.price),
            "status": order.status,
            "created_at": order.created_at,
            "completed_at": order.completed_at
        }
        for order in orders
    ]


@router.get("/recent-users")
async def get_recent_users(
    limit: int = 10,
    date_from: Optional[str] = Query(None, description="Дата начала YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="Дата окончания YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Получить последних пользователей"""
    start_dt, end_dt = _resolve_date_range(date_from, date_to, default_days=30)

    stmt = (
        select(User)
        .where(User.created_at >= start_dt, User.created_at < end_dt)
        .order_by(User.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    users = result.scalars().all()
    
    return [
        {
            "id": user.id,
            "user_id": user.user_id,
            "balance": float(user.balance),
            "language": user.language,
            "is_banned": user.is_banned,
            "created_at": user.created_at
        }
        for user in users
    ]
