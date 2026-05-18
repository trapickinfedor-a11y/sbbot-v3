"""
Главный файл Worker Bot
"""

import asyncio
import logging
import signal
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from worker_bot.config import worker_bot_config
from worker_bot.handlers import start, dashboard as worker_dashboard
from support_bot.handlers import (
    orders,
    bulk_orders,
    statistics,
    profile,
    files,
    work_orders,
    history,
    user_info,
    complaints,
    upload_product,
    worker_withdrawal,
)
from support_bot.middlewares.database import DatabaseMiddleware
from support_bot.middlewares.worker_auth import WorkerAuthMiddleware
from support_bot.services.notification_service import NotificationService
from support_bot.services.worker_notification_service import WorkerNotificationService
from support_bot.services.order_channel_service import OrderChannelService
from support_bot.services.order_notification_service import OrderNotificationService
from support_bot.services.support_logger import SupportLogger
from support_bot.services.worker_reminder_service import run_worker_order_reminder_watcher
from shared.config.env_utils import StartupValidationError, validate_startup_env
from shared.database.session import async_session_maker
from shared.database.tasks_session import init_tasks_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("worker_bot.log"),
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger(__name__)


def _validate_worker_bot_startup() -> None:
    warnings = validate_startup_env(
        "worker_bot",
        required=["WORKER_BOT_TOKEN", "DATABASE_URL", "INTERNAL_API_TOKEN"],
        optional=["ADMIN_IDS", "ORDERS_CHANNEL_ID", "SUPPORT_LOG_CHAT_ID"],
    )
    for warning in warnings:
        logger.warning(warning)


async def start_api_server():
    """Запуск API сервера в отдельной задаче"""
    import uvicorn
    from worker_bot.api_server import app

    config = uvicorn.Config(
        app=app,
        host="0.0.0.0",
        port=8181,
        log_level="info",
    )
    server = uvicorn.Server(config)
    await server.serve()


async def main():
    """Запуск Worker Bot"""
    try:
        _validate_worker_bot_startup()
    except StartupValidationError as exc:
        logger.error(str(exc))
        sys.exit(1)

    await init_tasks_db()

    bot = Bot(
        token=worker_bot_config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    NotificationService.init(bot)
    WorkerNotificationService.init(bot)
    OrderNotificationService.init(bot)
    SupportLogger.init(bot)

    from shared.services.admin_notification_service import AdminNotificationService

    AdminNotificationService.init(bot)

    if worker_bot_config.orders_channel_id:
        OrderChannelService.init(bot, worker_bot_config.orders_channel_id)
        logger.info("Order channel enabled: %s", worker_bot_config.orders_channel_id)

    dp = Dispatcher()


    @dp.errors()

    async def _global_error_handler(event, **kwargs):

        import logging as _l

        _l.getLogger(__name__).exception("Unhandled bot error: %s", event.exception)

        return True

    dp.update.middleware(DatabaseMiddleware(async_session_maker))
    dp.message.middleware(WorkerAuthMiddleware())
    dp.callback_query.middleware(WorkerAuthMiddleware())

    dp.include_router(worker_dashboard.router)
    dp.include_router(start.router)
    dp.include_router(work_orders.router)
    dp.include_router(user_info.router)
    dp.include_router(history.router)
    dp.include_router(complaints.router)
    dp.include_router(orders.router)
    dp.include_router(bulk_orders.router)
    dp.include_router(statistics.router)
    dp.include_router(profile.router)
    dp.include_router(files.router)
    dp.include_router(upload_product.router)
    dp.include_router(worker_withdrawal.router)

    logger.info("Worker Bot starting...")

    loop = asyncio.get_event_loop()
    stop_event = asyncio.Event()

    def _sigterm_handler(*_):
        logger.info("SIGTERM received, shutting down Worker Bot...")
        stop_event.set()

    loop.add_signal_handler(signal.SIGTERM, _sigterm_handler)

    try:
        try:
            await bot.delete_webhook(drop_pending_updates=True)
        except Exception as _dw_exc:
            import logging; logging.getLogger(__name__).warning("delete_webhook failed (ignored): %s", _dw_exc)

        api_task = asyncio.create_task(start_api_server())
        bot_task = asyncio.create_task(dp.start_polling(bot))
        reminder_task = asyncio.create_task(
            run_worker_order_reminder_watcher(stop_event, async_session_maker, bot)
        )

        # Wait for any task to finish or for SIGTERM stop_event
        stop_waiter = asyncio.create_task(stop_event.wait())
        done, pending = await asyncio.wait(
            [api_task, bot_task, reminder_task, stop_waiter],
            return_when=asyncio.FIRST_COMPLETED,
        )

        stop_event.set()
        for task in pending:
            task.cancel()

        for task in done:
            if task is not stop_waiter:
                exc = task.exception()
                if exc:
                    raise exc

    finally:
        await bot.session.close()
        logger.info("Worker Bot stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Worker Bot stopped by user")
