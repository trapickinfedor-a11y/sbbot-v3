from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import (
    BruteBankItem,
    SellerBank,
    SellerCCItem,
    SellerCheckItem,
    SellerNFCItem,
    SellerOTPItem,
    SellerSelfregCCItem,
    SellerUploadBatch,
)

router = Router(name="seller_uploads")


def _uploads_keyboard(batches: list[SellerUploadBatch]) -> InlineKeyboardMarkup:
    rows = []
    for batch in batches:
        rows.append([
            InlineKeyboardButton(
                text=f"#{batch.id} {batch.item_type.upper()} | {batch.moderation_status} | {batch.total_items}",
                callback_data=f"seller_upload_batch:{batch.id}",
            )
        ])
    rows.append([InlineKeyboardButton(text="⬅️ Back", callback_data="seller_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data == "seller_uploads")
async def seller_uploads_list(callback: CallbackQuery, session: AsyncSession, seller, **kwargs):
    seller_actor = kwargs.get("seller_actor")
    if not seller or not seller_actor or not seller_actor.can_upload():
        await callback.answer("❌ Not authorized", show_alert=True)
        return
    result = await session.execute(
        select(SellerUploadBatch)
        .where(SellerUploadBatch.seller_id == seller.id)
        .order_by(SellerUploadBatch.created_at.desc(), SellerUploadBatch.id.desc())
        .limit(20)
    )
    batches = list(result.scalars().all())
    if not batches:
        await callback.message.edit_text(
            "🗂 <b>My Uploads</b>\n\nNo upload batches yet.",
            reply_markup=_uploads_keyboard([]),
        )
        await callback.answer()
        return

    lines = ["🗂 <b>My Uploads</b>\n"]
    for batch in batches:
        lines.append(
            f"• #{batch.id} | {batch.item_type.upper()} | {batch.moderation_status} | "
            f"items {batch.total_items} | approved {batch.approved_items or 0} | "
            f"pending {batch.pending_items or 0}"
        )
    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=_uploads_keyboard(batches),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("seller_upload_batch:"))
async def seller_upload_batch_detail(callback: CallbackQuery, session: AsyncSession, seller, **kwargs):
    seller_actor = kwargs.get("seller_actor")
    if not seller or not seller_actor or not seller_actor.can_upload():
        await callback.answer("❌ Not authorized", show_alert=True)
        return
    batch_id = int(callback.data.split(":")[1])
    batch = await session.scalar(
        select(SellerUploadBatch).where(
            and_(
                SellerUploadBatch.id == batch_id,
                SellerUploadBatch.seller_id == seller.id,
            )
        )
    )
    if not batch:
        await callback.answer("Batch not found", show_alert=True)
        return

    if batch.item_type == "bank":
        items = (await session.execute(select(SellerBank).where(SellerBank.upload_batch_id == batch.id))).scalars().all()
        item_lines = [
            f"• #{item.id} {item.bank_name} | qty {item.stock_count} | {item.moderation_status}"
            + (f" | {item.moderation_comment}" if item.moderation_comment else "")
            for item in items
        ]
    elif batch.item_type == "cc":
        items = (await session.execute(select(SellerCCItem).where(SellerCCItem.upload_batch_id == batch.id))).scalars().all()
        item_lines = [
            f"• #{item.id} {item.item_name} | ${item.seller_price:.2f} | {item.moderation_status}"
            + (f" | {item.moderation_comment}" if item.moderation_comment else "")
            for item in items[:20]
        ]
    elif batch.item_type == "nfc":
        items = (await session.execute(select(SellerNFCItem).where(SellerNFCItem.upload_batch_id == batch.id))).scalars().all()
        item_lines = [
            f"• #{item.id} {item.item_name} | ${item.seller_price:.2f} | {item.moderation_status}"
            + (f" | {item.moderation_comment}" if item.moderation_comment else "")
            for item in items[:20]
        ]
    elif batch.item_type == "otp":
        items = (await session.execute(select(SellerOTPItem).where(SellerOTPItem.upload_batch_id == batch.id))).scalars().all()
        item_lines = [
            f"• #{item.id} {item.item_name} | ${item.seller_price:.2f} | {item.moderation_status}"
            + (f" | {item.moderation_comment}" if item.moderation_comment else "")
            for item in items[:20]
        ]
    elif batch.item_type == "selfreg_cc":
        items = (await session.execute(select(SellerSelfregCCItem).where(SellerSelfregCCItem.upload_batch_id == batch.id))).scalars().all()
        item_lines = [
            f"• #{item.id} {item.item_name} | ${item.seller_price:.2f} | {item.moderation_status}"
            + (f" | {item.moderation_comment}" if item.moderation_comment else "")
            for item in items[:20]
        ]
    elif batch.item_type == "check":
        items = (await session.execute(select(SellerCheckItem).where(SellerCheckItem.upload_batch_id == batch.id))).scalars().all()
        item_lines = [
            f"• #{item.id} {item.item_name} | ${item.seller_price:.2f} | {item.moderation_status}"
            + (f" | {item.moderation_comment}" if item.moderation_comment else "")
            for item in items[:20]
        ]
    else:
        items = (await session.execute(select(BruteBankItem).where(BruteBankItem.upload_batch_id == batch.id))).scalars().all()
        item_lines = [
            f"• #{item.id} {item.bank_name} | ${item.price:.2f} | {item.moderation_status}"
            + (f" | {item.moderation_comment}" if item.moderation_comment else "")
            for item in items[:20]
        ]

    text = (
        f"🗂 <b>Batch #{batch.id}</b>\n\n"
        f"Type: {batch.item_type.upper()}\n"
        f"Mode: {batch.upload_mode}\n"
        f"Status: {batch.moderation_status}\n"
        f"Items: {batch.total_items}\n"
        f"Approved: {batch.approved_items or 0}\n"
        f"Pending: {batch.pending_items or 0}\n"
        f"Rejected: {batch.rejected_items or 0}\n"
        f"Changes requested: {batch.changes_requested_items or 0}\n"
        f"Comment: {batch.moderation_comment or '-'}\n\n"
        f"{chr(10).join(item_lines) if item_lines else 'No items attached.'}"
    )
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Back", callback_data="seller_uploads")],
        ]),
    )
    await callback.answer()
