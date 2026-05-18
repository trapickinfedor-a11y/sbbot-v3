"""
SSN/DL automation runner using usfull.info API.

Flow per order:
  1. After order is created (balance already deducted), enqueue_order() is called.
  2. Runner checks AutomationConfig.is_enabled for the service_code.
     - Disabled or no API key → reset order to "pending" → notify workers (normal flow).
  3. For each item (or single order): calls usfull.info API.
     - Found     → deliver result to user, mark job/order done, log finance entries.
     - Not found → reset order item to "pending", log expense, notify workers.
  4. For bulk orders: waits until ALL items are processed; if any pending remain → notify workers.

Finance tracking (AutomationFinanceEntry):
  - income  = order price portion (revenue from client)
  - expense = API call cost ($0.40/$1.00 found; $0.01 SSN not-found; $0.00 DL not-found)
"""
from __future__ import annotations
import asyncio
import json
import logging
from datetime import datetim, timezone
from decimal import Decimal
from typing import Optional

from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from shared.database.models import (
    AutomationApiKey,
    AutomationConfig,
    AutomationFinanceEntry,
    AutomationJob,
    BulkOrderItem,
    Order,
)
from shared.database.session import async_session_maker

logger = logging.getLogger(__name__)

# API costs per request (usfull.info pricing)
_COSTS: dict[str, dict[str, Decimal]] = {
    "lookup_ssn": {"success": Decimal("0.40"), "noresult": Decimal("0.01")},
    "lookup_dl":  {"success": Decimal("1.00"), "noresult": Decimal("0.00")},
}


class SsnDlAutomationRunner:
    """
    Lightweight HTTP-based automation runner for SSN (lookup_ssn)
    and DL (lookup_dl) orders. No browser required — pure API calls.
    """

    def __init__(self, bot: Bot, mirror_bot_id: int):
        self.bot = bot
        self.mirror_bot_id = mirror_bot_id
        self._queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._worker_tasks: list = []

    async def start(self):
        if self._running:
            return
        self._running = True
        for i in range(3):
            task = asyncio.create_task(
                self._worker_loop(i + 1),
                name=f"ssndl-worker-{self.mirror_bot_id}-{i + 1}",
            )
            self._worker_tasks.append(task)
        logger.info("SSN/DL automation started for mirror bot %s", self.mirror_bot_id)

    async def stop(self):
        if not self._running:
            return
        self._running = False
        for _ in self._worker_tasks:
            await self._queue.put(None)
        await asyncio.gather(*self._worker_tasks, return_exceptions=True)
        self._worker_tasks.clear()
        logger.info("SSN/DL automation stopped for mirror bot %s", self.mirror_bot_id)

    # ─── Public API ───────────────────────────────────────────────────────────

    async def enqueue_order(self, order_id: int, service_code: str):
        """Create automation jobs for the order and add to processing queue."""
        async with async_session_maker() as session:
            order = await self._load_order(session, order_id)
            if not order:
                return

            existing = await session.execute(
                select(AutomationJob.id).where(AutomationJob.order_id == order.id)
            )
            if existing.all():
                return

            config = await self._get_or_create_config(session, service_code)
            if not config.is_enabled:
                logger.info(
                    "SSN/DL automation disabled for %s, forwarding order %s to workers",
                    service_code, order_id,
                )
                await self._send_to_workers(order)
                return

            order.status = "processing"
            if not order.taken_at:
                order.taken_at = datetime.now(timezone.utc)

            new_jobs: list[AutomationJob] = []
            if order.is_bulk:
                for item in order.bulk_items:
                    job = AutomationJob(
                        order_id=order.id,
                        bulk_item_number=item.item_number,
                        service_code=service_code,
                        status="queued",
                        user_id=order.user_id,
                        mirror_bot_id=order.mirror_bot_id,
                        input_payload=item.input_data or {},
                        priority=100,
                    )
                    session.add(job)
                    new_jobs.append(job)
            else:
                job = AutomationJob(
                    order_id=order.id,
                    service_code=service_code,
                    status="queued",
                    user_id=order.user_id,
                    mirror_bot_id=order.mirror_bot_id,
                    input_payload=order.input_data or {},
                    priority=100,
                )
                session.add(job)
                new_jobs.append(job)

            await session.commit()
            for job in new_jobs:
                await self._queue.put(job.id)

    # ─── Worker loop ──────────────────────────────────────────────────────────

    async def _worker_loop(self, worker_number: int):
        while True:
            job_id = await self._queue.get()
            if job_id is None:
                self._queue.task_done()
                return
            try:
                await self._process_job(worker_number, job_id)
            except Exception as exc:
                logger.exception(
                    "SSN/DL worker %s failed on job %s: %s", worker_number, job_id, exc
                )
            finally:
                self._queue.task_done()

    async def _process_job(self, worker_number: int, job_id: int):
        async with async_session_maker() as session:
            result = await session.execute(
                select(AutomationJob)
                .where(AutomationJob.id == job_id)
                .options(selectinload(AutomationJob.order))
            )
            job = result.scalar_one_or_none()
            if not job:
                return

            client = await self._get_client(session)
            if not client:
                logger.warning("No usfull API key, falling back to workers for job %s", job_id)
                order = job.order
                order.status = "pending"
                job.status = "skipped"
                job.error_message = "No API key configured"
                job.completed_at = datetime.now(timezone.utc)
                await session.commit()
                await self._send_to_workers(order)
                return

            job.status = "processing"
            job.attempts = (job.attempts or 0) + 1
            job.started_at = job.started_at or datetime.now(timezone.utc)
            job.worker_label = f"ssndl-worker-{worker_number}"
            service_code = job.service_code
            payload = dict(job.input_payload or {})
            await session.commit()

        # Pre-check required fields before making the API call
        # (avoids wasting API balance on incomplete orders)
        if service_code == "lookup_dl":
            missing = _check_dl_required_fields(payload)
            if missing:
                logger.info(
                    "DL job %s missing required fields %s, forwarding to workers", job_id, missing
                )
                await self._mark_skipped(job_id, error=f"Missing required fields: {missing}")
                return

        # API call outside the session
        try:
            if service_code == "lookup_ssn":
                api_result = await client.search_ssn_from_order_data(payload)
            elif service_code == "lookup_dl":
                api_result = await client.search_dl_from_order_data(payload)
            else:
                await self._mark_skipped(job_id, error=f"Unknown service_code: {service_code}")
                return
        except Exception as exc:
            logger.error("USFull API error for job %s: %s", job_id, exc)
            await self._mark_skipped(job_id, error=str(exc))
            return

        if api_result.get("success") and api_result.get("results"):
            await self._handle_success(job_id, api_result)
        else:
            await self._handle_noresult(job_id)

    # ─── Outcome handlers ─────────────────────────────────────────────────────

    async def _handle_success(self, job_id: int, api_result: dict):
        async with async_session_maker() as session:
            result = await session.execute(
                select(AutomationJob)
                .where(AutomationJob.id == job_id)
                .options(selectinload(AutomationJob.order))
            )
            job = result.scalar_one_or_none()
            if not job:
                return

            order = job.order
            item = await self._get_bulk_item(session, order.id, job.bulk_item_number)
            results = api_result.get("results", [])
            result_payload = {"status": "done", "source": "usfull_api", "data": results}

            costs = _COSTS.get(job.service_code, {})
            api_cost = costs.get("success", Decimal("0.00"))
            item_price = self._item_price(order)

            if order.is_bulk and item:
                item.status = "done"
                item.result_data = result_payload
                item.completed_at = datetime.now(timezone.utc)

            job.status = "success"
            job.result_payload = result_payload
            job.completed_at = datetime.now(timezone.utc)
            await session.commit()

            await self._add_finance(session, job, order, "income", item_price,
                                    f"{job.service_code} success — revenue")
            if api_cost > 0:
                await self._add_finance(session, job, order, "expense", api_cost,
                                        f"USFull API cost — {job.service_code}")

            if not order.is_bulk:
                from support_bot.services.order_service import OrderService as SupportOrderService
                await SupportOrderService.complete_order(session, order, result_data=result_payload)

            msg = _format_result(job.service_code, results, job.bulk_item_number)
            try:
                await self.bot.send_message(order.user_id, msg, parse_mode="Markdown")
            except Exception as e:
                logger.error("Failed to send result to user %s: %s", order.user_id, e)

            if order.is_bulk:
                await self._check_bulk_complete(session, order)

    async def _handle_noresult(self, job_id: int):
        """API returned no results → send to workers queue."""
        async with async_session_maker() as session:
            result = await session.execute(
                select(AutomationJob)
                .where(AutomationJob.id == job_id)
                .options(selectinload(AutomationJob.order))
            )
            job = result.scalar_one_or_none()
            if not job:
                return

            order = job.order
            costs = _COSTS.get(job.service_code, {})
            api_cost = costs.get("noresult", Decimal("0.00"))

            job.status = "noresult"
            job.error_message = "No results from API"
            job.completed_at = datetime.now(timezone.utc)

            if order.is_bulk:
                item = await self._get_bulk_item(session, order.id, job.bulk_item_number)
                if item:
                    item.status = "pending"
            else:
                order.status = "pending"

            await session.commit()

            if api_cost > 0:
                await self._add_finance(session, job, order, "expense", api_cost,
                                        f"USFull API cost (no result) — {job.service_code}")

            if not order.is_bulk:
                await self._send_to_workers(order)
            else:
                await self._check_bulk_complete(session, order)

    async def _mark_skipped(self, job_id: int, error: str = ""):
        async with async_session_maker() as session:
            result = await session.execute(
                select(AutomationJob)
                .where(AutomationJob.id == job_id)
                .options(selectinload(AutomationJob.order))
            )
            job = result.scalar_one_or_none()
            if not job:
                return
            order = job.order
            job.status = "skipped"
            job.error_message = error
            job.completed_at = datetime.now(timezone.utc)
            order.status = "pending"
            await session.commit()
            await self._send_to_workers(order)

    # ─── Bulk finalization ────────────────────────────────────────────────────

    async def _check_bulk_complete(self, session, order: Order):
        """After all bulk items are processed: complete or forward pending to workers."""
        await session.refresh(order, ["bulk_items"])
        processing = [i for i in order.bulk_items if i.status in ("pending", "processing")]
        if processing:
            # Still processing — workers will handle pending items when all API calls finish
            # Notify workers if any items remain pending
            pending_workers = [i for i in order.bulk_items if i.status == "pending"]
            if pending_workers:
                await self._send_to_workers(order)
            return

        done_count = sum(1 for i in order.bulk_items if i.status == "done")
        total = len(order.bulk_items)

        if done_count == total:
            from support_bot.services.order_service import OrderService as SupportOrderService
            summary = {"status": "bulk_completed", "done": done_count, "total": total}
            await SupportOrderService.complete_order(session, order, result_data=summary)
            try:
                await self.bot.send_message(
                    order.user_id,
                    f"✅ *Bulk lookup completed*\n\n✅ Found: `{done_count}`\n📋 Total: `{total}`",
                    parse_mode="Markdown",
                )
            except Exception as e:
                logger.error("Failed to send bulk complete message: %s", e)

    # ─── Worker notification ──────────────────────────────────────────────────

    async def _send_to_workers(self, order: Order):
        """Forward order to the manual workers queue."""
        try:
            from shared.services.order_notification_service import OrderNotificationService
            order_data = {
                "id": order.id,
                "user_id": order.user_id,
                "mirror_bot_id": order.mirror_bot_id,
                "category": order.category,
                "service_name": order.service_name,
                "price": float(order.price),
                "is_bulk": order.is_bulk,
                "bulk_count": order.bulk_count,
                "created_at": order.created_at.isoformat(),
                "input_data": order.input_data or {},
            }
            await OrderNotificationService.notify_new_order(order_data)
            await OrderNotificationService.send_order_to_channel(order_data)
        except Exception as e:
            logger.error("Failed to notify workers for order %s: %s", order.id, e)

    # ─── Finance ──────────────────────────────────────────────────────────────

    async def _add_finance(self, session, job, order, entry_type, amount, description):
        entry = AutomationFinanceEntry(
            job_id=job.id,
            order_id=order.id,
            entry_type=entry_type,
            source_type="order",
            source_ref=f"order:{order.id}",
            amount=amount,
            description=description,
            payload={"service_code": job.service_code, "bulk_item_number": job.bulk_item_number},
        )
        session.add(entry)
        await session.commit()

    # ─── DB helpers ───────────────────────────────────────────────────────────

    async def _get_or_create_config(self, session, service_code: str) -> AutomationConfig:
        result = await session.execute(
            select(AutomationConfig).where(AutomationConfig.service_code == service_code)
        )
        config = result.scalar_one_or_none()
        if config:
            return config
        config = AutomationConfig(
            service_code=service_code,
            is_enabled=False,
            worker_count=3,
            max_retries=1,
            poll_interval_seconds=3,
        )
        session.add(config)
        await session.commit()
        await session.refresh(config)
        return config

    async def _get_client(self, session):
        """Load usfull API credentials from DB and return a UsfullClient, or None."""
        result = await session.execute(
            select(AutomationApiKey)
            .where(
                AutomationApiKey.provider == "usfull",
                AutomationApiKey.is_active == True,
            )
            .order_by(AutomationApiKey.id.asc())
        )
        key_record = result.scalar_one_or_none()
        if not key_record:
            return None

        username = password = None
        if key_record.notes:
            try:
                creds = json.loads(key_record.notes)
                username = creds.get("username")
                password = creds.get("password")
            except (json.JSONDecodeError, AttributeError):
                parts = key_record.notes.split(":", 1)
                if len(parts) == 2:
                    username, password = parts

        from mirror_bot.services.usfull_service import UsfullClient
        return UsfullClient(api_key=key_record.key_value, username=username, password=password)

    async def _load_order(self, session, order_id: int) -> Optional[Order]:
        result = await session.execute(
            select(Order)
            .where(Order.id == order_id)
            .options(selectinload(Order.bulk_items))
        )
        return result.scalar_one_or_none()

    async def _get_bulk_item(self, session, order_id: int, item_number: Optional[int]):
        if item_number is None:
            return None
        result = await session.execute(
            select(BulkOrderItem).where(
                BulkOrderItem.order_id == order_id,
                BulkOrderItem.item_number == item_number,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _item_price(order: Order) -> Decimal:
        return (Decimal(str(order.price)) / Decimal(str(order.bulk_count or 1))).quantize(
            Decimal("0.01")
        )


# ─── Field validators ─────────────────────────────────────────────────────────

def _check_dl_required_fields(input_data: dict) -> list[str]:
    """
    Return list of missing required fields for the usfull DL API.
    DLLookupData has address/zip_code/dob as Optional, but the API mandates them.
    """
    missing = []
    if not input_data.get("address"):
        missing.append("address")
    if not (input_data.get("zip_code") or input_data.get("zip")):
        missing.append("zip_code")
    if not input_data.get("dob"):
        missing.append("dob")
    return missing


# ─── Result formatter ──────────────────────────────────────────────────────────

def _format_result(
    service_code: str, results: list, item_number: Optional[int] = None
) -> str:
    prefix = f"📋 *Item #{item_number}*\n\n" if item_number else ""

    if service_code == "lookup_ssn":
        lines = [f"✅ *SSN Lookup — {len(results)} result(s)*\n"]
        for i, r in enumerate(results[:5], 1):
            fn = (r.get("firstname") or "").strip()
            mn = (r.get("middlename") or "").strip()
            ln = (r.get("lastname") or "").strip()
            name_parts = [p for p in [fn, mn, ln] if p and p.upper() != "NULL"]
            lines.append(f"**#{i}**")
            if name_parts:
                lines.append(f"👤 `{' '.join(name_parts)}`")
            addr = (r.get("address") or "").strip()
            if addr and addr.upper() != "NULL":
                lines.append(f"📍 `{addr}`")
            city = (r.get("city") or "").strip()
            st_ = (r.get("st") or "").strip()
            zip_ = (r.get("zip") or "").strip()
            loc_parts = [p for p in [city, st_, zip_] if p and p.upper() != "NULL"]
            if loc_parts:
                lines.append(f"🏙️ `{', '.join(loc_parts)}`")
            ssn = r.get("ssn")
            if ssn and str(ssn).upper() != "NULL":
                lines.append(f"🆔 SSN: `{ssn}`")
            dob = r.get("dob")
            if dob and str(dob).upper() != "NULL":
                lines.append(f"🎂 DOB: `{dob}`")
            phone = r.get("phone")
            if phone and str(phone).upper() != "NULL":
                lines.append(f"📞 `{phone}`")
            lines.append("")
        return prefix + "\n".join(lines)

    if service_code == "lookup_dl":
        r = results[0] if results else {}
        lic = r.get("license_number") or "N/A"
        state = r.get("license_state") or "N/A"
        return prefix + f"✅ *DL Lookup — Found*\n\n🪪 License: `{lic}`\n🏛️ State: `{state}`"

    return prefix + "✅ *Result found*"


# ─── Global registry ──────────────────────────────────────────────────────────

_RUNNERS: dict[int, SsnDlAutomationRunner] = {}


def get_ssn_dl_runner(mirror_bot_id: int) -> Optional[SsnDlAutomationRunner]:
    return _RUNNERS.get(mirror_bot_id)


def register_ssn_dl_runner(mirror_bot_id: int, runner: SsnDlAutomationRunner):
    _RUNNERS[mirror_bot_id] = runner
