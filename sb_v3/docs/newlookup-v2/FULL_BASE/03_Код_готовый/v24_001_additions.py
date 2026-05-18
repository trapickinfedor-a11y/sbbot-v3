"""v24 additions: new columns and tables

Revision ID: v24_001
Revises: (укажи ID последней миграции v2)
Create Date: 2026-03-14

ИНСТРУКЦИЯ:
1. Найди ID последней миграции: alembic history
2. Замени "REPLACE_WITH_LAST_MIGRATION_ID" на реальный ID
3. Запусти: alembic upgrade head
"""

from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers
revision = 'v24_001'
down_revision = None  # ← ЗАМЕНИ на ID последней миграции v2 (alembic history)
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Добавляет все новые таблицы и колонки v24."""

    # ══════════════════════════════════════════════════════════
    # 1. Новая таблица: system_settings
    # ══════════════════════════════════════════════════════════
    op.create_table(
        'system_settings',
        sa.Column('key', sa.String(100), primary_key=True),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow),
    )

    # Начальные значения констант
    op.execute("""
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
    """)

    # ══════════════════════════════════════════════════════════
    # 2. Новая таблица: worker_violations
    # ══════════════════════════════════════════════════════════
    op.create_table(
        'worker_violations',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('worker_id', sa.Integer(), sa.ForeignKey('workers.id'), nullable=False),
        sa.Column('order_id', sa.Integer(), sa.ForeignKey('orders.id'), nullable=True),
        sa.Column('violation_type', sa.String(50), nullable=False),
        sa.Column('original_text', sa.Text(), nullable=False),
        sa.Column('filtered_text', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), default=datetime.utcnow),
    )
    op.create_index('ix_worker_violations_worker_id', 'worker_violations', ['worker_id'])

    # ══════════════════════════════════════════════════════════
    # 3. Новая таблица: seller_order_disputes
    # ══════════════════════════════════════════════════════════
    op.create_table(
        'seller_order_disputes',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('order_id', sa.Integer(), sa.ForeignKey('seller_orders.id'), nullable=False, unique=True),
        sa.Column('opened_by', sa.BigInteger(), nullable=False),
        sa.Column('reason', sa.String(50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(20), default='open'),
        sa.Column('resolution_note', sa.Text(), nullable=True),
        sa.Column('resolved_by', sa.BigInteger(), nullable=True),
        sa.Column('created_at', sa.DateTime(), default=datetime.utcnow),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
    )

    # ══════════════════════════════════════════════════════════
    # 4. Новые колонки в seller_orders
    # ══════════════════════════════════════════════════════════
    op.add_column('seller_orders', sa.Column('escrow_released', sa.Boolean(), default=False, server_default='false'))
    op.add_column('seller_orders', sa.Column('marketer_commission_paid', sa.Boolean(), default=False, server_default='false'))
    op.add_column('seller_orders', sa.Column('worker_paid', sa.Boolean(), default=False, server_default='false'))
    op.add_column('seller_orders', sa.Column('auto_complete_at', sa.DateTime(), nullable=True))
    op.add_column('seller_orders', sa.Column('dispute_deadline_at', sa.DateTime(), nullable=True))
    op.add_column('seller_orders', sa.Column('marketer_id', sa.Integer(), sa.ForeignKey('marketers.id'), nullable=True))
    op.add_column('seller_orders', sa.Column('marketer_commission_amount', sa.Numeric(10, 2), nullable=True))

    # ══════════════════════════════════════════════════════════
    # 5. Новые колонки в products
    # ══════════════════════════════════════════════════════════
    # Проверяем существование колонок перед добавлением
    # (некоторые могут уже быть в v2)
    try:
        op.add_column('products', sa.Column('is_active', sa.Boolean(), default=True, server_default='true'))
    except Exception:
        pass  # Колонка уже существует

    try:
        op.add_column('products', sa.Column('moderation_status', sa.String(30), default='pending_moderation', server_default='pending_moderation'))
    except Exception:
        pass

    try:
        op.add_column('products', sa.Column('moderation_comment', sa.Text(), nullable=True))
    except Exception:
        pass

    try:
        op.add_column('products', sa.Column('moderated_at', sa.DateTime(), nullable=True))
    except Exception:
        pass

    try:
        op.add_column('products', sa.Column('moderated_by', sa.BigInteger(), nullable=True))
    except Exception:
        pass

    # ══════════════════════════════════════════════════════════
    # 6. Новые колонки в workers
    # ══════════════════════════════════════════════════════════
    try:
        op.add_column('workers', sa.Column('violation_count', sa.Integer(), default=0, server_default='0'))
    except Exception:
        pass

    try:
        op.add_column('workers', sa.Column('is_suspended', sa.Boolean(), default=False, server_default='false'))
    except Exception:
        pass

    try:
        op.add_column('workers', sa.Column('suspended_at', sa.DateTime(), nullable=True))
    except Exception:
        pass

    try:
        op.add_column('workers', sa.Column('suspended_reason', sa.Text(), nullable=True))
    except Exception:
        pass

    # ══════════════════════════════════════════════════════════
    # 7. Новые колонки в users
    # ══════════════════════════════════════════════════════════
    try:
        op.add_column('users', sa.Column('language', sa.String(10), default='ru', server_default='ru'))
    except Exception:
        pass

    try:
        op.add_column('users', sa.Column('trust_score', sa.Integer(), default=100, server_default='100'))
    except Exception:
        pass

    try:
        op.add_column('users', sa.Column('last_active_at', sa.DateTime(), nullable=True))
    except Exception:
        pass

    # ══════════════════════════════════════════════════════════
    # 8. Индексы для производительности
    # ══════════════════════════════════════════════════════════
    op.create_index('ix_seller_orders_status', 'seller_orders', ['status'])
    op.create_index('ix_seller_orders_auto_complete', 'seller_orders', ['auto_complete_at'])
    op.create_index('ix_products_moderation_status', 'products', ['moderation_status'])
    op.create_index('ix_products_is_active', 'products', ['is_active'])


def downgrade() -> None:
    """Откатывает все изменения v24."""

    # Индексы
    op.drop_index('ix_seller_orders_status', 'seller_orders')
    op.drop_index('ix_seller_orders_auto_complete', 'seller_orders')
    op.drop_index('ix_products_moderation_status', 'products')
    op.drop_index('ix_products_is_active', 'products')

    # Колонки users
    op.drop_column('users', 'last_active_at')
    op.drop_column('users', 'trust_score')
    op.drop_column('users', 'language')

    # Колонки workers
    op.drop_column('workers', 'suspended_reason')
    op.drop_column('workers', 'suspended_at')
    op.drop_column('workers', 'is_suspended')
    op.drop_column('workers', 'violation_count')

    # Колонки products
    op.drop_column('products', 'moderated_by')
    op.drop_column('products', 'moderated_at')
    op.drop_column('products', 'moderation_comment')
    op.drop_column('products', 'moderation_status')
    op.drop_column('products', 'is_active')

    # Колонки seller_orders
    op.drop_column('seller_orders', 'marketer_commission_amount')
    op.drop_column('seller_orders', 'marketer_id')
    op.drop_column('seller_orders', 'dispute_deadline_at')
    op.drop_column('seller_orders', 'auto_complete_at')
    op.drop_column('seller_orders', 'worker_paid')
    op.drop_column('seller_orders', 'marketer_commission_paid')
    op.drop_column('seller_orders', 'escrow_released')

    # Таблицы
    op.drop_table('seller_order_disputes')
    op.drop_table('worker_violations')
    op.drop_table('system_settings')
