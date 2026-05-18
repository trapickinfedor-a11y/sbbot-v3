"""
Конфигурация Support Bot
"""

from dataclasses import dataclass, field
import os
from dotenv import load_dotenv
from shared.config.env_utils import parse_int_env, parse_int_list_env

load_dotenv()


@dataclass
class SupportBotConfig:
    """Конфигурация Support Bot"""
    
    # Telegram Bot Token
    bot_token: str = os.getenv("SUPPORT_BOT_TOKEN", "")
    
    # Database URL (используем общую базу)
    database_url: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://newlookup:tgbotnewlookup@postgres:5432/newlookup")
    
    # Основные админы системы (из .env)
    system_admin_ids: list = field(default_factory=lambda: parse_int_list_env("ADMIN_IDS"))
    
    # Уведомления
    enable_notifications: bool = True
    
    # Канал для отклика всех заказов
    orders_channel_id: int = parse_int_env("ORDERS_CHANNEL_ID", 0)
    
    # Чат для логирования действий саппортов
    support_log_chat_id: int = parse_int_env("SUPPORT_LOG_CHAT_ID", 0)
    
    # Статусы заказов
    ORDER_STATUS_PENDING = "pending"
    ORDER_STATUS_PROCESSING = "processing"
    ORDER_STATUS_COMPLETED = "completed"
    ORDER_STATUS_CANCELLED = "cancelled"
    
    # Статусы элементов bulk
    ITEM_STATUS_PENDING = "pending"
    ITEM_STATUS_DONE = "done"
    ITEM_STATUS_NF = "nf"
    
    # Категории
    CATEGORIES = {
        "lookup_ssn": "SSN Lookup",
        "lookup_dl": "DL Lookup",
        "lookup_mvr": "MVR",
        "lookup_fullmvr": "Full MVR",
        "lookup_credit": "Credit Score",
        "lookup_bg": "Background Check",
        "lookup_mmn": "MMN",
        "lookup_ein": "EIN",
        "phone_name": "Phone Name",
        "phone_ssn": "Phone SSN",
        "phone_full": "Phone Full",
        "cr_transunion": "TransUnion CR",
        "cr_experian": "Experian CR",
        "cr_equifax": "Equifax CR",
        "cr_lexisnexis": "LexisNexis CR",
        "cr_wallet": "WalletHub CR",
        "fullz": "FULLZ",
        "fullz_biz": "BIZ FULLZ",
        "banks": "Banks",
        "accounts_addinfo": "Add Info",
        "esim": "eSIM",
        # Новые категории (для совместимости)
        "🔎 Search": "Search Services",
        "📈 CREDIT REPORTS": "Credit Reports", 
        "📄 DOCUMENTS": "Documents",
        "🧰 PROS & FULLZ": "FULLZ Services",
        "🏦 BANKS": "Banks",
        "🧾 Subscriptions / Accounts": "Accounts",
        "✍️ Add info in CR": "Add Info",
        "📶 eSIM": "eSIM Services",
    }


support_bot_config = SupportBotConfig()

