"""
Middleware для проверки активности зеркального бота
"""

import logging
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery, Update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from shared.database.models import MirrorBot

logger = logging.getLogger(__name__)


class BotStatusCheckMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        session: AsyncSession = data.get("session")
        mirror_bot_id: int = data.get("mirror_bot_id")

        if not session or not mirror_bot_id:
            return await handler(event, data)

        result = await session.execute(
            select(MirrorBot.is_active).where(MirrorBot.id == mirror_bot_id)
        )
        bot_active = result.scalar_one_or_none()

        if bot_active is not True:
            texts = data.get('texts')
            if not texts:
                from mirror_bot.constants.language_loader import get_texts
                texts = get_texts('en')

            msg = texts.BOT_DEACTIVATED_MESSAGE

            if isinstance(event, Update):
                if event.message:
                    await event.message.answer(msg)
                elif event.callback_query:
                    await event.callback_query.answer(msg, show_alert=True)
            elif isinstance(event, Message):
                await event.answer(msg)
            elif isinstance(event, CallbackQuery):
                await event.answer(msg, show_alert=True)
            return

        return await handler(event, data)
