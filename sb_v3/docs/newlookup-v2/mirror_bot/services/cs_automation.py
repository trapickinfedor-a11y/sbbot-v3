from __future__ import annotations

import asyncio
import logging
import random
from datetime import datetim, timezone
from decimal import Decimal
from typing import Optional

from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from scripts.universal_credit_parser import run_funnel
from mirror_bot.keyboards.inline import cs_retry_keyboard
from mirror_bot.services.user_service import UserService
from shared.database.models import (
    AutomationConfig,
    AutomationFinanceEntry,
    AutomationJob,
    AutomationProxy,
    BulkOrderItem,
    Order,
)
from shared.database.session import async_session_maker
from shared.services.admin_notification_service import AdminNotificationService
from support_bot.services.balance_service import BalanceService
from support_bot.services.order_service import OrderService as SupportOrderService

logger = logging.getLogger(__name__)

_DEFAULT_WORKERS = 10
_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]
_TIMEZONES = [
    "America/New_York",
    "America/Chicago",
    "America/Denver",
    "America/Los_Angeles",
    "America/Phoenix",
]
_LOCALES = ["en-US", "en"]
_VIEWPORTS = [
    {"width": 1366, "height": 768},
    {"width": 1440, "height": 900},
    {"width": 1920, "height": 1080},
]


class CsAutomationRunner:
    """Локальный раннер CS automation внутри client bot."""

    def __init__(self, bot: Bot, mirror_bot_id: int):
        self.bot = bot
        self.mirror_bot_id = mirror_bot_id
        self._running = False
        self._queue: asyncio.Queue[Optional[int]] = asyncio.Queue()
        self._poller_task: Optional[asyncio.Task] = None
        self._worker_tasks: list[asyncio.Task] = []
        self._scheduled_job_ids: set[int] = set()

    async def start(self):
        if self._running:
            return

        config = await self._ensure_config()
        worker_count = max(1, int(config.worker_count or _DEFAULT_WORKERS))

        self._running = True
        self._poller_task = asyncio.create_task(self._poll_jobs_loop(), name=f"cs-poller-{self.mirror_bot_id}")
        for worker_idx in range(worker_count):
            task = asyncio.create_task(self._worker_loop(worker_idx + 1), name=f"cs-worker-{self.mirror_bot_id}-{worker_idx + 1}")
            self._worker_tasks.append(task)

        logger.info("CS automation runner started for mirror bot %s with %s workers", self.mirror_bot_id, worker_count)

    async def stop(self):
        if not self._running:
            return

        self._running = False
        if self._poller_task:
            self._poller_task.cancel()

        for _ in self._worker_tasks:
            await self._queue.put(None)

        if self._worker_tasks:
            await asyncio.gather(*self._worker_tasks, return_exceptions=True)
        if self._poller_task:
            await asyncio.gather(self._poller_task, return_exceptions=True)

        self._worker_tasks.clear()
        self._scheduled_job_ids.clear()
        logger.info("CS automation runner stopped for mirror bot %s", self.mirror_bot_id)

    async def enqueue_order(self, order_id: int):
        """Создать automation jobs для single/bulk order и отправить их в локальный раннер."""
        async with async_session_maker() as session:
            order = await self._load_order(session, order_id)
            if not order or order.service_name != "lookup_credit":
                return

            existing_result = await session.execute(
                select(AutomationJob.id).where(AutomationJob.order_id == order.id)
            )
            existing_ids = [row[0] for row in existing_result.all()]
            if existing_ids:
                await self._schedule_jobs(existing_ids)
                return

            order.status = "processing"
            if not order.taken_at:
                order.taken_at = datetime.now(timezone.utc)

            new_jobs: list[AutomationJob] = []
            if order.is_bulk:
                for item in order.bulk_items:
                    new_jobs.append(
                        AutomationJob(
                            order_id=order.id,
                            bulk_item_number=item.item_number,
                            service_code="lookup_credit",
                            status="queued",
                            user_id=order.user_id,
                            mirror_bot_id=order.mirror_bot_id,
                            input_payload=item.input_data or {},
                            priority=100,
                        )
                    )
            else:
                new_jobs.append(
                    AutomationJob(
                        order_id=order.id,
                        service_code="lookup_credit",
                        status="queued",
                        user_id=order.user_id,
                        mirror_bot_id=order.mirror_bot_id,
                        input_payload=order.input_data or {},
                        priority=100,
                    )
                )

            session.add_all(new_jobs)
            await session.commit()

            job_ids = [job.id for job in new_jobs]
            await self._schedule_jobs(job_ids)

    async def _poll_jobs_loop(self):
        while self._running:
            try:
                config = await self._ensure_config()
                if not config.is_enabled:
                    await asyncio.sleep(5)
                    continue

                async with async_session_maker() as session:
                    result = await session.execute(
                        select(AutomationJob)
                        .where(
                            AutomationJob.mirror_bot_id == self.mirror_bot_id,
                            AutomationJob.service_code == "lookup_credit",
                            AutomationJob.status.in_(["queued", "assigned"]),
                        )
                        .order_by(AutomationJob.priority.asc(), AutomationJob.created_at.asc())
                        .limit(100)
                    )
                    jobs = result.scalars().all()

                    ready_ids = []
                    for job in jobs:
                        if job.id in self._scheduled_job_ids:
                            continue
                        if job.status == "queued":
                            job.status = "assigned"
                        ready_ids.append(job.id)

                    if ready_ids:
                        await session.commit()
                        await self._schedule_jobs(ready_ids)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.exception("CS poll loop failed: %s", exc)

            await asyncio.sleep(3)

    async def _worker_loop(self, worker_number: int):
        while True:
            job_id = await self._queue.get()
            if job_id is None:
                self._queue.task_done()
                return

            try:
                await self._process_job(worker_number, job_id)
            except Exception as exc:
                logger.exception("CS worker %s failed on job %s: %s", worker_number, job_id, exc)
                await self._mark_job_failed(job_id, str(exc), retry=True)
            finally:
                self._scheduled_job_ids.discard(job_id)
                self._queue.task_done()

    async def _process_job(self, worker_number: int, job_id: int):
        async with async_session_maker() as session:
            job = await self._load_job(session, job_id)
            if not job:
                return

            config = await self._ensure_config(session)
            max_retries = max(1, int(config.max_retries or 3))

            job.status = "processing"
            job.attempts = (job.attempts or 0) + 1
            job.started_at = job.started_at or datetime.now(timezone.utc)
            job.worker_label = f"cs-worker-{worker_number}"
            await session.commit()

            proxy_record = await self._get_active_proxy(session, config)
            runtime_kwargs = self._build_runtime_kwargs(proxy_record, config.headless)
            payload = dict(job.input_payload or {})

        result = await run_funnel(payload, **runtime_kwargs)
        score = result.get("credit_score")
        error_text = result.get("error") or "Credit score not found"

        if result.get("success") and score:
            await self._complete_job_success(job_id, int(score), result)
            return

        if job.attempts < max_retries:
            await self._mark_job_failed(job_id, error_text, retry=True)
            return

        await self._complete_job_nf(job_id, error_text, result)

    async def _complete_job_success(self, job_id: int, score: int, result: dict):
        async with async_session_maker() as session:
            job = await self._load_job(session, job_id)
            if not job:
                return

            order = job.order
            item = await self._get_bulk_item(session, order.id, job.bulk_item_number)
            result_payload = {
                "status": "done",
                "credit_score": score,
                "raw_text": result.get("raw_text"),
                "source": "client_bot_cs_runner",
            }

            if order.is_bulk and item:
                item.status = "done"
                item.result_data = result_payload
                item.completed_at = datetime.now(timezone.utc)
                await session.commit()

                job.status = "success"
                job.result_payload = result_payload
                job.completed_at = datetime.now(timezone.utc)
                await session.commit()

                await self._create_finance_entry(
                    session,
                    job,
                    order,
                    entry_type="income",
                    amount=self._item_price(order),
                    description=f"CS bulk item #{item.item_number} success",
                )

                await self.bot.send_message(
                    order.user_id,
                    f"✅ CS bulk item #{item.item_number} ready\n\nScore: `{score}`",
                    parse_mode="Markdown",
                )

                await self._finalize_bulk_order_if_ready(session, order)
                return

            order.result_data = result_payload
            await session.commit()
            await SupportOrderService.complete_order(session, order, result_data=result_payload)

            job.status = "success"
            job.result_payload = result_payload
            job.completed_at = datetime.now(timezone.utc)
            await session.commit()

            await self._create_finance_entry(
                session,
                job,
                order,
                entry_type="income",
                amount=Decimal(str(order.price)),
                description="CS order completed successfully",
            )

            await self.bot.send_message(
                order.user_id,
                f"✅ CS result ready\n\nCredit score: `{score}`",
                parse_mode="Markdown",
            )

    async def _complete_job_nf(self, job_id: int, error_text: str, result: Optional[dict] = None):
        async with async_session_maker() as session:
            job = await self._load_job(session, job_id)
            if not job:
                return

            order = job.order
            item = await self._get_bulk_item(session, order.id, job.bulk_item_number)
            payload = {
                "status": "nf",
                "error": error_text,
                "raw_text": (result or {}).get("raw_text"),
            }

            if order.is_bulk and item:
                refund_amount = self._item_price(order)
                refund_success = await BalanceService.refund_order(
                    session,
                    order.user_id,
                    refund_amount,
                    order.id,
                    commit=False,
                )
                item.status = "nf"
                item.result_data = {**payload, "refunded": refund_success}
                item.completed_at = datetime.now(timezone.utc)
                await session.commit()

                job.status = "failed"
                job.error_message = error_text
                job.result_payload = {**payload, "refunded": refund_success}
                job.completed_at = datetime.now(timezone.utc)
                await session.commit()

                await self._create_finance_entry(
                    session,
                    job,
                    order,
                    entry_type="expense",
                    amount=refund_amount,
                    description=f"CS bulk item #{item.item_number} refund",
                )

                await self.bot.send_message(
                    order.user_id,
                    f"❌ CS bulk item #{item.item_number} not found\nRefund: `${refund_amount:.2f}`",
                    parse_mode="Markdown",
                    reply_markup=cs_retry_keyboard(order.id, await self._get_user_language(session, order), item.item_number),
                )
                await self._notify_admin_error(order.id, error_text, bulk_item_number=item.item_number)
                await self._finalize_bulk_order_if_ready(session, order)
                return

            refund_amount = Decimal(str(order.price))
            refund_success = await BalanceService.refund_order(
                session,
                order.user_id,
                refund_amount,
                order.id,
                commit=False,
            )
            payload["refunded"] = refund_success
            order.result_data = payload
            await session.commit()
            await SupportOrderService.complete_order(session, order, result_data=payload)

            job.status = "failed"
            job.error_message = error_text
            job.result_payload = payload
            job.completed_at = datetime.now(timezone.utc)
            await session.commit()

            await self._create_finance_entry(
                session,
                job,
                order,
                entry_type="expense",
                amount=refund_amount,
                description="CS order refunded after failed automation",
            )

            await self.bot.send_message(
                order.user_id,
                f"❌ CS result not found\nRefund: `${refund_amount:.2f}`",
                parse_mode="Markdown",
                reply_markup=cs_retry_keyboard(order.id, await self._get_user_language(session, order)),
            )
            await self._notify_admin_error(order.id, error_text)

    async def _finalize_bulk_order_if_ready(self, session, order: Order):
        await session.refresh(order, ["bulk_items"])
        pending_exists = any(item.status == "pending" for item in order.bulk_items)
        if pending_exists:
            return

        done_count = sum(1 for item in order.bulk_items if item.status == "done")
        nf_count = sum(1 for item in order.bulk_items if item.status == "nf")
        summary = {
            "status": "bulk_completed",
            "done": done_count,
            "nf": nf_count,
            "total": len(order.bulk_items),
        }
        await SupportOrderService.complete_order(session, order, result_data=summary)

        await self.bot.send_message(
            order.user_id,
            (
                "✅ CS bulk completed\n\n"
                f"Done: `{done_count}`\n"
                f"NF: `{nf_count}`\n"
                f"Total: `{len(order.bulk_items)}`"
            ),
            parse_mode="Markdown",
        )

    async def _mark_job_failed(self, job_id: int, error_text: str, retry: bool):
        async with async_session_maker() as session:
            job = await self._load_job(session, job_id)
            if not job:
                return
            job.error_message = error_text
            job.status = "queued" if retry else "failed"
            await session.commit()

    async def _schedule_jobs(self, job_ids: list[int]):
        for job_id in job_ids:
            if job_id in self._scheduled_job_ids:
                continue
            self._scheduled_job_ids.add(job_id)
            await self._queue.put(job_id)

    async def _ensure_config(self, session=None) -> AutomationConfig:
        if session is not None:
            return await self._ensure_config_in_session(session)

        async with async_session_maker() as own_session:
            return await self._ensure_config_in_session(own_session)

    async def _ensure_config_in_session(self, session) -> AutomationConfig:
        result = await session.execute(
            select(AutomationConfig).where(AutomationConfig.service_code == "lookup_credit")
        )
        config = result.scalar_one_or_none()
        if config:
            return config

        config = AutomationConfig(
            service_code="lookup_credit",
            is_enabled=True,
            worker_count=_DEFAULT_WORKERS,
            max_retries=3,
            headless=True,
            poll_interval_seconds=5,
        )
        session.add(config)
        await session.commit()
        await session.refresh(config)
        return config

    async def _load_job(self, session, job_id: int) -> Optional[AutomationJob]:
        result = await session.execute(
            select(AutomationJob)
            .where(AutomationJob.id == job_id)
            .options(selectinload(AutomationJob.order))
        )
        return result.scalar_one_or_none()

    async def _load_order(self, session, order_id: int) -> Optional[Order]:
        result = await session.execute(
            select(Order)
            .where(Order.id == order_id)
            .options(selectinload(Order.bulk_items))
        )
        return result.scalar_one_or_none()

    async def _get_bulk_item(self, session, order_id: int, item_number: Optional[int]) -> Optional[BulkOrderItem]:
        if item_number is None:
            return None
        result = await session.execute(
            select(BulkOrderItem).where(
                BulkOrderItem.order_id == order_id,
                BulkOrderItem.item_number == item_number,
            )
        )
        return result.scalar_one_or_none()

    async def _get_active_proxy(self, session, config: AutomationConfig) -> Optional[AutomationProxy]:
        if config.active_proxy_id:
            result = await session.execute(
                select(AutomationProxy).where(
                    AutomationProxy.id == config.active_proxy_id,
                    AutomationProxy.is_active == True,
                )
            )
            proxy = result.scalar_one_or_none()
            if proxy:
                return proxy

        result = await session.execute(
            select(AutomationProxy)
            .where(AutomationProxy.is_active == True)
            .order_by(AutomationProxy.is_default.desc(), AutomationProxy.id.asc())
        )
        return result.scalar_one_or_none()

    def _build_runtime_kwargs(self, proxy: Optional[AutomationProxy], headless: bool) -> dict:
        kwargs = {
            "headless": headless,
            "user_agent": random.choice(_USER_AGENTS),
            "locale": random.choice(_LOCALES),
            "timezone_id": random.choice(_TIMEZONES),
            "viewport": random.choice(_VIEWPORTS),
            "extra_http_headers": {"Accept-Language": "en-US,en;q=0.9"},
        }
        if proxy:
            kwargs["proxy"] = {
                "server": f"{proxy.proxy_type}://{proxy.host}:{proxy.port}",
                "username": proxy.username or "",
                "password": proxy.password or "",
            }
        return kwargs

    async def _create_finance_entry(
        self,
        session,
        job: AutomationJob,
        order: Order,
        *,
        entry_type: str,
        amount: Decimal,
        description: str,
    ):
        entry = AutomationFinanceEntry(
            job_id=job.id,
            order_id=order.id,
            entry_type=entry_type,
            source_type="order",
            source_ref=f"order:{order.id}",
            amount=amount,
            description=description,
            payload={"service_name": order.service_name, "bulk_item_number": job.bulk_item_number},
        )
        session.add(entry)
        await session.commit()

    async def _notify_admin_error(self, order_id: int, error_text: str, bulk_item_number: Optional[int] = None):
        suffix = f"\n• Bulk item: <code>{bulk_item_number}</code>" if bulk_item_number else ""
        await AdminNotificationService.notify_admin_action(
            title="CS automation error",
            lines=[
                f"• Order: <code>{order_id}</code>{suffix}",
                f"• Mirror bot: <code>{self.mirror_bot_id}</code>",
                f"• Error: {error_text[:500]}",
            ],
            event_type="cs_automation_error",
            urgent=True,
        )

    @staticmethod
    def _item_price(order: Order) -> Decimal:
        return (Decimal(str(order.price)) / Decimal(str(order.bulk_count or 1))).quantize(Decimal("0.01"))

    async def _get_user_language(self, session, order: Order) -> str:
        user = await UserService.get_user(session, order.user_id, order.mirror_bot_id)
        return user.language if user and user.language else "en"


_RUNNERS: dict[int, CsAutomationRunner] = {}


def get_cs_runner(mirror_bot_id: int) -> Optional[CsAutomationRunner]:
    return _RUNNERS.get(mirror_bot_id)


def register_cs_runner(mirror_bot_id: int, runner: CsAutomationRunner):
    _RUNNERS[mirror_bot_id] = runner

