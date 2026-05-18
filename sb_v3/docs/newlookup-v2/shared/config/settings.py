from dataclasses import dataclass
import os
from dotenv import load_dotenv

load_dotenv()


@dataclass
class GlobalSettings:
    database_url: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/newlookup.db")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    celery_broker_url: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
    celery_result_backend: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")
    celery_timezone: str = os.getenv("CELERY_TIMEZONE", "UTC")
    celery_auto_complete_interval_minutes: int = int(os.getenv("CELERY_AUTO_COMPLETE_INTERVAL_MINUTES", "5"))
    celery_violation_check_interval_minutes: int = int(os.getenv("CELERY_VIOLATION_CHECK_INTERVAL_MINUTES", "60"))
    referral_percent: float = 4.0
    nocodb_api_url: str = os.getenv("NOCODB_API_URL") or os.getenv("NOCODB_BASE_URL", "")
    nocodb_api_token: str = os.getenv("NOCODB_API_TOKEN", "")
    nocodb_order_messages_table_id: str = os.getenv("NOCODB_ORDER_MESSAGES_TABLE_ID", "")
    nocodb_moderator_actions_table_id: str = os.getenv("NOCODB_MODERATOR_ACTIONS_TABLE_ID", "")
    nocodb_seller_buyer_chat_table_id: str = os.getenv("NOCODB_SELLER_BUYER_CHAT_TABLE_ID", "")
    nocodb_support_tickets_table_id: str = os.getenv("NOCODB_SUPPORT_TICKETS_TABLE_ID", "")
    nocodb_financial_operations_table_id: str = os.getenv("NOCODB_FINANCIAL_OPERATIONS_TABLE_ID", "")
    nocodb_file_operations_table_id: str = os.getenv("NOCODB_FILE_OPERATIONS_TABLE_ID", "")
    nocodb_errors_table_id: str = os.getenv("NOCODB_ERRORS_TABLE_ID", "")
    nocodb_seller_uploads_table_id: str = os.getenv("NOCODB_SELLER_UPLOADS_TABLE_ID", "")
    nocodb_event_log_table_id: str = os.getenv("NOCODB_EVENT_LOG_TABLE_ID", "")
    
    @property
    def is_sqlite(self) -> bool:
        return "sqlite" in self.database_url

    @property
    def nocodb_enabled(self) -> bool:
        return bool(self.nocodb_api_url and self.nocodb_api_token)


global_settings = GlobalSettings()
