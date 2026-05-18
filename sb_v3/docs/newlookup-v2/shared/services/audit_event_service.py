from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import AuditLog
from shared.services.nocodb_service import NocoDBService


class AuditEventService:
    """Dual-write audit events to local DB and NocoDB."""

    @staticmethod
    async def log(
        session: AsyncSession,
        *,
        event_type: str,
        source: str = "system",
        actor_type: str | None = None,
        actor_id: Any = None,
        target_type: str | None = None,
        target_id: Any = None,
        status: str = "ok",
        payload: Optional[dict[str, Any]] = None,
        created_at: datetime | None = None,
        commit: bool = False,
    ) -> AuditLog:
        event = AuditLog(
            source=source or "system",
            event_type=event_type,
            actor_type=actor_type,
            actor_id=int(actor_id) if actor_id is not None else None,
            target_type=target_type,
            target_id=int(target_id) if target_id is not None else None,
            status=status or "ok",
            payload=payload or {},
            created_at=created_at or datetime.now(timezone.utc),
        )
        session.add(event)
        await session.flush()

        NocoDBService.log_event(
            event_type=event.event_type,
            actor_type=event.actor_type,
            actor_id=event.actor_id,
            target_type=event.target_type,
            target_id=event.target_id,
            status=event.status,
            payload={
                "source": event.source,
                **(event.payload or {}),
            },
            timestamp=event.created_at,
        )

        if commit:
            await session.commit()
            await session.refresh(event)

        return event
