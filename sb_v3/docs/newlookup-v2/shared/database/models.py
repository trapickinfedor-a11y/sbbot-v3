from __future__ import annotations

from sqlalchemy import BigInteger, String, Integer, DateTime, Boolean, Text, JSON, ForeignKey, Date, Numeric, Float, UniqueConstraint, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from datetime import datetime
from typing import Optional, List
from decimal import Decimal

class Base(DeclarativeBase):
    pass


LEDGER_CURRENCY_USD = "USD"

LEDGER_ACCOUNT_USER = "user"
LEDGER_ACCOUNT_SELLER = "seller"
LEDGER_ACCOUNT_WORKER = "worker"
LEDGER_ACCOUNT_MARKETER = "marketer"
LEDGER_ACCOUNT_OWNER = "owner"

TRANSACTION_TYPE_DEPOSIT = "deposit"
TRANSACTION_TYPE_PURCHASE = "purchase"
TRANSACTION_TYPE_WITHDRAWAL = "withdrawal"
TRANSACTION_TYPE_COMMISSION = "commission"
TRANSACTION_TYPE_REFUND = "refund"
TRANSACTION_TYPE_PAYOUT_WORKER = "payout_worker"

TRANSACTION_STATUS_PENDING = "pending"
TRANSACTION_STATUS_COMPLETED = "completed"
TRANSACTION_STATUS_FAILED = "failed"
TRANSACTION_STATUS_ON_HOLD = "on_hold"
TRANSACTION_STATUS_DISPUTED = "disputed"


class MirrorBot(Base):
    __tablename__ = "mirror_bots"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bot_token: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    bot_username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    owner_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    bot_type: Mapped[str] = mapped_column(String(20), default="user")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    users: Mapped[List["User"]] = relationship("User", back_populates="mirror_bot")
    orders: Mapped[List["Order"]] = relationship("Order", back_populates="mirror_bot")
    owner_stats: Mapped[List["BotOwnerStats"]] = relationship("BotOwnerStats", back_populates="mirror_bot", cascade="all, delete-orphan")


class BotOwnerStats(Base):
    """Ежедневная статистика владельца бота: потрачено, пополнено, доход"""
    __tablename__ = "bot_owner_stats"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mirror_bot_id: Mapped[int] = mapped_column(ForeignKey("mirror_bots.id"), nullable=False)
    date: Mapped[datetime] = mapped_column(Date, nullable=False)
    
    spent: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0.00)  # Сумма заказов
    topped_up: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0.00)  # Пополнения юзеров
    owner_income: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0.00)  # 7% с пополнений
    
    mirror_bot: Mapped["MirrorBot"] = relationship("MirrorBot", back_populates="owner_stats")


class BotOwner(Base):
    """Баланс владельца ботов (может иметь несколько ботов)"""
    __tablename__ = "bot_owners"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    
    balance: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0.00)
    total_earned: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0.00)
    total_withdrawn: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0.00)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class BotOwnerWithdrawal(Base):
    """Заявки на вывод владельцев ботов"""
    __tablename__ = "bot_owner_withdrawals"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    payment_method: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    payment_network: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    requisites: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tx_hash: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    funds_reserved: Mapped[bool] = mapped_column(Boolean, default=False)
    reject_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    processed_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)


class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    mirror_bot_id: Mapped[int] = mapped_column(ForeignKey("mirror_bots.id"), nullable=False)
    language: Mapped[str] = mapped_column(String(10), default="ru")
    trust_score: Mapped[int] = mapped_column(Integer, default=100)
    last_active_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    archive_channel_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, index=True)
    # Notification preferences
    notif_order_updates: Mapped[bool] = mapped_column(Boolean, default=True)
    notif_promo: Mapped[bool] = mapped_column(Boolean, default=True)
    notif_price_drops: Mapped[bool] = mapped_column(Boolean, default=True)
    notif_dispute_updates: Mapped[bool] = mapped_column(Boolean, default=True)
    balance: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0.00)
    referrer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    marketer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("marketers.id"), nullable=True)  # пришёл по промокоду маркетолога
    first_topup_bonus_applied: Mapped[bool] = mapped_column(Boolean, default=False)  # 3% бонус на первое пополнение
    referral_link: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    ban_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rules_accepted: Mapped[bool] = mapped_column(Boolean, default=False)
    active_coupon_code: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    active_coupon_set_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    mirror_bot: Mapped["MirrorBot"] = relationship("MirrorBot", back_populates="users")
    orders: Mapped[List["Order"]] = relationship("Order", back_populates="user")
    transactions: Mapped[List["Transaction"]] = relationship("Transaction", back_populates="user")
    wishlist_items: Mapped[List["WishlistItem"]] = relationship("WishlistItem", back_populates="user", cascade="all, delete-orphan")
    shopping_cart: Mapped[Optional["ShoppingCart"]] = relationship("ShoppingCart", back_populates="user", uselist=False, cascade="all, delete-orphan")


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        Index("ix_orders_user_status", "user_id", "status"),
        Index("ix_orders_mirror_bot_status", "mirror_bot_id", "status"),
        Index("ix_orders_worker_status", "worker_id", "status"),
        Index("ix_orders_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), nullable=False)
    mirror_bot_id: Mapped[int] = mapped_column(ForeignKey("mirror_bots.id"), nullable=False)
    
    category: Mapped[str] = mapped_column(String(50), nullable=False)  # SSN, DL, MVR, FULLZ, etc.
    service_name: Mapped[str] = mapped_column(String(100), nullable=False)
    input_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    
    is_bulk: Mapped[bool] = mapped_column(Boolean, default=False)  # Single или Bulk заказ
    bulk_count: Mapped[int] = mapped_column(Integer, default=1)  # Количество элементов (1 для single)
    
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    original_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    coupon_code: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    discount_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, processing, completed, cancelled
    
    worker_id: Mapped[Optional[int]] = mapped_column(ForeignKey("workers.id"), nullable=True)
    result_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    files: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    feedback_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # liked, disliked
    feedback_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    report_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # reported
    reported_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Таймстампы
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    taken_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_worker_reminder_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Для "Add Info" заказов
    wait_time_hours: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 24, 48, etc.
    order_type: Mapped[str] = mapped_column(String(20), default="order", server_default="order", nullable=False)
    eta_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # ID сообщения уведомления для Support Bot (чтобы можно было отвечать)
    notification_message_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    support_chat_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)  # Chat ID саппорта
    review_requested: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)

    mirror_bot: Mapped["MirrorBot"] = relationship("MirrorBot", back_populates="orders")
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id], back_populates="orders")
    worker: Mapped[Optional["Worker"]] = relationship("Worker", back_populates="orders")
    bulk_items: Mapped[List["BulkOrderItem"]] = relationship("BulkOrderItem", back_populates="order", cascade="all, delete-orphan")


class BulkOrderItem(Base):
    __tablename__ = "bulk_order_items"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    item_number: Mapped[int] = mapped_column(Integer, nullable=False)  # 1, 2, 3, ... 20
    
    input_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, done, nf
    result_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    order: Mapped["Order"] = relationship("Order", back_populates="bulk_items")


class WorkerOrder(Base):
    """Compatibility mirror of worker-facing order state for v3 flows."""
    __tablename__ = "worker_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), unique=True, nullable=False)
    worker_id: Mapped[Optional[int]] = mapped_column(ForeignKey("workers.id"), nullable=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), nullable=False)
    category_slug: Mapped[str] = mapped_column(String(50), nullable=False)
    input_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="new")  # new, in_progress, completed, rejected, dispute
    hidden_input: Mapped[bool] = mapped_column(Boolean, default=True)
    last_reminder_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    result_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    files: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    taken_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    timer_paused_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    info_requested_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    info_request_text: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    intermediate_status: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)  # in_progress | searching | problem
    info_replied_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    order: Mapped["Order"] = relationship("Order")
    worker: Mapped[Optional["Worker"]] = relationship("Worker")
    customer: Mapped["User"] = relationship("User", foreign_keys=[customer_id])


class Worker(Base):
    __tablename__ = "workers"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    categories: Mapped[list] = mapped_column(JSON, nullable=False)
    services: Mapped[Optional[list]] = mapped_column(JSON, nullable=True, default=list)
    balance: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0.00)
    orders_completed: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    violation_count: Mapped[int] = mapped_column(Integer, default=0)
    is_suspended: Mapped[bool] = mapped_column(Boolean, default=False)
    suspended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    suspended_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    can_load_products: Mapped[bool] = mapped_column(Boolean, default=False)  # Доступ к загрузке товаров
    can_check_balance: Mapped[bool] = mapped_column(Boolean, default=False)
    upload_categories: Mapped[Optional[list]] = mapped_column(JSON, nullable=True, default=list)
    upload_services: Mapped[Optional[list]] = mapped_column(JSON, nullable=True, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Оплата: fixed_price > commission_percent > 100% от заказа
    fixed_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)  # Фикс. сумма за заказ (если задана)
    commission_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # % от Order.price (если задан)
    total_earned: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0.00)
    total_withdrawn: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0.00)
    
    worker_score: Mapped[float] = mapped_column(Float, default=5.0)
    avg_completion_minutes: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    success_rate: Mapped[float] = mapped_column(Float, default=1.0)
    score_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    orders: Mapped[List["Order"]] = relationship("Order", back_populates="worker")
    stats: Mapped[List["WorkerStats"]] = relationship("WorkerStats", back_populates="worker")
    withdrawals: Mapped[List["WorkerWithdrawal"]] = relationship("WorkerWithdrawal", back_populates="worker", cascade="all, delete-orphan")
    expense_reports: Mapped[List["WorkerExpenseReport"]] = relationship("WorkerExpenseReport", back_populates="worker", cascade="all, delete-orphan")


class WorkerStats(Base):
    __tablename__ = "worker_stats"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    worker_id: Mapped[int] = mapped_column(ForeignKey("workers.id"), nullable=False)
    date: Mapped[datetime] = mapped_column(Date, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Статистика
    orders_done: Mapped[int] = mapped_column(Integer, default=0)
    orders_nf: Mapped[int] = mapped_column(Integer, default=0)
    orders_cancelled: Mapped[int] = mapped_column(Integer, default=0)
    orders_total: Mapped[int] = mapped_column(Integer, default=0)
    
    # Будет использоваться для будущих расчетов админом
    earnings: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0.00)
    
    worker: Mapped["Worker"] = relationship("Worker", back_populates="stats")


class WorkerWithdrawal(Base):
    """Заявки на вывод средств воркеров (как у селлеров/маркетологов)"""
    __tablename__ = "worker_withdrawals"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    worker_id: Mapped[int] = mapped_column(ForeignKey("workers.id"), nullable=False)
    
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    requisites: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, approved, rejected
    funds_reserved: Mapped[bool] = mapped_column(Boolean, default=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    processed_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    reject_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    worker: Mapped["Worker"] = relationship("Worker", back_populates="withdrawals")


class WorkerExpenseReport(Base):
    """Отчёты воркеров о расходах (для CRM и учёта)"""
    __tablename__ = "worker_expense_reports"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    worker_id: Mapped[int] = mapped_column(ForeignKey("workers.id"), nullable=False)
    
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)  # proxy, cards, other
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    receipt_file_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)  # Telegram file_id
    
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, approved, rejected
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    processed_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    admin_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    worker: Mapped["Worker"] = relationship("Worker", back_populates="expense_reports")


class Transaction(Base):
    __tablename__ = "transactions"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.user_id"), nullable=True)
    account_type: Mapped[str] = mapped_column(String(20), nullable=False, default=LEDGER_ACCOUNT_USER)
    account_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default=LEDGER_CURRENCY_USD)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=TRANSACTION_STATUS_COMPLETED)
    related_entity_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    related_entity_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    effective_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(120), unique=True, nullable=True)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id], back_populates="transactions")


class Product(Base):
    __tablename__ = "products"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    seller_id: Mapped[Optional[int]] = mapped_column(ForeignKey("sellers.id"), nullable=True)
    uploaded_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # "worker:123" or "admin:456"
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False)  # docs, pros_fullz
    service: Mapped[str] = mapped_column(String(100), nullable=False)  # dl_front_back, work_travel, etc
    state: Mapped[str] = mapped_column(String(2), nullable=False)  # US state code
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    base_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    final_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    markup_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    markup_fixed: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_name: Mapped[str] = mapped_column(String(200), nullable=False)
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    moderation_status: Mapped[str] = mapped_column(String(30), default="pending_moderation")
    moderation_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    moderated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    moderated_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ProductCatalogService(Base):
    __tablename__ = "product_catalog_services"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category_key: Mapped[str] = mapped_column(String(50), nullable=False)  # docs, pros_fullz
    category_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)  # "📄 Documents"
    menu_group: Mapped[str] = mapped_column(String(50), nullable=False)  # documents_photo, documents_direct, fullz_personal
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MirrorMenuCategory(Base):
    __tablename__ = "mirror_menu_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    route_key: Mapped[str] = mapped_column(String(50), nullable=False)
    count_key: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    label_en: Mapped[str] = mapped_column(String(200), nullable=False)
    label_ru: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    label_zh: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    label_es: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    row_index: Mapped[int] = mapped_column(Integer, default=0)
    position: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ProductPurchase(Base):
    __tablename__ = "product_purchases"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), nullable=False)
    order_id: Mapped[Optional[int]] = mapped_column(ForeignKey("orders.id"), nullable=True)
    purchased_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    guarantee_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    file_deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    report_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    reported_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    product: Mapped["Product"] = relationship("Product")
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    order: Mapped[Optional["Order"]] = relationship("Order", foreign_keys=[order_id])


class ProductRating(Base):
    __tablename__ = "product_ratings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    purchase_id: Mapped[int] = mapped_column(ForeignKey("product_purchases.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), nullable=False)
    rating: Mapped[str] = mapped_column(String(20), nullable=False)  # like, dislike
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    purchase: Mapped["ProductPurchase"] = relationship("ProductPurchase")
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])


class ProductActionLog(Base):
    __tablename__ = "product_action_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[Optional[int]] = mapped_column(ForeignKey("products.id"), nullable=True)
    actor_type: Mapped[str] = mapped_column(String(20), nullable=False)  # admin, worker, user, system
    actor_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)  # create, update, delete, view, download, purchase, upload
    product_age_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    product: Mapped[Optional["Product"]] = relationship("Product")


class SupportTicket(Base):
    __tablename__ = "support_tickets"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), nullable=False)
    mirror_bot_id: Mapped[int] = mapped_column(ForeignKey("mirror_bots.id"), nullable=False)
    
    category: Mapped[str] = mapped_column(String(50), nullable=False)  # payment, product, general, partnership, financial, technical, suggestion
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="open")  # open, in_progress, waiting_user, pending, solved, closed
    priority: Mapped[str] = mapped_column(String(20), default="NORMAL")  # CRITICAL, HIGH, NORMAL, LOW
    assigned_to: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    # SLA fields
    first_response_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    escalated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    sla_breach: Mapped[bool] = mapped_column(Boolean, default=False)

    # CSAT
    csat_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 1=bad, 2=ok, 3=good
    csat_requested_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    mirror_bot: Mapped["MirrorBot"] = relationship("MirrorBot")
    messages: Mapped[List["SupportMessage"]] = relationship("SupportMessage", back_populates="ticket", cascade="all, delete-orphan", order_by="SupportMessage.created_at")


class SupportMessage(Base):
    __tablename__ = "support_messages"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("support_tickets.id"), nullable=False)
    
    sender_type: Mapped[str] = mapped_column(String(20), nullable=False)  # user, admin
    sender_id: Mapped[int] = mapped_column(BigInteger, nullable=False)  # Telegram ID отправителя
    
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    files: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)  # Массив file_id
    
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    ticket: Mapped["SupportTicket"] = relationship("SupportTicket", back_populates="messages")


class SupportTicketMessage(Base):
    """Расширенные сообщения тикета с поддержкой внутренних комментариев"""
    __tablename__ = "support_ticket_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("support_tickets.id"), nullable=False)
    sender_type: Mapped[str] = mapped_column(String(20), nullable=False)  # user, support, system
    sender_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_internal: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    ticket: Mapped["SupportTicket"] = relationship("SupportTicket")


class Complaint(Base):
    __tablename__ = "complaints"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    worker_id: Mapped[int] = mapped_column(ForeignKey("workers.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), nullable=False)
    order_id: Mapped[Optional[int]] = mapped_column(ForeignKey("orders.id"), nullable=True)
    
    reason: Mapped[str] = mapped_column(String(50), nullable=False)  # ban_request, invalid_data, abuse, other
    description: Mapped[str] = mapped_column(Text, nullable=False)
    
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, reviewed, resolved, rejected
    admin_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    worker: Mapped["Worker"] = relationship("Worker")
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    order: Mapped[Optional["Order"]] = relationship("Order")


class Broadcast(Base):
    __tablename__ = "broadcasts"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mirror_bot_id: Mapped[Optional[int]] = mapped_column(ForeignKey("mirror_bots.id"), nullable=True)  # Null = все боты
    bot_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # admin/marketer/user (filter bots by type)
    audience: Mapped[str] = mapped_column(String(30), default="users")  # users, workers, sellers, marketers, all
    
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    files: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    buttons: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)  # [{text, url}] inline keyboard buttons
    
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, scheduled, in_progress, completed, failed
    
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)  # Когда отправить (если задано)
    
    total_users: Mapped[int] = mapped_column(Integer, default=0)
    sent_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    
    created_by: Mapped[int] = mapped_column(BigInteger, nullable=False)  # Admin telegram ID
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    mirror_bot: Mapped[Optional["MirrorBot"]] = relationship("MirrorBot")
    translations: Mapped[List["BroadcastTranslation"]] = relationship(
        "BroadcastTranslation",
        back_populates="broadcast",
        cascade="all, delete-orphan",
    )


class BroadcastTranslation(Base):
    __tablename__ = "broadcast_translations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    broadcast_id: Mapped[int] = mapped_column(ForeignKey("broadcasts.id"), nullable=False)
    language: Mapped[str] = mapped_column(String(5), nullable=False)
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    broadcast: Mapped["Broadcast"] = relationship("Broadcast", back_populates="translations")


class UiTranslation(Base):
    __tablename__ = "ui_translations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    language: Mapped[str] = mapped_column(String(5), nullable=False, index=True)
    text_value: Mapped[str] = mapped_column(Text, nullable=False)
    namespace: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Report(Base):
    """
    Модель для обращений пользователей (жалобы, предложения о партнерстве и т.д.)
    Используется через Mirror Bot, управляется через Web Panel
    """
    __tablename__ = "reports"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), nullable=False)
    mirror_bot_id: Mapped[int] = mapped_column(ForeignKey("mirror_bots.id"), nullable=False)
    
    report_type: Mapped[str] = mapped_column(String(50), nullable=False)  # payment, product, partnership, complaint, other
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, answered, closed
    admin_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    files: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)  # Массив file_id если есть файлы
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    answered_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    mirror_bot: Mapped["MirrorBot"] = relationship("MirrorBot")


# ==================== SELLER SYSTEM ====================


class Seller(Base):
    __tablename__ = "sellers"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    language: Mapped[str] = mapped_column(String(2), default="en")
    rules_accepted: Mapped[bool] = mapped_column(Boolean, default=False)
    
    seller_type: Mapped[str] = mapped_column(String(20), default="external")  # internal / external
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    access_status: Mapped[str] = mapped_column(String(20), default="pending_deposit")  # pending_deposit, active, frozen, banned, left
    
    markup_percent: Mapped[float] = mapped_column(Float, default=20.0)
    
    total_orders: Mapped[int] = mapped_column(Integer, default=0)
    total_earned: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0.00)
    deposit_balance: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0.00)  # Deposit thresholds are enforced in seller flows
    security_deposit_balance: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0.00)
    security_deposit_status: Mapped[str] = mapped_column(String(20), default="unpaid")  # unpaid, held, refund_pending, refunded, withheld
    security_deposit_categories: Mapped[Optional[list]] = mapped_column(JSON, nullable=True, default=list)
    pending_balance: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0.00)
    withdrawable_balance: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0.00)
    likes_count: Mapped[int] = mapped_column(Integer, default=0)
    dislikes_count: Mapped[int] = mapped_column(Integer, default=0)
    seller_score: Mapped[float] = mapped_column(Float, default=5.0)
    score_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    security_deposit_paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    ban_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_banned_for_leak: Mapped[bool] = mapped_column(Boolean, default=False)
    is_on_vacation: Mapped[bool] = mapped_column(Boolean, default=False)
    vacation_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    auto_payout_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_payout_threshold: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("1000.00"))
    # Quiet hours (UTC): no promotional notifications during these hours
    quiet_hours_start: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # e.g. 22
    quiet_hours_end: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)    # e.g. 9
    vacation_ends_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    banned_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    banned_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    leave_requested_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    left_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    deposit_payments: Mapped[List["SellerDepositPayment"]] = relationship(
        "SellerDepositPayment",
        back_populates="seller",
        cascade="all, delete-orphan",
    )
    banks: Mapped[List["SellerBank"]] = relationship("SellerBank", back_populates="seller", cascade="all, delete-orphan")
    cc_items: Mapped[List["SellerCCItem"]] = relationship("SellerCCItem", back_populates="seller", cascade="all, delete-orphan")
    nfc_items: Mapped[List["SellerNFCItem"]] = relationship("SellerNFCItem", back_populates="seller", cascade="all, delete-orphan")
    otp_items: Mapped[List["SellerOTPItem"]] = relationship("SellerOTPItem", back_populates="seller", cascade="all, delete-orphan")
    enroll_items: Mapped[List["SellerEnrollItem"]] = relationship("SellerEnrollItem", back_populates="seller", cascade="all, delete-orphan")
    bank_items: Mapped[List["SellerBankItem"]] = relationship("SellerBankItem", back_populates="seller", cascade="all, delete-orphan")
    selfreg_cc_items: Mapped[List["SellerSelfregCCItem"]] = relationship("SellerSelfregCCItem", back_populates="seller", cascade="all, delete-orphan")
    check_items: Mapped[List["SellerCheckItem"]] = relationship("SellerCheckItem", back_populates="seller", cascade="all, delete-orphan")
    logs_items: Mapped[List["SellerLogsItem"]] = relationship("SellerLogsItem", back_populates="seller", cascade="all, delete-orphan")
    document_items: Mapped[List["SellerDocumentItem"]] = relationship("SellerDocumentItem", back_populates="seller", cascade="all, delete-orphan")
    fullz_items: Mapped[List["SellerFullzItem"]] = relationship("SellerFullzItem", back_populates="seller", cascade="all, delete-orphan")
    seller_orders: Mapped[List["SellerOrder"]] = relationship("SellerOrder", back_populates="seller")
    seller_cc_orders: Mapped[List["SellerCCOrder"]] = relationship("SellerCCOrder", back_populates="seller")
    seller_nfc_orders: Mapped[List["SellerNFCOrder"]] = relationship("SellerNFCOrder", back_populates="seller")
    seller_otp_orders: Mapped[List["SellerOTPOrder"]] = relationship("SellerOTPOrder", back_populates="seller")
    seller_enroll_orders: Mapped[List["SellerEnrollOrder"]] = relationship("SellerEnrollOrder", back_populates="seller")
    seller_bank_orders: Mapped[List["SellerBankOrder"]] = relationship("SellerBankOrder", back_populates="seller")
    seller_selfreg_cc_orders: Mapped[List["SellerSelfregCCOrder"]] = relationship("SellerSelfregCCOrder", back_populates="seller")
    seller_check_orders: Mapped[List["SellerCheckOrder"]] = relationship("SellerCheckOrder", back_populates="seller")
    seller_logs_orders: Mapped[List["SellerLogsOrder"]] = relationship("SellerLogsOrder", back_populates="seller")
    withdrawals: Mapped[List["SellerWithdrawal"]] = relationship("SellerWithdrawal", back_populates="seller", cascade="all, delete-orphan")
    conversations: Mapped[List["SellerConversation"]] = relationship("SellerConversation", back_populates="seller", cascade="all, delete-orphan")
    upload_batches: Mapped[List["SellerUploadBatch"]] = relationship("SellerUploadBatch", back_populates="seller", cascade="all, delete-orphan")
    upload_templates: Mapped[List["SellerUploadTemplate"]] = relationship("SellerUploadTemplate", back_populates="seller", cascade="all, delete-orphan")
    brute_bank_orders: Mapped[List["BruteBankOrder"]] = relationship("BruteBankOrder", back_populates="seller")
    helpers: Mapped[List["SellerHelper"]] = relationship(
        "SellerHelper",
        back_populates="seller",
        cascade="all, delete-orphan",
        foreign_keys="SellerHelper.seller_id",
    )
    helper_audit_logs: Mapped[List["SellerHelperAuditLog"]] = relationship("SellerHelperAuditLog", back_populates="seller", cascade="all, delete-orphan")


class SellerHelper(Base):
    __tablename__ = "seller_helpers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("sellers.id"), nullable=False)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    role: Mapped[str] = mapped_column(String(30), default="support_helper")  # upload_helper, support_helper, manager_helper
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, active, blocked, removed
    invited_by: Mapped[Optional[int]] = mapped_column(ForeignKey("sellers.id"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    joined_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    blocked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    seller: Mapped["Seller"] = relationship("Seller", foreign_keys=[seller_id], back_populates="helpers")


class SellerDepositPayment(Base):
    __tablename__ = "seller_deposit_payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("sellers.id"), nullable=False)
    package_code: Mapped[str] = mapped_column(String(30), nullable=False)
    categories: Mapped[Optional[list]] = mapped_column(JSON, nullable=True, default=list)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    provider: Mapped[str] = mapped_column(String(30), default="btcpay")
    provider_invoice_id: Mapped[Optional[str]] = mapped_column(String(120), unique=True, nullable=True)
    checkout_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, paid, expired, refunded, withheld, cancelled
    raw_payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    seller: Mapped["Seller"] = relationship("Seller", back_populates="deposit_payments")


class SellerHelperAuditLog(Base):
    __tablename__ = "seller_helper_audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("sellers.id"), nullable=False)
    helper_id: Mapped[Optional[int]] = mapped_column(ForeignKey("seller_helpers.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    object_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    object_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    payload_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    seller: Mapped["Seller"] = relationship("Seller", back_populates="helper_audit_logs")
    helper: Mapped[Optional["SellerHelper"]] = relationship("SellerHelper")


class SellerUploadBatch(Base):
    """Партия одиночной или массовой загрузки seller-товаров"""
    __tablename__ = "seller_upload_batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("sellers.id"), nullable=False)
    item_type: Mapped[str] = mapped_column(String(30), nullable=False)  # bank, cc, brute
    upload_mode: Mapped[str] = mapped_column(String(20), default="single")  # single, bulk
    title: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    total_items: Mapped[int] = mapped_column(Integer, default=1)
    moderation_status: Mapped[str] = mapped_column(String(30), default="pending")  # pending, approved, rejected, partial, changes_requested
    moderation_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    draft_payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    validation_summary: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    error_report: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    resubmitted_from_batch_id: Mapped[Optional[int]] = mapped_column(ForeignKey("seller_upload_batches.id"), nullable=True)
    approved_items: Mapped[int] = mapped_column(Integer, default=0)
    rejected_items: Mapped[int] = mapped_column(Integer, default=0)
    changes_requested_items: Mapped[int] = mapped_column(Integer, default=0)
    pending_items: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    seller: Mapped["Seller"] = relationship("Seller", back_populates="upload_batches")
    banks: Mapped[List["SellerBank"]] = relationship("SellerBank", back_populates="upload_batch")
    cc_items: Mapped[List["SellerCCItem"]] = relationship("SellerCCItem", back_populates="upload_batch")
    nfc_items: Mapped[List["SellerNFCItem"]] = relationship("SellerNFCItem", back_populates="upload_batch")
    otp_items: Mapped[List["SellerOTPItem"]] = relationship("SellerOTPItem", back_populates="upload_batch")
    selfreg_cc_items: Mapped[List["SellerSelfregCCItem"]] = relationship("SellerSelfregCCItem", back_populates="upload_batch")
    check_items: Mapped[List["SellerCheckItem"]] = relationship("SellerCheckItem", back_populates="upload_batch")
    brute_items: Mapped[List["BruteBankItem"]] = relationship("BruteBankItem", back_populates="upload_batch")
    document_items: Mapped[List["SellerDocumentItem"]] = relationship("SellerDocumentItem", back_populates="upload_batch")
    fullz_items: Mapped[List["SellerFullzItem"]] = relationship("SellerFullzItem", back_populates="upload_batch")
    source_batch: Mapped[Optional["SellerUploadBatch"]] = relationship("SellerUploadBatch", remote_side=[id])


class SellerUploadTemplate(Base):
    __tablename__ = "seller_upload_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("sellers.id"), nullable=False, index=True)
    item_type: Mapped[str] = mapped_column(String(30), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    seller: Mapped["Seller"] = relationship("Seller", back_populates="upload_templates")


class SellerBank(Base):
    __tablename__ = "seller_banks"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("sellers.id"), nullable=False)
    upload_batch_id: Mapped[Optional[int]] = mapped_column(ForeignKey("seller_upload_batches.id"), nullable=True)
    
    bank_name: Mapped[str] = mapped_column(String(200), nullable=False)
    bank_code: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)  # vcc, personal, business, crypto
    product_type: Mapped[str] = mapped_column(String(20), default="bank")  # bank, enrol
    product_subtype: Mapped[str] = mapped_column(String(30), default="log")  # log, selfreg, brute
    
    seller_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    base_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    final_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    buyer_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    markup_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    markup_fixed: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    markup_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    markup_kind: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # flat, percent
    markup_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    
    is_in_stock: Mapped[bool] = mapped_column(Boolean, default=True)
    stock_count: Mapped[int] = mapped_column(Integer, default=0)
    reserved_count: Mapped[int] = mapped_column(Integer, default=0)
    
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    instruction: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    zip: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    portal: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    card_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    has_ssn: Mapped[bool] = mapped_column(Boolean, default=False)
    has_dob: Mapped[bool] = mapped_column(Boolean, default=False)
    has_name: Mapped[bool] = mapped_column(Boolean, default=False)
    has_address: Mapped[bool] = mapped_column(Boolean, default=False)
    has_email: Mapped[bool] = mapped_column(Boolean, default=False)
    has_security_qa: Mapped[bool] = mapped_column(Boolean, default=False)
    has_docs: Mapped[bool] = mapped_column(Boolean, default=False)
    doc_type: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    phone_area_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    has_chat: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    number_access_available: Mapped[bool] = mapped_column(Boolean, default=False)
    rental_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    adaptive_report_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    number_change_allowed: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_unpublish_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    listing_duration_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    auto_unpublish_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    moderation_status: Mapped[str] = mapped_column(String(30), default="pending_moderation")  # pending_moderation, approved, rejected, changes_requested, suspended
    moderation_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    moderated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    moderated_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)  # admin telegram_id
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    seller: Mapped["Seller"] = relationship("Seller", back_populates="banks")
    upload_batch: Mapped[Optional["SellerUploadBatch"]] = relationship("SellerUploadBatch", back_populates="banks")
    seller_orders: Mapped[List["SellerOrder"]] = relationship("SellerOrder", back_populates="seller_bank")


class SellerOrder(Base):
    __tablename__ = "seller_orders"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[Optional[int]] = mapped_column(ForeignKey("orders.id"), nullable=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("sellers.id"), nullable=False)
    seller_bank_id: Mapped[int] = mapped_column(ForeignKey("seller_banks.id"), nullable=False)
    buyer_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mirror_bot_id: Mapped[Optional[int]] = mapped_column(ForeignKey("mirror_bots.id"), nullable=True)
    
    status: Mapped[str] = mapped_column(String(20), default="pending_admin")
    product_type: Mapped[str] = mapped_column(String(20), default="bank")
    product_subtype: Mapped[str] = mapped_column(String(30), default="log")
    
    price_for_buyer: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    price_for_seller: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    escrow_released: Mapped[bool] = mapped_column(Boolean, default=False)
    marketer_commission_paid: Mapped[bool] = mapped_column(Boolean, default=False)
    worker_paid: Mapped[bool] = mapped_column(Boolean, default=False)
    marketer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("marketers.id"), nullable=True)
    marketer_commission_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    reserved_quantity: Mapped[int] = mapped_column(Integer, default=1)
    
    admin_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    seller_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    result_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    files: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    check_window_minutes: Mapped[int] = mapped_column(Integer, default=15)
    check_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    check_confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    check_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    feedback_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # liked, disliked
    feedback_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    report_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # reported
    reported_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    buyer_rating: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # like, dislike
    buyer_rating_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    buyer_rating_reason: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    return_reason: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    return_reason_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    return_requested_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    assigned_helper_id: Mapped[Optional[int]] = mapped_column(ForeignKey("seller_helpers.id"), nullable=True)
    assigned_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    assigned_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    
    admin_message_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    seller_message_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    reserved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    reservation_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    reservation_released_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    admin_approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    taken_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    auto_complete_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    dispute_deadline_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    pending_credited_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    settled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    returned_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    disputed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    seller: Mapped["Seller"] = relationship("Seller", back_populates="seller_orders")
    seller_bank: Mapped["SellerBank"] = relationship("SellerBank", back_populates="seller_orders")
    order: Mapped[Optional["Order"]] = relationship("Order")
    mirror_bot: Mapped[Optional["MirrorBot"]] = relationship("MirrorBot")
    chat_messages: Mapped[List["SellerChat"]] = relationship("SellerChat", back_populates="seller_order", foreign_keys="SellerChat.seller_order_id", cascade="all, delete-orphan", order_by="SellerChat.created_at")


class SellerWithdrawal(Base):
    """Заявки на вывод средств продавцов"""
    __tablename__ = "seller_withdrawals"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("sellers.id"), nullable=False)
    
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    requisites: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # wallet, card, etc.
    
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, approved, rejected
    funds_reserved: Mapped[bool] = mapped_column(Boolean, default=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    processed_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)  # admin telegram_id
    reject_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    seller: Mapped["Seller"] = relationship("Seller", back_populates="withdrawals")


class SellerConversation(Base):
    """Один чат на каждого покупателя у селлера (не на заказ)"""
    __tablename__ = "seller_conversations"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("sellers.id"), nullable=False)
    buyer_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mirror_bot_id: Mapped[Optional[int]] = mapped_column(ForeignKey("mirror_bots.id"), nullable=True)
    source_order_type: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    source_order_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    assigned_helper_id: Mapped[Optional[int]] = mapped_column(ForeignKey("seller_helpers.id"), nullable=True)
    assigned_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    assigned_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    seller: Mapped["Seller"] = relationship("Seller", back_populates="conversations")
    mirror_bot: Mapped[Optional["MirrorBot"]] = relationship("MirrorBot")
    assigned_helper: Mapped[Optional["SellerHelper"]] = relationship("SellerHelper")
    messages: Mapped[List["SellerChat"]] = relationship(
        "SellerChat", back_populates="conversation",
        cascade="all, delete-orphan", order_by="SellerChat.created_at"
    )


class SellerChat(Base):
    __tablename__ = "seller_chats"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    seller_conversation_id: Mapped[Optional[int]] = mapped_column(ForeignKey("seller_conversations.id"), nullable=True)  # основной чат
    seller_order_id: Mapped[Optional[int]] = mapped_column(ForeignKey("seller_orders.id"), nullable=True)  # контекст заказа
    
    sender_type: Mapped[str] = mapped_column(String(20), nullable=False)  # buyer, seller, admin
    sender_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    
    message_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    files: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    conversation: Mapped["SellerConversation"] = relationship("SellerConversation", back_populates="messages")
    seller_order: Mapped[Optional["SellerOrder"]] = relationship("SellerOrder", back_populates="chat_messages")


class BankPosition(Base):
    """Порядок отображения банков в категориях (для админки) — legacy"""
    __tablename__ = "bank_positions"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bank_id: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class BankItem(Base):
    """Динамическое управление банками через админку"""
    __tablename__ = "bank_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bank_code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)  # vcc, personal, business, crypto
    section: Mapped[str] = mapped_column(String(20), default="order")  # order (на заказ) / stock (в наличии)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ServicePrice(Base):
    """Динамическое управление ценами всех сервисов"""
    __tablename__ = "service_prices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    bulk_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    order_type: Mapped[str] = mapped_column(String(20), default="order", server_default="order", nullable=False)
    eta_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    service_link: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PricingConfig(Base):
    """Глобальные ключевые настройки цен и таймеров для панели."""
    __tablename__ = "pricing_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    value_type: Mapped[str] = mapped_column(String(20), default="number")  # number, text, json, bool
    value_number: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    value_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    value_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Coupon(Base):
    """Купоны для специальных скидок в Mirror Bot."""
    __tablename__ = "coupons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(60), unique=True, nullable=False, index=True)
    title: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    discount_type: Mapped[str] = mapped_column(String(20), nullable=False, default="percent")  # percent, fixed
    discount_value: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    min_order_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    allowed_categories: Mapped[Optional[list]] = mapped_column(JSON, nullable=True, default=list)
    allowed_services: Mapped[Optional[list]] = mapped_column(JSON, nullable=True, default=list)
    max_total_uses: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_uses_per_user: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    starts_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    ends_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    redemptions: Mapped[List["CouponRedemption"]] = relationship(
        "CouponRedemption",
        back_populates="coupon",
        cascade="all, delete-orphan",
    )


class UserCoupon(Base):
    """Активированные пользователем купоны v24."""
    __tablename__ = "user_coupons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    coupon_id: Mapped[int] = mapped_column(ForeignKey("coupons.id"), nullable=False, index=True)
    activated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    is_used: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    order_id: Mapped[Optional[int]] = mapped_column(ForeignKey("orders.id"), nullable=True)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    __table_args__ = (UniqueConstraint("user_id", "coupon_id", name="uq_user_coupons_user_coupon"),)

    coupon: Mapped["Coupon"] = relationship("Coupon")
    user: Mapped["User"] = relationship("User")
    order: Mapped[Optional["Order"]] = relationship("Order")


class CouponRedemption(Base):
    """Фиксация применения купонов для лимитов и аналитики."""
    __tablename__ = "coupon_redemptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    coupon_id: Mapped[int] = mapped_column(ForeignKey("coupons.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), nullable=False)
    order_id: Mapped[Optional[int]] = mapped_column(ForeignKey("orders.id"), nullable=True)
    mirror_bot_id: Mapped[Optional[int]] = mapped_column(ForeignKey("mirror_bots.id"), nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    service_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    original_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    final_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    coupon: Mapped["Coupon"] = relationship("Coupon", back_populates="redemptions")
    order: Mapped[Optional["Order"]] = relationship("Order")
    mirror_bot: Mapped[Optional["MirrorBot"]] = relationship("MirrorBot")


class NotificationLog(Base):
    """Лог всех попыток отправки уведомлений — для раздела «Проверки»"""
    __tablename__ = "notification_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(30), nullable=False, index=True)

    recipient_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, index=True)
    related_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    related_type: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)

    status: Mapped[str] = mapped_column(String(20), default="sent", nullable=False, index=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class AdminRole(Base):
    """Кастомные роли администраторов с правами"""
    __tablename__ = "admin_roles"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    permissions: Mapped[dict] = mapped_column(JSON, nullable=False)  # {"users": True, "orders": True, ...}
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)  # встроенные роли не удаляются
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    admins: Mapped[List["Admin"]] = relationship("Admin", back_populates="role_obj")


class UploaderCatalogPermission(Base):
    """Scoped catalog permissions for uploader admins."""
    __tablename__ = "uploader_catalog_permissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    uploader_id: Mapped[int] = mapped_column(ForeignKey("admins.id"), nullable=False, index=True)
    catalog_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    uploader: Mapped["Admin"] = relationship("Admin", back_populates="uploader_catalog_permissions")


class Admin(Base):
    """Web panel admin with role-based access"""
    __tablename__ = "admins"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(30), nullable=False)  # super_admin, admin, moderator, support, viewer
    role_id: Mapped[Optional[int]] = mapped_column(ForeignKey("admin_roles.id"), nullable=True)  # кастомная роль
    allowed_catalogs: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
    telegram_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    role_obj: Mapped[Optional["AdminRole"]] = relationship("AdminRole", back_populates="admins")
    uploader_catalog_permissions: Mapped[List["UploaderCatalogPermission"]] = relationship(
        "UploaderCatalogPermission",
        back_populates="uploader",
        cascade="all, delete-orphan",
    )
    audit_logs: Mapped[List["AdminAuditLog"]] = relationship("AdminAuditLog", back_populates="admin")


class AdminAuditLog(Base):
    """Audit log for admin actions"""
    __tablename__ = "admin_audit_logs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    admin_id: Mapped[Optional[int]] = mapped_column(ForeignKey("admins.id"), nullable=True)  # null if admin from env
    action: Mapped[str] = mapped_column(String(50), nullable=False)  # login, user_ban, order_approve, etc.
    entity_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # user, order, seller
    entity_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    admin: Mapped[Optional["Admin"]] = relationship("Admin", back_populates="audit_logs")


class AuditLog(Base):
    """Universal append-only audit stream for cross-system events."""
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="system")
    event_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    actor_type: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    actor_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, index=True)
    target_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    target_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ok")
    payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


# ==================== MARKETERS ====================


class Marketer(Base):
    """Маркетологи (реферальные партнёры)"""
    __tablename__ = "marketers"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    language: Mapped[str] = mapped_column(String(5), default="ru")
    rules_accepted: Mapped[bool] = mapped_column(Boolean, default=False)
    
    promo_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    reward_percent: Mapped[float] = mapped_column(Float, default=7.0)
    user_bonus_percent: Mapped[float] = mapped_column(Float, default=0.0)
    
    balance: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0.00)
    total_earned: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0.00)
    total_withdrawn: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0.00)
    last_registration_milestone: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    stats: Mapped[List["MarketerStats"]] = relationship("MarketerStats", back_populates="marketer", cascade="all, delete-orphan")
    withdrawals: Mapped[List["MarketerWithdrawal"]] = relationship("MarketerWithdrawal", back_populates="marketer", cascade="all, delete-orphan")
    activity_logs: Mapped[List["MarketerActivityLog"]] = relationship("MarketerActivityLog", back_populates="marketer", cascade="all, delete-orphan")
    bot_links: Mapped[List["MarketerBotLink"]] = relationship("MarketerBotLink", back_populates="marketer", cascade="all, delete-orphan")
    own_bots: Mapped[List["MarketerOwnBot"]] = relationship("MarketerOwnBot", back_populates="marketer", cascade="all, delete-orphan")


class MarketerStats(Base):
    """Ежедневная статистика маркетологов"""
    __tablename__ = "marketer_stats"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    marketer_id: Mapped[int] = mapped_column(ForeignKey("marketers.id"), nullable=False)
    date: Mapped[datetime] = mapped_column(Date, nullable=False)
    
    registrations: Mapped[int] = mapped_column(Integer, default=0)
    first_topups: Mapped[int] = mapped_column(Integer, default=0)
    topup_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0.00)
    earned: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0.00)
    buyers_count: Mapped[int] = mapped_column(Integer, default=0)   # unique buyers today
    sales_count: Mapped[int] = mapped_column(Integer, default=0)    # purchases today
    
    marketer: Mapped["Marketer"] = relationship("Marketer", back_populates="stats")


class MarketerWithdrawal(Base):
    """Заявки на вывод средств маркетологов"""
    __tablename__ = "marketer_withdrawals"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    marketer_id: Mapped[int] = mapped_column(ForeignKey("marketers.id"), nullable=False)
    
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    requisites: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    status: Mapped[str] = mapped_column(String(20), default="pending")
    funds_reserved: Mapped[bool] = mapped_column(Boolean, default=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    processed_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    reject_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    marketer: Mapped["Marketer"] = relationship("Marketer", back_populates="withdrawals")


class MarketerActivityLog(Base):
    """Лог всех действий маркетологов: начисления, выводы, одобрения"""
    __tablename__ = "marketer_activity_logs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    marketer_id: Mapped[int] = mapped_column(ForeignKey("marketers.id"), nullable=False)
    
    action: Mapped[str] = mapped_column(String(50), nullable=False)  # earning, withdrawal_request, withdrawal_approved, withdrawal_rejected
    amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    withdrawal_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    mirror_bot_id: Mapped[Optional[int]] = mapped_column(ForeignKey("mirror_bots.id"), nullable=True)
    user_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    processed_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    marketer: Mapped["Marketer"] = relationship("Marketer", back_populates="activity_logs")


class MarketerBotLink(Base):
    """Связь маркетолога с ботами — для аналитики по ботам (подключение нескольких ботов)"""
    __tablename__ = "marketer_bot_links"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    marketer_id: Mapped[int] = mapped_column(ForeignKey("marketers.id"), nullable=False)
    mirror_bot_id: Mapped[int] = mapped_column(ForeignKey("mirror_bots.id"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_registration_milestone: Mapped[int] = mapped_column(Integer, default=0)
    
    marketer: Mapped["Marketer"] = relationship("Marketer", back_populates="bot_links")
    mirror_bot: Mapped["MirrorBot"] = relationship("MirrorBot")


class MarketerOwnBot(Base):
    """Бот-клон маркетолога — маркетолог регистрирует свой токен через BotFather"""
    __tablename__ = "marketer_own_bots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    marketer_id: Mapped[int] = mapped_column(ForeignKey("marketers.id"), nullable=False)

    bot_token: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    bot_username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    bot_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    welcome_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    total_users: Mapped[int] = mapped_column(Integer, default=0)
    total_orders: Mapped[int] = mapped_column(Integer, default=0)
    total_earned: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0.00)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_activity_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    marketer: Mapped["Marketer"] = relationship("Marketer", back_populates="own_bots")


# ==================== Wishlist & Cart ====================


class WishlistItem(Base):
    """Список желаний покупателя"""
    __tablename__ = "wishlist_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    product_type: Mapped[str] = mapped_column(String(50), nullable=False)  # bank, cc, fullz, etc.
    product_id: Mapped[int] = mapped_column(Integer, nullable=False)
    product_name: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    price_at_add: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    notified_price_drop: Mapped[bool] = mapped_column(Boolean, default=False)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship("User", back_populates="wishlist_items")


class ShoppingCart(Base):
    """Корзина покупателя"""
    __tablename__ = "shopping_carts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active")  # active, abandoned, checked_out
    abandoned_notified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user: Mapped["User"] = relationship("User", back_populates="shopping_cart")
    items: Mapped[List["CartItem"]] = relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")


class CartItem(Base):
    """Элемент корзины"""
    __tablename__ = "cart_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cart_id: Mapped[int] = mapped_column(ForeignKey("shopping_carts.id"), nullable=False)
    product_type: Mapped[str] = mapped_column(String(50), nullable=False)
    product_id: Mapped[int] = mapped_column(Integer, nullable=False)
    product_name: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    cart: Mapped["ShoppingCart"] = relationship("ShoppingCart", back_populates="items")


# ==================== Support Tickets SLA ====================


# ==================== CC (Credit Cards) ====================


class CCCategory(Base):
    """Категории CC (3-4 шт), управляются через админку"""
    __tablename__ = "cc_categories"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CCItem(Base):
    """Товары CC (на заказ), как BankItem"""
    __tablename__ = "cc_items"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cc_code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category_code: Mapped[str] = mapped_column(String(50), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SellerCCItem(Base):
    """CC товары от селлеров (в наличии), модерация как SellerBank"""
    __tablename__ = "seller_cc_items"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("sellers.id"), nullable=False)
    upload_batch_id: Mapped[Optional[int]] = mapped_column(ForeignKey("seller_upload_batches.id"), nullable=True)
    
    card_bin: Mapped[Optional[str]] = mapped_column("bin", String(6), nullable=True, index=True)
    item_name: Mapped[str] = mapped_column(String(200), nullable=False)
    cc_code: Mapped[str] = mapped_column(String(100), nullable=False)
    category_code: Mapped[str] = mapped_column(String(50), nullable=False)
    product_type: Mapped[str] = mapped_column(String(20), default="cc")
    product_subtype: Mapped[str] = mapped_column(String(30), default="with_fullz")  # with_zip, with_fullz
    
    seller_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    base_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    final_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    buyer_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    markup_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    markup_fixed: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    markup_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    markup_kind: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # flat, percent
    markup_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    
    is_in_stock: Mapped[bool] = mapped_column(Boolean, default=True)
    stock_count: Mapped[int] = mapped_column(Integer, default=0)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False)  # deprecated, use moderation_status
    
    moderation_status: Mapped[str] = mapped_column(String(30), default="pending_moderation")  # pending_moderation, approved, rejected, changes_requested, suspended
    moderation_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    moderated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    moderated_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)  # admin telegram_id
    
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    instruction: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    number: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    exp_mm: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    exp_yyyy: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cvv: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    fname: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    lname: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    zip: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    bank_name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    card_brand: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    card_level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    card_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # CREDIT, DEBIT, PREPAID
    is_non_vbv: Mapped[bool] = mapped_column(Boolean, default=False)
    has_fullz: Mapped[bool] = mapped_column(Boolean, default=False)
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # BIN, card, exp, cvc, type, level, bank, country, billing, shipping
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Mini App v2 additions - NON VBV pricing
    seller_price_non_vbv: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    buyer_price_non_vbv: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    seller: Mapped["Seller"] = relationship("Seller", back_populates="cc_items")
    upload_batch: Mapped[Optional["SellerUploadBatch"]] = relationship("SellerUploadBatch", back_populates="cc_items")
    cc_orders: Mapped[List["SellerCCOrder"]] = relationship("SellerCCOrder", back_populates="seller_cc_item")


class SellerCCOrder(Base):
    """Заказы CC от селлеров (аналог SellerOrder)"""
    __tablename__ = "seller_cc_orders"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("sellers.id"), nullable=False)
    seller_cc_item_id: Mapped[int] = mapped_column(ForeignKey("seller_cc_items.id"), nullable=False)
    buyer_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mirror_bot_id: Mapped[Optional[int]] = mapped_column(ForeignKey("mirror_bots.id"), nullable=True)
    
    status: Mapped[str] = mapped_column(String(20), default="pending_admin")
    product_type: Mapped[str] = mapped_column(String(20), default="cc")
    product_subtype: Mapped[str] = mapped_column(String(30), default="with_fullz")
    
    price_for_buyer: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    price_for_seller: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    
    admin_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    result_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    files: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    check_window_minutes: Mapped[int] = mapped_column(Integer, default=15)
    check_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    check_confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    check_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    feedback_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    feedback_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    report_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    reported_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    admin_message_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    escrow_released: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_complete_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    settled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    admin_approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    seller: Mapped["Seller"] = relationship("Seller", back_populates="seller_cc_orders")
    seller_cc_item: Mapped["SellerCCItem"] = relationship("SellerCCItem", back_populates="cc_orders")


# ==================== EDUCATION (подписки, мануалы) ====================


class EducationCategory(Base):
    """Категории Education (подписки, мануалы)"""
    __tablename__ = "education_categories"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    item_type: Mapped[str] = mapped_column(String(20), nullable=False)  # subscription, manual
    position: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class EducationSubscription(Base):
    """Подписки на время — выдаются как заказ"""
    __tablename__ = "education_subscriptions"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category_code: Mapped[str] = mapped_column(String(50), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class EducationManual(Base):
    """Мануалы — каталог файлов"""
    __tablename__ = "education_manuals"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category_code: Mapped[str] = mapped_column(String(50), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_name: Mapped[str] = mapped_column(String(200), nullable=False)
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ManualDelivery(Base):
    """Log of watermarked manual deliveries for leak tracing"""
    __tablename__ = "manual_deliveries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    manual_id: Mapped[int] = mapped_column(Integer, nullable=False)
    delivered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ==================== ACCOUNTS (Subscriptions / Accounts) ====================


class AccountCategory(Base):
    """Категории аккаунтов (Background Accounts, Lookup BA, AI, Proxy и др.)"""
    __tablename__ = "account_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category_type: Mapped[str] = mapped_column(String(30), default="background")  # background, lookup_ba, email, ai, proxy
    position: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    items: Mapped[List["AccountItem"]] = relationship("AccountItem", back_populates="category_obj", cascade="all, delete-orphan")


class AccountItem(Base):
    """Товар в каталоге аккаунтов — подписка на сервис"""
    __tablename__ = "account_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category_code: Mapped[str] = mapped_column(String(50), ForeignKey("account_categories.code"), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    duration_months: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    category_obj: Mapped["AccountCategory"] = relationship("AccountCategory", back_populates="items")
    inventory: Mapped[List["AccountInventory"]] = relationship("AccountInventory", back_populates="item_obj", cascade="all, delete-orphan")


class AccountInventory(Base):
    """Загруженные единицы товара для мгновенной выдачи"""
    __tablename__ = "account_inventory"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("account_items.id"), nullable=False, index=True)
    credentials: Mapped[dict] = mapped_column(JSON, nullable=False)
    is_sold: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    sold_to_user_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    sold_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    order_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    uploaded_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    item_obj: Mapped["AccountItem"] = relationship("AccountItem", back_populates="inventory")


# ==================== ANOTHER SERVICES ====================


class AnotherServiceButton(Base):
    """Кнопки/ссылки раздела Another Services"""
    __tablename__ = "another_service_buttons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    text_en: Mapped[str] = mapped_column(String(200), nullable=False)
    text_ru: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    text_zh: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    text_es: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    callback_data: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    button_type: Mapped[str] = mapped_column(String(20), default="url")  # url, callback, info
    position: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ==================== BRUTE BANK ====================


class BruteBankItem(Base):
    """Банковские аккаунты от брута — продаются мгновенно после одобрения"""
    __tablename__ = "brute_bank_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("sellers.id"), nullable=False)
    upload_batch_id: Mapped[Optional[int]] = mapped_column(ForeignKey("seller_upload_batches.id"), nullable=True)
    group_id: Mapped[Optional[int]] = mapped_column(ForeignKey("brute_bank_groups.id"), nullable=True)

    bank_name: Mapped[str] = mapped_column(String(200), nullable=False)
    bank_code: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # vcc, personal, business, crypto
    product_type: Mapped[str] = mapped_column(String(20), default="bank")  # bank
    product_subtype: Mapped[str] = mapped_column(String(30), default="brute")  # brute
    balance_range: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    account_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)

    credentials: Mapped[dict] = mapped_column(JSON, nullable=False)  # {"login": ..., "password": ..., "extra": ...}
    account_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    routing_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    holder_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    holder_address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    balance_info: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # "$12,450"
    account_details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    base_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    buyer_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    markup_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    markup_kind: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    markup_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)

    moderation_status: Mapped[str] = mapped_column(String(30), default="pending", index=True)  # pending, approved, rejected
    moderation_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    moderated_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    status: Mapped[str] = mapped_column(String(20), default="available", index=True)  # available, sold, removed
    buyer_user_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    mirror_bot_id: Mapped[Optional[int]] = mapped_column(ForeignKey("mirror_bots.id"), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    sold_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    seller: Mapped["Seller"] = relationship("Seller")
    upload_batch: Mapped[Optional["SellerUploadBatch"]] = relationship("SellerUploadBatch", back_populates="brute_items")
    group: Mapped[Optional["BruteBankGroup"]] = relationship("BruteBankGroup", back_populates="items")
    orders: Mapped[List["BruteBankOrder"]] = relationship("BruteBankOrder", back_populates="item")


class BruteBankGroup(Base):
    """Группа Brute Bank на уровне банка/витрины, управляется админкой"""
    __tablename__ = "brute_bank_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_key: Mapped[str] = mapped_column(String(220), nullable=False, unique=True, index=True)
    bank_code: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    bank_name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # vcc, personal, business, crypto
    attributes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # AN:RN+INST YODLEE...
    position: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    items: Mapped[List["BruteBankItem"]] = relationship("BruteBankItem", back_populates="group")


class BruteBankOrder(Base):
    """Ledger of brute-bank purchases for audit and seller settlements."""
    __tablename__ = "brute_bank_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    brute_bank_item_id: Mapped[int] = mapped_column(ForeignKey("brute_bank_items.id"), nullable=False)
    seller_id: Mapped[int] = mapped_column(ForeignKey("sellers.id"), nullable=False)
    buyer_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mirror_bot_id: Mapped[Optional[int]] = mapped_column(ForeignKey("mirror_bots.id"), nullable=True)

    status: Mapped[str] = mapped_column(String(20), default="completed")  # completed, refunded, disputed
    price_for_buyer: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    price_for_seller: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    admin_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    check_window_minutes: Mapped[int] = mapped_column(Integer, default=15)
    check_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    check_confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    check_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    feedback_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    feedback_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    report_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    reported_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    escrow_released: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_complete_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    settled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    item: Mapped["BruteBankItem"] = relationship("BruteBankItem", back_populates="orders")
    seller: Mapped["Seller"] = relationship("Seller", back_populates="brute_bank_orders")
    mirror_bot: Mapped[Optional["MirrorBot"]] = relationship("MirrorBot")


class EnrollCategory(Base):
    __tablename__ = "enroll_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_custom: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    items: Mapped[List["SellerEnrollItem"]] = relationship("SellerEnrollItem", back_populates="enroll_category")


class EnrollCategoryRequest(Base):
    __tablename__ = "enroll_category_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("sellers.id"), nullable=False, index=True)
    requested_name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)  # pending, approved, rejected
    admin_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class BankTypeRequest(Base):
    """Requests from sellers to add new bank types to the Banks section"""
    __tablename__ = "bank_type_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("sellers.id"), nullable=False, index=True)
    requested_name: Mapped[str] = mapped_column(String(200), nullable=False)
    state: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    zip: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    has_docs: Mapped[bool] = mapped_column(Boolean, default=False)
    doc_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    product_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # bank, enrol
    product_subtype: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)  # log, selfreg
    category: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # vcc, personal, business, crypto
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)  # pending, approved, rejected
    admin_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class BruteBankTypeRequest(Base):
    """Requests from sellers to add new bank types to Brute Bank section"""
    __tablename__ = "brute_bank_type_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("sellers.id"), nullable=False, index=True)
    requested_name: Mapped[str] = mapped_column(String(200), nullable=False)
    bank_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    attributes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # vcc, personal, business, crypto
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)  # pending, approved, rejected
    admin_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class SellerEnrollItem(Base):
    __tablename__ = "seller_enroll_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("sellers.id"), nullable=False)
    enroll_category_id: Mapped[Optional[int]] = mapped_column(ForeignKey("enroll_categories.id"), nullable=True, index=True)
    portal: Mapped[str] = mapped_column(String(100), nullable=False)
    bank_name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    card_zip: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    card_state: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    card_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # credit, debit
    balance: Mapped[float] = mapped_column(Float, nullable=False)
    data_file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    has_ssn: Mapped[bool] = mapped_column(Boolean, default=False)
    has_dob: Mapped[bool] = mapped_column(Boolean, default=False)
    has_address: Mapped[bool] = mapped_column(Boolean, default=False)
    has_docs: Mapped[bool] = mapped_column(Boolean, default=False)
    online_access: Mapped[bool] = mapped_column(Boolean, default=True)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    is_in_stock: Mapped[bool] = mapped_column(Boolean, default=True)
    moderation_status: Mapped[str] = mapped_column(String(20), default="pending_moderation")
    raw_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Mini App v2 additions - Detailed personal data
    first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    dob: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    ssn: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # Encrypted
    address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    zip: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    additional_info: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    seller: Mapped["Seller"] = relationship("Seller", back_populates="enroll_items")
    enroll_category: Mapped[Optional["EnrollCategory"]] = relationship("EnrollCategory", back_populates="items")
    orders: Mapped[List["SellerEnrollOrder"]] = relationship("SellerEnrollOrder", back_populates="item")


class SellerEnrollOrder(Base):
    __tablename__ = "seller_enroll_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("seller_enroll_items.id"), nullable=False)
    buyer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    seller_id: Mapped[int] = mapped_column(ForeignKey("sellers.id"), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    purchased_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    guarantee_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    report_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    escrow_released: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_complete_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    settled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Modern-schema fields used by the generic specials purchase flow
    buyer_user_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    mirror_bot_id: Mapped[Optional[int]] = mapped_column(ForeignKey("mirror_bots.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="completed")
    price_for_buyer: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    price_for_seller: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    result_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    check_window_minutes: Mapped[int] = mapped_column(Integer, default=60)
    check_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    check_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    feedback_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    feedback_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    reported_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    item: Mapped["SellerEnrollItem"] = relationship("SellerEnrollItem", back_populates="orders")
    buyer: Mapped["User"] = relationship("User", foreign_keys=[buyer_id])
    seller: Mapped["Seller"] = relationship("Seller", back_populates="seller_enroll_orders")


class SellerBankItem(Base):
    __tablename__ = "seller_bank_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("sellers.id"), nullable=False)
    bank: Mapped[str] = mapped_column(String(100), nullable=False)
    registration_date: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    zip: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    has_phone: Mapped[bool] = mapped_column(Boolean, default=False)
    phone_days_remaining: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    phone_renewable: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    email_access: Mapped[bool] = mapped_column(Boolean, default=False)
    has_ssn: Mapped[bool] = mapped_column(Boolean, default=False)
    has_docs: Mapped[bool] = mapped_column(Boolean, default=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    is_in_stock: Mapped[bool] = mapped_column(Boolean, default=True)
    moderation_status: Mapped[str] = mapped_column(String(20), default="pending")
    raw_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Mini App v2 additions
    category: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    bank_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    product_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    phone_can_swap: Mapped[bool] = mapped_column(Boolean, default=False)
    return_item_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    return_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    seller: Mapped["Seller"] = relationship("Seller", back_populates="bank_items")
    orders: Mapped[List["SellerBankOrder"]] = relationship("SellerBankOrder", back_populates="item")


class SellerBankOrder(Base):
    __tablename__ = "seller_bank_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("seller_bank_items.id"), nullable=False)
    buyer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    seller_id: Mapped[int] = mapped_column(ForeignKey("sellers.id"), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    purchased_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    guarantee_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    report_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    item: Mapped["SellerBankItem"] = relationship("SellerBankItem", back_populates="orders")
    buyer: Mapped["User"] = relationship("User", foreign_keys=[buyer_id])
    seller: Mapped["Seller"] = relationship("Seller", back_populates="seller_bank_orders")


class SellerLogsItem(Base):
    __tablename__ = "seller_logs_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("sellers.id"), nullable=False)
    bank: Mapped[str] = mapped_column(String(100), nullable=False)
    total_balance: Mapped[float] = mapped_column(Float, nullable=False)
    log_file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    description_en: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    has_cvv: Mapped[bool] = mapped_column(Boolean, default=False)
    bt_available: Mapped[bool] = mapped_column(Boolean, default=False)
    promo_available: Mapped[bool] = mapped_column(Boolean, default=False)
    zelle_enroll: Mapped[bool] = mapped_column(Boolean, default=False)
    wire_available: Mapped[bool] = mapped_column(Boolean, default=False)
    safepass_unlocked: Mapped[bool] = mapped_column(Boolean, default=False)
    email_valid: Mapped[bool] = mapped_column(Boolean, default=False)
    has_cookies: Mapped[bool] = mapped_column(Boolean, default=False)
    has_screenshot: Mapped[bool] = mapped_column(Boolean, default=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    is_in_stock: Mapped[bool] = mapped_column(Boolean, default=True)
    moderation_status: Mapped[str] = mapped_column(String(20), default="pending_moderation")
    raw_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    seller: Mapped["Seller"] = relationship("Seller", back_populates="logs_items")
    orders: Mapped[List["SellerLogsOrder"]] = relationship("SellerLogsOrder", back_populates="item")


class SellerLogsOrder(Base):
    __tablename__ = "seller_logs_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("seller_logs_items.id"), nullable=False)
    buyer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    seller_id: Mapped[int] = mapped_column(ForeignKey("sellers.id"), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    purchased_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    guarantee_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    report_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    item: Mapped["SellerLogsItem"] = relationship("SellerLogsItem", back_populates="orders")
    buyer: Mapped["User"] = relationship("User", foreign_keys=[buyer_id])
    seller: Mapped["Seller"] = relationship("Seller", back_populates="seller_logs_orders")


class SellerNFCItem(Base):
    __tablename__ = "seller_nfc_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("sellers.id"), nullable=False)
    upload_batch_id: Mapped[Optional[int]] = mapped_column(ForeignKey("seller_upload_batches.id"), nullable=True)
    item_name: Mapped[str] = mapped_column(String(200), nullable=False)
    product_type: Mapped[str] = mapped_column(String(20), default="nfc")
    product_subtype: Mapped[str] = mapped_column(String(30), default="apple_pay")
    nfc_type: Mapped[str] = mapped_column(String(10), nullable=False)  # ap, gp, other
    bank_name: Mapped[str] = mapped_column(String(120), nullable=False)
    country: Mapped[str] = mapped_column(String(10), nullable=False)
    state: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    zip: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    seller_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    base_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    final_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    buyer_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    markup_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    markup_fixed: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    markup_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    markup_kind: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    markup_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    data_file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    instruction: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    moderation_status: Mapped[str] = mapped_column(String(30), default="pending_moderation")
    moderation_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    moderated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    moderated_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    is_in_stock: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    seller: Mapped["Seller"] = relationship("Seller", back_populates="nfc_items")
    upload_batch: Mapped[Optional["SellerUploadBatch"]] = relationship("SellerUploadBatch", back_populates="nfc_items")
    orders: Mapped[List["SellerNFCOrder"]] = relationship("SellerNFCOrder", back_populates="item")


class SellerNFCOrder(Base):
    __tablename__ = "seller_nfc_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("sellers.id"), nullable=False)
    seller_nfc_item_id: Mapped[int] = mapped_column(ForeignKey("seller_nfc_items.id"), nullable=False)
    buyer_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mirror_bot_id: Mapped[Optional[int]] = mapped_column(ForeignKey("mirror_bots.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending_admin")
    product_type: Mapped[str] = mapped_column(String(20), default="nfc")
    product_subtype: Mapped[str] = mapped_column(String(30), default="apple_pay")
    price_for_buyer: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    price_for_seller: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    result_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    files: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    check_window_minutes: Mapped[int] = mapped_column(Integer, default=60)
    check_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    check_confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    check_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    feedback_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    feedback_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    report_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    reported_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    escrow_released: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_complete_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    settled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    seller: Mapped["Seller"] = relationship("Seller", back_populates="seller_nfc_orders")
    item: Mapped["SellerNFCItem"] = relationship("SellerNFCItem", back_populates="orders")


class SellerOTPItem(Base):
    __tablename__ = "seller_otp_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("sellers.id"), nullable=False)
    upload_batch_id: Mapped[Optional[int]] = mapped_column(ForeignKey("seller_upload_batches.id"), nullable=True)
    item_name: Mapped[str] = mapped_column(String(200), nullable=False)
    product_type: Mapped[str] = mapped_column(String(20), default="otp")
    product_subtype: Mapped[str] = mapped_column(String(30), default="otp_card")
    bank_name: Mapped[str] = mapped_column(String(120), nullable=False)
    balance: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    has_fullz: Mapped[bool] = mapped_column(Boolean, default=False)
    sms_access_type: Mapped[str] = mapped_column(String(30), nullable=False)  # seller_mediated, account_access
    data_file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    seller_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    base_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    final_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    buyer_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    markup_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    markup_fixed: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    markup_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    markup_kind: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    markup_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    instruction: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    moderation_status: Mapped[str] = mapped_column(String(30), default="pending_moderation")
    moderation_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    moderated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    moderated_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    is_in_stock: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Mini App v2 additions - Fullz fields
    state: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    zip: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    fullz_first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    fullz_last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    fullz_dob: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    fullz_ssn: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # Encrypted
    fullz_address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    fullz_city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    fullz_state: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    fullz_zip: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    fullz_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    fullz_email: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    seller: Mapped["Seller"] = relationship("Seller", back_populates="otp_items")
    upload_batch: Mapped[Optional["SellerUploadBatch"]] = relationship("SellerUploadBatch", back_populates="otp_items")
    orders: Mapped[List["SellerOTPOrder"]] = relationship("SellerOTPOrder", back_populates="item")


class SellerOTPOrder(Base):
    __tablename__ = "seller_otp_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("sellers.id"), nullable=False)
    seller_otp_item_id: Mapped[int] = mapped_column(ForeignKey("seller_otp_items.id"), nullable=False)
    buyer_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mirror_bot_id: Mapped[Optional[int]] = mapped_column(ForeignKey("mirror_bots.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending_admin")
    product_type: Mapped[str] = mapped_column(String(20), default="otp")
    product_subtype: Mapped[str] = mapped_column(String(30), default="otp_card")
    price_for_buyer: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    price_for_seller: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    result_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    files: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    check_window_minutes: Mapped[int] = mapped_column(Integer, default=60)
    check_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    check_confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    check_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    feedback_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    feedback_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    report_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    reported_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    escrow_released: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_complete_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    settled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    seller: Mapped["Seller"] = relationship("Seller", back_populates="seller_otp_orders")
    item: Mapped["SellerOTPItem"] = relationship("SellerOTPItem", back_populates="orders")


class SelfregCCCategory(Base):
    __tablename__ = "selfreg_cc_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_custom: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    items: Mapped[List["SellerSelfregCCItem"]] = relationship("SellerSelfregCCItem", back_populates="selfreg_cc_category")
    card_names: Mapped[List["SelfregCCCardName"]] = relationship("SelfregCCCardName", back_populates="category", cascade="all, delete-orphan")


class SelfregCCCardName(Base):
    """Card names for Selfreg CC categories (Mini App v2)"""
    __tablename__ = "selfreg_cc_card_names"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("selfreg_cc_categories.id", ondelete="CASCADE"), nullable=False, index=True)
    card_name: Mapped[str] = mapped_column(String(200), nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    category: Mapped["SelfregCCCategory"] = relationship("SelfregCCCategory", back_populates="card_names")


class SelfregCCCategoryRequest(Base):
    __tablename__ = "selfreg_cc_category_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("sellers.id"), nullable=False, index=True)
    requested_name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    admin_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class SellerSelfregCCItem(Base):
    __tablename__ = "seller_selfreg_cc_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("sellers.id"), nullable=False)
    upload_batch_id: Mapped[Optional[int]] = mapped_column(ForeignKey("seller_upload_batches.id"), nullable=True)
    selfreg_cc_category_id: Mapped[Optional[int]] = mapped_column(ForeignKey("selfreg_cc_categories.id"), nullable=True, index=True)
    item_name: Mapped[str] = mapped_column(String(200), nullable=False)
    product_type: Mapped[str] = mapped_column(String(20), default="bank")
    product_subtype: Mapped[str] = mapped_column(String(30), default="selfreg_cc")
    bank_name: Mapped[str] = mapped_column(String(120), nullable=False)
    card_name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    credit_limit: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    vcc_limit: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    zip: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    has_email: Mapped[bool] = mapped_column(Boolean, default=False)
    has_phone: Mapped[bool] = mapped_column(Boolean, default=False)
    phone_days_remaining: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    phone_renewable: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    phone_change_allowed: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    online_access: Mapped[bool] = mapped_column(Boolean, default=False)
    seller_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    base_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    final_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    buyer_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    markup_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    markup_fixed: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    markup_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    markup_kind: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    markup_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    instruction: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    moderation_status: Mapped[str] = mapped_column(String(30), default="pending_moderation")
    moderation_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    moderated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    moderated_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    is_in_stock: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Mini App v2 additions
    registration_date: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    vcc_bin: Mapped[Optional[str]] = mapped_column(String(6), nullable=True)
    return_item_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    return_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    seller: Mapped["Seller"] = relationship("Seller", back_populates="selfreg_cc_items")
    upload_batch: Mapped[Optional["SellerUploadBatch"]] = relationship("SellerUploadBatch", back_populates="selfreg_cc_items")
    selfreg_cc_category: Mapped[Optional["SelfregCCCategory"]] = relationship("SelfregCCCategory", back_populates="items")
    orders: Mapped[List["SellerSelfregCCOrder"]] = relationship("SellerSelfregCCOrder", back_populates="item")


class SellerSelfregCCOrder(Base):
    __tablename__ = "seller_selfreg_cc_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("sellers.id"), nullable=False)
    seller_selfreg_cc_item_id: Mapped[int] = mapped_column(ForeignKey("seller_selfreg_cc_items.id"), nullable=False)
    buyer_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mirror_bot_id: Mapped[Optional[int]] = mapped_column(ForeignKey("mirror_bots.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending_admin")
    product_type: Mapped[str] = mapped_column(String(20), default="bank")
    product_subtype: Mapped[str] = mapped_column(String(30), default="selfreg_cc")
    price_for_buyer: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    price_for_seller: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    result_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    files: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    check_window_minutes: Mapped[int] = mapped_column(Integer, default=60)
    check_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    check_confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    check_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    feedback_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    feedback_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    report_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    reported_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    seller: Mapped["Seller"] = relationship("Seller", back_populates="seller_selfreg_cc_orders")
    item: Mapped["SellerSelfregCCItem"] = relationship("SellerSelfregCCItem", back_populates="orders")


class SellerCheckItem(Base):
    __tablename__ = "seller_check_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("sellers.id"), nullable=False)
    upload_batch_id: Mapped[Optional[int]] = mapped_column(ForeignKey("seller_upload_batches.id"), nullable=True)
    item_name: Mapped[str] = mapped_column(String(200), nullable=False)
    product_type: Mapped[str] = mapped_column(String(20), default="bank")
    product_subtype: Mapped[str] = mapped_column(String(30), default="checks")
    check_type: Mapped[str] = mapped_column(String(30), nullable=False)
    bank_name: Mapped[str] = mapped_column(String(120), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    state: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    zip: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    has_holder_name: Mapped[bool] = mapped_column(Boolean, default=False)
    has_address: Mapped[bool] = mapped_column(Boolean, default=False)
    check_date: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    seller_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    scan_file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    template_file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    seller_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    base_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    final_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    buyer_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    markup_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    markup_fixed: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    markup_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    markup_kind: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    markup_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    moderation_status: Mapped[str] = mapped_column(String(30), default="pending_moderation")
    moderation_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    moderated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    moderated_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    is_in_stock: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    seller: Mapped["Seller"] = relationship("Seller", back_populates="check_items")
    upload_batch: Mapped[Optional["SellerUploadBatch"]] = relationship("SellerUploadBatch", back_populates="check_items")
    orders: Mapped[List["SellerCheckOrder"]] = relationship("SellerCheckOrder", back_populates="item")


class SellerCheckOrder(Base):
    __tablename__ = "seller_check_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("sellers.id"), nullable=False)
    seller_check_item_id: Mapped[int] = mapped_column(ForeignKey("seller_check_items.id"), nullable=False)
    buyer_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mirror_bot_id: Mapped[Optional[int]] = mapped_column(ForeignKey("mirror_bots.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending_admin")
    product_type: Mapped[str] = mapped_column(String(20), default="bank")
    product_subtype: Mapped[str] = mapped_column(String(30), default="checks")
    price_for_buyer: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    price_for_seller: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    result_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    files: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    check_window_minutes: Mapped[int] = mapped_column(Integer, default=60)
    check_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    check_confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    check_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    feedback_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    feedback_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    report_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    reported_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    escrow_released: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_complete_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    settled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    seller: Mapped["Seller"] = relationship("Seller", back_populates="seller_check_orders")
    item: Mapped["SellerCheckItem"] = relationship("SellerCheckItem", back_populates="orders")


# ==================== DOCUMENT ITEMS ====================


class SellerDocumentItem(Base):
    """Seller-uploaded fake document templates (DL, passport, business docs)."""
    __tablename__ = "seller_document_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("sellers.id"), nullable=False)
    upload_batch_id: Mapped[Optional[int]] = mapped_column(ForeignKey("seller_upload_batches.id"), nullable=True)
    item_name: Mapped[str] = mapped_column(String(200), nullable=False)
    product_type: Mapped[str] = mapped_column(String(20), default="docs")
    product_subtype: Mapped[str] = mapped_column(String(50), nullable=False)  # dl_front_back, dl_selfie, passport, business_docs
    state: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    quality: Mapped[str] = mapped_column(String(20), default="standard")  # standard, premium
    has_hologram: Mapped[bool] = mapped_column(Boolean, default=False)
    has_selfie: Mapped[bool] = mapped_column(Boolean, default=False)
    sample_file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    seller_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    seller_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    base_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    final_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    buyer_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    markup_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    markup_fixed: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    markup_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    markup_kind: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    markup_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    moderation_status: Mapped[str] = mapped_column(String(30), default="pending_moderation")
    moderation_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    moderated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    moderated_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    is_in_stock: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    seller: Mapped["Seller"] = relationship("Seller", back_populates="document_items")
    upload_batch: Mapped[Optional["SellerUploadBatch"]] = relationship("SellerUploadBatch", back_populates="document_items")


# ==================== FULLZ ITEMS ====================


class SellerFullzItem(Base):
    """Seller-uploaded fullz datasets (personal / business)."""
    __tablename__ = "seller_fullz_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("sellers.id"), nullable=False)
    upload_batch_id: Mapped[Optional[int]] = mapped_column(ForeignKey("seller_upload_batches.id"), nullable=True)
    item_name: Mapped[str] = mapped_column(String(200), nullable=False)
    product_type: Mapped[str] = mapped_column(String(20), default="fullz")
    fullz_type: Mapped[str] = mapped_column(String(20), nullable=False)  # personal, business
    state: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    credit_score: Mapped[str] = mapped_column(String(20), default="any")  # any, 500+, 700+, 800+
    age_range: Mapped[str] = mapped_column(String(20), default="any")    # any, 18-25, 26-35, 36+
    gender: Mapped[str] = mapped_column(String(10), default="any")       # any, male, female
    company_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # sole, llc, corp
    loan_size: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)     # any, 25k-200k, 200k-500k, 500k+
    report_group: Mapped[str] = mapped_column(String(30), default="basic")          # basic, cr, cr_dl, cr_dl_mvr, cr_dl_fullmvr
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    data_file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    seller_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    seller_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    base_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    final_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    buyer_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    markup_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    markup_fixed: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    markup_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    markup_kind: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    markup_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    moderation_status: Mapped[str] = mapped_column(String(30), default="pending_moderation")
    moderation_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    moderated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    moderated_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    is_in_stock: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    seller: Mapped["Seller"] = relationship("Seller", back_populates="fullz_items")
    upload_batch: Mapped[Optional["SellerUploadBatch"]] = relationship("SellerUploadBatch", back_populates="fullz_items")


# ==================== AUTOMATION ====================


class AutomationProxy(Base):
    """Прокси для автоматизации lookup_credit."""
    __tablename__ = "automation_proxies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    password: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    proxy_type: Mapped[str] = mapped_column(String(20), default="http")
    country: Mapped[str] = mapped_column(String(10), default="us")
    rotate_every: Mapped[int] = mapped_column(Integer, default=3)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_checked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AutomationApiKey(Base):
    """API-ключи, связанные с автоматизацией и внешними сервисами."""
    __tablename__ = "automation_api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str] = mapped_column(String(80), nullable=False, default="other")
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    key_value: Mapped[str] = mapped_column(Text, nullable=False)
    balance: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    daily_limit: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AutomationConfig(Base):
    """Глобальная конфигурация automation-движка."""
    __tablename__ = "automation_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    service_code: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, default="lookup_credit")
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    worker_count: Mapped[int] = mapped_column(Integer, default=10)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)
    headless: Mapped[bool] = mapped_column(Boolean, default=True)
    poll_interval_seconds: Mapped[int] = mapped_column(Integer, default=5)
    screenshot_dir: Mapped[str] = mapped_column(String(255), default="./data/automation/screenshots")
    active_proxy_id: Mapped[Optional[int]] = mapped_column(ForeignKey("automation_proxies.id"), nullable=True)
    notify_admin_on_error: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_user_on_error: Mapped[bool] = mapped_column(Boolean, default=True)
    admin_chat_ids: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    active_proxy: Mapped[Optional["AutomationProxy"]] = relationship("AutomationProxy")


class AutomationJob(Base):
    """Задача автоматизации, привязанная к заказу lookup_credit."""
    __tablename__ = "automation_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False, index=True)
    bulk_item_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    service_code: Mapped[str] = mapped_column(String(80), default="lookup_credit", index=True)
    status: Mapped[str] = mapped_column(String(30), default="queued", index=True)
    priority: Mapped[int] = mapped_column(Integer, default=100)
    external_job_id: Mapped[Optional[str]] = mapped_column(String(120), nullable=True, unique=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    mirror_bot_id: Mapped[int] = mapped_column(ForeignKey("mirror_bots.id"), nullable=False)
    input_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    result_payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    worker_label: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    needs_ssn: Mapped[bool] = mapped_column(Boolean, default=False)
    ssn_requested_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    ssn_received_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    order: Mapped["Order"] = relationship("Order")
    mirror_bot: Mapped["MirrorBot"] = relationship("MirrorBot")
    finance_entries: Mapped[List["AutomationFinanceEntry"]] = relationship(
        "AutomationFinanceEntry",
        back_populates="job",
        cascade="all, delete-orphan",
    )


class AutomationFinanceEntry(Base):
    """Журнал доходов и расходов automation-раздела."""
    __tablename__ = "automation_finance_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[Optional[int]] = mapped_column(ForeignKey("automation_jobs.id"), nullable=True)
    order_id: Mapped[Optional[int]] = mapped_column(ForeignKey("orders.id"), nullable=True)
    entry_type: Mapped[str] = mapped_column(String(20), nullable=False)  # income | expense
    source_type: Mapped[str] = mapped_column(String(30), nullable=False)  # order | proxy | api_key | manual
    source_ref: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    job: Mapped[Optional["AutomationJob"]] = relationship("AutomationJob", back_populates="finance_entries")
    order: Mapped[Optional["Order"]] = relationship("Order")


class SystemSetting(Base):
    """Динамические системные настройки v24."""
    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class WorkerViolation(Base):
    """Нарушения воркеров, связанные с утечкой контактов и иными нарушениями."""
    __tablename__ = "worker_violations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    worker_id: Mapped[int] = mapped_column(ForeignKey("workers.id"), nullable=False, index=True)
    order_id: Mapped[Optional[int]] = mapped_column(ForeignKey("orders.id"), nullable=True)
    violation_type: Mapped[str] = mapped_column(String(100), nullable=False)
    original_text: Mapped[str] = mapped_column(Text, nullable=False)
    filtered_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    worker: Mapped["Worker"] = relationship("Worker")
    order: Mapped[Optional["Order"]] = relationship("Order")


class ProductModerationLog(Base):
    """История модерации товаров v24."""
    __tablename__ = "product_moderation_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False, index=True)
    moderator_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    previous_status: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    new_status: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    product: Mapped["Product"] = relationship("Product")


class EscrowRelease(Base):
    """Журнал идемпотентных выплат эскроу.

    Supports multiple order tables via order_table + seller_order_id.
    """
    __tablename__ = "escrow_releases"
    __table_args__ = (
        UniqueConstraint("order_table", "seller_order_id", name="uq_escrow_order"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    seller_order_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    order_table: Mapped[str] = mapped_column(String(60), default="seller_orders", nullable=False)
    seller_id: Mapped[int] = mapped_column(ForeignKey("sellers.id"), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    released_by: Mapped[str] = mapped_column(String(30), default="system")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    seller: Mapped["Seller"] = relationship("Seller")


class SellerOrderDispute(Base):
    """Споры по seller_orders в логике v24."""
    __tablename__ = "seller_order_disputes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("seller_orders.id"), nullable=False, unique=True)
    opened_by: Mapped[int] = mapped_column(BigInteger, nullable=False)
    reason: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="open")
    seller_response_due_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    seller_responded_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    buyer_evidence: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    seller_evidence: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    assigned_admin_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    appeal_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    appeal_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    appeal_requested_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    resolution_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolved_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    order: Mapped["SellerOrder"] = relationship("SellerOrder")

class BulkDiscountTier(Base):
    """Настраиваемые скидки за количество — управляются из admin-панели."""
    __tablename__ = "bulk_discount_tiers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # e.g. banks, esim, fullz, cc, accounts, docs
    min_qty: Mapped[int] = mapped_column(Integer, nullable=False)
    discount_percent: Mapped[float] = mapped_column(Float, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (UniqueConstraint("category", "min_qty", name="uq_bulk_discount_cat_qty"),)


class KnowledgeBaseArticle(Base):
    """База знаний — статьи для Answer Bot и раздела помощи воркерам."""
    __tablename__ = "kb_articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    keywords: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # comma-separated
    category: Mapped[str] = mapped_column(String(50), default="general")  # general, financial, technical, worker, suggestion
    audience: Mapped[str] = mapped_column(String(20), default="user")  # user, worker, all
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    views: Mapped[int] = mapped_column(Integer, default=0)
    helpful_votes: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ─── Referral System ─────────────────────────────────────────────────────────

class Referral(Base):
    """Реферальные связи между пользователями."""
    __tablename__ = "referrals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    referrer_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    referred_id: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True, index=True)
    source_bot: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # marketer_bot, seller_bot, etc.
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    # JSON array of up to 5 ancestor telegram_ids: [level1_id, level2_id, ...]
    referral_chain: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")  # active, blocked
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index("ix_referrals_referrer_created", "referrer_id", "created_at"),
    )


class ReferralReward(Base):
    """Начисления по реферальной программе — проходят модерацию."""
    __tablename__ = "referral_rewards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    referrer_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    # telegram_id маркетолога-реферера
    referred_user_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    # telegram_id нового пользователя (реферала)
    referral_id: Mapped[Optional[int]] = mapped_column(ForeignKey("referrals.id"), nullable=True, index=True)
    # связь с записью в таблице referrals
    amount_display: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0.00)
    # сумма, которую показываем пользователю (отображаемый %)
    amount_real: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0.00)
    # реальная выплата (внутренняя логика)
    level: Mapped[int] = mapped_column(Integer, default=1)
    # уровень реферальной цепочки (1=прямой, 2=второй уровень, и т.д.)
    source: Mapped[str] = mapped_column(String(50), default="purchase")
    # источник: purchase, registration
    status: Mapped[str] = mapped_column(String(30), default="pending_moderation")
    # pending_moderation / approved / rejected / paid
    reviewed_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    reject_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    referral: Mapped[Optional["Referral"]] = relationship("Referral")


class ReferralWithdrawal(Base):
    """Заявки на вывод реферального бонуса."""
    __tablename__ = "referral_withdrawals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    referrer_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    # telegram_id маркетолога
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    requisites: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending_moderation")
    # pending_moderation / approved / rejected
    reviewed_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    reject_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ReferralSettings(Base):
    """Настройки реферальной системы (singleton, id=1)."""
    __tablename__ = "referral_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Уровни выплат (display — что показываем, real — что выплачиваем)
    level1_display_pct: Mapped[float] = mapped_column(Float, default=15.0)
    level1_real_pct: Mapped[float] = mapped_column(Float, default=7.0)
    level2_display_pct: Mapped[float] = mapped_column(Float, default=7.0)
    level2_real_pct: Mapped[float] = mapped_column(Float, default=3.0)
    level3_display_pct: Mapped[float] = mapped_column(Float, default=3.0)
    level3_real_pct: Mapped[float] = mapped_column(Float, default=1.0)
    level4_display_pct: Mapped[float] = mapped_column(Float, default=1.0)
    level4_real_pct: Mapped[float] = mapped_column(Float, default=0.2)
    # Антифрод
    max_daily_referrals: Mapped[int] = mapped_column(Integer, default=50)
    cooldown_hours: Mapped[int] = mapped_column(Integer, default=0)
    min_purchase_usd: Mapped[float] = mapped_column(Float, default=1.0)
    # Вывод
    min_withdrawal_usd: Mapped[float] = mapped_column(Float, default=10.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
