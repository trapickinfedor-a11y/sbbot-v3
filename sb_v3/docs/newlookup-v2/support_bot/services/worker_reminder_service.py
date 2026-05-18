from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from shared.database.models import Order, Worker
from shared.database.task_models import WorkerReminderTask
from shared.database.tasks_session import tasks_session_maker
from shared.services.pricing_config_service import PricingConfigService
from support_bot.keyboards.inline import working_order_keyboard

logger = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 7200


async def run_worker_order_reminder_watcher(
    stop_event: asyncio.Event,
    session_maker: async_sessionmaker,
    bot,
) -> None:
    while not stop_event.is_set():
        try:
            await _process_worker_order_reminders(session_maker, bot)
        except Exception as exc:
            logger.warning("Worker order reminder watcher failed: %s", exc)

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=CHECK_INTERVAL_SECONDS)
        except asyncio.TimeoutError:
            continue


async def _process_worker_order_reminders(session_maker: async_sessionmaker, bot) -> None:
    async with session_maker() as session:
        enabled = await PricingConfigService.get_value(session, "worker_order_reminder_enabled", True)
        if not enabled:
            return

        reminder_hours = await PricingConfigService.get_value(session, "worker_order_reminder_hours", 2)
        reminder_delta = timedelta(hours=float(reminder_hours or 2))
        cutoff = datetime.utcnow() - reminder_delta

        result = await session.execute(
            select(Order, Worker)
            .join(Worker, Worker.id == Order.worker_id)
            .where(
                Order.worker_id.is_not(None),
                Order.status == "processing",
                Order.taken_at.is_not(None),
                Order.taken_at <= cutoff,
                Worker.is_active == True,
                Worker.is_suspended == False,
            )
        )
        rows = result.all()
        if not rows:
            return

        for order, worker in rows:
            last_reminder_at = getattr(order, "last_worker_reminder_at", None)
            if last_reminder_at and last_reminder_at > cutoff:
                continue

            try:
                await bot.send_message(
                    chat_id=worker.telegram_id,
                    text=(
                        f"⏰ <b>Reminder for Order #{order.id}</b>\n\n"
                        f"Service: <b>{order.service_name}</b>\n"
                        f"Category: <b>{order.category}</b>\n"
                        f"Taken at: {order.taken_at.strftime('%Y-%m-%d %H:%M') if order.taken_at else 'unknown'}\n\n"
                        "This order is still in progress. Please complete it, mark NF, cancel it, or send a complaint."
                    ),
                    reply_markup=working_order_keyboard(
                        order.id,
                        is_bulk=bool(order.is_bulk),
                        category=order.category,
                    ),
                )
                order.last_worker_reminder_at = datetime.utcnow()
                async with tasks_session_maker() as task_session:
                    task = await task_session.scalar(
                        select(WorkerReminderTask).where(
                            WorkerReminderTask.order_id == order.id,
                            WorkerReminderTask.status == "pending",
                            WorkerReminderTask.is_active == True,
                        )
                    )
                    if task:
                        task.status = "sent"
                        task.sent_at = datetime.utcnow()
                        task.is_active = False
                        await task_session.commit()
            except Exception as exc:
                logger.warning("Failed to send worker reminder for order %s: %s", order.id, exc)
                async with tasks_session_maker() as task_session:
                    task = await task_session.scalar(
                        select(WorkerReminderTask).where(
                            WorkerReminderTask.order_id == order.id,
                            WorkerReminderTask.status == "pending",
                            WorkerReminderTask.is_active == True,
                        )
                    )
                    if task:
                        task.last_error = str(exc)
                        await task_session.commit()

        await session.commit()
