"""Referral system migration: referrals, referral_rewards, referral_settings tables.

revision: referral_001
down_revision: v24_001
"""

from alembic import op
import sqlalchemy as sa
from decimal import Decimal

revision = "referral_001"
down_revision = "v24_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # referral_settings
    op.create_table(
        "referral_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("display_percent", sa.Float(), nullable=False),
        sa.Column("real_percent", sa.Float(), nullable=False),
        sa.Column("max_daily", sa.Integer(), nullable=True),
        sa.Column("cooldown_hours", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("level", name="uq_referral_settings_level"),
    )

    # referrals
    op.create_table(
        "referrals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("referrer_id", sa.BigInteger(), nullable=False),
        sa.Column("referred_id", sa.BigInteger(), nullable=False),
        sa.Column("source_bot", sa.String(50), nullable=True),
        sa.Column("level", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("referral_chain", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("referred_id", name="uq_referrals_referred_id"),
    )
    op.create_index("ix_referrals_referrer_id", "referrals", ["referrer_id"])
    op.create_index("ix_referrals_referred_id", "referrals", ["referred_id"])
    op.create_index("ix_referrals_created_at", "referrals", ["created_at"])
    op.create_index("ix_referrals_referrer_created", "referrals", ["referrer_id", "created_at"])

    # referral_rewards
    op.create_table(
        "referral_rewards",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("from_referral_id", sa.Integer(), sa.ForeignKey("referrals.id"), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("display_percent", sa.Float(), nullable=False),
        sa.Column("real_percent", sa.Float(), nullable=False),
        sa.Column("amount", sa.Numeric(10, 4), nullable=False),
        sa.Column("purchase_amount", sa.Numeric(10, 4), nullable=False, server_default="0"),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending_moderation"),
        sa.Column("reviewed_by", sa.BigInteger(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_referral_rewards_user_id", "referral_rewards", ["user_id"])
    op.create_index("ix_referral_rewards_created_at", "referral_rewards", ["created_at"])
    op.create_index("ix_referral_rewards_user_status", "referral_rewards", ["user_id", "status"])

    # Seed default settings
    op.execute(sa.text("""
        INSERT INTO referral_settings (level, display_percent, real_percent, max_daily, cooldown_hours, is_active, updated_at)
        VALUES
            (1, 15.0, 7.0,  100, 0, 1, CURRENT_TIMESTAMP),
            (2,  7.0, 3.0,  100, 0, 1, CURRENT_TIMESTAMP),
            (3,  3.0, 1.0,  100, 0, 1, CURRENT_TIMESTAMP),
            (4,  1.0, 0.2,  100, 0, 1, CURRENT_TIMESTAMP),
            (5,  0.5, 0.0,  100, 0, 1, CURRENT_TIMESTAMP)
    """))


def downgrade() -> None:
    op.drop_table("referral_rewards")
    op.drop_table("referrals")
    op.drop_table("referral_settings")
