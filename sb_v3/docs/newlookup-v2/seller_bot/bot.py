import asyncio
# Disable uvloop
try:
    import uvloop; asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())
except ImportError:
    pass
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from seller_bot.config import seller_bot_config
from seller_bot.handlers import (
    start,
    stock,
    orders,
    chat,
    profile,
    cc_stock,
    upload_fsm,
    brute_bank,
    withdrawal,
    broadcast,
    uploads,
    helpers,
    special_products,
    listings,
    bulk_import,
    documents,
    fullz,
    add_seller,
    buy_access,
)
from seller_bot.middlewares.database import DatabaseMiddleware
from seller_bot.middlewares.seller_auth import SellerAuthMiddleware
from seller_bot.middlewares.language import SellerLanguageMiddleware
from shared.config.env_utils import StartupValidationError, validate_startup_env
from shared.database.session import async_session_maker
from shared.database.tasks_session import init_tasks_db
from shared.middlewares.error_logging import GlobalErrorLoggingMiddleware

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('seller_bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def _validate_seller_bot_startup() -> None:
    warnings = validate_startup_env(
        "seller_bot",
        required=["SELLER_BOT_TOKEN", "DATABASE_URL"],
        optional=["ADMIN_IDS", "SUPPORT_BOT_TOKEN", "SELLER_MINI_APP_URL"],
    )
    for warning in warnings:
        logger.warning(warning)


async def main():
    try:
        _validate_seller_bot_startup()
    except StartupValidationError as exc:
        logger.error(str(exc))
        sys.exit(1)
    
    bot = Bot(
        token=seller_bot_config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    dp = Dispatcher()

    
    @dp.errors()
    
    async def _global_error_handler(event, **kwargs):
    
        import logging as _l
    
        _l.getLogger(__name__).exception("Unhandled bot error: %s", event.exception)
    
        return True

    
    dp.update.middleware(DatabaseMiddleware(async_session_maker))
    dp.update.middleware(GlobalErrorLoggingMiddleware("seller_bot"))
    dp.message.middleware(SellerAuthMiddleware())
    dp.callback_query.middleware(SellerAuthMiddleware())
    dp.message.middleware(SellerLanguageMiddleware())
    dp.callback_query.middleware(SellerLanguageMiddleware())
    
    dp.include_router(start.router)
    dp.include_router(stock.router)
    dp.include_router(orders.router)
    dp.include_router(chat.router)
    dp.include_router(profile.router)
    dp.include_router(upload_fsm.router)
    dp.include_router(cc_stock.router)
    dp.include_router(brute_bank.router)
    dp.include_router(special_products.router)
    dp.include_router(uploads.router)
    dp.include_router(helpers.router)
    dp.include_router(withdrawal.router)
    dp.include_router(broadcast.router)
    dp.include_router(listings.router)
    dp.include_router(bulk_import.router)
    dp.include_router(documents.router)
    dp.include_router(fullz.router)
    dp.include_router(add_seller.router)
    dp.include_router(buy_access.router)
    
    await init_tasks_db()
    logger.info("Seller Bot starting...")

    # Start background services
    from seller_bot.services.weekly_report_service import run_weekly_report_service
    from seller_bot.services.auto_payout_service import run_auto_payout_watcher
    from seller_bot.services.daily_report_service import run_daily_report_service
    stop_event = asyncio.Event()
    weekly_task = asyncio.create_task(run_weekly_report_service(stop_event, async_session_maker, bot))
    payout_task = asyncio.create_task(run_auto_payout_watcher(stop_event, async_session_maker, bot))
    daily_task = asyncio.create_task(run_daily_report_service(stop_event, async_session_maker, bot))

    try:
        try:
            await bot.delete_webhook(drop_pending_updates=True)
        except Exception as _dw_exc:
            import logging; logging.getLogger(__name__).warning("delete_webhook failed (ignored): %s", _dw_exc)
        await dp.start_polling(bot)
    finally:
        stop_event.set()
        weekly_task.cancel()
        payout_task.cancel()
        daily_task.cancel()
        await bot.session.close()
        logger.info("Seller Bot stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Seller Bot stopped by user")
