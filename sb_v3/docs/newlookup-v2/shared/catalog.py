"""
Shared catalog for Banks - used by seller_bot and mirror_bot.
Returns bank types (id, name) for "Add to existing" flow.
"""
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


async def get_bank_types_for_category(session: AsyncSession, category: str) -> List[Dict]:
    """
    Get bank types for a category - BankItem from DB first, then fallback to hardcoded.
    Returns list of {"id": bank_code, "name": display_name}.
    """
    try:
        from shared.database.models import BankItem

        result = await session.execute(
            select(BankItem).where(
                BankItem.category == category,
                BankItem.is_active == True
            ).order_by(BankItem.position, BankItem.id)
        )
        db_items = result.scalars().all()
        if db_items:
            return [{"id": b.bank_code, "name": b.name} for b in db_items]
    except Exception:
        pass

    # Fallback to hardcoded catalog (must match mirror_bot BankData)
    from shared.catalog_banks import BANK_CATALOG
    return BANK_CATALOG.get(category, [])


def get_bank_by_id_from_catalog(bank_id: str) -> Optional[Dict]:
    """Get bank info by id from hardcoded catalog (for seller bot when no session)."""
    from shared.catalog_banks import BANK_CATALOG
    for items in BANK_CATALOG.values():
        for b in items:
            if b["id"] == bank_id:
                return b
    return None


async def get_bank_name_by_id(session: AsyncSession, bank_id: str) -> Optional[str]:
    """Get bank display name by id - BankItem first, then hardcoded catalog."""
    try:
        from shared.database.models import BankItem
        from sqlalchemy import select
        result = await session.execute(
            select(BankItem.name).where(BankItem.bank_code == bank_id)
        )
        row = result.scalar_one_or_none()
        if row:
            return row
    except Exception:
        pass
    info = get_bank_by_id_from_catalog(bank_id)
    return info["name"] if info else bank_id
