#!/usr/bin/env python3
"""
Миграция: добавить can_load_products в workers и создать таблицу bank_positions.
Запуск: python scripts/migrate_worker_bank.py
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def migrate():
    from sqlalchemy import text
    from shared.database.session import engine
    from shared.database.models import Base, BankPosition  # BankPosition для create_all

    url = str(engine.url)
    async with engine.begin() as conn:
        # workers.can_load_products
        if "postgresql" in url:
            await conn.execute(text("""
                ALTER TABLE workers 
                ADD COLUMN IF NOT EXISTS can_load_products BOOLEAN DEFAULT FALSE
            """))
        else:
            try:
                await conn.execute(text("ALTER TABLE workers ADD COLUMN can_load_products BOOLEAN DEFAULT 0"))
            except Exception as e:
                if "duplicate" not in str(e).lower():
                    raise
        print("✅ workers.can_load_products")

    # bank_positions
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ bank_positions")
    print("Миграция завершена.")

if __name__ == "__main__":
    asyncio.run(migrate())
