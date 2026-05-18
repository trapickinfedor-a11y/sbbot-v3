"""Сервис логирования действий маркетологов"""
from decimal import Decimal
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import MarketerActivityLog


async def log_marketer_activity(
    session: AsyncSession,
    marketer_id: int,
    action: str,
    amount: Optional[Decimal] = None,
    details: Optional[str] = None,
    withdrawal_id: Optional[int] = None,
    mirror_bot_id: Optional[int] = None,
    user_id: Optional[int] = None,
    processed_by: Optional[int] = None,
):
    """Записать действие в лог маркетолога"""
    log = MarketerActivityLog(
        marketer_id=marketer_id,
        action=action,
        amount=amount,
        details=details,
        withdrawal_id=withdrawal_id,
        mirror_bot_id=mirror_bot_id,
        user_id=user_id,
        processed_by=processed_by,
    )
    session.add(log)
    await session.flush()
