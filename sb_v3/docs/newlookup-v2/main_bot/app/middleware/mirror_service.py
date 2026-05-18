"""Middleware для инъекции MirrorBotService в handlers"""
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject


class MirrorServiceMiddleware(BaseMiddleware):
    def __init__(self, mirror_service):
        self.mirror_service = mirror_service

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        data["mirror_service"] = self.mirror_service
        return await handler(event, data)
