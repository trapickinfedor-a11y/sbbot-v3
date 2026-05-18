"""
shared/i18n — centralised internationalisation helper.

Usage:
    from shared.i18n import t, get_locale, SUPPORTED_LANGS

    text = t("common.choose_language", "ru")
    text = t("seller.welcome_back", "en", name="Alice", total_orders=5, total_earned=120.0)
"""
from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

SUPPORTED_LANGS = ("en", "ru", "es", "zh")
DEFAULT_LANG = "en"

_LOCALES_DIR = Path(__file__).parent / "locales"


@lru_cache(maxsize=None)
def _load_locale(lang: str) -> dict:
    """Load and cache a locale JSON file."""
    path = _LOCALES_DIR / f"{lang}.json"
    if not path.exists():
        logger.warning("Locale file not found: %s, falling back to %s", path, DEFAULT_LANG)
        fallback = _LOCALES_DIR / f"{DEFAULT_LANG}.json"
        with fallback.open(encoding="utf-8") as f:
            return json.load(f)
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _resolve_key(data: dict, key: str):
    """Navigate dot-separated key path in nested dict."""
    parts = key.split(".")
    node = data
    for part in parts:
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            return None
    return node


def t(key: str, lang: Optional[str] = None, **kwargs) -> str:
    """
    Translate *key* to *lang* (default: 'en').

    Supports format placeholders:
        t("seller.welcome_back", "ru", name="Vasya", total_orders=3, total_earned=50.0)

    Falls back to English if the key is missing in the requested language.
    Returns the key itself if not found anywhere.
    """
    effective_lang = lang if lang in SUPPORTED_LANGS else DEFAULT_LANG

    locale = _load_locale(effective_lang)
    value = _resolve_key(locale, key)

    if value is None and effective_lang != DEFAULT_LANG:
        # Fallback to default language
        fallback_locale = _load_locale(DEFAULT_LANG)
        value = _resolve_key(fallback_locale, key)

    if value is None:
        logger.debug("Missing i18n key '%s' for lang '%s'", key, effective_lang)
        return key  # return raw key so UI still shows something

    if kwargs:
        try:
            return str(value).format(**kwargs)
        except (KeyError, ValueError) as exc:
            logger.warning("i18n format error for key '%s': %s", key, exc)
            return str(value)

    return str(value)


def get_locale(lang: Optional[str] = None) -> dict:
    """Return the full locale dict for *lang*."""
    effective_lang = lang if lang in SUPPORTED_LANGS else DEFAULT_LANG
    return _load_locale(effective_lang)


def reload_locales() -> None:
    """Clear the locale cache (useful for hot-reload in development)."""
    _load_locale.cache_clear()
