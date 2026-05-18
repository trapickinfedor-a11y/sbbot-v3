#!/usr/bin/env python3
"""
Run Mini App v2 database migration.

This script applies the sync_mini_app_v2 migration and seeds the card names table.
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from shared.database.session import engine


async def run_migration():
    """Apply the Mini App v2 migration."""
    print("🚀 Starting Mini App v2 migration...")
    
    try:
        async with engine.begin() as conn:
            print("📊 Step 1/10: Renaming seller_bank_selfreg_items to seller_bank_items...")
            await conn.execute(text("ALTER TABLE seller_bank_selfreg_items RENAME TO seller_bank_items"))
            
            print("📊 Step 2/10: Adding new columns to seller_bank_items...")
            await conn.execute(text("ALTER TABLE seller_bank_items ADD COLUMN IF NOT EXISTS category VARCHAR(20)"))
            await conn.execute(text("ALTER TABLE seller_bank_items ADD COLUMN IF NOT EXISTS bank_code VARCHAR(50)"))
            await conn.execute(text("ALTER TABLE seller_bank_items ADD COLUMN IF NOT EXISTS product_type VARCHAR(100)"))
            await conn.execute(text("ALTER TABLE seller_bank_items ADD COLUMN IF NOT EXISTS balance NUMERIC(10,2) DEFAULT 0"))
            await conn.execute(text("ALTER TABLE seller_bank_items ADD COLUMN IF NOT EXISTS phone_can_swap BOOLEAN DEFAULT FALSE"))
            await conn.execute(text("ALTER TABLE seller_bank_items ADD COLUMN IF NOT EXISTS return_item_enabled BOOLEAN DEFAULT FALSE"))
            await conn.execute(text("ALTER TABLE seller_bank_items ADD COLUMN IF NOT EXISTS return_days INTEGER"))
            await conn.execute(text("UPDATE seller_bank_items SET category = 'personal' WHERE category IS NULL"))
            await conn.execute(text("UPDATE seller_bank_items SET balance = 0 WHERE balance IS NULL"))
            
            print("📊 Step 3/10: Adding fields to brute_bank_items...")
            await conn.execute(text("ALTER TABLE brute_bank_items ADD COLUMN IF NOT EXISTS exact_balance VARCHAR(50)"))
            await conn.execute(text("ALTER TABLE brute_bank_items ADD COLUMN IF NOT EXISTS account_number VARCHAR(255)"))
            await conn.execute(text("ALTER TABLE brute_bank_items ADD COLUMN IF NOT EXISTS routing_number VARCHAR(255)"))
            await conn.execute(text("ALTER TABLE brute_bank_items ADD COLUMN IF NOT EXISTS holder_name VARCHAR(200)"))
            await conn.execute(text("ALTER TABLE brute_bank_items ADD COLUMN IF NOT EXISTS address VARCHAR(500)"))
            await conn.execute(text("ALTER TABLE brute_bank_items ADD COLUMN IF NOT EXISTS state VARCHAR(10)"))
            await conn.execute(text("ALTER TABLE brute_bank_items ADD COLUMN IF NOT EXISTS zip VARCHAR(20)"))
            await conn.execute(text("ALTER TABLE brute_bank_items ADD COLUMN IF NOT EXISTS additional_info TEXT"))
            await conn.execute(text("ALTER TABLE brute_bank_items ADD COLUMN IF NOT EXISTS has_docs BOOLEAN DEFAULT FALSE"))
            
            print("📊 Step 4/10: Adding NON VBV pricing to seller_cc_items...")
            await conn.execute(text("ALTER TABLE seller_cc_items ADD COLUMN IF NOT EXISTS seller_price_non_vbv NUMERIC(10,2)"))
            await conn.execute(text("ALTER TABLE seller_cc_items ADD COLUMN IF NOT EXISTS buyer_price_non_vbv NUMERIC(10,2)"))
            await conn.execute(text("UPDATE seller_cc_items SET seller_price_non_vbv = seller_price WHERE seller_price_non_vbv IS NULL"))
            await conn.execute(text("UPDATE seller_cc_items SET buyer_price_non_vbv = buyer_price WHERE buyer_price_non_vbv IS NULL"))
            
            print("📊 Step 5/10: Adding fields to seller_selfreg_cc_items...")
            await conn.execute(text("ALTER TABLE seller_selfreg_cc_items ADD COLUMN IF NOT EXISTS registration_date DATE"))
            await conn.execute(text("ALTER TABLE seller_selfreg_cc_items ADD COLUMN IF NOT EXISTS vcc_bin VARCHAR(6)"))
            await conn.execute(text("ALTER TABLE seller_selfreg_cc_items ADD COLUMN IF NOT EXISTS return_item_enabled BOOLEAN DEFAULT FALSE"))
            await conn.execute(text("ALTER TABLE seller_selfreg_cc_items ADD COLUMN IF NOT EXISTS return_days INTEGER"))
            
            print("📊 Step 6/10: Adding Fullz fields to seller_otp_items...")
            await conn.execute(text("ALTER TABLE seller_otp_items ADD COLUMN IF NOT EXISTS state VARCHAR(10)"))
            await conn.execute(text("ALTER TABLE seller_otp_items ADD COLUMN IF NOT EXISTS zip VARCHAR(20)"))
            await conn.execute(text("ALTER TABLE seller_otp_items ADD COLUMN IF NOT EXISTS fullz_first_name VARCHAR(100)"))
            await conn.execute(text("ALTER TABLE seller_otp_items ADD COLUMN IF NOT EXISTS fullz_last_name VARCHAR(100)"))
            await conn.execute(text("ALTER TABLE seller_otp_items ADD COLUMN IF NOT EXISTS fullz_dob DATE"))
            await conn.execute(text("ALTER TABLE seller_otp_items ADD COLUMN IF NOT EXISTS fullz_ssn VARCHAR(20)"))
            await conn.execute(text("ALTER TABLE seller_otp_items ADD COLUMN IF NOT EXISTS fullz_address VARCHAR(500)"))
            await conn.execute(text("ALTER TABLE seller_otp_items ADD COLUMN IF NOT EXISTS fullz_city VARCHAR(100)"))
            await conn.execute(text("ALTER TABLE seller_otp_items ADD COLUMN IF NOT EXISTS fullz_state VARCHAR(10)"))
            await conn.execute(text("ALTER TABLE seller_otp_items ADD COLUMN IF NOT EXISTS fullz_zip VARCHAR(20)"))
            await conn.execute(text("ALTER TABLE seller_otp_items ADD COLUMN IF NOT EXISTS fullz_phone VARCHAR(50)"))
            await conn.execute(text("ALTER TABLE seller_otp_items ADD COLUMN IF NOT EXISTS fullz_email VARCHAR(200)"))
            
            print("📊 Step 7/10: Adding detailed fields to seller_enroll_items...")
            await conn.execute(text("ALTER TABLE seller_enroll_items ADD COLUMN IF NOT EXISTS first_name VARCHAR(100)"))
            await conn.execute(text("ALTER TABLE seller_enroll_items ADD COLUMN IF NOT EXISTS last_name VARCHAR(100)"))
            await conn.execute(text("ALTER TABLE seller_enroll_items ADD COLUMN IF NOT EXISTS dob DATE"))
            await conn.execute(text("ALTER TABLE seller_enroll_items ADD COLUMN IF NOT EXISTS ssn VARCHAR(20)"))
            await conn.execute(text("ALTER TABLE seller_enroll_items ADD COLUMN IF NOT EXISTS address VARCHAR(500)"))
            await conn.execute(text("ALTER TABLE seller_enroll_items ADD COLUMN IF NOT EXISTS city VARCHAR(100)"))
            await conn.execute(text("ALTER TABLE seller_enroll_items ADD COLUMN IF NOT EXISTS state VARCHAR(10)"))
            await conn.execute(text("ALTER TABLE seller_enroll_items ADD COLUMN IF NOT EXISTS zip VARCHAR(20)"))
            await conn.execute(text("ALTER TABLE seller_enroll_items ADD COLUMN IF NOT EXISTS phone VARCHAR(50)"))
            await conn.execute(text("ALTER TABLE seller_enroll_items ADD COLUMN IF NOT EXISTS email VARCHAR(200)"))
            await conn.execute(text("ALTER TABLE seller_enroll_items ADD COLUMN IF NOT EXISTS additional_info TEXT"))
            
            print("📊 Step 8/10: Creating selfreg_cc_card_names table...")
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS selfreg_cc_card_names (
                    id SERIAL PRIMARY KEY,
                    category_id INTEGER NOT NULL REFERENCES selfreg_cc_categories(id) ON DELETE CASCADE,
                    card_name VARCHAR(200) NOT NULL,
                    position INTEGER DEFAULT 0,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_selfreg_cc_card_names_category_id ON selfreg_cc_card_names(category_id)"))
            
            print("📊 Step 9/10: Adding new Selfreg CC banks and Elan portal...")
            await conn.execute(text("""
                INSERT INTO selfreg_cc_categories (code, name, position, is_active, is_custom) VALUES
                ('capital_one', 'Capital One', 5, TRUE, FALSE),
                ('discover', 'Discover', 6, TRUE, FALSE),
                ('amex', 'American Express', 7, TRUE, FALSE),
                ('usbank', 'US Bank', 8, TRUE, FALSE),
                ('pnc', 'PNC Bank', 9, TRUE, FALSE),
                ('td', 'TD Bank', 10, TRUE, FALSE),
                ('barclays', 'Barclays', 11, TRUE, FALSE),
                ('synchrony', 'Synchrony', 12, TRUE, FALSE)
                ON CONFLICT (code) DO NOTHING
            """))
            await conn.execute(text("""
                INSERT INTO enroll_categories (code, name, position, is_active, is_custom) VALUES
                ('elan', 'Elan', 12, TRUE, FALSE)
                ON CONFLICT (code) DO NOTHING
            """))
            
            print("📊 Step 10/10: Creating performance indexes...")
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_seller_bank_items_category ON seller_bank_items(category)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_seller_bank_items_bank_code ON seller_bank_items(bank_code)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_brute_bank_items_state ON brute_bank_items(state)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_seller_otp_items_state ON seller_otp_items(state)"))
            
            print("✅ Schema migration completed successfully!")
            
        print("\n📝 Seeding Selfreg CC card names...")
        async with engine.begin() as conn:
            # Read and execute the seed SQL
            seed_file = project_root / "shared" / "database" / "seeds" / "selfreg_cc_card_names.sql"
            if seed_file.exists():
                seed_sql = seed_file.read_text()
                # Split by semicolons and execute each statement
                statements = [s.strip() for s in seed_sql.split(';') if s.strip()]
                for stmt in statements:
                    await conn.execute(text(stmt))
                print(f"✅ Seeded {len(statements)} card name records!")
            else:
                print("⚠️  Seed file not found, skipping card names seeding")
        
        print("\n🎉 Mini App v2 migration completed successfully!")
        print("\nNext steps:")
        print("1. Update backend parsers to handle new fields")
        print("2. Update Mini App frontend to use new bank lists")
        print("3. Test product uploads with new formats")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        print("\nTo rollback, run: python3 scripts/rollback_mini_app_v2_migration.py")
        raise


async def main():
    await run_migration()


if __name__ == "__main__":
    asyncio.run(main())
