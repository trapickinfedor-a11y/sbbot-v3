"""
API для управления заказами
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelt, timezone

from web_panel.auth import require_orders_access
from web_panel.database import get_db
from shared.database.models import Order, BulkOrderItem, User
from aiogram import Bot
from web_panel.config import web_panel_config
from web_panel.services.bot_integration import bot_integration

router = APIRouter()


def calculate_order_income(order: Order, bulk_items: Optional[List[BulkOrderItem]] = None) -> float:
    """
    Рассчитать реальный доход от заказа с учетом NF элементов

    Args:
        order: Заказ
        bulk_items: Список bulk элементов (если None, будет загружен из order.bulk_items)

    Returns:
        float: Реальный доход
    """
    # Для single заказов возвращаем полную цену
    if not order.is_bulk:
        return float(order.price)

    # Для bulk заказов рассчитываем на основе выполненных элементов
    if bulk_items is None:
        bulk_items = order.bulk_items if hasattr(order, 'bulk_items') else []

    if not bulk_items:
        # Если нет данных о bulk элементах, возвращаем полную цену
        return float(order.price)

    # Подсчитываем выполненные элементы (status = 'done')
    done_count = sum(1 for item in bulk_items if item.status == 'done')

    # Если нет выполненных элементов, доход = 0
    if done_count == 0:
        return 0.0

    # Рассчитываем цену за элемент и умножаем на количество выполненных
    price_per_item = float(order.price) / order.bulk_count
    return price_per_item * done_count


class OrderUpdate(BaseModel):
    status: Optional[str] = None
    worker_id: Optional[int] = None
    result_data: Optional[dict] = None


@router.get("/")
async def get_orders(
    status: Optional[str] = None,
    category: Optional[str] = None,
    worker_id: Optional[int] = None,
    user_id: Optional[int] = None,
    search: Optional[str] = None,
    seller_id: Optional[int] = None,
    product_type: Optional[str] = None,
    page: int = 1,
    per_page: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_orders_access())
):
    """Получить список заказов с пагинацией и поиском"""
    limit = per_page
    offset = (page - 1) * per_page

    # Базовый запрос для подсчета общего количества
    count_stmt = select(func.count(Order.id))
    
    conditions = []
    if status:
        conditions.append(Order.status == status)
    if category:
        conditions.append(Order.category == category)
    if worker_id:
        conditions.append(Order.worker_id == worker_id)
    if user_id:
        conditions.append(Order.user_id == user_id)
    if seller_id:
        conditions.append(Order.seller_id == seller_id)
    if product_type:
        conditions.append(Order.category == product_type)
    
    # Search by order ID or user_id
    if search:
        search_term = search.strip()
        if search_term.isdigit():
            # Search by order ID or user ID
            search_conditions = or_(
                Order.id == int(search_term),
                Order.user_id == int(search_term)
            )
            conditions.append(search_conditions)
        else:
            # Search by service name or category
            search_conditions = or_(
                Order.service_name.ilike(f'%{search_term}%'),
                Order.category.ilike(f'%{search_term}%')
            )
            conditions.append(search_conditions)
    
    if conditions:
        count_stmt = count_stmt.where(and_(*conditions))

    # Получаем общее количество
    total_count_result = await db.execute(count_stmt)
    total = total_count_result.scalar() or 0

    # Запрос для получения данных с пагинацией
    stmt = select(Order)
    
    if conditions:
        stmt = stmt.where(and_(*conditions))

    stmt = stmt.order_by(Order.created_at.desc()).limit(limit).offset(offset)

    result = await db.execute(stmt)
    orders = result.scalars().all()

    # Формируем результаты с расчетом дохода
    items = []
    for order in orders:
        # Для bulk заказов загружаем элементы для расчета дохода
        bulk_items = []
        if order.is_bulk:
            bulk_items_stmt = select(BulkOrderItem).where(BulkOrderItem.order_id == order.id)
            bulk_items_result = await db.execute(bulk_items_stmt)
            bulk_items = bulk_items_result.scalars().all()

        # Рассчитываем доход
        income = calculate_order_income(order, bulk_items)

        # Для bulk заказов также показываем статистику
        done_count = 0
        nf_count = 0
        if order.is_bulk and bulk_items:
            done_count = sum(1 for item in bulk_items if item.status == 'done')
            nf_count = sum(1 for item in bulk_items if item.status == 'nf')

        items.append({
            "id": order.id,
            "user_id": order.user_id,
            "category": order.category,
            "service_name": order.service_name,
            "price": float(order.price),
            "income": income,  # Реальный доход с учетом NF
            "status": order.status,
            "is_bulk": order.is_bulk,
            "bulk_count": order.bulk_count,
            "done_count": done_count if order.is_bulk else None,
            "nf_count": nf_count if order.is_bulk else None,
            "worker_id": order.worker_id,
            "created_at": order.created_at,
            "completed_at": order.completed_at
        })

    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": max(1, (total + per_page - 1) // per_page),
        "items": items
    }


@router.get("/{order_id}")
async def get_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_orders_access())
):
    """Получить детали заказа"""
    
    stmt = select(Order).where(Order.id == order_id)
    result = await db.execute(stmt)
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    bulk_items = []
    if order.is_bulk:
        stmt = select(BulkOrderItem).where(BulkOrderItem.order_id == order_id)
        result = await db.execute(stmt)
        bulk_items = [
            {
                "item_number": item.item_number,
                "status": item.status,
                "input_data": item.input_data,
                "result_data": item.result_data,
                "completed_at": item.completed_at
            }
            for item in result.scalars().all()
        ]
    
    return {
        "id": order.id,
        "user_id": order.user_id,
        "mirror_bot_id": order.mirror_bot_id,
        "category": order.category,
        "service_name": order.service_name,
        "input_data": order.input_data,
        "price": float(order.price),
        "status": order.status,
        "is_bulk": order.is_bulk,
        "bulk_count": order.bulk_count,
        "worker_id": order.worker_id,
        "result_data": order.result_data,
        "files": order.files,
        "created_at": order.created_at,
        "taken_at": order.taken_at,
        "completed_at": order.completed_at,
        "bulk_items": bulk_items
    }


@router.post("/{order_id}/force-complete")
async def force_complete_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_orders_access())
):
    """Принудительно завершить застрявший заказ"""
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.status == "completed":
        raise HTTPException(status_code=400, detail="Order already completed")
    
    order.status = "completed"
    order.completed_at = datetime.now(timezone.utc)
    
    await db.commit()
    
    return {"ok": True, "message": "Order force-completed successfully"}


@router.post("/{order_id}/force-cancel")
async def force_cancel_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_orders_access())
):
    """Принудительно отменить застрявший заказ"""
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.status in ["completed", "cancelled"]:
        raise HTTPException(status_code=400, detail=f"Order already {order.status}")
    
    order.status = "cancelled"
    order.completed_at = datetime.now(timezone.utc)
    
    await db.commit()
    
    return {"ok": True, "message": "Order force-cancelled successfully"}


@router.put("/{order_id}")
async def update_order(
    order_id: int,
    data: OrderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_orders_access())
):
    """Обновить заказ"""
    
    stmt = select(Order).where(Order.id == order_id)
    result = await db.execute(stmt)
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Обновляем поля
    if data.status is not None:
        valid_statuses = ["pending", "processing", "completed", "cancelled"]
        if data.status not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
        
        order.status = data.status
        
        if data.status == "completed":
            order.completed_at = datetime.now(timezone.utc)
    
    if data.worker_id is not None:
        order.worker_id = data.worker_id
        if order.status == "pending":
            order.status = "processing"
            order.taken_at = datetime.now(timezone.utc)
    
    if data.result_data is not None:
        order.result_data = data.result_data
    
    await db.commit()
    await db.refresh(order)
    
    # Уведомляем support bot об обновлении заказа
    try:
        await bot_integration.notify_support_order_update(
            order_id=order_id,
            status=order.status,
            worker_id=order.worker_id,
            result_data=order.result_data
        )
    except Exception as e:
        # Логируем ошибку, но не прерываем операцию
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to notify support bot about order update: {e}")
    
    return {
        "message": "Order updated successfully",
        "order_id": order_id,
        "status": order.status
    }


@router.post("/send-to-channel")
async def send_order_to_channel(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_orders_access())
):
    """Публичная отправка заказов в каналы отключена."""
    raise HTTPException(status_code=403, detail="Channel notifications are disabled; use direct bot notifications instead")


@router.get("/stats/by-category")
async def get_orders_by_category(
    period_days: int = 30,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_orders_access())
):
    """Получить статистику заказов по категориям"""
    
    start_date = datetime.now(timezone.utc) - timedelta(days=period_days)
    
    stmt = select(
        Order.category,
        func.count(Order.id).label("total"),
        func.sum(func.case((Order.status == "completed", 1), else_=0)).label("completed"),
        func.sum(Order.price).label("revenue")
    ).where(
        Order.created_at >= start_date
    ).group_by(Order.category)
    
    result = await db.execute(stmt)
    stats = result.all()
    
    return [
        {
            "category": row.category,
            "total_orders": row.total,
            "completed_orders": row.completed,
            "revenue": float(row.revenue or 0)
        }
        for row in stats
    ]

