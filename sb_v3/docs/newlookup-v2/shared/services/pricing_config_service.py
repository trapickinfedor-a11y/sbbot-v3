from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import PricingConfig


DEFAULT_PRICING_CONFIGS: dict[str, dict[str, Any]] = {
    "worker_order_reminder_enabled": {
        "value_type": "bool",
        "value_json": {"enabled": True},
        "description": "Enable automatic worker reminders for in-progress orders.",
    },
    "worker_order_reminder_hours": {
        "value_type": "number",
        "value_number": Decimal("2"),
        "description": "How many hours between automatic worker order reminders.",
    },
    "buyer_rating_window_minutes": {
        "value_type": "number",
        "value_number": Decimal("60"),
        "description": "Minutes available for buyer rating actions after order delivery.",
    },
}


class PricingConfigService:
    @staticmethod
    async def ensure_defaults(session: AsyncSession) -> None:
        for key, payload in DEFAULT_PRICING_CONFIGS.items():
            row = await session.scalar(select(PricingConfig).where(PricingConfig.key == key))
            if row:
                continue
            row = PricingConfig(
                key=key,
                value_type=payload.get("value_type", "number"),
                value_number=payload.get("value_number"),
                value_text=payload.get("value_text"),
                value_json=payload.get("value_json"),
                description=payload.get("description"),
                is_active=True,
            )
            session.add(row)
        await session.commit()

    @staticmethod
    async def list_all(session: AsyncSession) -> list[PricingConfig]:
        result = await session.execute(select(PricingConfig).order_by(PricingConfig.key.asc()))
        return list(result.scalars().all())

    @staticmethod
    async def get_row(session: AsyncSession, key: str) -> PricingConfig | None:
        return await session.scalar(select(PricingConfig).where(PricingConfig.key == key))

    @staticmethod
    async def get_value(session: AsyncSession, key: str, default: Any = None) -> Any:
        row = await PricingConfigService.get_row(session, key)
        if not row:
            return default
        return PricingConfigService.deserialize(row)

    @staticmethod
    def deserialize(row: PricingConfig) -> Any:
        if row.value_type == "json":
            return row.value_json
        if row.value_type == "bool":
            if row.value_json is not None:
                if isinstance(row.value_json, dict) and "enabled" in row.value_json:
                    return bool(row.value_json["enabled"])
                return bool(row.value_json)
            if row.value_text is not None:
                return row.value_text.strip().lower() in {"1", "true", "yes", "on"}
            return bool(row.value_number)
        if row.value_type == "text":
            return row.value_text
        if row.value_number is not None:
            return float(row.value_number)
        return row.value_text

    @staticmethod
    async def upsert(
        session: AsyncSession,
        *,
        key: str,
        value_type: str,
        value: Any,
        description: str | None = None,
        is_active: bool = True,
    ) -> PricingConfig:
        row = await PricingConfigService.get_row(session, key)
        if not row:
            row = PricingConfig(key=key)
            session.add(row)

        row.value_type = value_type
        row.description = description
        row.is_active = is_active
        row.value_number = None
        row.value_text = None
        row.value_json = None

        if value_type == "json":
            row.value_json = value
        elif value_type == "bool":
            row.value_json = {"enabled": bool(value)}
        elif value_type == "text":
            row.value_text = str(value) if value is not None else None
        else:
            row.value_number = Decimal(str(value)) if value is not None else None

        await session.commit()
        await session.refresh(row)
        return row
