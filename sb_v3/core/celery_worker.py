"""
celery_worker.py — Celery application entrypoint.
Workers: notification reminder, ENF account monitor, invoice checker,
cache cleanup, usfull balance monitor.
"""

import os
import logging
from pathlib import Path
from datetime import datetime

from celery import Celery, signals
from celery.schedules import crontab

Path("logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/celery.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("celery_worker")

# ── Celery config ──────────────────────────────────────────────────────
broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

celery_app = Celery(
    "sbbot",
    broker=broker_url,
    backend=result_backend,
    include=[
        "tasks.account_monitor",
        "tasks.invoice_checker",
        "tasks.cache_cleanup",
        "tasks.usfull_monitor",
        "tasks.notifications",
    ],
)

# ── Beat schedule (periodic tasks) ───────────────────────────────────
celery_app.conf.beatSchedule = {
    "enf-balance-check": {
        "task": "tasks.account_monitor.check_enf_balances",
        "schedule": crontab(minute="*/30"),
    },
    "usfull-balance-check": {
        "task": "tasks.usfull_monitor.check_usfull_balances",
        "schedule": crontab(minute="*/30"),
    },
    "guarantee-reminders": {
        "task": "tasks.notifications.send_guarantee_reminders",
        "schedule": crontab(minute="*/15"),
    },
    "invoice-status-check": {
        "task": "tasks.invoice_checker.check_pending_invoices",
        "schedule": crontab(minute="*/5"),
    },
    "cache-cleanup": {
        "task": "tasks.cache_cleanup.clear_expired",
        "schedule": crontab(minute=0, hour="*/1"),
    },
}

celery_app.conf.task_serializer = "json"
celery_app.conf.result_serializer = "json"
celery_app.conf.accept_content = ["json"]
celery_app.conf.timezone = "UTC"
celery_app.conf.enable_utc = True
celery_app.conf.task_track_started = True
celery_app.conf.task_acks_late = True
celery_app.conf.worker_prefetch_multiplier = 1
celery_app.conf.task_routes = {
    "tasks.notifications.send_guarantee_reminders": {"queue": "notifications"},
    "tasks.notifications.send_single_reminder": {"queue": "notifications"},
    "tasks.invoice_checker.check_pending_invoices": {"queue": "payments"},
    "tasks.account_monitor.check_enf_balances": {"queue": "monitor"},
    "tasks.usfull_monitor.check_usfull_balances": {"queue": "monitor"},
}

# ── Task failure alerting ──────────────────────────────────────────────

@signals.task_failure.connect
def _on_task_failure(sender=None, exception=None, traceback=None, **kwargs):
    """Send admin alert when a Celery task fails."""
    task_name = sender.name if sender else "unknown"
    admin_chat = os.getenv("ADMIN_CHAT_ID", "")
    bot_token = os.getenv("BOT_TOKEN", "")
    if not admin_chat or not bot_token:
        return

    import aiohttp
    text = (
        f"⚠️ *Celery Task Failed*\n\n"
        f"📋 Task: `{task_name}`\n"
        f"❌ Error: `{exception}`\n"
        f"🕐 Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": int(admin_chat), "text": text, "parse_mode": "Markdown"}
    try:
        async def _send():
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload,
                                       timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    pass
        import asyncio
        asyncio.new_event_loop().run_until_complete(_send())
    except Exception:
        pass
    logger.error(f"[Celery] Task failure: {task_name} — {exception}")


@signals.task_retry.connect
def _on_task_retry(sender=None, reason=None, **kwargs):
    """Log task retry attempts."""
    task_name = sender.name if sender else "unknown"
    logger.warning(f"[Celery] Task retry: {task_name} — reason: {reason}")


# ── Health check task ────────────────────────────────────────────────

@celery_app.task(bind=False)
def health_check():
    """Simple health check — returns OK if Celery is running."""
    return {"status": "ok", "service": "celery_worker"}


if __name__ == "__main__":
    celery_app.start()