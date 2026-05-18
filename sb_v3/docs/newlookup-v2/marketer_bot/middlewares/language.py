"""Language middleware for Marketer Bot — injects `texts` and `user_language` into handler data."""
from __future__ import annotations

from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from shared.database.models import Marketer
from marketer_bot.constants.language_loader import get_texts, DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES


class MarketerLanguageMiddleware(BaseMiddleware):

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        lang = DEFAULT_LANGUAGE

        if user:
            session: AsyncSession | None = data.get("session")
            if session:
                try:
                    r = await session.execute(
                        select(Marketer.language).where(Marketer.telegram_id == user.id)
                    )
                    db_lang = r.scalar_one_or_none()
                    if db_lang and db_lang in SUPPORTED_LANGUAGES:
                        lang = db_lang
                except Exception:
                    pass

        data["user_language"] = lang
        data["texts"] = get_texts(lang)
        return await handler(event, data)
