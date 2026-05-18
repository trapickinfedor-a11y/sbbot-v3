"""
Credit Report automation runner — uses the self-hosted Lookup API (/api/cr/).

Replaces the Playwright-based CsAutomationRunner for all structured CR services
(TransUnion, Experian, Equifax, LexisNexis).  WalletHub orders still go to workers
because they have no structured data to query.

Service codes handled:
  cr_transunion, cr_experian, cr_equifax, cr_lexisnexis

Flow per order:
  1. enqueue_order() creates AutomationJob record(s).
  2. Runner checks AutomationConfig.is_enabled and API key presence.
     – Disabled or no key → order stays "pending", workers notified.
  3. API call to /api/cr/ with SSN + name + bureau.
     – Found     → format report, deliver to user, complete order, log finance.
     – Not found → refund user, notify user + admin, mark job failed.
  4. Bulk: same per-item; finalise when all items done.

Finance tracking (AutomationFinanceEntry):
  income  = order price (revenue from client)
  expense = API call cost (PRICE_CR_FOUND / PRICE_CR_NOFOUND from env)
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetim, timezone
from decimal import Decimal
from typing import Optional

from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from mirror_bot.services.user_service import UserService
from shared.database.models import (
    AutomationApiKey,
    AutomationConfig,
    AutomationFinanceEntry,
    AutomationJob,
    BulkOrderItem,
    Order,
)
from shared.database.session import async_session_maker
from shared.services.admin_notification_service import AdminNotificationService
from support_bot.services.balance_service import BalanceService
from support_bot.services.order_service import OrderService as SupportOrderService

logger = logging.getLogger(__name__)

# Bureau mapping: service_code → API bureau param
_BUREAU_MAP: dict[str, str] = {
    "cr_transunion":  "transunion",
    "cr_experian":    "experian",
    "cr_equifax":     "equifax",
    "cr_lexisnexis":  "lexisnexis",
}

# API costs (can be overridden via env like the lookup_api server)
_COST_FOUND    = Decimal(os.getenv("PRICE_CR_FOUND",    "0.40"))
_COST_NOFOUND  = Decimal(os.getenv("PRICE_CR_NOFOUND",  "0.01"))


class CrAutomationRunner:
    """
    Lightweight API-based Credit Report automation.
    Reads AutomationApiKey records where provider='lookup_api' (or 'usfull').
    """

    def __init__(self, bot: Bot, mirror_bot_id: int):
        self.bot = bot
        self.mirror_bot_id = mirror_bot_id
        self._queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._worker_tasks: list = []

    # ─── Lifecycle ────────────────────────────────────────────────────────────

    async def start(self):
        if self._running:
            return
        self._running = True
        for i in range(3):
            task = asyncio.create_task(
                self._worker_loop(i + 1),
                name=f"cr-worker-{self.mirror_bot_id}-{i + 1}",
            )
            self._worker_tasks.append(task)
        logger.info("CR automation runner started for mirror bot %s", self.mirror_bot_id)

    async def stop(self):
        if not self._running:
            return
        self._running = False
        for _ in self._worker_tasks:
            await self._queue.put(None)
        await asyncio.gather(*self._worker_tasks, return_exceptions=True)
        self._worker_tasks.clear()
        logger.info("CR automation runner stopped for mirror bot %s", self.mirror_bot_id)

    # ─── Enqueue ──────────────────────────────────────────────────────────────

    async def enqueue_order(self, order_id: int):
        """Create AutomationJob records and push them into the processing queue."""
        async with async_session_maker() as session:
            order = await self._load_order(session, order_id)
            if not order:
                return

            service_code = order.service_name  # e.g. 'cr_transunion'
            if service_code not in _BUREAU_MAP:
                logger.warning("CR runner: unsupported service code %s", service_code)
                return

            # Check config
            config = await self._ensure_config(session, service_code)
            if not config.is_enabled:
                logger.info("CR automation disabled for %s, routing to workers", service_code)
                await self._forward_to_workers(session, order)
                return

            # Check API key
            api_key_obj = await self._get_api_key(session)
            if not api_key_obj:
                logger.warning("No active Lookup API key, routing CR order %s to workers", order_id)
                await self._forward_to_workers(session, order)
                return

            # Check if jobs already exist
            existing = await session.execute(
                select(AutomationJob.id).where(AutomationJob.order_id == order.id)
            )
            existing_ids = [r[0] for r in existing.all()]
            if existing_ids:
                for jid in existing_ids:
                    await self._queue.put(jid)
                return

            # Mark order as processing
            order.status = "processing"
            if not order.taken_at:
                order.taken_at = datetime.now(timezone.utc)

            new_jobs: list[AutomationJob] = []
            if order.is_bulk:
                for item in order.bulk_items:
                    new_jobs.append(AutomationJob(
                        order_id=order.id,
                        bulk_item_number=item.item_number,
                        service_code=service_code,
                        status="queued",
                        user_id=order.user_id,
                        mirror_bot_id=order.mirror_bot_id,
                        input_payload=item.input_data or {},
                        priority=100,
                    ))
            else:
                new_jobs.append(AutomationJob(
                    order_id=order.id,
                    service_code=service_code,
                    status="queued",
                    user_id=order.user_id,
                    mirror_bot_id=order.mirror_bot_id,
                    input_payload=order.input_data or {},
                    priority=100,
                ))

            session.add_all(new_jobs)
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
                logger.exception("CR worker %s failed on job %s: %s", worker_number, job_id, exc)
                await self._mark_failed(job_id, str(exc))
            finally:
                self._queue.task_done()

    # ─── Job processing ───────────────────────────────────────────────────────

    async def _process_job(self, worker_number: int, job_id: int):
        async with async_session_maker() as session:
            job = await self._load_job(session, job_id)
            if not job:
                return

            job.status = "processing"
            job.attempts = (job.attempts or 0) + 1
            job.started_at = job.started_at or datetime.now(timezone.utc)
            job.worker_label = f"cr-worker-{worker_number}"
            await session.commit()

            api_key_obj = await self._get_api_key(session)
            if not api_key_obj:
                await self._mark_failed(job_id, "No active API key")
                return

            payload = dict(job.input_payload or {})
            bureau = _BUREAU_MAP.get(job.service_code, "any")

        # API call outside session
        from mirror_bot.services.usfull_service import UsfullClient
        client = _build_client(api_key_obj)
        try:
            api_result = await client.search_cr_from_order_data(payload, bureau=bureau)
        except Exception as exc:
            logger.exception("CR API error for job %s: %s", job_id, exc)
            await self._mark_failed(job_id, f"API error: {exc}")
            return

        if api_result.get("success") and api_result.get("results"):
            await self._handle_success(job_id, api_result["results"][0])
        else:
            await self._handle_noresult(job_id)

    async def _handle_success(self, job_id: int, result: dict):
        async with async_session_maker() as session:
            job = await self._load_job(session, job_id)
            if not job:
                return

            order = job.order
            item = await self._get_bulk_item(session, order.id, job.bulk_item_number)

            credit_score = result.get("credit_score")
            bureau = result.get("bureau", "")
            report_data = result.get("report_data") or {}
            raw_text = result.get("raw_text", "")
            has_pdf = result.get("has_pdf", False)
            pdf_record_id = result.get("id")

            result_payload = {
                "status": "done",
                "credit_score": credit_score,
                "bureau": bureau,
                "report_data": report_data,
                "raw_text": raw_text,
                "has_pdf": has_pdf,
                "source": "cr_automation_api",
            }

            msg = _format_cr_result(result, order.service_name)

            if order.is_bulk and item:
                item.status = "done"
                item.result_data = result_payload
                item.completed_at = datetime.now(timezone.utc)
                await session.commit()

                job.status = "success"
                job.result_payload = result_payload
                job.completed_at = datetime.now(timezone.utc)
                await session.commit()

                await self._log_finance(session, job, order, "income", self._item_price(order),
                                        f"CR bulk item #{item.item_number} success")
                await self._log_finance(session, job, order, "expense", _COST_FOUND,
                                        f"CR API cost item #{item.item_number}")
                await session.commit()

                await self.bot.send_message(order.user_id, msg, parse_mode="Markdown")
                if has_pdf and pdf_record_id:
                    await self._send_pdf(order.user_id, job, pdf_record_id)
                await self._finalize_bulk_if_ready(session, order)
                return

            # Single order
            order.result_data = result_payload
            await session.commit()
            await SupportOrderService.complete_order(session, order, result_data=result_payload)

            job.status = "success"
            job.result_payload = result_payload
            job.completed_at = datetime.now(timezone.utc)
            await session.commit()

            await self._log_finance(session, job, order, "income", Decimal(str(order.price)),
                                    "CR order completed")
            await self._log_finance(session, job, order, "expense", _COST_FOUND, "CR API cost")
            await session.commit()

            await self.bot.send_message(order.user_id, msg, parse_mode="Markdown")
            if has_pdf and pdf_record_id:
                await self._send_pdf(order.user_id, job, pdf_record_id)

    async def _send_pdf(self, user_id: int, job, record_id: int):
        """Download CR PDF from API and send it to the user via Telegram."""
        try:
            api_key_obj = None
            async with async_session_maker() as session:
                api_key_obj = await self._get_api_key(session)
            if not api_key_obj:
                return

            client = _build_client(api_key_obj)
            import tempfile
            dest = os.path.join(tempfile.gettempdir(), f"cr_{record_id}_{job.id}.pdf")
            downloaded = await client.download_cr_pdf(record_id, dest)
            if not downloaded:
                logger.warning("PDF not available for CR record %s", record_id)
                return

            from aiogram.types import FSInputFile
            pdf_file = FSInputFile(dest, filename=f"CreditReport_{record_id}.pdf")
            await self.bot.send_document(user_id, document=pdf_file, caption="📄 Credit Report (PDF)")

            try:
                os.remove(dest)
            except OSError:
                pass
        except Exception as exc:
            logger.error("Failed to send CR PDF to user %s: %s", user_id, exc)

    async def _handle_noresult(self, job_id: int):
        async with async_session_maker() as session:
            job = await self._load_job(session, job_id)
            if not job:
                return

            order = job.order
            item = await self._get_bulk_item(session, order.id, job.bulk_item_number)

            if order.is_bulk and item:
                refund_amt = self._item_price(order)
                refund_ok = await BalanceService.refund_order(
                    session, order.user_id, refund_amt, order.id, commit=False
                )
                item.status = "nf"
                item.result_data = {"status": "nf", "refunded": refund_ok}
                item.completed_at = datetime.now(timezone.utc)
                await session.commit()

                job.status = "failed"
                job.error_message = "Not found in database"
                job.result_payload = {"status": "nf"}
                job.completed_at = datetime.now(timezone.utc)
                await session.commit()

                await self._log_finance(session, job, order, "expense", _COST_NOFOUND,
                                        f"CR API cost item #{item.item_number} (not found)")
                await session.commit()

                await self.bot.send_message(
                    order.user_id,
                    f"❌ CR bulk item #{item.item_number} — not found\n"
                    f"Refund: `${refund_amt:.2f}`",
                    parse_mode="Markdown",
                )
                await self._notify_admin(order.id, "Not found in database", item.item_number)
                await self._finalize_bulk_if_ready(session, order)
                return

            # Single order
            refund_amt = Decimal(str(order.price))
            refund_ok = await BalanceService.refund_order(
                session, order.user_id, refund_amt, order.id, commit=False
            )
            order.result_data = {"status": "nf", "refunded": refund_ok}
            await session.commit()
            await SupportOrderService.complete_order(session, order, result_data=order.result_data)

            job.status = "failed"
            job.error_message = "Not found in database"
            job.result_payload = {"status": "nf"}
            job.completed_at = datetime.now(timezone.utc)
            await session.commit()

            await self._log_finance(session, job, order, "expense", _COST_NOFOUND,
                                    "CR API cost (not found)")
            await session.commit()

            await self.bot.send_message(
                order.user_id,
                f"❌ Credit Report not found\nRefund: `${refund_amt:.2f}`",
                parse_mode="Markdown",
            )
            await self._notify_admin(order.id, "Not found in database")

    # ─── Helpers ──────────────────────────────────────────────────────────────

    async def _finalize_bulk_if_ready(self, session, order: Order):
        await session.refresh(order, ["bulk_items"])
        if any(item.status == "pending" for item in order.bulk_items):
            return
        done = sum(1 for i in order.bulk_items if i.status == "done")
        nf   = sum(1 for i in order.bulk_items if i.status == "nf")
        summary = {"status": "bulk_completed", "done": done, "nf": nf, "total": len(order.bulk_items)}
        await SupportOrderService.complete_order(session, order, result_data=summary)
        await self.bot.send_message(
            order.user_id,
            f"✅ CR bulk completed\n\nDone: `{done}`\nNF: `{nf}`\nTotal: `{len(order.bulk_items)}`",
            parse_mode="Markdown",
        )

    async def _forward_to_workers(self, session, order: Order):
        """Reset order to pending and fire worker notifications."""
        order.status = "pending"
        await session.commit()
        from shared.services.order_notification_service import OrderNotificationService
        order_data = {
            "id": order.id,
            "user_id": order.user_id,
            "mirror_bot_id": order.mirror_bot_id,
            "category": order.category,
            "service_name": order.service_name,
            "price": float(order.price or 0),
            "is_bulk": order.is_bulk,
            "bulk_count": order.bulk_count,
            "created_at": order.created_at.isoformat() if order.created_at else "",
            "input_data": order.input_data or {},
        }
        await OrderNotificationService.notify_new_order(order_data)

    async def _mark_failed(self, job_id: int, error: str):
        async with async_session_maker() as session:
            job = await self._load_job(session, job_id)
            if job:
                job.status = "failed"
                job.error_message = error
                job.completed_at = datetime.now(timezone.utc)
                await session.commit()

    async def _log_finance(self, session, job, order: Order, entry_type: str,
                           amount: Decimal, description: str):
        session.add(AutomationFinanceEntry(
            job_id=job.id,
            order_id=order.id,
            entry_type=entry_type,
            source_type="order",
            source_ref=f"order:{order.id}",
            amount=amount,
            description=description,
            payload={"service_name": order.service_name, "bulk_item_number": job.bulk_item_number},
        ))

    async def _notify_admin(self, order_id: int, error: str, item_number: Optional[int] = None):
        suffix = f"\n• Bulk item: <code>{item_number}</code>" if item_number else ""
        await AdminNotificationService.notify_admin_action(
            title="CR automation — not found",
            lines=[
                f"• Order: <code>{order_id}</code>{suffix}",
                f"• Mirror bot: <code>{self.mirror_bot_id}</code>",
                f"• Error: {error[:300]}",
            ],
            event_type="cr_automation_nf",
            urgent=False,
        )

    @staticmethod
    def _item_price(order: Order) -> Decimal:
        return (Decimal(str(order.price)) / Decimal(str(order.bulk_count or 1))).quantize(Decimal("0.01"))

    async def _ensure_config(self, session, service_code: str) -> AutomationConfig:
        result = await session.execute(
            select(AutomationConfig).where(AutomationConfig.service_code == service_code)
        )
        config = result.scalar_one_or_none()
        if config:
            return config
        config = AutomationConfig(
            service_code=service_code,
            is_enabled=True,
            worker_count=3,
            max_retries=2,
            headless=True,
            poll_interval_seconds=5,
        )
        session.add(config)
        await session.commit()
        await session.refresh(config)
        return config

    async def _get_api_key(self, session) -> Optional[AutomationApiKey]:
        result = await session.execute(
            select(AutomationApiKey).where(
                AutomationApiKey.is_active == True,
                AutomationApiKey.provider.in_(["lookup_api", "usfull"]),
            )
        )
        return result.scalars().first()

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


# ─── Formatting ───────────────────────────────────────────────────────────────

def _format_cr_result(result: dict, service_code: str) -> str:
    """Format credit report API result into a readable Telegram message."""
    bureau_label = {
        "cr_transunion":  "TransUnion",
        "cr_experian":    "Experian",
        "cr_equifax":     "Equifax",
        "cr_lexisnexis":  "LexisNexis",
    }.get(service_code, result.get("bureau", "Credit Bureau").capitalize())

    score = result.get("credit_score")
    score_line = f"📊 Score: `{score}`" if score else "📊 Score: N/A"

    lines = [f"✅ *{bureau_label} Credit Report*", "", score_line]

    report_data = result.get("report_data") or {}
    if isinstance(report_data, str):
        try:
            report_data = json.loads(report_data)
        except Exception:
            report_data = {}

    # Accounts summary
    accounts = report_data.get("accounts") or []
    if accounts:
        lines.append(f"\n📋 *Accounts ({len(accounts)})*")
        for acc in accounts[:5]:  # Show up to 5
            status = acc.get("status", "")
            name   = acc.get("name", "Account")
            bal    = acc.get("balance", "")
            bal_str = f" — ${bal}" if bal else ""
            status_icon = "✅" if str(status).lower() in ("current", "open") else "⚠️"
            lines.append(f"  {status_icon} {name}{bal_str}")
        if len(accounts) > 5:
            lines.append(f"  _…and {len(accounts) - 5} more_")

    # Inquiries
    inquiries = report_data.get("inquiries") or []
    if inquiries:
        lines.append(f"\n🔍 *Inquiries*: {len(inquiries)}")

    # Negative items
    negatives = report_data.get("negative_items") or report_data.get("derogatory") or []
    if negatives:
        lines.append(f"\n⛔ *Negative items*: {len(negatives)}")

    # Raw text fallback (trimmed)
    raw = result.get("raw_text", "")
    if raw and not accounts:
        lines.append(f"\n```\n{raw[:800]}{'...' if len(raw) > 800 else ''}\n```")

    return "\n".join(lines)


# ─── Build API client ─────────────────────────────────────────────────────────

def _build_client(api_key_obj: AutomationApiKey):
    from mirror_bot.services.usfull_service import UsfullClient
    # Support usfull-style keys that store username/password in notes JSON
    username = None
    password = None
    if api_key_obj.notes:
        try:
            creds = json.loads(api_key_obj.notes)
            username = creds.get("username")
            password = creds.get("password")
        except Exception:
            pass
    return UsfullClient(
        api_key=api_key_obj.key_value,
        username=username,
        password=password,
    )


# ─── Registry ─────────────────────────────────────────────────────────────────

_RUNNERS: dict[int, CrAutomationRunner] = {}


def get_cr_runner(mirror_bot_id: int) -> Optional[CrAutomationRunner]:
    return _RUNNERS.get(mirror_bot_id)


def register_cr_runner(mirror_bot_id: int, runner: CrAutomationRunner):
    _RUNNERS[mirror_bot_id] = runner
