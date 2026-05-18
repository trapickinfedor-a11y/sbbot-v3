"""
Middleware для работы с базой данных
"""

from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession


class DatabaseMiddleware(BaseMiddleware):
    """Middleware для добавления сессии БД в handler"""
    
    def __init__(self, session_maker: async_sessionmaker):
        super().__init__()
        self.session_maker = session_maker
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        async with self.session_maker() as session:
            data["session"] = session
            return await handler(event, data)

