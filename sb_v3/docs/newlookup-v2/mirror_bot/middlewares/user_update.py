from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from shared.database.models import User


class UserUpdateMiddleware(BaseMiddleware):
    """Middleware для автоматического обновления username пользователя"""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Получаем информацию о пользователе из события
        user = None
        username = None

        if isinstance(event, Message):
            user = event.from_user
            username = user.username if user else None
        elif isinstance(event, CallbackQuery):
            user = event.from_user
            username = user.username if user else None

        # Если есть информация о пользователе и session
        if user and username and "session" in data:
            session: AsyncSession = data["session"]

            try:
                # Обновляем username в базе данных если он изменился
                await session.execute(
                    update(User)
                    .where(User.user_id == user.id)
                    .where(User.username != username)
                    .values(username=username)
                )
                await session.commit()
            except Exception:
                # Игнорируем ошибки обновления, чтобы не блокировать основной функционал
                await session.rollback()

        return await handler(event, data)
