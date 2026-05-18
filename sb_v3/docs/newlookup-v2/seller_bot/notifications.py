"""seller_bot/notifications.py

Seller notification dispatcher.

Called from shared/services/ or webhooks to send Telegram messages
to sellers about key events:
- New buyer message in chat
- Product moderation result (approved / rejected)
- New purchase of a product
- New complaint on a product
- Withdrawal approved / rejected

Usage:
    from seller_bot.notifications import SellerNotifier

    async def handler():
        notifier = SellerNotifier(bot)
        await notifier.notify_new_message(seller_telegram_id, order_id, buyer_name, preview, lang)
"""
from __future__ import annotations

import logging
import os
from typing import Optional

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest

from shared.i18n import t

logger = logging.getLogger(__name__)


class SellerNotifier:
    """Sends event-driven Telegram notifications to a seller."""

    def __init__(self, bot: Optional[Bot] = None):
        """
        If bot is None, a temporary Bot instance is created from SELLER_BOT_TOKEN.
        Use an injected bot when possible to reuse the connection pool.
        """
        self._bot = bot
        self._owns_bot = bot is None

    async def _get_bot(self) -> Bot:
        if self._bot:
            return self._bot
        token = os.getenv("SELLER_BOT_TOKEN", "").strip()
        if not token:
            raise RuntimeError("SELLER_BOT_TOKEN is not configured")
        self._bot = Bot(token=token)
        return self._bot

    async def _send(self, telegram_id: int, text: str) -> bool:
        """Send message; return False if seller blocked the bot."""
        bot = await self._get_bot()
        try:
            await bot.send_message(chat_id=telegram_id, text=text, parse_mode="HTML")
            return True
        except TelegramForbiddenError:
            logger.warning("Seller %s blocked the bot — skipping notification", telegram_id)
            return False
        except TelegramBadRequest as exc:
            logger.warning("Bad request sending notification to %s: %s", telegram_id, exc)
            return False
        except Exception as exc:
            logger.error("Failed to send notification to seller %s: %s", telegram_id, exc)
            return False
        finally:
            if self._owns_bot and self._bot:
                await self._bot.session.close()
                self._bot = None

    async def notify_new_message(
        self,
        seller_telegram_id: int,
        order_id: int,
        buyer_name: str,
        message_preview: str,
        lang: str = "en",
    ) -> bool:
        text = t(
            "seller.notif_new_message",
            lang,
            order_id=order_id,
            buyer_name=buyer_name,
            preview=message_preview[:200],
        )
        return await self._send(seller_telegram_id, text)

    async def notify_moderation_approved(
        self,
        seller_telegram_id: int,
        product_name: str,
        lang: str = "en",
    ) -> bool:
        text = t(
            "seller.notif_moderation_approved",
            lang,
            product_name=product_name,
        )
        return await self._send(seller_telegram_id, text)

    async def notify_moderation_rejected(
        self,
        seller_telegram_id: int,
        product_name: str,
        reason: str,
        lang: str = "en",
    ) -> bool:
        text = t(
            "seller.notif_moderation_rejected",
            lang,
            product_name=product_name,
            reason=reason,
        )
        return await self._send(seller_telegram_id, text)

    async def notify_new_purchase(
        self,
        seller_telegram_id: int,
        product_name: str,
        buyer_name: str,
        amount: float,
        order_id: int,
        lang: str = "en",
    ) -> bool:
        text = t(
            "seller.notif_new_purchase",
            lang,
            product_name=product_name,
            buyer_name=buyer_name,
            amount=amount,
            order_id=order_id,
        )
        return await self._send(seller_telegram_id, text)

    async def notify_new_complaint(
        self,
        seller_telegram_id: int,
        order_id: int,
        product_name: str,
        reason: str,
        lang: str = "en",
    ) -> bool:
        text = t(
            "seller.notif_new_complaint",
            lang,
            order_id=order_id,
            product_name=product_name,
            reason=reason,
        )
        return await self._send(seller_telegram_id, text)

    async def notify_withdrawal_approved(
        self,
        seller_telegram_id: int,
        amount: float,
        details: str,
        lang: str = "en",
    ) -> bool:
        text = t(
            "seller.notif_withdrawal_approved",
            lang,
            amount=amount,
            details=details,
        )
        return await self._send(seller_telegram_id, text)

    async def notify_withdrawal_rejected(
        self,
        seller_telegram_id: int,
        amount: float,
        reason: str,
        lang: str = "en",
    ) -> bool:
        text = t(
            "seller.notif_withdrawal_rejected",
            lang,
            amount=amount,
            reason=reason,
        )
        return await self._send(seller_telegram_id, text)


# ---------------------------------------------------------------------------
# Convenience standalone helpers (fire-and-forget, used from shared/services)
# ---------------------------------------------------------------------------

async def send_seller_notification(
    seller_telegram_id: int,
    event_type: str,
    lang: str = "en",
    **kwargs,
) -> bool:
    """
    Standalone helper that creates a temporary bot and dispatches a notification.

    event_type values:
        new_message, moderation_approved, moderation_rejected,
        new_purchase, new_complaint, withdrawal_approved, withdrawal_rejected

    Example:
        await send_seller_notification(
            123456789,
            "new_purchase",
            lang="ru",
            product_name="Chase Bank Log",
            buyer_name="User#777",
            amount=95.0,
            order_id=4231,
        )
    """
    notifier = SellerNotifier()
    method_map = {
        "new_message": notifier.notify_new_message,
        "moderation_approved": notifier.notify_moderation_approved,
        "moderation_rejected": notifier.notify_moderation_rejected,
        "new_purchase": notifier.notify_new_purchase,
        "new_complaint": notifier.notify_new_complaint,
        "withdrawal_approved": notifier.notify_withdrawal_approved,
        "withdrawal_rejected": notifier.notify_withdrawal_rejected,
    }
    method = method_map.get(event_type)
    if not method:
        logger.error("Unknown seller notification event_type: %s", event_type)
        return False
    return await method(seller_telegram_id, lang=lang, **kwargs)
