from __future__ import annotations

import logging
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User

logger = logging.getLogger(__name__)

class LoggingMiddleware(BaseMiddleware):
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user: User = data.get("event_from_user")
        
        if user:
            logger.info(
                f"User {user.id} (@{user.username}) | "
                f"Event: {event.__class__.__name__}"
            )
        
        return await handler(event, data)

