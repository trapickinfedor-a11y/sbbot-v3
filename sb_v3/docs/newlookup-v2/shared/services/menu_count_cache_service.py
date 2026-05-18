from __future__ import annotations

import json

try:
    from redis.asyncio import Redis, from_url as _redis_from_url
    def from_url(url: str, **kwargs):
        return _redis_from_url(url, **kwargs)
except ImportError:
    Redis = None  # type: ignore
    def from_url(url: str, **kwargs):  # type: ignore
        return None

from shared.config.settings import global_settings


class MenuCountCacheService:
    KEY_PREFIX = "mirror_bot:menu_counts:v1"
    TTL_SECONDS = 60 * 10

    @classmethod
    async def _get_redis(cls) -> Redis | None:
        try:
            return from_url(global_settings.redis_url, encoding="utf-8", decode_responses=True)
        except Exception:
            return None

    @classmethod
    def _cache_key(cls, name: str) -> str:
        return f"{cls.KEY_PREFIX}:{name}"

    @classmethod
    async def get_counts(cls, name: str) -> dict | None:
        redis = await cls._get_redis()
        if redis is None:
            return None
        try:
            raw = await redis.get(cls._cache_key(name))
            if not raw:
                return None
            return json.loads(raw)
        except Exception:
            return None
        finally:
            await redis.aclose()

    @classmethod
    async def set_counts(cls, name: str, payload: dict) -> None:
        redis = await cls._get_redis()
        if redis is None:
            return
        try:
            await redis.set(
                cls._cache_key(name),
                json.dumps(payload),
                ex=cls.TTL_SECONDS,
            )
        except Exception:
            return
        finally:
            await redis.aclose()

    @classmethod
    async def warm_all_counts(cls, session) -> dict:
        from mirror_bot.services.menu_counts_service import MenuCountService

        payload = {
            "documents": await MenuCountService.build_documents_counts(session),
            "fullz": await MenuCountService.build_fullz_counts(session),
            "banks": await MenuCountService.build_banks_counts(session),
            "cc": await MenuCountService.build_cc_counts(session),
            "seller_specials": await MenuCountService.build_seller_specials_counts(session),
            "accounts": await MenuCountService.build_accounts_counts(session),
            "education": await MenuCountService.build_education_counts(session),
        }
        for key, value in payload.items():
            await cls.set_counts(key, value)
        return payload
