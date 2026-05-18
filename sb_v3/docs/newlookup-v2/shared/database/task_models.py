"""
Модели для отдельной БД задач.

Финансовые withdrawal task-модели выведены из runtime и больше не являются
источником данных для payouts; в tasks DB остаются только нефинансовые задачи.
"""

from sqlalchemy import BigInteger, String, Integer, DateTime, Text, JSON, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import datetime
from typing import Optional


class TaskBase(DeclarativeBase):
    pass


class WorkerReminderTask(TaskBase):
    """Durable reminder tasks for worker orders."""
    __tablename__ = "worker_reminder_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    worker_order_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    worker_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    worker_telegram_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, index=True)
    reminder_type: Mapped[str] = mapped_column(String(30), default="in_progress")
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, sent, cancelled, failed
    scheduled_for: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    payload_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
