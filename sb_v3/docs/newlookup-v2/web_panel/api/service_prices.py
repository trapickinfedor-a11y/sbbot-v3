"""
API для динамического управления ценами всех сервисов
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from web_panel.database import get_db
from web_panel.auth import get_current_user, has_any_role
from shared.database.models import ServicePrice
from web_panel.services.audit_service import log_action

router = APIRouter()


class PriceUpdate(BaseModel):
    reason: str
    display_name: Optional[str] = None
    price: Optional[float] = Field(default=None, ge=0, le=1_000_000)
    bulk_price: Optional[float] = Field(default=None, ge=0, le=1_000_000)
    description: Optional[str] = None
    is_active: Optional[bool] = None
    position: Optional[int] = Field(default=None, ge=0, le=100_000)


class PriceCreate(BaseModel):
    key: str
    category: str
    display_name: str
    price: float = Field(ge=0, le=1_000_000)
    bulk_price: Optional[float] = Field(default=None, ge=0, le=1_000_000)
    description: Optional[str] = None
    is_active: bool = True
    position: int = Field(default=0, ge=0, le=100_000)


def _ensure_price_read(current_user: dict) -> None:
    if not has_any_role(current_user, "support", "moderator", "admin", "owner", "super_admin"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")


def _ensure_price_update(current_user: dict) -> None:
    if not has_any_role(current_user, "support", "moderator", "admin", "owner", "super_admin"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")


def _ensure_price_admin(current_user: dict) -> None:
    if not has_any_role(current_user, "admin", "owner", "super_admin"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")


@router.get("/")
async def get_all_prices(
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    _ensure_price_read(current_user)
    stmt = select(ServicePrice)
    if category:
        stmt = stmt.where(ServicePrice.category == category)
    stmt = stmt.order_by(ServicePrice.category, ServicePrice.position, ServicePrice.id)

    result = await db.execute(stmt)
    items = result.scalars().all()

    return [
        {
            "id": s.id, "key": s.key, "category": s.category,
            "display_name": s.display_name, "price": float(s.price),
            "bulk_price": float(s.bulk_price) if s.bulk_price else None,
            "description": s.description, "is_active": s.is_active,
            "position": s.position,
            "updated_at": s.updated_at.isoformat() if s.updated_at else None,
        }
        for s in items
    ]


@router.put("/{item_id}")
async def update_price(
    item_id: int,
    data: PriceUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    _ensure_price_update(current_user)
    reason = (data.reason or "").strip()
    if not reason:
        raise HTTPException(status_code=400, detail="Reason is required")
    result = await db.execute(select(ServicePrice).where(ServicePrice.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Service price not found")

    old_values = {
        "display_name": item.display_name,
        "price": float(item.price),
        "bulk_price": float(item.bulk_price) if item.bulk_price is not None else None,
        "description": item.description,
        "is_active": item.is_active,
        "position": item.position,
    }

    if data.display_name is not None:
        item.display_name = data.display_name
    if data.price is not None:
        item.price = Decimal(str(data.price))
    if data.bulk_price is not None:
        item.bulk_price = Decimal(str(data.bulk_price))
    if data.description is not None:
        item.description = data.description
    if data.is_active is not None:
        item.is_active = data.is_active
    if data.position is not None:
        item.position = data.position

    await log_action(
        db,
        current_user.get("admin_id"),
        "service_price_update",
        "service_price",
        item.id,
        {
            "key": item.key,
            "reason": reason,
            "old": old_values,
            "new": {
                "display_name": item.display_name,
                "price": float(item.price),
                "bulk_price": float(item.bulk_price) if item.bulk_price is not None else None,
                "description": item.description,
                "is_active": item.is_active,
                "position": item.position,
            },
            "actor_role": current_user.get("role"),
        },
        request.client.host if request.client else None,
    )
    await db.commit()
    return {"message": "Price updated", "id": item.id}


@router.post("/")
async def create_price(
    data: PriceCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    _ensure_price_admin(current_user)
    existing = await db.execute(select(ServicePrice).where(ServicePrice.key == data.key))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Key already exists")

    item = ServicePrice(
        key=data.key, category=data.category, display_name=data.display_name,
        price=Decimal(str(data.price)),
        bulk_price=Decimal(str(data.bulk_price)) if data.bulk_price is not None else None,
        description=data.description, is_active=data.is_active, position=data.position,
    )
    db.add(item)
    await log_action(
        db,
        current_user.get("admin_id"),
        "service_price_create",
        "service_price",
        None,
        {
            "key": data.key,
            "category": data.category,
            "price": data.price,
            "bulk_price": data.bulk_price,
            "actor_role": current_user.get("role"),
        },
        request.client.host if request.client else None,
    )
    await db.commit()
    await db.refresh(item)
    return {"message": "Price created", "id": item.id}


@router.delete("/{item_id}")
async def delete_price(
    item_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    _ensure_price_admin(current_user)
    result = await db.execute(select(ServicePrice).where(ServicePrice.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    await log_action(
        db,
        current_user.get("admin_id"),
        "service_price_delete",
        "service_price",
        item.id,
        {
            "key": item.key,
            "category": item.category,
            "price": float(item.price),
            "actor_role": current_user.get("role"),
        },
        request.client.host if request.client else None,
    )
    await db.delete(item)
    await db.commit()
    return {"message": "Deleted"}


@router.post("/seed")
async def seed_prices(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Import all hardcoded prices from ServicePrices into DB"""
    _ensure_price_admin(current_user)
    from mirror_bot.constants.prices import ServicePrices

    ALL_SERVICES = [
        # Lookup
        ("lookup_ssn", "lookup", "SSN + DOB Lookup", ServicePrices.LOOKUP_SSN_DOB, ServicePrices.LOOKUP_SSN_DOB_BULK),
        ("lookup_credit", "lookup", "Credit Score Lookup", ServicePrices.LOOKUP_CREDIT_SCORE, ServicePrices.LOOKUP_CREDIT_SCORE_BULK),
        ("lookup_dl", "lookup", "DL Lookup", ServicePrices.LOOKUP_DL, ServicePrices.LOOKUP_DL_BULK),
        ("lookup_mvr", "lookup", "MVR Lookup", ServicePrices.LOOKUP_MVR, ServicePrices.LOOKUP_MVR_BULK),
        ("lookup_fullmvr", "lookup", "Full MVR Lookup", ServicePrices.LOOKUP_FULL_MVR, ServicePrices.LOOKUP_FULL_MVR_BULK),
        ("lookup_bg", "lookup", "Background Check", ServicePrices.LOOKUP_BG, ServicePrices.LOOKUP_BG_BULK),
        ("lookup_mmn", "lookup", "MMN Lookup", ServicePrices.LOOKUP_MMN, None),
        ("lookup_ein", "lookup", "EIN Lookup", ServicePrices.LOOKUP_EIN, None),
        ("phone_name", "lookup", "Phone -> Name", ServicePrices.LOOKUP_PHONE_NAME, None),
        ("phone_ssn", "lookup", "Phone -> SSN", ServicePrices.LOOKUP_PHONE_SSN, None),
        ("phone_full", "lookup", "Phone -> Full Info", ServicePrices.LOOKUP_PHONE_FULL, None),
        # Credit Reports
        ("cr_transunion", "credit_reports", "TransUnion CR", ServicePrices.CR_TRANSUNION, ServicePrices.CR_TRANSUNION_BULK),
        ("cr_experian", "credit_reports", "Experian CR", ServicePrices.CR_EXPERIAN, ServicePrices.CR_EXPERIAN_BULK),
        ("cr_equifax", "credit_reports", "Equifax CR", ServicePrices.CR_EQUIFAX, None),
        ("cr_lexisnexis", "credit_reports", "LexisNexis CR", ServicePrices.CR_LEXISNEXIS, ServicePrices.CR_LEXISNEXIS_BULK),
        ("cr_wallethub", "credit_reports", "WalletHub CR", ServicePrices.CR_WALLETHUB, ServicePrices.CR_WALLETHUB_BULK),
        # Fullz
        ("fullz_base", "fullz", "FULLZ Base Price", ServicePrices.FULLZ_BASE, None),
        ("fullz_biz_base", "fullz", "Business FULLZ Base", ServicePrices.FULLZ_BIZ_BASE, None),
        # Add Info
        ("addinfo_phone_address_employer", "addinfo", "Phone+Address+Employer (All CRs)", ServicePrices.ADD_INFO_PHONE_ADDRESS_EMPLOYER_ALL, None),
        ("addinfo_phone_address", "addinfo", "Phone+Address (All CRs)", ServicePrices.ADD_INFO_PHONE_ADDRESS_ALL, None),
        ("addinfo_phone_all", "addinfo", "Phone (All CRs)", ServicePrices.ADD_INFO_PHONE_ALL, None),
        ("addinfo_address_all", "addinfo", "Address (All CRs)", ServicePrices.ADD_INFO_ADDRESS_ALL, None),
        ("addinfo_phone_ex", "addinfo", "Phone (Experian)", ServicePrices.ADD_INFO_PHONE_EX, None),
        ("addinfo_address_ex", "addinfo", "Address (Experian)", ServicePrices.ADD_INFO_ADDRESS_EX, None),
        ("addinfo_phone_tu", "addinfo", "Phone (TransUnion)", ServicePrices.ADD_INFO_PHONE_TU, None),
        ("addinfo_address_tu", "addinfo", "Address (TransUnion)", ServicePrices.ADD_INFO_ADDRESS_TU, None),
        ("addinfo_bg_phone_address", "addinfo", "BG Phone+Address", ServicePrices.ADD_INFO_BG_PHONE_ADDRESS, None),
        ("addinfo_bg_phone", "addinfo", "BG Phone", ServicePrices.ADD_INFO_BG_PHONE, None),
        ("addinfo_bg_address", "addinfo", "BG Address", ServicePrices.ADD_INFO_BG_ADDRESS, None),
        ("add_employer_tu", "addinfo", "Add Employer (TU)", ServicePrices.ADD_EMPLOYER_TU, None),
        ("update_employer", "addinfo", "Update Employer", ServicePrices.UPDATE_EMPLOYER, None),
        ("remove_employer", "addinfo", "Remove Employer", ServicePrices.REMOVE_EMPLOYER, None),
        ("unfreeze_tu", "addinfo", "Unfreeze TU", ServicePrices.UNFREEZE_TU, None),
        ("unfreeze_ex", "addinfo", "Unfreeze EX", ServicePrices.UNFREEZE_EX, None),
        # eSIM SMS
        ("esim_verizon_1", "esim", "Verizon SMS 1mo", ServicePrices.ESIM_VERIZON, None),
        ("esim_verizon_3", "esim", "Verizon SMS 3mo", ServicePrices.ESIM_VERIZON_3, None),
        ("esim_verizon_6", "esim", "Verizon SMS 6mo", ServicePrices.ESIM_VERIZON_6, None),
        ("esim_att_1", "esim", "AT&T SMS 1mo", ServicePrices.ESIM_ATT, None),
        ("esim_att_3", "esim", "AT&T SMS 3mo", ServicePrices.ESIM_ATT_3, None),
        ("esim_att_6", "esim", "AT&T SMS 6mo", ServicePrices.ESIM_ATT_6, None),
        ("esim_tmobile_1", "esim", "T-Mobile SMS 1mo", ServicePrices.ESIM_TMOBILE, None),
        ("esim_tmobile_3", "esim", "T-Mobile SMS 3mo", ServicePrices.ESIM_TMOBILE_3, None),
        ("esim_tmobile_6", "esim", "T-Mobile SMS 6mo", ServicePrices.ESIM_TMOBILE_6, None),
        # eSIM Data
        ("esim_data_verizon_5", "esim", "Verizon Data 5GB", ServicePrices.ESIM_DATA_VERIZON_5GB, None),
        ("esim_data_verizon_10", "esim", "Verizon Data 10GB", ServicePrices.ESIM_DATA_VERIZON_10GB, None),
        ("esim_data_verizon_15", "esim", "Verizon Data 15GB", ServicePrices.ESIM_DATA_VERIZON_15GB, None),
        ("esim_data_att_5", "esim", "AT&T Data 5GB", ServicePrices.ESIM_DATA_ATT_5GB, None),
        ("esim_data_att_10", "esim", "AT&T Data 10GB", ServicePrices.ESIM_DATA_ATT_10GB, None),
        ("esim_data_att_15", "esim", "AT&T Data 15GB", ServicePrices.ESIM_DATA_ATT_15GB, None),
        ("esim_data_tmobile_5", "esim", "T-Mobile Data 5GB", ServicePrices.ESIM_DATA_TMOBILE_5GB, None),
        ("esim_data_tmobile_10", "esim", "T-Mobile Data 10GB", ServicePrices.ESIM_DATA_TMOBILE_10GB, None),
        ("esim_data_tmobile_15", "esim", "T-Mobile Data 15GB", ServicePrices.ESIM_DATA_TMOBILE_15GB, None),
        # Accounts
        ("acc_bg_beenverified", "accounts", "BeenVerified", ServicePrices.ACC_BG_BEENVERIFIED, None),
        ("acc_bg_truthfinder", "accounts", "TruthFinder", ServicePrices.ACC_BG_TRUTHFINDER, None),
        ("acc_bg_instantcheck", "accounts", "InstantCheck", ServicePrices.ACC_BG_INSTANTCHECK, None),
        ("acc_bg_intelius", "accounts", "Intelius", ServicePrices.ACC_BG_INTELIUS, None),
        ("acc_bg_whitepages", "accounts", "WhitePages", ServicePrices.ACC_BG_WHITEPAGES, None),
        ("acc_bg_mylife", "accounts", "MyLife", ServicePrices.ACC_BG_MYLIFE, None),
        ("acc_lookup_monarch", "accounts", "Monarch", ServicePrices.ACC_LOOKUP_MONARCH, None),
        ("acc_lookup_yodlee", "accounts", "Yodlee", ServicePrices.ACC_LOOKUP_YODLEE, None),
        ("acc_lookup_empower", "accounts", "Empower", ServicePrices.ACC_LOOKUP_EMPOWER, None),
        ("acc_lookup_pocketguard", "accounts", "PocketGuard", ServicePrices.ACC_LOOKUP_POCKETGUARD, None),
        ("acc_lookup_everydollar", "accounts", "EveryDollar", ServicePrices.ACC_LOOKUP_EVERYDOLLAR, None),
        ("acc_bg_intelius_30", "accounts", "Intelius 30 days", ServicePrices.ACC_BG_INTELIUS_30, None),
        ("acc_bg_truthfinder_30", "accounts", "TruthFinder 30 days", ServicePrices.ACC_BG_TRUTHFINDER_30, None),
        ("acc_bg_instantcheck_30", "accounts", "InstantCheck 30 days", ServicePrices.ACC_BG_INSTANTCHECK_30, None),
        ("acc_bg_whitepages_30", "accounts", "WhitePages 30 days", ServicePrices.ACC_BG_WHITEPAGES_30, None),
    ]

    count = 0
    for idx, (key, cat, name, price, bulk) in enumerate(ALL_SERVICES):
        existing = await db.execute(select(ServicePrice).where(ServicePrice.key == key))
        if existing.scalar_one_or_none():
            continue
        item = ServicePrice(
            key=key, category=cat, display_name=name,
            price=price, bulk_price=bulk,
            is_active=True, position=idx,
        )
        db.add(item)
        count += 1

    await db.commit()
    return {"message": f"Seeded {count} service prices"}
