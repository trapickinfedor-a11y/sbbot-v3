"""
API для управления типами заказов и ETA по категориям сервисов (Mirror Bot).

Позволяет админу:
- Устанавливать order_type (order / order_catalog / catalog) для каждого сервиса
- Устанавливать eta_minutes для каждого сервиса
- Управлять service_link (ссылка на сервис, только для order и order_catalog)
"""
from __future__ import annotations

import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from web_panel.auth import get_current_user, has_any_role
from web_panel.database import get_db
from shared.database.models import ServicePrice

logger = logging.getLogger(__name__)

router = APIRouter()

ORDER_TYPE_ORDER = "order"
ORDER_TYPE_ORDER_CATALOG = "order_catalog"
ORDER_TYPE_CATALOG = "catalog"
VALID_ORDER_TYPES = {ORDER_TYPE_ORDER, ORDER_TYPE_ORDER_CATALOG, ORDER_TYPE_CATALOG}

ORDER_TYPE_LABELS = {
    ORDER_TYPE_ORDER: "⚡ Order (Real-time)",
    ORDER_TYPE_ORDER_CATALOG: "📦 Order+Catalog",
    ORDER_TYPE_CATALOG: "📂 Catalog",
}


def _ensure_admin(current_user: dict) -> None:
    if not has_any_role(current_user, "admin", "owner", "super_admin"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")


class ServiceOrderConfigUpdate(BaseModel):
    order_type: Optional[str] = Field(default=None, description="order | order_catalog | catalog")
    eta_minutes: Optional[int] = Field(default=None, ge=0, le=10080)  # max 1 week
    service_link: Optional[str] = Field(default=None, max_length=500)


class ServiceOrderConfigResponse(BaseModel):
    id: int
    key: str
    category: str
    display_name: str
    order_type: str
    eta_minutes: Optional[int]
    service_link: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True


@router.get("/", response_model=List[ServiceOrderConfigResponse])
async def list_service_configs(
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Список всех сервисов с их order_type, ETA и service_link."""
    _ensure_admin(current_user)

    stmt = select(ServicePrice).order_by(ServicePrice.category, ServicePrice.position, ServicePrice.id)
    if category:
        stmt = stmt.where(ServicePrice.category == category)

    result = await db.execute(stmt)
    prices = result.scalars().all()

    return [
        ServiceOrderConfigResponse(
            id=sp.id,
            key=sp.key,
            category=sp.category,
            display_name=sp.display_name,
            order_type=getattr(sp, "order_type", ORDER_TYPE_ORDER) or ORDER_TYPE_ORDER,
            eta_minutes=getattr(sp, "eta_minutes", None),
            service_link=getattr(sp, "service_link", None),
            is_active=sp.is_active,
        )
        for sp in prices
    ]


@router.put("/{service_id}")
async def update_service_config(
    service_id: int,
    body: ServiceOrderConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Обновить order_type, ETA и service_link для сервиса."""
    _ensure_admin(current_user)

    result = await db.execute(select(ServicePrice).where(ServicePrice.id == service_id))
    sp: Optional[ServicePrice] = result.scalar_one_or_none()
    if sp is None:
        raise HTTPException(status_code=404, detail="Service not found")

    if body.order_type is not None:
        if body.order_type not in VALID_ORDER_TYPES:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid order_type. Must be one of: {', '.join(VALID_ORDER_TYPES)}",
            )
        sp.order_type = body.order_type

    if body.eta_minutes is not None:
        sp.eta_minutes = body.eta_minutes
    elif "eta_minutes" in body.model_fields_set:
        # Explicitly passed null — reset to None (use code default)
        sp.eta_minutes = None

    if body.service_link is not None:
        # Validate: service_link only relevant for order/order_catalog
        ot = getattr(sp, "order_type", ORDER_TYPE_ORDER) or ORDER_TYPE_ORDER
        if ot == ORDER_TYPE_CATALOG:
            raise HTTPException(
                status_code=422,
                detail="service_link is not applicable for 'catalog' order type",
            )
        sp.service_link = body.service_link
    elif "service_link" in body.model_fields_set:
        sp.service_link = None

    await db.commit()
    await db.refresh(sp)

    return {
        "id": sp.id,
        "key": sp.key,
        "order_type": getattr(sp, "order_type", ORDER_TYPE_ORDER) or ORDER_TYPE_ORDER,
        "eta_minutes": getattr(sp, "eta_minutes", None),
        "service_link": getattr(sp, "service_link", None),
    }


@router.put("/bulk")
async def bulk_update_service_configs(
    body: List[dict],
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Массовое обновление order_type/ETA/service_link для нескольких сервисов."""
    _ensure_admin(current_user)

    updated = 0
    for item in body:
        service_id = item.get("id")
        if not service_id:
            continue
        result = await db.execute(select(ServicePrice).where(ServicePrice.id == service_id))
        sp: Optional[ServicePrice] = result.scalar_one_or_none()
        if sp is None:
            continue

        if "order_type" in item and item["order_type"] in VALID_ORDER_TYPES:
            sp.order_type = item["order_type"]
        if "eta_minutes" in item:
            sp.eta_minutes = item["eta_minutes"]
        if "service_link" in item:
            sp.service_link = item["service_link"] or None
        updated += 1

    await db.commit()
    return {"updated": updated}


@router.get("/categories")
async def get_categories(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Список уникальных категорий сервисов."""
    _ensure_admin(current_user)
    result = await db.execute(select(ServicePrice.category).distinct().order_by(ServicePrice.category))
    categories = [row[0] for row in result.all()]
    return {"categories": categories}
