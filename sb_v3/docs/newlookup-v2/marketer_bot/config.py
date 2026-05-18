from dataclasses import dataclass
import os
from dotenv import load_dotenv
from shared.config.env_utils import parse_int_list_env

load_dotenv()


@dataclass
class MarketerBotConfig:
    bot_token: str = os.getenv("MARKETER_BOT_TOKEN", "")
    database_url: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://newlookup:tgbotnewlookup@postgres:5432/newlookup")
    admin_ids: list = None

    def __post_init__(self):
        self.admin_ids = parse_int_list_env("ADMIN_IDS")


marketer_bot_config = MarketerBotConfig()
