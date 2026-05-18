"""
Утилиты для мультиязычности в web_panel.
Поддерживаемые языки: en, ru, zh, es
"""

import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from shared.database.models import User

logger = logging.getLogger(__name__)

_ADMIN_MESSAGE_PREFIX = {
    "ru": "📢 Сообщение от администратора:\n\n",
    "zh": "📢 管理员消息:\n\n",
    "es": "📢 Mensaje del administrador:\n\n",
    "en": "📢 Message from Admin:\n\n",
}

_ADMIN_BROADCAST_PREFIX = {
    "ru": "📢 Массовая рассылка от администрации:\n\n",
    "zh": "📢 管理部门群发消息:\n\n",
    "es": "📢 Mensaje masivo de la administración:\n\n",
    "en": "📢 Mass Broadcast from Administration:\n\n",
}


async def _get_user_language(session: AsyncSession, user_id: int, mirror_bot_id: int) -> str:
    try:
        result = await session.execute(
            select(User.language).where(
                User.user_id == user_id,
                User.mirror_bot_id == mirror_bot_id,
            )
        )
        lang = result.scalar_one_or_none()
        return (lang or "en").lower()
    except Exception as exc:
        logger.error("Error getting user language for user_id=%s: %s", user_id, exc)
        return "en"


async def get_user_admin_message_prefix(
    session: AsyncSession, user_id: int, mirror_bot_id: int
) -> str:
    """Вернуть мультиязычный префикс сообщения от администратора для пользователя."""
    lang = await _get_user_language(session, user_id, mirror_bot_id)
    return _ADMIN_MESSAGE_PREFIX.get(lang, _ADMIN_MESSAGE_PREFIX["en"])


async def get_user_admin_broadcast_prefix(
    session: AsyncSession, user_id: int, mirror_bot_id: int
) -> str:
    """Вернуть мультиязычный префикс массовой рассылки от администратора."""
    lang = await _get_user_language(session, user_id, mirror_bot_id)
    return _ADMIN_BROADCAST_PREFIX.get(lang, _ADMIN_BROADCAST_PREFIX["en"])
