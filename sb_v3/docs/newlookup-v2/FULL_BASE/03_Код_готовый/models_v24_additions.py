"""
Newlookup v24 — Дополнения к моделям
Файл: shared/database/models_v24_additions.py

ИНСТРУКЦИЯ: Этот файл содержит ТОЛЬКО новые модели и изменения.
Добавь их в конец shared/database/models.py

НОВЫЕ ТАБЛИЦЫ:
1. SystemSetting — динамические константы
2. WorkerViolation — нарушения воркеров
3. ProductModerationLog — история модерации
4. EscrowRelease — идемпотентность выплат
5. Coupon / CouponUsage — купоны (если не было)
6. SellerOrderDispute — споры по заказам

НОВЫЕ КОЛОНКИ (добавить в существующие модели):
- SellerOrder: escrow_released, marketer_commission_paid, worker_paid, auto_complete_at
- Product: moderation_status, moderation_comment, seller_id (если нет)
- User: language (если нет)
- Worker: violation_count, is_suspended
"""

from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, TYPE_CHECKING

from sqlalchemy import (
    BigInteger, Boolean, DateTime, ForeignKey, Integer,
    Numeric, String, Text, UniqueConstraint, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Импортируй Base из своего файла:
# from shared.database.models import Base
# Здесь используется заглушка для документации:
# Base = DeclarativeBase()


# ══════════════════════════════════════════════════════════════
# НОВАЯ ТАБЛИЦА 1: SystemSetting
# Хранит все динамические константы системы
# ══════════════════════════════════════════════════════════════
class SystemSetting:
    """
    Динамические константы системы.
    
    Добавь в shared/database/models.py:
    
    class SystemSetting(Base):
        __tablename__ = "system_settings"
        
        key: Mapped[str] = mapped_column(String(100), primary_key=True)
        value: Mapped[str] = mapped_column(Text, nullable=False)
        description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
        updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    НАЧАЛЬНЫЕ ЗНАЧЕНИЯ (вставь через migration или init_db.sql):
    
    INSERT INTO system_settings (key, value, description) VALUES
    ('PLATFORM_FEE_BASE', '0.15', 'Базовая комиссия платформы (15%)'),
    ('MARKETER_COMMISSION_RATE', '0.10', 'Комиссия маркетолога (10%)'),
    ('ESCROW_HOLD_HOURS', '48', 'Часов удержания эскроу'),
    ('DISPUTE_WINDOW_HOURS', '24', 'Часов на открытие спора'),
    ('AUTO_COMPLETE_HOURS', '24', 'Часов до автозавершения'),
    ('WORKER_VIOLATION_LIMIT', '3', 'Нарушений до отстранения'),
    ('WORKER_VIOLATION_WINDOW_DAYS', '30', 'Дней для подсчёта нарушений'),
    ('MIN_WITHDRAWAL_AMOUNT', '10.00', 'Минимальная сумма вывода'),
    ('MAX_WITHDRAWAL_AMOUNT', '5000.00', 'Максимальная сумма вывода')
    ON CONFLICT (key) DO NOTHING;
    """
    pass


# ══════════════════════════════════════════════════════════════
# НОВАЯ ТАБЛИЦА 2: WorkerViolation
# Фиксирует нарушения воркеров (попытки передать контакты)
# ══════════════════════════════════════════════════════════════
class WorkerViolation:
    """
    Добавь в shared/database/models.py:
    
    class WorkerViolation(Base):
        __tablename__ = "worker_violations"
        
        id: Mapped[int] = mapped_column(Integer, primary_key=True)
        worker_id: Mapped[int] = mapped_column(ForeignKey("workers.id"), nullable=False, index=True)
        order_id: Mapped[Optional[int]] = mapped_column(ForeignKey("orders.id"), nullable=True)
        violation_type: Mapped[str] = mapped_column(String(50), nullable=False)
        # contact_leak | spam | inappropriate | other
        original_text: Mapped[str] = mapped_column(Text, nullable=False)
        filtered_text: Mapped[str] = mapped_column(Text, nullable=False)
        created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
        
        worker: Mapped["Worker"] = relationship("Worker")
    
    Также добавь в Worker модель:
        violation_count: Mapped[int] = mapped_column(Integer, default=0)
        is_suspended: Mapped[bool] = mapped_column(Boolean, default=False)
        suspended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
        suspended_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    """
    pass


# ══════════════════════════════════════════════════════════════
# НОВЫЕ КОЛОНКИ для SellerOrder
# Добавь в класс SellerOrder в shared/database/models.py
# ══════════════════════════════════════════════════════════════
SELLER_ORDER_NEW_COLUMNS = """
# Добавь эти колонки в класс SellerOrder:

    # ── Идемпотентность финансовых операций ──────────────────
    escrow_released: Mapped[bool] = mapped_column(Boolean, default=False)
    # True = эскроу уже выплачен продавцу. Защита от двойной выплаты.
    
    marketer_commission_paid: Mapped[bool] = mapped_column(Boolean, default=False)
    # True = комиссия маркетолога уже выплачена. Защита от двойной выплаты.
    
    worker_paid: Mapped[bool] = mapped_column(Boolean, default=False)
    # True = воркер уже получил оплату. Защита от двойной выплаты.
    
    # ── Таймеры ──────────────────────────────────────────────
    auto_complete_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    # Когда заказ автоматически завершится (если покупатель не подтвердил)
    
    dispute_deadline_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    # До какого времени покупатель может открыть спор
    
    # ── Маркетолог ───────────────────────────────────────────
    marketer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("marketers.id"), nullable=True)
    # ID маркетолога, привлёкшего покупателя (для выплаты комиссии)
    
    marketer_commission_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    # Сумма комиссии маркетолога (рассчитывается при создании заказа)
"""


# ══════════════════════════════════════════════════════════════
# НОВЫЕ КОЛОНКИ для Product
# Добавь в класс Product в shared/database/models.py
# ══════════════════════════════════════════════════════════════
PRODUCT_NEW_COLUMNS = """
# Добавь эти колонки в класс Product (если их нет):

    seller_id: Mapped[Optional[int]] = mapped_column(ForeignKey("sellers.id"), nullable=True)
    # ID продавца-владельца товара
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Активен ли товар (мягкое удаление)
    
    moderation_status: Mapped[str] = mapped_column(String(30), default="pending_moderation")
    # pending_moderation | approved | rejected | changes_requested
    
    moderation_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Комментарий модератора при отклонении
    
    moderated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    moderated_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
"""


# ══════════════════════════════════════════════════════════════
# НОВЫЕ КОЛОНКИ для User
# Добавь в класс User в shared/database/models.py
# ══════════════════════════════════════════════════════════════
USER_NEW_COLUMNS = """
# Добавь эти колонки в класс User (если их нет):

    language: Mapped[str] = mapped_column(String(10), default='ru')
    # Язык интерфейса: ru | en
    
    trust_score: Mapped[int] = mapped_column(Integer, default=100)
    # Рейтинг доверия (0-100), снижается при нарушениях
    
    last_active_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    # Последняя активность
"""


# ══════════════════════════════════════════════════════════════
# НОВАЯ ТАБЛИЦА 3: SellerOrderDispute
# Споры по заказам
# ══════════════════════════════════════════════════════════════
SELLER_ORDER_DISPUTE_MODEL = """
# Добавь в shared/database/models.py:

class SellerOrderDispute(Base):
    __tablename__ = "seller_order_disputes"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("seller_orders.id"), nullable=False, unique=True)
    opened_by: Mapped[int] = mapped_column(BigInteger, nullable=False)  # telegram_id покупателя
    
    reason: Mapped[str] = mapped_column(String(50), nullable=False)
    # not_received | wrong_item | quality_issue | other
    
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    status: Mapped[str] = mapped_column(String(20), default="open")
    # open | resolved_buyer | resolved_seller | cancelled
    
    resolution_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolved_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)  # admin telegram_id
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    order: Mapped["SellerOrder"] = relationship("SellerOrder")
"""
