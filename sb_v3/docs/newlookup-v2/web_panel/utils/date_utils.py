"""
Общие утилиты для работы с диапазонами дат в web_panel.
Используется вместо дублирующихся _resolve_date_range в каждом роутере.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional


def resolve_date_range(
    date_from: Optional[str],
    date_to: Optional[str],
    default_days: int = 30,
) -> tuple[datetime, datetime]:
    """
    Преобразует строки дат YYYY-MM-DD в диапазон datetime.

    - Если задан date_from — берётся как начало.
    - Если задан только date_to — начало = date_to - default_days.
    - Если оба None — конец = сейчас, начало = сейчас - default_days.
    """
    now = datetime.now(timezone.utc)

    if date_from:
        start_dt = datetime.strptime(date_from, "%Y-%m-%d")
    elif date_to:
        end_base = datetime.strptime(date_to, "%Y-%m-%d")
        start_dt = end_base - timedelta(days=max(default_days - 1, 0))
    else:
        start_dt = now - timedelta(days=default_days)

    if date_to:
        end_dt = datetime.strptime(date_to, "%Y-%m-%d") + timedelta(days=1)
    else:
        end_dt = now + timedelta(seconds=1)

    return start_dt, end_dt
