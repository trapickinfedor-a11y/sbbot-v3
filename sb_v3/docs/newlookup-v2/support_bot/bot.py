"""
Главный файл Support Bot
"""

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

from support_bot.config import support_bot_config
from support_bot.handlers import (
    accountant_panel,
    accounts,
    bulk_orders,
    complaints,
    esim,
    files,
    history,
    manual_balance,
    mass_broadcast,
    orders,
    profile,
    seller_moderation,
    seller_orders,
    start,
    statistics,
    upload_product,
    uploader_panel,
    user_info,
    tickets,
    work_orders,
    worker_withdrawal,
)
from support_bot.middlewares.database import DatabaseMiddleware
from support_bot.middlewares.worker_auth import WorkerAuthMiddleware
from shared.config.env_utils import StartupValidationError, validate_startup_env
from shared.database.session import async_session_maker
from shared.database.tasks_session import init_tasks_db
from shared.middlewares.error_logging import GlobalErrorLoggingMiddleware

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('support_bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def _validate_support_bot_startup() -> None:
    warnings = validate_startup_env(
        "support_bot",
        required=["SUPPORT_BOT_TOKEN", "DATABASE_URL", "INTERNAL_API_TOKEN"],
        optional=["ADMIN_IDS", "ORDERS_CHANNEL_ID", "SUPPORT_LOG_CHAT_ID"],
    )
    for warning in warnings:
        logger.warning(warning)

async def main():
    """Запуск бота"""

    try:
        _validate_support_bot_startup()
    except StartupValidationError as exc:
        logger.error(str(exc))
        sys.exit(1)

    await init_tasks_db()
    
    # Инициализация бота и диспетчера
    bot = Bot(
        token=support_bot_config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    from shared.services.admin_notification_service import AdminNotificationService
    AdminNotificationService.init(bot)
    
    dp = Dispatcher()

    
    @dp.errors()
    
    async def _global_error_handler(event, **kwargs):
    
        import logging as _l
    
        _l.getLogger(__name__).exception("Unhandled bot error: %s", event.exception)
    
        return True

    
    # Подключаем middleware для работы с БД
    dp.update.middleware(DatabaseMiddleware(async_session_maker))
    dp.update.middleware(GlobalErrorLoggingMiddleware("support_bot"))
    
    # Подключаем middleware для проверки прав воркеров
    dp.message.middleware(WorkerAuthMiddleware())
    dp.callback_query.middleware(WorkerAuthMiddleware())
    
    # Регистрируем роутеры
    # IMPORTANT: Порядок имеет значение — специфичные фильтры ПЕРЕД общими
    dp.include_router(tickets.router)
    dp.include_router(mass_broadcast.router)
    dp.include_router(start.router)
    dp.include_router(user_info.router)
    dp.include_router(seller_orders.router)
    dp.include_router(seller_moderation.router)
    dp.include_router(manual_balance.router)
    dp.include_router(upload_product.router)
    dp.include_router(uploader_panel.router)
    dp.include_router(accountant_panel.router)
    dp.include_router(accounts.router)
    dp.include_router(esim.router)
    # work_orders ПЕРЕД orders — notify_take:/work_done: не должны перехватываться orders
    dp.include_router(work_orders.router)
    # bulk_orders ПЕРЕД orders — bulk_item:/bulk_done: не должны перехватываться orders
    dp.include_router(bulk_orders.router)
    # files ПЕРЕД orders — FileStates устанавливается из orders (order_add_files:)
    # но обрабатываться должны именно files-роутером
    dp.include_router(files.router)
    dp.include_router(orders.router)
    dp.include_router(complaints.router)
    dp.include_router(profile.router)
    dp.include_router(statistics.router)
    dp.include_router(history.router)
    dp.include_router(worker_withdrawal.router)
    
    # Worker order reminder watcher (every 2h for in-progress orders)
    from support_bot.services.worker_reminder_service import run_worker_order_reminder_watcher
    _reminder_stop = asyncio.Event()
    _reminder_tasks: list = []

    async def _start_worker_reminders(*args, **kwargs):
        from shared.database.session import async_session_maker as _sm
        t = asyncio.create_task(run_worker_order_reminder_watcher(_reminder_stop, _sm, bot))
        _reminder_tasks.append(t)

    async def _stop_worker_reminders(*args, **kwargs):
        _reminder_stop.set()
        for t in _reminder_tasks:
            t.cancel()

    dp.startup.register(_start_worker_reminders)
    dp.shutdown.register(_stop_worker_reminders)

    logger.info("Support Bot starting...")

    try:
        try:
            await bot.delete_webhook(drop_pending_updates=True)
        except Exception as _dw_exc:
            import logging; logging.getLogger(__name__).warning("delete_webhook failed (ignored): %s", _dw_exc)
        await dp.start_polling(bot)
    
    finally:
        await bot.session.close()
        logger.info("Support Bot stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Support Bot stopped by user")

