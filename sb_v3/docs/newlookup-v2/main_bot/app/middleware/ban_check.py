"""
Middleware для проверки забаненных пользователей в главном боте
"""

from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery, Update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from shared.database.models import User
from shared.database.session import async_session_maker

logger = logging.getLogger(__name__)


class MainBotBanCheckMiddleware(BaseMiddleware):
    """
    Middleware для проверки ban статуса пользователя в главном боте
    Блокирует все действия забаненных пользователей
    """
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        
        # Получаем user_id из события
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
        
        # Проверяем ban статус пользователя в любом из его ботов
        async with async_session_maker() as session:
            result = await session.execute(
                select(User.is_banned, User.ban_reason).where(
                    User.user_id == user_id,
                    User.is_banned == True
                ).limit(1)
            )
            user_data = result.first()
            
            if user_data:  # Пользователь забанен хотя бы в одном боте
                ban_reason = user_data[1] or "Violation of service rules"
                logger.info(f"[MAIN BOT BAN CHECK] User {user_id} is BANNED: {ban_reason}")
                
                ban_message = f"""🚫 Account Blocked

Your account has been blocked.
Reason: {ban_reason}

If you believe this is a mistake, please contact support."""
                
                if isinstance(event, Update):
                    if event.message:
                        await event.message.answer(ban_message)
                    elif event.callback_query:
                        await event.callback_query.answer(ban_message, show_alert=True)
                elif isinstance(event, Message):
                    await event.answer(ban_message)
                elif isinstance(event, CallbackQuery):
                    await event.answer(ban_message, show_alert=True)
                
                # Не вызываем handler для забаненного пользователя
                return
        
        # Пользователь не забанен, продолжаем обработку
        return await handler(event, data)
