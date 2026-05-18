"""Language loader for Marketer Bot"""
from __future__ import annotations
import importlib
from typing import Any, Dict, Optional


SUPPORTED_LANGUAGES = ["ru", "en", "zh", "es"]
DEFAULT_LANGUAGE = "ru"

_cache: Dict[str, Any] = {}


def get_texts(language: Optional[str] = None) -> Any:
    lang = language if language in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE
    if lang not in _cache:
        try:
            module = importlib.import_module(f"marketer_bot.constants.texts_{lang}")
        except ImportError:
            module = importlib.import_module(f"marketer_bot.constants.texts_{DEFAULT_LANGUAGE}")
        _cache[lang] = module.MarketerTexts
    return _cache[lang]
