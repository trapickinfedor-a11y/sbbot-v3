from dataclasses import dataclass
import os
from dotenv import load_dotenv
from shared.config.env_utils import parse_int_list_env

load_dotenv()


@dataclass
class SellerBotConfig:
    bot_token: str = os.getenv("SELLER_BOT_TOKEN", "")
    admin_ids: list = None
    default_markup_percent: float = 20.0
    
    def __post_init__(self):
        self.admin_ids = parse_int_list_env("ADMIN_IDS")


seller_bot_config = SellerBotConfig()
