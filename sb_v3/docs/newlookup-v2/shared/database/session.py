"""
Database session factory and imperative schema migrations.

NOTE: This file contains ~2000 lines of inline ALTER TABLE / CREATE INDEX
migrations in init_db() and _run_post_create_migrations(). This was a pragmatic
choice during rapid development, but for production stability consider:
  1. Freezing the current schema as the Alembic "initial" revision.
  2. Writing new migrations as proper Alembic versions.
  3. Gradually moving the inline migrations into Alembic history.
See docs/LAUNCH_RUNBOOK.md § "Existing DB Upgrade" for the current workflow.
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from dotenv import load_dotenv
from shared.database.models import Base
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://newlookup:tgbotnewlookup@postgres:5432/newlookup")

_is_sqlite = "sqlite" in DATABASE_URL

# Для PostgreSQL настраиваем пул соединений:
# - pool_size=10  : постоянно открытые соединения
# - max_overflow=20: дополнительные при пике
# - pool_timeout=30: ждать соединение не более 30 с
# - pool_pre_ping=True: проверять соединение перед выдачей (устраняет "hanging connections")
# - pool_recycle=1800: пересоздавать соединения каждые 30 минут (предотвращает "gone away")
_engine_kwargs: dict = dict(
    echo=False,
    pool_pre_ping=True,
)
if _is_sqlite:
    _engine_kwargs["poolclass"] = NullPool
else:
    _engine_kwargs.update(
        pool_size=10,
        max_overflow=20,
        pool_timeout=30,
        pool_recycle=1800,
    )

engine = create_async_engine(DATABASE_URL, **_engine_kwargs)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        from sqlalchemy import text
        for stmt_sqlite, stmt_pg in [
            (
                "ALTER TABLE transactions ADD COLUMN account_type VARCHAR(20) DEFAULT 'user'",
                "ALTER TABLE transactions ADD COLUMN IF NOT EXISTS account_type VARCHAR(20) DEFAULT 'user'",
            ),
            (
                "ALTER TABLE transactions ADD COLUMN account_id BIGINT",
                "ALTER TABLE transactions ADD COLUMN IF NOT EXISTS account_id BIGINT",
            ),
            (
                "ALTER TABLE transactions ADD COLUMN currency VARCHAR(10) DEFAULT 'USD'",
                "ALTER TABLE transactions ADD COLUMN IF NOT EXISTS currency VARCHAR(10) DEFAULT 'USD'",
            ),
            (
                "ALTER TABLE transactions ADD COLUMN status VARCHAR(20) DEFAULT 'completed'",
                "ALTER TABLE transactions ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'completed'",
            ),
            (
                "ALTER TABLE transactions ADD COLUMN related_entity_type VARCHAR(50)",
                "ALTER TABLE transactions ADD COLUMN IF NOT EXISTS related_entity_type VARCHAR(50)",
            ),
            (
                "ALTER TABLE transactions ADD COLUMN related_entity_id BIGINT",
                "ALTER TABLE transactions ADD COLUMN IF NOT EXISTS related_entity_id BIGINT",
            ),
            (
                "ALTER TABLE transactions ADD COLUMN effective_at TIMESTAMP",
                "ALTER TABLE transactions ADD COLUMN IF NOT EXISTS effective_at TIMESTAMP",
            ),
            (
                "ALTER TABLE transactions ADD COLUMN idempotency_key VARCHAR(120)",
                "ALTER TABLE transactions ADD COLUMN IF NOT EXISTS idempotency_key VARCHAR(120)",
            ),
            (
                "ALTER TABLE products ADD COLUMN base_price NUMERIC(10,2)",
                "ALTER TABLE products ADD COLUMN IF NOT EXISTS base_price NUMERIC(10,2)",
            ),
            (
                "ALTER TABLE products ADD COLUMN final_price NUMERIC(10,2)",
                "ALTER TABLE products ADD COLUMN IF NOT EXISTS final_price NUMERIC(10,2)",
            ),
            (
                "ALTER TABLE products ADD COLUMN markup_percent FLOAT",
                "ALTER TABLE products ADD COLUMN IF NOT EXISTS markup_percent FLOAT",
            ),
            (
                "ALTER TABLE products ADD COLUMN markup_fixed NUMERIC(10,2)",
                "ALTER TABLE products ADD COLUMN IF NOT EXISTS markup_fixed NUMERIC(10,2)",
            ),
            (
                "ALTER TABLE products ADD COLUMN moderation_status VARCHAR(30) DEFAULT 'pending_moderation'",
                "ALTER TABLE products ADD COLUMN IF NOT EXISTS moderation_status VARCHAR(30) DEFAULT 'pending_moderation'",
            ),
            (
                "ALTER TABLE products ADD COLUMN is_active BOOLEAN DEFAULT 1",
                "ALTER TABLE products ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE",
            ),
            (
                "ALTER TABLE products ADD COLUMN moderation_comment TEXT",
                "ALTER TABLE products ADD COLUMN IF NOT EXISTS moderation_comment TEXT",
            ),
            (
                "ALTER TABLE products ADD COLUMN moderated_at TIMESTAMP",
                "ALTER TABLE products ADD COLUMN IF NOT EXISTS moderated_at TIMESTAMP",
            ),
            (
                "ALTER TABLE products ADD COLUMN moderated_by BIGINT",
                "ALTER TABLE products ADD COLUMN IF NOT EXISTS moderated_by BIGINT",
            ),
            (
                "ALTER TABLE seller_withdrawals ADD COLUMN funds_reserved BOOLEAN DEFAULT 0",
                "ALTER TABLE seller_withdrawals ADD COLUMN IF NOT EXISTS funds_reserved BOOLEAN DEFAULT FALSE",
            ),
            (
                "ALTER TABLE worker_withdrawals ADD COLUMN funds_reserved BOOLEAN DEFAULT 0",
                "ALTER TABLE worker_withdrawals ADD COLUMN IF NOT EXISTS funds_reserved BOOLEAN DEFAULT FALSE",
            ),
            (
                "ALTER TABLE marketer_withdrawals ADD COLUMN funds_reserved BOOLEAN DEFAULT 0",
                "ALTER TABLE marketer_withdrawals ADD COLUMN IF NOT EXISTS funds_reserved BOOLEAN DEFAULT FALSE",
            ),
            (
                "ALTER TABLE bot_owner_withdrawals ADD COLUMN funds_reserved BOOLEAN DEFAULT 0",
                "ALTER TABLE bot_owner_withdrawals ADD COLUMN IF NOT EXISTS funds_reserved BOOLEAN DEFAULT FALSE",
            ),
            (
                "ALTER TABLE workers ADD COLUMN upload_categories JSON",
                "ALTER TABLE workers ADD COLUMN IF NOT EXISTS upload_categories JSONB",
            ),
            (
                "ALTER TABLE workers ADD COLUMN upload_services JSON",
                "ALTER TABLE workers ADD COLUMN IF NOT EXISTS upload_services JSONB",
            ),
            (
                "ALTER TABLE workers ADD COLUMN violation_count INTEGER DEFAULT 0",
                "ALTER TABLE workers ADD COLUMN IF NOT EXISTS violation_count INTEGER DEFAULT 0",
            ),
            (
                "ALTER TABLE workers ADD COLUMN is_suspended BOOLEAN DEFAULT 0",
                "ALTER TABLE workers ADD COLUMN IF NOT EXISTS is_suspended BOOLEAN DEFAULT FALSE",
            ),
            (
                "ALTER TABLE workers ADD COLUMN suspended_at TIMESTAMP",
                "ALTER TABLE workers ADD COLUMN IF NOT EXISTS suspended_at TIMESTAMP",
            ),
            (
                "ALTER TABLE workers ADD COLUMN suspended_reason TEXT",
                "ALTER TABLE workers ADD COLUMN IF NOT EXISTS suspended_reason TEXT",
            ),
            (
                "ALTER TABLE admins ADD COLUMN allowed_catalogs JSON",
                "ALTER TABLE admins ADD COLUMN IF NOT EXISTS allowed_catalogs JSONB",
            ),
            (
                "ALTER TABLE broadcasts ADD COLUMN buttons JSON",
                "ALTER TABLE broadcasts ADD COLUMN IF NOT EXISTS buttons JSONB",
            ),
        ]:
            try:
                if "sqlite" in DATABASE_URL:
                    await conn.execute(text(stmt_sqlite))
                elif "postgresql" in DATABASE_URL:
                    await conn.execute(text(stmt_pg))
            except Exception:
                pass

        try:
            await conn.execute(text("UPDATE transactions SET account_id = user_id WHERE account_id IS NULL"))
        except Exception:
            pass

        # Миграция: scheduled_at в broadcasts
        if "postgresql" in DATABASE_URL:
            try:
                await conn.execute(text(
                    "ALTER TABLE broadcasts ADD COLUMN IF NOT EXISTS scheduled_at TIMESTAMP"
                ))
            except Exception:
                pass
            try:
                await conn.execute(text(
                    "ALTER TABLE broadcasts ADD COLUMN IF NOT EXISTS audience VARCHAR(30) DEFAULT 'users'"
                ))
            except Exception:
                pass
        elif "sqlite" in DATABASE_URL:
            try:
                await conn.execute(text(
                    "ALTER TABLE broadcasts ADD COLUMN audience VARCHAR(30) DEFAULT 'users'"
                ))
            except Exception:
                pass
        # Миграция: seller_conversation_id в seller_chats
        try:
            if "sqlite" in DATABASE_URL:
                await conn.execute(text(
                    "ALTER TABLE seller_chats ADD COLUMN seller_conversation_id INTEGER"
                ))
            elif "postgresql" in DATABASE_URL:
                await conn.execute(text(
                    "ALTER TABLE seller_chats ADD COLUMN IF NOT EXISTS seller_conversation_id INTEGER REFERENCES seller_conversations(id)"
                ))
        except Exception:
            pass  # колонка уже есть

        # Миграции seller_banks / seller_orders для seller mini app и confirm flow
        try:
            if "sqlite" in DATABASE_URL:
                await conn.execute(text(
                    "ALTER TABLE seller_banks ADD COLUMN has_chat BOOLEAN DEFAULT 1"
                ))
            elif "postgresql" in DATABASE_URL:
                await conn.execute(text(
                    "ALTER TABLE seller_banks ADD COLUMN IF NOT EXISTS has_chat BOOLEAN DEFAULT TRUE"
                ))
        except Exception:
            pass

        for stmt_sqlite, stmt_pg in [
            (
                "ALTER TABLE sellers ADD COLUMN language VARCHAR(2) DEFAULT 'en'",
                "ALTER TABLE sellers ADD COLUMN IF NOT EXISTS language VARCHAR(2) DEFAULT 'en'",
            ),
            (
                "ALTER TABLE sellers ADD COLUMN rules_accepted BOOLEAN DEFAULT 0",
                "ALTER TABLE sellers ADD COLUMN IF NOT EXISTS rules_accepted BOOLEAN DEFAULT FALSE",
            ),
            (
                "ALTER TABLE sellers ADD COLUMN access_status VARCHAR(20) DEFAULT 'pending_deposit'",
                "ALTER TABLE sellers ADD COLUMN IF NOT EXISTS access_status VARCHAR(20) DEFAULT 'pending_deposit'",
            ),
            (
                "ALTER TABLE sellers ADD COLUMN pending_balance NUMERIC(10,2) DEFAULT 0",
                "ALTER TABLE sellers ADD COLUMN IF NOT EXISTS pending_balance NUMERIC(10,2) DEFAULT 0",
            ),
            (
                "ALTER TABLE sellers ADD COLUMN withdrawable_balance NUMERIC(10,2) DEFAULT 0",
                "ALTER TABLE sellers ADD COLUMN IF NOT EXISTS withdrawable_balance NUMERIC(10,2) DEFAULT 0",
            ),
            (
                "ALTER TABLE sellers ADD COLUMN security_deposit_balance NUMERIC(10,2) DEFAULT 0",
                "ALTER TABLE sellers ADD COLUMN IF NOT EXISTS security_deposit_balance NUMERIC(10,2) DEFAULT 0",
            ),
            (
                "ALTER TABLE sellers ADD COLUMN security_deposit_status VARCHAR(20) DEFAULT 'unpaid'",
                "ALTER TABLE sellers ADD COLUMN IF NOT EXISTS security_deposit_status VARCHAR(20) DEFAULT 'unpaid'",
            ),
            (
                "ALTER TABLE sellers ADD COLUMN security_deposit_categories JSON",
                "ALTER TABLE sellers ADD COLUMN IF NOT EXISTS security_deposit_categories JSONB",
            ),
            (
                "ALTER TABLE sellers ADD COLUMN security_deposit_paid_at TIMESTAMP",
                "ALTER TABLE sellers ADD COLUMN IF NOT EXISTS security_deposit_paid_at TIMESTAMP",
            ),
            (
                "ALTER TABLE sellers ADD COLUMN ban_reason TEXT",
                "ALTER TABLE sellers ADD COLUMN IF NOT EXISTS ban_reason TEXT",
            ),
            (
                "ALTER TABLE sellers ADD COLUMN is_banned_for_leak BOOLEAN DEFAULT 0",
                "ALTER TABLE sellers ADD COLUMN IF NOT EXISTS is_banned_for_leak BOOLEAN DEFAULT FALSE",
            ),
            (
                "ALTER TABLE sellers ADD COLUMN banned_at TIMESTAMP",
                "ALTER TABLE sellers ADD COLUMN IF NOT EXISTS banned_at TIMESTAMP",
            ),
            (
                "ALTER TABLE sellers ADD COLUMN banned_by BIGINT",
                "ALTER TABLE sellers ADD COLUMN IF NOT EXISTS banned_by BIGINT",
            ),
            (
                "ALTER TABLE sellers ADD COLUMN leave_requested_at TIMESTAMP",
                "ALTER TABLE sellers ADD COLUMN IF NOT EXISTS leave_requested_at TIMESTAMP",
            ),
            (
                "ALTER TABLE sellers ADD COLUMN left_at TIMESTAMP",
                "ALTER TABLE sellers ADD COLUMN IF NOT EXISTS left_at TIMESTAMP",
            ),
            (
                "ALTER TABLE sellers ADD COLUMN likes_count INTEGER DEFAULT 0",
                "ALTER TABLE sellers ADD COLUMN IF NOT EXISTS likes_count INTEGER DEFAULT 0",
            ),
            (
                "ALTER TABLE sellers ADD COLUMN dislikes_count INTEGER DEFAULT 0",
                "ALTER TABLE sellers ADD COLUMN IF NOT EXISTS dislikes_count INTEGER DEFAULT 0",
            ),
            (
                "ALTER TABLE seller_banks ADD COLUMN reserved_count INTEGER DEFAULT 0",
                "ALTER TABLE seller_banks ADD COLUMN IF NOT EXISTS reserved_count INTEGER DEFAULT 0",
            ),
            (
                "ALTER TABLE seller_orders ADD COLUMN reserved_quantity INTEGER DEFAULT 1",
                "ALTER TABLE seller_orders ADD COLUMN IF NOT EXISTS reserved_quantity INTEGER DEFAULT 1",
            ),
            (
                "ALTER TABLE seller_orders ADD COLUMN reserved_at TIMESTAMP",
                "ALTER TABLE seller_orders ADD COLUMN IF NOT EXISTS reserved_at TIMESTAMP",
            ),
            (
                "ALTER TABLE seller_orders ADD COLUMN reservation_expires_at TIMESTAMP",
                "ALTER TABLE seller_orders ADD COLUMN IF NOT EXISTS reservation_expires_at TIMESTAMP",
            ),
            (
                "ALTER TABLE seller_orders ADD COLUMN reservation_released_at TIMESTAMP",
                "ALTER TABLE seller_orders ADD COLUMN IF NOT EXISTS reservation_released_at TIMESTAMP",
            ),
            (
                "ALTER TABLE seller_orders ADD COLUMN check_window_minutes INTEGER DEFAULT 15",
                "ALTER TABLE seller_orders ADD COLUMN IF NOT EXISTS check_window_minutes INTEGER DEFAULT 15",
            ),
            (
                "ALTER TABLE seller_orders ADD COLUMN check_confirmed_at TIMESTAMP",
                "ALTER TABLE seller_orders ADD COLUMN IF NOT EXISTS check_confirmed_at TIMESTAMP",
            ),
            (
                "ALTER TABLE seller_orders ADD COLUMN check_started_at TIMESTAMP",
                "ALTER TABLE seller_orders ADD COLUMN IF NOT EXISTS check_started_at TIMESTAMP",
            ),
            (
                "ALTER TABLE seller_orders ADD COLUMN check_expires_at TIMESTAMP",
                "ALTER TABLE seller_orders ADD COLUMN IF NOT EXISTS check_expires_at TIMESTAMP",
            ),
            (
                "ALTER TABLE seller_orders ADD COLUMN buyer_rating VARCHAR(20)",
                "ALTER TABLE seller_orders ADD COLUMN IF NOT EXISTS buyer_rating VARCHAR(20)",
            ),
            (
                "ALTER TABLE seller_orders ADD COLUMN buyer_rating_at TIMESTAMP",
                "ALTER TABLE seller_orders ADD COLUMN IF NOT EXISTS buyer_rating_at TIMESTAMP",
            ),
            (
                "ALTER TABLE seller_orders ADD COLUMN buyer_rating_reason VARCHAR(100)",
                "ALTER TABLE seller_orders ADD COLUMN IF NOT EXISTS buyer_rating_reason VARCHAR(100)",
            ),
            (
                "ALTER TABLE seller_orders ADD COLUMN return_reason VARCHAR(100)",
                "ALTER TABLE seller_orders ADD COLUMN IF NOT EXISTS return_reason VARCHAR(100)",
            ),
            (
                "ALTER TABLE seller_orders ADD COLUMN return_reason_comment TEXT",
                "ALTER TABLE seller_orders ADD COLUMN IF NOT EXISTS return_reason_comment TEXT",
            ),
            (
                "ALTER TABLE seller_orders ADD COLUMN return_requested_at TIMESTAMP",
                "ALTER TABLE seller_orders ADD COLUMN IF NOT EXISTS return_requested_at TIMESTAMP",
            ),
            (
                "ALTER TABLE seller_orders ADD COLUMN pending_credited_at TIMESTAMP",
                "ALTER TABLE seller_orders ADD COLUMN IF NOT EXISTS pending_credited_at TIMESTAMP",
            ),
            (
                "ALTER TABLE seller_orders ADD COLUMN settled_at TIMESTAMP",
                "ALTER TABLE seller_orders ADD COLUMN IF NOT EXISTS settled_at TIMESTAMP",
            ),
            (
                "ALTER TABLE seller_orders ADD COLUMN returned_at TIMESTAMP",
                "ALTER TABLE seller_orders ADD COLUMN IF NOT EXISTS returned_at TIMESTAMP",
            ),
            (
                "ALTER TABLE seller_orders ADD COLUMN disputed_at TIMESTAMP",
                "ALTER TABLE seller_orders ADD COLUMN IF NOT EXISTS disputed_at TIMESTAMP",
            ),
            (
                "ALTER TABLE seller_orders ADD COLUMN escrow_released BOOLEAN DEFAULT 0",
                "ALTER TABLE seller_orders ADD COLUMN IF NOT EXISTS escrow_released BOOLEAN DEFAULT FALSE",
            ),
            (
                "ALTER TABLE seller_orders ADD COLUMN marketer_commission_paid BOOLEAN DEFAULT 0",
                "ALTER TABLE seller_orders ADD COLUMN IF NOT EXISTS marketer_commission_paid BOOLEAN DEFAULT FALSE",
            ),
            (
                "ALTER TABLE seller_orders ADD COLUMN worker_paid BOOLEAN DEFAULT 0",
                "ALTER TABLE seller_orders ADD COLUMN IF NOT EXISTS worker_paid BOOLEAN DEFAULT FALSE",
            ),
            (
                "ALTER TABLE seller_orders ADD COLUMN auto_complete_at TIMESTAMP",
                "ALTER TABLE seller_orders ADD COLUMN IF NOT EXISTS auto_complete_at TIMESTAMP",
            ),
            (
                "ALTER TABLE seller_orders ADD COLUMN dispute_deadline_at TIMESTAMP",
                "ALTER TABLE seller_orders ADD COLUMN IF NOT EXISTS dispute_deadline_at TIMESTAMP",
            ),
            (
                "ALTER TABLE seller_orders ADD COLUMN marketer_id INTEGER",
                "ALTER TABLE seller_orders ADD COLUMN IF NOT EXISTS marketer_id INTEGER REFERENCES marketers(id)",
            ),
            (
                "ALTER TABLE seller_orders ADD COLUMN marketer_commission_amount NUMERIC(10,2)",
                "ALTER TABLE seller_orders ADD COLUMN IF NOT EXISTS marketer_commission_amount NUMERIC(10,2)",
            ),
        ]:
            try:
                if "sqlite" in DATABASE_URL:
                    await conn.execute(text(stmt_sqlite))
                elif "postgresql" in DATABASE_URL:
                    await conn.execute(text(stmt_pg))
            except Exception:
                pass

        for stmt_sqlite, stmt_pg in [
            (
                "ALTER TABLE sellers ADD COLUMN is_on_vacation BOOLEAN DEFAULT 0",
                "ALTER TABLE sellers ADD COLUMN IF NOT EXISTS is_on_vacation BOOLEAN DEFAULT FALSE",
            ),
            (
                "ALTER TABLE sellers ADD COLUMN vacation_started_at TIMESTAMP",
                "ALTER TABLE sellers ADD COLUMN IF NOT EXISTS vacation_started_at TIMESTAMP",
            ),
            (
                "ALTER TABLE sellers ADD COLUMN vacation_ends_at TIMESTAMP",
                "ALTER TABLE sellers ADD COLUMN IF NOT EXISTS vacation_ends_at TIMESTAMP",
            ),
            (
                "ALTER TABLE seller_order_disputes ADD COLUMN seller_response_due_at TIMESTAMP",
                "ALTER TABLE seller_order_disputes ADD COLUMN IF NOT EXISTS seller_response_due_at TIMESTAMP",
            ),
            (
                "ALTER TABLE seller_order_disputes ADD COLUMN seller_responded_at TIMESTAMP",
                "ALTER TABLE seller_order_disputes ADD COLUMN IF NOT EXISTS seller_responded_at TIMESTAMP",
            ),
            (
                "ALTER TABLE seller_order_disputes ADD COLUMN buyer_evidence JSON",
                "ALTER TABLE seller_order_disputes ADD COLUMN IF NOT EXISTS buyer_evidence JSONB",
            ),
            (
                "ALTER TABLE seller_order_disputes ADD COLUMN seller_evidence JSON",
                "ALTER TABLE seller_order_disputes ADD COLUMN IF NOT EXISTS seller_evidence JSONB",
            ),
            (
                "ALTER TABLE seller_order_disputes ADD COLUMN assigned_admin_id BIGINT",
                "ALTER TABLE seller_order_disputes ADD COLUMN IF NOT EXISTS assigned_admin_id BIGINT",
            ),
            (
                "ALTER TABLE seller_order_disputes ADD COLUMN appeal_status VARCHAR(20)",
                "ALTER TABLE seller_order_disputes ADD COLUMN IF NOT EXISTS appeal_status VARCHAR(20)",
            ),
            (
                "ALTER TABLE seller_order_disputes ADD COLUMN appeal_reason TEXT",
                "ALTER TABLE seller_order_disputes ADD COLUMN IF NOT EXISTS appeal_reason TEXT",
            ),
            (
                "ALTER TABLE seller_order_disputes ADD COLUMN appeal_requested_at TIMESTAMP",
                "ALTER TABLE seller_order_disputes ADD COLUMN IF NOT EXISTS appeal_requested_at TIMESTAMP",
            ),
        ]:
            try:
                if "sqlite" in DATABASE_URL:
                    await conn.execute(text(stmt_sqlite))
                elif "postgresql" in DATABASE_URL:
                    await conn.execute(text(stmt_pg))
            except Exception:
                pass

        for stmt_sqlite, stmt_pg in [
            (
                "ALTER TABLE seller_upload_batches ADD COLUMN draft_payload JSON",
                "ALTER TABLE seller_upload_batches ADD COLUMN IF NOT EXISTS draft_payload JSONB",
            ),
            (
                "ALTER TABLE seller_upload_batches ADD COLUMN validation_summary JSON",
                "ALTER TABLE seller_upload_batches ADD COLUMN IF NOT EXISTS validation_summary JSONB",
            ),
            (
                "ALTER TABLE seller_upload_batches ADD COLUMN error_report JSON",
                "ALTER TABLE seller_upload_batches ADD COLUMN IF NOT EXISTS error_report JSONB",
            ),
            (
                "ALTER TABLE seller_upload_batches ADD COLUMN submitted_at TIMESTAMP",
                "ALTER TABLE seller_upload_batches ADD COLUMN IF NOT EXISTS submitted_at TIMESTAMP",
            ),
            (
                "ALTER TABLE seller_upload_batches ADD COLUMN reviewed_at TIMESTAMP",
                "ALTER TABLE seller_upload_batches ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMP",
            ),
            (
                "ALTER TABLE seller_upload_batches ADD COLUMN resubmitted_from_batch_id INTEGER REFERENCES seller_upload_batches(id)",
                "ALTER TABLE seller_upload_batches ADD COLUMN IF NOT EXISTS resubmitted_from_batch_id INTEGER REFERENCES seller_upload_batches(id)",
            ),
            (
                "ALTER TABLE seller_upload_batches ADD COLUMN approved_items INTEGER DEFAULT 0",
                "ALTER TABLE seller_upload_batches ADD COLUMN IF NOT EXISTS approved_items INTEGER DEFAULT 0",
            ),
            (
                "ALTER TABLE seller_upload_batches ADD COLUMN rejected_items INTEGER DEFAULT 0",
                "ALTER TABLE seller_upload_batches ADD COLUMN IF NOT EXISTS rejected_items INTEGER DEFAULT 0",
            ),
            (
                "ALTER TABLE seller_upload_batches ADD COLUMN changes_requested_items INTEGER DEFAULT 0",
                "ALTER TABLE seller_upload_batches ADD COLUMN IF NOT EXISTS changes_requested_items INTEGER DEFAULT 0",
            ),
            (
                "ALTER TABLE seller_upload_batches ADD COLUMN pending_items INTEGER DEFAULT 0",
                "ALTER TABLE seller_upload_batches ADD COLUMN IF NOT EXISTS pending_items INTEGER DEFAULT 0",
            ),
        ]:
            try:
                if "sqlite" in DATABASE_URL:
                    await conn.execute(text(stmt_sqlite))
                elif "postgresql" in DATABASE_URL:
                    await conn.execute(text(stmt_pg))
            except Exception:
                pass

        try:
            if "postgresql" in DATABASE_URL:
                await conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS seller_helpers (
                        id SERIAL PRIMARY KEY,
                        seller_id INTEGER NOT NULL REFERENCES sellers(id),
                        telegram_id BIGINT NOT NULL,
                        username VARCHAR(100),
                        display_name VARCHAR(200),
                        role VARCHAR(30) DEFAULT 'support_helper',
                        status VARCHAR(20) DEFAULT 'pending',
                        invited_by INTEGER REFERENCES sellers(id),
                        created_at TIMESTAMP DEFAULT NOW(),
                        joined_at TIMESTAMP,
                        blocked_at TIMESTAMP
                    )
                """))
                await conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS seller_helper_audit_logs (
                        id SERIAL PRIMARY KEY,
                        seller_id INTEGER NOT NULL REFERENCES sellers(id),
                        helper_id INTEGER REFERENCES seller_helpers(id),
                        action VARCHAR(80) NOT NULL,
                        object_type VARCHAR(50),
                        object_id INTEGER,
                        payload_json JSONB,
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                """))
            elif "sqlite" in DATABASE_URL:
                await conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS seller_helpers (
                        id INTEGER PRIMARY KEY,
                        seller_id INTEGER NOT NULL,
                        telegram_id BIGINT NOT NULL,
                        username VARCHAR(100),
                        display_name VARCHAR(200),
                        role VARCHAR(30) DEFAULT 'support_helper',
                        status VARCHAR(20) DEFAULT 'pending',
                        invited_by INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        joined_at TIMESTAMP,
                        blocked_at TIMESTAMP
                    )
                """))
                await conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS seller_helper_audit_logs (
                        id INTEGER PRIMARY KEY,
                        seller_id INTEGER NOT NULL,
                        helper_id INTEGER,
                        action VARCHAR(80) NOT NULL,
                        object_type VARCHAR(50),
                        object_id INTEGER,
                        payload_json JSON,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
        except Exception:
            pass

        try:
            if "postgresql" in DATABASE_URL:
                await conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS brute_bank_orders (
                        id SERIAL PRIMARY KEY,
                        brute_bank_item_id INTEGER NOT NULL REFERENCES brute_bank_items(id),
                        seller_id INTEGER NOT NULL REFERENCES sellers(id),
                        buyer_user_id BIGINT NOT NULL,
                        mirror_bot_id INTEGER REFERENCES mirror_bots(id),
                        status VARCHAR(20) DEFAULT 'completed',
                        price_for_buyer NUMERIC(10,2) NOT NULL,
                        price_for_seller NUMERIC(10,2) NOT NULL,
                        admin_notes TEXT,
                        created_at TIMESTAMP DEFAULT NOW(),
                        delivered_at TIMESTAMP,
                        settled_at TIMESTAMP
                    )
                """))
            elif "sqlite" in DATABASE_URL:
                await conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS brute_bank_orders (
                        id INTEGER PRIMARY KEY,
                        brute_bank_item_id INTEGER NOT NULL,
                        seller_id INTEGER NOT NULL,
                        buyer_user_id BIGINT NOT NULL,
                        mirror_bot_id INTEGER,
                        status VARCHAR(20) DEFAULT 'completed',
                        price_for_buyer NUMERIC(10,2) NOT NULL,
                        price_for_seller NUMERIC(10,2) NOT NULL,
                        admin_notes TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        delivered_at TIMESTAMP,
                        settled_at TIMESTAMP
                    )
                """))
        except Exception:
            pass

        try:
            if "postgresql" in DATABASE_URL:
                await conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS manual_deliveries (
                        id SERIAL PRIMARY KEY,
                        user_id BIGINT NOT NULL,
                        username VARCHAR(100),
                        manual_id INTEGER NOT NULL,
                        delivered_at TIMESTAMP DEFAULT NOW()
                    )
                """))
            elif "sqlite" in DATABASE_URL:
                await conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS manual_deliveries (
                        id INTEGER PRIMARY KEY,
                        user_id BIGINT NOT NULL,
                        username VARCHAR(100),
                        manual_id INTEGER NOT NULL,
                        delivered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
        except Exception:
            pass

    from shared.services.product_catalog_service import ProductCatalogManager
    from shared.services.menu_category_service import MenuCategoryService
    from shared.services.pricing_config_service import PricingConfigService

    async with async_session_maker() as session:
        await ProductCatalogManager.ensure_defaults(session)
        await MenuCategoryService.ensure_defaults(session)
        await PricingConfigService.ensure_defaults(session)

    await _run_post_create_migrations()
    await _seed_referral_settings()


async def _run_post_create_migrations():
    from sqlalchemy import text

    async with engine.begin() as conn:
        for stmt_sqlite, stmt_pg in [
            (
                "ALTER TABLE users ADD COLUMN language VARCHAR(10) DEFAULT 'ru'",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS language VARCHAR(10) DEFAULT 'ru'",
            ),
            (
                "ALTER TABLE users ADD COLUMN marketer_id INTEGER",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS marketer_id INTEGER REFERENCES marketers(id)",
            ),
            (
                "ALTER TABLE users ADD COLUMN first_topup_bonus_applied BOOLEAN DEFAULT 0",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS first_topup_bonus_applied BOOLEAN DEFAULT FALSE",
            ),
            (
                "ALTER TABLE users ADD COLUMN rules_accepted BOOLEAN DEFAULT 0",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS rules_accepted BOOLEAN DEFAULT FALSE",
            ),
            (
                "ALTER TABLE users ADD COLUMN active_coupon_code VARCHAR(60)",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS active_coupon_code VARCHAR(60)",
            ),
            (
                "ALTER TABLE users ADD COLUMN active_coupon_set_at TIMESTAMP",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS active_coupon_set_at TIMESTAMP",
            ),
            (
                "ALTER TABLE users ADD COLUMN trust_score INTEGER DEFAULT 100",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS trust_score INTEGER DEFAULT 100",
            ),
            (
                "ALTER TABLE users ADD COLUMN last_active_at TIMESTAMP",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS last_active_at TIMESTAMP",
            ),
            (
                "ALTER TABLE users ADD COLUMN archive_channel_id BIGINT",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS archive_channel_id BIGINT",
            ),
            (
                "ALTER TABLE marketers ADD COLUMN last_registration_milestone INTEGER DEFAULT 0",
                "ALTER TABLE marketers ADD COLUMN IF NOT EXISTS last_registration_milestone INTEGER DEFAULT 0",
            ),
            (
                "ALTER TABLE marketer_bot_links ADD COLUMN last_registration_milestone INTEGER DEFAULT 0",
                "ALTER TABLE marketer_bot_links ADD COLUMN IF NOT EXISTS last_registration_milestone INTEGER DEFAULT 0",
            ),
            (
                "ALTER TABLE marketers ADD COLUMN language VARCHAR(5) DEFAULT 'ru'",
                "ALTER TABLE marketers ADD COLUMN IF NOT EXISTS language VARCHAR(5) DEFAULT 'ru'",
            ),
            (
                "ALTER TABLE mirror_bots ADD COLUMN bot_type VARCHAR(20) DEFAULT 'user'",
                "ALTER TABLE mirror_bots ADD COLUMN IF NOT EXISTS bot_type VARCHAR(20) DEFAULT 'user'",
            ),
            (
                "ALTER TABLE marketers ADD COLUMN rules_accepted BOOLEAN DEFAULT 0",
                "ALTER TABLE marketers ADD COLUMN IF NOT EXISTS rules_accepted BOOLEAN DEFAULT FALSE",
            ),
        ]:
            try:
                if "sqlite" in DATABASE_URL:
                    await conn.execute(text(stmt_sqlite))
                elif "postgresql" in DATABASE_URL:
                    await conn.execute(text(stmt_pg))
            except Exception:
                pass

        try:
            await conn.execute(text(
                "UPDATE sellers SET access_status = 'active' WHERE is_approved = TRUE AND is_active = TRUE AND COALESCE(access_status, '') IN ('', 'pending_deposit')"
            ))
        except Exception:
            pass

        try:
            if "postgresql" in DATABASE_URL:
                await conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS seller_upload_batches (
                        id SERIAL PRIMARY KEY,
                        seller_id INTEGER NOT NULL REFERENCES sellers(id),
                        item_type VARCHAR(30) NOT NULL,
                        upload_mode VARCHAR(20) DEFAULT 'single',
                        title VARCHAR(200),
                        total_items INTEGER DEFAULT 1,
                        moderation_status VARCHAR(30) DEFAULT 'pending',
                        moderation_comment TEXT,
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW()
                    )
                """))
            elif "sqlite" in DATABASE_URL:
                await conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS seller_upload_batches (
                        id INTEGER PRIMARY KEY,
                        seller_id INTEGER NOT NULL,
                        item_type VARCHAR(30) NOT NULL,
                        upload_mode VARCHAR(20) DEFAULT 'single',
                        title VARCHAR(200),
                        total_items INTEGER DEFAULT 1,
                        moderation_status VARCHAR(30) DEFAULT 'pending',
                        moderation_comment TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
        except Exception:
            pass

        for table_name in ("seller_banks", "seller_cc_items", "brute_bank_items"):
            try:
                if "sqlite" in DATABASE_URL:
                    await conn.execute(text(
                        f"ALTER TABLE {table_name} ADD COLUMN upload_batch_id INTEGER"
                    ))
                elif "postgresql" in DATABASE_URL:
                    await conn.execute(text(
                        f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS upload_batch_id INTEGER REFERENCES seller_upload_batches(id)"
                    ))
            except Exception:
                pass

        for stmt_sqlite, stmt_pg in [
            (
                "ALTER TABLE seller_banks ADD COLUMN product_type VARCHAR(20) DEFAULT 'bank'",
                "ALTER TABLE seller_banks ADD COLUMN IF NOT EXISTS product_type VARCHAR(20) DEFAULT 'bank'",
            ),
            (
                "ALTER TABLE seller_banks ADD COLUMN product_subtype VARCHAR(30) DEFAULT 'log'",
                "ALTER TABLE seller_banks ADD COLUMN IF NOT EXISTS product_subtype VARCHAR(30) DEFAULT 'log'",
            ),
            (
                "ALTER TABLE seller_banks ADD COLUMN base_price NUMERIC(10,2)",
                "ALTER TABLE seller_banks ADD COLUMN IF NOT EXISTS base_price NUMERIC(10,2)",
            ),
            (
                "ALTER TABLE seller_banks ADD COLUMN final_price NUMERIC(10,2)",
                "ALTER TABLE seller_banks ADD COLUMN IF NOT EXISTS final_price NUMERIC(10,2)",
            ),
            (
                "ALTER TABLE seller_banks ADD COLUMN markup_percent FLOAT",
                "ALTER TABLE seller_banks ADD COLUMN IF NOT EXISTS markup_percent FLOAT",
            ),
            (
                "ALTER TABLE seller_banks ADD COLUMN markup_fixed NUMERIC(10,2)",
                "ALTER TABLE seller_banks ADD COLUMN IF NOT EXISTS markup_fixed NUMERIC(10,2)",
            ),
            (
                "ALTER TABLE seller_banks ADD COLUMN markup_code VARCHAR(50)",
                "ALTER TABLE seller_banks ADD COLUMN IF NOT EXISTS markup_code VARCHAR(50)",
            ),
            (
                "ALTER TABLE seller_banks ADD COLUMN markup_kind VARCHAR(20)",
                "ALTER TABLE seller_banks ADD COLUMN IF NOT EXISTS markup_kind VARCHAR(20)",
            ),
            (
                "ALTER TABLE seller_banks ADD COLUMN markup_value NUMERIC(10,2)",
                "ALTER TABLE seller_banks ADD COLUMN IF NOT EXISTS markup_value NUMERIC(10,2)",
            ),
            (
                "ALTER TABLE seller_banks ADD COLUMN instruction TEXT",
                "ALTER TABLE seller_banks ADD COLUMN IF NOT EXISTS instruction TEXT",
            ),
            (
                "ALTER TABLE seller_banks ADD COLUMN number_access_available BOOLEAN DEFAULT 0",
                "ALTER TABLE seller_banks ADD COLUMN IF NOT EXISTS number_access_available BOOLEAN DEFAULT FALSE",
            ),
            (
                "ALTER TABLE seller_banks ADD COLUMN rental_days INTEGER",
                "ALTER TABLE seller_banks ADD COLUMN IF NOT EXISTS rental_days INTEGER",
            ),
            (
                "ALTER TABLE seller_banks ADD COLUMN adaptive_report_enabled BOOLEAN DEFAULT 0",
                "ALTER TABLE seller_banks ADD COLUMN IF NOT EXISTS adaptive_report_enabled BOOLEAN DEFAULT FALSE",
            ),
            (
                "ALTER TABLE seller_banks ADD COLUMN number_change_allowed BOOLEAN DEFAULT 0",
                "ALTER TABLE seller_banks ADD COLUMN IF NOT EXISTS number_change_allowed BOOLEAN DEFAULT FALSE",
            ),
            (
                "ALTER TABLE seller_banks ADD COLUMN auto_unpublish_enabled BOOLEAN DEFAULT 0",
                "ALTER TABLE seller_banks ADD COLUMN IF NOT EXISTS auto_unpublish_enabled BOOLEAN DEFAULT FALSE",
            ),
            (
                "ALTER TABLE seller_banks ADD COLUMN listing_duration_days INTEGER",
                "ALTER TABLE seller_banks ADD COLUMN IF NOT EXISTS listing_duration_days INTEGER",
            ),
            (
                "ALTER TABLE seller_banks ADD COLUMN auto_unpublish_at TIMESTAMP",
                "ALTER TABLE seller_banks ADD COLUMN IF NOT EXISTS auto_unpublish_at TIMESTAMP",
            ),
            (
                "ALTER TABLE seller_orders ADD COLUMN product_type VARCHAR(20) DEFAULT 'bank'",
                "ALTER TABLE seller_orders ADD COLUMN IF NOT EXISTS product_type VARCHAR(20) DEFAULT 'bank'",
            ),
            (
                "ALTER TABLE seller_orders ADD COLUMN product_subtype VARCHAR(30) DEFAULT 'log'",
                "ALTER TABLE seller_orders ADD COLUMN IF NOT EXISTS product_subtype VARCHAR(30) DEFAULT 'log'",
            ),
            (
                "ALTER TABLE seller_orders ADD COLUMN assigned_helper_id INTEGER",
                "ALTER TABLE seller_orders ADD COLUMN IF NOT EXISTS assigned_helper_id INTEGER REFERENCES seller_helpers(id)",
            ),
            (
                "ALTER TABLE seller_orders ADD COLUMN assigned_at TIMESTAMP",
                "ALTER TABLE seller_orders ADD COLUMN IF NOT EXISTS assigned_at TIMESTAMP",
            ),
            (
                "ALTER TABLE seller_orders ADD COLUMN assigned_by BIGINT",
                "ALTER TABLE seller_orders ADD COLUMN IF NOT EXISTS assigned_by BIGINT",
            ),
            (
                "ALTER TABLE seller_cc_items ADD COLUMN product_type VARCHAR(20) DEFAULT 'cc'",
                "ALTER TABLE seller_cc_items ADD COLUMN IF NOT EXISTS product_type VARCHAR(20) DEFAULT 'cc'",
            ),
            (
                "ALTER TABLE seller_cc_items ADD COLUMN product_subtype VARCHAR(30) DEFAULT 'with_fullz'",
                "ALTER TABLE seller_cc_items ADD COLUMN IF NOT EXISTS product_subtype VARCHAR(30) DEFAULT 'with_fullz'",
            ),
            (
                "ALTER TABLE seller_cc_items ADD COLUMN base_price NUMERIC(10,2)",
                "ALTER TABLE seller_cc_items ADD COLUMN IF NOT EXISTS base_price NUMERIC(10,2)",
            ),
            (
                "ALTER TABLE seller_cc_items ADD COLUMN final_price NUMERIC(10,2)",
                "ALTER TABLE seller_cc_items ADD COLUMN IF NOT EXISTS final_price NUMERIC(10,2)",
            ),
            (
                "ALTER TABLE seller_cc_items ADD COLUMN markup_percent FLOAT",
                "ALTER TABLE seller_cc_items ADD COLUMN IF NOT EXISTS markup_percent FLOAT",
            ),
            (
                "ALTER TABLE seller_cc_items ADD COLUMN markup_fixed NUMERIC(10,2)",
                "ALTER TABLE seller_cc_items ADD COLUMN IF NOT EXISTS markup_fixed NUMERIC(10,2)",
            ),
            (
                "ALTER TABLE seller_cc_items ADD COLUMN markup_code VARCHAR(50)",
                "ALTER TABLE seller_cc_items ADD COLUMN IF NOT EXISTS markup_code VARCHAR(50)",
            ),
            (
                "ALTER TABLE seller_cc_items ADD COLUMN markup_kind VARCHAR(20)",
                "ALTER TABLE seller_cc_items ADD COLUMN IF NOT EXISTS markup_kind VARCHAR(20)",
            ),
            (
                "ALTER TABLE seller_cc_items ADD COLUMN markup_value NUMERIC(10,2)",
                "ALTER TABLE seller_cc_items ADD COLUMN IF NOT EXISTS markup_value NUMERIC(10,2)",
            ),
            (
                "ALTER TABLE seller_cc_items ADD COLUMN instruction TEXT",
                "ALTER TABLE seller_cc_items ADD COLUMN IF NOT EXISTS instruction TEXT",
            ),
            (
                "ALTER TABLE seller_cc_orders ADD COLUMN product_type VARCHAR(20) DEFAULT 'cc'",
                "ALTER TABLE seller_cc_orders ADD COLUMN IF NOT EXISTS product_type VARCHAR(20) DEFAULT 'cc'",
            ),
            (
                "ALTER TABLE seller_cc_orders ADD COLUMN product_subtype VARCHAR(30) DEFAULT 'with_fullz'",
                "ALTER TABLE seller_cc_orders ADD COLUMN IF NOT EXISTS product_subtype VARCHAR(30) DEFAULT 'with_fullz'",
            ),
            (
                "ALTER TABLE brute_bank_items ADD COLUMN product_type VARCHAR(20) DEFAULT 'bank'",
                "ALTER TABLE brute_bank_items ADD COLUMN IF NOT EXISTS product_type VARCHAR(20) DEFAULT 'bank'",
            ),
            (
                "ALTER TABLE brute_bank_items ADD COLUMN product_subtype VARCHAR(30) DEFAULT 'brute'",
                "ALTER TABLE brute_bank_items ADD COLUMN IF NOT EXISTS product_subtype VARCHAR(30) DEFAULT 'brute'",
            ),
        ]:
            try:
                if "sqlite" in DATABASE_URL:
                    await conn.execute(text(stmt_sqlite))
                elif "postgresql" in DATABASE_URL:
                    await conn.execute(text(stmt_pg))
            except Exception:
                pass

        for stmt in [
            "UPDATE products SET base_price = COALESCE(base_price, price) WHERE price IS NOT NULL",
            "UPDATE products SET final_price = COALESCE(final_price, price) WHERE price IS NOT NULL",
            "UPDATE products SET moderation_status = COALESCE(NULLIF(moderation_status, ''), 'pending_moderation')",
            "UPDATE seller_banks SET base_price = COALESCE(base_price, seller_price) WHERE seller_price IS NOT NULL",
            "UPDATE seller_banks SET final_price = COALESCE(final_price, buyer_price, seller_price) WHERE seller_price IS NOT NULL",
            "UPDATE seller_cc_items SET base_price = COALESCE(base_price, seller_price) WHERE seller_price IS NOT NULL",
            "UPDATE seller_cc_items SET final_price = COALESCE(final_price, buyer_price, seller_price) WHERE seller_price IS NOT NULL",
        ]:
            try:
                await conn.execute(text(stmt))
            except Exception:
                pass

        for stmt_sqlite, stmt_pg in [
            (
                "ALTER TABLE seller_conversations ADD COLUMN assigned_helper_id INTEGER",
                "ALTER TABLE seller_conversations ADD COLUMN IF NOT EXISTS assigned_helper_id INTEGER REFERENCES seller_helpers(id)",
            ),
            (
                "ALTER TABLE seller_conversations ADD COLUMN assigned_at TIMESTAMP",
                "ALTER TABLE seller_conversations ADD COLUMN IF NOT EXISTS assigned_at TIMESTAMP",
            ),
            (
                "ALTER TABLE seller_conversations ADD COLUMN assigned_by BIGINT",
                "ALTER TABLE seller_conversations ADD COLUMN IF NOT EXISTS assigned_by BIGINT",
            ),
        ]:
            try:
                if "sqlite" in DATABASE_URL:
                    await conn.execute(text(stmt_sqlite))
                elif "postgresql" in DATABASE_URL:
                    await conn.execute(text(stmt_pg))
            except Exception:
                pass

        for stmt_sqlite, stmt_pg in [
            (
                "ALTER TABLE bot_owner_withdrawals ADD COLUMN payment_method VARCHAR(20)",
                "ALTER TABLE bot_owner_withdrawals ADD COLUMN IF NOT EXISTS payment_method VARCHAR(20)",
            ),
            (
                "ALTER TABLE bot_owner_withdrawals ADD COLUMN payment_network VARCHAR(20)",
                "ALTER TABLE bot_owner_withdrawals ADD COLUMN IF NOT EXISTS payment_network VARCHAR(20)",
            ),
            (
                "ALTER TABLE bot_owner_withdrawals ADD COLUMN tx_hash TEXT",
                "ALTER TABLE bot_owner_withdrawals ADD COLUMN IF NOT EXISTS tx_hash TEXT",
            ),
            (
                "ALTER TABLE bot_owner_withdrawals ADD COLUMN reject_reason TEXT",
                "ALTER TABLE bot_owner_withdrawals ADD COLUMN IF NOT EXISTS reject_reason TEXT",
            ),
        ]:
            try:
                if "sqlite" in DATABASE_URL:
                    await conn.execute(text(stmt_sqlite))
                elif "postgresql" in DATABASE_URL:
                    await conn.execute(text(stmt_pg))
            except Exception:
                pass

        for stmt_sqlite, stmt_pg in [
            (
                "ALTER TABLE workers ADD COLUMN fixed_price NUMERIC(10,2)",
                "ALTER TABLE workers ADD COLUMN IF NOT EXISTS fixed_price NUMERIC(10,2)",
            ),
            (
                "ALTER TABLE workers ADD COLUMN commission_percent FLOAT",
                "ALTER TABLE workers ADD COLUMN IF NOT EXISTS commission_percent FLOAT",
            ),
            (
                "ALTER TABLE workers ADD COLUMN total_earned NUMERIC(10,2) DEFAULT 0",
                "ALTER TABLE workers ADD COLUMN IF NOT EXISTS total_earned NUMERIC(10,2) DEFAULT 0",
            ),
            (
                "ALTER TABLE workers ADD COLUMN total_withdrawn NUMERIC(10,2) DEFAULT 0",
                "ALTER TABLE workers ADD COLUMN IF NOT EXISTS total_withdrawn NUMERIC(10,2) DEFAULT 0",
            ),
        ]:
            try:
                if "sqlite" in DATABASE_URL:
                    await conn.execute(text(stmt_sqlite))
                elif "postgresql" in DATABASE_URL:
                    await conn.execute(text(stmt_pg))
            except Exception:
                pass

        for stmt_sqlite, stmt_pg in [
            (
                "ALTER TABLE seller_nfc_items ADD COLUMN final_price NUMERIC(10,2)",
                "ALTER TABLE seller_nfc_items ADD COLUMN IF NOT EXISTS final_price NUMERIC(10,2)",
            ),
            (
                "ALTER TABLE seller_nfc_items ADD COLUMN markup_percent FLOAT",
                "ALTER TABLE seller_nfc_items ADD COLUMN IF NOT EXISTS markup_percent FLOAT",
            ),
            (
                "ALTER TABLE seller_nfc_items ADD COLUMN markup_fixed NUMERIC(10,2)",
                "ALTER TABLE seller_nfc_items ADD COLUMN IF NOT EXISTS markup_fixed NUMERIC(10,2)",
            ),
            (
                "ALTER TABLE seller_otp_items ADD COLUMN final_price NUMERIC(10,2)",
                "ALTER TABLE seller_otp_items ADD COLUMN IF NOT EXISTS final_price NUMERIC(10,2)",
            ),
            (
                "ALTER TABLE seller_otp_items ADD COLUMN markup_percent FLOAT",
                "ALTER TABLE seller_otp_items ADD COLUMN IF NOT EXISTS markup_percent FLOAT",
            ),
            (
                "ALTER TABLE seller_otp_items ADD COLUMN markup_fixed NUMERIC(10,2)",
                "ALTER TABLE seller_otp_items ADD COLUMN IF NOT EXISTS markup_fixed NUMERIC(10,2)",
            ),
            (
                "ALTER TABLE seller_selfreg_cc_items ADD COLUMN final_price NUMERIC(10,2)",
                "ALTER TABLE seller_selfreg_cc_items ADD COLUMN IF NOT EXISTS final_price NUMERIC(10,2)",
            ),
            (
                "ALTER TABLE seller_selfreg_cc_items ADD COLUMN markup_percent FLOAT",
                "ALTER TABLE seller_selfreg_cc_items ADD COLUMN IF NOT EXISTS markup_percent FLOAT",
            ),
            (
                "ALTER TABLE seller_selfreg_cc_items ADD COLUMN markup_fixed NUMERIC(10,2)",
                "ALTER TABLE seller_selfreg_cc_items ADD COLUMN IF NOT EXISTS markup_fixed NUMERIC(10,2)",
            ),
            (
                "ALTER TABLE seller_check_items ADD COLUMN final_price NUMERIC(10,2)",
                "ALTER TABLE seller_check_items ADD COLUMN IF NOT EXISTS final_price NUMERIC(10,2)",
            ),
            (
                "ALTER TABLE seller_check_items ADD COLUMN markup_percent FLOAT",
                "ALTER TABLE seller_check_items ADD COLUMN IF NOT EXISTS markup_percent FLOAT",
            ),
            (
                "ALTER TABLE seller_check_items ADD COLUMN markup_fixed NUMERIC(10,2)",
                "ALTER TABLE seller_check_items ADD COLUMN IF NOT EXISTS markup_fixed NUMERIC(10,2)",
            ),
            (
                "ALTER TABLE brute_bank_items ADD COLUMN group_id INTEGER REFERENCES brute_bank_groups(id)",
                "ALTER TABLE brute_bank_items ADD COLUMN IF NOT EXISTS group_id INTEGER REFERENCES brute_bank_groups(id)",
            ),
            (
                "ALTER TABLE brute_bank_items ADD COLUMN balance_range VARCHAR(50)",
                "ALTER TABLE brute_bank_items ADD COLUMN IF NOT EXISTS balance_range VARCHAR(50)",
            ),
            (
                "ALTER TABLE brute_bank_items ADD COLUMN account_type VARCHAR(50)",
                "ALTER TABLE brute_bank_items ADD COLUMN IF NOT EXISTS account_type VARCHAR(50)",
            ),
        ]:
            try:
                if "sqlite" in DATABASE_URL:
                    await conn.execute(text(stmt_sqlite))
                elif "postgresql" in DATABASE_URL:
                    await conn.execute(text(stmt_pg))
            except Exception:
                pass

        for stmt_sqlite, stmt_pg in [
            (
                "ALTER TABLE orders ADD COLUMN feedback_status VARCHAR(20)",
                "ALTER TABLE orders ADD COLUMN IF NOT EXISTS feedback_status VARCHAR(20)",
            ),
            (
                "ALTER TABLE orders ADD COLUMN feedback_at TIMESTAMP",
                "ALTER TABLE orders ADD COLUMN IF NOT EXISTS feedback_at TIMESTAMP",
            ),
            (
                "ALTER TABLE orders ADD COLUMN report_status VARCHAR(20)",
                "ALTER TABLE orders ADD COLUMN IF NOT EXISTS report_status VARCHAR(20)",
            ),
            (
                "ALTER TABLE orders ADD COLUMN reported_at TIMESTAMP",
                "ALTER TABLE orders ADD COLUMN IF NOT EXISTS reported_at TIMESTAMP",
            ),
            (
                "ALTER TABLE orders ADD COLUMN original_price NUMERIC(10,2)",
                "ALTER TABLE orders ADD COLUMN IF NOT EXISTS original_price NUMERIC(10,2)",
            ),
            (
                "ALTER TABLE orders ADD COLUMN coupon_code VARCHAR(60)",
                "ALTER TABLE orders ADD COLUMN IF NOT EXISTS coupon_code VARCHAR(60)",
            ),
            (
                "ALTER TABLE orders ADD COLUMN discount_amount NUMERIC(10,2)",
                "ALTER TABLE orders ADD COLUMN IF NOT EXISTS discount_amount NUMERIC(10,2)",
            ),
            (
                "ALTER TABLE orders ADD COLUMN last_worker_reminder_at TIMESTAMP",
                "ALTER TABLE orders ADD COLUMN IF NOT EXISTS last_worker_reminder_at TIMESTAMP",
            ),
            (
                "ALTER TABLE seller_orders ADD COLUMN feedback_status VARCHAR(20)",
                "ALTER TABLE seller_orders ADD COLUMN IF NOT EXISTS feedback_status VARCHAR(20)",
            ),
            (
                "ALTER TABLE seller_orders ADD COLUMN feedback_at TIMESTAMP",
                "ALTER TABLE seller_orders ADD COLUMN IF NOT EXISTS feedback_at TIMESTAMP",
            ),
            (
                "ALTER TABLE seller_orders ADD COLUMN report_status VARCHAR(20)",
                "ALTER TABLE seller_orders ADD COLUMN IF NOT EXISTS report_status VARCHAR(20)",
            ),
            (
                "ALTER TABLE seller_orders ADD COLUMN reported_at TIMESTAMP",
                "ALTER TABLE seller_orders ADD COLUMN IF NOT EXISTS reported_at TIMESTAMP",
            ),
            (
                "ALTER TABLE seller_conversations ADD COLUMN source_order_type VARCHAR(30)",
                "ALTER TABLE seller_conversations ADD COLUMN IF NOT EXISTS source_order_type VARCHAR(30)",
            ),
            (
                "ALTER TABLE seller_conversations ADD COLUMN source_order_id INTEGER",
                "ALTER TABLE seller_conversations ADD COLUMN IF NOT EXISTS source_order_id INTEGER",
            ),
            (
                "ALTER TABLE seller_banks ADD COLUMN state VARCHAR(50)",
                "ALTER TABLE seller_banks ADD COLUMN IF NOT EXISTS state VARCHAR(50)",
            ),
            (
                "ALTER TABLE seller_banks ADD COLUMN zip VARCHAR(20)",
                "ALTER TABLE seller_banks ADD COLUMN IF NOT EXISTS zip VARCHAR(20)",
            ),
            (
                "ALTER TABLE seller_banks ADD COLUMN portal VARCHAR(120)",
                "ALTER TABLE seller_banks ADD COLUMN IF NOT EXISTS portal VARCHAR(120)",
            ),
            (
                "ALTER TABLE seller_banks ADD COLUMN card_type VARCHAR(50)",
                "ALTER TABLE seller_banks ADD COLUMN IF NOT EXISTS card_type VARCHAR(50)",
            ),
            (
                "ALTER TABLE seller_banks ADD COLUMN has_ssn BOOLEAN DEFAULT 0",
                "ALTER TABLE seller_banks ADD COLUMN IF NOT EXISTS has_ssn BOOLEAN DEFAULT FALSE",
            ),
            (
                "ALTER TABLE seller_banks ADD COLUMN has_dob BOOLEAN DEFAULT 0",
                "ALTER TABLE seller_banks ADD COLUMN IF NOT EXISTS has_dob BOOLEAN DEFAULT FALSE",
            ),
            (
                "ALTER TABLE seller_banks ADD COLUMN has_name BOOLEAN DEFAULT 0",
                "ALTER TABLE seller_banks ADD COLUMN IF NOT EXISTS has_name BOOLEAN DEFAULT FALSE",
            ),
            (
                "ALTER TABLE seller_banks ADD COLUMN has_address BOOLEAN DEFAULT 0",
                "ALTER TABLE seller_banks ADD COLUMN IF NOT EXISTS has_address BOOLEAN DEFAULT FALSE",
            ),
            (
                "ALTER TABLE seller_banks ADD COLUMN has_email BOOLEAN DEFAULT 0",
                "ALTER TABLE seller_banks ADD COLUMN IF NOT EXISTS has_email BOOLEAN DEFAULT FALSE",
            ),
            (
                "ALTER TABLE seller_banks ADD COLUMN has_security_qa BOOLEAN DEFAULT 0",
                "ALTER TABLE seller_banks ADD COLUMN IF NOT EXISTS has_security_qa BOOLEAN DEFAULT FALSE",
            ),
            (
                "ALTER TABLE seller_banks ADD COLUMN has_docs BOOLEAN DEFAULT 0",
                "ALTER TABLE seller_banks ADD COLUMN IF NOT EXISTS has_docs BOOLEAN DEFAULT FALSE",
            ),
            (
                "ALTER TABLE seller_banks ADD COLUMN doc_type VARCHAR(80)",
                "ALTER TABLE seller_banks ADD COLUMN IF NOT EXISTS doc_type VARCHAR(80)",
            ),
            (
                "ALTER TABLE seller_banks ADD COLUMN phone_area_code VARCHAR(10)",
                "ALTER TABLE seller_banks ADD COLUMN IF NOT EXISTS phone_area_code VARCHAR(10)",
            ),
            (
                "ALTER TABLE seller_banks ADD COLUMN details JSON",
                "ALTER TABLE seller_banks ADD COLUMN IF NOT EXISTS details JSONB",
            ),
            (
                "ALTER TABLE seller_cc_items ADD COLUMN number VARCHAR(32)",
                "ALTER TABLE seller_cc_items ADD COLUMN IF NOT EXISTS number VARCHAR(32)",
            ),
            (
                "ALTER TABLE seller_cc_items ADD COLUMN exp_mm INTEGER",
                "ALTER TABLE seller_cc_items ADD COLUMN IF NOT EXISTS exp_mm INTEGER",
            ),
            (
                "ALTER TABLE seller_cc_items ADD COLUMN exp_yyyy INTEGER",
                "ALTER TABLE seller_cc_items ADD COLUMN IF NOT EXISTS exp_yyyy INTEGER",
            ),
            (
                "ALTER TABLE seller_cc_items ADD COLUMN cvv VARCHAR(10)",
                "ALTER TABLE seller_cc_items ADD COLUMN IF NOT EXISTS cvv VARCHAR(10)",
            ),
            (
                "ALTER TABLE seller_cc_items ADD COLUMN fname VARCHAR(120)",
                "ALTER TABLE seller_cc_items ADD COLUMN IF NOT EXISTS fname VARCHAR(120)",
            ),
            (
                "ALTER TABLE seller_cc_items ADD COLUMN lname VARCHAR(120)",
                "ALTER TABLE seller_cc_items ADD COLUMN IF NOT EXISTS lname VARCHAR(120)",
            ),
            (
                "ALTER TABLE seller_cc_items ADD COLUMN address VARCHAR(255)",
                "ALTER TABLE seller_cc_items ADD COLUMN IF NOT EXISTS address VARCHAR(255)",
            ),
            (
                "ALTER TABLE seller_cc_items ADD COLUMN city VARCHAR(120)",
                "ALTER TABLE seller_cc_items ADD COLUMN IF NOT EXISTS city VARCHAR(120)",
            ),
            (
                "ALTER TABLE seller_cc_items ADD COLUMN state VARCHAR(50)",
                "ALTER TABLE seller_cc_items ADD COLUMN IF NOT EXISTS state VARCHAR(50)",
            ),
            (
                "ALTER TABLE seller_cc_items ADD COLUMN zip VARCHAR(20)",
                "ALTER TABLE seller_cc_items ADD COLUMN IF NOT EXISTS zip VARCHAR(20)",
            ),
            (
                "ALTER TABLE seller_cc_items ADD COLUMN country VARCHAR(10)",
                "ALTER TABLE seller_cc_items ADD COLUMN IF NOT EXISTS country VARCHAR(10)",
            ),
            (
                "ALTER TABLE seller_cc_items ADD COLUMN bank_name VARCHAR(120)",
                "ALTER TABLE seller_cc_items ADD COLUMN IF NOT EXISTS bank_name VARCHAR(120)",
            ),
            (
                "ALTER TABLE seller_cc_items ADD COLUMN card_brand VARCHAR(50)",
                "ALTER TABLE seller_cc_items ADD COLUMN IF NOT EXISTS card_brand VARCHAR(50)",
            ),
            (
                "ALTER TABLE seller_cc_items ADD COLUMN card_level VARCHAR(50)",
                "ALTER TABLE seller_cc_items ADD COLUMN IF NOT EXISTS card_level VARCHAR(50)",
            ),
            (
                "ALTER TABLE seller_cc_items ADD COLUMN is_non_vbv BOOLEAN DEFAULT 0",
                "ALTER TABLE seller_cc_items ADD COLUMN IF NOT EXISTS is_non_vbv BOOLEAN DEFAULT FALSE",
            ),
            (
                "ALTER TABLE seller_cc_items ADD COLUMN has_fullz BOOLEAN DEFAULT 0",
                "ALTER TABLE seller_cc_items ADD COLUMN IF NOT EXISTS has_fullz BOOLEAN DEFAULT FALSE",
            ),
            (
                "ALTER TABLE seller_cc_orders ADD COLUMN check_window_minutes INTEGER DEFAULT 15",
                "ALTER TABLE seller_cc_orders ADD COLUMN IF NOT EXISTS check_window_minutes INTEGER DEFAULT 15",
            ),
            (
                "ALTER TABLE seller_cc_orders ADD COLUMN check_started_at TIMESTAMP",
                "ALTER TABLE seller_cc_orders ADD COLUMN IF NOT EXISTS check_started_at TIMESTAMP",
            ),
            (
                "ALTER TABLE seller_cc_orders ADD COLUMN check_confirmed_at TIMESTAMP",
                "ALTER TABLE seller_cc_orders ADD COLUMN IF NOT EXISTS check_confirmed_at TIMESTAMP",
            ),
            (
                "ALTER TABLE seller_cc_orders ADD COLUMN check_expires_at TIMESTAMP",
                "ALTER TABLE seller_cc_orders ADD COLUMN IF NOT EXISTS check_expires_at TIMESTAMP",
            ),
            (
                "ALTER TABLE seller_cc_orders ADD COLUMN feedback_status VARCHAR(20)",
                "ALTER TABLE seller_cc_orders ADD COLUMN IF NOT EXISTS feedback_status VARCHAR(20)",
            ),
            (
                "ALTER TABLE seller_cc_orders ADD COLUMN feedback_at TIMESTAMP",
                "ALTER TABLE seller_cc_orders ADD COLUMN IF NOT EXISTS feedback_at TIMESTAMP",
            ),
            (
                "ALTER TABLE seller_cc_orders ADD COLUMN report_status VARCHAR(20)",
                "ALTER TABLE seller_cc_orders ADD COLUMN IF NOT EXISTS report_status VARCHAR(20)",
            ),
            (
                "ALTER TABLE seller_cc_orders ADD COLUMN reported_at TIMESTAMP",
                "ALTER TABLE seller_cc_orders ADD COLUMN IF NOT EXISTS reported_at TIMESTAMP",
            ),
            (
                "ALTER TABLE brute_bank_items ADD COLUMN account_number VARCHAR(50)",
                "ALTER TABLE brute_bank_items ADD COLUMN IF NOT EXISTS account_number VARCHAR(50)",
            ),
            (
                "ALTER TABLE brute_bank_items ADD COLUMN routing_number VARCHAR(50)",
                "ALTER TABLE brute_bank_items ADD COLUMN IF NOT EXISTS routing_number VARCHAR(50)",
            ),
            (
                "ALTER TABLE brute_bank_items ADD COLUMN state VARCHAR(50)",
                "ALTER TABLE brute_bank_items ADD COLUMN IF NOT EXISTS state VARCHAR(50)",
            ),
            (
                "ALTER TABLE brute_bank_items ADD COLUMN holder_name VARCHAR(200)",
                "ALTER TABLE brute_bank_items ADD COLUMN IF NOT EXISTS holder_name VARCHAR(200)",
            ),
            (
                "ALTER TABLE brute_bank_items ADD COLUMN holder_address TEXT",
                "ALTER TABLE brute_bank_items ADD COLUMN IF NOT EXISTS holder_address TEXT",
            ),
            (
                "ALTER TABLE brute_bank_items ADD COLUMN base_price NUMERIC(10,2)",
                "ALTER TABLE brute_bank_items ADD COLUMN IF NOT EXISTS base_price NUMERIC(10,2)",
            ),
            (
                "ALTER TABLE brute_bank_items ADD COLUMN buyer_price NUMERIC(10,2)",
                "ALTER TABLE brute_bank_items ADD COLUMN IF NOT EXISTS buyer_price NUMERIC(10,2)",
            ),
            (
                "ALTER TABLE brute_bank_items ADD COLUMN markup_code VARCHAR(50)",
                "ALTER TABLE brute_bank_items ADD COLUMN IF NOT EXISTS markup_code VARCHAR(50)",
            ),
            (
                "ALTER TABLE brute_bank_items ADD COLUMN markup_kind VARCHAR(20)",
                "ALTER TABLE brute_bank_items ADD COLUMN IF NOT EXISTS markup_kind VARCHAR(20)",
            ),
            (
                "ALTER TABLE brute_bank_items ADD COLUMN markup_value NUMERIC(10,2)",
                "ALTER TABLE brute_bank_items ADD COLUMN IF NOT EXISTS markup_value NUMERIC(10,2)",
            ),
            (
                "ALTER TABLE brute_bank_orders ADD COLUMN check_window_minutes INTEGER DEFAULT 15",
                "ALTER TABLE brute_bank_orders ADD COLUMN IF NOT EXISTS check_window_minutes INTEGER DEFAULT 15",
            ),
            (
                "ALTER TABLE brute_bank_orders ADD COLUMN check_started_at TIMESTAMP",
                "ALTER TABLE brute_bank_orders ADD COLUMN IF NOT EXISTS check_started_at TIMESTAMP",
            ),
            (
                "ALTER TABLE brute_bank_orders ADD COLUMN check_confirmed_at TIMESTAMP",
                "ALTER TABLE brute_bank_orders ADD COLUMN IF NOT EXISTS check_confirmed_at TIMESTAMP",
            ),
            (
                "ALTER TABLE brute_bank_orders ADD COLUMN check_expires_at TIMESTAMP",
                "ALTER TABLE brute_bank_orders ADD COLUMN IF NOT EXISTS check_expires_at TIMESTAMP",
            ),
            (
                "ALTER TABLE brute_bank_orders ADD COLUMN feedback_status VARCHAR(20)",
                "ALTER TABLE brute_bank_orders ADD COLUMN IF NOT EXISTS feedback_status VARCHAR(20)",
            ),
            (
                "ALTER TABLE brute_bank_orders ADD COLUMN feedback_at TIMESTAMP",
                "ALTER TABLE brute_bank_orders ADD COLUMN IF NOT EXISTS feedback_at TIMESTAMP",
            ),
            (
                "ALTER TABLE brute_bank_orders ADD COLUMN report_status VARCHAR(20)",
                "ALTER TABLE brute_bank_orders ADD COLUMN IF NOT EXISTS report_status VARCHAR(20)",
            ),
            (
                "ALTER TABLE brute_bank_orders ADD COLUMN reported_at TIMESTAMP",
                "ALTER TABLE brute_bank_orders ADD COLUMN IF NOT EXISTS reported_at TIMESTAMP",
            ),
            (
                "ALTER TABLE seller_cc_items ADD COLUMN bin VARCHAR(6)",
                "ALTER TABLE seller_cc_items ADD COLUMN IF NOT EXISTS bin VARCHAR(6)",
            ),
            (
                "ALTER TABLE seller_enroll_items ADD COLUMN enroll_category_id INTEGER REFERENCES enroll_categories(id)",
                "ALTER TABLE seller_enroll_items ADD COLUMN IF NOT EXISTS enroll_category_id INTEGER REFERENCES enroll_categories(id)",
            ),
            (
                "ALTER TABLE seller_enroll_items ADD COLUMN bank_name VARCHAR(120)",
                "ALTER TABLE seller_enroll_items ADD COLUMN IF NOT EXISTS bank_name VARCHAR(120)",
            ),
            (
                "ALTER TABLE seller_enroll_items ADD COLUMN card_zip VARCHAR(20)",
                "ALTER TABLE seller_enroll_items ADD COLUMN IF NOT EXISTS card_zip VARCHAR(20)",
            ),
            (
                "ALTER TABLE seller_enroll_items ADD COLUMN card_state VARCHAR(50)",
                "ALTER TABLE seller_enroll_items ADD COLUMN IF NOT EXISTS card_state VARCHAR(50)",
            ),
            (
                "ALTER TABLE seller_enroll_items ADD COLUMN card_type VARCHAR(20)",
                "ALTER TABLE seller_enroll_items ADD COLUMN IF NOT EXISTS card_type VARCHAR(20)",
            ),
            (
                "ALTER TABLE brute_bank_groups ADD COLUMN group_key VARCHAR(220)",
                "ALTER TABLE brute_bank_groups ADD COLUMN IF NOT EXISTS group_key VARCHAR(220)",
            ),
            (
                "ALTER TABLE seller_selfreg_cc_items ADD COLUMN selfreg_cc_category_id INTEGER REFERENCES selfreg_cc_categories(id)",
                "ALTER TABLE seller_selfreg_cc_items ADD COLUMN IF NOT EXISTS selfreg_cc_category_id INTEGER REFERENCES selfreg_cc_categories(id)",
            ),
            (
                "ALTER TABLE seller_cc_items ADD COLUMN card_type VARCHAR(20)",
                "ALTER TABLE seller_cc_items ADD COLUMN IF NOT EXISTS card_type VARCHAR(20)",
            ),
            # New fields for special products (2026-03-22)
            (
                "ALTER TABLE seller_enroll_items ADD COLUMN data_file_path VARCHAR(500)",
                "ALTER TABLE seller_enroll_items ADD COLUMN IF NOT EXISTS data_file_path VARCHAR(500)",
            ),
            (
                "ALTER TABLE seller_otp_items ADD COLUMN data_file_path VARCHAR(500)",
                "ALTER TABLE seller_otp_items ADD COLUMN IF NOT EXISTS data_file_path VARCHAR(500)",
            ),
            (
                "ALTER TABLE seller_logs_items ADD COLUMN log_file_path VARCHAR(500)",
                "ALTER TABLE seller_logs_items ADD COLUMN IF NOT EXISTS log_file_path VARCHAR(500)",
            ),
            (
                "ALTER TABLE seller_logs_items ADD COLUMN description_en TEXT",
                "ALTER TABLE seller_logs_items ADD COLUMN IF NOT EXISTS description_en TEXT",
            ),
            (
                "ALTER TABLE seller_selfreg_ba_items ADD COLUMN registration_date DATE",
                "ALTER TABLE seller_selfreg_ba_items ADD COLUMN IF NOT EXISTS registration_date DATE",
            ),
            (
                "ALTER TABLE seller_selfreg_ba_items ADD COLUMN zip VARCHAR(20)",
                "ALTER TABLE seller_selfreg_ba_items ADD COLUMN IF NOT EXISTS zip VARCHAR(20)",
            ),
            (
                "ALTER TABLE seller_selfreg_ba_items ADD COLUMN phone_renewable BOOLEAN",
                "ALTER TABLE seller_selfreg_ba_items ADD COLUMN IF NOT EXISTS phone_renewable BOOLEAN",
            ),
        ]:
            try:
                if "sqlite" in DATABASE_URL:
                    await conn.execute(text(stmt_sqlite))
                elif "postgresql" in DATABASE_URL:
                    await conn.execute(text(stmt_pg))
            except Exception:
                pass

        for stmt in [
            "UPDATE brute_bank_items SET base_price = COALESCE(base_price, price) WHERE price IS NOT NULL",
            "UPDATE brute_bank_items SET buyer_price = COALESCE(buyer_price, price) WHERE price IS NOT NULL",
            "UPDATE seller_nfc_items SET final_price = COALESCE(final_price, buyer_price, seller_price) WHERE seller_price IS NOT NULL",
            "UPDATE seller_otp_items SET final_price = COALESCE(final_price, buyer_price, seller_price) WHERE seller_price IS NOT NULL",
            "UPDATE seller_selfreg_cc_items SET final_price = COALESCE(final_price, buyer_price, seller_price) WHERE seller_price IS NOT NULL",
            "UPDATE seller_check_items SET final_price = COALESCE(final_price, buyer_price, seller_price) WHERE seller_price IS NOT NULL",
            "UPDATE brute_bank_groups SET group_key = bank_code WHERE group_key IS NULL OR group_key = ''",
        ]:
            try:
                await conn.execute(text(stmt))
            except Exception:
                pass

        for backfill in [
            "UPDATE seller_cc_items SET bin = substr(number, 1, 6) WHERE bin IS NULL AND number IS NOT NULL AND length(number) >= 6",
        ]:
            try:
                await conn.execute(text(backfill))
            except Exception:
                pass

        if "postgresql" in DATABASE_URL:
            try:
                await conn.execute(text(
                    "UPDATE seller_cc_items SET card_type = UPPER(extra_data->>'card_type') "
                    "WHERE card_type IS NULL AND extra_data IS NOT NULL AND extra_data->>'card_type' IS NOT NULL"
                ))
            except Exception:
                pass

        if "postgresql" in DATABASE_URL:
            for stmt in [
                "ALTER TABLE brute_bank_groups ALTER COLUMN group_key SET NOT NULL",
                "ALTER TABLE brute_bank_groups DROP CONSTRAINT IF EXISTS brute_bank_groups_bank_code_key",
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_brute_bank_groups_group_key ON brute_bank_groups(group_key)",
                "CREATE INDEX IF NOT EXISTS ix_seller_cc_items_bin ON seller_cc_items(bin)",
            ]:
                try:
                    await conn.execute(text(stmt))
                except Exception:
                    pass
        elif "sqlite" in DATABASE_URL:
            for stmt in [
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_brute_bank_groups_group_key ON brute_bank_groups(group_key)",
                "CREATE INDEX IF NOT EXISTS ix_seller_cc_items_bin ON seller_cc_items(bin)",
            ]:
                try:
                    await conn.execute(text(stmt))
                except Exception:
                    pass

        try:
            if "postgresql" in DATABASE_URL:
                await conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS ui_translations (
                        id SERIAL PRIMARY KEY,
                        key VARCHAR(200) NOT NULL,
                        language VARCHAR(5) NOT NULL,
                        text_value TEXT NOT NULL,
                        namespace VARCHAR(50),
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW()
                    )
                """))
                await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_ui_translations_key_lang ON ui_translations(key, language)"))
            elif "sqlite" in DATABASE_URL:
                await conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS ui_translations (
                        id INTEGER PRIMARY KEY,
                        key VARCHAR(200) NOT NULL,
                        language VARCHAR(5) NOT NULL,
                        text_value TEXT NOT NULL,
                        namespace VARCHAR(50),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_ui_translations_key_lang ON ui_translations(key, language)"))
        except Exception:
            pass

        try:
            if "postgresql" in DATABASE_URL:
                await conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS seller_nfc_items (
                        id SERIAL PRIMARY KEY,
                        seller_id INTEGER NOT NULL REFERENCES sellers(id),
                        upload_batch_id INTEGER REFERENCES seller_upload_batches(id),
                        item_name VARCHAR(200) NOT NULL,
                        product_type VARCHAR(20) DEFAULT 'nfc',
                        product_subtype VARCHAR(30) DEFAULT 'apple_pay',
                        nfc_type VARCHAR(10) NOT NULL,
                        bank_name VARCHAR(120) NOT NULL,
                        country VARCHAR(10) NOT NULL,
                        state VARCHAR(50),
                        zip VARCHAR(20),
                        seller_price NUMERIC(10,2) NOT NULL,
                        base_price NUMERIC(10,2),
                        buyer_price NUMERIC(10,2) NOT NULL,
                        markup_code VARCHAR(50),
                        markup_kind VARCHAR(20),
                        markup_value NUMERIC(10,2),
                        data_file_path VARCHAR(500) NOT NULL,
                        description TEXT,
                        instruction TEXT,
                        moderation_status VARCHAR(30) DEFAULT 'pending_moderation',
                        moderation_comment TEXT,
                        moderated_at TIMESTAMP,
                        moderated_by BIGINT,
                        is_in_stock BOOLEAN DEFAULT TRUE,
                        is_active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW()
                    )
                """))
                await conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS seller_nfc_orders (
                        id SERIAL PRIMARY KEY,
                        seller_id INTEGER NOT NULL REFERENCES sellers(id),
                        seller_nfc_item_id INTEGER NOT NULL REFERENCES seller_nfc_items(id),
                        buyer_user_id BIGINT NOT NULL,
                        mirror_bot_id INTEGER REFERENCES mirror_bots(id),
                        status VARCHAR(20) DEFAULT 'pending_admin',
                        product_type VARCHAR(20) DEFAULT 'nfc',
                        product_subtype VARCHAR(30) DEFAULT 'apple_pay',
                        price_for_buyer NUMERIC(10,2) NOT NULL,
                        price_for_seller NUMERIC(10,2) NOT NULL,
                        result_data JSONB,
                        files JSONB,
                        check_window_minutes INTEGER DEFAULT 60,
                        check_started_at TIMESTAMP,
                        check_confirmed_at TIMESTAMP,
                        check_expires_at TIMESTAMP,
                        feedback_status VARCHAR(20),
                        feedback_at TIMESTAMP,
                        report_status VARCHAR(20),
                        reported_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT NOW(),
                        completed_at TIMESTAMP
                    )
                """))
                await conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS seller_otp_items (
                        id SERIAL PRIMARY KEY,
                        seller_id INTEGER NOT NULL REFERENCES sellers(id),
                        upload_batch_id INTEGER REFERENCES seller_upload_batches(id),
                        item_name VARCHAR(200) NOT NULL,
                        product_type VARCHAR(20) DEFAULT 'otp',
                        product_subtype VARCHAR(30) DEFAULT 'otp_card',
                        bank_name VARCHAR(120) NOT NULL,
                        balance NUMERIC(10,2) NOT NULL,
                        has_fullz BOOLEAN DEFAULT FALSE,
                        sms_access_type VARCHAR(30) NOT NULL,
                        seller_price NUMERIC(10,2) NOT NULL,
                        base_price NUMERIC(10,2),
                        buyer_price NUMERIC(10,2) NOT NULL,
                        markup_code VARCHAR(50),
                        markup_kind VARCHAR(20),
                        markup_value NUMERIC(10,2),
                        description TEXT,
                        instruction TEXT,
                        moderation_status VARCHAR(30) DEFAULT 'pending_moderation',
                        moderation_comment TEXT,
                        moderated_at TIMESTAMP,
                        moderated_by BIGINT,
                        is_in_stock BOOLEAN DEFAULT TRUE,
                        is_active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW()
                    )
                """))
                await conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS seller_otp_orders (
                        id SERIAL PRIMARY KEY,
                        seller_id INTEGER NOT NULL REFERENCES sellers(id),
                        seller_otp_item_id INTEGER NOT NULL REFERENCES seller_otp_items(id),
                        buyer_user_id BIGINT NOT NULL,
                        mirror_bot_id INTEGER REFERENCES mirror_bots(id),
                        status VARCHAR(20) DEFAULT 'pending_admin',
                        product_type VARCHAR(20) DEFAULT 'otp',
                        product_subtype VARCHAR(30) DEFAULT 'otp_card',
                        price_for_buyer NUMERIC(10,2) NOT NULL,
                        price_for_seller NUMERIC(10,2) NOT NULL,
                        result_data JSONB,
                        files JSONB,
                        check_window_minutes INTEGER DEFAULT 60,
                        check_started_at TIMESTAMP,
                        check_confirmed_at TIMESTAMP,
                        check_expires_at TIMESTAMP,
                        feedback_status VARCHAR(20),
                        feedback_at TIMESTAMP,
                        report_status VARCHAR(20),
                        reported_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT NOW(),
                        completed_at TIMESTAMP
                    )
                """))
                await conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS selfreg_cc_categories (
                        id SERIAL PRIMARY KEY,
                        code VARCHAR(80) UNIQUE NOT NULL,
                        name VARCHAR(200) NOT NULL,
                        position INTEGER DEFAULT 0,
                        is_active BOOLEAN DEFAULT TRUE,
                        is_custom BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                """))
                await conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS selfreg_cc_category_requests (
                        id SERIAL PRIMARY KEY,
                        seller_id INTEGER NOT NULL REFERENCES sellers(id),
                        requested_name VARCHAR(200) NOT NULL,
                        status VARCHAR(20) DEFAULT 'pending',
                        admin_note TEXT,
                        created_at TIMESTAMP DEFAULT NOW(),
                        resolved_at TIMESTAMP
                    )
                """))
                await conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS seller_selfreg_cc_items (
                        id SERIAL PRIMARY KEY,
                        seller_id INTEGER NOT NULL REFERENCES sellers(id),
                        upload_batch_id INTEGER REFERENCES seller_upload_batches(id),
                        selfreg_cc_category_id INTEGER REFERENCES selfreg_cc_categories(id),
                        item_name VARCHAR(200) NOT NULL,
                        product_type VARCHAR(20) DEFAULT 'bank',
                        product_subtype VARCHAR(30) DEFAULT 'selfreg_cc',
                        bank_name VARCHAR(120) NOT NULL,
                        card_name VARCHAR(120),
                        credit_limit NUMERIC(10,2),
                        vcc_limit NUMERIC(10,2),
                        state VARCHAR(50),
                        zip VARCHAR(20),
                        has_email BOOLEAN DEFAULT FALSE,
                        has_phone BOOLEAN DEFAULT FALSE,
                        phone_days_remaining INTEGER,
                        phone_renewable BOOLEAN,
                        phone_change_allowed BOOLEAN,
                        online_access BOOLEAN DEFAULT FALSE,
                        seller_price NUMERIC(10,2) NOT NULL,
                        base_price NUMERIC(10,2),
                        buyer_price NUMERIC(10,2) NOT NULL,
                        markup_code VARCHAR(50),
                        markup_kind VARCHAR(20),
                        markup_value NUMERIC(10,2),
                        description TEXT,
                        instruction TEXT,
                        moderation_status VARCHAR(30) DEFAULT 'pending_moderation',
                        moderation_comment TEXT,
                        moderated_at TIMESTAMP,
                        moderated_by BIGINT,
                        is_in_stock BOOLEAN DEFAULT TRUE,
                        is_active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW()
                    )
                """))
                await conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS seller_selfreg_cc_orders (
                        id SERIAL PRIMARY KEY,
                        seller_id INTEGER NOT NULL REFERENCES sellers(id),
                        seller_selfreg_cc_item_id INTEGER NOT NULL REFERENCES seller_selfreg_cc_items(id),
                        buyer_user_id BIGINT NOT NULL,
                        mirror_bot_id INTEGER REFERENCES mirror_bots(id),
                        status VARCHAR(20) DEFAULT 'pending_admin',
                        product_type VARCHAR(20) DEFAULT 'bank',
                        product_subtype VARCHAR(30) DEFAULT 'selfreg_cc',
                        price_for_buyer NUMERIC(10,2) NOT NULL,
                        price_for_seller NUMERIC(10,2) NOT NULL,
                        result_data JSONB,
                        files JSONB,
                        check_window_minutes INTEGER DEFAULT 60,
                        check_started_at TIMESTAMP,
                        check_confirmed_at TIMESTAMP,
                        check_expires_at TIMESTAMP,
                        feedback_status VARCHAR(20),
                        feedback_at TIMESTAMP,
                        report_status VARCHAR(20),
                        reported_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT NOW(),
                        completed_at TIMESTAMP
                    )
                """))
                await conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS seller_check_items (
                        id SERIAL PRIMARY KEY,
                        seller_id INTEGER NOT NULL REFERENCES sellers(id),
                        upload_batch_id INTEGER REFERENCES seller_upload_batches(id),
                        item_name VARCHAR(200) NOT NULL,
                        product_type VARCHAR(20) DEFAULT 'bank',
                        product_subtype VARCHAR(30) DEFAULT 'checks',
                        check_type VARCHAR(30) NOT NULL,
                        bank_name VARCHAR(120) NOT NULL,
                        amount NUMERIC(10,2) NOT NULL,
                        state VARCHAR(50),
                        zip VARCHAR(20),
                        has_holder_name BOOLEAN DEFAULT FALSE,
                        has_address BOOLEAN DEFAULT FALSE,
                        check_date DATE,
                        seller_description TEXT,
                        scan_file_path VARCHAR(500) NOT NULL,
                        template_file_path VARCHAR(500),
                        seller_price NUMERIC(10,2) NOT NULL,
                        base_price NUMERIC(10,2),
                        buyer_price NUMERIC(10,2) NOT NULL,
                        markup_code VARCHAR(50),
                        markup_kind VARCHAR(20),
                        markup_value NUMERIC(10,2),
                        moderation_status VARCHAR(30) DEFAULT 'pending_moderation',
                        moderation_comment TEXT,
                        moderated_at TIMESTAMP,
                        moderated_by BIGINT,
                        is_in_stock BOOLEAN DEFAULT TRUE,
                        is_active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW()
                    )
                """))
                await conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS seller_check_orders (
                        id SERIAL PRIMARY KEY,
                        seller_id INTEGER NOT NULL REFERENCES sellers(id),
                        seller_check_item_id INTEGER NOT NULL REFERENCES seller_check_items(id),
                        buyer_user_id BIGINT NOT NULL,
                        mirror_bot_id INTEGER REFERENCES mirror_bots(id),
                        status VARCHAR(20) DEFAULT 'pending_admin',
                        product_type VARCHAR(20) DEFAULT 'bank',
                        product_subtype VARCHAR(30) DEFAULT 'checks',
                        price_for_buyer NUMERIC(10,2) NOT NULL,
                        price_for_seller NUMERIC(10,2) NOT NULL,
                        result_data JSONB,
                        files JSONB,
                        check_window_minutes INTEGER DEFAULT 60,
                        check_started_at TIMESTAMP,
                        check_confirmed_at TIMESTAMP,
                        check_expires_at TIMESTAMP,
                        feedback_status VARCHAR(20),
                        feedback_at TIMESTAMP,
                        report_status VARCHAR(20),
                        reported_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT NOW(),
                        completed_at TIMESTAMP
                    )
                """))
            elif "sqlite" in DATABASE_URL:
                await conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS seller_nfc_items (
                        id INTEGER PRIMARY KEY,
                        seller_id INTEGER NOT NULL,
                        upload_batch_id INTEGER,
                        item_name VARCHAR(200) NOT NULL,
                        product_type VARCHAR(20) DEFAULT 'nfc',
                        product_subtype VARCHAR(30) DEFAULT 'apple_pay',
                        nfc_type VARCHAR(10) NOT NULL,
                        bank_name VARCHAR(120) NOT NULL,
                        country VARCHAR(10) NOT NULL,
                        state VARCHAR(50),
                        zip VARCHAR(20),
                        seller_price NUMERIC(10,2) NOT NULL,
                        base_price NUMERIC(10,2),
                        buyer_price NUMERIC(10,2) NOT NULL,
                        markup_code VARCHAR(50),
                        markup_kind VARCHAR(20),
                        markup_value NUMERIC(10,2),
                        data_file_path VARCHAR(500) NOT NULL,
                        description TEXT,
                        instruction TEXT,
                        moderation_status VARCHAR(30) DEFAULT 'pending_moderation',
                        moderation_comment TEXT,
                        moderated_at TIMESTAMP,
                        moderated_by BIGINT,
                        is_in_stock BOOLEAN DEFAULT 1,
                        is_active BOOLEAN DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                await conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS seller_nfc_orders (
                        id INTEGER PRIMARY KEY,
                        seller_id INTEGER NOT NULL,
                        seller_nfc_item_id INTEGER NOT NULL,
                        buyer_user_id BIGINT NOT NULL,
                        mirror_bot_id INTEGER,
                        status VARCHAR(20) DEFAULT 'pending_admin',
                        product_type VARCHAR(20) DEFAULT 'nfc',
                        product_subtype VARCHAR(30) DEFAULT 'apple_pay',
                        price_for_buyer NUMERIC(10,2) NOT NULL,
                        price_for_seller NUMERIC(10,2) NOT NULL,
                        result_data JSON,
                        files JSON,
                        check_window_minutes INTEGER DEFAULT 60,
                        check_started_at TIMESTAMP,
                        check_confirmed_at TIMESTAMP,
                        check_expires_at TIMESTAMP,
                        feedback_status VARCHAR(20),
                        feedback_at TIMESTAMP,
                        report_status VARCHAR(20),
                        reported_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        completed_at TIMESTAMP
                    )
                """))
                await conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS seller_otp_items (
                        id INTEGER PRIMARY KEY,
                        seller_id INTEGER NOT NULL,
                        upload_batch_id INTEGER,
                        item_name VARCHAR(200) NOT NULL,
                        product_type VARCHAR(20) DEFAULT 'otp',
                        product_subtype VARCHAR(30) DEFAULT 'otp_card',
                        bank_name VARCHAR(120) NOT NULL,
                        balance NUMERIC(10,2) NOT NULL,
                        has_fullz BOOLEAN DEFAULT 0,
                        sms_access_type VARCHAR(30) NOT NULL,
                        seller_price NUMERIC(10,2) NOT NULL,
                        base_price NUMERIC(10,2),
                        buyer_price NUMERIC(10,2) NOT NULL,
                        markup_code VARCHAR(50),
                        markup_kind VARCHAR(20),
                        markup_value NUMERIC(10,2),
                        description TEXT,
                        instruction TEXT,
                        moderation_status VARCHAR(30) DEFAULT 'pending_moderation',
                        moderation_comment TEXT,
                        moderated_at TIMESTAMP,
                        moderated_by BIGINT,
                        is_in_stock BOOLEAN DEFAULT 1,
                        is_active BOOLEAN DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                await conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS seller_otp_orders (
                        id INTEGER PRIMARY KEY,
                        seller_id INTEGER NOT NULL,
                        seller_otp_item_id INTEGER NOT NULL,
                        buyer_user_id BIGINT NOT NULL,
                        mirror_bot_id INTEGER,
                        status VARCHAR(20) DEFAULT 'pending_admin',
                        product_type VARCHAR(20) DEFAULT 'otp',
                        product_subtype VARCHAR(30) DEFAULT 'otp_card',
                        price_for_buyer NUMERIC(10,2) NOT NULL,
                        price_for_seller NUMERIC(10,2) NOT NULL,
                        result_data JSON,
                        files JSON,
                        check_window_minutes INTEGER DEFAULT 60,
                        check_started_at TIMESTAMP,
                        check_confirmed_at TIMESTAMP,
                        check_expires_at TIMESTAMP,
                        feedback_status VARCHAR(20),
                        feedback_at TIMESTAMP,
                        report_status VARCHAR(20),
                        reported_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        completed_at TIMESTAMP
                    )
                """))
                await conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS selfreg_cc_categories (
                        id INTEGER PRIMARY KEY,
                        code VARCHAR(80) UNIQUE NOT NULL,
                        name VARCHAR(200) NOT NULL,
                        position INTEGER DEFAULT 0,
                        is_active BOOLEAN DEFAULT 1,
                        is_custom BOOLEAN DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                await conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS selfreg_cc_category_requests (
                        id INTEGER PRIMARY KEY,
                        seller_id INTEGER NOT NULL,
                        requested_name VARCHAR(200) NOT NULL,
                        status VARCHAR(20) DEFAULT 'pending',
                        admin_note TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        resolved_at TIMESTAMP
                    )
                """))
                await conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS seller_selfreg_cc_items (
                        id INTEGER PRIMARY KEY,
                        seller_id INTEGER NOT NULL,
                        upload_batch_id INTEGER,
                        selfreg_cc_category_id INTEGER,
                        item_name VARCHAR(200) NOT NULL,
                        product_type VARCHAR(20) DEFAULT 'bank',
                        product_subtype VARCHAR(30) DEFAULT 'selfreg_cc',
                        bank_name VARCHAR(120) NOT NULL,
                        card_name VARCHAR(120),
                        credit_limit NUMERIC(10,2),
                        vcc_limit NUMERIC(10,2),
                        state VARCHAR(50),
                        zip VARCHAR(20),
                        has_email BOOLEAN DEFAULT 0,
                        has_phone BOOLEAN DEFAULT 0,
                        phone_days_remaining INTEGER,
                        phone_renewable BOOLEAN,
                        phone_change_allowed BOOLEAN,
                        online_access BOOLEAN DEFAULT 0,
                        seller_price NUMERIC(10,2) NOT NULL,
                        base_price NUMERIC(10,2),
                        buyer_price NUMERIC(10,2) NOT NULL,
                        markup_code VARCHAR(50),
                        markup_kind VARCHAR(20),
                        markup_value NUMERIC(10,2),
                        description TEXT,
                        instruction TEXT,
                        moderation_status VARCHAR(30) DEFAULT 'pending_moderation',
                        moderation_comment TEXT,
                        moderated_at TIMESTAMP,
                        moderated_by BIGINT,
                        is_in_stock BOOLEAN DEFAULT 1,
                        is_active BOOLEAN DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                await conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS seller_selfreg_cc_orders (
                        id INTEGER PRIMARY KEY,
                        seller_id INTEGER NOT NULL,
                        seller_selfreg_cc_item_id INTEGER NOT NULL,
                        buyer_user_id BIGINT NOT NULL,
                        mirror_bot_id INTEGER,
                        status VARCHAR(20) DEFAULT 'pending_admin',
                        product_type VARCHAR(20) DEFAULT 'bank',
                        product_subtype VARCHAR(30) DEFAULT 'selfreg_cc',
                        price_for_buyer NUMERIC(10,2) NOT NULL,
                        price_for_seller NUMERIC(10,2) NOT NULL,
                        result_data JSON,
                        files JSON,
                        check_window_minutes INTEGER DEFAULT 60,
                        check_started_at TIMESTAMP,
                        check_confirmed_at TIMESTAMP,
                        check_expires_at TIMESTAMP,
                        feedback_status VARCHAR(20),
                        feedback_at TIMESTAMP,
                        report_status VARCHAR(20),
                        reported_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        completed_at TIMESTAMP
                    )
                """))
                await conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS seller_check_items (
                        id INTEGER PRIMARY KEY,
                        seller_id INTEGER NOT NULL,
                        upload_batch_id INTEGER,
                        item_name VARCHAR(200) NOT NULL,
                        product_type VARCHAR(20) DEFAULT 'bank',
                        product_subtype VARCHAR(30) DEFAULT 'checks',
                        check_type VARCHAR(30) NOT NULL,
                        bank_name VARCHAR(120) NOT NULL,
                        amount NUMERIC(10,2) NOT NULL,
                        state VARCHAR(50),
                        zip VARCHAR(20),
                        has_holder_name BOOLEAN DEFAULT 0,
                        has_address BOOLEAN DEFAULT 0,
                        check_date DATE,
                        seller_description TEXT,
                        scan_file_path VARCHAR(500) NOT NULL,
                        template_file_path VARCHAR(500),
                        seller_price NUMERIC(10,2) NOT NULL,
                        base_price NUMERIC(10,2),
                        buyer_price NUMERIC(10,2) NOT NULL,
                        markup_code VARCHAR(50),
                        markup_kind VARCHAR(20),
                        markup_value NUMERIC(10,2),
                        moderation_status VARCHAR(30) DEFAULT 'pending_moderation',
                        moderation_comment TEXT,
                        moderated_at TIMESTAMP,
                        moderated_by BIGINT,
                        is_in_stock BOOLEAN DEFAULT 1,
                        is_active BOOLEAN DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                await conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS seller_check_orders (
                        id INTEGER PRIMARY KEY,
                        seller_id INTEGER NOT NULL,
                        seller_check_item_id INTEGER NOT NULL,
                        buyer_user_id BIGINT NOT NULL,
                        mirror_bot_id INTEGER,
                        status VARCHAR(20) DEFAULT 'pending_admin',
                        product_type VARCHAR(20) DEFAULT 'bank',
                        product_subtype VARCHAR(30) DEFAULT 'checks',
                        price_for_buyer NUMERIC(10,2) NOT NULL,
                        price_for_seller NUMERIC(10,2) NOT NULL,
                        result_data JSON,
                        files JSON,
                        check_window_minutes INTEGER DEFAULT 60,
                        check_started_at TIMESTAMP,
                        check_confirmed_at TIMESTAMP,
                        check_expires_at TIMESTAMP,
                        feedback_status VARCHAR(20),
                        feedback_at TIMESTAMP,
                        report_status VARCHAR(20),
                        reported_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        completed_at TIMESTAMP
                    )
                """))
        except Exception:
            pass

        for stmt_sqlite, stmt_pg in [
            (
                "ALTER TABLE product_purchases ADD COLUMN guarantee_until TIMESTAMP",
                "ALTER TABLE product_purchases ADD COLUMN IF NOT EXISTS guarantee_until TIMESTAMP",
            ),
            (
                "ALTER TABLE seller_enroll_items ADD COLUMN guarantee_until TIMESTAMP",
                "ALTER TABLE seller_enroll_items ADD COLUMN IF NOT EXISTS guarantee_until TIMESTAMP",
            ),
            (
                "ALTER TABLE seller_selfreg_ba_items ADD COLUMN guarantee_until TIMESTAMP",
                "ALTER TABLE seller_selfreg_ba_items ADD COLUMN IF NOT EXISTS guarantee_until TIMESTAMP",
            ),
            (
                "ALTER TABLE seller_logs_items ADD COLUMN guarantee_until TIMESTAMP",
                "ALTER TABLE seller_logs_items ADD COLUMN IF NOT EXISTS guarantee_until TIMESTAMP",
            ),
            (
                "ALTER TABLE seller_check_orders ADD COLUMN guarantee_until TIMESTAMP",
                "ALTER TABLE seller_check_orders ADD COLUMN IF NOT EXISTS guarantee_until TIMESTAMP",
            ),
            (
                "ALTER TABLE seller_nfc_orders ADD COLUMN guarantee_until TIMESTAMP",
                "ALTER TABLE seller_nfc_orders ADD COLUMN IF NOT EXISTS guarantee_until TIMESTAMP",
            ),
            (
                "ALTER TABLE seller_otp_orders ADD COLUMN guarantee_until TIMESTAMP",
                "ALTER TABLE seller_otp_orders ADD COLUMN IF NOT EXISTS guarantee_until TIMESTAMP",
            ),
            (
                "ALTER TABLE seller_selfreg_cc_orders ADD COLUMN guarantee_until TIMESTAMP",
                "ALTER TABLE seller_selfreg_cc_orders ADD COLUMN IF NOT EXISTS guarantee_until TIMESTAMP",
            ),
            (
                "ALTER TABLE product_purchases ADD COLUMN report_status VARCHAR(20)",
                "ALTER TABLE product_purchases ADD COLUMN IF NOT EXISTS report_status VARCHAR(20)",
            ),
            (
                "ALTER TABLE product_purchases ADD COLUMN reported_at TIMESTAMP",
                "ALTER TABLE product_purchases ADD COLUMN IF NOT EXISTS reported_at TIMESTAMP",
            ),
        ]:
            try:
                if "sqlite" in DATABASE_URL:
                    await conn.execute(text(stmt_sqlite))
                elif "postgresql" in DATABASE_URL:
                    await conn.execute(text(stmt_pg))
            except Exception:
                pass

        try:
            if "sqlite" in DATABASE_URL:
                await conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS product_ratings (
                        id INTEGER PRIMARY KEY,
                        purchase_id INTEGER NOT NULL,
                        user_id INTEGER NOT NULL,
                        rating VARCHAR(20) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY(purchase_id) REFERENCES product_purchases(id),
                        FOREIGN KEY(user_id) REFERENCES users(user_id)
                    )
                """))
            elif "postgresql" in DATABASE_URL:
                await conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS product_ratings (
                        id SERIAL PRIMARY KEY,
                        purchase_id INTEGER NOT NULL REFERENCES product_purchases(id),
                        user_id BIGINT NOT NULL REFERENCES users(user_id),
                        rating VARCHAR(20) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
        except Exception:
            pass

        if "postgresql" in DATABASE_URL:
            for stmt in [
                "ALTER TABLE products ALTER COLUMN moderation_status SET DEFAULT 'pending_moderation'",
                "ALTER TABLE users ALTER COLUMN language SET DEFAULT 'ru'",
                "CREATE INDEX IF NOT EXISTS ix_seller_orders_status ON seller_orders(status)",
                "CREATE INDEX IF NOT EXISTS ix_seller_orders_auto_complete ON seller_orders(auto_complete_at)",
                "CREATE INDEX IF NOT EXISTS ix_products_moderation_status ON products(moderation_status)",
                "CREATE INDEX IF NOT EXISTS ix_products_is_active ON products(is_active)",
                "CREATE INDEX IF NOT EXISTS idx_users_archive_channel_id ON users(archive_channel_id)",
            ]:
                try:
                    await conn.execute(text(stmt))
                except Exception:
                    pass
        elif "sqlite" in DATABASE_URL:
            for stmt in [
                "CREATE INDEX IF NOT EXISTS ix_seller_orders_status ON seller_orders(status)",
                "CREATE INDEX IF NOT EXISTS ix_seller_orders_auto_complete ON seller_orders(auto_complete_at)",
                "CREATE INDEX IF NOT EXISTS ix_products_moderation_status ON products(moderation_status)",
                "CREATE INDEX IF NOT EXISTS ix_products_is_active ON products(is_active)",
                "CREATE INDEX IF NOT EXISTS idx_users_archive_channel_id ON users(archive_channel_id)",
            ]:
                try:
                    await conn.execute(text(stmt))
                except Exception:
                    pass

        try:
            if "postgresql" in DATABASE_URL:
                await conn.execute(text(
                    """
                    INSERT INTO cc_categories (code, name, position, is_active)
                    SELECT 'non_vbv', 'NON VBV', 30, true
                    WHERE NOT EXISTS (SELECT 1 FROM cc_categories WHERE code = 'non_vbv')
                    """
                ))
            elif "sqlite" in DATABASE_URL:
                await conn.execute(text(
                    """
                    INSERT INTO cc_categories (code, name, position, is_active)
                    SELECT 'non_vbv', 'NON VBV', 30, 1
                    WHERE NOT EXISTS (SELECT 1 FROM cc_categories WHERE code = 'non_vbv')
                    """
                ))
        except Exception:
            pass

        enroll_rows = [
            ("fdecs", "FDECS"),
            ("digitalcardservice", "DIGITALCARDSERVICE"),
            ("mycardinfo", "MYCARDINFO"),
            ("card_suite_light", "CARD SUITE LIGHT"),
            ("cardnav", "CardNav"),
            ("firefighters", "FIREFIGHTERS"),
            ("coast_central", "COAST CENTRAL"),
            ("web_access", "WEB ACCESS"),
            ("card_suite", "Card Suite"),
            ("myaccountaccess", "Myaccountaccess"),
            ("centresuite_minik", "CENTRESUITE (minik)"),
        ]
        try:
            for pos, (code, name) in enumerate(enroll_rows):
                params = {"code": code, "name": name, "pos": pos}
                if "postgresql" in DATABASE_URL:
                    await conn.execute(
                        text(
                            """
                            INSERT INTO enroll_categories (code, name, position, is_active, is_custom)
                            SELECT :code, :name, :pos, true, false
                            WHERE NOT EXISTS (SELECT 1 FROM enroll_categories WHERE code = :code)
                            """
                        ),
                        params,
                    )
                elif "sqlite" in DATABASE_URL:
                    await conn.execute(
                        text(
                            """
                            INSERT INTO enroll_categories (code, name, position, is_active, is_custom)
                            SELECT :code, :name, :pos, 1, 0
                            WHERE NOT EXISTS (SELECT 1 FROM enroll_categories WHERE code = :code)
                            """
                        ),
                        params,
                    )
        except Exception:
            pass

        selfreg_cc_rows = [
            ("citi", "Citi"),
            ("chase", "Chase"),
            ("wells_fargo", "Wells Fargo"),
            ("onepay", "ONEPAY"),
            ("boa", "BOA"),
        ]
        try:
            for pos, (code, name) in enumerate(selfreg_cc_rows):
                params = {"code": code, "name": name, "pos": pos}
                if "postgresql" in DATABASE_URL:
                    await conn.execute(
                        text(
                            """
                            INSERT INTO selfreg_cc_categories (code, name, position, is_active, is_custom)
                            SELECT :code, :name, :pos, true, false
                            WHERE NOT EXISTS (SELECT 1 FROM selfreg_cc_categories WHERE code = :code)
                            """
                        ),
                        params,
                    )
                elif "sqlite" in DATABASE_URL:
                    await conn.execute(
                        text(
                            """
                            INSERT INTO selfreg_cc_categories (code, name, position, is_active, is_custom)
                            SELECT :code, :name, :pos, 1, 0
                            WHERE NOT EXISTS (SELECT 1 FROM selfreg_cc_categories WHERE code = :code)
                            """
                        ),
                        params,
                    )
        except Exception:
            pass

        # Миграция: order_type и eta_minutes в orders и service_prices (feat/mirror-orders)
        for stmt_sqlite, stmt_pg in [
            (
                "ALTER TABLE orders ADD COLUMN order_type VARCHAR(20) DEFAULT 'order'",
                "ALTER TABLE orders ADD COLUMN IF NOT EXISTS order_type VARCHAR(20) DEFAULT 'order'",
            ),
            (
                "ALTER TABLE orders ADD COLUMN eta_minutes INTEGER",
                "ALTER TABLE orders ADD COLUMN IF NOT EXISTS eta_minutes INTEGER",
            ),
            (
                "ALTER TABLE service_prices ADD COLUMN order_type VARCHAR(20) DEFAULT 'order'",
                "ALTER TABLE service_prices ADD COLUMN IF NOT EXISTS order_type VARCHAR(20) DEFAULT 'order'",
            ),
            (
                "ALTER TABLE service_prices ADD COLUMN eta_minutes INTEGER",
                "ALTER TABLE service_prices ADD COLUMN IF NOT EXISTS eta_minutes INTEGER",
            ),
            (
                "ALTER TABLE service_prices ADD COLUMN service_link VARCHAR(500)",
                "ALTER TABLE service_prices ADD COLUMN IF NOT EXISTS service_link VARCHAR(500)",
            ),
        ]:
            try:
                if "sqlite" in DATABASE_URL:
                    await conn.execute(text(stmt_sqlite))
                elif "postgresql" in DATABASE_URL:
                    await conn.execute(text(stmt_pg))
            except Exception:
                pass

        system_settings_seed = [
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
            ("MIN_WITHDRAWAL_AMOUNT", "100.00", "Минимальная сумма вывода ($100 по спеку v24)"),
            ("MAX_WITHDRAWAL_AMOUNT", "5000.00", "Максимальная сумма вывода"),
            ("AUTO_WITHDRAWAL_THRESHOLD", "500.00", "Порог авто-одобрения вывода без ручной проверки"),
            ("PLATFORM_FEE_TOP_SELLER", "0.12", "Комиссия для Top Seller (Score >= 4.8)"),
            ("PLATFORM_FEE_LOW_SELLER", "0.18", "Комиссия для Low Rating Seller (Score < 3.5)"),
            ("MARKETER_COMMISSION", "0.10", "Комиссия маркетолога от каждой покупки"),
            ("WELCOME_COUPON_CODE", "WELCOME10", "Приветственный купон для новых покупателей"),
            ("WELCOME_COUPON_DISCOUNT", "10", "Скидка по приветственному купону (%)"),
        ]
        for key, value, description in system_settings_seed:
            try:
                await conn.execute(
                    text(
                        """
                        INSERT INTO system_settings (key, value, description, updated_at)
                        VALUES (:key, :value, :description, CURRENT_TIMESTAMP)
                        ON CONFLICT (key) DO NOTHING
                        """
                    ),
                    {"key": key, "value": value, "description": description},
                )
            except Exception:
                pass


async def _seed_referral_settings() -> None:
    """Populate referral_settings with default level configs if not present."""
    from sqlalchemy import text

    defaults = [
        # (level, display_percent, real_percent, max_daily, cooldown_hours)
        (1, 15.0, 7.0, 100, 0),
        (2, 7.0, 3.0, 100, 0),
        (3, 3.0, 1.0, 100, 0),
        (4, 1.0, 0.2, 100, 0),
        (5, 0.5, 0.0, 100, 0),
    ]
    async with engine.begin() as conn:
        for level, display_pct, real_pct, max_daily, cooldown in defaults:
            try:
                if _is_sqlite:
                    await conn.execute(
                        text(
                            "INSERT OR IGNORE INTO referral_settings "
                            "(level, display_percent, real_percent, max_daily, cooldown_hours, is_active, updated_at) "
                            "VALUES (:level, :dp, :rp, :md, :ch, 1, CURRENT_TIMESTAMP)"
                        ),
                        {"level": level, "dp": display_pct, "rp": real_pct, "md": max_daily, "ch": cooldown},
                    )
                else:
                    await conn.execute(
                        text(
                            "INSERT INTO referral_settings "
                            "(level, display_percent, real_percent, max_daily, cooldown_hours, is_active, updated_at) "
                            "VALUES (:level, :dp, :rp, :md, :ch, TRUE, CURRENT_TIMESTAMP) "
                            "ON CONFLICT (level) DO NOTHING"
                        ),
                        {"level": level, "dp": display_pct, "rp": real_pct, "md": max_daily, "ch": cooldown},
                    )
            except Exception:
                pass


async def get_session() -> AsyncSession:
    async with async_session_maker() as session:
        yield session
