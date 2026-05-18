"""
Подключение к базе данных для веб-панели
"""

import logging
from typing import AsyncGenerator
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from shared.database.session import async_session_maker

logger = logging.getLogger(__name__)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency для получения сессии БД с автоматическим rollback при ошибке."""
    async with async_session_maker() as session:
        try:
            yield session
        except SQLAlchemyError as exc:
            logger.error("DB session error, rolling back: %s", exc)
            await session.rollback()
            raise
        finally:
            await session.close()
