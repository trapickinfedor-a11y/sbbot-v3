"""
API для управления каталогом банков: per-order каталог и available summary из seller stock.
"""

from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import BankItem, Seller, SellerBank
from web_panel.auth import require_catalog_read_access, require_catalog_write_access
from web_panel.database import get_db
from web_panel.services.audit_service import log_action

router = APIRouter()

VALID_CATEGORIES = ["vcc", "personal", "business", "crypto"]
VALID_SECTIONS = ["order", "stock"]


def _free_stock_expr():
    return SellerBank.stock_count - func.coalesce(SellerBank.reserved_count, 0)


def _available_stock_expr():
    free_stock = _free_stock_expr()
    return case((free_stock > 0, free_stock), else_=0)


class BankItemCreate(BaseModel):
    bank_code: str
    name: str
    category: str
    section: str = "order"
    price: float
    description: Optional[str] = None
    is_active: bool = True
    position: int = 0


class BankItemUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    section: Optional[str] = None
    price: Optional[float] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    position: Optional[int] = None


def _validate_category(category: str) -> None:
    if category not in VALID_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"Category must be one of: {VALID_CATEGORIES}")


def _validate_section(section: str) -> None:
    if section not in VALID_SECTIONS:
        raise HTTPException(status_code=400, detail=f"Section must be one of: {VALID_SECTIONS}")


@router.get("/")
async def get_bank_items(
    category: Optional[str] = None,
    section: Optional[str] = None,
    active_only: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_catalog_read_access("banks")),
):
    stmt = select(BankItem)
    if category:
        stmt = stmt.where(BankItem.category == category)
    if section:
        stmt = stmt.where(BankItem.section == section)
    if active_only:
        stmt = stmt.where(BankItem.is_active == True)
    stmt = stmt.order_by(BankItem.category, BankItem.section, BankItem.position, BankItem.id)

    result = await db.execute(stmt)
    items = result.scalars().all()
    return [
        {
            "id": item.id,
            "bank_code": item.bank_code,
            "name": item.name,
            "category": item.category,
            "section": item.section,
            "price": float(item.price),
            "description": item.description,
            "is_active": item.is_active,
            "position": item.position,
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "updated_at": item.updated_at.isoformat() if item.updated_at else None,
        }
        for item in items
    ]


@router.get('/overview')
async def get_bank_overview(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_catalog_read_access("banks")),
):
    overview = []
    for category in VALID_CATEGORIES:
        per_order_q = await db.execute(
            select(func.count(BankItem.id)).where(
                BankItem.category == category,
                BankItem.section == 'order',
                BankItem.is_active == True,
            )
        )
        available_q = await db.execute(
            select(func.coalesce(func.sum(_available_stock_expr()), 0)).join(Seller).where(
                SellerBank.category == category,
                SellerBank.is_in_stock == True,
                SellerBank.is_active == True,
                SellerBank.moderation_status == 'approved',
                _free_stock_expr() > 0,
                Seller.is_approved == True,
                Seller.is_active == True,
            )
        )
        overview.append({
            'category': category,
            'available_count': int(available_q.scalar() or 0),
            'per_order_count': int(per_order_q.scalar() or 0),
        })
    return overview


@router.get('/available-summary')
async def get_available_summary(
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_catalog_read_access("banks")),
):
    stmt = (
        select(
            SellerBank.bank_code,
            func.max(SellerBank.bank_name).label('bank_name'),
            func.max(SellerBank.category).label('category'),
            func.coalesce(func.sum(_available_stock_expr()), 0).label('available_count'),
            func.coalesce(func.sum(func.coalesce(SellerBank.reserved_count, 0)), 0).label('reserved_count'),
            func.count(SellerBank.id).label('seller_positions'),
            func.max(SellerBank.description).label('description'),
        )
        .join(Seller)
        .where(
            SellerBank.is_in_stock == True,
            SellerBank.is_active == True,
            SellerBank.moderation_status == 'approved',
            _free_stock_expr() > 0,
            Seller.is_approved == True,
            Seller.is_active == True,
        )
        .group_by(SellerBank.bank_code)
        .order_by(func.max(SellerBank.category), func.max(SellerBank.bank_name))
    )
    if category:
        stmt = stmt.where(SellerBank.category == category)

    result = await db.execute(stmt)
    rows = result.all()
    return [
        {
            'bank_code': row.bank_code,
            'bank_name': row.bank_name,
            'category': row.category,
            'available_count': int(row.available_count or 0),
            'reserved_count': int(row.reserved_count or 0),
            'seller_positions': int(row.seller_positions or 0),
            'description': row.description,
        }
        for row in rows
    ]


@router.get('/available-summary/{bank_code}/sellers')
async def get_available_sellers(
    bank_code: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_catalog_write_access("banks")),
):
    stmt = (
        select(SellerBank, Seller)
        .join(Seller)
        .where(
            SellerBank.bank_code == bank_code,
            SellerBank.is_in_stock == True,
            SellerBank.is_active == True,
            SellerBank.moderation_status == 'approved',
            _free_stock_expr() > 0,
            Seller.is_approved == True,
            Seller.is_active == True,
        )
        .order_by(SellerBank.stock_count.desc(), SellerBank.id)
    )
    result = await db.execute(stmt)
    rows = result.all()
    return [
        {
            'seller_bank_id': bank.id,
            'seller_id': seller.id,
            'seller_name': seller.display_name or seller.username or f'Seller #{seller.id}',
            'bank_name': bank.bank_name,
            'category': bank.category,
            'seller_price': float(bank.seller_price),
            'buyer_price': float(bank.buyer_price),
            'stock_count': int(bank.stock_count or 0),
            'reserved_count': int(getattr(bank, 'reserved_count', 0) or 0),
            'free_stock': max(0, int(bank.stock_count or 0) - int(getattr(bank, 'reserved_count', 0) or 0)),
            'description': bank.description,
            'has_chat': bool(getattr(bank, 'has_chat', True)),
        }
        for bank, seller in rows
    ]


@router.post('/')
async def create_bank_item(
    data: BankItemCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_catalog_write_access("banks")),
):
    _validate_category(data.category)
    _validate_section(data.section)

    existing = await db.execute(select(BankItem).where(BankItem.bank_code == data.bank_code))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail='Bank code already exists')

    item = BankItem(
        bank_code=data.bank_code,
        name=data.name,
        category=data.category,
        section=data.section,
        price=Decimal(str(data.price)),
        description=data.description,
        is_active=data.is_active,
        position=data.position,
    )
    db.add(item)
    await log_action(
        db,
        current_user.get("admin_id"),
        "bank_item_create",
        "bank_item",
        None,
        {
            "bank_code": data.bank_code,
            "category": data.category,
            "section": data.section,
            "price": data.price,
            "actor_role": current_user.get("role"),
        },
        request.client.host if request.client else None,
    )
    await db.commit()
    await db.refresh(item)
    return {'message': 'Bank item created', 'id': item.id}


@router.put('/{item_id}')
async def update_bank_item(
    item_id: int,
    data: BankItemUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_catalog_write_access("banks")),
):
    result = await db.execute(select(BankItem).where(BankItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail='Bank item not found')

    old_values = {
        "name": item.name,
        "category": item.category,
        "section": item.section,
        "price": float(item.price),
        "description": item.description,
        "is_active": item.is_active,
        "position": item.position,
    }

    if data.category is not None:
        _validate_category(data.category)
        item.category = data.category
    if data.section is not None:
        _validate_section(data.section)
        item.section = data.section
    if data.name is not None:
        item.name = data.name
    if data.price is not None:
        item.price = Decimal(str(data.price))
    if data.description is not None:
        item.description = data.description
    if data.is_active is not None:
        item.is_active = data.is_active
    if data.position is not None:
        item.position = data.position

    await log_action(
        db,
        current_user.get("admin_id"),
        "bank_item_update",
        "bank_item",
        item.id,
        {
            "bank_code": item.bank_code,
            "old": old_values,
            "new": {
                "name": item.name,
                "category": item.category,
                "section": item.section,
                "price": float(item.price),
                "description": item.description,
                "is_active": item.is_active,
                "position": item.position,
            },
            "actor_role": current_user.get("role"),
        },
        request.client.host if request.client else None,
    )
    await db.commit()
    await db.refresh(item)
    return {'message': 'Bank item updated', 'id': item.id}


@router.delete('/{item_id}')
async def delete_bank_item(
    item_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_catalog_write_access("banks")),
):
    result = await db.execute(select(BankItem).where(BankItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail='Bank item not found')
    await log_action(
        db,
        current_user.get("admin_id"),
        "bank_item_delete",
        "bank_item",
        item.id,
        {
            "bank_code": item.bank_code,
            "category": item.category,
            "section": item.section,
            "actor_role": current_user.get("role"),
        },
        request.client.host if request.client else None,
    )
    await db.delete(item)
    await db.commit()
    return {'message': 'Bank item deleted'}


@router.post('/seed')
async def seed_bank_items(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_catalog_write_access("banks")),
):
    """Импорт захардкоженных банков из bank_data.py в per-order каталог."""
    from mirror_bot.constants.bank_data import BankData

    count = 0
    for cat_key, cat_data in BankData.CATEGORIES.items():
        for idx, bank in enumerate(cat_data['items']):
            existing = await db.execute(select(BankItem).where(BankItem.bank_code == bank['id']))
            if existing.scalar_one_or_none():
                continue
            db.add(BankItem(
                bank_code=bank['id'],
                name=bank['name'],
                category=cat_key,
                section='order',
                price=bank['price'],
                description=bank.get('desc', ''),
                is_active=True,
                position=idx,
            ))
            count += 1

    await db.commit()
    return {'message': f'Seeded {count} bank items'}
