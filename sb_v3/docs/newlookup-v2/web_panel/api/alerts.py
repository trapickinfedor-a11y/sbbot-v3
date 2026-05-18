"""
Alerts API — текущий статус алертов и ручной запуск проверки.
"""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from web_panel.auth import get_current_user
from web_panel.database import get_db
from web_panel.services.alert_service import get_alert_status, check_alerts

router = APIRouter(prefix="/api/alerts", tags=["alerts"])
logger = logging.getLogger(__name__)


@router.get("/status")
async def alerts_status(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Текущий статус всех метрик алертов."""
    return await get_alert_status(db)


@router.post("/check")
async def trigger_alert_check(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Ручной запуск проверки алертов."""
    fired = await check_alerts(db)
    return {"fired": fired, "count": len(fired)}
