#!/usr/bin/env python3
"""
Seed Selfreg CC categories and card names.
Direct seeding script with proper transaction handling.
"""
import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from shared.database.session import engine


async def seed_all():
    """Seed categories and card names."""
    print("🌱 Starting seeding process...")
    
    try:
        # Step 1: Seed Selfreg CC categories
        print("\n📊 Step 1: Seeding Selfreg CC categories...")
        async with engine.begin() as conn:
            await conn.execute(text("""
                INSERT OR IGNORE INTO selfreg_cc_categories (code, name, position, is_active, is_custom, created_at) VALUES
                ('chase', 'Chase', 1, 1, 0, datetime('now')),
                ('citi', 'Citi', 2, 1, 0, datetime('now')),
                ('bofa', 'Bank of America', 3, 1, 0, datetime('now')),
                ('wells_fargo', 'Wells Fargo', 4, 1, 0, datetime('now')),
                ('capital_one', 'Capital One', 5, 1, 0, datetime('now')),
                ('discover', 'Discover', 6, 1, 0, datetime('now')),
                ('amex', 'American Express', 7, 1, 0, datetime('now')),
                ('usbank', 'US Bank', 8, 1, 0, datetime('now')),
                ('pnc', 'PNC Bank', 9, 1, 0, datetime('now')),
                ('td', 'TD Bank', 10, 1, 0, datetime('now')),
                ('barclays', 'Barclays', 11, 1, 0, datetime('now')),
                ('synchrony', 'Synchrony', 12, 1, 0, datetime('now'))
            """))
            
            result = await conn.execute(text("SELECT COUNT(*) FROM selfreg_cc_categories"))
            count = result.scalar()
            print(f"✅ Seeded {count} categories")
        
        # Step 2: Seed Enroll categories (add Elan)
        print("\n📊 Step 2: Adding Elan to Enroll categories...")
        async with engine.begin() as conn:
            await conn.execute(text("""
                INSERT OR IGNORE INTO enroll_categories (code, name, position, is_active, is_custom, created_at) VALUES
                ('elan', 'Elan', 12, 1, 0, datetime('now'))
            """))
            
            result = await conn.execute(text("SELECT COUNT(*) FROM enroll_categories"))
            count = result.scalar()
            print(f"✅ Total enroll categories: {count}")
        
        # Step 3: Seed card names
        print("\n📊 Step 3: Seeding card names...")
        async with engine.begin() as conn:
            # Get category IDs
            result = await conn.execute(text("SELECT id, code FROM selfreg_cc_categories ORDER BY position"))
            categories = {row[1]: row[0] for row in result}
            
            if not categories:
                print("❌ No categories found! Cannot seed card names.")
                return
            
            print(f"Found {len(categories)} categories")
            
            # Seed card names for each category
            card_data = {
                'chase': ['Freedom Unlimited', 'Freedom Flex', 'Sapphire Preferred', 'Sapphire Reserve', 'Ink Business Cash', 'Ink Business Unlimited'],
                'citi': ['Double Cash', 'Custom Cash', 'Premier', 'Rewards+', 'Diamond Preferred', 'Simplicity'],
                'bofa': ['Cash Rewards', 'Customized Cash Rewards', 'Unlimited Cash Rewards', 'Premium Rewards', 'Travel Rewards', 'Business Advantage Cash Rewards'],
                'wells_fargo': ['Active Cash', 'Reflect', 'Autograph', 'Attune', 'Business Platinum', 'Business Elite'],
                'capital_one': ['Quicksilver', 'Venture', 'Venture X', 'SavorOne', 'Spark Cash', 'Spark Miles'],
                'discover': ['it Cash Back', 'it Chrome', 'it Miles', 'it Student Cash Back', 'it Student Chrome', 'it Secured'],
                'amex': ['Gold Card', 'Platinum Card', 'Green Card', 'Blue Cash Preferred', 'Blue Cash Everyday', 'Cash Magnet'],
                'usbank': ['Cash+', 'Altitude Go', 'Altitude Reserve', 'Shopper Cash Rewards', 'Business Cash Rewards', 'Business Leverage'],
                'pnc': ['Cash Rewards', 'Cash Rewards Secured', 'Points', 'Core', 'Premier Traveler', 'Cash Unlimited'],
                'td': ['Double Up', 'Cash', 'Travel', 'Business Cash', 'Business Travel', 'Aeroplan'],
                'barclays': ['Arrival Plus', 'Arrival', 'Rewards', 'CashForward', 'Financing Visa', 'Business Aviator'],
                'synchrony': ['Premier', 'Dual', 'Smart', 'Value', 'Secured', 'Home']
            }
            
            inserted = 0
            for code, cards in card_data.items():
                if code in categories:
                    cat_id = categories[code]
                    for pos, card_name in enumerate(cards, 1):
                        await conn.execute(text("""
                            INSERT OR IGNORE INTO selfreg_cc_card_names 
                            (category_id, card_name, position, is_active, created_at) 
                            VALUES (:cat_id, :card_name, :pos, 1, datetime('now'))
                        """), {"cat_id": cat_id, "card_name": card_name, "pos": pos})
                        inserted += 1
            
            result = await conn.execute(text("SELECT COUNT(*) FROM selfreg_cc_card_names"))
            count = result.scalar()
            print(f"✅ Seeded {count} card names (attempted {inserted} inserts)")
        
        # Step 4: Verify
        print("\n📊 Step 4: Verification...")
        async with engine.begin() as conn:
            result = await conn.execute(text("""
                SELECT c.name, COUNT(cn.id) as card_count 
                FROM selfreg_cc_categories c 
                LEFT JOIN selfreg_cc_card_names cn ON c.id = cn.category_id 
                GROUP BY c.id, c.name 
                ORDER BY c.position
            """))
            
            print("\nCard names per category:")
            for row in result:
                print(f"  {row[0]}: {row[1]} cards")
        
        print("\n🎉 Seeding completed successfully!")
        
    except Exception as e:
        import traceback
        print(f"\n❌ Seeding failed: {e}")
        traceback.print_exc()
        raise


if __name__ == "__main__":
    asyncio.run(seed_all())
