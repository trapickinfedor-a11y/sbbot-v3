#!/usr/bin/env python3
"""
Rollback Mini App v2 database migration.

This script reverts the sync_mini_app_v2 migration changes.
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from shared.database.session import engine
from shared.database.migrations.sync_mini_app_v2 import downgrade


async def run_rollback():
    """Rollback the Mini App v2 migration."""
    print("⏪ Starting Mini App v2 migration rollback...")
    
    try:
        async with engine.begin() as conn:
            print("📊 Reverting schema changes...")
            await conn.run_sync(downgrade)
            print("✅ Schema rollback completed successfully!")
            
        print("\n⚠️  Note: Card names data was not deleted (manual cleanup required if needed)")
        print("\n🎉 Mini App v2 migration rollback completed!")
        
    except Exception as e:
        print(f"\n❌ Rollback failed: {e}")
        raise


async def main():
    await run_rollback()


if __name__ == "__main__":
    asyncio.run(main())
