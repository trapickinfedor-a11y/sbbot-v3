from __future__ import annotations

import os
import csv
import io
from pathlib import Path
from decimal import Decimal
from datetime import datetime, timedelt, timezone
from typing import Optional

from aiogram.types import BufferedInputFile, InlineKeyboardButton, InlineKeyboardMarkup
from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from seller_bot.config import seller_bot_config
from shared.database.models import BruteBankItem, MirrorBot, SellerBank, SellerChat, SellerConversation, SellerDepositPayment, SellerOrder, SellerUploadBatch, SellerUploadTemplate, SellerWithdrawal
from shared.services.bot_pool import get_mirror_bot_instance
from shared.services.seller_actor_service import SellerActorContext, resolve_seller_actor
from shared.services.seller_deposit_service import SellerDepositService
from shared.services.seller_dispute_service import SellerDisputeService
from shared.services.notification_service import NotificationService
from shared.services.ledger_projection_service import LedgerProjectionService
from shared.services.seller_upload_batch_service import SellerUploadBatchService
from shared.services.seller_upload_pipeline_service import SellerUploadPipelineService
from seller_bot.services.special_stock_service import SpecialStockService
from seller_bot.services.stock_service import StockService
from shared.services.nocodb_service import NocoDBService
from shared.utils.chat_filter import filter_message, is_message_blocked
from shared.utils.chat_render import CHAT_MSG_LIMIT, get_chat_messages
from shared.utils.telegram_auth import validate_telegram_init_data
from web_panel.database import get_db
from web_panel.utils.rate_limiter import seller_mini_app_limiter

router = APIRouter(prefix="/api/seller-mini-app", tags=["seller-mini-app"])

MAX_SELLER_CHAT_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_PARSE_FILE_UPLOAD_BYTES = 1 * 1024 * 1024
ALLOWED_SELLER_CHAT_UPLOAD_CONTENT_TYPES = {
    "application/json",
    "application/octet-stream",
    "application/pdf",
    "application/zip",
    "application/x-zip-compressed",
    "text/csv",
    "text/plain",
}
ALLOWED_SELLER_CHAT_UPLOAD_EXTENSIONS = {
    ".csv",
    ".json",
    ".pdf",
    ".txt",
    ".zip",
}
ALLOWED_PARSE_FILE_CONTENT_TYPES = {
    "application/octet-stream",
    "text/csv",
    "text/plain",
}
ALLOWED_PARSE_FILE_EXTENSIONS = {
    ".csv",
    ".txt",
}


def _short_product_name(name: Optional[str], limit: int = 28) -> str:
    if not name:
        return "Product"
    clean = " ".join(name.split())
    return clean if len(clean) <= limit else clean[: limit - 1] + "…"


def _parse_and_verify_init_data(init_data: str) -> dict:
    if not seller_bot_config.bot_token:
        raise HTTPException(status_code=500, detail="SELLER_BOT_TOKEN is not configured")
    try:
        return validate_telegram_init_data(init_data, seller_bot_config.bot_token, max_age_seconds=3600)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


def _validate_uploaded_file(
    *,
    file_name: Optional[str],
    content_type: Optional[str],
    file_bytes: bytes,
    allowed_content_types: set[str],
    allowed_extensions: set[str],
    max_size_bytes: int,
    detail_prefix: str,
) -> None:
    if not file_bytes:
        raise HTTPException(status_code=400, detail=f"{detail_prefix}: file is empty")
    if len(file_bytes) > max_size_bytes:
        raise HTTPException(status_code=400, detail=f"{detail_prefix}: file is too large")

    normalized_content_type = (content_type or "").split(";", 1)[0].strip().lower()
    suffix = Path(file_name or "").suffix.lower()
    if normalized_content_type and suffix:
        if normalized_content_type in allowed_content_types and suffix in allowed_extensions:
            return
    elif normalized_content_type:
        if normalized_content_type in allowed_content_types:
            return
    elif suffix:
        if suffix in allowed_extensions:
            return
    raise HTTPException(status_code=400, detail=f"{detail_prefix}: unsupported file type")


async def get_current_seller_from_webapp(
    db: AsyncSession = Depends(get_db),
    telegram_init_data: Optional[str] = Header(default=None, alias="X-Telegram-Init-Data"),
):
    seller_tg_id: Optional[int] = None

    if telegram_init_data:
        user = _parse_and_verify_init_data(telegram_init_data)
        seller_tg_id = int(user["id"])

    if not seller_tg_id:
        raise HTTPException(status_code=401, detail="Telegram WebApp auth required")

    seller_actor = await resolve_seller_actor(db, seller_tg_id)
    if not seller_actor or seller_actor.pending_approval:
        raise HTTPException(status_code=403, detail="Seller access not found")
    return seller_actor


async def _seller_rate_limit(seller_actor: SellerActorContext = Depends(get_current_seller_from_webapp)) -> None:
    """Rate-limit by seller id: 30 requests/minute."""
    if not seller_mini_app_limiter._is_allowed(seller_actor.seller.id):
        raise HTTPException(status_code=429, detail="Too many requests — max 30 per minute per seller")


class UploadPreviewRequest(BaseModel):
    item_type: str
    payload: dict


class UploadSubmitRequest(BaseModel):
    item_type: str
    payload: dict
    resubmitted_from_batch_id: Optional[int] = None


def _serialize_batch(batch: SellerUploadBatch) -> dict:
    return {
        "id": batch.id,
        "item_type": batch.item_type,
        "upload_mode": batch.upload_mode,
        "title": batch.title,
        "total_items": batch.total_items,
        "moderation_status": batch.moderation_status,
        "moderation_comment": batch.moderation_comment,
        "draft_payload": batch.draft_payload,
        "validation_summary": batch.validation_summary,
        "error_report": batch.error_report,
        "submitted_at": batch.submitted_at.isoformat() if batch.submitted_at else None,
        "reviewed_at": batch.reviewed_at.isoformat() if batch.reviewed_at else None,
        "resubmitted_from_batch_id": batch.resubmitted_from_batch_id,
        "approved_items": int(batch.approved_items or 0),
        "rejected_items": int(batch.rejected_items or 0),
        "changes_requested_items": int(batch.changes_requested_items or 0),
        "pending_items": int(batch.pending_items or 0),
        "created_at": batch.created_at.isoformat() if batch.created_at else None,
        "updated_at": batch.updated_at.isoformat() if batch.updated_at else None,
    }


async def _get_latest_order_for_conversation(db: AsyncSession, conv: SellerConversation) -> Optional[SellerOrder]:
    result = await db.execute(
        select(SellerOrder)
        .where(
            and_(
                SellerOrder.seller_id == conv.seller_id,
                SellerOrder.buyer_user_id == conv.buyer_user_id,
                SellerOrder.mirror_bot_id == conv.mirror_bot_id,
            )
        )
        .order_by(SellerOrder.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _get_conversation_product_label(db: AsyncSession, conv: SellerConversation, latest_order: Optional[SellerOrder]) -> str:
    if latest_order:
        seller_bank = None
        if latest_order.seller_bank_id:
            seller_bank = await db.scalar(select(SellerBank).where(SellerBank.id == latest_order.seller_bank_id))
        if seller_bank and seller_bank.bank_name:
            return _short_product_name(seller_bank.bank_name)
    latest_message = await db.scalar(
        select(SellerChat)
        .where(
            and_(
                SellerChat.seller_conversation_id == conv.id,
                SellerChat.seller_order_id.is_not(None),
            )
        )
        .order_by(SellerChat.created_at.desc())
        .limit(1)
    )
    if latest_message and latest_message.seller_order_id:
        order = await db.scalar(select(SellerOrder).where(SellerOrder.id == latest_message.seller_order_id))
        if order:
            seller_bank = await db.scalar(select(SellerBank).where(SellerBank.id == order.seller_bank_id))
            if seller_bank and seller_bank.bank_name:
                return _short_product_name(seller_bank.bank_name)
    return "Buyer chat"


@router.get("/me")
async def seller_mini_app_me(seller_actor: SellerActorContext = Depends(get_current_seller_from_webapp)):
    seller = seller_actor.seller
    return {
        "seller_id": seller.id,
        "telegram_id": seller.telegram_id,
        "display_name": seller.display_name or seller.username or f"Seller {seller.id}",
        "actor_role": seller_actor.role,
        "is_helper": seller_actor.is_helper,
        "access_status": getattr(seller, "access_status", "pending_deposit"),
        "security_deposit_status": getattr(seller, "security_deposit_status", "unpaid"),
        "allowed_categories": sorted(SellerDepositService.allowed_categories(seller)),
        "is_on_vacation": bool(getattr(seller, "is_on_vacation", False)),
        "auto_payout_enabled": bool(getattr(seller, "auto_payout_enabled", False)),
        "auto_payout_threshold": float(getattr(seller, "auto_payout_threshold", 1000) or 1000),
        "quiet_hours_start": getattr(seller, "quiet_hours_start", None),
        "quiet_hours_end": getattr(seller, "quiet_hours_end", None),
        "vacation_started_at": getattr(seller, "vacation_started_at", None),
        "vacation_ends_at": getattr(seller, "vacation_ends_at", None),
    }


@router.get("/conversations")
async def seller_mini_app_conversations(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    seller_actor: SellerActorContext = Depends(get_current_seller_from_webapp),
):
    if not seller_actor.can_support():
        raise HTTPException(status_code=403, detail="Chat access denied")
    seller = seller_actor.seller
    offset = (page - 1) * per_page

    total_result = await db.scalar(
        select(func.count(SellerConversation.id)).where(SellerConversation.seller_id == seller.id)
    )
    total = total_result or 0

    result = await db.execute(
        select(SellerConversation)
        .where(SellerConversation.seller_id == seller.id)
        .order_by(SellerConversation.updated_at.desc(), SellerConversation.id.desc())
        .limit(per_page)
        .offset(offset)
    )
    conversations = list(result.scalars().all())
    payload = []
    for conv in conversations:
        latest_message = await db.scalar(
            select(SellerChat)
            .where(SellerChat.seller_conversation_id == conv.id)
            .order_by(SellerChat.created_at.desc())
            .limit(1)
        )
        unread_count = await db.scalar(
            select(func.count(SellerChat.id)).where(
                and_(
                    SellerChat.seller_conversation_id == conv.id,
                    SellerChat.sender_type == "buyer",
                    SellerChat.is_read == False,
                )
            )
        )
        latest_order = await _get_latest_order_for_conversation(db, conv)
        product_label = await _get_conversation_product_label(db, conv, latest_order)
        if seller_actor.is_helper and seller_actor.role == "support_helper":
            if conv.assigned_helper_id not in (None, seller_actor.helper.id):
                continue
        payload.append(
            {
                "id": conv.id,
                "buyer_label": "Buyer",
                "mirror_bot_id": conv.mirror_bot_id,
                "product_label": product_label,
                "latest_message": latest_message.message_text if latest_message else "",
                "latest_message_at": latest_message.created_at.isoformat() if latest_message else None,
                "unread_count": unread_count or 0,
                "latest_order_id": latest_order.id if latest_order else None,
                "latest_order_status": latest_order.status if latest_order else None,
            }
        )
    return {
        "items": payload,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": max(1, (total + per_page - 1) // per_page),
    }


@router.get("/messages")
async def seller_mini_app_messages(
    conv_id: int = Query(...),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    seller_actor: SellerActorContext = Depends(get_current_seller_from_webapp),
):
    if not seller_actor.can_support():
        raise HTTPException(status_code=403, detail="Chat access denied")
    seller = seller_actor.seller
    conv = await db.scalar(
        select(SellerConversation).where(
            and_(SellerConversation.id == conv_id, SellerConversation.seller_id == seller.id)
        )
    )
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if seller_actor.is_helper and seller_actor.role == "support_helper" and conv.assigned_helper_id not in (None, seller_actor.helper.id):
        raise HTTPException(status_code=403, detail="Conversation is assigned to another helper")

    messages, total = await get_chat_messages(db, conversation_id=conv_id, offset=offset, limit=CHAT_MSG_LIMIT)
    for msg in messages:
        if msg.sender_type == "buyer" and not msg.is_read:
            msg.is_read = True
    await db.commit()

    return {
        "conversation": {
            "id": conv.id,
            "buyer_label": "Buyer",
            "mirror_bot_id": conv.mirror_bot_id,
        },
        "total": total,
        "messages": [
            {
                "id": msg.id,
                "sender_type": msg.sender_type,
                "message_text": msg.message_text,
                "files": msg.files,
                "created_at": msg.created_at.isoformat(),
                "is_read": msg.is_read,
            }
            for msg in messages
        ],
    }


@router.post("/send", dependencies=[Depends(lambda: None)])  # Rate limit applied via middleware
async def seller_mini_app_send(
    conv_id: int = Form(...),
    text: str = Form(""),
    file: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
    seller_actor: SellerActorContext = Depends(get_current_seller_from_webapp),
):
    if not seller_actor.can_support():
        raise HTTPException(status_code=403, detail="Chat access denied")
    seller = seller_actor.seller
    conv = await db.scalar(
        select(SellerConversation).where(
            and_(SellerConversation.id == conv_id, SellerConversation.seller_id == seller.id)
        )
    )
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if seller_actor.is_helper and seller_actor.role == "support_helper" and conv.assigned_helper_id not in (None, seller_actor.helper.id):
        raise HTTPException(status_code=403, detail="Conversation is assigned to another helper")
    if seller_actor.is_helper and conv.assigned_helper_id is None:
        conv.assigned_helper_id = seller_actor.helper.id
        conv.assigned_at = datetime.now(timezone.utc)
        conv.assigned_by = seller_actor.actor_telegram_id

    if not text.strip() and not file:
        raise HTTPException(status_code=400, detail="Message text or file is required")
    if file and (file.content_type or "").startswith("image/"):
        raise HTTPException(status_code=400, detail="Seller cannot send photos from Mini App")

    if not conv.mirror_bot_id:
        raise HTTPException(status_code=400, detail="Mirror bot is missing for this buyer")

    mirror_bot = await db.scalar(select(MirrorBot).where(MirrorBot.id == conv.mirror_bot_id))
    if not mirror_bot:
        raise HTTPException(status_code=404, detail="Mirror bot not found")

    latest_order = await _get_latest_order_for_conversation(db, conv)
    buyer_bot = get_mirror_bot_instance(mirror_bot.bot_token)
    reply_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💬 Reply", callback_data=f"buyer_chat_conv:{conv.id}:{latest_order.id if latest_order else 0}")]
        ]
    )
    header = "💬 <b>The seller of this product wrote to you</b>\n\n"
    raw_text = text.strip()
    if raw_text and is_message_blocked(raw_text):
        raise HTTPException(status_code=400, detail="Message contains only blocked contact information")
    filtered_text = filter_message(raw_text)

    files_payload = None
    file_bytes = b""
    if file:
        file_bytes = await file.read()
        _validate_uploaded_file(
            file_name=file.filename,
            content_type=file.content_type,
            file_bytes=file_bytes,
            allowed_content_types=ALLOWED_SELLER_CHAT_UPLOAD_CONTENT_TYPES,
            allowed_extensions=ALLOWED_SELLER_CHAT_UPLOAD_EXTENSIONS,
            max_size_bytes=MAX_SELLER_CHAT_UPLOAD_BYTES,
            detail_prefix="Mini App upload rejected",
        )
        file_label_source = file.filename or "seller_file"
        if file_label_source and is_message_blocked(file_label_source):
            file_label = "seller_file"
        else:
            file_label = filter_message(file_label_source) or "seller_file"
        sent = await buyer_bot.send_document(
            conv.buyer_user_id,
            document=BufferedInputFile(file_bytes, filename=file_label),
            caption=header + (filtered_text or ""),
            parse_mode="HTML",
            reply_markup=reply_kb,
        )
        if sent.document:
            files_payload = [sent.document.file_id]
    else:
        await buyer_bot.send_message(
            conv.buyer_user_id,
            header + filtered_text,
            parse_mode="HTML",
            reply_markup=reply_kb,
        )

    chat_message = SellerChat(
        seller_conversation_id=conv.id,
        seller_order_id=latest_order.id if latest_order else None,
        sender_type="seller",
        sender_id=seller_actor.actor_telegram_id,
        message_text=filtered_text or f"[file] {file_label if file else 'seller_file'}",
        files=files_payload,
    )
    db.add(chat_message)
    if latest_order:
        await SellerDisputeService.mark_seller_responded(
            db,
            order_id=latest_order.id,
            message_text=filtered_text,
            files=files_payload,
        )
    conv.updated_at = datetime.now(timezone.utc)
    await db.commit()
    NocoDBService.log_seller_buyer_chat(
        order_id=latest_order.id if latest_order else getattr(conv, "source_order_id", None),
        seller_id=conv.seller_id,
        buyer_id=conv.buyer_user_id,
        message=filtered_text or f"[file] {file_label if file else 'seller_file'}",
        files=files_payload,
        extra={
            "sender_type": "seller",
            "sender_id": seller_actor.actor_telegram_id,
            "conversation_id": conv.id,
            "source": "seller_mini_app",
        },
    )

    return {"ok": True}


class VacationToggleRequest(BaseModel):
    enabled: bool
    ends_at: Optional[datetime] = None


class SellerTemplateCreateRequest(BaseModel):
    item_type: str
    title: str
    payload: dict


class SellerBulkPriceRequest(BaseModel):
    listing_ids: list[int]
    mode: str  # set | percent | delta
    value: Decimal


def _serialize_template(template: SellerUploadTemplate) -> dict:
    return {
        "id": template.id,
        "item_type": template.item_type,
        "title": template.title,
        "payload": template.payload,
        "created_at": template.created_at.isoformat() if template.created_at else None,
        "updated_at": template.updated_at.isoformat() if template.updated_at else None,
    }


@router.post("/settings/vacation")
async def seller_vacation_toggle(
    body: VacationToggleRequest,
    db: AsyncSession = Depends(get_db),
    seller_actor: SellerActorContext = Depends(get_current_seller_from_webapp),
):
    seller = seller_actor.seller
    seller.is_on_vacation = bool(body.enabled)
    seller.vacation_started_at = datetime.now(timezone.utc) if body.enabled else None
    seller.vacation_ends_at = body.ends_at if body.enabled else None
    await db.commit()
    return {
        "ok": True,
        "is_on_vacation": bool(seller.is_on_vacation),
        "vacation_started_at": seller.vacation_started_at,
        "vacation_ends_at": seller.vacation_ends_at,
    }


class AutoPayoutRequest(BaseModel):
    enabled: bool
    threshold: Optional[float] = 1000.0


@router.post("/settings/auto-payout")
async def seller_auto_payout_toggle(
    body: AutoPayoutRequest,
    db: AsyncSession = Depends(get_db),
    seller_actor: SellerActorContext = Depends(get_current_seller_from_webapp),
):
    seller = seller_actor.seller
    seller.auto_payout_enabled = bool(body.enabled)
    if body.threshold and body.threshold > 0:
        from decimal import Decimal as _Dec
        seller.auto_payout_threshold = _Dec(str(body.threshold))
    await db.commit()
    return {
        "ok": True,
        "auto_payout_enabled": bool(seller.auto_payout_enabled),
        "auto_payout_threshold": float(seller.auto_payout_threshold or 1000),
    }


class QuietHoursRequest(BaseModel):
    quiet_hours_start: Optional[int] = None  # 0-23 UTC hour or null to disable
    quiet_hours_end: Optional[int] = None


@router.post("/settings/quiet-hours")
async def seller_quiet_hours(
    body: QuietHoursRequest,
    db: AsyncSession = Depends(get_db),
    seller_actor: SellerActorContext = Depends(get_current_seller_from_webapp),
):
    """Set or clear quiet hours for seller notifications."""
    seller = seller_actor.seller
    seller.quiet_hours_start = body.quiet_hours_start
    seller.quiet_hours_end = body.quiet_hours_end
    await db.commit()
    return {
        "ok": True,
        "quiet_hours_start": seller.quiet_hours_start,
        "quiet_hours_end": seller.quiet_hours_end,
    }


@router.get("/analytics/summary")
async def seller_analytics_summary(
    db: AsyncSession = Depends(get_db),
    seller_actor: SellerActorContext = Depends(get_current_seller_from_webapp),
):
    seller = seller_actor.seller
    total_orders = int(await db.scalar(select(func.count(SellerOrder.id)).where(SellerOrder.seller_id == seller.id)) or 0)
    completed_orders = int(
        await db.scalar(
            select(func.count(SellerOrder.id)).where(
                SellerOrder.seller_id == seller.id,
                SellerOrder.status == "completed",
            )
        ) or 0
    )
    active_listings = int(
        await db.scalar(
            select(func.count(SellerBank.id)).where(
                SellerBank.seller_id == seller.id,
                SellerBank.is_active == True,
            )
        ) or 0
    )
    gross_sales = Decimal(
        str(
            await db.scalar(
                select(func.coalesce(func.sum(SellerOrder.price_for_buyer), 0)).where(
                    SellerOrder.seller_id == seller.id,
                    SellerOrder.completed_at.is_not(None),
                )
            ) or 0
        )
    )
    projection = await LedgerProjectionService.get_seller_projection(db, seller.id)
    feedback_total = int(getattr(seller, "likes_count", 0) or 0) + int(getattr(seller, "dislikes_count", 0) or 0)
    completion_rate = round((completed_orders / total_orders) * 100, 2) if total_orders else 0.0
    rating = round((int(getattr(seller, "likes_count", 0) or 0) / feedback_total) * 5, 2) if feedback_total else 0.0
    return {
        "total_orders": total_orders,
        "completed_orders": completed_orders,
        "completion_rate": completion_rate,
        "gross_sales": float(gross_sales),
        "net_earned": float(projection["total_earned"]),
        "pending_balance": float(projection["pending_balance"]),
        "withdrawable_balance": float(projection["withdrawable_balance"]),
        "active_listings": active_listings,
        "rating": rating,
        "likes": int(getattr(seller, "likes_count", 0) or 0),
        "dislikes": int(getattr(seller, "dislikes_count", 0) or 0),
    }


@router.get("/analytics/funnel")
async def seller_analytics_funnel(
    db: AsyncSession = Depends(get_db),
    seller_actor: SellerActorContext = Depends(get_current_seller_from_webapp),
):
    """Conversion funnel analytics: listings → orders → completed → revenue."""
    seller = seller_actor.seller

    # Total active listings
    total_listings = int(await db.scalar(
        select(func.count(SellerBank.id)).where(
            SellerBank.seller_id == seller.id,
            SellerBank.is_active == True,
        )
    ) or 0)

    # Total orders placed (any status)
    total_orders = int(await db.scalar(
        select(func.count(SellerOrder.id)).where(SellerOrder.seller_id == seller.id)
    ) or 0)

    # Completed orders
    completed_orders = int(await db.scalar(
        select(func.count(SellerOrder.id)).where(
            SellerOrder.seller_id == seller.id,
            SellerOrder.status == "completed",
        )
    ) or 0)

    # Disputed orders
    disputed_orders = int(await db.scalar(
        select(func.count(SellerOrder.id)).where(
            SellerOrder.seller_id == seller.id,
            SellerOrder.status == "disputed",
        )
    ) or 0)

    # Revenue (last 30 days vs previous 30 days for trend)
    from datetime import timedelt, timezone
    from sqlalchemy import and_
    now = datetime.now(timezone.utc)
    period_30 = now - timedelta(days=30)
    period_60 = now - timedelta(days=60)

    rev_30 = float(await db.scalar(
        select(func.coalesce(func.sum(SellerOrder.price_for_buyer), 0)).where(
            SellerOrder.seller_id == seller.id,
            SellerOrder.completed_at >= period_30,
        )
    ) or 0)
    rev_prev_30 = float(await db.scalar(
        select(func.coalesce(func.sum(SellerOrder.price_for_buyer), 0)).where(
            SellerOrder.seller_id == seller.id,
            SellerOrder.completed_at >= period_60,
            SellerOrder.completed_at < period_30,
        )
    ) or 0)

    rev_trend = round(((rev_30 - rev_prev_30) / rev_prev_30 * 100), 1) if rev_prev_30 else 0.0

    # Top-5 products by sales count
    top_rows = (await db.execute(
        select(SellerBank.bank_name, SellerBank.category, func.count(SellerOrder.id).label("cnt"))
        .join(SellerOrder, SellerOrder.seller_bank_id == SellerBank.id, isouter=True)
        .where(SellerBank.seller_id == seller.id)
        .group_by(SellerBank.id, SellerBank.bank_name, SellerBank.category)
        .order_by(func.count(SellerOrder.id).desc())
        .limit(5)
    )).all()

    # Conversion rates
    listing_to_order = round(total_orders / total_listings * 100, 1) if total_listings else 0.0
    order_to_complete = round(completed_orders / total_orders * 100, 1) if total_orders else 0.0
    dispute_rate = round(disputed_orders / total_orders * 100, 1) if total_orders else 0.0

    return {
        "funnel": [
            {"stage": "Active Listings", "value": total_listings, "icon": "📦"},
            {"stage": "Orders Placed", "value": total_orders, "icon": "🛒"},
            {"stage": "Completed", "value": completed_orders, "icon": "✅"},
        ],
        "conversion": {
            "listing_to_order": listing_to_order,
            "order_to_complete": order_to_complete,
            "dispute_rate": dispute_rate,
        },
        "revenue": {
            "last_30_days": rev_30,
            "prev_30_days": rev_prev_30,
            "trend_pct": rev_trend,
        },
        "top_products": [
            {"name": r.bank_name, "category": r.category, "sales": r.cnt}
            for r in top_rows
        ],
    }


@router.get("/finance/summary")
async def seller_finance_summary(
    db: AsyncSession = Depends(get_db),
    seller_actor: SellerActorContext = Depends(get_current_seller_from_webapp),
):
    seller = seller_actor.seller
    projection = await LedgerProjectionService.get_seller_projection(db, seller.id)
    completed_amount = Decimal(
        str(
            await db.scalar(
                select(func.coalesce(func.sum(SellerOrder.price_for_buyer), 0)).where(
                    SellerOrder.seller_id == seller.id,
                    SellerOrder.completed_at.is_not(None),
                )
            ) or 0
        )
    )
    return {
        "seller_id": seller.id,
        "gross_sales": float(completed_amount),
        "pending_balance": float(projection["pending_balance"]),
        "withdrawable_balance": float(projection["withdrawable_balance"]),
        "total_earned": float(projection["total_earned"]),
        "security_deposit_balance": float(Decimal(str(getattr(seller, "security_deposit_balance", 0) or 0))),
    }


@router.get("/finance/export.csv")
async def seller_finance_export(
    db: AsyncSession = Depends(get_db),
    seller_actor: SellerActorContext = Depends(get_current_seller_from_webapp),
):
    seller = seller_actor.seller
    try:
        result = await db.execute(
            select(SellerOrder)
            .where(SellerOrder.seller_id == seller.id)
            .order_by(SellerOrder.created_at.desc())
            .limit(1000)
        )
        orders = list(result.scalars().all())
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["order_id", "status", "buyer_amount", "seller_amount", "platform_fee", "created_at", "completed_at"])
        for order in orders:
            buyer_amount = Decimal(str(order.price_for_buyer or 0))
            seller_amount = Decimal(str(order.price_for_seller or 0))
            writer.writerow([
                order.id,
                order.status,
                f"{buyer_amount:.2f}",
                f"{seller_amount:.2f}",
                f"{(buyer_amount - seller_amount):.2f}",
                order.created_at.isoformat() if order.created_at else "",
                order.completed_at.isoformat() if order.completed_at else "",
            ])
        return Response(
            content=buffer.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="seller-finance-export.csv"'},
        )
    except Exception as exc:
        import logging as _log
        _log.getLogger(__name__).error("finance export error seller=%s: %s", seller.id, exc)
        raise HTTPException(status_code=500, detail="Export failed")


# ── NEW: Orders list for mini app ──────────────────────────────────────────
@router.get("/orders")
async def seller_mini_app_orders(
    status_filter: Optional[str] = Query(default="active"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    seller_actor: SellerActorContext = Depends(get_current_seller_from_webapp),
):
    """Return seller orders with pagination, never exposing buyer_user_id."""
    seller = seller_actor.seller
    base_where = [SellerOrder.seller_id == seller.id]

    if status_filter == "active":
        base_where.append(SellerOrder.status.in_(["approved", "in_progress"]))
    elif status_filter == "completed":
        base_where.append(SellerOrder.status == "completed")
    elif status_filter == "disputed":
        base_where.append(SellerOrder.status == "disputed")
    # "all" — no extra filter

    total = await db.scalar(select(func.count(SellerOrder.id)).where(*base_where)) or 0
    offset = (page - 1) * per_page

    query = select(SellerOrder, SellerBank).join(
        SellerBank, SellerOrder.seller_bank_id == SellerBank.id, isouter=True
    ).where(*base_where)

    query = query.order_by(SellerOrder.created_at.desc()).limit(per_page).offset(offset)
    result = await db.execute(query)
    rows = result.all()

    def _ser(order: SellerOrder, bank: Optional[SellerBank]) -> dict:
        return {
            "id": order.id,
            "status": order.status,
            "product_type": order.product_type,
            "product_subtype": order.product_subtype,
            "bank_name": bank.bank_name if bank else None,
            "category": bank.category if bank else None,
            "quantity": order.quantity,
            "price_for_seller": float(order.price_for_seller),
            "price_for_buyer": float(order.price_for_buyer),
            "escrow_released": order.escrow_released,
            "seller_notes": order.seller_notes,
            "admin_notes": order.admin_notes,
            "created_at": order.created_at.isoformat() if order.created_at else None,
            "taken_at": order.taken_at.isoformat() if order.taken_at else None,
            "completed_at": order.completed_at.isoformat() if order.completed_at else None,
            "auto_complete_at": order.auto_complete_at.isoformat() if order.auto_complete_at else None,
            "dispute_deadline_at": order.dispute_deadline_at.isoformat() if order.dispute_deadline_at else None,
        }

    return {
        "items": [_ser(o, b) for o, b in rows],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": max(1, (total + per_page - 1) // per_page),
    }


# ── NEW: Withdrawal request for mini app ───────────────────────────────────
class WithdrawRequest(BaseModel):
    amount: float
    requisites: str


@router.post("/finance/withdraw")
async def seller_mini_app_withdraw(
    body: WithdrawRequest,
    db: AsyncSession = Depends(get_db),
    seller_actor: SellerActorContext = Depends(get_current_seller_from_webapp),
):
    seller = seller_actor.seller
    if not seller_actor.can_manage_finance():
        raise HTTPException(status_code=403, detail="Finance access required")

    projection = await LedgerProjectionService.get_seller_projection(db, seller.id)
    withdrawable = float(projection["withdrawable_balance"])
    amount = round(float(body.amount), 2)

    # Security: Minimum withdrawal amount
    MIN_WITHDRAWAL = 10.0
    if amount < MIN_WITHDRAWAL:
        raise HTTPException(status_code=400, detail=f"Minimum withdrawal amount is ${MIN_WITHDRAWAL:.2f}")
    
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    if amount > withdrawable:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient withdrawable balance (${withdrawable:.2f} available)",
        )
    if not body.requisites or len(body.requisites.strip()) < 5:
        raise HTTPException(status_code=400, detail="Please provide valid payment requisites")
    
    # Security: Check for recent withdrawals (prevent spam)
    recent_check = datetime.now(timezone.utc) - timedelta(hours=1)
    recent_withdrawal = await db.scalar(
        select(SellerWithdrawal).where(
            SellerWithdrawal.seller_id == seller.id,
            SellerWithdrawal.created_at >= recent_check,
        ).order_by(SellerWithdrawal.created_at.desc())
    )
    if recent_withdrawal:
        raise HTTPException(
            status_code=429,
            detail="Please wait at least 1 hour between withdrawal requests"
        )

    withdrawal = SellerWithdrawal(
        seller_id=seller.id,
        amount=Decimal(str(amount)),
        requisites=body.requisites.strip(),
        status="pending",
    )
    db.add(withdrawal)
    await db.flush()   # flush чтобы получить DB-generated id до commit
    withdrawal_id = withdrawal.id
    await db.commit()

    # Notify seller about withdrawal request
    await NotificationService.send(
        role="seller",
        user_id=seller.id,
        text=(
            f"💸 <b>Withdrawal request submitted</b>\n\n"
            f"Amount: <b>${amount:.2f}</b>\n"
            f"Request ID: <code>#{withdrawal_id}</code>\n"
            f"Status: pending review"
        ),
        event_type="withdrawal_requested",
    )

    return {"ok": True, "withdrawal_id": withdrawal_id, "amount": amount, "status": "pending"}


# ── Deposit system ────────────────────────────────────────────────────────

class DepositBuyRequest(BaseModel):
    package_id: str  # package code: "bank", "cc", "bank_plus", "cc_plus", "full"


@router.get("/deposit/status")
async def seller_deposit_status(
    db: AsyncSession = Depends(get_db),
    seller_actor: SellerActorContext = Depends(get_current_seller_from_webapp),
):
    """Current seller deposit balance and status."""
    seller = seller_actor.seller
    balance = float(Decimal(str(getattr(seller, "security_deposit_balance", 0) or 0)))
    paid_at = getattr(seller, "security_deposit_paid_at", None)
    return {
        "balance": balance,
        "currency": "USD",
        "status": getattr(seller, "security_deposit_status", "unpaid"),
        "allowed_categories": sorted(SellerDepositService.allowed_categories(seller)),
        "last_deposit_at": paid_at.isoformat() if paid_at else None,
    }


@router.get("/deposit/packages")
async def seller_deposit_packages(
    seller_actor: SellerActorContext = Depends(get_current_seller_from_webapp),
):
    """Available deposit packages with pricing and descriptions."""
    from shared.services.seller_deposit_service import PACKAGE_AMOUNTS, PACKAGE_CATEGORIES
    packages = []
    for idx, (code, amount) in enumerate(PACKAGE_AMOUNTS.items()):
        categories = sorted(PACKAGE_CATEGORIES.get(code, set()))
        packages.append({
            "id": code,
            "label": SellerDepositService.package_label(code),
            "amount": float(amount),
            "currency": "USD",
            "categories": categories,
            "popular": code == "full",
        })
    return {"packages": packages}


@router.post("/deposit/buy")
async def seller_deposit_buy(
    body: DepositBuyRequest,
    db: AsyncSession = Depends(get_db),
    seller_actor: SellerActorContext = Depends(get_current_seller_from_webapp),
    _rl: None = Depends(_seller_rate_limit),
):
    """Initiate a deposit purchase — creates a BTCPay invoice and returns checkout URL."""
    seller = seller_actor.seller
    package_code = body.package_id.strip().lower()
    try:
        payment = await SellerDepositService.create_btcpay_invoice(
            db, seller, package_code
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "success": True,
        "transaction_id": payment.id,
        "package_code": payment.package_code,
        "amount": float(payment.amount),
        "currency": payment.currency,
        "checkout_url": payment.checkout_url,
        "status": payment.status,
        "expires_at": payment.expires_at.isoformat() if payment.expires_at else None,
    }


@router.get("/listings")
async def seller_listings(
    db: AsyncSession = Depends(get_db),
    seller_actor: SellerActorContext = Depends(get_current_seller_from_webapp),
):
    seller = seller_actor.seller
    rows = list(
        (
            await db.execute(
                select(SellerBank)
                .where(SellerBank.seller_id == seller.id, SellerBank.is_active == True)
                .order_by(SellerBank.updated_at.desc(), SellerBank.id.desc())
                .limit(200)
            )
        ).scalars().all()
    )
    return [
        {
            "id": row.id,
            "bank_name": row.bank_name,
            "bank_code": row.bank_code,
            "category": row.category,
            "seller_price": float(Decimal(str(row.seller_price or 0))),
            "buyer_price": float(Decimal(str(row.buyer_price or 0))),
            "stock_count": int(row.stock_count or 0),
            "reserved_count": int(getattr(row, "reserved_count", 0) or 0),
            "moderation_status": row.moderation_status,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }
        for row in rows
    ]


@router.get("/orders/{order_id}/dispute")
async def get_order_dispute(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    seller_actor: SellerActorContext = Depends(get_current_seller_from_webapp),
):
    """Get dispute details for an order"""
    seller = seller_actor.seller
    
    # Find seller order
    order = await db.get(SellerOrder, order_id)
    if not order or order.seller_id != seller.id:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Get dispute from NocoDB or DB
    # For now, return dispute status from order
    return {
        "id": order_id,
        "order_id": order_id,
        "status": "disputed" if order.status == "disputed" else "open",
        "reason": getattr(order, "dispute_reason", None),
        "description": getattr(order, "dispute_description", None),
        "opened_by": "buyer",
        "opened_at": order.disputed_at.isoformat() if order.disputed_at else None,
        "messages": []  # Would need separate dispute_messages table
    }


@router.post("/orders/{order_id}/dispute/reply")
async def reply_to_dispute(
    order_id: int,
    body: dict,
    db: AsyncSession = Depends(get_db),
    seller_actor: SellerActorContext = Depends(get_current_seller_from_webapp),
):
    """Reply to a dispute"""
    seller = seller_actor.seller
    
    order = await db.get(SellerOrder, order_id)
    if not order or order.seller_id != seller.id:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.status != "disputed":
        raise HTTPException(status_code=400, detail="Order is not in dispute")
    
    # Save reply (would need dispute_messages table)
    # For now, just log
    message = body.get("message", "")
    
    # NocoDB log
    NocoDBService.log_seller_buyer_chat(
        order_id=order_id,
        seller_id=seller.id,
        buyer_id=order.buyer_user_id,
        message=message,
        files=None,
        extra={"type": "dispute_reply", "from": "seller"}
    )
    
    return {"ok": True, "message": "Reply submitted"}


@router.post("/orders/{order_id}/dispute/accept")
async def accept_dispute(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    seller_actor: SellerActorContext = Depends(get_current_seller_from_webapp),
):
    """Accept dispute - refund buyer"""
    seller = seller_actor.seller
    
    order = await db.get(SellerOrder, order_id)
    if not order or order.seller_id != seller.id:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.status != "disputed":
        raise HTTPException(status_code=400, detail="Order is not in dispute")
    
    # Process refund
    order.status = "refunded"
    await db.commit()

    # Audit
    from shared.services.audit_event_service import AuditEventService
    await AuditEventService.log(
        session=db,
        seller_id=seller.id,
        action_type="dispute_accepted",
        description=f"Seller accepted dispute for order {order_id}",
        target_type="seller_order",
        target_id=order_id,
    )

    # Telegram notification to seller
    await NotificationService.send(
        role="seller",
        user_id=seller.id,
        text=(
            f"✅ <b>Dispute resolved</b>\n\n"
            f"Order <code>#{order_id}</code> — you accepted the dispute.\n"
            f"Buyer has been refunded."
        ),
        event_type="dispute_accepted",
    )

    return {"ok": True, "status": "refunded"}


@router.post("/orders/{order_id}/dispute/escalate")
async def escalate_dispute(
    order_id: int,
    body: dict,
    db: AsyncSession = Depends(get_db),
    seller_actor: SellerActorContext = Depends(get_current_seller_from_webapp),
):
    """Escalate dispute to admin"""
    seller = seller_actor.seller
    
    order = await db.get(SellerOrder, order_id)
    if not order or order.seller_id != seller.id:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.status != "disputed":
        raise HTTPException(status_code=400, detail="Order is not in dispute")
    
    # Mark for admin review
    order.admin_notes = body.get("admin_note", "Escalated by seller")
    await db.commit()
    
    # Notify admin
    from shared.services.admin_notification_service import AdminNotificationService
    await AdminNotificationService.notify_dispute_escalation(db, order_id, seller.id)
    
    return {"ok": True, "message": "Escalated to admin"}


@router.post("/orders/{order_id}/dispute/open")
async def open_dispute_as_seller(
    order_id: int,
    body: dict,
    db: AsyncSession = Depends(get_db),
    seller_actor: SellerActorContext = Depends(get_current_seller_from_webapp),
):
    """Seller opens dispute (rare case)"""
    seller = seller_actor.seller
    
    order = await db.get(SellerOrder, order_id)
    if not order or order.seller_id != seller.id:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Open dispute
    order.status = "disputed"
    order.disputed_at = datetime.now(timezone.utc)
    # Set dispute deadline (24 hours from now)
    order.dispute_deadline_at = datetime.now(timezone.utc) + timedelta(hours=24)

    await db.commit()

    # Audit
    from shared.services.audit_event_service import AuditEventService
    await AuditEventService.log(
        session=db,
        seller_id=seller.id,
        action_type="dispute_opened",
        description=f"Seller opened dispute for order {order_id}",
        target_type="seller_order",
        target_id=order_id,
    )

    # Telegram notification to seller
    await NotificationService.send(
        role="seller",
        user_id=seller.id,
        text=(
            f"⚠️ <b>Dispute opened</b>\n\n"
            f"You opened a dispute for order <code>#{order_id}</code>.\n"
            f"Admin review will begin shortly. Deadline: 24h."
        ),
        event_type="dispute_opened",
    )
    # Notify support/admin
    await NotificationService.broadcast(
        roles=["support", "admin"],
        text=(
            f"⚠️ <b>New dispute opened by seller</b>\n\n"
            f"Order: <code>#{order_id}</code>\n"
            f"Seller ID: {seller.id}"
        ),
        event_type="dispute_opened",
    )

    return {"ok": True, "status": "disputed"}


@router.get("/listings/price-comparison")
async def seller_listing_price_comparison(
    db: AsyncSession = Depends(get_db),
    seller_actor: SellerActorContext = Depends(get_current_seller_from_webapp),
):
    """Compare seller's listing prices with platform average per category."""
    seller = seller_actor.seller
    rows = list(
        (
            await db.execute(
                select(SellerBank)
                .where(SellerBank.seller_id == seller.id, SellerBank.is_active == True)
                .limit(200)
            )
        ).scalars().all()
    )
    categories = list({r.category for r in rows if r.category})
    result = []
    for cat in categories:
        avg_r = await db.scalar(
            select(func.avg(SellerBank.buyer_price)).where(
                SellerBank.category == cat,
                SellerBank.is_active == True,
                SellerBank.moderation_status == "approved",
            )
        )
        market_avg = float(avg_r or 0)
        seller_items = [r for r in rows if r.category == cat]
        for item in seller_items:
            my_price = float(item.buyer_price or item.seller_price or 0)
            diff_pct = ((my_price - market_avg) / market_avg * 100) if market_avg > 0 else 0
            result.append({
                "id": item.id,
                "bank_name": item.bank_name,
                "category": cat,
                "my_price": my_price,
                "market_avg": round(market_avg, 2),
                "diff_pct": round(diff_pct, 1),
                "positioning": "above" if diff_pct > 5 else ("below" if diff_pct < -5 else "competitive"),
            })
    result.sort(key=lambda x: abs(x["diff_pct"]), reverse=True)
    return result


@router.get("/analytics/abandoned-carts")
async def seller_abandoned_carts_report(
    db: AsyncSession = Depends(get_db),
    seller_actor: SellerActorContext = Depends(get_current_seller_from_webapp),
):
    """Report: items that were added to carts but not purchased (potential lost sales)."""
    from shared.database.models import CartItem, ShoppingCart
    seller = seller_actor.seller

    # Get seller's listing IDs
    listing_ids = list(
        (await db.execute(
            select(SellerBank.id).where(SellerBank.seller_id == seller.id, SellerBank.is_active == True)
        )).scalars().all()
    )
    if not listing_ids:
        return {"lost_sales_count": 0, "lost_revenue": 0.0, "items": []}

    # Find cart items for abandoned carts referencing seller's listings
    cart_items_r = await db.execute(
        select(CartItem, ShoppingCart)
        .join(ShoppingCart, ShoppingCart.id == CartItem.cart_id)
        .where(
            CartItem.product_id.in_(listing_ids),
            CartItem.product_type == "bank",
            ShoppingCart.status == "abandoned",
        )
        .order_by(ShoppingCart.updated_at.desc())
        .limit(100)
    )
    cart_rows = list(cart_items_r.all())

    items = []
    total_lost = 0.0
    for ci, cart in cart_rows:
        price = float(ci.price or 0)
        total_lost += price
        items.append({
            "cart_item_id": ci.id,
            "product_name": ci.product_name or f"Product #{ci.product_id}",
            "price": price,
            "abandoned_at": cart.updated_at.isoformat() if cart.updated_at else None,
        })

    return {
        "lost_sales_count": len(items),
        "lost_revenue": round(total_lost, 2),
        "items": items,
    }


@router.post("/listings/bulk-price")
async def seller_bulk_price_update(
    body: SellerBulkPriceRequest,
    db: AsyncSession = Depends(get_db),
    seller_actor: SellerActorContext = Depends(get_current_seller_from_webapp),
):
    seller = seller_actor.seller
    listing_ids = [int(x) for x in body.listing_ids if x]
    if not listing_ids:
        raise HTTPException(status_code=400, detail="No listing_ids provided")
    updated: list[int] = []
    for listing_id in listing_ids[:200]:
        bank = await db.scalar(
            select(SellerBank).where(
                SellerBank.id == listing_id,
                SellerBank.seller_id == seller.id,
                SellerBank.is_active == True,
            )
        )
        if not bank:
            continue
        current_price = Decimal(str(bank.seller_price or 0))
        if body.mode == "set":
            new_price = Decimal(str(body.value))
        elif body.mode == "percent":
            new_price = current_price + (current_price * Decimal(str(body.value)) / Decimal("100"))
        elif body.mode == "delta":
            new_price = current_price + Decimal(str(body.value))
        else:
            raise HTTPException(status_code=400, detail="Unsupported mode")
        if new_price <= 0:
            continue
        await StockService.update_price(db, bank.id, new_price)
        updated.append(bank.id)
    return {"ok": True, "updated_ids": updated, "updated_count": len(updated)}


@router.get("/templates")
async def seller_templates(
    db: AsyncSession = Depends(get_db),
    seller_actor: SellerActorContext = Depends(get_current_seller_from_webapp),
):
    seller = seller_actor.seller
    rows = list(
        (
            await db.execute(
                select(SellerUploadTemplate)
                .where(SellerUploadTemplate.seller_id == seller.id)
                .order_by(SellerUploadTemplate.updated_at.desc(), SellerUploadTemplate.id.desc())
                .limit(100)
            )
        ).scalars().all()
    )
    return [_serialize_template(row) for row in rows]


@router.post("/templates")
async def seller_create_template(
    body: SellerTemplateCreateRequest,
    db: AsyncSession = Depends(get_db),
    seller_actor: SellerActorContext = Depends(get_current_seller_from_webapp),
):
    seller = seller_actor.seller
    template = SellerUploadTemplate(
        seller_id=seller.id,
        item_type=body.item_type,
        title=body.title.strip(),
        payload=body.payload,
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return _serialize_template(template)


@router.delete("/templates/{template_id}")
async def seller_delete_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    seller_actor: SellerActorContext = Depends(get_current_seller_from_webapp),
):
    seller = seller_actor.seller
    template = await db.scalar(
        select(SellerUploadTemplate).where(
            SellerUploadTemplate.id == template_id,
            SellerUploadTemplate.seller_id == seller.id,
        )
    )
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    await db.delete(template)
    await db.commit()
    return {"ok": True}


@router.get("/uploads/batches")
async def seller_upload_batches(
    db: AsyncSession = Depends(get_db),
    seller_actor: SellerActorContext = Depends(get_current_seller_from_webapp),
):
    if not seller_actor.can_upload():
        raise HTTPException(status_code=403, detail="Upload access denied")
    seller = seller_actor.seller
    batches = await SellerUploadBatchService.list_batches(db, seller.id, limit=100)
    return [_serialize_batch(batch) for batch in batches]


@router.get("/uploads/batches/{batch_id}")
async def seller_upload_batch_detail(
    batch_id: int,
    db: AsyncSession = Depends(get_db),
    seller_actor: SellerActorContext = Depends(get_current_seller_from_webapp),
):
    if not seller_actor.can_upload():
        raise HTTPException(status_code=403, detail="Upload access denied")
    seller = seller_actor.seller
    batch = await db.scalar(
        select(SellerUploadBatch).where(
            and_(
                SellerUploadBatch.id == batch_id,
                SellerUploadBatch.seller_id == seller.id,
            )
        )
    )
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    items_payload: list[dict] = []
    if batch.item_type == "bank":
        rows = (await db.execute(select(SellerBank).where(SellerBank.upload_batch_id == batch.id))).scalars().all()
        items_payload = [
            {
                "id": row.id,
                "name": row.bank_name,
                "code": row.bank_code,
                "price": float(row.seller_price),
                "stock_count": int(row.stock_count or 0),
                "moderation_status": row.moderation_status,
                "moderation_comment": row.moderation_comment,
            }
            for row in rows
        ]
    elif batch.item_type == "brute":
        rows = (await db.execute(select(BruteBankItem).where(BruteBankItem.upload_batch_id == batch.id))).scalars().all()
        items_payload = [
            {
                "id": row.id,
                "name": row.bank_name,
                "price": float(row.price),
                "balance_range": row.balance_range,
                "account_type": row.account_type,
                "moderation_status": row.moderation_status,
                "moderation_comment": row.moderation_comment,
            }
            for row in rows
        ]
    return {
        "batch": _serialize_batch(batch),
        "items": items_payload,
    }


@router.post("/uploads/preview")
async def seller_upload_preview(
    body: UploadPreviewRequest,
    seller_actor: SellerActorContext = Depends(get_current_seller_from_webapp),
    _rl: None = Depends(_seller_rate_limit),
):
    if not seller_actor.can_upload():
        raise HTTPException(status_code=403, detail="Upload access denied")
    seller = seller_actor.seller
    try:
        if body.item_type == "bank":
            if not SellerDepositService.has_upload_access(seller, "bank"):
                raise HTTPException(status_code=403, detail="Bank package access required")
            normalized, summary = SellerUploadPipelineService.validate_bank_payload(body.payload, seller.id)
        elif body.item_type == "brute":
            if not SellerDepositService.has_upload_access(seller, "brute"):
                raise HTTPException(status_code=403, detail="Bank package access required")
            normalized, summary = await SellerUploadPipelineService.validate_brute_payload(body.payload)
        elif body.item_type == "nfc":
            if not SellerDepositService.has_upload_access(seller, "bank"):
                raise HTTPException(status_code=403, detail="Bank package access required")
            normalized = {
                "bank_name": str(body.payload.get("bank_name", "")).strip(),
                "country": str(body.payload.get("country", "")).strip().upper(),
                "state": str(body.payload.get("state", "")).strip() or None,
                "zip": str(body.payload.get("zip", "")).strip() or None,
                "nfc_type": str(body.payload.get("nfc_type", "")).strip().lower(),
                "seller_price": str(body.payload.get("seller_price", "")).strip(),
                "data_file_path": str(body.payload.get("data_file_path", "")).strip(),
            }
            if normalized["nfc_type"] not in {"ap", "gp", "other"} or not normalized["bank_name"] or not normalized["country"] or not normalized["seller_price"] or not normalized["data_file_path"]:
                raise ValueError("nfc preview requires bank_name, country, nfc_type(ap/gp/other), seller_price and data_file_path")
            summary = {"item_type": "nfc", "title": normalized["bank_name"], "upload_mode": "single", "total_items": 1}
        elif body.item_type == "otp":
            if not SellerDepositService.has_upload_access(seller, "bank"):
                raise HTTPException(status_code=403, detail="Bank package access required")
            normalized = {
                "bank_name": str(body.payload.get("bank_name", "")).strip(),
                "balance": str(body.payload.get("balance", "")).strip(),
                "has_fullz": bool(body.payload.get("has_fullz")),
                "sms_access_type": str(body.payload.get("sms_access_type", "")).strip(),
                "seller_price": str(body.payload.get("seller_price", "")).strip(),
            }
            if normalized["sms_access_type"] not in {"seller_mediated", "account_access"} or not normalized["bank_name"] or not normalized["balance"] or not normalized["seller_price"]:
                raise ValueError("otp preview requires bank_name, balance, sms_access_type and seller_price")
            summary = {"item_type": "otp", "title": normalized["bank_name"], "upload_mode": "single", "total_items": 1}
        elif body.item_type == "selfreg_cc":
            if not SellerDepositService.has_upload_access(seller, "cc"):
                raise HTTPException(status_code=403, detail="CC package access required")
            normalized = dict(body.payload)
            if not str(normalized.get("bank_name", "")).strip() or not str(normalized.get("seller_price", "")).strip():
                raise ValueError("selfreg_cc preview requires bank_name and seller_price")
            summary = {"item_type": "selfreg_cc", "title": normalized.get("bank_name"), "upload_mode": "single", "total_items": 1}
        else:
            raise HTTPException(status_code=400, detail="Unsupported item_type")
    except ValueError as exc:
        NocoDBService.log_seller_upload(
            seller_id=seller.id,
            category=body.payload.get("category") if isinstance(body.payload, dict) else None,
            status="failed",
            error_reason=str(exc),
            extra={"item_type": body.item_type, "source": "seller_mini_app"},
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "item_type": body.item_type,
        "normalized": normalized,
        "summary": summary,
    }


@router.post("/uploads/parse-file")
async def seller_upload_parse_file(
    item_type: str = Form(...),
    bank_name: str = Form(""),
    bank_code: str = Form(""),
    upload_mode: str = Form("bulk"),
    file: UploadFile = File(...),
    seller_actor: SellerActorContext = Depends(get_current_seller_from_webapp),
):
    if not seller_actor.can_upload():
        raise HTTPException(status_code=403, detail="Upload access denied")
    seller = seller_actor.seller
    if item_type != "brute":
        raise HTTPException(status_code=400, detail="File parsing is currently supported only for brute uploads")
    raw_bytes = await file.read()
    _validate_uploaded_file(
        file_name=file.filename,
        content_type=file.content_type,
        file_bytes=raw_bytes,
        allowed_content_types=ALLOWED_PARSE_FILE_CONTENT_TYPES,
        allowed_extensions=ALLOWED_PARSE_FILE_EXTENSIONS,
        max_size_bytes=MAX_PARSE_FILE_UPLOAD_BYTES,
        detail_prefix="Upload parser rejected file",
    )
    raw_text = raw_bytes.decode("utf-8", errors="ignore")
    try:
        normalized, summary = await SellerUploadPipelineService.validate_brute_payload({
            "bank_name": bank_name,
            "bank_code": bank_code,
            "upload_mode": upload_mode,
            "bulk_text": raw_text,
        })
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "item_type": item_type,
        "normalized": normalized,
        "summary": summary,
        "raw_text": raw_text,
        "seller_id": seller.id,
    }


@router.post("/uploads/submit")
async def seller_upload_submit(
    body: UploadSubmitRequest,
    db: AsyncSession = Depends(get_db),
    seller_actor: SellerActorContext = Depends(get_current_seller_from_webapp),
    _rl: None = Depends(_seller_rate_limit),
):
    if not seller_actor.can_upload():
        raise HTTPException(status_code=403, detail="Upload access denied")
    seller = seller_actor.seller
    try:
        if body.item_type == "bank":
            if not SellerDepositService.has_upload_access(seller, "bank"):
                raise HTTPException(status_code=403, detail="Bank package access required")
            batch, bank, summary = await SellerUploadPipelineService.create_bank_batch(
                db,
                seller_id=seller.id,
                markup_percent=seller.markup_percent,
                payload=body.payload,
                resubmitted_from_batch_id=body.resubmitted_from_batch_id,
            )
            return {
                "ok": True,
                "batch": _serialize_batch(batch),
                "items": [{
                    "id": bank.id,
                    "name": bank.bank_name,
                    "stock_count": int(bank.stock_count or 0),
                    "moderation_status": bank.moderation_status,
                }],
                "summary": summary,
            }
        if body.item_type == "brute":
            if not SellerDepositService.has_upload_access(seller, "brute"):
                raise HTTPException(status_code=403, detail="Bank package access required")
            batch, items, summary = await SellerUploadPipelineService.create_brute_batch(
                db,
                seller_id=seller.id,
                payload=body.payload,
                resubmitted_from_batch_id=body.resubmitted_from_batch_id,
            )
            return {
                "ok": True,
                "batch": _serialize_batch(batch),
                "items": [
                    {
                        "id": item.id,
                        "name": item.bank_name,
                        "price": float(item.price),
                        "moderation_status": item.moderation_status,
                    }
                    for item in items
                ],
                "summary": summary,
            }
        if body.item_type == "nfc":
            if not SellerDepositService.has_upload_access(seller, "bank"):
                raise HTTPException(status_code=403, detail="Bank package access required")
            seller_price = Decimal(str(body.payload["seller_price"]))
            nfc_type = str(body.payload["nfc_type"]).strip().lower()
            batch = await SellerUploadBatchService.create_batch(
                db,
                seller_id=seller.id,
                item_type="nfc",
                upload_mode="single",
                title=f"{body.payload['bank_name']} {nfc_type.upper()}",
                total_items=1,
                draft_payload=body.payload,
                submitted=True,
                resubmitted_from_batch_id=body.resubmitted_from_batch_id,
            )
            nfc_label = "Apple Pay" if nfc_type == "ap" else "Google Pay" if nfc_type == "gp" else "Other"
            sub = "apple_pay" if nfc_type == "ap" else "google_pay" if nfc_type == "gp" else "other"
            item = await SpecialStockService.add_nfc_item(
                db,
                seller_id=seller.id,
                upload_batch_id=batch.id,
                item_name=f"{nfc_label} | {body.payload['bank_name']}",
                nfc_type=nfc_type,
                product_subtype=sub,
                bank_name=body.payload["bank_name"],
                country=body.payload["country"],
                state=body.payload.get("state"),
                zip=body.payload.get("zip"),
                seller_price=seller_price,
                base_price=seller_price,
                buyer_price=seller_price,
                data_file_path=body.payload["data_file_path"],
                moderation_status="pending_moderation",
                is_in_stock=True,
                is_active=True,
            )
            return {"ok": True, "batch": _serialize_batch(batch), "items": [{"id": item.id, "name": item.item_name, "moderation_status": item.moderation_status}], "summary": {"total_items": 1}}
        if body.item_type == "otp":
            if not SellerDepositService.has_upload_access(seller, "bank"):
                raise HTTPException(status_code=403, detail="Bank package access required")
            seller_price = Decimal(str(body.payload["seller_price"]))
            batch = await SellerUploadBatchService.create_batch(
                db,
                seller_id=seller.id,
                item_type="otp",
                upload_mode="single",
                title=f"OTP | {body.payload['bank_name']}",
                total_items=1,
                draft_payload=body.payload,
                submitted=True,
                resubmitted_from_batch_id=body.resubmitted_from_batch_id,
            )
            item = await SpecialStockService.add_otp_item(
                db,
                seller_id=seller.id,
                upload_batch_id=batch.id,
                item_name=f"OTP | {body.payload['bank_name']} | ${Decimal(str(body.payload['balance'])):.0f}",
                bank_name=body.payload["bank_name"],
                balance=Decimal(str(body.payload["balance"])),
                has_fullz=bool(body.payload.get("has_fullz")),
                sms_access_type=body.payload["sms_access_type"],
                seller_price=seller_price,
                base_price=seller_price,
                buyer_price=seller_price,
                moderation_status="pending_moderation",
                is_in_stock=True,
                is_active=True,
            )
            return {"ok": True, "batch": _serialize_batch(batch), "items": [{"id": item.id, "name": item.item_name, "moderation_status": item.moderation_status}], "summary": {"total_items": 1}}
        if body.item_type == "selfreg_cc":
            if not SellerDepositService.has_upload_access(seller, "cc"):
                raise HTTPException(status_code=403, detail="CC package access required")
            seller_price = Decimal(str(body.payload["seller_price"]))
            batch = await SellerUploadBatchService.create_batch(
                db,
                seller_id=seller.id,
                item_type="selfreg_cc",
                upload_mode="single",
                title=f"{body.payload['bank_name']} selfreg cc",
                total_items=1,
                draft_payload=body.payload,
                submitted=True,
                resubmitted_from_batch_id=body.resubmitted_from_batch_id,
            )
            item = await SpecialStockService.add_selfreg_cc_item(
                db,
                seller_id=seller.id,
                upload_batch_id=batch.id,
                item_name=f"{body.payload['bank_name']} — {body.payload.get('card_name') or 'Selfreg CC'}",
                bank_name=body.payload["bank_name"],
                card_name=body.payload.get("card_name"),
                credit_limit=Decimal(str(body.payload["credit_limit"])) if body.payload.get("credit_limit") else None,
                vcc_limit=Decimal(str(body.payload["vcc_limit"])) if body.payload.get("vcc_limit") else None,
                state=body.payload.get("state"),
                zip=body.payload.get("zip"),
                has_email=bool(body.payload.get("has_email")),
                has_phone=bool(body.payload.get("has_phone")),
                phone_days_remaining=body.payload.get("phone_days_remaining"),
                phone_renewable=body.payload.get("phone_renewable"),
                phone_change_allowed=body.payload.get("phone_change_allowed"),
                online_access=bool(body.payload.get("online_access")),
                seller_price=seller_price,
                base_price=seller_price,
                buyer_price=seller_price,
                moderation_status="pending_moderation",
                is_in_stock=True,
                is_active=True,
            )
            return {"ok": True, "batch": _serialize_batch(batch), "items": [{"id": item.id, "name": item.item_name, "moderation_status": item.moderation_status}], "summary": {"total_items": 1}}
        
        # CC (Credit Cards) Upload
        if body.item_type == "cc":
            if not SellerDepositService.has_upload_access(seller, "cc"):
                raise HTTPException(status_code=403, detail="CC package access required")
            from seller_bot.services.cc_stock_service import CCStockService
            seller_price = Decimal(str(body.payload["seller_price"]))
            # Parse card number to extract BIN and other data
            number = (body.payload.get("number") or "").replace(" ", "")
            card_bin = number[:6] if len(number) >= 6 else None
            parsed_data = {
                "number": body.payload.get("number"),
                "exp_mm": body.payload.get("exp", "")[:2] if body.payload.get("exp") else None,
                "exp_yyyy": body.payload.get("exp", "")[-2:] if body.payload.get("exp") else None,
                "cvv": body.payload.get("cvv"),
                "fname": body.payload.get("fname"),
                "lname": body.payload.get("lname"),
                "address": body.payload.get("address"),
                "city": body.payload.get("city"),
                "state": body.payload.get("state"),
                "zip": body.payload.get("zip"),
                "country": body.payload.get("country"),
                "bank_name": body.payload.get("bank_name"),
                "card_brand": body.payload.get("card_brand"),
                "card_level": body.payload.get("card_level"),
                "card_type": body.payload.get("card_type"),
                "is_non_vbv": body.payload.get("is_non_vbv", False),
            }
            batch = await SellerUploadBatchService.create_batch(
                db,
                seller_id=seller.id,
                item_type="cc",
                upload_mode="single",
                title=f"CC {body.payload.get('card_brand', '')} {number[-4:]}",
                total_items=1,
                draft_payload=body.payload,
                submitted=True,
                resubmitted_from_batch_id=body.resubmitted_from_batch_id,
            )
            item = await CCStockService.add_cc_item(
                session=db,
                seller_id=seller.id,
                item_name=f"{body.payload.get('card_brand', 'CC')} {number[-4:]}",
                category_code=body.payload.get("category_code", "usa"),
                cc_code=number,
                seller_price=seller_price,
                product_subtype="cc",
                extra_data=body.payload.get("extra_data", {}),
                parsed_data=parsed_data,
                upload_batch_id=batch.id,
            )
            return {"ok": True, "batch": _serialize_batch(batch), "items": [{"id": item.id, "name": item.item_name, "moderation_status": item.moderation_status}], "summary": {"total_items": 1}}
        
        # Enroll Upload
        if body.item_type == "enroll":
            if not SellerDepositService.has_upload_access(seller, "bank"):
                raise HTTPException(status_code=403, detail="Bank package access required")
            seller_price = Decimal(str(body.payload["seller_price"]))
            batch = await SellerUploadBatchService.create_batch(
                db,
                seller_id=seller.id,
                item_type="enroll",
                upload_mode="single",
                title=f"Enroll {body.payload.get('portal', '')}",
                total_items=1,
                draft_payload=body.payload,
                submitted=True,
                resubmitted_from_batch_id=body.resubmitted_from_batch_id,
            )
            item = await SpecialStockService.add_enroll_item(
                db,
                seller_id=seller.id,
                upload_batch_id=batch.id,
                portal=body.payload.get("portal"),
                card_type=body.payload.get("card_type"),
                balance=Decimal(str(body.payload["balance"])) if body.payload.get("balance") else None,
                state=body.payload.get("state"),
                zip=body.payload.get("zip"),
                has_ssn=bool(body.payload.get("has_ssn")),
                has_dob=bool(body.payload.get("has_dob")),
                has_name=bool(body.payload.get("has_name")),
                has_address=bool(body.payload.get("has_address")),
                has_email=bool(body.payload.get("has_email")),
                has_security_qa=bool(body.payload.get("has_security_qa")),
                has_docs=bool(body.payload.get("has_docs")),
                doc_type=body.payload.get("doc_type"),
                phone_area_code=body.payload.get("phone_area_code"),
                seller_price=seller_price,
                base_price=seller_price,
                buyer_price=seller_price,
                moderation_status="pending_moderation",
                is_in_stock=True,
                is_active=True,
            )
            return {"ok": True, "batch": _serialize_batch(batch), "items": [{"id": item.id, "name": f"Enroll {item.portal or ''}", "moderation_status": item.moderation_status}], "summary": {"total_items": 1}}
        
        # Checks Upload
        if body.item_type == "checks":
            if not SellerDepositService.has_upload_access(seller, "bank"):
                raise HTTPException(status_code=403, detail="Bank package access required")
            seller_price = Decimal(str(body.payload["seller_price"]))
            batch = await SellerUploadBatchService.create_batch(
                db,
                seller_id=seller.id,
                item_type="checks",
                upload_mode="single",
                title=f"Check {body.payload.get('check_type', 'personal')}",
                total_items=1,
                draft_payload=body.payload,
                submitted=True,
                resubmitted_from_batch_id=body.resubmitted_from_batch_id,
            )
            item = await SpecialStockService.add_check_item(
                db,
                seller_id=seller.id,
                upload_batch_id=batch.id,
                check_type=body.payload.get("check_type", "personal"),
                amount=Decimal(str(body.payload["amount"])) if body.payload.get("amount") else None,
                check_date=body.payload.get("check_date"),
                bank_name=body.payload.get("bank_name"),
                state=body.payload.get("state"),
                zip=body.payload.get("zip"),
                scan_file_path=body.payload.get("scan_file_path"),
                template_file_path=body.payload.get("template_file_path"),
                seller_price=seller_price,
                base_price=seller_price,
                buyer_price=seller_price,
                moderation_status="pending_moderation",
                is_in_stock=True,
                is_active=True,
            )
            return {"ok": True, "batch": _serialize_batch(batch), "items": [{"id": item.id, "name": f"Check {item.check_type or ''} ${float(item.amount or 0):.2f}", "moderation_status": item.moderation_status}], "summary": {"total_items": 1}}
        
        raise HTTPException(status_code=400, detail="Unsupported item_type")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


class CategoryUnlockRequest(BaseModel):
    category_type: str  # e.g. "nfc_bank", "enroll", "checks_bank"
    name: str  # Bank or portal name requested


@router.post("/uploads/request-category", status_code=201)
async def seller_request_category_unlock(
    body: CategoryUnlockRequest,
    db: AsyncSession = Depends(get_db),
    seller_actor: SellerActorContext = Depends(get_current_seller_from_webapp),
):
    """Seller requests access to a restricted upload category (NFC bank, enrollment portal, checks bank).
    The request is logged and support staff will review it within 1-6 hours.
    """
    from shared.database.models import AuditLog
    seller = seller_actor.seller

    ALLOWED_CATEGORY_TYPES = {"nfc_bank", "enroll", "checks_bank"}
    if body.category_type not in ALLOWED_CATEGORY_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid category_type. Allowed: {sorted(ALLOWED_CATEGORY_TYPES)}")

    if not body.name or len(body.name.strip()) < 2:
        raise HTTPException(status_code=400, detail="Name must be at least 2 characters")

    # Log the request in the universal audit log so support can review
    audit = AuditLog(
        source="seller_mini_app",
        event_type="category_unlock_requested",
        actor_type="seller",
        actor_id=seller.id,
        target_type="category",
        status="pending",
        payload={"category_type": body.category_type, "name": body.name.strip()},
    )
    db.add(audit)
    await db.commit()

    return {"ok": True, "message": "Request submitted — support will review within 1–6 hours"}


@router.get("/analytics/export.csv")
async def seller_analytics_export_csv(
    date_from: Optional[str] = Query(default=None),
    date_to: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    seller_actor: SellerActorContext = Depends(get_current_seller_from_webapp),
):
    """Export analytics data as CSV for a given date range."""
    seller = seller_actor.seller

    where_clauses = [SellerOrder.seller_id == seller.id]
    if date_from:
        try:
            dt_from = datetime.strptime(date_from, "%Y-%m-%d")
            where_clauses.append(SellerOrder.created_at >= dt_from)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date_from format. Use YYYY-MM-DD")
    if date_to:
        try:
            dt_to = datetime.strptime(date_to, "%Y-%m-%d")
            # Include the entire end day
            dt_to = dt_to.replace(hour=23, minute=59, second=59)
            where_clauses.append(SellerOrder.created_at <= dt_to)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date_to format. Use YYYY-MM-DD")

    result = await db.execute(
        select(SellerOrder)
        .where(*where_clauses)
        .order_by(SellerOrder.created_at.desc())
        .limit(5000)
    )
    orders = list(result.scalars().all())

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["order_id", "status", "product_name", "buyer_amount", "seller_amount", "platform_fee", "created_at", "completed_at"])
    for order in orders:
        buyer_amount = Decimal(str(order.price_for_buyer or 0))
        seller_amount = Decimal(str(order.price_for_seller or 0))
        writer.writerow([
            order.id,
            order.status,
            order.product_name or "",
            f"{buyer_amount:.2f}",
            f"{seller_amount:.2f}",
            f"{(buyer_amount - seller_amount):.2f}",
            order.created_at.isoformat() if order.created_at else "",
            order.completed_at.isoformat() if order.completed_at else "",
        ])

    filename = f"analytics_{date_from or 'all'}_{date_to or 'all'}.csv"
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
