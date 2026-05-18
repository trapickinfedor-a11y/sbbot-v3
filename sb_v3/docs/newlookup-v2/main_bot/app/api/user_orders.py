from __future__ import annotations

import os
import secrets
from datetime import datetime
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mirror_bot.services.product_service import ProductService
from shared.database.models import MirrorBot, User
from shared.database.session import get_session
from shared.security.internal_api import get_internal_api_token
from shared.services.coupon_service import CouponService
from shared.utils.telegram_auth import validate_telegram_init_data

app = FastAPI()


class SellerInfo(BaseModel):
    id: int
    username: str


class ProductInfo(BaseModel):
    id: int
    name: str
    category_name: str


class OrderHistoryItem(BaseModel):
    id: int
    amount: float
    status: str
    created_at: datetime
    seller: SellerInfo
    product: ProductInfo


class PaginatedOrderHistory(BaseModel):
    items: list[OrderHistoryItem]
    total: int
    page: int
    limit: int


class SetArchiveChannelRequest(BaseModel):
    channel_id: int


class CouponActivateRequest(BaseModel):
    code: str


async def get_db():
    session_gen = get_session()
    session = await session_gen.__anext__()
    try:
        yield session
    finally:
        await session.close()


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    telegram_init_data: Optional[str] = Header(default=None, alias="X-Telegram-Init-Data"),
    mirror_bot_id: Optional[int] = Header(default=None, alias="X-Mirror-Bot-Id"),
    dev_user_id: Optional[int] = Header(default=None, alias="X-Dev-User-Id"),
    internal_token: Optional[str] = Header(default=None, alias="X-Internal-Token"),
    internal_user_id: Optional[int] = Header(default=None, alias="X-User-Id"),
) -> User:
    if mirror_bot_id is None:
        raise HTTPException(status_code=401, detail="X-Mirror-Bot-Id header is required")

    user_telegram_id: Optional[int] = None
    expected_internal_token = get_internal_api_token()
    if (
        internal_token
        and internal_user_id is not None
        and expected_internal_token
        and secrets.compare_digest(internal_token, expected_internal_token)
    ):
        user_telegram_id = int(internal_user_id)
    elif telegram_init_data:
        mirror_bot = await db.scalar(select(MirrorBot).where(MirrorBot.id == mirror_bot_id))
        if not mirror_bot or not mirror_bot.bot_token:
            raise HTTPException(status_code=401, detail="Mirror bot auth is not configured")
        try:
            telegram_user = validate_telegram_init_data(
                telegram_init_data,
                mirror_bot.bot_token,
                max_age_seconds=3600,
            )
        except ValueError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
        user_telegram_id = int(telegram_user["id"])
    elif os.getenv("ENVIRONMENT") != "production" and dev_user_id is not None:
        user_telegram_id = int(dev_user_id)

    if user_telegram_id is None:
        raise HTTPException(status_code=401, detail="Telegram user auth required")

    user = await db.scalar(
        select(User).where(
            User.user_id == user_telegram_id,
            User.mirror_bot_id == mirror_bot_id,
        )
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.get("/orders/my", response_model=PaginatedOrderHistory)
async def get_my_orders(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=50),
    category_id: Optional[str] = Query(default=None),
    seller_id: Optional[int] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await ProductService.get_user_purchase_history(
        db,
        user_id=current_user.user_id,
        mirror_bot_id=current_user.mirror_bot_id,
        page=page,
        limit=limit,
        category_id=category_id,
        seller_id=seller_id,
    )
    return {
        "items": [
            {
                "id": item["id"],
                "amount": item["amount"],
                "status": item["status"],
                "created_at": item["created_at"],
                "seller": {
                    "id": item["seller"]["id"] or 0,
                    "username": item["seller"]["name"],
                },
                "product": {
                    "id": item["product"]["id"],
                    "name": item["product"]["name"],
                    "category_name": item["product"]["category_id"],
                },
            }
            for item in result["items"]
        ],
        "total": result["total"],
        "page": result["page"],
        "limit": result["limit"],
    }


@app.post("/users/me/set-archive-channel")
async def set_archive_channel(
    payload: SetArchiveChannelRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    updated = await ProductService.set_archive_channel(
        db,
        user_id=current_user.user_id,
        mirror_bot_id=current_user.mirror_bot_id,
        channel_id=payload.channel_id,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="User not found")
    return {"status": "ok"}


@app.post("/coupons/activate")
async def activate_coupon(
    payload: CouponActivateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    application = await CouponService.activate_coupon(db, user=current_user, code=payload.code)
    if not application.coupon:
        raise HTTPException(status_code=404, detail=application.message or "Coupon not found")
    if application.message == "Coupon already activated by this user":
        raise HTTPException(status_code=409, detail=application.message)
    if application.message != "Coupon applied":
        raise HTTPException(status_code=400, detail=application.message or "Coupon cannot be activated")
    return {
        "status": "ok",
        "code": application.code,
        "message": application.message,
        "discount_type": application.coupon.discount_type,
        "discount_value": float(application.coupon.discount_value),
    }
