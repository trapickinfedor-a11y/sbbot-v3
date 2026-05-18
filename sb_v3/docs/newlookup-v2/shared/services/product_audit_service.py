from __future__ import annotations

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import ProductActionLog
from shared.services.admin_notification_service import AdminNotificationService
from shared.services.nocodb_service import NocoDBService
from shared.services.product_catalog_service import ProductCatalogManager


STALE_PRODUCT_DAYS = 14


async def log_product_action(
    session: AsyncSession,
    *,
    action: str,
    actor_type: str,
    actor_id: Optional[int] = None,
    product=None,
    details: Optional[dict] = None,
    notify_if_stale: bool = False,
) -> ProductActionLog:
    age_days = ProductCatalogManager.compute_age_days(getattr(product, "created_at", None))
    entry = ProductActionLog(
        product_id=getattr(product, "id", None),
        actor_type=actor_type,
        actor_id=actor_id,
        action=action,
        product_age_days=age_days,
        details=details or {},
    )
    session.add(entry)
    await session.commit()
    await session.refresh(entry)

    file_action_map = {
        "create": "add",
        "upload": "add",
        "delete": "delete",
        "download": "view",
        "view": "view",
    }
    mapped_action = file_action_map.get(action)
    if mapped_action and product:
        NocoDBService.log_file_operation(
            user_id=actor_id,
            action=mapped_action,
            file_id=product.id,
            category=getattr(product, "category", None),
            timestamp=getattr(entry, "created_at", None),
            extra={
                "actor_type": actor_type,
                "product_name": getattr(product, "name", None),
                "service": getattr(product, "service", None),
                "state": getattr(product, "state", None),
                "details": details or {},
                "source_action": action,
            },
        )

    if notify_if_stale and product and age_days is not None and age_days >= STALE_PRODUCT_DAYS:
        await AdminNotificationService.notify_admin_action(
            title="STALE PRODUCT ACTION",
            lines=[
                f"📦 <b>Product:</b> #{product.id} {product.name}",
                f"🎯 <b>Action:</b> {action}",
                f"👤 <b>Actor:</b> {actor_type}:{actor_id or 'n/a'}",
                f"📂 <b>Section:</b> {product.category}/{product.service}/{product.state}",
                f"🕒 <b>Age:</b> {age_days} days",
            ],
            event_type="stale_product_action",
            urgent=True,
        )

    return entry
