"""
Модуль для загрузки и валидации конфигурации из .env файла.
Использует pydantic-settings для удобной работы с переменными окружения.
"""

import logging
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    # --- Telegram Bot ---
    BOT_TOKEN: str

    # --- 9proxy Credentials ---
    PROXY_HOST: str
    PROXY_PORT: int
    PROXY_USERNAME: str
    PROXY_PASSWORD: str

    # --- Worker Pool Settings ---
    WORKER_COUNT: int = 5
    WORKER_ROTATE_ON_SUCCESS: int = 3
    WORKER_HEADLESS: bool = True
    WORKER_SCREENSHOT_DIR: str = "./data/screenshots"

    # --- Logging ---
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding='utf-8')

try:
    settings = Settings()
except Exception as e:
    logger.error(f"FATAL: Could not load settings from .env file. Error: {e}")
    logger.error("Please make sure a .env file exists and contains all required variables.")
    exit(1)
