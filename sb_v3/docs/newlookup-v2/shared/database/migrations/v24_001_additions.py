"""Reference v24 migration artifact.

This repo still applies schema sync imperatively at startup, but the package
expects a visible migration artifact for the v24 additions. Keep this file in
sync with `shared/database/session.py` when schema changes are added.
"""

from alembic import op
import sqlalchemy as sa
from datetime import datetime


revision = "v24_001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("transactions", sa.Column("account_type", sa.String(20), nullable=False, server_default="user"))
    op.add_column("transactions", sa.Column("account_id", sa.BigInteger(), nullable=True))
    op.add_column("transactions", sa.Column("currency", sa.String(10), nullable=False, server_default="USD"))
    op.add_column("transactions", sa.Column("status", sa.String(20), nullable=False, server_default="completed"))
    op.add_column("transactions", sa.Column("related_entity_type", sa.String(50), nullable=True))
    op.add_column("transactions", sa.Column("related_entity_id", sa.BigInteger(), nullable=True))
    op.add_column("transactions", sa.Column("effective_at", sa.DateTime(), nullable=True))
    op.add_column("transactions", sa.Column("idempotency_key", sa.String(120), nullable=True))
    op.create_index("ix_transactions_status", "transactions", ["status"])
    op.create_index("ix_transactions_effective_at", "transactions", ["effective_at"])
    op.create_index("ix_transactions_related_entity", "transactions", ["related_entity_type", "related_entity_id"])
    op.create_unique_constraint("uq_transactions_idempotency_key", "transactions", ["idempotency_key"])
    op.execute(sa.text("UPDATE transactions SET account_id = user_id WHERE account_id IS NULL"))

    op.create_table(
        "system_settings",
        sa.Column("key", sa.String(100), primary_key=True),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow),
    )

    op.create_table(
        "worker_violations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("worker_id", sa.Integer(), sa.ForeignKey("workers.id"), nullable=False),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=True),
        sa.Column("violation_type", sa.String(50), nullable=False),
        sa.Column("original_text", sa.Text(), nullable=False),
        sa.Column("filtered_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), default=datetime.utcnow),
    )
    op.create_index("ix_worker_violations_worker_id", "worker_violations", ["worker_id"])

    op.create_table(
        "seller_order_disputes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("seller_orders.id"), nullable=False, unique=True),
        sa.Column("opened_by", sa.BigInteger(), nullable=False),
        sa.Column("reason", sa.String(50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), default="open"),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        sa.Column("resolved_by", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(), default=datetime.utcnow),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "product_moderation_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("moderator_id", sa.BigInteger(), nullable=True),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("previous_status", sa.String(30), nullable=True),
        sa.Column("new_status", sa.String(30), nullable=True),
        sa.Column("created_at", sa.DateTime(), default=datetime.utcnow, nullable=False),
    )
    op.create_index("ix_product_moderation_logs_product_id", "product_moderation_logs", ["product_id"])
    op.create_index("ix_product_moderation_logs_created_at", "product_moderation_logs", ["created_at"])

    op.create_table(
        "escrow_releases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("seller_order_id", sa.Integer(), sa.ForeignKey("seller_orders.id"), nullable=False, unique=True),
        sa.Column("seller_id", sa.Integer(), sa.ForeignKey("sellers.id"), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("released_by", sa.String(30), nullable=False, server_default="system"),
        sa.Column("created_at", sa.DateTime(), default=datetime.utcnow, nullable=False),
    )
    op.create_index("ix_escrow_releases_seller_id", "escrow_releases", ["seller_id"])
    op.create_index("ix_escrow_releases_created_at", "escrow_releases", ["created_at"])

    op.create_table(
        "user_coupons",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("coupon_id", sa.Integer(), sa.ForeignKey("coupons.id"), nullable=False),
        sa.Column("activated_at", sa.DateTime(), default=datetime.utcnow, nullable=False),
        sa.Column("is_used", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=True),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("user_id", "coupon_id", name="uq_user_coupons_user_coupon"),
    )
    op.create_index("ix_user_coupons_user_id", "user_coupons", ["user_id"])
    op.create_index("ix_user_coupons_coupon_id", "user_coupons", ["coupon_id"])
    op.create_index("ix_user_coupons_activated_at", "user_coupons", ["activated_at"])
    op.create_index("ix_user_coupons_is_used", "user_coupons", ["is_used"])

    op.add_column("seller_orders", sa.Column("escrow_released", sa.Boolean(), default=False, server_default="false"))
    op.add_column("seller_orders", sa.Column("marketer_commission_paid", sa.Boolean(), default=False, server_default="false"))
    op.add_column("seller_orders", sa.Column("worker_paid", sa.Boolean(), default=False, server_default="false"))
    op.add_column("seller_orders", sa.Column("auto_complete_at", sa.DateTime(), nullable=True))
    op.add_column("seller_orders", sa.Column("dispute_deadline_at", sa.DateTime(), nullable=True))
    op.add_column("seller_orders", sa.Column("marketer_id", sa.Integer(), sa.ForeignKey("marketers.id"), nullable=True))
    op.add_column("seller_orders", sa.Column("marketer_commission_amount", sa.Numeric(10, 2), nullable=True))

    op.add_column("products", sa.Column("base_price", sa.Numeric(10, 2), nullable=True))
    op.add_column("products", sa.Column("final_price", sa.Numeric(10, 2), nullable=True))
    op.add_column("products", sa.Column("markup_percent", sa.Float(), nullable=True))
    op.add_column("products", sa.Column("markup_fixed", sa.Numeric(10, 2), nullable=True))
    op.add_column("products", sa.Column("moderation_status", sa.String(30), nullable=True, server_default="pending_moderation"))
    op.add_column("products", sa.Column("is_active", sa.Boolean(), nullable=True, server_default="true"))
    op.add_column("products", sa.Column("moderation_comment", sa.Text(), nullable=True))
    op.add_column("products", sa.Column("moderated_at", sa.DateTime(), nullable=True))
    op.add_column("products", sa.Column("moderated_by", sa.BigInteger(), nullable=True))

    op.add_column("workers", sa.Column("upload_categories", sa.JSON(), nullable=True))
    op.add_column("workers", sa.Column("upload_services", sa.JSON(), nullable=True))
    op.add_column("workers", sa.Column("violation_count", sa.Integer(), nullable=True, server_default="0"))
    op.add_column("workers", sa.Column("is_suspended", sa.Boolean(), nullable=True, server_default="false"))
    op.add_column("workers", sa.Column("suspended_at", sa.DateTime(), nullable=True))
    op.add_column("workers", sa.Column("suspended_reason", sa.Text(), nullable=True))
    op.add_column("workers", sa.Column("fixed_price", sa.Numeric(10, 2), nullable=True))
    op.add_column("workers", sa.Column("commission_percent", sa.Float(), nullable=True))
    op.add_column("workers", sa.Column("total_earned", sa.Numeric(10, 2), nullable=True, server_default="0"))
    op.add_column("workers", sa.Column("total_withdrawn", sa.Numeric(10, 2), nullable=True, server_default="0"))

    op.add_column("users", sa.Column("language", sa.String(10), nullable=True, server_default="ru"))
    op.add_column("users", sa.Column("marketer_id", sa.Integer(), sa.ForeignKey("marketers.id"), nullable=True))
    op.add_column("users", sa.Column("first_topup_bonus_applied", sa.Boolean(), nullable=True, server_default="false"))
    op.add_column("users", sa.Column("rules_accepted", sa.Boolean(), nullable=True, server_default="false"))
    op.add_column("users", sa.Column("active_coupon_code", sa.String(60), nullable=True))
    op.add_column("users", sa.Column("active_coupon_set_at", sa.DateTime(), nullable=True))
    op.add_column("users", sa.Column("trust_score", sa.Integer(), nullable=True, server_default="100"))
    op.add_column("users", sa.Column("last_active_at", sa.DateTime(), nullable=True))
    op.add_column("users", sa.Column("archive_channel_id", sa.BigInteger(), nullable=True))

    op.create_index("ix_seller_orders_status", "seller_orders", ["status"])
    op.create_index("ix_seller_orders_auto_complete", "seller_orders", ["auto_complete_at"])
    op.create_index("ix_products_moderation_status", "products", ["moderation_status"])
    op.create_index("ix_products_is_active", "products", ["is_active"])
    op.create_index("idx_users_archive_channel_id", "users", ["archive_channel_id"])

    op.add_column("seller_withdrawals", sa.Column("funds_reserved", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("worker_withdrawals", sa.Column("funds_reserved", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("marketer_withdrawals", sa.Column("funds_reserved", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("bot_owner_withdrawals", sa.Column("funds_reserved", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("sellers", sa.Column("is_on_vacation", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("sellers", sa.Column("vacation_started_at", sa.DateTime(), nullable=True))
    op.add_column("sellers", sa.Column("vacation_ends_at", sa.DateTime(), nullable=True))
    op.add_column("seller_order_disputes", sa.Column("seller_response_due_at", sa.DateTime(), nullable=True))
    op.add_column("seller_order_disputes", sa.Column("seller_responded_at", sa.DateTime(), nullable=True))
    op.add_column("seller_order_disputes", sa.Column("buyer_evidence", sa.JSON(), nullable=True))
    op.add_column("seller_order_disputes", sa.Column("seller_evidence", sa.JSON(), nullable=True))
    op.add_column("seller_order_disputes", sa.Column("assigned_admin_id", sa.BigInteger(), nullable=True))
    op.add_column("seller_order_disputes", sa.Column("appeal_status", sa.String(length=20), nullable=True))
    op.add_column("seller_order_disputes", sa.Column("appeal_reason", sa.Text(), nullable=True))
    op.add_column("seller_order_disputes", sa.Column("appeal_requested_at", sa.DateTime(), nullable=True))
    op.create_table(
        "seller_upload_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("seller_id", sa.Integer(), sa.ForeignKey("sellers.id"), nullable=False),
        sa.Column("item_type", sa.String(length=30), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    for key, value, description in [
        ("PLATFORM_FEE_BASE", "0.15", "Базовая комиссия платформы (15%)"),
        ("MARKETER_COMMISSION_RATE", "0.10", "Комиссия маркетолога (10%)"),
        ("ESCROW_HOLD_HOURS", "48", "Часов удержания эскроу"),
        ("ESCROW_HOLD_TOP_SELLER_HOURS", "12", "Часов удержания эскроу для top seller"),
        ("ESCROW_HOLD_STANDARD_HOURS", "48", "Стандартных часов удержания эскроу"),
        ("ESCROW_HOLD_NEW_SELLER_HOURS", "72", "Часов удержания эскроу для новых seller"),
        ("ESCROW_NEW_SELLER_SALES_THRESHOLD", "10", "Порог заказов для статуса нового seller"),
        ("ESCROW_TOP_SELLER_SCORE_X10", "48", "Порог reputation score x10 для top seller"),
        ("ESCROW_HOLD_RISKY_BUYER_HOURS", "72", "Часов удержания эскроу для risky buyer"),
        ("BUYER_TRUST_SCORE_RISK_THRESHOLD", "30", "Порог trust score для risky buyer"),
        ("DISPUTE_WINDOW_HOURS", "24", "Часов на открытие спора"),
        ("AUTO_COMPLETE_HOURS", "24", "Часов до автозавершения"),
        ("SELLER_DISPUTE_RESPONSE_HOURS", "24", "Часов на ответ seller по спору"),
        ("WORKER_VIOLATION_LIMIT", "3", "Нарушений до отстранения"),
        ("WORKER_VIOLATION_WINDOW_DAYS", "30", "Дней для подсчёта нарушений"),
        ("MIN_WITHDRAWAL_AMOUNT", "100.00", "Минимальная сумма вывода"),
        ("MAX_WITHDRAWAL_AMOUNT", "5000.00", "Максимальная сумма вывода"),
        ("AUTO_WITHDRAWAL_THRESHOLD", "500.00", "Порог авто-одобрения вывода"),
        ("WELCOME_COUPON_CODE", "WELCOME10", "Приветственный купон"),
        ("WELCOME_COUPON_DISCOUNT", "10", "Скидка по приветственному купону (%)"),
    ]:
        op.execute(
            sa.text(
                """
                INSERT INTO system_settings (key, value, description, updated_at)
                VALUES (:key, :value, :description, CURRENT_TIMESTAMP)
                """
            ).bindparams(key=key, value=value, description=description)
        )


def downgrade() -> None:
    op.drop_column("bot_owner_withdrawals", "funds_reserved")
    op.drop_column("marketer_withdrawals", "funds_reserved")
    op.drop_column("worker_withdrawals", "funds_reserved")
    op.drop_column("seller_withdrawals", "funds_reserved")

    op.drop_index("ix_products_is_active", "products")
    op.drop_index("ix_products_moderation_status", "products")
    op.drop_index("ix_seller_orders_auto_complete", "seller_orders")
    op.drop_index("ix_seller_orders_status", "seller_orders")

    op.drop_column("users", "last_active_at")
    op.drop_column("users", "trust_score")
    op.drop_column("users", "active_coupon_set_at")
    op.drop_column("users", "active_coupon_code")
    op.drop_column("users", "rules_accepted")
    op.drop_column("users", "first_topup_bonus_applied")
    op.drop_column("users", "marketer_id")
    op.drop_column("users", "language")
    op.drop_index("idx_users_archive_channel_id", "users")
    op.drop_column("users", "archive_channel_id")

    op.drop_column("workers", "total_withdrawn")
    op.drop_column("workers", "total_earned")
    op.drop_column("workers", "commission_percent")
    op.drop_column("workers", "fixed_price")
    op.drop_column("workers", "suspended_reason")
    op.drop_column("workers", "suspended_at")
    op.drop_column("workers", "is_suspended")
    op.drop_column("workers", "violation_count")
    op.drop_column("workers", "upload_services")
    op.drop_column("workers", "upload_categories")

    op.drop_column("products", "moderated_by")
    op.drop_column("products", "moderated_at")
    op.drop_column("products", "moderation_comment")
    op.drop_column("products", "is_active")
    op.drop_column("products", "moderation_status")
    op.drop_column("products", "markup_fixed")
    op.drop_column("products", "markup_percent")
    op.drop_column("products", "final_price")
    op.drop_column("products", "base_price")

    op.drop_column("seller_orders", "marketer_commission_amount")
    op.drop_column("seller_orders", "marketer_id")
    op.drop_column("seller_orders", "dispute_deadline_at")
    op.drop_column("seller_orders", "auto_complete_at")
    op.drop_column("seller_orders", "worker_paid")
    op.drop_column("seller_orders", "marketer_commission_paid")
    op.drop_column("seller_orders", "escrow_released")

    op.drop_index("ix_user_coupons_is_used", "user_coupons")
    op.drop_index("ix_user_coupons_activated_at", "user_coupons")
    op.drop_index("ix_user_coupons_coupon_id", "user_coupons")
    op.drop_index("ix_user_coupons_user_id", "user_coupons")
    op.drop_table("user_coupons")
    op.drop_table("seller_upload_templates")
    op.drop_table("seller_order_disputes")
    op.drop_index("ix_escrow_releases_created_at", "escrow_releases")
    op.drop_index("ix_escrow_releases_seller_id", "escrow_releases")
    op.drop_table("escrow_releases")
    op.drop_index("ix_product_moderation_logs_created_at", "product_moderation_logs")
    op.drop_index("ix_product_moderation_logs_product_id", "product_moderation_logs")
    op.drop_table("product_moderation_logs")
    op.drop_index("ix_worker_violations_worker_id", "worker_violations")
    op.drop_table("worker_violations")
    op.drop_table("system_settings")
    op.drop_constraint("uq_transactions_idempotency_key", "transactions", type_="unique")
    op.drop_index("ix_transactions_related_entity", "transactions")
    op.drop_index("ix_transactions_effective_at", "transactions")
    op.drop_index("ix_transactions_status", "transactions")
    op.drop_column("transactions", "idempotency_key")
    op.drop_column("transactions", "effective_at")
    op.drop_column("transactions", "related_entity_id")
    op.drop_column("transactions", "related_entity_type")
    op.drop_column("transactions", "status")
    op.drop_column("transactions", "currency")
    op.drop_column("transactions", "account_id")
    op.drop_column("transactions", "account_type")
