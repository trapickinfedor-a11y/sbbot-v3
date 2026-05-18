"""
Конфигурация Worker Bot
"""

from dataclasses import dataclass, field
import os
from dotenv import load_dotenv
from shared.config.env_utils import parse_int_env, parse_int_list_env

load_dotenv()


@dataclass
class WorkerBotConfig:
    """Конфигурация Worker Bot"""

    bot_token: str = os.getenv("WORKER_BOT_TOKEN", "")
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://newlookup:tgbotnewlookup@postgres:5432/newlookup",
    )
    system_admin_ids: list = field(default_factory=lambda: parse_int_list_env("ADMIN_IDS"))
    orders_channel_id: int = parse_int_env("ORDERS_CHANNEL_ID", 0)
    support_log_chat_id: int = parse_int_env("SUPPORT_LOG_CHAT_ID", 0)


worker_bot_config = WorkerBotConfig()
