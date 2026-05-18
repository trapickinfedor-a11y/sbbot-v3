from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mirror_bot.constants.prices import ServicePrices
from shared.database.models import ServicePrice
from shared.services.pricing_config_service import PricingConfigService


class RuntimePricingService:
    """Runtime pricing/config reader with DB-first and constant fallback behavior."""

    @staticmethod
    async def get_service_price(
        session: AsyncSession,
        *,
        key: str,
        is_bulk: bool = False,
        fallback: Decimal | None = None,
    ) -> Decimal:
        row = await session.scalar(
            select(ServicePrice).where(ServicePrice.key == key, ServicePrice.is_active == True)
        )
        if row:
            if is_bulk and row.bulk_price is not None:
                return row.bulk_price
            return row.price
        if fallback is not None:
            return fallback
        return ServicePrices.get_service_price(key, is_bulk=is_bulk)

    @staticmethod
    async def get_pair(
        session: AsyncSession,
        *,
        key: str,
        fallback_single: Decimal | None = None,
        fallback_bulk: Decimal | None = None,
    ) -> tuple[Decimal | None, Decimal | None]:
        row = await session.scalar(
            select(ServicePrice).where(ServicePrice.key == key, ServicePrice.is_active == True)
        )
        if row:
            return row.price, row.bulk_price or row.price
        if fallback_single is not None or fallback_bulk is not None:
            return fallback_single, fallback_bulk if fallback_bulk is not None else fallback_single
        dynamic = await ServicePrices.get_dynamic_price_pair(session, key)
        return dynamic or (None, None)

    @staticmethod
    async def get_config(
        session: AsyncSession,
        *,
        key: str,
        default: Any = None,
    ) -> Any:
        return await PricingConfigService.get_value(session, key, default)
