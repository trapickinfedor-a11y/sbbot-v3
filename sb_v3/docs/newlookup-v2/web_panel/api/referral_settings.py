"""Admin API — referral chain rates & VIP Watchlist settings."""
from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from shared.database.models import SystemSetting
from web_panel.auth import require_page_access
from web_panel.database import get_db
from web_panel.services.audit_service import log_action

router = APIRouter()

_REFERRAL_KEY = "referral_rates"
_VIP_DESC_KEY = "vip_watchlist_description"
_VIP_VIDEO_KEY = "vip_watchlist_video_file_id"

_DEFAULT_RATES = {"1": 10.0, "2": 7.0, "3": 5.0, "4": 3.0}


async def _get_setting(session: AsyncSession, key: str, default: str = "") -> str:
    row = await session.scalar(select(SystemSetting).where(SystemSetting.key == key))
    return row.value if row else default


async def _set_setting(session: AsyncSession, key: str, value: str, description: str = "") -> None:
    row = await session.scalar(select(SystemSetting).where(SystemSetting.key == key))
    if row:
        row.value = value
    else:
        session.add(SystemSetting(key=key, value=value, description=description))
    await session.commit()


# ─── Referral Rates ───────────────────────────────────────────────────────────

@router.get("/referral-rates")
async def get_referral_rates(
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_page_access("pricing-config")),
):
    raw = await _get_setting(db, _REFERRAL_KEY, json.dumps(_DEFAULT_RATES))
    try:
        rates = {**_DEFAULT_RATES, **json.loads(raw)}
    except Exception:
        rates = _DEFAULT_RATES
    return rates


class ReferralRatesPayload(BaseModel):
    level_1: float = Field(ge=0, le=100)
    level_2: float = Field(ge=0, le=100)
    level_3: float = Field(ge=0, le=100)
    level_4: float = Field(ge=0, le=100)


@router.put("/referral-rates")
async def update_referral_rates(
    payload: ReferralRatesPayload,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_page_access("pricing-config")),
):
    rates = {
        "1": payload.level_1,
        "2": payload.level_2,
        "3": payload.level_3,
        "4": payload.level_4,
    }
    await _set_setting(db, _REFERRAL_KEY, json.dumps(rates), "4-level referral rates (%)")
    await log_action(
        db, current_user.get("admin_id"), "referral_rates_update",
        "system_settings", None, rates, request.client.host if request.client else None,
    )
    return {"ok": True, "rates": rates}


# ─── VIP Watchlist ─────────────────────────────────────────────────────────────

@router.get("/vip-watchlist")
async def get_vip_settings(
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_page_access("pricing-config")),
):
    description = await _get_setting(db, _VIP_DESC_KEY, "🌟 VIP Watchlist — $500\n\nPriority fulfillment by top specialists.")
    video_file_id = await _get_setting(db, _VIP_VIDEO_KEY, "")
    return {"description": description, "video_file_id": video_file_id}


class VIPWatchlistPayload(BaseModel):
    description: str = Field(max_length=4000)
    video_file_id: Optional[str] = None


@router.put("/vip-watchlist")
async def update_vip_settings(
    payload: VIPWatchlistPayload,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_page_access("pricing-config")),
):
    await _set_setting(db, _VIP_DESC_KEY, payload.description, "VIP Watchlist description shown in bot")
    await _set_setting(db, _VIP_VIDEO_KEY, payload.video_file_id or "", "VIP Watchlist video Telegram file_id")
    await log_action(
        db, current_user.get("admin_id"), "vip_watchlist_update",
        "system_settings", None, {"desc_len": len(payload.description)},
        request.client.host if request.client else None,
    )
    return {"ok": True}
