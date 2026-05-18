from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import UiTranslation


@dataclass
class UiTranslator:
    session: AsyncSession | None
    language: str = "en"
    namespace: str | None = None

    async def get(self, key: str, default: str | None = None, *, namespace: str | None = None, **fmt: Any) -> str:
        text_value = await get_ui_text(
            self.session,
            key,
            language=self.language,
            default=default,
            namespace=namespace or self.namespace,
        )
        if fmt:
            try:
                return text_value.format(**fmt)
            except Exception:
                return text_value
        return text_value


async def get_ui_text(
    session: AsyncSession | None,
    key: str,
    *,
    language: str = "en",
    default: str | None = None,
    namespace: str | None = None,
) -> str:
    if not session:
        return default or key

    stmt = select(UiTranslation.text_value).where(
        UiTranslation.key == key,
        UiTranslation.language == (language or "en"),
    )
    if namespace:
        stmt = stmt.where((UiTranslation.namespace == namespace) | (UiTranslation.namespace.is_(None)))
    stmt = stmt.order_by(UiTranslation.namespace.desc())
    result = await session.execute(stmt.limit(1))
    text_value = result.scalar_one_or_none()
    if text_value:
        return text_value

    fallback_stmt = select(UiTranslation.text_value).where(
        UiTranslation.key == key,
        UiTranslation.language == "en",
    )
    if namespace:
        fallback_stmt = fallback_stmt.where((UiTranslation.namespace == namespace) | (UiTranslation.namespace.is_(None)))
    fallback_stmt = fallback_stmt.order_by(UiTranslation.namespace.desc())
    fallback_result = await session.execute(fallback_stmt.limit(1))
    fallback_value = fallback_result.scalar_one_or_none()
    if fallback_value:
        return fallback_value
    return default or key


async def upsert_ui_translation(
    session: AsyncSession,
    *,
    key: str,
    language: str,
    text_value: str,
    namespace: str | None = None,
) -> UiTranslation:
    existing = await session.scalar(
        select(UiTranslation).where(
            UiTranslation.key == key,
            UiTranslation.language == language,
            UiTranslation.namespace == namespace,
        )
    )
    if existing:
        existing.text_value = text_value
        await session.flush()
        return existing

    row = UiTranslation(
        key=key,
        language=language,
        text_value=text_value,
        namespace=namespace,
    )
    session.add(row)
    await session.flush()
    return row
