from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject


class MirrorBotMiddleware(BaseMiddleware):
    def __init__(self, mirror_bot_id: int):
        self.mirror_bot_id = mirror_bot_id
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        data["mirror_bot_id"] = self.mirror_bot_id
        return await handler(event, data)

