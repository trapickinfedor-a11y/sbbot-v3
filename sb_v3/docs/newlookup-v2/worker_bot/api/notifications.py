"""
API для получения уведомлений о заказах воркера
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.session import async_session_maker
from shared.security.internal_api import verify_internal_api_request
from shared.database.models import Order
from support_bot.services.order_notification_service import OrderNotificationService
from support_bot.services.worker_notification_service import WorkerNotificationService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/notifications",
    tags=["notifications"],
    dependencies=[Depends(verify_internal_api_request)],
)


class OrderNotificationData(BaseModel):
    """Данные заказа для уведомления"""

    id: int
    user_id: int
    mirror_bot_id: int
    category: str
    service_name: str
    price: float
    is_bulk: bool = False
    bulk_count: Optional[int] = None
    created_at: str
    input_data: Dict[str, Any] = {}


class ComplaintResolutionData(BaseModel):
    """Данные о решении жалобы"""

    complaint_id: int
    worker_telegram_id: int
    status: str
    admin_response: str
    action: Optional[str] = None


async def get_db():
    """Получить сессию БД"""
    async with async_session_maker() as session:
        yield session


@router.post("/new-order")
async def notify_new_order(
    order_data: OrderNotificationData,
    session: AsyncSession = Depends(get_db),
):
    """Получить уведомление о новом заказе и разослать его воркерам"""
    try:
        logger.info("Received new worker order notification: %s", order_data.id)

        temp_order = Order(
            id=order_data.id,
            user_id=order_data.user_id,
            mirror_bot_id=order_data.mirror_bot_id,
            category=order_data.category,
            service_name=order_data.service_name,
            price=order_data.price,
            is_bulk=order_data.is_bulk,
            bulk_count=order_data.bulk_count,
            created_at=datetime.fromisoformat(order_data.created_at.replace("Z", "+00:00")),
            input_data=order_data.input_data,
            status="pending",
        )

        success = await OrderNotificationService.notify_workers_about_new_order(
            session, temp_order
        )

        if success:
            return {"status": "success", "message": "Workers notified"}
        return {"status": "warning", "message": "No workers to notify"}

    except Exception as exc:
        logger.error("Failed to process new worker order notification: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/order-to-channel")
async def send_order_to_channel(order_data: OrderNotificationData):
    """Публичная отправка заказов в каналы отключена."""
    logger.info(
        "Skipping order-to-channel for order %s: DM-only notifications enabled",
        order_data.id,
    )
    return {"status": "disabled", "message": "Channel notifications are disabled"}


@router.post("/complaint-resolved")
async def notify_complaint_resolved(complaint_data: ComplaintResolutionData):
    """Уведомить воркера о решении жалобы"""
    try:
        logger.info(
            "Notifying worker about complaint resolution: %s",
            complaint_data.complaint_id,
        )
        await WorkerNotificationService.notify_complaint_resolved(
            worker_telegram_id=complaint_data.worker_telegram_id,
            complaint_id=complaint_data.complaint_id,
            status=complaint_data.status,
            admin_response=complaint_data.admin_response,
            action=complaint_data.action,
        )
        return {
            "status": "success",
            "message": "Worker notified about complaint resolution",
        }
    except Exception as exc:
        logger.error("Failed to notify worker about complaint resolution: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
