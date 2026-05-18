"""BIN Lookup Service — auto-fills card TYPE / BRAND / LEVEL / BANK from first 6 digits."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Optional

import aiohttp

logger = logging.getLogger(__name__)

_BIN_API_URL = "https://lookup.binlist.net/{bin}"
_CACHE_MAX = 2000
_CACHE_TTL = 86400  # 24 hours
_REQUEST_TIMEOUT = 8  # seconds
_MIN_REQUEST_INTERVAL = 0.25  # 250ms between API calls (rate-limit guard)


@dataclass(frozen=True)
class BinInfo:
    card_brand: str | None    # visa, mastercard, amex, discover
    card_type: str | None     # debit, credit, prepaid
    card_level: str | None    # Classic, Gold, Platinum, Signature …
    bank_name: str | None     # issuer name
    country: str | None       # alpha-2 country code


_cache: dict[str, tuple[BinInfo | None, float]] = {}
_last_request_ts: float = 0.0
_lock: Optional[asyncio.Lock] = None


def _get_lock() -> asyncio.Lock:
    """Lazy initialization of lock to avoid event loop issues at import time."""
    global _lock
    if _lock is None:
        _lock = asyncio.Lock()
    return _lock


def _evict_stale() -> None:
    """Remove expired entries when cache exceeds max size."""
    if len(_cache) <= _CACHE_MAX:
        return
    now = time.monotonic()
    expired = [k for k, (_, ts) in _cache.items() if now - ts > _CACHE_TTL]
    for k in expired:
        _cache.pop(k, None)
    if len(_cache) > _CACHE_MAX:
        oldest = sorted(_cache, key=lambda k: _cache[k][1])
        for k in oldest[: len(_cache) - _CACHE_MAX]:
            _cache.pop(k, None)


class BinLookupService:

    @staticmethod
    async def lookup(bin_prefix: str) -> BinInfo | None:
        """Look up BIN (first 6-8 digits) via binlist.net with LRU cache.

        Returns None on any failure — callers should keep existing values.
        """
        global _last_request_ts

        clean = (bin_prefix or "").strip()[:8]
        if len(clean) < 6 or not clean.isdigit():
            return None

        key = clean[:6]

        cached = _cache.get(key)
        if cached is not None:
            info, ts = cached
            if time.monotonic() - ts < _CACHE_TTL:
                return info

        async with _get_lock():
            cached = _cache.get(key)
            if cached is not None:
                info, ts = cached
                if time.monotonic() - ts < _CACHE_TTL:
                    return info

            now = time.monotonic()
            wait = _MIN_REQUEST_INTERVAL - (now - _last_request_ts)
            if wait > 0:
                await asyncio.sleep(wait)

            info = await BinLookupService._fetch(key)
            _last_request_ts = time.monotonic()
            _evict_stale()
            _cache[key] = (info, time.monotonic())
            return info

    @staticmethod
    async def _fetch(bin6: str) -> BinInfo | None:
        url = _BIN_API_URL.format(bin=bin6)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers={"Accept-Version": "3"},
                    timeout=aiohttp.ClientTimeout(total=_REQUEST_TIMEOUT),
                ) as resp:
                    if resp.status == 404:
                        return None
                    if resp.status == 429:
                        logger.warning("BIN lookup rate-limited (429) for %s", bin6)
                        return None
                    if resp.status != 200:
                        logger.warning("BIN lookup HTTP %s for %s", resp.status, bin6)
                        return None
                    data = await resp.json(content_type=None)
        except Exception as exc:
            logger.warning("BIN lookup failed for %s: %s", bin6, exc)
            return None

        if not isinstance(data, dict):
            return None

        scheme = (data.get("scheme") or "").strip().lower()
        brand_map = {"visa": "Visa", "mastercard": "Mastercard", "amex": "Amex",
                     "american express": "Amex", "discover": "Discover",
                     "jcb": "JCB", "unionpay": "UnionPay", "maestro": "Maestro"}
        card_brand = brand_map.get(scheme, scheme.title() if scheme else None)

        card_type_raw = (data.get("type") or "").strip().lower()
        card_type = card_type_raw.upper() if card_type_raw else None

        card_level = (data.get("brand") or "").strip() or None

        bank_obj = data.get("bank") or {}
        bank_name = (bank_obj.get("name") or "").strip() or None

        country_obj = data.get("country") or {}
        country = (country_obj.get("alpha2") or "").strip().upper() or None

        return BinInfo(
            card_brand=card_brand,
            card_type=card_type,
            card_level=card_level,
            bank_name=bank_name,
            country=country,
        )

    @staticmethod
    async def enrich_parsed(parsed: dict) -> dict:
        """Fill empty card_type / card_brand / card_level / bank_name from BIN lookup.

        Mutates and returns the same dict for convenience.
        """
        number = parsed.get("number") or ""
        if len(number) < 6:
            return parsed

        needs_brand = not parsed.get("card_brand")
        needs_type = not (parsed.get("extra_data") or {}).get("card_type")
        needs_level = not parsed.get("card_level")
        needs_bank = not parsed.get("bank_name")
        needs_country = not parsed.get("country")

        if not (needs_brand or needs_type or needs_level or needs_bank or needs_country):
            return parsed

        info = await BinLookupService.lookup(number[:6])
        if info is None:
            return parsed

        if needs_brand and info.card_brand:
            parsed["card_brand"] = info.card_brand
            extra = parsed.get("extra_data") or {}
            extra["brand"] = info.card_brand
            parsed["extra_data"] = extra

        if needs_type and info.card_type:
            extra = parsed.get("extra_data") or {}
            extra["card_type"] = info.card_type
            parsed["extra_data"] = extra

        if needs_level and info.card_level:
            parsed["card_level"] = info.card_level
            extra = parsed.get("extra_data") or {}
            extra["level"] = info.card_level
            parsed["extra_data"] = extra

        if needs_bank and info.bank_name:
            parsed["bank_name"] = info.bank_name
            extra = parsed.get("extra_data") or {}
            extra["bank"] = info.bank_name
            parsed["extra_data"] = extra

        if needs_country and info.country:
            parsed["country"] = info.country
            extra = parsed.get("extra_data") or {}
            extra["country"] = info.country
            parsed["extra_data"] = extra

        return parsed
