"""Mirror Bot Order Types + ETA migration artifact.

Adds:
- orders.order_type VARCHAR(20) DEFAULT 'order'
  Values: 'order' | 'order_catalog' | 'catalog'
  - order: fulfilled in real-time by a worker
  - order_catalog: worker loads catalog items or fulfills if not available
  - catalog: full catalog load (no user input required)
- orders.eta_minutes INTEGER NULLABLE
  Per-order ETA override; NULL means use category default from service_prices

- service_prices.order_type VARCHAR(20) DEFAULT 'order'
  Category-level default order type
- service_prices.eta_minutes INTEGER NULLABLE
  Category-level default ETA in minutes (NULL = use code constant)
- service_prices.service_link VARCHAR(500) NULLABLE
  External service URL (shown only for order / order_catalog types)

This repo applies schema changes imperatively at startup via session.py
_run_post_create_migrations(). Keep this file in sync.
"""

from alembic import op
import sqlalchemy as sa


revision = "mirror_orders_001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # orders table
    op.add_column("orders", sa.Column("order_type", sa.String(20), nullable=False, server_default="order"))
    op.add_column("orders", sa.Column("eta_minutes", sa.Integer(), nullable=True))

    # service_prices table
    op.add_column("service_prices", sa.Column("order_type", sa.String(20), nullable=False, server_default="order"))
    op.add_column("service_prices", sa.Column("eta_minutes", sa.Integer(), nullable=True))
    op.add_column("service_prices", sa.Column("service_link", sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column("service_prices", "service_link")
    op.drop_column("service_prices", "eta_minutes")
    op.drop_column("service_prices", "order_type")
    op.drop_column("orders", "eta_minutes")
    op.drop_column("orders", "order_type")
