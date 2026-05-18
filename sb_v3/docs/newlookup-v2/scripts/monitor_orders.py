#!/usr/bin/env python3
"""
Monitoring script to check for hanging orders and alert administrators
"""

import asyncio
import logging
from datetime import datetime, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.session import async_session_maker
from shared.database.models import Order

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def get_order_statistics(session: AsyncSession) -> dict:
    """Get comprehensive order statistics"""
    
    # Total orders by status
    result = await session.execute(
        select(Order.status, func.count(Order.id)).group_by(Order.status)
    )
    status_counts = dict(result.fetchall())
    
    # Orders created in last 24 hours
    yesterday = datetime.utcnow() - timedelta(hours=24)
    result = await session.execute(
        select(func.count(Order.id)).where(Order.created_at >= yesterday)
    )
    orders_24h = result.scalar()
    
    # Hanging orders (pending > 1 hour)
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    result = await session.execute(
        select(func.count(Order.id)).where(
            Order.status == "pending",
            Order.created_at < one_hour_ago,
            Order.worker_id.is_(None)
        )
    )
    hanging_orders = result.scalar()
    
    # Orders by category (last 24h)
    result = await session.execute(
        select(Order.category, func.count(Order.id))
        .where(Order.created_at >= yesterday)
        .group_by(Order.category)
    )
    category_counts = dict(result.fetchall())
    
    return {
        "status_counts": status_counts,
        "orders_24h": orders_24h,
        "hanging_orders": hanging_orders,
        "category_counts": category_counts
    }


async def get_hanging_orders_details(session: AsyncSession) -> list[dict]:
    """Get detailed information about hanging orders"""
    
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    
    result = await session.execute(
        select(Order).where(
            Order.status == "pending",
            Order.created_at < one_hour_ago,
            Order.worker_id.is_(None)
        ).order_by(Order.created_at.asc())
    )
    
    hanging_orders = result.scalars().all()
    
    details = []
    for order in hanging_orders:
        age_hours = (datetime.utcnow() - order.created_at).total_seconds() / 3600
        details.append({
            "id": order.id,
            "category": order.category,
            "service_name": order.service_name,
            "user_id": order.user_id,
            "price": float(order.price),
            "age_hours": round(age_hours, 1),
            "created_at": order.created_at.isoformat(),
            "is_bulk": order.is_bulk,
            "bulk_count": order.bulk_count
        })
    
    return details


async def main():
    """Main monitoring function"""
    
    logger.info("📊 Generating order monitoring report...")
    
    async with async_session_maker() as session:
        # Get statistics
        stats = await get_order_statistics(session)
        hanging_details = await get_hanging_orders_details(session)
        
        # Print report
        print("\n" + "="*60)
        print("📋 ORDER MONITORING REPORT")
        print("="*60)
        print(f"📅 Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
        print()
        
        # Status overview
        print("📊 ORDER STATUS OVERVIEW:")
        for status, count in stats["status_counts"].items():
            print(f"  {status.upper()}: {count}")
        print()
        
        # 24h activity
        print(f"📈 ORDERS IN LAST 24H: {stats['orders_24h']}")
        print()
        
        # Category breakdown
        if stats["category_counts"]:
            print("📦 ORDERS BY CATEGORY (24h):")
            for category, count in stats["category_counts"].items():
                print(f"  {category}: {count}")
            print()
        
        # Hanging orders alert
        hanging_count = stats["hanging_orders"]
        if hanging_count > 0:
            print(f"🚨 ALERT: {hanging_count} HANGING ORDERS DETECTED!")
            print("   These orders are pending for more than 1 hour:")
            print()
            
            for order in hanging_details:
                print(f"   Order #{order['id']}: {order['category']}/{order['service_name']}")
                print(f"     User: {order['user_id']}, Price: ${order['price']}")
                print(f"     Age: {order['age_hours']}h, Created: {order['created_at']}")
                if order['is_bulk']:
                    print(f"     Bulk order: {order['bulk_count']} items")
                print()
            
            print("🔧 To fix hanging orders, run:")
            print("   python scripts/fix_hanging_orders.py")
            print()
        else:
            print("✅ NO HANGING ORDERS DETECTED")
            print()
        
        print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
