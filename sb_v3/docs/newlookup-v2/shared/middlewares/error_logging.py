from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import TelegramObject

from shared.services.nocodb_service import NocoDBService

logger = logging.getLogger(__name__)


def _event_user_id(event: TelegramObject) -> int | None:
    from_user = getattr(event, "from_user", None)
    if from_user and getattr(from_user, "id", None):
        return from_user.id
    chat = getattr(event, "chat", None)
    if chat and getattr(chat, "id", None):
        return chat.id
    return None


class GlobalErrorLoggingMiddleware(BaseMiddleware):
    def __init__(self, source: str):
        self.source = source

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        try:
            return await handler(event, data)
        except TelegramBadRequest as exc:
            logger.error("Telegram bad request in %s: %s", self.source, exc)
            NocoDBService.log_error(
                user_id=_event_user_id(event),
                error_type="telegram_bad_request",
                context={
                    "source": self.source,
                    "event_type": type(event).__name__,
                    "error": str(exc),
                },
            )
            return None
        except TelegramForbiddenError as exc:
            logger.warning("Telegram forbidden in %s: %s", self.source, exc)
            NocoDBService.log_error(
                user_id=_event_user_id(event),
                error_type="telegram_forbidden",
                context={
                    "source": self.source,
                    "event_type": type(event).__name__,
                    "error": str(exc),
                },
            )
            return None
        except Exception as exc:
            logger.exception("Unhandled error in %s: %s", self.source, exc)
            NocoDBService.log_error(
                user_id=_event_user_id(event),
                error_type=type(exc).__name__,
                context={
                    "source": self.source,
                    "event_type": type(event).__name__,
                    "error": str(exc),
                },
            )
            return None
