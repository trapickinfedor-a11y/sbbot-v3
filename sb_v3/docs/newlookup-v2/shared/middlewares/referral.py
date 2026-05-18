"""Referral middleware for aiogram bots.

Intercepts /start ref_XXX commands and registers the referral relationship
before the normal start handler runs.

Usage in bot.py:
    from shared.middlewares.referral import ReferralMiddleware
    dp.update.middleware(ReferralMiddleware(source_bot="seller_bot"))
"""
from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject, Update

from shared.referral.service import parse_ref_code, create_referral

logger = logging.getLogger(__name__)


class ReferralMiddleware(BaseMiddleware):
    """
    Processes /start ref_<telegram_id> deep links.

    Stores the parsed referrer_id in handler data as ``referral_referrer_id``
    so start handlers can optionally use it.

    The referral DB record is created here (before handler) so duplicate
    /start invocations are idempotent (already_referred guard is in service).
    """

    def __init__(self, source_bot: str = "unknown"):
        self.source_bot = source_bot

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        # Only act on Message events that look like /start <payload>
        if isinstance(event, Update):
            message = event.message
        elif isinstance(event, Message):
            message = event
        else:
            return await handler(event, data)

        if message and message.text:
            parts = message.text.strip().split(maxsplit=1)
            if parts[0] in ("/start", f"/start@{self.source_bot}") and len(parts) == 2:
                payload = parts[1]
                referrer_id = parse_ref_code(payload)
                if referrer_id is not None:
                    referred_id = message.from_user.id if message.from_user else None
                    if referred_id and referred_id != referrer_id:
                        session = data.get("session")
                        if session is not None:
                            try:
                                _, reason = await create_referral(
                                    session=session,
                                    referrer_telegram_id=referrer_id,
                                    referred_telegram_id=referred_id,
                                    source_bot=self.source_bot,
                                )
                                if reason == "ok":
                                    await session.commit()
                                    logger.info(
                                        "[%s] Referral registered: %s -> %s",
                                        self.source_bot,
                                        referrer_id,
                                        referred_id,
                                    )
                                else:
                                    logger.debug(
                                        "[%s] Referral skipped (%s): %s -> %s",
                                        self.source_bot,
                                        reason,
                                        referrer_id,
                                        referred_id,
                                    )
                            except Exception as exc:
                                logger.warning(
                                    "[%s] Referral middleware error: %s", self.source_bot, exc
                                )

                    # Always pass the referrer_id to downstream handlers
                    data["referral_referrer_id"] = referrer_id

        return await handler(event, data)
