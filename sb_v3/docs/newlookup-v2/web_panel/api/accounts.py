"""
API for Accounts / Subscriptions catalog management
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List
from pydantic import BaseModel
from decimal import Decimal
from datetime import datetime, timezone

from web_panel.database import get_db
from web_panel.auth import require_catalog_read_access, require_catalog_write_access
from shared.database.models import AccountCategory, AccountItem, AccountInventory
from sqlalchemy import func

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None


class ReorderPayload(BaseModel):
    ids: List[int]


class ItemCreate(BaseModel):
    code: str
    name: str
    category_code: str
    price: float
    duration_months: Optional[int] = None
    description: Optional[str] = None
    is_active: bool = True
    position: int = 0


class ItemUpdate(BaseModel):
    name: Optional[str] = None
    category_code: Optional[str] = None
    price: Optional[float] = None
    duration_months: Optional[int] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    position: Optional[int] = None


class InventoryUpload(BaseModel):
    item_id: int
    entries: List[dict]
    notes: Optional[str] = None


class ManualIssue(BaseModel):
    inventory_id: int
    user_id: int


# ── Categories ────────────────────────────────────────────────────────────────

@router.get("/categories")
async def list_categories(
    category_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_catalog_read_access("accounts"))
):
    stmt = select(AccountCategory).order_by(AccountCategory.position, AccountCategory.id)
    if category_type:
        stmt = stmt.where(AccountCategory.category_type == category_type)
    result = await db.execute(stmt)
    cats = result.scalars().all()
    return [
        {
            "id": c.id, "code": c.code, "name": c.name,
            "category_type": c.category_type, "position": c.position,
            "is_active": c.is_active, "created_at": c.created_at.isoformat()
        }
        for c in cats
    ]


@router.put("/categories/reorder")
async def reorder_categories(
    data: ReorderPayload,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_catalog_write_access("accounts"))
):
    for pos, cat_id in enumerate(data.ids):
        result = await db.execute(select(AccountCategory).where(AccountCategory.id == cat_id))
        cat = result.scalar_one_or_none()
        if cat:
            cat.position = pos
    await db.commit()
    return {"ok": True}


@router.put("/categories/{cat_id}")
async def update_category(
    cat_id: int,
    data: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_catalog_write_access("accounts"))
):
    """Only name and is_active can be edited. Categories are predefined in code."""
    result = await db.execute(select(AccountCategory).where(AccountCategory.id == cat_id))
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    if data.name is not None:
        cat.name = data.name
    if data.is_active is not None:
        cat.is_active = data.is_active
    await db.commit()
    return {"ok": True}


# ── Items ─────────────────────────────────────────────────────────────────────

@router.get("/items")
async def list_items(
    category_code: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_catalog_read_access("accounts"))
):
    stmt = select(AccountItem).order_by(AccountItem.category_code, AccountItem.position, AccountItem.id)
    if category_code:
        stmt = stmt.where(AccountItem.category_code == category_code)
    result = await db.execute(stmt)
    items = result.scalars().all()
    return [
        {
            "id": i.id, "code": i.code, "name": i.name,
            "category_code": i.category_code, "price": float(i.price),
            "duration_months": i.duration_months, "description": i.description,
            "is_active": i.is_active, "position": i.position,
            "created_at": i.created_at.isoformat()
        }
        for i in items
    ]


@router.post("/items")
async def create_item(
    data: ItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_catalog_write_access("accounts"))
):
    existing = await db.execute(select(AccountItem).where(AccountItem.code == data.code))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Item code already exists")
    item = AccountItem(**data.model_dump())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return {"id": item.id, "code": item.code, "name": item.name}


@router.put("/items/reorder")
async def reorder_items(
    data: ReorderPayload,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_catalog_write_access("accounts"))
):
    """Set item positions based on ordered list of IDs."""
    for pos, item_id in enumerate(data.ids):
        result = await db.execute(select(AccountItem).where(AccountItem.id == item_id))
        item = result.scalar_one_or_none()
        if item:
            item.position = pos
    await db.commit()
    return {"ok": True}


@router.put("/items/{item_id}")
async def update_item(
    item_id: int,
    data: ItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_catalog_write_access("accounts"))
):
    result = await db.execute(select(AccountItem).where(AccountItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(item, k, v)
    item.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return {"ok": True}


@router.delete("/items/{item_id}")
async def delete_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_catalog_write_access("accounts"))
):
    result = await db.execute(select(AccountItem).where(AccountItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    await db.delete(item)
    await db.commit()
    return {"ok": True}


@router.post("/items/{item_id}/toggle")
async def toggle_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_catalog_write_access("accounts"))
):
    result = await db.execute(select(AccountItem).where(AccountItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    item.is_active = not item.is_active
    await db.commit()
    return {"ok": True, "is_active": item.is_active}


@router.post("/seed")
async def seed_accounts(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_catalog_write_access("accounts"))
):
    """Seed default categories and items"""
    default_categories = [
        {"code": "background", "name": "Background Accounts", "category_type": "background", "position": 1},
        {"code": "lookup_ba", "name": "Lookup BA", "category_type": "lookup_ba", "position": 2},
        {"code": "email", "name": "Email Accounts", "category_type": "email", "position": 3},
        {"code": "ai", "name": "AI Accounts", "category_type": "ai", "position": 4},
        {"code": "proxy", "name": "Proxy / VPN", "category_type": "proxy", "position": 5},
    ]
    default_items = [
        # Background Accounts
        {"code": "beenverified_1m", "name": "BeenVerified", "category_code": "background", "price": 13.00, "duration_months": 1},
        {"code": "truthfinder_1m", "name": "TruthFinder", "category_code": "background", "price": 10.00, "duration_months": 1},
        {"code": "instantcheckmate_1m", "name": "InstantCheckmate", "category_code": "background", "price": 10.00, "duration_months": 1},
        {"code": "intelius_1m", "name": "Intelius", "category_code": "background", "price": 12.00, "duration_months": 1},
        {"code": "whitepages_1m", "name": "WhitePages", "category_code": "background", "price": 13.00, "duration_months": 1},
        {"code": "mylife_1m", "name": "MyLife", "category_code": "background", "price": 10.00, "duration_months": 1},
        {"code": "intelius_30d", "name": "Intelius 30 days", "category_code": "background", "price": 39.00, "duration_months": 1},
        {"code": "truthfinder_30d", "name": "TruthFinder 30 days", "category_code": "background", "price": 39.00, "duration_months": 1},
        {"code": "instantcheckmate_30d", "name": "InstantCheckmate 30 days", "category_code": "background", "price": 35.00, "duration_months": 1},
        {"code": "whitepages_30d", "name": "Whitepages 30 days", "category_code": "background", "price": 45.00, "duration_months": 1},
        # Lookup BA
        {"code": "monarch_money", "name": "Monarch Money", "category_code": "lookup_ba", "price": 15.00, "duration_months": 1},
        {"code": "yodlee", "name": "Yodlee", "category_code": "lookup_ba", "price": 15.00, "duration_months": 1},
        {"code": "empower", "name": "Empower", "category_code": "lookup_ba", "price": 12.00, "duration_months": 1},
        {"code": "pocketguard", "name": "PocketGuard", "category_code": "lookup_ba", "price": 12.00, "duration_months": 1},
        {"code": "everydollar", "name": "EveryDollar", "category_code": "lookup_ba", "price": 12.00, "duration_months": 1},
        # Email Accounts
        {"code": "gmail_acc", "name": "Gmail", "category_code": "email", "price": 5.00, "duration_months": None},
        {"code": "outlook_acc", "name": "Outlook / Hotmail", "category_code": "email", "price": 5.00, "duration_months": None},
        {"code": "yahoo_acc", "name": "Yahoo Mail", "category_code": "email", "price": 4.00, "duration_months": None},
        {"code": "icloud_acc", "name": "iCloud", "category_code": "email", "price": 8.00, "duration_months": None},
        {"code": "protonmail_acc", "name": "ProtonMail", "category_code": "email", "price": 6.00, "duration_months": None},
        {"code": "aol_acc", "name": "AOL Mail", "category_code": "email", "price": 4.00, "duration_months": None},
        # AI Accounts
        {"code": "chatgpt_plus", "name": "ChatGPT Plus", "category_code": "ai", "price": 12.00, "duration_months": 1},
        {"code": "midjourney", "name": "Midjourney", "category_code": "ai", "price": 15.00, "duration_months": 1},
        {"code": "claude_pro", "name": "Claude Pro", "category_code": "ai", "price": 14.00, "duration_months": 1},
        {"code": "github_copilot", "name": "GitHub Copilot", "category_code": "ai", "price": 10.00, "duration_months": 1},
        {"code": "gemini_advanced", "name": "Gemini Advanced", "category_code": "ai", "price": 10.00, "duration_months": 1},
        # Proxy / VPN
        {"code": "nordvpn", "name": "NordVPN", "category_code": "proxy", "price": 8.00, "duration_months": 1},
        {"code": "expressvpn", "name": "ExpressVPN", "category_code": "proxy", "price": 10.00, "duration_months": 1},
        {"code": "surfshark", "name": "Surfshark", "category_code": "proxy", "price": 6.00, "duration_months": 1},
        {"code": "ipvanish", "name": "IPVanish", "category_code": "proxy", "price": 7.00, "duration_months": 1},
        {"code": "911s5_proxy", "name": "911 S5 Proxy", "category_code": "proxy", "price": 15.00, "duration_months": 1},
    ]

    created = 0
    for c in default_categories:
        existing = await db.execute(select(AccountCategory).where(AccountCategory.code == c["code"]))
        if not existing.scalar_one_or_none():
            db.add(AccountCategory(**c))
            created += 1
    await db.commit()

    for item_data in default_items:
        existing = await db.execute(select(AccountItem).where(AccountItem.code == item_data["code"]))
        if not existing.scalar_one_or_none():
            db.add(AccountItem(**item_data))
            created += 1
    await db.commit()

    return {"ok": True, "created": created}


# ── Inventory ─────────────────────────────────────────────────────────────────

@router.get("/inventory")
async def list_inventory(
    item_id: Optional[int] = None,
    only_available: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_catalog_read_access("accounts"))
):
    stmt = select(AccountInventory).order_by(AccountInventory.created_at.desc())
    if item_id:
        stmt = stmt.where(AccountInventory.item_id == item_id)
    if only_available:
        stmt = stmt.where(AccountInventory.is_sold == False)
    result = await db.execute(stmt.limit(500))
    rows = result.scalars().all()
    return [
        {
            "id": r.id, "item_id": r.item_id,
            "credentials": r.credentials,
            "is_sold": r.is_sold,
            "sold_to_user_id": r.sold_to_user_id,
            "sold_at": r.sold_at.isoformat() if r.sold_at else None,
            "order_id": r.order_id,
            "uploaded_by": r.uploaded_by,
            "notes": r.notes,
            "created_at": r.created_at.isoformat()
        }
        for r in rows
    ]


@router.get("/inventory/stats")
async def inventory_stats(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_catalog_read_access("accounts"))
):
    stmt = (
        select(
            AccountInventory.item_id,
            AccountItem.name,
            func.count(AccountInventory.id).label("total"),
            func.count(AccountInventory.id).filter(AccountInventory.is_sold == False).label("available"),
            func.count(AccountInventory.id).filter(AccountInventory.is_sold == True).label("sold"),
        )
        .join(AccountItem, AccountItem.id == AccountInventory.item_id)
        .group_by(AccountInventory.item_id, AccountItem.name)
    )
    result = await db.execute(stmt)
    return [
        {"item_id": r.item_id, "name": r.name, "total": r.total, "available": r.available, "sold": r.sold}
        for r in result.all()
    ]


@router.post("/inventory/upload")
async def upload_inventory(
    data: InventoryUpload,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_catalog_write_access("accounts"))
):
    item = await db.execute(select(AccountItem).where(AccountItem.id == data.item_id))
    if not item.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Item not found")

    added = 0
    for entry in data.entries:
        inv = AccountInventory(
            item_id=data.item_id,
            credentials=entry,
            uploaded_by=current_user.get("username", "admin"),
            notes=data.notes,
        )
        db.add(inv)
        added += 1
    await db.commit()
    return {"ok": True, "added": added}


@router.post("/inventory/upload-text")
async def upload_inventory_text(
    item_id: int,
    text_data: str,
    separator: str = ":",
    notes: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_catalog_write_access("accounts"))
):
    """Upload inventory from plain text — one entry per line, fields separated by separator."""
    item = await db.execute(select(AccountItem).where(AccountItem.id == item_id))
    if not item.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Item not found")

    added = 0
    for line in text_data.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(separator)
        creds = {"login": parts[0].strip()}
        if len(parts) > 1:
            creds["password"] = parts[1].strip()
        if len(parts) > 2:
            creds["extra"] = separator.join(parts[2:]).strip()
        inv = AccountInventory(
            item_id=item_id,
            credentials=creds,
            uploaded_by=current_user.get("username", "admin"),
            notes=notes,
        )
        db.add(inv)
        added += 1
    await db.commit()
    return {"ok": True, "added": added}


@router.post("/inventory/issue")
async def manual_issue(
    data: ManualIssue,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_catalog_write_access("accounts"))
):
    """Manually issue an inventory item to a user."""
    result = await db.execute(
        select(AccountInventory).where(
            AccountInventory.id == data.inventory_id,
            AccountInventory.is_sold == False,
        )
    )
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Inventory item not found or already sold")

    inv.is_sold = True
    inv.sold_to_user_id = data.user_id
    inv.sold_at = datetime.now(timezone.utc)
    await db.commit()
    return {"ok": True, "inventory_id": inv.id, "user_id": data.user_id}


@router.delete("/inventory/{inv_id}")
async def delete_inventory(
    inv_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_catalog_write_access("accounts"))
):
    result = await db.execute(select(AccountInventory).where(AccountInventory.id == inv_id))
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Not found")
    await db.delete(inv)
    await db.commit()
    return {"ok": True}
