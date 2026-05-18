import logging
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject, Update
from aiogram.fsm.context import FSMContext

logger = logging.getLogger(__name__)


class DebugLoggerMiddleware(BaseMiddleware):
    """Middleware для отладки - логирует ВСЕ входящие события"""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Логируем Message (PII-маскирование: DEBUG level, обрезка текста)
        if isinstance(event, Message):
            user_id = str(event.from_user.id) if event.from_user else "Unknown"
            text = event.text[:30] + "..." if event.text and len(event.text) > 30 else event.text
            logger.debug(f"[DEBUG] Message from user {user_id[:4]}***: {text or '<no text>'}")

        # Логируем CallbackQuery
        elif isinstance(event, CallbackQuery):
            user_id = str(event.from_user.id) if event.from_user else "Unknown"
            callback_data = event.data or "<no data>"
            logger.debug(f"[DEBUG] CallbackQuery from user {user_id[:4]}***: {callback_data}")

        # Логируем Update (весь объект)
        elif isinstance(event, Update):
            logger.debug(f"[DEBUG] Update type: {event.event_type if hasattr(event, 'event_type') else 'Unknown'}")
        
        return await handler(event, data)

