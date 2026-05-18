"""Сервис учёта статистики владельцев ботов (spent при завершении заказа)"""
from datetime import date
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from shared.database.models import BotOwnerStats, MirrorBot


async def record_owner_spent(
    session: AsyncSession,
    mirror_bot_id: int,
    amount: Decimal,
) -> None:
    """Добавить сумму заказа в spent владельца бота за сегодня"""
    today = date.today()
    result = await session.execute(
        select(BotOwnerStats).where(
            BotOwnerStats.mirror_bot_id == mirror_bot_id,
            BotOwnerStats.date == today
        )
    )
    stats = result.scalar_one_or_none()
    if not stats:
        stats = BotOwnerStats(mirror_bot_id=mirror_bot_id, date=today)
        session.add(stats)
        await session.flush()
    current_spent = stats.spent if isinstance(stats.spent, Decimal) else Decimal(str(stats.spent or 0))
    stats.spent = current_spent + Decimal(str(amount or 0))
    await session.flush()
