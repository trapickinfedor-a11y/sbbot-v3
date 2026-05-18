"""
API for eSIM price management — wraps service_prices filtered by category 'esim'
and provides eSIM-specific structured view
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from pydantic import BaseModel

from web_panel.database import get_db
from web_panel.auth import require_catalog_read_access, require_catalog_write_access
from shared.database.models import ServicePrice

router = APIRouter(prefix="/api/esim", tags=["esim"])

ESIM_OPERATORS = ["verizon", "att", "tmobile"]
ESIM_SMS_PERIODS = ["1", "3", "6"]
ESIM_DATA_GBS = ["5", "10", "15"]

# Canonical service price keys for eSIM
ESIM_KEY_MAP = {
    # SMS
    "esim_verizon_1m":  ("verizon", "sms", "1"),
    "esim_verizon_3m":  ("verizon", "sms", "3"),
    "esim_verizon_6m":  ("verizon", "sms", "6"),
    "esim_att_1m":      ("att",     "sms", "1"),
    "esim_att_3m":      ("att",     "sms", "3"),
    "esim_att_6m":      ("att",     "sms", "6"),
    "esim_tmobile_1m":  ("tmobile", "sms", "1"),
    "esim_tmobile_3m":  ("tmobile", "sms", "3"),
    "esim_tmobile_6m":  ("tmobile", "sms", "6"),
    # Data
    "esim_data_5gb":    (None, "data", "5"),
    "esim_data_10gb":   (None, "data", "10"),
    "esim_data_15gb":   (None, "data", "15"),
}


class PriceUpdateSingle(BaseModel):
    price: float
    is_active: Optional[bool] = None


@router.get("/prices")
async def get_esim_prices(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_catalog_read_access("esim"))
):
    """Return all eSIM prices structured by type (sms/data) and operator/plan"""
    result = await db.execute(
        select(ServicePrice).where(ServicePrice.category == "esim").order_by(ServicePrice.position, ServicePrice.key)
    )
    prices = {p.key: p for p in result.scalars().all()}

    sms_grid = {}
    data_grid = {}

    for key, (operator, ptype, plan) in ESIM_KEY_MAP.items():
        p = prices.get(key)
        entry = {
            "key": key,
            "price": float(p.price) if p else 0,
            "display_name": p.display_name if p else key,
            "is_active": p.is_active if p else True,
            "id": p.id if p else None,
        }
        if ptype == "sms":
            if operator not in sms_grid:
                sms_grid[operator] = {}
            sms_grid[operator][plan] = entry
        else:
            data_grid[plan] = entry

    return {
        "sms": sms_grid,
        "data": data_grid,
        "operators": ESIM_OPERATORS,
        "sms_periods": ESIM_SMS_PERIODS,
        "data_gbs": ESIM_DATA_GBS,
    }


@router.put("/prices/{price_id}")
async def update_esim_price(
    price_id: int,
    data: PriceUpdateSingle,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_catalog_write_access("esim"))
):
    result = await db.execute(select(ServicePrice).where(ServicePrice.id == price_id))
    price = result.scalar_one_or_none()
    if not price:
        raise HTTPException(status_code=404, detail="Price not found")
    price.price = data.price
    if data.is_active is not None:
        price.is_active = data.is_active
    await db.commit()
    return {"ok": True, "price": float(price.price)}


@router.post("/seed")
async def seed_esim_prices(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_catalog_write_access("esim"))
):
    """Create default eSIM price entries if they don't exist"""
    defaults = {
        "esim_verizon_1m":  ("Verizon SMS 1 Month",  45.0),
        "esim_verizon_3m":  ("Verizon SMS 3 Months", 90.0),
        "esim_verizon_6m":  ("Verizon SMS 6 Months", 160.0),
        "esim_att_1m":      ("AT&T SMS 1 Month",     40.0),
        "esim_att_3m":      ("AT&T SMS 3 Months",    80.0),
        "esim_att_6m":      ("AT&T SMS 6 Months",    145.0),
        "esim_tmobile_1m":  ("T-Mobile SMS 1 Month",  38.0),
        "esim_tmobile_3m":  ("T-Mobile SMS 3 Months", 75.0),
        "esim_tmobile_6m":  ("T-Mobile SMS 6 Months", 135.0),
        "esim_data_5gb":    ("eSIM Data 5 GB",   25.0),
        "esim_data_10gb":   ("eSIM Data 10 GB",  45.0),
        "esim_data_15gb":   ("eSIM Data 15 GB",  60.0),
    }
    created = 0
    for i, (key, (display_name, price)) in enumerate(defaults.items()):
        existing = await db.execute(select(ServicePrice).where(ServicePrice.key == key))
        if not existing.scalar_one_or_none():
            db.add(ServicePrice(key=key, category="esim", display_name=display_name, price=price, position=i))
            created += 1
    await db.commit()
    return {"ok": True, "created": created}
