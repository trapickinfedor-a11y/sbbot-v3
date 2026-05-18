from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from seller_bot.constants.language_loader import get_buttons, get_texts
from shared.services.ui_translation_service import UiTranslator


class SellerLanguageMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        seller = data.get("seller")
        language = getattr(seller, "language", None) or "en"
        if not seller and isinstance(event, (Message, CallbackQuery)):
            code = (event.from_user.language_code or "en").lower()
            language = code if code in {"en", "ru", "zh", "es"} else "en"
        data["user_language"] = language
        data["texts"] = get_texts(language)
        data["buttons"] = get_buttons(language)
        data["ui_texts"] = UiTranslator(session=data.get("session"), language=language, namespace="seller_bot")
        return await handler(event, data)
