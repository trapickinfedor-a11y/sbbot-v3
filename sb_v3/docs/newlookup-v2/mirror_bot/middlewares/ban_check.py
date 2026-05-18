"""
Middleware для проверки забаненных пользователей
"""

import logging
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery, Update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from shared.database.models import User

logger = logging.getLogger(__name__)


class BanCheckMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user_id = None
        if isinstance(event, Update):
            if event.message:
                user_id = event.message.from_user.id
            elif event.callback_query:
                user_id = event.callback_query.from_user.id
        elif isinstance(event, Message):
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id

        if not user_id:
            return await handler(event, data)

        session: AsyncSession = data.get("session")
        if not session:
            return await handler(event, data)

        result = await session.execute(
            select(User.is_banned, User.ban_reason).where(
                User.user_id == user_id,
                User.is_banned == True
            ).limit(1)
        )
        user_data = result.first()

        if user_data and user_data[0]:
            texts_obj = data.get('texts')
            default_reason = texts_obj.VIOLATION_OF_SERVICE_RULES if texts_obj and hasattr(texts_obj, 'VIOLATION_OF_SERVICE_RULES') else "Violation of service rules"
            ban_reason = user_data[1] or default_reason

            texts = data.get('texts')
            if not texts:
                from mirror_bot.constants.language_loader import get_texts
                texts = get_texts('en')

            ban_message = texts.ACCOUNT_BLOCKED_MESSAGE.format(reason=ban_reason)

            if isinstance(event, Update):
                if event.message:
                    await event.message.answer(ban_message)
                elif event.callback_query:
                    await event.callback_query.answer(ban_message, show_alert=True)
            elif isinstance(event, Message):
                await event.answer(ban_message)
            elif isinstance(event, CallbackQuery):
                await event.answer(ban_message, show_alert=True)
            return

        return await handler(event, data)
