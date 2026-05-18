#!/usr/bin/env python3
"""
Apply Mini App v2 database migration.
Handles the actual table structure in the database.
"""
import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from shared.database.session import engine, init_db


async def column_exists(conn, table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    result = await conn.execute(text(f"PRAGMA table_info({table_name})"))
    columns = [row[1] for row in result.fetchall()]
    return column_name in columns


async def table_exists(conn, table_name: str) -> bool:
    """Check if a table exists."""
    result = await conn.execute(text(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=:table_name"
    ), {"table_name": table_name})
    return result.fetchone() is not None


async def add_column_if_not_exists(conn, table_name: str, column_name: str, column_def: str):
    """Add a column if it doesn't exist."""
    if not await column_exists(conn, table_name, column_name):
        await conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}"))
        return True
    return False


async def run_migration():
    """Apply the Mini App v2 migration."""
    print("🚀 Starting Mini App v2 migration...")
    
    try:
        # Initialize database first
        print("\n📊 Initializing database...")
        await init_db()
        print("✅ Database initialized!")
        
        async with engine.begin() as conn:
            # Check current state
            has_selfreg_ba = await table_exists(conn, 'seller_selfreg_ba_items')
            has_bank_items = await table_exists(conn, 'seller_bank_items')
            
            print(f"\n📋 Current state:")
            print(f"   - seller_selfreg_ba_items: {'✓' if has_selfreg_ba else '✗'}")
            print(f"   - seller_bank_items: {'✓' if has_bank_items else '✗'}")
            
            # Step 1: Rename seller_selfreg_ba_items to seller_bank_items
            if has_selfreg_ba and not has_bank_items:
                print(f"\n📊 Step 1: Renaming seller_selfreg_ba_items to seller_bank_items...")
                await conn.execute(text("ALTER TABLE seller_selfreg_ba_items RENAME TO seller_bank_items"))
                await conn.execute(text("ALTER TABLE seller_selfreg_ba_orders RENAME TO seller_bank_orders"))
                print("✅ Tables renamed!")
            elif has_bank_items:
                print(f"\n⚠️  seller_bank_items already exists, skipping rename")
            else:
                print(f"\n⚠️  Neither table exists, will be created by init_db")
            
            # Step 2: Add new columns to seller_bank_items
            print(f"\n📊 Step 2: Adding new columns to seller_bank_items...")
            added = 0
            added += await add_column_if_not_exists(conn, 'seller_bank_items', 'category', 'VARCHAR(20)')
            added += await add_column_if_not_exists(conn, 'seller_bank_items', 'bank_code', 'VARCHAR(50)')
            added += await add_column_if_not_exists(conn, 'seller_bank_items', 'product_type', 'VARCHAR(100)')
            added += await add_column_if_not_exists(conn, 'seller_bank_items', 'phone_can_swap', 'BOOLEAN DEFAULT 0')
            added += await add_column_if_not_exists(conn, 'seller_bank_items', 'return_item_enabled', 'BOOLEAN DEFAULT 0')
            added += await add_column_if_not_exists(conn, 'seller_bank_items', 'return_days', 'INTEGER')
            
            # Update existing records
            if await column_exists(conn, 'seller_bank_items', 'category'):
                await conn.execute(text("UPDATE seller_bank_items SET category = 'personal' WHERE category IS NULL"))
            
            print(f"✅ Added {added} new columns")
            
            # Step 3: Brute Bank fields
            print(f"\n📊 Step 3: Adding fields to brute_bank_items...")
            added = 0
            added += await add_column_if_not_exists(conn, 'brute_bank_items', 'exact_balance', 'VARCHAR(50)')
            added += await add_column_if_not_exists(conn, 'brute_bank_items', 'account_number', 'VARCHAR(255)')
            added += await add_column_if_not_exists(conn, 'brute_bank_items', 'routing_number', 'VARCHAR(255)')
            added += await add_column_if_not_exists(conn, 'brute_bank_items', 'holder_name', 'VARCHAR(200)')
            added += await add_column_if_not_exists(conn, 'brute_bank_items', 'address', 'VARCHAR(500)')
            added += await add_column_if_not_exists(conn, 'brute_bank_items', 'state', 'VARCHAR(10)')
            added += await add_column_if_not_exists(conn, 'brute_bank_items', 'zip', 'VARCHAR(20)')
            added += await add_column_if_not_exists(conn, 'brute_bank_items', 'additional_info', 'TEXT')
            added += await add_column_if_not_exists(conn, 'brute_bank_items', 'has_docs', 'BOOLEAN DEFAULT 0')
            print(f"✅ Added {added} new columns")
            
            # Step 4: CC NON VBV pricing
            print(f"\n📊 Step 4: Adding NON VBV pricing to seller_cc_items...")
            added = 0
            added += await add_column_if_not_exists(conn, 'seller_cc_items', 'seller_price_non_vbv', 'NUMERIC(10,2)')
            added += await add_column_if_not_exists(conn, 'seller_cc_items', 'buyer_price_non_vbv', 'NUMERIC(10,2)')
            
            if await column_exists(conn, 'seller_cc_items', 'seller_price_non_vbv'):
                await conn.execute(text("UPDATE seller_cc_items SET seller_price_non_vbv = seller_price WHERE seller_price_non_vbv IS NULL"))
                await conn.execute(text("UPDATE seller_cc_items SET buyer_price_non_vbv = buyer_price WHERE buyer_price_non_vbv IS NULL"))
            
            print(f"✅ Added {added} new columns")
            
            # Step 5: Selfreg CC fields
            print(f"\n📊 Step 5: Adding fields to seller_selfreg_cc_items...")
            added = 0
            added += await add_column_if_not_exists(conn, 'seller_selfreg_cc_items', 'registration_date', 'DATE')
            added += await add_column_if_not_exists(conn, 'seller_selfreg_cc_items', 'vcc_bin', 'VARCHAR(6)')
            added += await add_column_if_not_exists(conn, 'seller_selfreg_cc_items', 'return_item_enabled', 'BOOLEAN DEFAULT 0')
            added += await add_column_if_not_exists(conn, 'seller_selfreg_cc_items', 'return_days', 'INTEGER')
            print(f"✅ Added {added} new columns")
            
            # Step 6: OTP Fullz fields
            print(f"\n📊 Step 6: Adding Fullz fields to seller_otp_items...")
            added = 0
            added += await add_column_if_not_exists(conn, 'seller_otp_items', 'state', 'VARCHAR(10)')
            added += await add_column_if_not_exists(conn, 'seller_otp_items', 'zip', 'VARCHAR(20)')
            added += await add_column_if_not_exists(conn, 'seller_otp_items', 'fullz_first_name', 'VARCHAR(100)')
            added += await add_column_if_not_exists(conn, 'seller_otp_items', 'fullz_last_name', 'VARCHAR(100)')
            added += await add_column_if_not_exists(conn, 'seller_otp_items', 'fullz_dob', 'DATE')
            added += await add_column_if_not_exists(conn, 'seller_otp_items', 'fullz_ssn', 'VARCHAR(20)')
            added += await add_column_if_not_exists(conn, 'seller_otp_items', 'fullz_address', 'VARCHAR(500)')
            added += await add_column_if_not_exists(conn, 'seller_otp_items', 'fullz_city', 'VARCHAR(100)')
            added += await add_column_if_not_exists(conn, 'seller_otp_items', 'fullz_state', 'VARCHAR(10)')
            added += await add_column_if_not_exists(conn, 'seller_otp_items', 'fullz_zip', 'VARCHAR(20)')
            added += await add_column_if_not_exists(conn, 'seller_otp_items', 'fullz_phone', 'VARCHAR(50)')
            added += await add_column_if_not_exists(conn, 'seller_otp_items', 'fullz_email', 'VARCHAR(200)')
            print(f"✅ Added {added} new columns")
            
            # Step 7: Enrollment fields
            print(f"\n📊 Step 7: Adding detailed fields to seller_enroll_items...")
            added = 0
            added += await add_column_if_not_exists(conn, 'seller_enroll_items', 'first_name', 'VARCHAR(100)')
            added += await add_column_if_not_exists(conn, 'seller_enroll_items', 'last_name', 'VARCHAR(100)')
            added += await add_column_if_not_exists(conn, 'seller_enroll_items', 'dob', 'DATE')
            added += await add_column_if_not_exists(conn, 'seller_enroll_items', 'ssn', 'VARCHAR(20)')
            added += await add_column_if_not_exists(conn, 'seller_enroll_items', 'address', 'VARCHAR(500)')
            added += await add_column_if_not_exists(conn, 'seller_enroll_items', 'city', 'VARCHAR(100)')
            added += await add_column_if_not_exists(conn, 'seller_enroll_items', 'state', 'VARCHAR(10)')
            added += await add_column_if_not_exists(conn, 'seller_enroll_items', 'zip', 'VARCHAR(20)')
            added += await add_column_if_not_exists(conn, 'seller_enroll_items', 'phone', 'VARCHAR(50)')
            added += await add_column_if_not_exists(conn, 'seller_enroll_items', 'email', 'VARCHAR(200)')
            added += await add_column_if_not_exists(conn, 'seller_enroll_items', 'additional_info', 'TEXT')
            print(f"✅ Added {added} new columns")
            
            # Step 8: Create selfreg_cc_card_names table
            print(f"\n📊 Step 8: Creating selfreg_cc_card_names table...")
            if not await table_exists(conn, 'selfreg_cc_card_names'):
                await conn.execute(text("""
                    CREATE TABLE selfreg_cc_card_names (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        category_id INTEGER NOT NULL REFERENCES selfreg_cc_categories(id) ON DELETE CASCADE,
                        card_name VARCHAR(200) NOT NULL,
                        position INTEGER DEFAULT 0,
                        is_active BOOLEAN DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                await conn.execute(text("CREATE INDEX ix_selfreg_cc_card_names_category_id ON selfreg_cc_card_names(category_id)"))
                print("✅ Table created!")
            else:
                print("⚠️  Table already exists")
            
            # Step 9: Add new categories
            print(f"\n📊 Step 9: Adding new Selfreg CC banks and Elan portal...")
            await conn.execute(text("""
                INSERT OR IGNORE INTO selfreg_cc_categories (code, name, position, is_active, is_custom) VALUES
                ('capital_one', 'Capital One', 5, 1, 0),
                ('discover', 'Discover', 6, 1, 0),
                ('amex', 'American Express', 7, 1, 0),
                ('usbank', 'US Bank', 8, 1, 0),
                ('pnc', 'PNC Bank', 9, 1, 0),
                ('td', 'TD Bank', 10, 1, 0),
                ('barclays', 'Barclays', 11, 1, 0),
                ('synchrony', 'Synchrony', 12, 1, 0)
            """))
            await conn.execute(text("""
                INSERT OR IGNORE INTO enroll_categories (code, name, position, is_active, is_custom) VALUES
                ('elan', 'Elan', 12, 1, 0)
            """))
            print("✅ Categories added!")
            
            # Step 10: Create indexes
            print(f"\n📊 Step 10: Creating performance indexes...")
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_seller_bank_items_category ON seller_bank_items(category)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_seller_bank_items_bank_code ON seller_bank_items(bank_code)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_brute_bank_items_state ON brute_bank_items(state)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_seller_otp_items_state ON seller_otp_items(state)"))
            print("✅ Indexes created!")
        
        # Step 11: Seed card names
        print(f"\n📊 Step 11: Seeding Selfreg CC card names...")
        async with engine.begin() as conn:
            seed_file = project_root / "shared" / "database" / "seeds" / "selfreg_cc_card_names.sql"
            if seed_file.exists():
                seed_sql = seed_file.read_text()
                seed_sql = seed_sql.replace("TRUE", "1").replace("FALSE", "0")
                
                statements = [s.strip() for s in seed_sql.split(';') if s.strip() and 'INSERT' in s.upper()]
                for stmt in statements:
                    stmt = stmt.replace("INSERT INTO", "INSERT OR IGNORE INTO")
                    try:
                        await conn.execute(text(stmt))
                    except Exception as e:
                        print(f"⚠️  Skipping statement (may already exist): {str(e)[:100]}")
                
                print(f"✅ Seeded {len(statements)} card name records!")
            else:
                print("⚠️  Seed file not found")
        
        print("\n🎉 Mini App v2 migration completed successfully!")
        print("\n📋 Summary:")
        print("   ✓ seller_selfreg_ba_items → seller_bank_items")
        print("   ✓ All product tables extended with new fields")
        print("   ✓ Card names table created and seeded")
        print("   ✓ Performance indexes added")
        print("\n🚀 Next steps:")
        print("   1. Update models.py to reflect new schema")
        print("   2. Update backend parsers for new fields")
        print("   3. Update Mini App frontend")
        
    except Exception as e:
        import traceback
        print(f"\n❌ Migration failed: {e}")
        traceback.print_exc()
        raise


if __name__ == "__main__":
    asyncio.run(run_migration())
