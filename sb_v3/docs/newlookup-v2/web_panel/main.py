from __future__ import annotations

"""
Главный файл веб-панели админа
"""

import os
import asyncio
import signal
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import logging

from shared.config.env_utils import StartupValidationError, validate_startup_env
from shared.database.session import init_db, async_session_maker
from shared.database.tasks_session import init_tasks_db
from sqlalchemy import select
from shared.database.models import Broadcast
from shared.services.nocodb_service import NocoDBService
from web_panel.config import web_panel_config
from web_panel.api.broadcasts import send_broadcast_task
import web_panel.auth as auth  # auth helpers: require_page_access, require_finance_access, etc.

limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
from web_panel.api import (
    auth as auth_api, workers, users, bots, orders, analytics, reports, 
    support_tickets, complaints, broadcasts, dashboard, telegram_sync, files, products,
    deposits, sellers, banks, admins, audit, bank_items, pricing_config, service_prices, seller_moderation, cc_catalog,
    checks, accounts, esim, cc, education, another_services, brute_bank, seller_crm, worker_crm, marketers, bot_owners, admin_roles, export, automation, services, stock,
    seller_mini_app, seller_deposits, menu_categories, knowledge_base, seller_team,
)
from web_panel.api import bulk_discounts, referral_settings
from web_panel.api import service_order_config as service_order_config_api
from web_panel.api import admin_referrals as admin_referrals_api
from web_panel.api import documents as documents_api
from web_panel.api import disputes as disputes_api
from web_panel.api import withdrawals as withdrawals_api
from web_panel.api import ops_dashboard
from web_panel.api import global_search
from web_panel.api import analytics_advanced
from web_panel.api import alerts as alerts_api

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def _validate_web_panel_startup() -> None:
    warnings = validate_startup_env(
        "web_panel",
        required=[
            "DATABASE_URL",
            "ADMIN_USERNAME",
            "ADMIN_PASSWORD",
            "WEB_PANEL_SECRET_KEY",
            "INTERNAL_API_TOKEN",
        ],
        optional=["MAIN_BOT_TOKEN", "SUPPORT_BOT_TOKEN", "WORKER_BOT_TOKEN", "ORDERS_CHANNEL_ID"],
    )
    for warning in warnings:
        logger.warning(warning)

async def _send_daily_owner_stats():
    """Ежедневная рассылка статистики владельцам ботов"""
    from aiogram import Bot
    from shared.database.models import MirrorBot
    from shared.services.bot_owner_service import get_owner_stats

    token = web_panel_config.main_bot_token
    if not token:
        return

    bot = Bot(token=token)
    try:
        async with async_session_maker() as session:
            result = await session.execute(
                select(MirrorBot.owner_user_id).where(MirrorBot.is_active == True).distinct()
            )
            owner_ids = list(set(row[0] for row in result.all()))

            for owner_id in owner_ids:
                try:
                    stats = await get_owner_stats(session, owner_id)
                    if stats["income_total"] == 0 and stats["balance"] == 0:
                        continue

                    text = (
                        f"📊 **Ежедневный отчёт по вашим ботам**\n\n"
                        f"💰 Баланс: ${stats['balance']:.2f}\n"
                        f"📈 Доход всего: ${stats['income_total']:.2f}\n\n"
                        f"**За день:** потратили ${stats['spent_today']:.2f} | пополнили ${stats['topped_up_today']:.2f} | ваш доход ${stats['income_today']:.2f}\n"
                        f"**За неделю:** потратили ${stats['spent_week']:.2f} | пополнили ${stats['topped_up_week']:.2f} | ваш доход ${stats['income_week']:.2f}\n"
                        f"**За месяц:** потратили ${stats['spent_month']:.2f} | пополнили ${stats['topped_up_month']:.2f} | ваш доход ${stats['income_month']:.2f}"
                    )
                    await bot.send_message(owner_id, text, parse_mode="Markdown")
                except Exception as e:
                    logger.warning(f"Failed to send daily stats to owner {owner_id}: {e}")
    finally:
        await bot.session.close()


async def _check_scheduled_broadcasts():
    """Проверка отложенных рассылок — запуск по таймеру"""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    async with async_session_maker() as session:
        result = await session.execute(
            select(Broadcast).where(
                Broadcast.status == "scheduled",
                Broadcast.scheduled_at <= now
            )
        )
        broadcasts = result.scalars().all()
        for broadcast in broadcasts:
            broadcast.status = "pending"
            broadcast.scheduled_at = None
            await session.commit()
            logger.info(f"Starting scheduled broadcast {broadcast.id}")
            asyncio.create_task(send_broadcast_task(broadcast.id, web_panel_config.database_url))


async def _auto_confirm_seller_orders():
    from shared.services.seller_order_delivery_service import auto_confirm_expired_orders

    async with async_session_maker() as session:
        confirmed = await auto_confirm_expired_orders(session)
        if confirmed:
            logger.info("Auto-confirmed %s seller orders", confirmed)


async def _auto_unpublish_seller_items():
    from shared.services.seller_inventory_service import auto_unpublish_expired_seller_items

    async with async_session_maker() as session:
        unpublished = await auto_unpublish_expired_seller_items(session)
        if unpublished:
            logger.info("Auto-unpublished %s seller items", unpublished)


async def _warm_menu_count_cache():
    from shared.services.menu_count_cache_service import MenuCountCacheService

    async with async_session_maker() as session:
        await MenuCountCacheService.warm_all_counts(session)


async def _run_ledger_reconciliation():
    from shared.services.ledger_reconciliation_service import LedgerReconciliationService

    async with async_session_maker() as session:
        result = await LedgerReconciliationService.run_full_reconciliation(session)
        if result["issue_count"]:
            logger.warning("Ledger reconciliation detected %s issues", result["issue_count"])


async def _auto_resolve_disputes():
    """Auto-resolve disputes where seller didn't respond within 24h.
    
    NOTE: This is a fallback for environments without Celery.
    Primary implementation: shared.tasks.auto_complete.process_expired_seller_disputes
    """
    from shared.services.seller_dispute_service import SellerDisputeService
    async with async_session_maker() as session:
        resolved = await SellerDisputeService.auto_resolve_expired_disputes(session, limit=50)
        if resolved > 0:
            logger.info("Auto-resolved %d expired disputes (seller no-response)", resolved)


async def _check_alerts_job():
    """Периодическая проверка алертов и отправка в Telegram."""
    from web_panel.services.alert_service import check_alerts
    try:
        async with async_session_maker() as session:
            fired = await check_alerts(session)
            if fired:
                logger.info("Alerts fired: %s", fired)
    except Exception as exc:
        logger.warning("Alert check job error: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _validate_web_panel_startup()
    await init_db()
    await init_tasks_db()

    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(_check_scheduled_broadcasts, "interval", minutes=1, id="broadcast_check",
                      misfire_grace_time=30, coalesce=True)
    scheduler.add_job(_auto_confirm_seller_orders, "interval", minutes=5, id="seller_order_auto_confirm",
                      misfire_grace_time=60, coalesce=True)
    scheduler.add_job(_auto_unpublish_seller_items, "interval", minutes=5, id="seller_item_auto_unpublish",
                      misfire_grace_time=60, coalesce=True)
    scheduler.add_job(_warm_menu_count_cache, "interval", minutes=5, id="mirror_menu_count_cache",
                      misfire_grace_time=60, coalesce=True)
    scheduler.add_job(_run_ledger_reconciliation, "interval", minutes=15, id="ledger_reconciliation",
                      misfire_grace_time=120, coalesce=True)
    scheduler.add_job(_send_daily_owner_stats, "cron", hour=9, minute=0, id="daily_owner_stats",
                      misfire_grace_time=300, coalesce=True)
    # scheduler.add_job(_auto_resolve_disputes, "interval", minutes=10, id="dispute_auto_resolve",
    #                   misfire_grace_time=60, coalesce=True)  # REMOVED: Celery task process_expired_seller_disputes (15min) handles disputes
    scheduler.add_job(_check_alerts_job, "interval", minutes=5, id="alert_check",
                      misfire_grace_time=60, coalesce=True)
    scheduler.start()

    try:
        await _warm_menu_count_cache()
    except Exception as exc:
        logger.warning("Menu count cache warm failed (non-fatal): %s", exc)
    try:
        from shared.services.system_settings_service import SystemSettingsService
        async with async_session_maker() as _ss:
            await SystemSettingsService.seed_defaults(_ss)
    except Exception as exc:
        logger.warning("SystemSettings seed failed (non-fatal): %s", exc)

    yield

    # Graceful shutdown: даём текущим job'ам завершиться (до 30 с)
    scheduler.shutdown(wait=True)
    logger.info("Scheduler shut down cleanly")


# Создание приложения
app = FastAPI(
    title="Admin Panel",
    description="Панель управления ботами и заказами",
    version="1.0.0",
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Prometheus-compatible metrics middleware
from web_panel.services.metrics_service import MetricsMiddleware, get_metrics_text
from starlette.responses import PlainTextResponse as _PlainTextResponse
app.add_middleware(MetricsMiddleware)


@app.exception_handler(Exception)
async def _unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled web_panel exception: %s", exc)
    NocoDBService.log_error(
        user_id=None,
        error_type=type(exc).__name__,
        context={
            "source": "web_panel",
            "path": request.url.path,
            "method": request.method,
            "error": str(exc),
        },
    )
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# Ловим SQLAlchemy OperationalError отдельно для понятного сообщения
from sqlalchemy.exc import OperationalError as _SAOperationalError

@app.exception_handler(_SAOperationalError)
async def _db_error_handler(request: Request, exc: _SAOperationalError):
    logger.error("Database connection error on %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(status_code=503, content={"detail": "Database temporarily unavailable, please retry"})

# CORS - restrict in production via CORS_ORIGINS env
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Статические файлы и шаблоны
import os as _os
_static_dir = _os.path.join(_os.path.dirname(__file__), "static")
if _os.path.exists(_static_dir):
    app.mount("/static", StaticFiles(directory=_static_dir), name="static")
templates = Jinja2Templates(directory="web_panel/templates")

# Seller Mini App v2 - serve dist assets at /seller-mini-app/assets
_seller_mini_app_assets = _os.path.join(_os.path.dirname(__file__), "seller_mini_app_v2", "dist", "public", "assets")
if _os.path.exists(_seller_mini_app_assets):
    app.mount("/seller-mini-app/assets", StaticFiles(directory=_seller_mini_app_assets), name="seller_mini_app_assets")

# Подключение роутеров
app.include_router(auth_api.router, prefix="/api/auth", tags=["auth"])
app.include_router(
    workers.router,
    prefix="/api/workers",
    tags=["workers"],
    dependencies=[Depends(auth.require_page_access("workers"))],
)
app.include_router(
    users.router,
    prefix="/api/users",
    tags=["users"],
    dependencies=[Depends(auth.require_page_access("users"))],
)
app.include_router(
    bots.router,
    prefix="/api/bots",
    tags=["bots"],
    dependencies=[Depends(auth.require_page_access("bots"))],
)
app.include_router(
    orders.router,
    prefix="/api/orders",
    tags=["orders"],
    dependencies=[Depends(auth.require_orders_access())],
)
app.include_router(
    analytics.router,
    prefix="/api/analytics",
    tags=["analytics"],
    dependencies=[Depends(auth.require_page_access("analytics"))],
)
app.include_router(
    reports.router,
    prefix="/api/reports",
    tags=["reports"],
    dependencies=[Depends(auth.require_finance_access())],
)
app.include_router(
    support_tickets.router,
    prefix="/api/support-tickets",
    tags=["support"],
    dependencies=[Depends(auth.require_support_access())],
)
app.include_router(
    complaints.router,
    prefix="/api/complaints",
    tags=["complaints"],
    dependencies=[Depends(auth.require_complaints_access())],
)
app.include_router(
    broadcasts.router,
    prefix="/api/broadcasts",
    tags=["broadcasts"],
    dependencies=[Depends(auth.require_page_access("broadcasts"))],
)
app.include_router(
    dashboard.router,
    prefix="/api/dashboard",
    tags=["dashboard"],
    dependencies=[Depends(auth.require_page_access("dashboard"))],
)
app.include_router(
    telegram_sync.router,
    prefix="/api/telegram",
    tags=["telegram"],
    dependencies=[Depends(auth.require_page_access("bots"))],
)
app.include_router(
    files.router,
    prefix="/api/files",
    tags=["files"],
    dependencies=[Depends(auth.require_page_access("products"))],
)
app.include_router(
    products.router,
    prefix="/api/products",
    tags=["products"],
    dependencies=[Depends(auth.require_catalog_read_access())],
)
app.include_router(
    deposits.router,
    prefix="/api/deposits",
    tags=["deposits"],
    dependencies=[Depends(auth.require_finance_access())],
)
app.include_router(
    bank_items.router,
    prefix="/api/bank-items",
    tags=["bank-items"],
    dependencies=[Depends(auth.require_catalog_read_access("banks"))],
)
app.include_router(
    pricing_config.router,
    prefix="/api/pricing-config",
    tags=["pricing-config"],
    dependencies=[Depends(auth.require_page_access("pricing-config"))],
)
app.include_router(
    service_prices.router,
    prefix="/api/service-prices",
    tags=["service-prices"],
    dependencies=[Depends(auth.require_page_access("service-prices"))],
)
app.include_router(services.router)
app.include_router(stock.router)
app.include_router(
    sellers.router,
    dependencies=[Depends(auth.require_seller_read_access())],
)
app.include_router(
    banks.router,
    prefix="/api/banks",
    tags=["banks"],
    dependencies=[Depends(auth.require_catalog_read_access("banks"))],
)
app.include_router(
    admins.router,
    prefix="/api/admins",
    tags=["admins"],
    dependencies=[Depends(auth.require_admin_management_access())],
)
app.include_router(
    audit.router,
    prefix="/api/audit",
    tags=["audit"],
    dependencies=[Depends(auth.require_audit_access())],
)
app.include_router(
    checks.router,
    prefix="/api/checks",
    tags=["checks"],
    dependencies=[Depends(auth.require_page_access("checks"))],
)
app.include_router(
    documents_api.router,
    dependencies=[Depends(auth.require_seller_moderation_access())],
)
app.include_router(
    brute_bank.router,
    tags=["brute-bank"],
    dependencies=[Depends(auth.require_catalog_read_access("brute_bank"))],
)
app.include_router(
    seller_moderation.router,
    dependencies=[Depends(auth.require_seller_moderation_access())],
)
app.include_router(
    cc_catalog.router,
    dependencies=[Depends(auth.require_catalog_read_access("cc"))],
)
app.include_router(
    accounts.router,
    dependencies=[Depends(auth.require_catalog_read_access("accounts"))],
)
app.include_router(
    esim.router,
    dependencies=[Depends(auth.require_catalog_read_access("esim"))],
)
app.include_router(
    education.router,
    dependencies=[Depends(auth.require_catalog_read_access("education"))],
)
app.include_router(knowledge_base.router, prefix="/api/knowledge-base", tags=["knowledge-base"])
app.include_router(
    another_services.router,
    dependencies=[Depends(auth.require_catalog_read_access("another-services"))],
)
app.include_router(
    seller_crm.router,
    dependencies=[Depends(auth.require_seller_read_access())],
)
app.include_router(
    worker_crm.router,
    dependencies=[Depends(auth.require_page_access("worker_crm"))],
)
app.include_router(
    marketers.router,
    dependencies=[Depends(auth.require_finance_access())],
)
app.include_router(bot_owners.router)
app.include_router(
    admin_roles.router,
    dependencies=[Depends(auth.require_admin_management_access())],
)
app.include_router(
    export.router,
    dependencies=[Depends(auth.require_finance_access())],
)
app.include_router(
    automation.router,
    dependencies=[Depends(auth.require_page_access("automation"))],
)
app.include_router(seller_mini_app.router)
app.include_router(
    seller_deposits.router,
    dependencies=[Depends(auth.require_finance_access())],
)
app.include_router(seller_team.router)
app.include_router(
    menu_categories.router,
    dependencies=[Depends(auth.require_catalog_read_access())],
)
app.include_router(
    bulk_discounts.router,
    prefix="/api/bulk-discounts",
    tags=["bulk-discounts"],
    dependencies=[Depends(auth.require_page_access("bulk-discounts"))],
)
app.include_router(
    referral_settings.router,
    prefix="/api/settings",
    tags=["settings"],
    dependencies=[Depends(auth.require_page_access("pricing-config"))],
)
app.include_router(
    service_order_config_api.router,
    prefix="/api/service-order-config",
    tags=["service-order-config"],
    dependencies=[Depends(auth.require_page_access("pricing-config"))],
)

# ── New analytics & control routers ──────────────────────────────────────────
app.include_router(
    disputes_api.router,
    dependencies=[Depends(auth.require_finance_access())],
)
app.include_router(
    withdrawals_api.router,
    dependencies=[Depends(auth.require_finance_access())],
)
app.include_router(
    ops_dashboard.router,
    dependencies=[Depends(auth.require_page_access("ops"))],
)
app.include_router(
    global_search.router,
    dependencies=[Depends(auth.require_page_access("users"))],
)
app.include_router(
    analytics_advanced.router,
    dependencies=[Depends(auth.require_page_access("analytics"))],
)
app.include_router(
    alerts_api.router,
    dependencies=[Depends(auth.require_page_access("ops"))],
)
app.include_router(
    admin_referrals_api.router,
    dependencies=[Depends(auth.require_page_access("referrals"))],
)


def _ctx(request: Request, active_page: str = "", current_user: dict = None, **extra):
    """Стандартный контекст для шаблонов"""
    ctx = {"request": request, "active_page": active_page, **extra}
    if current_user is not None:
        allowed = current_user.get("allowed_pages") or auth.get_allowed_pages_for_role(
            current_user.get("role"),
            current_user.get("allowed_catalogs"),
            current_user.get("permissions"),
        )
        ctx["allowed_pages"] = list(allowed) if not isinstance(allowed, list) else allowed
    return ctx


@app.get("/")
async def root(request: Request):
    """Главная страница"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/dashboard")
async def dashboard_page(request: Request, current_user: dict = Depends(auth.require_page_access("dashboard"))):
    """Главная панель управления"""
    return templates.TemplateResponse("dashboard.html", _ctx(request, "dashboard", current_user=current_user))


@app.get("/support")
async def support_page(request: Request, current_user: dict = Depends(auth.require_page_access("support"))):
    """Страница Support Chat"""
    return templates.TemplateResponse("support_chat.html", _ctx(request, "support", current_user=current_user))


@app.get("/support-old")
async def support_old_page(request: Request, current_user: dict = Depends(auth.require_page_access("support"))):
    """Старая страница Support Tickets"""
    return templates.TemplateResponse("support_tickets.html", _ctx(request, "support", current_user=current_user))


@app.get("/deposits")
async def deposits_page(request: Request, current_user: dict = Depends(auth.require_finance_access())):
    """Страница депозитов"""
    return templates.TemplateResponse("deposits.html", _ctx(request, "deposits", current_user=current_user))


@app.get("/finance")
async def finance_page(request: Request, current_user: dict = Depends(auth.require_finance_access())):
    """Finance hub page."""
    return templates.TemplateResponse("finance.html", _ctx(request, "finance", current_user=current_user))


@app.get("/banks")
async def bank_items_page(request: Request, current_user: dict = Depends(auth.require_catalog_read_access("banks"))):
    """Страница управления банками"""
    return templates.TemplateResponse("bank_items.html", _ctx(request, "banks", current_user=current_user))


@app.get("/service-prices")
async def service_prices_page(request: Request, current_user: dict = Depends(auth.require_page_access("service-prices"))):
    """Страница управления ценами"""
    return templates.TemplateResponse("service_prices.html", _ctx(request, "service-prices", current_user=current_user))


@app.get("/pricing-config")
async def pricing_config_page(request: Request, current_user: dict = Depends(auth.require_page_access("pricing-config"))):
    """Runtime pricing config"""
    return templates.TemplateResponse("pricing_config.html", _ctx(request, "pricing-config", current_user=current_user))


@app.get("/bulk-discounts")
async def bulk_discounts_page(request: Request, current_user: dict = Depends(auth.require_page_access("pricing-config"))):
    """Bulk discount tiers management"""
    return templates.TemplateResponse("bulk_discounts.html", _ctx(request, "bulk-discounts", current_user=current_user))


@app.get("/service-order-config")
async def service_order_config_page(request: Request, current_user: dict = Depends(auth.require_page_access("pricing-config"))):
    """Service order types & ETA configuration"""
    return templates.TemplateResponse("service_order_config.html", _ctx(request, "service-order-config", current_user=current_user))


@app.get("/products")
async def products_page(request: Request, current_user: dict = Depends(auth.require_catalog_read_access("products"))):
    """Страница управления товарами"""
    return templates.TemplateResponse("products.html", _ctx(request, "products", current_user=current_user))


@app.get("/users")
async def users_page(request: Request, current_user: dict = Depends(auth.require_page_access("users"))):
    """Страница управления пользователями"""
    return templates.TemplateResponse("users.html", _ctx(request, "users", current_user=current_user))


@app.get("/bots")
async def bots_page(request: Request, current_user: dict = Depends(auth.require_page_access("bots"))):
    """Страница управления ботами"""
    return templates.TemplateResponse("bots.html", _ctx(request, "bots", current_user=current_user))


@app.get("/workers")
async def workers_page(request: Request, current_user: dict = Depends(auth.require_page_access("workers"))):
    """Страница управления воркерами"""
    return templates.TemplateResponse("workers.html", _ctx(request, "workers", current_user=current_user))


@app.get("/complaints")
async def complaints_page(request: Request, current_user: dict = Depends(auth.require_complaints_access())):
    """Страница управления жалобами"""
    return templates.TemplateResponse("complaints.html", _ctx(request, "complaints", current_user=current_user))


@app.get("/disputes")
async def disputes_page(request: Request, current_user: dict = Depends(auth.require_finance_access())):
    """Standalone disputes queue."""
    return templates.TemplateResponse("disputes.html", _ctx(request, "disputes", current_user=current_user))


@app.get("/sellers")
async def sellers_page(request: Request, current_user: dict = Depends(auth.require_seller_read_access())):
    """Страница управления селлерами"""
    return templates.TemplateResponse("sellers.html", _ctx(request, "sellers", current_user=current_user))


@app.get("/seller-moderation")
async def seller_moderation_page(request: Request, current_user: dict = Depends(auth.require_seller_moderation_access())):
    """Страница модерации товаров селлеров (Banks, CC)"""
    return templates.TemplateResponse("seller_moderation.html", _ctx(request, "seller_moderation", current_user=current_user))


@app.get("/seller-crm")
async def seller_crm_page(request: Request, current_user: dict = Depends(auth.require_seller_read_access())):
    """Seller CRM Kanban"""
    return templates.TemplateResponse("seller_crm.html", _ctx(request, "seller_crm", current_user=current_user))


@app.get("/worker-crm")
async def worker_crm_page(request: Request, current_user: dict = Depends(auth.require_page_access("worker_crm"))):
    """Worker CRM: выводы, расходы, HR-метрики"""
    return templates.TemplateResponse("worker_crm.html", _ctx(request, "worker_crm", current_user=current_user))


@app.get("/seller-mini-app")
async def seller_mini_app_page(request: Request):
    """Serve Seller Mini App v2 (Vite build or dev server)."""
    import os
    from fastapi.responses import FileResponse
    
    # Production build directory
    dist_dir = os.path.join(os.path.dirname(__file__), "seller_mini_app_v2", "dist", "public")
    index_html = os.path.join(dist_dir, "index.html")
    
    if os.path.exists(index_html):
        return FileResponse(index_html)
    
    # Development mode - show instructions
    return templates.TemplateResponse("seller_mini_app_v2.html", {"request": request})


@app.get("/seller-mini-app-test")
async def seller_mini_app_test_page(request: Request):
    """Test page for Seller Mini App v2."""
    return {"message": "Seller Mini App v2 is ready", "version": "2.0"}


@app.get("/marketers")
async def marketers_page(request: Request, current_user: dict = Depends(auth.require_finance_access())):
    """Маркетологи"""
    return templates.TemplateResponse("marketers.html", _ctx(request, "marketers", current_user=current_user))


@app.get("/seller-deposits")
async def seller_deposits_page(request: Request, current_user: dict = Depends(auth.require_finance_access())):
    """Seller security deposit payments"""
    return templates.TemplateResponse("seller_deposits.html", _ctx(request, "seller-deposits", current_user=current_user))


@app.get("/withdrawals")
async def withdrawals_page(request: Request, current_user: dict = Depends(auth.require_finance_access())):
    """Unified withdrawals page for all team members"""
    return templates.TemplateResponse("withdrawals.html", _ctx(request, "withdrawals", current_user=current_user))


@app.get("/admins")
async def admins_page(request: Request, current_user: dict = Depends(auth.require_admin_management_access())):
    """Страница управления админами"""
    return templates.TemplateResponse("admins.html", _ctx(request, "admins", current_user=current_user))


@app.get("/admin-roles")
async def admin_roles_page(request: Request, current_user: dict = Depends(auth.require_admin_management_access())):
    """Кастомные роли администраторов"""
    return templates.TemplateResponse("admin_roles.html", _ctx(request, "admin_roles", current_user=current_user))


@app.get("/audit")
async def audit_page(request: Request, current_user: dict = Depends(auth.require_audit_access())):
    """Страница журнала аудита"""
    return templates.TemplateResponse("audit.html", _ctx(request, "audit", current_user=current_user))


@app.get("/broadcasts")
async def broadcasts_page(request: Request, current_user: dict = Depends(auth.require_page_access("broadcasts"))):
    """Страница рассылок с таймером"""
    return templates.TemplateResponse("broadcasts.html", _ctx(request, "broadcasts", current_user=current_user))


@app.get("/referrals")
async def referrals_page(request: Request, _: dict = Depends(auth.require_page_access("referrals"))):
    """Страница управления реферальной программой"""
    return templates.TemplateResponse("admin_referrals.html", _ctx(request, "referrals"))


@app.get("/checks")
async def checks_page(request: Request, current_user: dict = Depends(auth.require_page_access("checks"))):
    """Страница мониторинга доставки уведомлений"""
    return templates.TemplateResponse("checks.html", _ctx(request, "checks", current_user=current_user))


@app.get("/documents")
async def documents_page(request: Request, current_user: dict = Depends(auth.require_seller_moderation_access())):
    """Страница управления Document / Fullz items (seller uploads)"""
    return templates.TemplateResponse("documents.html", _ctx(request, "documents", current_user=current_user))


@app.get("/brute-bank")
async def brute_bank_page(request: Request, current_user: dict = Depends(auth.require_catalog_read_access("brute_bank"))):
    """Страница управления Brute Bank"""
    return templates.TemplateResponse("brute_bank.html", _ctx(request, "brute_bank", current_user=current_user))


@app.get("/orders")
async def orders_page(request: Request, current_user: dict = Depends(auth.require_orders_access())):
    """Страница управления заказами"""
    return templates.TemplateResponse("orders.html", _ctx(request, "orders", current_user=current_user))


@app.get("/analytics")
async def analytics_page(request: Request, current_user: dict = Depends(auth.require_page_access("analytics"))):
    """Страница аналитики"""
    return templates.TemplateResponse("analytics.html", _ctx(request, "analytics", current_user=current_user))


@app.get("/ops")
async def ops_dashboard_page(request: Request, current_user: dict = Depends(auth.require_page_access("ops"))):
    """Ops Dashboard - мониторинг очередей и алертов"""
    return templates.TemplateResponse("ops_dashboard.html", _ctx(request, "ops", current_user=current_user))


@app.get("/accounts")
async def accounts_page(request: Request, current_user: dict = Depends(auth.require_catalog_read_access("accounts"))):
    """Страница управления аккаунтами/подписками"""
    return templates.TemplateResponse("accounts.html", _ctx(request, "accounts", current_user=current_user))


@app.get("/esim")
async def esim_page(request: Request, current_user: dict = Depends(auth.require_catalog_read_access("esim"))):
    """Страница управления eSIM"""
    return templates.TemplateResponse("esim.html", _ctx(request, "esim", current_user=current_user))


@app.get("/cc")
async def cc_page(request: Request, current_user: dict = Depends(auth.require_catalog_read_access("cc"))):
    """Страница управления CC"""
    return templates.TemplateResponse("cc.html", _ctx(request, "cc", current_user=current_user))


@app.get("/education")
async def education_page(request: Request, current_user: dict = Depends(auth.require_catalog_read_access("education"))):
    """Страница управления Education"""
    return templates.TemplateResponse("education.html", _ctx(request, "education", current_user=current_user))


@app.get("/another-services")
async def another_services_page(request: Request, current_user: dict = Depends(auth.require_catalog_read_access("another-services"))):
    """Страница управления Another Services"""
    return templates.TemplateResponse("another_services.html", _ctx(request, "another-services", current_user=current_user))


@app.get("/automation")
async def automation_page(request: Request, current_user: dict = Depends(auth.require_page_access("automation"))):
    """Страница управления automation"""
    return templates.TemplateResponse("automation.html", _ctx(request, "automation", current_user=current_user))


@app.get("/instructions")
async def instructions_page(request: Request, current_user: dict = Depends(auth.require_page_access("instructions"))):
    """Страница видео-инструкций"""
    from web_panel.config import web_panel_config
    return templates.TemplateResponse(
        "instructions.html",
        _ctx(request, "instructions", tutorial_url=web_panel_config.instructions_tutorial_url)
    )


@app.get("/knowledge-base")
async def knowledge_base_page(request: Request, current_user: dict = Depends(auth.require_page_access("knowledge-base"))):
    """Страница управления базой знаний"""
    return templates.TemplateResponse("knowledge_base.html", _ctx(request, "knowledge-base", current_user=current_user))


@app.get("/admin-structure")
async def admin_structure_page(request: Request, current_user: dict = Depends(auth.require_page_access("admin-structure"))):
    """Карта разделов админки и статус готовности"""
    return templates.TemplateResponse("admin_structure.html", _ctx(request, "admin-structure", current_user=current_user))


@app.get("/categories")
async def categories_page(request: Request, current_user: dict = Depends(auth.require_page_access("categories"))):
    """Страница управления категориями"""
    return templates.TemplateResponse("menu_categories.html", _ctx(request, "categories", current_user=current_user))


@app.get("/services")
async def services_page(request: Request, current_user: dict = Depends(auth.require_page_access("service-prices"))):
    """Страница управления сервисами"""
    return templates.TemplateResponse("services.html", _ctx(request, "services", current_user=current_user))


@app.get("/reports")
async def reports_page(request: Request, current_user: dict = Depends(auth.require_finance_access())):
    """Страница отчётов (Revenue, By Bots, By Users)"""
    return templates.TemplateResponse("reports.html", _ctx(request, "reports", current_user=current_user))


@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    return {"status": "ok"}


@app.get("/metrics")
async def prometheus_metrics():
    """Prometheus-compatible metrics endpoint."""
    from shared.database.session import engine as _db_engine
    return _PlainTextResponse(get_metrics_text(_db_engine), media_type="text/plain; version=0.0.4")


if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting Admin Panel on {web_panel_config.host}:{web_panel_config.port}")
    
    uvicorn.run(
        "web_panel.main:app",
        host=web_panel_config.host,
        port=web_panel_config.port,
        reload=True
    )

