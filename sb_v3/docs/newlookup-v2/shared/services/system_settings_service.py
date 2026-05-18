"""SystemSetting CRUD helpers and seeding.

Usage:
    from shared.services.system_settings_service import SystemSettingsService

    async with async_session_maker() as session:
        fee = await SystemSettingsService.get_float(session, "platform_fee_percent", default=5.0)
"""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import SystemSetting

logger = logging.getLogger(__name__)

# Default values seeded on first startup
_DEFAULTS: list[tuple[str, str, str]] = [
    ("platform_fee_percent",        "5.0",  "Platform fee applied to buyer order price (%)"),
    ("marketer_commission_percent", "10.0", "Marketer referral commission as % of order price"),
    ("escrow_default_hours",        "24",   "Default escrow hold period in hours"),
    ("escrow_min_hours",            "1",    "Minimum escrow hold period (hours) for low-risk items"),
    ("escrow_max_hours",            "72",   "Maximum escrow hold period (hours) for high-risk items"),
    ("seller_vacation_max_days",    "30",   "Maximum number of days a seller can stay on vacation"),
    ("worker_violation_suspend_at", "3",    "Suspend worker after this many violations"),
    ("buyer_trust_risky_threshold", "50",   "trust_score below this value triggers extended escrow"),
    ("auto_complete_hours",         "24",   "Hours before an approved seller order auto-completes"),
]


class SystemSettingsService:
    """Read, write and seed SystemSetting rows."""

    @staticmethod
    async def seed_defaults(session: AsyncSession) -> int:
        """Insert default rows that do not yet exist. Returns count of rows inserted."""
        inserted = 0
        for key, value, description in _DEFAULTS:
            existing = await session.get(SystemSetting, key)
            if existing is None:
                session.add(SystemSetting(key=key, value=value, description=description))
                inserted += 1
        if inserted:
            await session.commit()
            logger.info("SystemSettings: seeded %d default rows", inserted)
        return inserted

    @staticmethod
    async def get(session: AsyncSession, key: str, default: Optional[str] = None) -> Optional[str]:
        row = await session.get(SystemSetting, key)
        if row is None:
            return default
        return row.value

    @staticmethod
    async def get_int(session: AsyncSession, key: str, default: int = 0) -> int:
        val = await SystemSettingsService.get(session, key)
        try:
            return int(val) if val is not None else default
        except (ValueError, TypeError):
            return default

    @staticmethod
    async def get_float(session: AsyncSession, key: str, default: float = 0.0) -> float:
        val = await SystemSettingsService.get(session, key)
        try:
            return float(val) if val is not None else default
        except (ValueError, TypeError):
            return default

    @staticmethod
    async def get_bool(session: AsyncSession, key: str, default: bool = False) -> bool:
        val = await SystemSettingsService.get(session, key)
        if val is None:
            return default
        return val.lower() in ("1", "true", "yes", "on")

    @staticmethod
    async def set(session: AsyncSession, key: str, value: str) -> SystemSetting:
        row = await session.get(SystemSetting, key)
        if row is None:
            row = SystemSetting(key=key, value=value)
            session.add(row)
        else:
            row.value = value
        await session.commit()
        await session.refresh(row)
        return row

    @staticmethod
    async def list_all(session: AsyncSession) -> list[SystemSetting]:
        result = await session.execute(select(SystemSetting).order_by(SystemSetting.key))
        return list(result.scalars().all())
