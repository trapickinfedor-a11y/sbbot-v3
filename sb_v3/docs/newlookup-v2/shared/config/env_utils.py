from __future__ import annotations

import os


class StartupValidationError(RuntimeError):
    pass


def parse_int_env(name: str, default: int) -> int:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc


def parse_float_env(name: str, default: float) -> float:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number") from exc


def parse_int_list_env(name: str) -> list[int]:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return []

    values: list[int] = []
    for chunk in raw.split(","):
        item = chunk.strip()
        if not item:
            continue
        try:
            values.append(int(item))
        except ValueError as exc:
            raise ValueError(f"{name} must be a comma-separated list of integers") from exc
    return values


def validate_startup_env(
    service_name: str,
    *,
    required: list[str] | None = None,
    require_one_of: list[tuple[str, ...]] | None = None,
    optional: list[str] | None = None,
) -> list[str]:
    required = required or []
    require_one_of = require_one_of or []
    optional = optional or []

    missing = [name for name in required if not (os.getenv(name) or "").strip()]
    invalid_groups = [
        group for group in require_one_of
        if not any((os.getenv(name) or "").strip() for name in group)
    ]

    if missing or invalid_groups:
        details: list[str] = []
        if missing:
            details.append("missing required env vars: " + ", ".join(missing))
        if invalid_groups:
            details.append(
                "missing one-of groups: " + ", ".join(" / ".join(group) for group in invalid_groups)
            )
        raise StartupValidationError(f"{service_name} startup validation failed: {'; '.join(details)}")

    warnings = [
        f"{service_name} optional env var not set: {name}"
        for name in optional
        if not (os.getenv(name) or "").strip()
    ]
    return warnings
