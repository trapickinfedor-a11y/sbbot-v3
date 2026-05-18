#!/usr/bin/env python3
"""
Script to identify and fix hanging orders that weren't properly notified to workers
"""

import asyncio
import logging
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.session import async_session_maker
from shared.database.models import Order
from shared.services.order_notification_service import OrderNotificationService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def find_hanging_orders(session: AsyncSession, hours_old: int = 1) -> list[Order]:
    """
    Find orders that are pending for more than specified hours
    
    Args:
        session: Database session
        hours_old: Minimum age in hours for orders to be considered hanging
        
    Returns:
        List of hanging orders
    """
    cutoff_time = datetime.utcnow() - timedelta(hours=hours_old)
    
    result = await session.execute(
        select(Order).where(
            Order.status == "pending",
            Order.created_at < cutoff_time,
            Order.worker_id.is_(None)
        ).order_by(Order.created_at.asc())
    )
    
    return list(result.scalars().all())


async def re_notify_order(order: Order) -> bool:
    """
    Re-send notification for a hanging order
    
    Args:
        order: Order to re-notify
        
    Returns:
        Success status
    """
    try:
        # Подготавливаем данные заказа
        order_data = {
            "id": order.id,
            "user_id": order.user_id,
            "mirror_bot_id": order.mirror_bot_id,
            "category": order.category,
            "service_name": order.service_name,
            "price": float(order.price),
            "is_bulk": order.is_bulk,
            "bulk_count": order.bulk_count,
            "created_at": order.created_at.isoformat(),
            "input_data": order.input_data or {}
        }
        
        # Отправляем уведомление
        success = await OrderNotificationService.notify_new_order(order_data)
        
        if success:
            logger.info(f"✅ Successfully re-notified order #{order.id}")
        else:
            logger.error(f"❌ Failed to re-notify order #{order.id}")
        
        return success
        
    except Exception as e:
        logger.error(f"❌ Error re-notifying order #{order.id}: {e}")
        return False


async def main():
    """Main function to find and fix hanging orders"""
    
    logger.info("🔍 Searching for hanging orders...")
    
    async with async_session_maker() as session:
        # Find orders hanging for more than 1 hour
        hanging_orders = await find_hanging_orders(session, hours_old=1)
        
        if not hanging_orders:
            logger.info("✅ No hanging orders found!")
            return
        
        logger.info(f"📋 Found {len(hanging_orders)} hanging orders:")
        
        for order in hanging_orders:
            age_hours = (datetime.utcnow() - order.created_at).total_seconds() / 3600
            logger.info(f"  - Order #{order.id}: {order.category}/{order.service_name} (age: {age_hours:.1f}h)")
        
        # Ask for confirmation
        print(f"\n🤔 Re-notify workers about {len(hanging_orders)} hanging orders? (y/N): ", end="")
        confirm = input().strip().lower()
        
        if confirm != 'y':
            logger.info("❌ Cancelled by user")
            return
        
        # Re-notify each order
        success_count = 0
        for order in hanging_orders:
            logger.info(f"🔄 Re-notifying order #{order.id}...")
            if await re_notify_order(order):
                success_count += 1
            
            # Small delay between notifications
            await asyncio.sleep(0.5)
        
        logger.info(f"✅ Re-notification complete: {success_count}/{len(hanging_orders)} successful")


if __name__ == "__main__":
    asyncio.run(main())
