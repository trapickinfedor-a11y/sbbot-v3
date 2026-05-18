"""
Сервис логирования уведомлений.
Записывает каждую попытку отправки — успешно или с ошибкой.
Используется из admin_notification_service, order_notification_service и др.
"""

import asyncio
import logging
from typing import Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


async def _write_log(
    event_type: str,
    channel: str,
    status: str,
    recipient_id: Optional[int] = None,
    related_id: Optional[int] = None,
    related_type: Optional[str] = None,
    error_message: Optional[str] = None,
    payload: Optional[dict] = None,
) -> None:
    """Записать запись лога в БД (внутренняя функция)."""
    try:
        from shared.database.session import async_session_maker
        from shared.database.models import NotificationLog

        async with async_session_maker() as session:
            log = NotificationLog(
                event_type=event_type,
                channel=channel,
                status=status,
                recipient_id=recipient_id,
                related_id=related_id,
                related_type=related_type,
                error_message=str(error_message)[:500] if error_message else None,
                payload=payload,
                sent_at=datetime.now(timezone.utc) if status == "sent" else None,
            )
            session.add(log)
            await session.commit()
    except Exception as e:
        logger.error(f"Failed to write notification log: {e}")


def fire_log(
    event_type: str,
    channel: str,
    status: str,
    recipient_id: Optional[int] = None,
    related_id: Optional[int] = None,
    related_type: Optional[str] = None,
    error_message: Optional[str] = None,
    payload: Optional[dict] = None,
) -> None:
    """
    Запланировать запись лога как фоновую задачу (non-blocking).
    Безопасно вызывать из любого async-контекста.
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(
                _write_log(
                    event_type=event_type,
                    channel=channel,
                    status=status,
                    recipient_id=recipient_id,
                    related_id=related_id,
                    related_type=related_type,
                    error_message=error_message,
                    payload=payload,
                )
            )
    except Exception as e:
        logger.error(f"Failed to schedule notification log: {e}")


async def log_async(
    event_type: str,
    channel: str,
    status: str,
    recipient_id: Optional[int] = None,
    related_id: Optional[int] = None,
    related_type: Optional[str] = None,
    error_message: Optional[str] = None,
    payload: Optional[dict] = None,
) -> None:
    """
    Асинхронная версия — await-able, для использования напрямую.
    """
    await _write_log(
        event_type=event_type,
        channel=channel,
        status=status,
        recipient_id=recipient_id,
        related_id=related_id,
        related_type=related_type,
        error_message=error_message,
        payload=payload,
    )
