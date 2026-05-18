import asyncio
try:
    import uvloop; asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())
except ImportError:
    pass
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from marketer_bot.config import marketer_bot_config
from marketer_bot.handlers import start, logs, help as help_handler, my_bots, analytics, withdrawal, referral
from marketer_bot.middlewares.database import DatabaseMiddleware
from marketer_bot.middlewares.language import MarketerLanguageMiddleware
from marketer_bot.services.daily_report import run_daily_report_loop
from shared.config.env_utils import StartupValidationError, validate_startup_env
from shared.database.session import async_session_maker
from shared.middlewares.error_logging import GlobalErrorLoggingMiddleware

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


def _validate_marketer_bot_startup() -> None:
    warnings = validate_startup_env(
        "marketer_bot",
        require_one_of=[("MARKETER_BOT_TOKEN",)],
        required=["DATABASE_URL"],
        optional=["ADMIN_IDS"],
    )
    for warning in warnings:
        logger.warning(warning)


async def main():
    try:
        _validate_marketer_bot_startup()
    except StartupValidationError as exc:
        logger.error(str(exc))
        sys.exit(1)

    bot = Bot(
        token=marketer_bot_config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher()

    @dp.errors()
    async def _global_error_handler(event, **kwargs):
        import logging as _l
        _l.getLogger(__name__).exception("Unhandled bot error: %s", event.exception)
        return True

    dp.update.middleware(DatabaseMiddleware(async_session_maker))
    dp.update.middleware(GlobalErrorLoggingMiddleware("marketer_bot"))
    dp.update.middleware(MarketerLanguageMiddleware())

    dp.include_router(my_bots.router)
    dp.include_router(analytics.router)
    dp.include_router(withdrawal.router)
    dp.include_router(referral.router)
    dp.include_router(start.router)
    dp.include_router(logs.router)
    dp.include_router(help_handler.router)

    logger.info("Marketer Bot starting...")

    report_task = asyncio.create_task(run_daily_report_loop(bot))

    try:
        try:
            await bot.delete_webhook(drop_pending_updates=True)
        except Exception as _dw_exc:
            logger.warning("delete_webhook failed (ignored): %s", _dw_exc)
        await dp.start_polling(bot)
    finally:
        report_task.cancel()
        await bot.session.close()
        logger.info("Marketer Bot stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Marketer Bot stopped by user")
