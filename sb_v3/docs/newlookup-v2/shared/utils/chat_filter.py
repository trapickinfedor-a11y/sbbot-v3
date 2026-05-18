"""
Newlookup v24 — Обновлённый chat_filter.py
Файл: shared/utils/chat_filter_v24.py

ИНСТРУКЦИЯ: Замени содержимое shared/utils/chat_filter.py этим файлом.

ИЗМЕНЕНИЯ по сравнению с v2:
1. Добавлена функция filter_and_log() — фильтрует И логирует нарушение в БД
2. Добавлена проверка email-адресов
3. Добавлена проверка Discord/WhatsApp/Telegram ников
4. Счётчик нарушений воркера увеличивается при каждом нарушении
"""

import logging
import re
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# ── Паттерны для фильтрации ───────────────────────────────────
PATTERNS = {
    "url": re.compile(r"(https?://[^\s]+)|(www\.[^\s]+)|(t\.me/[^\s]+)", re.IGNORECASE),
    "email": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    "discord": re.compile(r"\b\w+#\d{4}\b"),
    "whatsapp": re.compile(r"(whatsapp|wa\.me|signal|telegram|tg)\s*:?\s*[^\s]+", re.IGNORECASE),
    "phone": re.compile(r"\+\d{10,15}|\b\d{10,15}\b"),
    "telegram_username": re.compile(r"@\w+", re.IGNORECASE),
}

REPLACEMENTS = {
    "telegram_username": "[КОНТАКТ СКРЫТ]",
    "url": "[ССЫЛКА СКРЫТА]",
    "phone": "[ТЕЛЕФОН СКРЫТ]",
    "email": "[EMAIL СКРЫТ]",
    "discord": "[КОНТАКТ СКРЫТ]",
    "whatsapp": "[КОНТАКТ СКРЫТ]",
}


def filter_message(text: str) -> str:
    """
    Фильтрует контактные данные из текста.
    Возвращает отфильтрованный текст.

    Совместима с v2 — замена drop-in.
    """
    if not text or not isinstance(text, str):
        return text or ""

    for pattern_name, pattern in PATTERNS.items():
        text = pattern.sub(REPLACEMENTS[pattern_name], text)

    return text.strip()


def is_message_blocked(text: str) -> bool:
    """
    True если сообщение содержит ТОЛЬКО заблокированный контент.
    Совместима с v2 — замена drop-in.
    """
    if not text:
        return True
    filtered = filter_message(text)
    sanitized = filtered
    for replacement in set(REPLACEMENTS.values()):
        sanitized = sanitized.replace(replacement, " ")
    sanitized = re.sub(r"[\W_]+", "", sanitized, flags=re.UNICODE)
    return not sanitized


def check_violations(text: str) -> list[str]:
    """
    Возвращает список типов нарушений в тексте.
    Новая функция v24.

    Пример: ["telegram_username", "phone"]
    """
    violations = []
    for pattern_name, pattern in PATTERNS.items():
        if pattern.search(text):
            violations.append(pattern_name)
    return violations


async def filter_and_log(
    text: str,
    worker_id: int,
    order_id: Optional[int],
    session,
) -> Tuple[str, bool]:
    """
    Фильтрует текст И логирует нарушение в БД если оно есть.

    Новая функция v24. Используй вместо filter_message() в worker_bot.

    Возвращает: (filtered_text, was_violation)

    Пример использования:
        filtered, violated = await filter_and_log(
            text=message.text,
            worker_id=worker.id,
            order_id=order_id,
            session=session
        )
    """
    violations = check_violations(text)
    filtered_text = filter_message(text)
    was_violation = len(violations) > 0

    if was_violation:
        try:
            from sqlalchemy import select
            from shared.database.models import Worker, WorkerViolation

            try:
                session.add(
                    WorkerViolation(
                        worker_id=worker_id,
                        order_id=order_id,
                        violation_type=",".join(violations),
                        original_text=text[:1000],
                        filtered_text=filtered_text[:1000],
                    )
                )

                worker_result = await session.execute(
                    select(Worker).where(Worker.id == worker_id)
                )
                worker = worker_result.scalar_one_or_none()
                if worker and hasattr(worker, "violation_count"):
                    worker.violation_count += 1

                await session.flush()

            except Exception as db_err:
                logger.warning(f"Could not log violation to DB: {db_err}")

            logger.warning(
                f"Worker {worker_id} violation in order {order_id}: "
                f"types={violations}"
            )

        except Exception as e:
            logger.error(f"filter_and_log error: {e}")

    return filtered_text, was_violation
