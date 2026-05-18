"""
Cached Bot instance pool to avoid creating new Bot() on every message relay.
Uses a simple dict cache with lazy initialization.
"""

from aiogram import Bot
from typing import Optional
import logging

logger = logging.getLogger(__name__)

_bot_cache: dict[str, Bot] = {}


def get_bot(token: str) -> Bot:
    """Get or create a cached Bot instance for the given token."""
    if token not in _bot_cache:
        _bot_cache[token] = Bot(token=token)
        logger.debug(f"Created new Bot instance for token {token[:10]}...")
    return _bot_cache[token]


async def close_bot(token: str):
    """Close and remove a cached Bot instance."""
    if token in _bot_cache:
        try:
            await _bot_cache[token].session.close()
        except Exception:
            pass
        del _bot_cache[token]


async def close_all():
    """Close all cached Bot instances."""
    for token, bot in list(_bot_cache.items()):
        try:
            await bot.session.close()
        except Exception:
            pass
    _bot_cache.clear()


def get_seller_bot() -> Optional[Bot]:
    """Get cached seller bot instance."""
    from seller_bot.config import seller_bot_config
    if not seller_bot_config.bot_token:
        return None
    return get_bot(seller_bot_config.bot_token)


def get_support_bot() -> Optional[Bot]:
    """Get cached support bot instance."""
    from support_bot.config import support_bot_config
    if not support_bot_config.bot_token:
        return None
    return get_bot(support_bot_config.bot_token)


def get_mirror_bot_instance(token: str) -> Bot:
    """Get cached mirror bot instance by token."""
    return get_bot(token)
