"""
Manual migration script to create bank request tables.
Since Alembic is not configured, we'll create tables directly.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from shared.database.session import engine


async def create_tables():
    """Create bank_type_requests and brute_bank_type_requests tables."""
    
    async with engine.begin() as conn:
        print("Creating bank_type_requests table...")
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS bank_type_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                seller_id INTEGER NOT NULL,
                requested_name VARCHAR(200) NOT NULL,
                state VARCHAR(10),
                zip VARCHAR(20),
                has_docs BOOLEAN DEFAULT 0,
                doc_type VARCHAR(100),
                description TEXT,
                product_type VARCHAR(20),
                product_subtype VARCHAR(30),
                category VARCHAR(20),
                status VARCHAR(20) DEFAULT 'pending',
                admin_note TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                resolved_at DATETIME,
                FOREIGN KEY (seller_id) REFERENCES sellers(id)
            )
        """))
        
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_bank_type_requests_seller_id 
            ON bank_type_requests(seller_id)
        """))
        
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_bank_type_requests_status 
            ON bank_type_requests(status)
        """))
        
        print("✅ bank_type_requests table created")
        
        print("Creating brute_bank_type_requests table...")
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS brute_bank_type_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                seller_id INTEGER NOT NULL,
                requested_name VARCHAR(200) NOT NULL,
                bank_code VARCHAR(100),
                attributes TEXT,
                category VARCHAR(50),
                status VARCHAR(20) DEFAULT 'pending',
                admin_note TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                resolved_at DATETIME,
                FOREIGN KEY (seller_id) REFERENCES sellers(id)
            )
        """))
        
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_brute_bank_type_requests_seller_id 
            ON brute_bank_type_requests(seller_id)
        """))
        
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_brute_bank_type_requests_status 
            ON brute_bank_type_requests(status)
        """))
        
        print("✅ brute_bank_type_requests table created")
        
        # Verify tables exist
        result = await conn.execute(text("""
            SELECT name FROM sqlite_master 
            WHERE type='table' 
            AND name IN ('bank_type_requests', 'brute_bank_type_requests')
        """))
        tables = [row[0] for row in result]
        
        print(f"\n✅ Migration complete! Created tables: {tables}")


if __name__ == "__main__":
    asyncio.run(create_tables())
