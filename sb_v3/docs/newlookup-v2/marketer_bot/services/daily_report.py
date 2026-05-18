"""Daily auto-report — background task, sends at 21:00 MSK, respects language."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, time, timedelta, timezone

from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import Marketer
from shared.database.session import async_session_maker
from marketer_bot.constants.language_loader import get_texts
from marketer_bot.services.analytics_service import build_daily_report

logger = logging.getLogger(__name__)

MSK = timezone(timedelta(hours=3))
REPORT_TIME = time(21, 0)


def _seconds_until(target: time, tz: timezone) -> float:
    now = datetime.now(tz)
    target_dt = datetime.combine(now.date(), target, tzinfo=tz)
    if target_dt <= now:
        target_dt += timedelta(days=1)
    return (target_dt - now).total_seconds()


async def _send_reports(bot: Bot) -> None:
    sent = 0
    failed = 0
    async with async_session_maker() as session:
        result = await session.execute(
            select(Marketer).where(Marketer.is_active == True)
        )
        marketers = list(result.scalars().all())

        for marketer in marketers:
            try:
                t = get_texts(marketer.language)
                text = await build_daily_report(session, marketer.id, t)
                await bot.send_message(marketer.telegram_id, text, parse_mode="HTML")
                sent += 1
            except Exception as e:
                logger.warning("Daily report to %s failed: %s", marketer.telegram_id, e)
                failed += 1
            await asyncio.sleep(0.1)

    logger.info("Daily reports sent: %d ok, %d failed", sent, failed)


async def run_daily_report_loop(bot: Bot) -> None:
    logger.info("Daily report scheduler started (target: %s MSK)", REPORT_TIME)
    while True:
        wait = _seconds_until(REPORT_TIME, MSK)
        logger.info("Next daily report in %.0f seconds", wait)
        await asyncio.sleep(wait)
        try:
            await _send_reports(bot)
        except Exception:
            logger.exception("Daily report loop error")
        await asyncio.sleep(60)
