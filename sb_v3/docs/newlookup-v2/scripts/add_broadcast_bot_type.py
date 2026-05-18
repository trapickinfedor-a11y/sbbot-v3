#!/usr/bin/env python3
"""
Migration script to add bot_type column to broadcasts table
Run this once to add the new column for existing database
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "newlookup.db"

def add_bot_type_column():
    """Add bot_type column to broadcasts table if it doesn't exist"""
    if not DB_PATH.exists():
        print(f"❌ Database not found at {DB_PATH}")
        return False
    
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(broadcasts)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if "bot_type" in columns:
            print("✅ bot_type column already exists")
            return True
        
        # Add the column
        cursor.execute("""
            ALTER TABLE broadcasts
            ADD COLUMN bot_type VARCHAR(20)
        """)
        conn.commit()
        print("✅ Successfully added bot_type column to broadcasts table")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    print("🔧 Running broadcast bot_type migration...")
    success = add_bot_type_column()
    if success:
        print("✅ Migration completed successfully")
    else:
        print("❌ Migration failed")
        exit(1)
