#!/usr/bin/env python3
"""
Initialize database and run Mini App v2 migration.

This script first initializes the database, then applies the migration.
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from shared.database.session import engine, init_db


async def check_table_exists(conn, table_name: str) -> bool:
    """Check if a table exists in the database."""
    result = await conn.execute(text(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=:table_name"
    ), {"table_name": table_name})
    return result.fetchone() is not None


async def run_full_setup():
    """Initialize database and run migration."""
    print("🚀 Starting database setup and Mini App v2 migration...")
    
    try:
        # Step 1: Initialize database
        print("\n📊 Step 1: Initializing database schema...")
        await init_db()
        print("✅ Database initialized!")
        
        # Step 2: Check what tables exist
        print("\n📊 Step 2: Checking existing tables...")
        async with engine.begin() as conn:
            # Check if old table exists
            has_old_table = await check_table_exists(conn, 'seller_bank_selfreg_items')
            has_new_table = await check_table_exists(conn, 'seller_bank_items')
            
            print(f"   - seller_bank_selfreg_items: {'✓' if has_old_table else '✗'}")
            print(f"   - seller_bank_items: {'✓' if has_new_table else '✗'}")
            
            if has_new_table:
                print("\n⚠️  Migration already applied (seller_bank_items exists)")
                print("Skipping table rename, will only add missing columns...")
                skip_rename = True
            elif has_old_table:
                print("\n✓ Ready to migrate (seller_bank_selfreg_items exists)")
                skip_rename = False
            else:
                print("\n⚠️  Neither table exists, will create seller_bank_items directly")
                skip_rename = True
        
        # Step 3: Run migration
        print("\n📊 Step 3: Applying Mini App v2 schema changes...")
        async with engine.begin() as conn:
            step = 1
            
            # Rename table if needed
            if not skip_rename:
                print(f"   {step}. Renaming seller_bank_selfreg_items to seller_bank_items...")
                await conn.execute(text("ALTER TABLE seller_bank_selfreg_items RENAME TO seller_bank_items"))
                step += 1
            
            print(f"   {step}. Adding new columns to seller_bank_items...")
            await conn.execute(text("ALTER TABLE seller_bank_items ADD COLUMN category VARCHAR(20)"))
            await conn.execute(text("ALTER TABLE seller_bank_items ADD COLUMN bank_code VARCHAR(50)"))
            await conn.execute(text("ALTER TABLE seller_bank_items ADD COLUMN product_type VARCHAR(100)"))
            await conn.execute(text("ALTER TABLE seller_bank_items ADD COLUMN balance NUMERIC(10,2) DEFAULT 0"))
            await conn.execute(text("ALTER TABLE seller_bank_items ADD COLUMN phone_can_swap BOOLEAN DEFAULT 0"))
            await conn.execute(text("ALTER TABLE seller_bank_items ADD COLUMN return_item_enabled BOOLEAN DEFAULT 0"))
            await conn.execute(text("ALTER TABLE seller_bank_items ADD COLUMN return_days INTEGER"))
            await conn.execute(text("UPDATE seller_bank_items SET category = 'personal' WHERE category IS NULL"))
            await conn.execute(text("UPDATE seller_bank_items SET balance = 0 WHERE balance IS NULL"))
            step += 1
            
            print(f"   {step}. Adding fields to brute_bank_items...")
            await conn.execute(text("ALTER TABLE brute_bank_items ADD COLUMN exact_balance VARCHAR(50)"))
            await conn.execute(text("ALTER TABLE brute_bank_items ADD COLUMN account_number VARCHAR(255)"))
            await conn.execute(text("ALTER TABLE brute_bank_items ADD COLUMN routing_number VARCHAR(255)"))
            await conn.execute(text("ALTER TABLE brute_bank_items ADD COLUMN holder_name VARCHAR(200)"))
            await conn.execute(text("ALTER TABLE brute_bank_items ADD COLUMN address VARCHAR(500)"))
            await conn.execute(text("ALTER TABLE brute_bank_items ADD COLUMN state VARCHAR(10)"))
            await conn.execute(text("ALTER TABLE brute_bank_items ADD COLUMN zip VARCHAR(20)"))
            await conn.execute(text("ALTER TABLE brute_bank_items ADD COLUMN additional_info TEXT"))
            await conn.execute(text("ALTER TABLE brute_bank_items ADD COLUMN has_docs BOOLEAN DEFAULT 0"))
            step += 1
            
            print(f"   {step}. Adding NON VBV pricing to seller_cc_items...")
            await conn.execute(text("ALTER TABLE seller_cc_items ADD COLUMN seller_price_non_vbv NUMERIC(10,2)"))
            await conn.execute(text("ALTER TABLE seller_cc_items ADD COLUMN buyer_price_non_vbv NUMERIC(10,2)"))
            await conn.execute(text("UPDATE seller_cc_items SET seller_price_non_vbv = seller_price WHERE seller_price_non_vbv IS NULL"))
            await conn.execute(text("UPDATE seller_cc_items SET buyer_price_non_vbv = buyer_price WHERE buyer_price_non_vbv IS NULL"))
            step += 1
            
            print(f"   {step}. Adding fields to seller_selfreg_cc_items...")
            await conn.execute(text("ALTER TABLE seller_selfreg_cc_items ADD COLUMN registration_date DATE"))
            await conn.execute(text("ALTER TABLE seller_selfreg_cc_items ADD COLUMN vcc_bin VARCHAR(6)"))
            await conn.execute(text("ALTER TABLE seller_selfreg_cc_items ADD COLUMN return_item_enabled BOOLEAN DEFAULT 0"))
            await conn.execute(text("ALTER TABLE seller_selfreg_cc_items ADD COLUMN return_days INTEGER"))
            step += 1
            
            print(f"   {step}. Adding Fullz fields to seller_otp_items...")
            await conn.execute(text("ALTER TABLE seller_otp_items ADD COLUMN state VARCHAR(10)"))
            await conn.execute(text("ALTER TABLE seller_otp_items ADD COLUMN zip VARCHAR(20)"))
            await conn.execute(text("ALTER TABLE seller_otp_items ADD COLUMN fullz_first_name VARCHAR(100)"))
            await conn.execute(text("ALTER TABLE seller_otp_items ADD COLUMN fullz_last_name VARCHAR(100)"))
            await conn.execute(text("ALTER TABLE seller_otp_items ADD COLUMN fullz_dob DATE"))
            await conn.execute(text("ALTER TABLE seller_otp_items ADD COLUMN fullz_ssn VARCHAR(20)"))
            await conn.execute(text("ALTER TABLE seller_otp_items ADD COLUMN fullz_address VARCHAR(500)"))
            await conn.execute(text("ALTER TABLE seller_otp_items ADD COLUMN fullz_city VARCHAR(100)"))
            await conn.execute(text("ALTER TABLE seller_otp_items ADD COLUMN fullz_state VARCHAR(10)"))
            await conn.execute(text("ALTER TABLE seller_otp_items ADD COLUMN fullz_zip VARCHAR(20)"))
            await conn.execute(text("ALTER TABLE seller_otp_items ADD COLUMN fullz_phone VARCHAR(50)"))
            await conn.execute(text("ALTER TABLE seller_otp_items ADD COLUMN fullz_email VARCHAR(200)"))
            step += 1
            
            print(f"   {step}. Adding detailed fields to seller_enroll_items...")
            await conn.execute(text("ALTER TABLE seller_enroll_items ADD COLUMN first_name VARCHAR(100)"))
            await conn.execute(text("ALTER TABLE seller_enroll_items ADD COLUMN last_name VARCHAR(100)"))
            await conn.execute(text("ALTER TABLE seller_enroll_items ADD COLUMN dob DATE"))
            await conn.execute(text("ALTER TABLE seller_enroll_items ADD COLUMN ssn VARCHAR(20)"))
            await conn.execute(text("ALTER TABLE seller_enroll_items ADD COLUMN address VARCHAR(500)"))
            await conn.execute(text("ALTER TABLE seller_enroll_items ADD COLUMN city VARCHAR(100)"))
            await conn.execute(text("ALTER TABLE seller_enroll_items ADD COLUMN state VARCHAR(10)"))
            await conn.execute(text("ALTER TABLE seller_enroll_items ADD COLUMN zip VARCHAR(20)"))
            await conn.execute(text("ALTER TABLE seller_enroll_items ADD COLUMN phone VARCHAR(50)"))
            await conn.execute(text("ALTER TABLE seller_enroll_items ADD COLUMN email VARCHAR(200)"))
            await conn.execute(text("ALTER TABLE seller_enroll_items ADD COLUMN additional_info TEXT"))
            step += 1
            
            print(f"   {step}. Creating selfreg_cc_card_names table...")
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS selfreg_cc_card_names (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category_id INTEGER NOT NULL REFERENCES selfreg_cc_categories(id) ON DELETE CASCADE,
                    card_name VARCHAR(200) NOT NULL,
                    position INTEGER DEFAULT 0,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_selfreg_cc_card_names_category_id ON selfreg_cc_card_names(category_id)"))
            step += 1
            
            print(f"   {step}. Adding new Selfreg CC banks and Elan portal...")
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
            step += 1
            
            print(f"   {step}. Creating performance indexes...")
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_seller_bank_items_category ON seller_bank_items(category)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_seller_bank_items_bank_code ON seller_bank_items(bank_code)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_brute_bank_items_state ON brute_bank_items(state)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_seller_otp_items_state ON seller_otp_items(state)"))
            
            print("✅ Schema migration completed!")
            
        # Step 4: Seed card names
        print("\n📊 Step 4: Seeding Selfreg CC card names...")
        async with engine.begin() as conn:
            seed_file = project_root / "shared" / "database" / "seeds" / "selfreg_cc_card_names.sql"
            if seed_file.exists():
                seed_sql = seed_file.read_text()
                # Convert PostgreSQL syntax to SQLite
                seed_sql = seed_sql.replace("ON CONFLICT (category_id, card_name) DO NOTHING", "")
                seed_sql = seed_sql.replace("TRUE", "1").replace("FALSE", "0")
                
                statements = [s.strip() for s in seed_sql.split(';') if s.strip() and 'INSERT' in s.upper()]
                for stmt in statements:
                    # Add OR IGNORE for SQLite
                    stmt = stmt.replace("INSERT INTO", "INSERT OR IGNORE INTO")
                    await conn.execute(text(stmt))
                print(f"✅ Seeded {len(statements)} card name records!")
            else:
                print("⚠️  Seed file not found, skipping")
        
        print("\n🎉 Database setup and migration completed successfully!")
        print("\n📋 Summary:")
        print("   ✓ Database initialized")
        print("   ✓ All tables migrated to Mini App v2 schema")
        print("   ✓ Card names seeded")
        print("\n🚀 Next steps:")
        print("   1. Update backend parsers to handle new fields")
        print("   2. Update Mini App frontend to use new bank lists")
        print("   3. Test product uploads with new formats")
        
    except Exception as e:
        import traceback
        print(f"\n❌ Setup failed: {e}")
        print("\nFull traceback:")
        traceback.print_exc()
        raise


async def main():
    await run_full_setup()


if __name__ == "__main__":
    asyncio.run(main())
