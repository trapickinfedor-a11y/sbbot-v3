from __future__ import annotations

import logging
import os
from typing import Iterable, Optional

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from sqlalchemy import select

from shared.database.models import Admin, BotOwner, Marketer, Seller, Worker
from shared.database.session import async_session_maker
from shared.services.notification_log_service import fire_log

logger = logging.getLogger(__name__)


class NotificationService:
    """Role-aware notification routing across internal Telegram bots."""

    _bots: dict[str, Bot] = {}
    _ROLE_ALIASES = {
        "marketing": "marketer",
        "bot_owner": "owner",
        "accountant": "finance",
    }

    @classmethod
    def _normalize_role(cls, role: str) -> str:
        return cls._ROLE_ALIASES.get((role or "").strip().lower(), (role or "").strip().lower())

    @classmethod
    def _token_for_role(cls, role: str) -> str:
        normalized = cls._normalize_role(role)
        if normalized in {"support", "moderator", "admin", "super_admin", "worker", "finance"}:
            return os.getenv("SUPPORT_BOT_TOKEN", "").strip()
        if normalized == "seller":
            return os.getenv("SELLER_BOT_TOKEN", "").strip()
        if normalized == "marketer":
            return os.getenv("MARKETER_BOT_TOKEN", "").strip()
        if normalized == "owner":
            return os.getenv("MAIN_BOT_TOKEN", "").strip()
        return ""

    @classmethod
    def _channel_name(cls, role: str) -> str:
        return f"{cls._normalize_role(role)}_bot"

    @classmethod
    def _get_bot(cls, role: str) -> Optional[Bot]:
        normalized = cls._normalize_role(role)
        token = cls._token_for_role(normalized)
        if not token:
            return None
        bot = cls._bots.get(token)
        if bot:
            return bot
        bot = Bot(
            token=token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        cls._bots[token] = bot
        return bot

    @classmethod
    async def _resolve_chat_id(cls, role: str, user_id: int) -> Optional[int]:
        normalized = cls._normalize_role(role)
        async with async_session_maker() as session:
            if normalized in {"support", "moderator", "admin", "super_admin", "finance"}:
                admin = await session.scalar(
                    select(Admin).where(
                        Admin.is_active == True,
                        ((Admin.id == user_id) | (Admin.telegram_id == user_id)),
                    )
                )
                if admin and admin.telegram_id:
                    return int(admin.telegram_id)
                if normalized in {"admin", "super_admin", "finance"}:
                    return int(user_id)
                return None

            if normalized == "worker":
                worker = await session.scalar(
                    select(Worker).where(
                        Worker.is_active == True,
                        Worker.is_suspended == False,
                        ((Worker.id == user_id) | (Worker.telegram_id == user_id)),
                    )
                )
                return int(worker.telegram_id) if worker else None

            if normalized == "seller":
                seller = await session.scalar(
                    select(Seller).where(
                        Seller.is_active == True,
                        ((Seller.id == user_id) | (Seller.telegram_id == user_id)),
                    )
                )
                return int(seller.telegram_id) if seller else None

            if normalized == "marketer":
                marketer = await session.scalar(
                    select(Marketer).where(
                        Marketer.is_active == True,
                        ((Marketer.id == user_id) | (Marketer.telegram_id == user_id)),
                    )
                )
                return int(marketer.telegram_id) if marketer else None

            if normalized == "owner":
                owner = await session.scalar(
                    select(BotOwner).where(
                        (BotOwner.id == user_id) | (BotOwner.owner_user_id == user_id),
                    )
                )
                return int(owner.owner_user_id) if owner else int(user_id)

        return None

    @classmethod
    async def _role_chat_ids(cls, role: str) -> set[int]:
        normalized = cls._normalize_role(role)
        async with async_session_maker() as session:
            if normalized in {"support", "moderator", "admin", "super_admin", "finance"}:
                result = await session.execute(
                    select(Admin.telegram_id).where(
                        Admin.is_active == True,
                        Admin.role == normalized,
                        Admin.telegram_id.is_not(None),
                    )
                )
                chat_ids = {int(chat_id) for chat_id in result.scalars().all() if chat_id}
                if normalized in {"admin", "super_admin"}:
                    for raw_id in os.getenv("ADMIN_IDS", "").split(","):
                        raw_id = raw_id.strip()
                        if raw_id:
                            chat_ids.add(int(raw_id))
                return chat_ids

            if normalized == "worker":
                result = await session.execute(
                    select(Worker.telegram_id).where(
                        Worker.is_active == True,
                        Worker.is_suspended == False,
                    )
                )
                return {int(chat_id) for chat_id in result.scalars().all() if chat_id}

            if normalized == "seller":
                result = await session.execute(
                    select(Seller.telegram_id).where(Seller.is_active == True)
                )
                return {int(chat_id) for chat_id in result.scalars().all() if chat_id}

            if normalized == "marketer":
                result = await session.execute(
                    select(Marketer.telegram_id).where(Marketer.is_active == True)
                )
                return {int(chat_id) for chat_id in result.scalars().all() if chat_id}

            if normalized == "owner":
                result = await session.execute(select(BotOwner.owner_user_id))
                return {int(chat_id) for chat_id in result.scalars().all() if chat_id}

        return set()

    @classmethod
    async def send(
        cls,
        *,
        role: str,
        user_id: int,
        text: str,
        event_type: str = "notification",
    ) -> bool:
        chat_id = await cls._resolve_chat_id(role, user_id)
        if not chat_id:
            fire_log(
                event_type=event_type,
                channel=cls._channel_name(role),
                status="failed",
                recipient_id=user_id,
                error_message="Recipient chat not found",
            )
            return False

        bot = cls._get_bot(role)
        if not bot:
            fire_log(
                event_type=event_type,
                channel=cls._channel_name(role),
                status="failed",
                recipient_id=chat_id,
                error_message="Bot token is not configured",
            )
            return False

        try:
            await bot.send_message(chat_id=chat_id, text=text)
            fire_log(
                event_type=event_type,
                channel=cls._channel_name(role),
                status="sent",
                recipient_id=chat_id,
                payload={"role": cls._normalize_role(role)},
            )
            return True
        except Exception as exc:
            logger.error("Failed to send %s notification to %s/%s: %s", event_type, role, chat_id, exc)
            fire_log(
                event_type=event_type,
                channel=cls._channel_name(role),
                status="failed",
                recipient_id=chat_id,
                error_message=str(exc),
                payload={"role": cls._normalize_role(role)},
            )
            return False

    @classmethod
    async def broadcast(
        cls,
        *,
        roles: Iterable[str],
        text: str,
        event_type: str,
    ) -> int:
        sent = 0
        seen: set[tuple[str, int]] = set()
        for role in roles:
            normalized = cls._normalize_role(role)
            for chat_id in await cls._role_chat_ids(normalized):
                key = (normalized, chat_id)
                if key in seen:
                    continue
                seen.add(key)
                bot = cls._get_bot(normalized)
                if not bot:
                    fire_log(
                        event_type=event_type,
                        channel=cls._channel_name(normalized),
                        status="failed",
                        recipient_id=chat_id,
                        error_message="Bot token is not configured",
                    )
                    continue
                try:
                    await bot.send_message(chat_id=chat_id, text=text)
                    sent += 1
                    fire_log(
                        event_type=event_type,
                        channel=cls._channel_name(normalized),
                        status="sent",
                        recipient_id=chat_id,
                        payload={"role": normalized},
                    )
                except Exception as exc:
                    logger.error("Failed to broadcast %s to %s/%s: %s", event_type, normalized, chat_id, exc)
                    fire_log(
                        event_type=event_type,
                        channel=cls._channel_name(normalized),
                        status="failed",
                        recipient_id=chat_id,
                        error_message=str(exc),
                        payload={"role": normalized},
                    )
        return sent
