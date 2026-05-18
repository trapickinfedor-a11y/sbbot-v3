"""
Отдельная БД для задач (заявки на вывод и т.д.)
"""

import os
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from dotenv import load_dotenv

from shared.database.task_models import TaskBase

load_dotenv()

def _resolve_tasks_database_url() -> str:
    configured = os.getenv("TASKS_DATABASE_URL")
    if configured:
        if configured.startswith("sqlite"):
            raw_path = configured.split("///", 1)[-1]
            db_path = Path(raw_path)
            if not db_path.is_absolute():
                db_path = (Path(__file__).resolve().parent.parent.parent / db_path).resolve()
            db_path.parent.mkdir(parents=True, exist_ok=True)
            return f"sqlite+aiosqlite:///{db_path}"
        return configured

    default_path = (Path(__file__).resolve().parent.parent.parent / "data" / "tasks.db").resolve()
    default_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite+aiosqlite:///{default_path}"


TASKS_DB_PATH = _resolve_tasks_database_url()

tasks_engine = create_async_engine(
    TASKS_DB_PATH,
    echo=False,
)

tasks_session_maker = async_sessionmaker(
    tasks_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def init_tasks_db():
    """Создать таблицы в БД задач"""
    async with tasks_engine.begin() as conn:
        await conn.run_sync(TaskBase.metadata.create_all)


async def get_tasks_session() -> AsyncSession:
    async with tasks_session_maker() as session:
        yield session
