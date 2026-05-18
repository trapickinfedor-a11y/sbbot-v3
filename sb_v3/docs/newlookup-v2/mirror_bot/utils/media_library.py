from __future__ import annotations

from pathlib import Path
from typing import Iterable

from aiogram.types import FSInputFile


WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
PHOTO_DIR = WORKSPACE_ROOT / "photo"
MEDIA_DIR = WORKSPACE_ROOT / "media"
SUPPORTED_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".gif")


def _candidate_names(*keys: str) -> list[str]:
    candidates: list[str] = []
    for key in keys:
        normalized = (key or "").strip()
        if not normalized:
            continue
        candidates.extend(
            [
                normalized,
                normalized.lower(),
                normalized.replace("_", " "),
                normalized.replace("_", "-"),
                normalized.replace(" ", "_"),
                normalized.replace(" ", "-"),
            ]
        )
    seen: set[str] = set()
    unique: list[str] = []
    for item in candidates:
        lowered = item.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        unique.append(item)
    return unique


def _iter_candidate_paths(directory: Path, names: Iterable[str]) -> list[Path]:
    paths: list[Path] = []
    for name in names:
        raw_path = directory / name
        if raw_path.suffix.lower() in SUPPORTED_EXTENSIONS:
            paths.append(raw_path)
        else:
            for extension in SUPPORTED_EXTENSIONS:
                paths.append(directory / f"{name}{extension}")
    return paths


def resolve_bot_photo(*keys: str, fallback_path: str | None = None) -> FSInputFile | None:
    names = _candidate_names(*keys)
    for directory in (PHOTO_DIR, MEDIA_DIR):
        for candidate in _iter_candidate_paths(directory, names):
            if candidate.exists() and candidate.is_file():
                return FSInputFile(str(candidate))
    if fallback_path:
        fallback_file = WORKSPACE_ROOT / fallback_path
        if fallback_file.exists() and fallback_file.is_file():
            return FSInputFile(str(fallback_file))
    return None
