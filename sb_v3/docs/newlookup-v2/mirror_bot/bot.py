from __future__ import annotations

import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from mirror_bot.middlewares.session import DatabaseSessionMiddleware
from mirror_bot.middlewares.mirror_bot import MirrorBotMiddleware
from mirror_bot.middlewares.reply_keyboard_cancel import ReplyKeyboardCancelMiddleware
from mirror_bot.middlewares.ban_check import BanCheckMiddleware
from mirror_bot.middlewares.bot_status_check import BotStatusCheckMiddleware
from mirror_bot.middlewares.debug_logger import DebugLoggerMiddleware
from mirror_bot.middlewares.language import LanguageMiddleware
from mirror_bot.middlewares.user_update import UserUpdateMiddleware
from shared.middlewares.error_logging import GlobalErrorLoggingMiddleware

logger = logging.getLogger(__name__)


def create_mirror_bot(token: str, mirror_bot_id: int) -> tuple[Bot, Dispatcher]:
    bot = Bot(
        token=token,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
    )
    
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    @dp.errors()
    async def _global_error_handler(event, **kwargs):
        import logging as _l
        _l.getLogger(__name__).exception("Unhandled bot error: %s", event.exception)
        return True

    
    dp.update.middleware(DebugLoggerMiddleware())  # Debug логирование
    dp.update.middleware(DatabaseSessionMiddleware())
    dp.update.middleware(GlobalErrorLoggingMiddleware("mirror_bot"))
    dp.update.middleware(MirrorBotMiddleware(mirror_bot_id))
    dp.update.middleware(UserUpdateMiddleware())  # Обновление username пользователя (должно быть после DatabaseSessionMiddleware)
    dp.update.middleware(LanguageMiddleware())  # Определение языка пользователя (должно быть ПЕРЕД проверками)
    dp.update.middleware(BotStatusCheckMiddleware())  # Проверка активности бота (после языка)
    dp.update.middleware(BanCheckMiddleware())  # Проверка бана пользователя (после языка)
    dp.message.middleware(ReplyKeyboardCancelMiddleware())

    cs_disabled = os.getenv("DISABLE_CS_AUTOMATION", "").strip().lower() in {"1", "true", "yes", "on"}
    if not cs_disabled:
        from mirror_bot.services.cs_automation import CsAutomationRunner, register_cs_runner

        cs_runner = CsAutomationRunner(bot=bot, mirror_bot_id=mirror_bot_id)
        register_cs_runner(mirror_bot_id, cs_runner)

        async def _startup(*args, **kwargs):
            await cs_runner.start()

        async def _shutdown(*args, **kwargs):
            await cs_runner.stop()

        dp.startup.register(_startup)
        dp.shutdown.register(_shutdown)
    else:
        logger.info("CS automation disabled via DISABLE_CS_AUTOMATION")

    # CR (Credit Report) automation runner — API-based, replaces Playwright CS runner
    cr_disabled = os.getenv("DISABLE_CR_AUTOMATION", "").strip().lower() in {"1", "true", "yes", "on"}
    if not cr_disabled:
        from mirror_bot.services.cr_automation import CrAutomationRunner, register_cr_runner

        cr_runner = CrAutomationRunner(bot=bot, mirror_bot_id=mirror_bot_id)
        register_cr_runner(mirror_bot_id, cr_runner)

        async def _cr_startup(*args, **kwargs):
            await cr_runner.start()

        async def _cr_shutdown(*args, **kwargs):
            await cr_runner.stop()

        dp.startup.register(_cr_startup)
        dp.shutdown.register(_cr_shutdown)
    else:
        logger.info("CR automation disabled via DISABLE_CR_AUTOMATION")

    # SSN / DL automation runner (usfull.info / self-hosted API)
    ssndl_disabled = os.getenv("DISABLE_SSNDL_AUTOMATION", "").strip().lower() in {"1", "true", "yes", "on"}
    if not ssndl_disabled:
        from mirror_bot.services.ssn_dl_automation import SsnDlAutomationRunner, register_ssn_dl_runner

        ssndl_runner = SsnDlAutomationRunner(bot=bot, mirror_bot_id=mirror_bot_id)
        register_ssn_dl_runner(mirror_bot_id, ssndl_runner)

        async def _ssndl_startup(*args, **kwargs):
            await ssndl_runner.start()

        async def _ssndl_shutdown(*args, **kwargs):
            await ssndl_runner.stop()

        dp.startup.register(_ssndl_startup)
        dp.shutdown.register(_ssndl_shutdown)
    else:
        logger.info("SSN/DL automation disabled via DISABLE_SSNDL_AUTOMATION")

    # Abandoned cart background watcher (only for first mirror bot to avoid duplicates)
    import asyncio
    from mirror_bot.services.abandoned_cart_service import run_abandoned_cart_watcher
    from shared.database.session import async_session_maker as _session_maker

    _cart_stop = asyncio.Event()
    _cart_task_ref: list = []

    async def _start_cart_watcher(*args, **kwargs):
        t = asyncio.create_task(run_abandoned_cart_watcher(_cart_stop, _session_maker, bot))
        _cart_task_ref.append(t)
        logger.info("Abandoned cart watcher started for mirror_bot_id=%s", mirror_bot_id)

    async def _stop_cart_watcher(*args, **kwargs):
        _cart_stop.set()
        for t in _cart_task_ref:
            t.cancel()

    if mirror_bot_id == 1:  # only first bot instance runs the watcher
        dp.startup.register(_start_cart_watcher)
        dp.shutdown.register(_stop_cart_watcher)

    # Review request service (24h after purchase) — only bot instance #1
    from mirror_bot.services.review_request_service import run_review_request_service
    _review_stop = asyncio.Event()
    _review_task_ref: list = []

    async def _start_review_service(*args, **kwargs):
        t = asyncio.create_task(run_review_request_service(_review_stop, _session_maker, bot))
        _review_task_ref.append(t)

    async def _stop_review_service(*args, **kwargs):
        _review_stop.set()
        for t in _review_task_ref:
            t.cancel()

    if mirror_bot_id == 1:
        dp.startup.register(_start_review_service)
        dp.shutdown.register(_stop_review_service)
    
    # Импортируем роутеры ВНУТРИ функции, чтобы каждый раз создавались новые экземпляры
    from mirror_bot.handlers import start, dynamic_menu, profile, rules, credit_reports, banks, esim, accounts, addinfo, documents, fullz, support, payment, products, buyer_chat, buyer_orders, cc, education, education_admin, another_services, brute_bank, seller_specials, checkout_coupons, wishlist, cart, catalog_search, onboarding, fallback, vip_watchlist
    from mirror_bot.handlers.lookup import main as lookup_main, ssn, phone, others, bank_lookup

    routers = [
        start.router, dynamic_menu.router, profile.router, rules.router, checkout_coupons.router, support.router, payment.router, lookup_main.router,
        ssn.router, phone.router, others.router, bank_lookup.router, credit_reports.router,
        banks.router, esim.router, accounts.router, addinfo.router,
        documents.router, fullz.router, products.router,
        cc.router, education.router, education_admin.router, another_services.router,
        seller_specials.router,
        brute_bank.router,
        buyer_chat.router,
        buyer_orders.router,
        wishlist.router,
        cart.router,
        catalog_search.router,
        onboarding.router,
        vip_watchlist.router,
        fallback.router  # Fallback должен быть ПОСЛЕДНИМ!
    ]
    
    for router in routers:
        router._parent_router = None  # Сбрасываем привязку к диспетчеру
        dp.include_router(router)
    
    logger.info(f"Mirror bot created for token: {token[:10]}...")
    return bot, dp
