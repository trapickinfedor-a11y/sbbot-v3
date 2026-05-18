"""
Единый роутер внутренних уведомлений по Telegram log-чатам.

Использует MAIN_BOT_TOKEN и маршрутизирует события по каналам:
- LOG_CHANNEL_OPS
- LOG_CHANNEL_AUDIT
- LOG_CHANNEL_FINANCE
- LOG_CHANNEL_ORDERS
- LOG_CHANNEL_AUTH
"""

import logging
import os
from typing import Dict, Optional, Set

from aiogram import Bot
from aiogram.enums import ParseMode

from shared.services.notification_log_service import fire_log

logger = logging.getLogger(__name__)


class LogChannelService:
    """Маршрутизация внутренних уведомлений по log-чатам."""

    _bot: Optional[Bot] = None

    CHANNELS: Dict[str, int] = {
        "ops": int(os.getenv("LOG_CHANNEL_OPS", "0") or 0),
        "audit": int(os.getenv("LOG_CHANNEL_AUDIT", "0") or 0),
        "finance": int(os.getenv("LOG_CHANNEL_FINANCE", "0") or 0),
        "orders": int(os.getenv("LOG_CHANNEL_ORDERS", "0") or 0),
        "auth": int(os.getenv("LOG_CHANNEL_AUTH", "0") or 0),
    }

    MAIN_BOT_TOKEN = os.getenv("MAIN_BOT_TOKEN", "")

    ORDER_EVENTS = {
        "new_order",
        "order_taken",
        "order_completed",
        "order_cancelled",
        "bulk_order_completed",
        "bulk_item_completed",
        "files_sent",
        "addinfo_set",
        "dispute_opened",
        "product_purchased",
        "support_order_taken",
        "support_order_completed",
        "support_order_with_files",
        "support_addinfo_completed",
        "support_order_cancelled",
        "support_addinfo_processing",
        "support_bulk_item_reset",
        "support_bulk_order_completed",
    }

    FINANCE_EVENTS = {
        "payment_success",
        "payment_expired",
        "balance_update",
        "seller_withdrawal_requested",
        "seller_withdrawal_approved",
        "seller_withdrawal_rejected",
        "bot_owner_withdrawal_approve",
        "bot_owner_withdrawal_reject",
        "marketer_withdrawal_approve",
        "marketer_withdrawal_reject",
    }

    AUTH_EVENTS = {
        "login",
        "logout",
        "auth_login",
        "auth_logout",
        "auth_failed",
        "auth_access_denied",
    }

    OPS_EVENTS = {
        "new_user",
        "user_banned",
        "new_support_ticket",
        "new_complaint",
        "support_complaint_filed",
        "admin_action",
    }

    CRITICAL_EVENTS = {
        "payment_success",
        "balance_update",
        "seller_withdrawal_requested",
        "seller_withdrawal_approved",
        "seller_withdrawal_rejected",
        "order_cancelled",
        "dispute_opened",
        "new_complaint",
        "support_complaint_filed",
        "user_banned",
        "login",
        "auth_failed",
        "auth_access_denied",
    }

    @classmethod
    def _get_bot(cls) -> Optional[Bot]:
        if cls._bot:
            return cls._bot
        if not cls.MAIN_BOT_TOKEN:
            return None
        cls._bot = Bot(token=cls.MAIN_BOT_TOKEN)
        return cls._bot

    @classmethod
    def _resolve_routes(cls, event_type: str) -> Set[str]:
        routes: Set[str] = {"audit"}

        if event_type in cls.ORDER_EVENTS or "order" in event_type or "bulk" in event_type:
            routes.add("orders")
        if event_type in cls.FINANCE_EVENTS or any(
            key in event_type for key in ("payment", "balance", "withdraw", "refund", "finance")
        ):
            routes.add("finance")
        if event_type in cls.AUTH_EVENTS or any(
            key in event_type for key in ("auth", "login", "logout", "token", "password")
        ):
            routes.add("auth")
        if event_type in cls.OPS_EVENTS or not routes.difference({"audit"}):
            routes.add("ops")

        return routes

    @classmethod
    def _event_emoji(cls, event_type: str, urgent: bool) -> str:
        if urgent:
            return "🚨"
        if event_type in cls.CRITICAL_EVENTS:
            return "⚠️"
        if event_type in cls.AUTH_EVENTS or "auth" in event_type or "login" in event_type:
            return "🔐"
        if event_type in cls.FINANCE_EVENTS or any(
            key in event_type for key in ("payment", "balance", "withdraw", "refund", "finance")
        ):
            return "💰"
        if event_type in cls.ORDER_EVENTS or "order" in event_type or "bulk" in event_type:
            return "📦"
        return "📣"

    @classmethod
    def _format_message(cls, text: str, event_type: str, urgent: bool) -> str:
        emoji = cls._event_emoji(event_type, urgent)
        event_label = event_type.replace("_", " ").upper()
        return f"""{emoji} <b>{event_label}</b>

{text}"""

    @classmethod
    async def send(
        cls,
        *,
        text: str,
        event_type: str,
        urgent: bool = False,
        payload: Optional[dict] = None,
    ) -> None:
        bot = cls._get_bot()
        if not bot:
            logger.warning("LogChannelService: MAIN_BOT_TOKEN not configured")
            fire_log(
                event_type=event_type,
                channel="log_channels",
                status="failed",
                error_message="MAIN_BOT_TOKEN not configured",
                payload=payload or {"text_preview": text[:300]},
            )
            return

        routes = cls._resolve_routes(event_type)
        chat_ids = {cls.CHANNELS.get(route, 0) for route in routes}
        chat_ids = {chat_id for chat_id in chat_ids if chat_id}

        if not chat_ids:
            logger.info("LogChannelService: no log channels configured for event %s", event_type)
            return

        message = cls._format_message(text, event_type, urgent)

        for chat_id in chat_ids:
            try:
                await bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=True,
                )
                fire_log(
                    event_type=event_type,
                    channel=f"log_chat:{chat_id}",
                    status="sent",
                    payload=payload or {"text_preview": text[:300]},
                )
            except Exception as e:
                logger.error("Failed to send log event %s to chat %s: %s", event_type, chat_id, e)
                fire_log(
                    event_type=event_type,
                    channel=f"log_chat:{chat_id}",
                    status="failed",
                    error_message=str(e),
                    payload=payload or {"text_preview": text[:300]},
                )
