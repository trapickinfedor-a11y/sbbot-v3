#!/usr/bin/env python3
"""Add moderation columns to seller_banks and seller_cc_items."""
import asyncio
from sqlalchemy import text
from shared.database.session import async_session_maker


async def run_alter(session, sql: str):
    try:
        await session.execute(text(sql))
        await session.commit()
        return True
    except Exception as e:
        if "already exists" in str(e).lower():
            await session.rollback()
            return False
        raise


async def migrate():
    async with async_session_maker() as session:
        for sql in [
            # Existing rows get 'approved' so they stay visible; new rows get pending_moderation from app
            "ALTER TABLE seller_banks ADD COLUMN IF NOT EXISTS moderation_status VARCHAR(30) DEFAULT 'approved'",
            "ALTER TABLE seller_banks ADD COLUMN IF NOT EXISTS moderation_comment TEXT",
            "ALTER TABLE seller_banks ADD COLUMN IF NOT EXISTS moderated_at TIMESTAMP",
            "ALTER TABLE seller_banks ADD COLUMN IF NOT EXISTS moderated_by BIGINT",
        ]:
            await run_alter(session, sql)
        print("seller_banks: moderation columns ok")

        for sql in [
            "ALTER TABLE seller_cc_items ADD COLUMN IF NOT EXISTS moderation_status VARCHAR(30) DEFAULT 'pending_moderation'",
            "ALTER TABLE seller_cc_items ADD COLUMN IF NOT EXISTS moderation_comment TEXT",
            "ALTER TABLE seller_cc_items ADD COLUMN IF NOT EXISTS moderated_at TIMESTAMP",
            "ALTER TABLE seller_cc_items ADD COLUMN IF NOT EXISTS moderated_by BIGINT",
            "ALTER TABLE seller_cc_items ADD COLUMN IF NOT EXISTS extra_data JSONB",
        ]:
            await run_alter(session, sql)
        print("seller_cc_items: moderation columns ok")

        for sql in [
            "ALTER TABLE sellers ADD COLUMN IF NOT EXISTS deposit_balance NUMERIC(10,2) DEFAULT 0",
        ]:
            await run_alter(session, sql)
        print("sellers: deposit_balance column ok")


if __name__ == "__main__":
    asyncio.run(migrate())
