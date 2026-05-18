# FastAPI Routes — Full Specification (v24)

This document provides the complete, copy-ready FastAPI route definitions with Pydantic schemas for all modules of the Newlookup platform. This is the authoritative reference for the backend API layer.

---

## Project Structure (API Layer)

```
app/
├── api/
│   ├── v1/
│   │   ├── auth.py
│   │   ├── users.py
│   │   ├── products.py
│   │   ├── orders.py
│   │   ├── disputes.py
│   │   ├── coupons.py
│   │   ├── finance.py
│   │   ├── admin/
│   │   │   ├── users.py
│   │   │   ├── products.py
│   │   │   ├── orders.py
│   │   │   ├── finance.py
│   │   │   └── settings.py
│   │   └── bots/
│   │       ├── mirror.py
│   │       └── seller.py
├── schemas/
│   ├── user.py
│   ├── product.py
│   ├── order.py
│   ├── dispute.py
│   ├── coupon.py
│   └── finance.py
└── main.py
```

---

## 1. Pydantic Schemas

### `app/schemas/user.py`

```python
from pydantic import BaseModel
from typing import Optional
import datetime

class UserBase(BaseModel):
    telegram_id: int
    username: Optional[str] = None

class UserCreate(UserBase):
    pass

class UserOut(UserBase):
    id: int
    balance: float
    roles: str
    created_at: datetime.datetime
    is_banned: bool

    class Config:
        orm_mode = True

class UserBalanceUpdate(BaseModel):
    amount: float
    reason: str

class UserBan(BaseModel):
    reason: str
```

### `app/schemas/product.py`

```python
from pydantic import BaseModel, validator
from typing import Optional
import datetime

class ProductBase(BaseModel):
    title: str
    description: Optional[str] = None
    category: str
    price: float
    stock: int

    @validator('price')
    def price_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Price must be positive')
        return v

    @validator('stock')
    def stock_must_be_non_negative(cls, v):
        if v < 0:
            raise ValueError('Stock cannot be negative')
        return v

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    stock: Optional[int] = None
    is_active: Optional[bool] = None

class ProductOut(ProductBase):
    id: int
    seller_id: int
    is_active: bool
    created_at: datetime.datetime

    class Config:
        orm_mode = True
```

### `app/schemas/order.py`

```python
from pydantic import BaseModel
from typing import Optional
import datetime

class OrderCreate(BaseModel):
    product_id: int
    quantity: int = 1
    coupon_code: Optional[str] = None

class OrderOut(BaseModel):
    id: int
    buyer_id: int
    product_id: int
    quantity: int
    total_price: float
    status: str
    created_at: datetime.datetime

    class Config:
        orm_mode = True

class PurchaseHistoryFilter(BaseModel):
    category: Optional[str] = None
    seller_id: Optional[int] = None
    status: Optional[str] = None
    date_from: Optional[datetime.date] = None
    date_to: Optional[datetime.date] = None
```

### `app/schemas/dispute.py`

```python
from pydantic import BaseModel
from typing import Optional
import datetime

class DisputeCreate(BaseModel):
    order_id: int
    reason: str

class DisputeUpdate(BaseModel):
    status: str
    resolution_note: Optional[str] = None

class DisputeOut(BaseModel):
    id: int
    order_id: int
    buyer_id: int
    seller_id: int
    status: str
    reason: str
    created_at: datetime.datetime

    class Config:
        orm_mode = True
```

### `app/schemas/coupon.py`

```python
from pydantic import BaseModel
from typing import Optional

class CouponCreate(BaseModel):
    code: str
    discount_percent: float
    max_uses: int = 1

class CouponActivate(BaseModel):
    code: str

class CouponOut(BaseModel):
    id: int
    code: str
    discount_percent: float
    max_uses: int
    use_count: int
    is_active: bool

    class Config:
        orm_mode = True
```

### `app/schemas/finance.py`

```python
from pydantic import BaseModel
import datetime

class TransactionOut(BaseModel):
    id: int
    user_id: int
    amount: float
    type: str
    created_at: datetime.datetime

    class Config:
        orm_mode = True

class DepositRequest(BaseModel):
    amount: float
    payment_method: str  # e.g., "crypto_btc", "crypto_usdt"

class WithdrawalRequest(BaseModel):
    amount: float
    wallet_address: str
    currency: str
```

---

## 2. API Route Definitions

### `app/api/v1/auth.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.user import UserOut
from app.services.user_service import UserService
from app.db import get_db

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/telegram", response_model=UserOut)
async def telegram_auth(
    telegram_id: int,
    username: str = None,
    db: Session = Depends(get_db)
):
    """
    Authenticate or register a user via Telegram.
    Called by bots when a user starts a conversation.
    Returns the user object (existing or newly created).
    """
    service = UserService(db)
    user = service.get_or_create_user(telegram_id=telegram_id, username=username)
    return user
```

### `app/api/v1/users.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.schemas.user import UserOut
from app.schemas.coupon import CouponActivate, CouponOut
from app.schemas.finance import TransactionOut
from app.services.user_service import UserService
from app.services.coupon_service import CouponService
from app.db import get_db
from app.dependencies import get_current_user

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me", response_model=UserOut)
async def get_my_profile(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the current user's profile."""
    return current_user

@router.post("/me/coupons/activate", response_model=CouponOut)
async def activate_coupon(
    payload: CouponActivate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Activate a coupon code for the current user.
    Only available in the Profile section.
    Coupons are created exclusively by the owner via Admin Panel.
    """
    service = CouponService(db)
    activated = service.activate_coupon(user_id=current_user.id, code=payload.code)
    if not activated:
        raise HTTPException(status_code=400, detail="Invalid or already used coupon code.")
    return activated

@router.get("/me/transactions", response_model=List[TransactionOut])
async def get_my_transactions(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the current user's transaction history."""
    service = UserService(db)
    return service.get_transactions(user_id=current_user.id)

@router.post("/me/archive-channel")
async def set_archive_channel(
    channel_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Set the user's personal Telegram archive channel.
    The user must have added the bot as an admin to the channel first.
    After setting, all future purchases will be forwarded to this channel.
    """
    service = UserService(db)
    service.set_archive_channel(user_id=current_user.id, channel_id=channel_id)
    return {"status": "ok", "message": "Archive channel set successfully."}
```

### `app/api/v1/products.py`

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.schemas.product import ProductCreate, ProductUpdate, ProductOut
from app.services.product_service import ProductService
from app.db import get_db
from app.dependencies import get_current_user, require_role

router = APIRouter(prefix="/products", tags=["products"])

@router.get("/", response_model=List[ProductOut])
async def list_products(
    category: Optional[str] = Query(None),
    seller_id: Optional[int] = Query(None),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    List all active products with optional filters.
    Used by Mirror Bot to display the product catalog.
    """
    service = ProductService(db)
    return service.list_products(
        category=category, seller_id=seller_id,
        min_price=min_price, max_price=max_price,
        skip=skip, limit=limit
    )

@router.get("/{product_id}", response_model=ProductOut)
async def get_product(product_id: int, db: Session = Depends(get_db)):
    """Get a single product by ID."""
    service = ProductService(db)
    product = service.get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")
    return product

@router.post("/", response_model=ProductOut)
async def create_product(
    payload: ProductCreate,
    current_user = Depends(require_role("seller")),
    db: Session = Depends(get_db)
):
    """Create a new product. Requires seller role."""
    service = ProductService(db)
    return service.create_product(seller_id=current_user.id, **payload.dict())

@router.put("/{product_id}", response_model=ProductOut)
async def update_product(
    product_id: int,
    payload: ProductUpdate,
    current_user = Depends(require_role("seller")),
    db: Session = Depends(get_db)
):
    """Update a product. Only the owning seller can update."""
    service = ProductService(db)
    product = service.get_product(product_id)
    if not product or product.seller_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this product.")
    return service.update_product(product_id, payload.dict(exclude_unset=True))
```

### `app/api/v1/orders.py`

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import datetime
from app.schemas.order import OrderCreate, OrderOut
from app.services.order_service import OrderService
from app.db import get_db
from app.dependencies import get_current_user

router = APIRouter(prefix="/orders", tags=["orders"])

@router.post("/", response_model=OrderOut)
async def create_order(
    payload: OrderCreate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new order (purchase a product).
    Handles: stock check, balance deduction, coupon application,
    seller payout, message pinning trigger, archive channel forwarding.
    """
    service = OrderService(db)
    try:
        order = service.create_order(
            buyer_id=current_user.id,
            product_id=payload.product_id,
            quantity=payload.quantity,
            coupon_code=payload.coupon_code
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return order

@router.get("/me", response_model=List[OrderOut])
async def get_my_orders(
    category: Optional[str] = Query(None),
    seller_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    date_from: Optional[datetime.date] = Query(None),
    date_to: Optional[datetime.date] = Query(None),
    skip: int = 0,
    limit: int = 50,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the current user's purchase history.
    Supports filters: by category (Selfreg BA/CC, Logs, Brute, Dumps),
    by seller, by status, and by date range.
    """
    service = OrderService(db)
    return service.get_user_orders(
        buyer_id=current_user.id,
        category=category, seller_id=seller_id,
        status=status, date_from=date_from, date_to=date_to,
        skip=skip, limit=limit
    )
```

### `app/api/v1/disputes.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.schemas.dispute import DisputeCreate, DisputeUpdate, DisputeOut
from app.services.dispute_service import DisputeService
from app.db import get_db
from app.dependencies import get_current_user, require_role

router = APIRouter(prefix="/disputes", tags=["disputes"])

@router.post("/", response_model=DisputeOut)
async def open_dispute(
    payload: DisputeCreate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Open a dispute for an order. Only the buyer can open a dispute."""
    service = DisputeService(db)
    try:
        dispute = service.open_dispute(
            buyer_id=current_user.id,
            order_id=payload.order_id,
            reason=payload.reason
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return dispute

@router.get("/me", response_model=List[DisputeOut])
async def get_my_disputes(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all disputes for the current user (as buyer or seller)."""
    service = DisputeService(db)
    return service.get_user_disputes(user_id=current_user.id)

@router.put("/{dispute_id}", response_model=DisputeOut)
async def update_dispute(
    dispute_id: int,
    payload: DisputeUpdate,
    current_user = Depends(require_role("support")),
    db: Session = Depends(get_db)
):
    """
    Update dispute status. Requires support role.
    Support can: close with refund, close without refund, escalate.
    """
    service = DisputeService(db)
    return service.update_dispute(dispute_id=dispute_id, **payload.dict())
```

### `app/api/v1/coupons.py` (Admin/Owner only)

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.schemas.coupon import CouponCreate, CouponOut
from app.services.coupon_service import CouponService
from app.db import get_db
from app.dependencies import require_role

router = APIRouter(prefix="/coupons", tags=["coupons"])

@router.post("/", response_model=CouponOut)
async def create_coupon(
    payload: CouponCreate,
    current_user = Depends(require_role("owner")),
    db: Session = Depends(get_db)
):
    """
    Create a new coupon. ONLY the owner can create coupons.
    This is accessible via the Admin Panel only.
    """
    service = CouponService(db)
    return service.create_coupon(
        created_by=current_user.id,
        code=payload.code,
        discount_percent=payload.discount_percent,
        max_uses=payload.max_uses
    )

@router.get("/", response_model=List[CouponOut])
async def list_coupons(
    current_user = Depends(require_role("owner")),
    db: Session = Depends(get_db)
):
    """List all coupons. Owner only."""
    service = CouponService(db)
    return service.list_coupons()

@router.delete("/{coupon_id}")
async def delete_coupon(
    coupon_id: int,
    current_user = Depends(require_role("owner")),
    db: Session = Depends(get_db)
):
    """Delete/deactivate a coupon. Owner only."""
    service = CouponService(db)
    service.deactivate_coupon(coupon_id)
    return {"status": "ok"}
```

---

## 3. Admin Panel API Routes

### `app/api/v1/admin/users.py`

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.schemas.user import UserOut, UserBan, UserBalanceUpdate
from app.services.user_service import UserService
from app.db import get_db
from app.dependencies import require_role

router = APIRouter(prefix="/admin/users", tags=["admin-users"])

@router.get("/", response_model=List[UserOut])
async def admin_list_users(
    search: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    is_banned: Optional[bool] = Query(None),
    skip: int = 0,
    limit: int = 100,
    current_user = Depends(require_role("support")),
    db: Session = Depends(get_db)
):
    """List all users with filters. Accessible by support and above."""
    service = UserService(db)
    return service.admin_list_users(
        search=search, role=role, is_banned=is_banned,
        skip=skip, limit=limit
    )

@router.get("/{user_id}", response_model=UserOut)
async def admin_get_user(
    user_id: int,
    current_user = Depends(require_role("support")),
    db: Session = Depends(get_db)
):
    """Get a specific user's details. Accessible by support and above."""
    service = UserService(db)
    user = service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return user

@router.post("/{user_id}/ban")
async def admin_ban_user(
    user_id: int,
    payload: UserBan,
    current_user = Depends(require_role("moderator")),
    db: Session = Depends(get_db)
):
    """Ban a user. Requires moderator role or above."""
    service = UserService(db)
    service.ban_user(user_id=user_id, reason=payload.reason, banned_by=current_user.id)
    return {"status": "ok"}

@router.post("/{user_id}/unban")
async def admin_unban_user(
    user_id: int,
    current_user = Depends(require_role("moderator")),
    db: Session = Depends(get_db)
):
    """Unban a user. Requires moderator role or above."""
    service = UserService(db)
    service.unban_user(user_id=user_id, unbanned_by=current_user.id)
    return {"status": "ok"}

@router.post("/{user_id}/balance")
async def admin_adjust_balance(
    user_id: int,
    payload: UserBalanceUpdate,
    current_user = Depends(require_role("finance")),
    db: Session = Depends(get_db)
):
    """
    Adjust a user's balance (add or subtract).
    Requires finance role or above.
    Creates an audit log entry.
    """
    service = UserService(db)
    service.update_balance(
        user_id=user_id,
        amount=payload.amount,
        reason=payload.reason,
        adjusted_by=current_user.id
    )
    return {"status": "ok"}
```

### `app/api/v1/admin/settings.py`

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import get_db
from app.dependencies import require_role

router = APIRouter(prefix="/admin/settings", tags=["admin-settings"])

@router.get("/")
async def get_settings(
    current_user = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    """Get all platform settings. Admin only."""
    # Returns key-value pairs from the settings table
    pass

@router.put("/")
async def update_settings(
    settings: dict,
    current_user = Depends(require_role("owner")),
    db: Session = Depends(get_db)
):
    """
    Update platform settings. Owner only.
    Settings include: platform fee %, min deposit, max withdrawal, etc.
    """
    pass
```

---

## 4. Bot Webhook Endpoints

### `app/api/v1/bots/mirror.py`

```python
from fastapi import APIRouter, Request
from aiogram import Bot, Dispatcher

router = APIRouter(prefix="/webhooks/mirror", tags=["webhooks"])

@router.post("/")
async def mirror_bot_webhook(request: Request):
    """
    Webhook endpoint for the Mirror Bot.
    Receives Telegram updates and passes them to the aiogram dispatcher.
    """
    update = await request.json()
    # await dp.process_update(update)
    return {"ok": True}
```

---

## 5. Dependencies

### `app/dependencies.py`

```python
from fastapi import Depends, HTTPException, Header
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import User

async def get_current_user(
    x_telegram_id: int = Header(...),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get the current authenticated user.
    Reads Telegram ID from the X-Telegram-Id header (set by bots).
    """
    user = db.query(User).filter(User.telegram_id == x_telegram_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found.")
    if user.is_banned:
        raise HTTPException(status_code=403, detail="User is banned.")
    return user

def require_role(required_role: str):
    """
    Dependency factory to require a specific role.
    Role hierarchy: buyer < seller < marketer < worker < support < moderator < finance < admin < owner
    """
    ROLE_HIERARCHY = [
        "buyer", "seller", "marketer", "worker",
        "support", "moderator", "finance", "admin", "owner"
    ]

    async def check_role(current_user: User = Depends(get_current_user)) -> User:
        user_roles = current_user.roles.split(",")
        required_level = ROLE_HIERARCHY.index(required_role)
        user_max_level = max(
            (ROLE_HIERARCHY.index(r) for r in user_roles if r in ROLE_HIERARCHY),
            default=-1
        )
        if user_max_level < required_level:
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions. Required role: {required_role}"
            )
        return current_user

    return check_role
```

---

## 6. Main Application Entry Point

### `app/main.py`

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import auth, users, products, orders, disputes, coupons
from app.api.v1.admin import users as admin_users, settings as admin_settings
from app.api.v1.bots import mirror as mirror_webhook

app = FastAPI(
    title="Newlookup API",
    version="24.0.0",
    description="Backend API for the Newlookup Telegram CRM Marketplace"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(products.router, prefix="/api/v1")
app.include_router(orders.router, prefix="/api/v1")
app.include_router(disputes.router, prefix="/api/v1")
app.include_router(coupons.router, prefix="/api/v1")
app.include_router(admin_users.router, prefix="/api/v1")
app.include_router(admin_settings.router, prefix="/api/v1")
app.include_router(mirror_webhook.router, prefix="/api/v1")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "24.0.0"}
```
