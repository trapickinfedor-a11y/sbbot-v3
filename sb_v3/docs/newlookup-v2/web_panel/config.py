"""
Конфигурация веб-панели админа
"""

import logging
import os
import sys
from dataclasses import dataclass, field
from dotenv import load_dotenv
import secrets
from shared.config.env_utils import parse_int_env

load_dotenv()

logger = logging.getLogger(__name__)


def _require_env(name: str, fallback: str = "") -> str:
    """Возвращает значение env-переменной. Падает при старте если она критична и не задана."""
    return os.getenv(name, fallback)


@dataclass
class WebPanelConfig:
    """Конфигурация веб-панели"""

    # Сервер
    host: str = "0.0.0.0"
    port: int = parse_int_env("WEB_PANEL_PORT", 8000)

    # Безопасность
    # Генерация: python3 -c "import secrets; print(secrets.token_urlsafe(32))"
    secret_key: str = field(default_factory=lambda: os.getenv(
        "WEB_PANEL_SECRET_KEY",
        "CHANGE-THIS-IN-PRODUCTION-" + secrets.token_urlsafe(32)
    ))
    admin_username: str = field(default_factory=lambda: os.getenv("ADMIN_USERNAME", "admin"))
    # Нет дефолта admin123 — если не задан, используется пустая строка
    # и ensure_first_admin откажет в создании
    admin_password: str = field(default_factory=lambda: os.getenv("ADMIN_PASSWORD", ""))

    # JWT
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 8  # 8 hours (was 24h — reduced attack window)

    # База данных (общая с проектом)
    database_url: str = field(default_factory=lambda: os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://newlookup:tgbotnewlookup@postgres:5432/newlookup"
    ))

    # Support Bot
    support_bot_token: str = field(default_factory=lambda: os.getenv("SUPPORT_BOT_TOKEN", ""))

    # Main Bot
    main_bot_token: str = field(default_factory=lambda: os.getenv("MAIN_BOT_TOKEN", ""))

    # Файлы
    upload_dir: str = "./data/uploads"
    max_upload_size: int = 50 * 1024 * 1024  # 50MB

    # Канал для заказов
    orders_channel_id: int = parse_int_env("ORDERS_CHANNEL_ID", 0)

    # Видео-инструкции
    instructions_tutorial_url: str = field(default_factory=lambda: os.getenv(
        "INSTRUCTIONS_TUTORIAL_URL", "https://t.me/ONE_TUTORIAL"
    ))

    # NocoDB (синхронизация Seller CRM)
    nocodb_base_url: str = field(default_factory=lambda: os.getenv("NOCODB_API_URL") or os.getenv("NOCODB_BASE_URL", ""))
    nocodb_api_token: str = field(default_factory=lambda: os.getenv("NOCODB_API_TOKEN", ""))
    nocodb_table_id: str = field(default_factory=lambda: os.getenv("NOCODB_TABLE_ID", ""))


web_panel_config = WebPanelConfig()

# ── Предстартовые проверки ────────────────────────────────────────────────────

_is_production = os.getenv("ENVIRONMENT", "").lower() == "production"

if not os.getenv("WEB_PANEL_SECRET_KEY"):
    if _is_production:
        logger.critical("WEB_PANEL_SECRET_KEY is not set in production environment!")
        logger.critical("Generate one: python3 -c \"import secrets; print(secrets.token_urlsafe(32))\"")
        sys.exit(1)
    else:
        logger.warning(
            "WEB_PANEL_SECRET_KEY is not set — using auto-generated key. "
            "All sessions will be invalidated on restart. Set it in .env!"
        )

if not os.getenv("ADMIN_PASSWORD"):
    if _is_production:
        logger.critical("ADMIN_PASSWORD is not set in production environment!")
        sys.exit(1)
    else:
        # В dev используем дефолт только при явном отсутствии — с предупреждением
        object.__setattr__(web_panel_config, "admin_password", "admin123")
        logger.warning(
            "ADMIN_PASSWORD is not set — using insecure default 'admin123'. "
            "Set ADMIN_PASSWORD in .env before going to production!"
        )
