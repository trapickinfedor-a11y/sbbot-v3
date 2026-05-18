import logging
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update, ErrorEvent
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

logger = logging.getLogger(__name__)

class ErrorHandlerMiddleware(BaseMiddleware):
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        try:
            return await handler(event, data)
        except TelegramBadRequest as e:
            logger.error(f"Telegram Bad Request: {e}")
            return None
        except TelegramForbiddenError as e:
            logger.warning(f"User blocked bot: {e}")
            return None
        except Exception as e:
            logger.exception(f"Unhandled error: {e}")
            return None

