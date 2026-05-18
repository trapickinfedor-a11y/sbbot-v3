"""ETA Service — fetches ETA for a service from DB (service_prices) with fallback
to static constants from mirror_bot.constants.service_eta.

Order type constants:
  ORDER_TYPE_ORDER          = "order"          — executed in real-time by a worker
  ORDER_TYPE_ORDER_CATALOG  = "order_catalog"  — worker loads catalog or fulfills if absent
  ORDER_TYPE_CATALOG        = "catalog"        — full catalog download, no user input
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import ServicePrice

logger = logging.getLogger(__name__)

# Order type constants
ORDER_TYPE_ORDER = "order"
ORDER_TYPE_ORDER_CATALOG = "order_catalog"
ORDER_TYPE_CATALOG = "catalog"

ORDER_TYPES = (ORDER_TYPE_ORDER, ORDER_TYPE_ORDER_CATALOG, ORDER_TYPE_CATALOG)

ORDER_TYPE_LABELS = {
    ORDER_TYPE_ORDER: "⚡ Real-time",
    ORDER_TYPE_ORDER_CATALOG: "📦 On Order",
    ORDER_TYPE_CATALOG: "📂 Catalog",
}


def _minutes_to_human(minutes: int) -> str:
    """Convert integer minutes to human-readable string."""
    if minutes == 0:
        return "Instant ⚡"
    if minutes < 60:
        return f"{minutes} min"
    hours = minutes // 60
    rem = minutes % 60
    if rem == 0:
        return f"{hours}h"
    return f"{hours}h {rem}m"


def _order_type_label(order_type: str) -> str:
    return ORDER_TYPE_LABELS.get(order_type, order_type)


class ETAService:
    """Fetches ETA and order_type from DB; falls back to static constants."""

    @staticmethod
    async def get_service_info(
        session: AsyncSession,
        service_key: str,
    ) -> dict:
        """Return dict with 'order_type', 'eta_minutes', 'eta_text', 'service_link'."""
        try:
            result = await session.execute(
                select(ServicePrice).where(ServicePrice.key == service_key)
            )
            sp: Optional[ServicePrice] = result.scalar_one_or_none()
            if sp is not None:
                eta_minutes = sp.eta_minutes
                order_type = getattr(sp, "order_type", ORDER_TYPE_ORDER) or ORDER_TYPE_ORDER
                service_link = getattr(sp, "service_link", None)
                if eta_minutes is not None:
                    eta_text = _minutes_to_human(eta_minutes)
                else:
                    # fall back to static constant
                    from mirror_bot.constants.service_eta import ServiceETA
                    eta_text = ServiceETA.get_eta(service_key)
                return {
                    "order_type": order_type,
                    "eta_minutes": eta_minutes,
                    "eta_text": eta_text,
                    "service_link": service_link,
                }
        except Exception as e:
            logger.warning(f"ETAService: DB lookup failed for '{service_key}': {e}")

        # Full fallback to static constants
        from mirror_bot.constants.service_eta import ServiceETA
        return {
            "order_type": ORDER_TYPE_ORDER,
            "eta_minutes": None,
            "eta_text": ServiceETA.get_eta(service_key),
            "service_link": None,
        }

    @staticmethod
    async def get_eta_text(
        session: AsyncSession,
        service_key: str,
    ) -> str:
        info = await ETAService.get_service_info(session, service_key)
        return info["eta_text"]

    @staticmethod
    async def get_order_type(
        session: AsyncSession,
        service_key: str,
    ) -> str:
        info = await ETAService.get_service_info(session, service_key)
        return info["order_type"]

    @staticmethod
    def format_eta_for_user(eta_text: str, order_type: str) -> str:
        """Format ETA + order type label for display to user."""
        type_label = _order_type_label(order_type)
        return f"{type_label} | ⏱ ETA: {eta_text}"
