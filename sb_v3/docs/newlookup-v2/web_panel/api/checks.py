from __future__ import annotations

"""
API раздела «Проверки» — мониторинг отправки уведомлений,
отслеживание потерь и ошибок доставки.
"""

import logging
import os
from datetime import datetime, timedelt, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram import Bot
from aiogram.enums import ParseMode

from shared.database.session import async_session_maker
from shared.database.models import NotificationLog
from web_panel.auth import get_current_user, has_any_role

router = APIRouter()
logger = logging.getLogger(__name__)

SUPPORT_BOT_TOKEN = os.getenv("SUPPORT_BOT_TOKEN", "")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]


def _ensure_checks_view(current_user: dict) -> None:
    if not has_any_role(current_user, "admin", "owner", "super_admin"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")


def _ensure_checks_action(current_user: dict) -> None:
    if not has_any_role(current_user, "admin", "owner", "super_admin"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")


# ──────────────────────────────────────────
# Stats
# ──────────────────────────────────────────

@router.get("/stats")
async def get_checks_stats(
    date_from: Optional[str] = Query(None, description="ISO datetime (UTC), напр. 2026-03-01T00:00:00"),
    date_to: Optional[str] = Query(None, description="ISO datetime (UTC), напр. 2026-03-04T23:59:59"),
    current_user=Depends(get_current_user),
):
    """Сводная статистика доставки уведомлений за произвольный диапазон дат."""
    _ensure_checks_view(current_user)
    now = datetime.now(timezone.utc)

    def _parse(s: Optional[str]) -> Optional[datetime]:
        if not s:
            return None
        try:
            return datetime.fromisoformat(s.replace("Z", ""))
        except Exception:
            return None

    dt_from = _parse(date_from)
    dt_to = _parse(date_to) or now

    async with async_session_maker() as session:

        async def _counts(since: Optional[datetime] = None, until: Optional[datetime] = None):
            base = []
            if since:
                base.append(NotificationLog.created_at >= since)
            if until:
                base.append(NotificationLog.created_at <= until)

            sent_q = await session.execute(
                select(func.count()).where(*base, NotificationLog.status == "sent")
            )
            failed_q = await session.execute(
                select(func.count()).where(*base, NotificationLog.status == "failed")
            )
            retried_q = await session.execute(
                select(func.count()).where(*base, NotificationLog.status == "retried")
            )
            sent = sent_q.scalar() or 0
            failed = failed_q.scalar() or 0
            retried = retried_q.scalar() or 0
            total = sent + failed
            return {
                "sent": sent,
                "failed": failed,
                "retried": retried,
                "total": total,
                "failure_rate": round(failed / total * 100, 1) if total else 0,
            }

        # Основной диапазон (или всё время если не передан)
        stats_range = await _counts(dt_from, dt_to)

        # Разбивка по каналам в выбранном диапазоне
        ch_filters = []
        if dt_from:
            ch_filters.append(NotificationLog.created_at >= dt_from)
        ch_filters.append(NotificationLog.created_at <= dt_to)

        channel_q = await session.execute(
            select(NotificationLog.channel, NotificationLog.status, func.count())
            .where(*ch_filters)
            .group_by(NotificationLog.channel, NotificationLog.status)
        )
        channels: dict = {}
        for channel, status, count in channel_q.fetchall():
            if channel not in channels:
                channels[channel] = {"sent": 0, "failed": 0}
            channels[channel][status] = count

        # Топ ошибок в диапазоне
        event_q = await session.execute(
            select(NotificationLog.event_type, func.count())
            .where(*ch_filters, NotificationLog.status == "failed")
            .group_by(NotificationLog.event_type)
            .order_by(desc(func.count()))
            .limit(10)
        )
        top_failed_events = [
            {"event_type": et, "count": cnt} for et, cnt in event_q.fetchall()
        ]

    return {
        "range": stats_range,
        "date_from": dt_from.isoformat() if dt_from else None,
        "date_to": dt_to.isoformat(),
        "channels": channels,
        "top_failed_events": top_failed_events,
    }


# ──────────────────────────────────────────
# Logs list
# ──────────────────────────────────────────

@router.get("/logs")
async def get_notification_logs(
    status: Optional[str] = Query(None, description="sent | failed | retried"),
    channel: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    related_type: Optional[str] = Query(None),
    related_id: Optional[int] = Query(None),
    recipient_id: Optional[int] = Query(None),
    date_from: Optional[str] = Query(None, description="ISO datetime UTC, напр. 2026-03-01T00:00:00"),
    date_to: Optional[str] = Query(None, description="ISO datetime UTC, напр. 2026-03-04T23:59:59"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user=Depends(get_current_user),
):
    """Список записей лога уведомлений с фильтрацией по произвольному диапазону дат."""
    _ensure_checks_view(current_user)

    def _parse(s: Optional[str]) -> Optional[datetime]:
        if not s:
            return None
        try:
            return datetime.fromisoformat(s.replace("Z", ""))
        except Exception:
            return None

    dt_from = _parse(date_from)
    dt_to = _parse(date_to)

    async with async_session_maker() as session:
        filters = []

        if dt_from:
            filters.append(NotificationLog.created_at >= dt_from)
        if dt_to:
            filters.append(NotificationLog.created_at <= dt_to)
        if status:
            filters.append(NotificationLog.status == status)
        if channel:
            filters.append(NotificationLog.channel == channel)
        if event_type:
            filters.append(NotificationLog.event_type == event_type)
        if related_type:
            filters.append(NotificationLog.related_type == related_type)
        if related_id is not None:
            filters.append(NotificationLog.related_id == related_id)
        if recipient_id is not None:
            filters.append(NotificationLog.recipient_id == recipient_id)

        q_args = filters if filters else []
        q = await session.execute(
            select(NotificationLog)
            .where(*q_args)
            .order_by(desc(NotificationLog.created_at))
            .limit(limit)
            .offset(offset)
        )
        logs = q.scalars().all()

        total_q = await session.execute(
            select(func.count()).where(*q_args)
        )
        total = total_q.scalar() or 0

    return {
        "total": total,
        "items": [
            {
                "id": log.id,
                "event_type": log.event_type,
                "channel": log.channel,
                "status": log.status,
                "recipient_id": log.recipient_id,
                "related_id": log.related_id,
                "related_type": log.related_type,
                "error_message": log.error_message,
                "retry_count": log.retry_count,
                "created_at": log.created_at.isoformat() if log.created_at else None,
                "sent_at": log.sent_at.isoformat() if log.sent_at else None,
                "payload": log.payload,
            }
            for log in logs
        ],
    }


# ──────────────────────────────────────────
# Retry
# ──────────────────────────────────────────

@router.post("/retry/{log_id}")
async def retry_notification(
    log_id: int,
    current_user=Depends(get_current_user),
):
    """
    Повторно отправить упавшее уведомление.
    Работает для канала 'admin' (отправка через support bot).
    """
    _ensure_checks_action(current_user)
    async with async_session_maker() as session:
        q = await session.execute(
            select(NotificationLog).where(NotificationLog.id == log_id)
        )
        log_entry = q.scalar_one_or_none()

        if not log_entry:
            raise HTTPException(status_code=404, detail="Log entry not found")

        if log_entry.status not in ("failed",):
            raise HTTPException(
                status_code=400,
                detail=f"Cannot retry log with status '{log_entry.status}'",
            )

        if log_entry.channel != "admin":
            raise HTTPException(
                status_code=400,
                detail="Retry is only supported for 'admin' channel notifications",
            )

        if not ADMIN_IDS:
            raise HTTPException(status_code=500, detail="No ADMIN_IDS configured")

        if not SUPPORT_BOT_TOKEN:
            raise HTTPException(status_code=500, detail="SUPPORT_BOT_TOKEN not set")

        payload = log_entry.payload or {}
        text = payload.get("text") or payload.get("text_preview", "")
        if not text:
            raise HTTPException(
                status_code=400,
                detail="No text in payload to retry",
            )

        bot = Bot(token=SUPPORT_BOT_TOKEN)
        sent_count = 0
        errors = []
        try:
            for admin_id in ADMIN_IDS:
                try:
                    await bot.send_message(
                        chat_id=admin_id,
                        text=f"♻️ <b>[RETRY]</b>\n\n{text}",
                        parse_mode=ParseMode.HTML,
                    )
                    sent_count += 1
                except Exception as e:
                    errors.append({"admin_id": admin_id, "error": str(e)})
        finally:
            await bot.session.close()

        # Обновляем запись лога
        log_entry.retry_count = (log_entry.retry_count or 0) + 1
        log_entry.status = "retried" if sent_count > 0 else "failed"
        await session.commit()

    return {
        "success": sent_count > 0,
        "sent_count": sent_count,
        "errors": errors,
        "new_status": log_entry.status,
    }


# ──────────────────────────────────────────
# Cleanup old logs
# ──────────────────────────────────────────

@router.delete("/logs/cleanup")
async def cleanup_old_logs(
    days: int = Query(30, ge=1, le=365, description="Удалить записи старше N дней"),
    current_user=Depends(get_current_user),
):
    """Удалить старые записи лога (только для owner / super_admin)."""
    if current_user.get("role") not in {"owner", "super_admin"}:
        raise HTTPException(status_code=403, detail="Only owner can cleanup logs")

    async with async_session_maker() as session:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        from sqlalchemy import delete
        result = await session.execute(
            delete(NotificationLog).where(NotificationLog.created_at < cutoff)
        )
        await session.commit()
        deleted = result.rowcount

    return {"deleted": deleted, "cutoff": cutoff.isoformat()}


# ──────────────────────────────────────────
# Send test message (проверка отправки)
# ──────────────────────────────────────────

@router.post("/send-test")
async def send_test_message(
    current_user=Depends(get_current_user),
):
    """
    Отправить проверочное сообщение «Проверка» всем админам через Support Bot.
    Используется для проверки работоспособности канала доставки.
    """
    _ensure_checks_action(current_user)
    if not SUPPORT_BOT_TOKEN:
        raise HTTPException(status_code=500, detail="SUPPORT_BOT_TOKEN not set")

    if not ADMIN_IDS:
        raise HTTPException(status_code=500, detail="ADMIN_IDS not configured")

    test_text = "🔔 <b>Проверка</b>\n\nТестовое сообщение для проверки отправки уведомлений."

    bot = Bot(token=SUPPORT_BOT_TOKEN)
    sent_count = 0
    errors = []
    try:
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(
                    chat_id=admin_id,
                    text=test_text,
                    parse_mode=ParseMode.HTML,
                )
                sent_count += 1
            except Exception as e:
                errors.append({"admin_id": admin_id, "error": str(e)})
    finally:
        await bot.session.close()

    return {
        "success": sent_count > 0,
        "sent_count": sent_count,
        "total_admins": len(ADMIN_IDS),
        "errors": errors,
        "message": "Проверка" if sent_count > 0 else "Ошибка отправки",
    }


# ──────────────────────────────────────────
# Distinct filter values
# ──────────────────────────────────────────

@router.get("/meta")
async def get_checks_meta(current_user=Depends(get_current_user)):
    """Возвращает список уникальных event_type и channel для фильтров."""
    _ensure_checks_view(current_user)
    async with async_session_maker() as session:
        et_q = await session.execute(
            select(NotificationLog.event_type).distinct().order_by(NotificationLog.event_type)
        )
        ch_q = await session.execute(
            select(NotificationLog.channel).distinct().order_by(NotificationLog.channel)
        )
    return {
        "event_types": [r[0] for r in et_q.fetchall()],
        "channels": [r[0] for r in ch_q.fetchall()],
    }
