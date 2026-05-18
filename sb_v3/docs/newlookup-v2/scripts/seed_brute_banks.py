#!/usr/bin/env python3
"""
Seed script to preload 70+ Brute Bank groups from user-provided list.

Format: BankName [Attributes] [Count]
Example: 3RiversFCU [AN:RN] [3]
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from shared.database.session import async_session_maker
from shared.database.models import BruteBankGroup
from shared.brute_bank_group_key import make_brute_group_key


BRUTE_BANKS_DATA = """
3RiversFCU [AN:RN] [3]
53 [AN:RN+INST YODLEE+INST FINICITY] [1439]
53 [AN:RN+INST YODLEE+INST FINICITY+NAME+ADRESS] [26]
AllianceCCU [AN:RN] [3]
BECU [AN:RN+INST FINICITY] [13]
Bellco [AN:RN+INST FINICITY] [1]
BMO [AN:RN+INST YODLEE] [242]
BMO [AN:RN+INST YODLEE+NAME+ADRESS] [26]
Canvas [AN:RN+INST FINICITY] [2]
CentraCU [AN:RN] [2]
Comerica [AN:RN+INST YODLEE+INST FINICITY+NAME] [1]
Connexuscu [AN:RN+INST FINICITY] [1]
CorningCU [AN:RN+INST FINICITY+NAME] [3]
DesertfinancialCU [AN:RN+INST FINICITY] [2]
DFCUFinancial [AN:RN] [19]
DiscoverBank [AN:RN] [172]
EducatorsCU [AN:RN+INST FINICITY] [2]
EmpowerFCU [AN:RN+INST FINICITY] [1]
EnrichmentFCU [AN:RN+INST FINICITY] [1]
FACU [AN:RN] [1]
Familytrust [AN:RN+INST FINICITY] [1]
FibreFCU [AN:RN+INST FINICITY] [1]
FirstentCU [AN:RN] [2]
FloridaCU [AN:RN+INST FINICITY] [46]
FNBO [AN:RN] [2]
FourLeafFCU [AN:RN+INST FINICITY] [2]
GlobalCU [AN:RN+INST FINICITY] [66]
GoldenwestCU [AN:RN+INST FINICITY] [3]
GrowFinancalFCU [AN:RN+INST FINICITY] [22]
GTE [AN:RN+INST YODLEE] [355]
HarboreOne [AN:RN+INST YODLEE+INST FINICITY] [2]
Huntington [AN:RN+INST YODLEE] [12]
HVCU [AN:RN+INST FINICITY] [11]
Jeffersonfinancial [AN:RN+INST FINICITY] [1]
KFCU [AN:RN+INST FINICITY] [2]
Kinecta [AN:RN+INST FINICITY] [1]
Landmarkcu [INST FINICITY] [8]
MACU [AN:RN+INST FINICITY] [4]
MaineStateCU [AN:RN+INST FINICITY] [1]
Members1st [AN:RN+INST YODLEE+INST FINICITY] [82]
Members1st [AN:RN+INST YODLEE+INST FINICITY+NAME] [26]
Members1st [AN:RN+INST YODLEE+INST FINICITY+NAME+ADR] [18]
MSUFCU [AN:RN+INST FINICITY] [9]
MSUFCU [AN:RN+INST YODLEE+INST FINICITY] [18]
myoccu [AN:RN+INST FINICITY] [8]
NasaFCU [AN:RN+INST FINICITY] [1]
PacificCrestFCU [INST FINICITY] [7]
Parkcommunity [AN:RN+INST FINICITY] [1]
Patelco [AN:RN+INST FINICITY] [1]
Pefcu [AN:RN+NAME+ADRESS] [22]
PSFCU [AN:RN+INST FINICITY] [1]
QualstarCU [AN:RN+INST FINICITY] [1]
Radiantcu [AN:RN+INST FINICITY] [1]
REVFCU [AN:RN+INST FINICITY] [1]
RivermarkCCU [INST FINICITY] [2]
Santanderbank [AN:RN+INST YODLEE+INST FINICITY] [2]
Santanderbank [AN:RN+INST YODLEE+INST FINICITY+NAME] [1]
SchoolsFirst [AN:RN+INST FINICITY] [2]
SchoolsFirst [AN:RN+INST FINICITY+NAME+ADRESS] [1]
SkylaCU [AN:RN+INST FINICITY] [4]
Sunward [AN:RN+INST FINICITY] [1]
Synovus [AN:RN+INST YODLEE+INST FINICITY] [1]
UnitusCCU [AN:RN+INST FINICITY] [4]
ValleyStrong [AN:RN+INST FINICITY] [5]
VantageWest [AN:RN+INST FINICITY] [8]
VeridianCU [AN:RN+INST FINICITY] [4]
WescomCU [AN:RN+ONLINE ACCESS+NAME+ADRESS] [5]
"""


def parse_brute_bank_line(line: str) -> Optional[dict]:
    """
    Parse a line like: BankName [Attributes] [Count]
    Returns: {"bank_name": str, "attributes": str, "count": int}
    """
    line = line.strip()
    if not line:
        return None
    
    # Extract bank name (everything before first [)
    if "[" not in line:
        return None
    
    bank_name = line.split("[")[0].strip()
    
    # Extract attributes (between first [ and second [)
    parts = line.split("[")
    if len(parts) < 2:
        return None
    
    attributes_part = parts[1].split("]")[0].strip() if "]" in parts[1] else ""
    
    # Extract count (between last [ and ])
    count = 1
    if len(parts) >= 3:
        count_part = parts[-1].split("]")[0].strip()
        try:
            count = int(count_part)
        except ValueError:
            count = 1
    
    return {
        "bank_name": bank_name,
        "attributes": attributes_part if attributes_part else None,
        "count": count,
    }


async def seed_brute_banks():
    """Seed Brute Bank groups from the provided list."""
    async with async_session_maker() as session:
        lines = [line.strip() for line in BRUTE_BANKS_DATA.strip().splitlines() if line.strip()]
        
        created_count = 0
        skipped_count = 0
        
        for line in lines:
            parsed = parse_brute_bank_line(line)
            if not parsed:
                print(f"⚠️  Skipped invalid line: {line}")
                skipped_count += 1
                continue
            
            bank_name = parsed["bank_name"]
            attributes = parsed["attributes"]
            count = parsed["count"]
            
            # Generate bank_code from bank_name
            bank_code = bank_name.lower().replace(" ", "_").replace("-", "_")
            bank_code = "".join(c for c in bank_code if c.isalnum() or c == "_")
            
            # Default category to personal (can be updated by admin later)
            category = "personal"
            
            # Generate group key
            group_key = make_brute_group_key(bank_code, attributes)
            
            # Check if already exists
            existing = await session.scalar(
                select(BruteBankGroup).where(BruteBankGroup.group_key == group_key)
            )
            
            if existing:
                print(f"⏭️  Skipped (exists): {bank_name} [{attributes or 'no attrs'}]")
                skipped_count += 1
                continue
            
            # Create new group
            group = BruteBankGroup(
                group_key=group_key,
                bank_code=bank_code,
                bank_name=bank_name,
                category=category,
                attributes=attributes,
                position=created_count,
                is_active=True,
            )
            
            session.add(group)
            print(f"✅ Created: {bank_name} [{attributes or 'no attrs'}] (count: {count})")
            created_count += 1
        
        await session.commit()
        
        print(f"\n{'='*60}")
        print(f"✅ Seeding complete!")
        print(f"   Created: {created_count}")
        print(f"   Skipped: {skipped_count}")
        print(f"   Total:   {created_count + skipped_count}")
        print(f"{'='*60}")


if __name__ == "__main__":
    print("🔓 Seeding Brute Bank Groups...")
    print(f"{'='*60}\n")
    asyncio.run(seed_brute_banks())
