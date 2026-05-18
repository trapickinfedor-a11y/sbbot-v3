from __future__ import annotations

"""
Moderation of SellerBank and SellerCCItem - approve/reject/request changes
"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, or_, select
from datetime import datetime, timezone

from shared.database.models import (
    Seller,
    SellerBank,
    SellerBankItem,
    SellerCCItem,
    SellerEnrollItem,
    SellerCheckItem,
    SellerLogsItem,
    SellerNFCItem,
    SellerOTPItem,
    SellerSelfregCCItem,
)
from shared.services.admin_audit_service import log_admin_action
from shared.services.moderation_pricing_service import (
    apply_bank_markup,
    apply_cc_markup,
    apply_enroll_markup,
    apply_check_markup,
    apply_logs_markup,
    apply_nfc_markup,
    apply_otp_markup,
    apply_selfreg_cc_markup,
)
from shared.services.seller_deposit_service import SellerDepositService
from shared.services.seller_upload_batch_service import SellerUploadBatchService
from support_bot.services.access_service import SupportBotActor
from shared.utils.seller_product_meta import bank_item_badge, cc_item_badge
from web_panel.auth import ROLE_ADMIN, ROLE_SUPER_ADMIN

logger = logging.getLogger(__name__)
router = Router(name="seller_moderation")


class RequestChangesStates(StatesGroup):
    waiting_comment = State()


class ModCCSearchStates(StatesGroup):
    waiting_query = State()


def _actor(kwargs) -> SupportBotActor | None:
    return kwargs.get("support_bot_actor")


def _can_moderate(kwargs) -> bool:
    actor = _actor(kwargs)
    return bool(actor and actor.can_moderate_sellers)


def _can_ban_seller(kwargs) -> bool:
    actor = _actor(kwargs)
    if not actor:
        return False
    if actor.source == "system_admin":
        return True
    return actor.role in {ROLE_ADMIN, ROLE_SUPER_ADMIN}


@router.message(Command("seller_ban"))
async def cmd_seller_ban(message: Message, session: AsyncSession, **kwargs):
    actor = _actor(kwargs)
    if not _can_ban_seller(kwargs):
        await message.answer("❌ Admin only")
        return

    parts = (message.text or "").split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("Usage: /seller_ban <seller_id> <reason>")
        return

    try:
        seller_id = int(parts[1])
    except ValueError:
        await message.answer("Seller ID must be a number.")
        return

    reason = parts[2].strip()
    if not reason:
        await message.answer("Reason is required.")
        return

    seller = await session.scalar(select(Seller).where(Seller.id == seller_id))
    if not seller:
        await message.answer("Seller not found.")
        return

    affected = await SellerDepositService.ban_seller(
        session,
        seller,
        actor_id=actor.admin_id or message.from_user.id,
        reason=reason,
        source="support_bot",
        ban_for_leak=False,
    )
    await _log_seller_ban_audit(
        session,
        seller=seller,
        actor=actor,
        actor_telegram_id=message.from_user.id,
        reason=reason,
        affected=affected,
    )
    await session.commit()
    await message.answer(
        "🚫 <b>Seller banned.</b>\n\n"
        f"Seller: {seller.display_name or seller.username or seller.id}\n"
        f"Reason: {reason}\n"
        f"Banks removed: {affected['banks_disabled']}\n"
        f"CC removed: {affected['cc_disabled']}\n"
        f"NFC removed: {affected['nfc_disabled']}\n"
        f"OTP removed: {affected['otp_disabled']}\n"
        f"Selfreg CC removed: {affected['selfreg_cc_disabled']}\n"
        f"Checks removed: {affected['checks_disabled']}\n"
        f"Brute removed: {affected['brute_disabled']}"
    )


@router.message(Command("seller_leak_ban"))
async def cmd_seller_leak_ban(message: Message, session: AsyncSession, **kwargs):
    actor = _actor(kwargs)
    if not _can_ban_seller(kwargs):
        await message.answer("❌ Admin only")
        return

    parts = (message.text or "").split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("Usage: /seller_leak_ban <seller_id> <reason>")
        return

    try:
        seller_id = int(parts[1])
    except ValueError:
        await message.answer("Seller ID must be a number.")
        return

    reason = parts[2].strip()
    if not reason:
        await message.answer("Reason is required.")
        return

    seller = await session.scalar(select(Seller).where(Seller.id == seller_id))
    if not seller:
        await message.answer("Seller not found.")
        return

    affected = await SellerDepositService.ban_seller(
        session,
        seller,
        actor_id=actor.admin_id or message.from_user.id,
        reason=reason,
        source="support_bot_leak_ban",
        ban_for_leak=True,
    )
    await _log_seller_ban_audit(
        session,
        seller=seller,
        actor=actor,
        actor_telegram_id=message.from_user.id,
        reason=reason,
        affected=affected,
        action="seller_leak_ban",
        source="support_bot_leak_ban",
    )
    await session.commit()
    await message.answer(
        "🚫 <b>Seller banned for leak.</b>\n\n"
        f"Seller: {seller.display_name or seller.username or seller.id}\n"
        f"Reason: {reason}\n"
        f"Banks removed: {affected['banks_disabled']}\n"
        f"CC removed: {affected['cc_disabled']}\n"
        f"NFC removed: {affected['nfc_disabled']}\n"
        f"OTP removed: {affected['otp_disabled']}\n"
        f"Selfreg CC removed: {affected['selfreg_cc_disabled']}\n"
        f"Checks removed: {affected['checks_disabled']}\n"
        f"Brute removed: {affected['brute_disabled']}\n"
        "Deposit: withheld"
    )


async def _log_moderation_audit(
    session: AsyncSession,
    *,
    action: str,
    entity_type: str,
    entity_id: int,
    seller_id: int,
    source: str,
    actor: SupportBotActor | None = None,
    actor_telegram_id: int,
    payload: dict,
):
    details = {
        "seller_id": seller_id,
        "source": source,
        "actor_telegram_id": actor_telegram_id,
        **payload,
    }
    await log_admin_action(
        session,
        admin_id=actor.admin_id if actor else None,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
        actor_label=actor.actor_label() if actor else f"{source}:{actor_telegram_id}",
    )


async def _log_seller_ban_audit(
    session: AsyncSession,
    *,
    seller: Seller,
    actor: SupportBotActor | None = None,
    actor_telegram_id: int,
    reason: str,
    affected: dict,
    action: str = "seller_ban",
    source: str = "support_bot",
):
    await log_admin_action(
        session,
        admin_id=actor.admin_id if actor else None,
        action=action,
        entity_type="seller",
        entity_id=seller.id,
        details={
            "seller_id": seller.id,
            "seller_name": seller.display_name or seller.username or seller.id,
            "reason": reason,
            "source": source,
            "actor_telegram_id": actor_telegram_id,
            "affected": affected,
            "deposit_withheld": True,
        },
        actor_label=actor.actor_label() if actor else f"support_bot:{actor_telegram_id}",
    )


def _special_item_payload(item, *, comment: str | None = None) -> dict:
    payload = {
        "item_name": getattr(item, "item_name", getattr(item, "bank_name", getattr(item, "bank", getattr(item, "portal", str(item.id))))),
        "upload_batch_id": getattr(item, "upload_batch_id", None),
        "moderation_status": getattr(item, "moderation_status", None),
    }
    if getattr(item, "bank_name", None):
        payload["bank_name"] = item.bank_name
    if getattr(item, "bank", None):
        payload["bank"] = item.bank
    if getattr(item, "portal", None):
        payload["portal"] = item.portal
    if getattr(item, "cc_code", None):
        payload["cc_code"] = item.cc_code
    if getattr(item, "nfc_type", None):
        payload["nfc_type"] = item.nfc_type
    if getattr(item, "check_type", None):
        payload["check_type"] = item.check_type
    if getattr(item, "price", None) is not None:
        payload["price"] = float(item.price or 0)
    if getattr(item, "seller_price", None) is not None:
        payload["seller_price"] = float(item.seller_price or 0)
    if getattr(item, "base_price", None) is not None:
        payload["base_price"] = float(item.base_price or 0)
    if getattr(item, "buyer_price", None) is not None:
        payload["buyer_price"] = float(item.buyer_price or 0)
    if getattr(item, "final_price", None) is not None:
        payload["final_price"] = float(item.final_price or 0)
    if comment is not None:
        payload["comment"] = comment
    return payload


def _selected_rule(callback_data: str) -> str | None:
    parts = callback_data.split(":")
    return parts[2] if len(parts) > 2 and parts[2] else None


def _bank_rule_rows(bank_id: int) -> list[list[InlineKeyboardButton]]:
    return [
        [
            InlineKeyboardButton(text="Logs +15%", callback_data=f"mod_bank_approve:{bank_id}:logs"),
            InlineKeyboardButton(text="Checks +15%", callback_data=f"mod_bank_approve:{bank_id}:checks"),
        ],
        [
            InlineKeyboardButton(text="Enroll +$20", callback_data=f"mod_bank_approve:{bank_id}:enroll"),
            InlineKeyboardButton(text="Selfreg BA +20%", callback_data=f"mod_bank_approve:{bank_id}:selfreg_ba"),
        ],
    ]


def _cc_rule_rows(item_id: int) -> list[list[InlineKeyboardButton]]:
    return [
        [
            InlineKeyboardButton(text="ZIP/Fullz +$20", callback_data=f"mod_cc_approve:{item_id}:cc_zip_fullz"),
            InlineKeyboardButton(text="NON-VBV +$25", callback_data=f"mod_cc_approve:{item_id}:non_vbv_cc"),
        ],
        [
            InlineKeyboardButton(text="OTP +25%", callback_data=f"mod_cc_approve:{item_id}:otp"),
            InlineKeyboardButton(text="Selfregs +15%", callback_data=f"mod_cc_approve:{item_id}:selfregs_cc"),
        ],
        [
            InlineKeyboardButton(text="Checks +15%", callback_data=f"mod_cc_approve:{item_id}:checks"),
            InlineKeyboardButton(text="Base price", callback_data=f"mod_cc_approve:{item_id}"),
        ],
    ]


@router.message(Command("seller_moderation"))
async def cmd_seller_moderation(message: Message, session: AsyncSession, **kwargs):
    """List pending SellerBank and SellerCCItem for moderation"""
    if not _can_moderate(kwargs):
        await message.answer("❌ Admin only")
        return
    
    # Pending banks
    bank_result = await session.execute(
        select(SellerBank, Seller).join(Seller, SellerBank.seller_id == Seller.id).where(
            SellerBank.moderation_status == "pending_moderation",
            SellerBank.is_active == True
        ).order_by(SellerBank.created_at.desc()).limit(20)
    )
    pending_banks = list(bank_result.all())
    
    # Pending CC items
    cc_result = await session.execute(
        select(SellerCCItem, Seller).join(Seller, SellerCCItem.seller_id == Seller.id).where(
            SellerCCItem.moderation_status == "pending_moderation",
            SellerCCItem.is_active == True
        ).order_by(SellerCCItem.created_at.desc()).limit(20)
    )
    pending_cc = list(cc_result.all())
    pending_nfc = list((await session.execute(
        select(SellerNFCItem, Seller).join(Seller, SellerNFCItem.seller_id == Seller.id).where(
            SellerNFCItem.moderation_status == "pending_moderation",
            SellerNFCItem.is_active == True
        ).order_by(SellerNFCItem.created_at.desc()).limit(20)
    )).all())
    pending_otp = list((await session.execute(
        select(SellerOTPItem, Seller).join(Seller, SellerOTPItem.seller_id == Seller.id).where(
            SellerOTPItem.moderation_status == "pending_moderation",
            SellerOTPItem.is_active == True
        ).order_by(SellerOTPItem.created_at.desc()).limit(20)
    )).all())
    pending_selfreg_cc = list((await session.execute(
        select(SellerSelfregCCItem, Seller).join(Seller, SellerSelfregCCItem.seller_id == Seller.id).where(
            SellerSelfregCCItem.moderation_status == "pending_moderation",
            SellerSelfregCCItem.is_active == True
        ).order_by(SellerSelfregCCItem.created_at.desc()).limit(20)
    )).all())
    pending_enroll = list((await session.execute(
        select(SellerEnrollItem, Seller).join(Seller, SellerEnrollItem.seller_id == Seller.id).where(
            SellerEnrollItem.moderation_status == "pending_moderation",
            SellerEnrollItem.is_active == True
        ).order_by(SellerEnrollItem.created_at.desc()).limit(20)
    )).all())
    # Note: selfreg_ba merged with bank items
    pending_logs = list((await session.execute(
        select(SellerLogsItem, Seller).join(Seller, SellerLogsItem.seller_id == Seller.id).where(
            SellerLogsItem.moderation_status == "pending_moderation",
            SellerLogsItem.is_active == True
        ).order_by(SellerLogsItem.created_at.desc()).limit(20)
    )).all())
    pending_checks = list((await session.execute(
        select(SellerCheckItem, Seller).join(Seller, SellerCheckItem.seller_id == Seller.id).where(
            SellerCheckItem.moderation_status == "pending_moderation",
            SellerCheckItem.is_active == True
        ).order_by(SellerCheckItem.created_at.desc()).limit(20)
    )).all())

    text = "📋 <b>Seller Product Moderation</b>\n\n"
    text += f"🏦 <b>Banks pending:</b> {len(pending_banks)}\n"
    text += f"💳 <b>CC items pending:</b> {len(pending_cc)}\n\n"
    text += f"📱 <b>NFC pending:</b> {len(pending_nfc)}\n"
    text += f"📲 <b>OTP pending:</b> {len(pending_otp)}\n"
    text += f"🪪 <b>Enroll pending:</b> {len(pending_enroll)}\n"
    text += f"📋 <b>Logs pending:</b> {len(pending_logs)}\n"
    text += f"💳 <b>Selfreg CC pending:</b> {len(pending_selfreg_cc)}\n"
    text += f"🖊 <b>Checks pending:</b> {len(pending_checks)}\n\n"
    text += "Select to moderate:"

    buttons = []
    if pending_banks:
        buttons.append([InlineKeyboardButton(text=f"🏦 Banks ({len(pending_banks)})", callback_data="mod_banks_list")])
    if pending_cc:
        buttons.append([InlineKeyboardButton(text=f"💳 CC Items ({len(pending_cc)})", callback_data="mod_cc_list")])
    if pending_nfc:
        buttons.append([InlineKeyboardButton(text=f"📱 NFC ({len(pending_nfc)})", callback_data="mod_nfc_list")])
    if pending_otp:
        buttons.append([InlineKeyboardButton(text=f"📲 OTP ({len(pending_otp)})", callback_data="mod_otp_list")])
    if pending_enroll:
        buttons.append([InlineKeyboardButton(text=f"🪪 Enroll ({len(pending_enroll)})", callback_data="mod_enroll_list")])
    # Note: selfreg_ba merged with bank items
    if pending_logs:
        buttons.append([InlineKeyboardButton(text=f"📋 Logs ({len(pending_logs)})", callback_data="mod_logs_list")])
    if pending_selfreg_cc:
        buttons.append([InlineKeyboardButton(text=f"💳 Selfreg CC ({len(pending_selfreg_cc)})", callback_data="mod_selfreg_cc_list")])
    if pending_checks:
        buttons.append([InlineKeyboardButton(text=f"🖊 Checks ({len(pending_checks)})", callback_data="mod_checks_list")])
    buttons.append([InlineKeyboardButton(text="🔄 Refresh", callback_data="mod_refresh")])
    
    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data == "mod_refresh")
async def mod_refresh(callback: CallbackQuery, session: AsyncSession, **kwargs):
    if not _can_moderate(kwargs):
        await callback.answer("❌ Admin only", show_alert=True)
        return
    await callback.answer()
    await cmd_seller_moderation(callback.message, session, **kwargs)


@router.callback_query(F.data == "mod_banks_list")
async def mod_banks_list(callback: CallbackQuery, session: AsyncSession, **kwargs):
    if not _can_moderate(kwargs):
        await callback.answer("❌ Admin only", show_alert=True)
        return
    
    result = await session.execute(
        select(SellerBank, Seller).join(Seller, SellerBank.seller_id == Seller.id).where(
            SellerBank.moderation_status == "pending_moderation",
            SellerBank.is_active == True
        ).order_by(SellerBank.created_at.desc()).limit(15)
    )
    rows = list(result.all())
    
    if not rows:
        await callback.message.edit_text("No banks pending moderation.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Back", callback_data="mod_back")]
        ]))
        await callback.answer()
        return
    
    text = "🏦 <b>Banks pending moderation</b>\n\n"
    buttons = []
    for bank, seller in rows:
        batch_text = f" | batch #{bank.upload_batch_id}" if getattr(bank, "upload_batch_id", None) else ""
        text += f"• #{bank.id} {bank.bank_name} | ${bank.seller_price} | {seller.display_name or seller.username or '?'}{batch_text}\n"
        buttons.append([
            InlineKeyboardButton(text=f"#{bank.id} {bank.bank_name}", callback_data=f"mod_bank:{bank.id}")
        ])
    buttons.append([InlineKeyboardButton(text="⬅️ Back", callback_data="mod_back")])
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()


@router.callback_query(F.data.startswith("mod_bank:"))
async def mod_bank_detail(callback: CallbackQuery, session: AsyncSession, **kwargs):
    if not _can_moderate(kwargs):
        await callback.answer("❌ Admin only", show_alert=True)
        return
    
    bank_id = int(callback.data.split(":")[1])
    result = await session.execute(
        select(SellerBank, Seller).join(Seller, SellerBank.seller_id == Seller.id).where(SellerBank.id == bank_id)
    )
    row = result.one_or_none()
    if not row:
        await callback.answer("Not found", show_alert=True)
        return
    
    bank, seller = row
    
    text = (
        f"🏦 <b>Bank #{bank.id}</b>\n\n"
        f"Name: {bank.bank_name}\n"
        f"Code: {bank.bank_code}\n"
        f"Product: {bank_item_badge(getattr(bank, 'product_type', 'bank'), getattr(bank, 'product_subtype', 'log'))}\n"
        f"Category: {bank.category}\n"
        f"Batch: #{bank.upload_batch_id or '-'}\n"
        f"Seller price: ${bank.seller_price}\n"
        f"Base price: ${getattr(bank, 'base_price', bank.seller_price)}\n"
        f"Final price: ${getattr(bank, 'final_price', bank.buyer_price)}\n"
        f"Markup: {getattr(bank, 'markup_code', '-')}\n"
        f"Seller: {seller.display_name or seller.username} (@{seller.username or 'N/A'})\n"
        f"Description: {bank.description or '-'}\n"
        f"Instruction: {getattr(bank, 'instruction', None) or '-'}\n"
        f"Status: {bank.moderation_status}\n"
        f"Created: {bank.created_at.strftime('%Y-%m-%d %H:%M')}\n"
    )
    
    if bank.moderation_status == "pending_moderation":
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Approve base price", callback_data=f"mod_bank_approve:{bank.id}")],
            *_bank_rule_rows(bank.id),
            [
                InlineKeyboardButton(text="❌ Reject", callback_data=f"mod_bank_reject:{bank.id}")
            ],
            [InlineKeyboardButton(text="📝 Request changes", callback_data=f"mod_bank_changes:{bank.id}")],
            [InlineKeyboardButton(text="⬅️ Back", callback_data="mod_banks_list")]
        ])
    else:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Back", callback_data="mod_banks_list")]
        ])
    
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("mod_bank_approve:"))
async def mod_bank_approve(callback: CallbackQuery, session: AsyncSession, **kwargs):
    actor = _actor(kwargs)
    if not _can_moderate(kwargs):
        await callback.answer("❌ Admin only", show_alert=True)
        return
    
    bank_id = int(callback.data.split(":")[1])
    rule_code = _selected_rule(callback.data)
    result = await session.execute(select(SellerBank).where(SellerBank.id == bank_id))
    bank = result.scalar_one_or_none()
    if not bank:
        await callback.answer("Not found", show_alert=True)
        return
    
    rule = apply_bank_markup(bank, rule_code=rule_code)
    bank.moderation_status = "approved"
    bank.moderated_at = datetime.now(timezone.utc)
    bank.moderated_by = callback.from_user.id
    bank.moderation_comment = None
    await _log_moderation_audit(
        session,
        action="seller_bank_moderation_approve",
        entity_type="seller_bank",
        entity_id=bank.id,
        seller_id=bank.seller_id,
        source="support_bot",
        actor=actor,
        actor_telegram_id=callback.from_user.id,
        payload={
            "bank_name": bank.bank_name,
            "bank_code": bank.bank_code,
            "upload_batch_id": getattr(bank, "upload_batch_id", None),
            "base_price": float(bank.base_price or 0),
            "final_price": float(getattr(bank, "final_price", bank.buyer_price) or 0),
            "buyer_price": float(bank.buyer_price or 0),
            "markup_code": rule.code if rule else None,
            "moderation_status": bank.moderation_status,
        },
    )
    await session.commit()
    await SellerUploadBatchService.recalc_batch_status(session, bank.upload_batch_id, "bank")
    
    approval_label = rule.label if rule else "base price"
    await callback.answer(f"✅ Approved with {approval_label}", show_alert=True)
    callback.data = "mod_banks_list"
    await mod_banks_list(callback, session, **kwargs)


@router.callback_query(F.data.startswith("mod_bank_reject:"))
async def mod_bank_reject(callback: CallbackQuery, session: AsyncSession, **kwargs):
    actor = _actor(kwargs)
    if not _can_moderate(kwargs):
        await callback.answer("❌ Admin only", show_alert=True)
        return
    
    bank_id = int(callback.data.split(":")[1])
    result = await session.execute(select(SellerBank).where(SellerBank.id == bank_id))
    bank = result.scalar_one_or_none()
    if not bank:
        await callback.answer("Not found", show_alert=True)
        return
    
    bank.moderation_status = "rejected"
    bank.moderated_at = datetime.now(timezone.utc)
    bank.moderated_by = callback.from_user.id
    await _log_moderation_audit(
        session,
        action="seller_bank_moderation_reject",
        entity_type="seller_bank",
        entity_id=bank.id,
        seller_id=bank.seller_id,
        source="support_bot",
        actor=actor,
        actor_telegram_id=callback.from_user.id,
        payload={
            "bank_name": bank.bank_name,
            "bank_code": bank.bank_code,
            "upload_batch_id": getattr(bank, "upload_batch_id", None),
            "moderation_status": bank.moderation_status,
        },
    )
    await session.commit()
    await SellerUploadBatchService.recalc_batch_status(session, bank.upload_batch_id, "bank")
    
    await callback.answer("❌ Rejected", show_alert=True)
    callback.data = "mod_banks_list"
    await mod_banks_list(callback, session, **kwargs)


@router.callback_query(F.data.startswith("mod_bank_changes:"))
async def mod_bank_changes_start(callback: CallbackQuery, state: FSMContext, **kwargs):
    if not _can_moderate(kwargs):
        await callback.answer("❌ Admin only", show_alert=True)
        return
    
    bank_id = int(callback.data.split(":")[1])
    await state.set_state(RequestChangesStates.waiting_comment)
    await state.update_data(mod_entity="bank", mod_id=bank_id)
    await callback.message.edit_text(
        "📝 Enter the comment for the seller (what to fix):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancel", callback_data=f"mod_bank:{bank_id}")]
        ])
    )
    await callback.answer()


@router.message(RequestChangesStates.waiting_comment, Command("cancel"))
async def mod_changes_cancel(message: Message, state: FSMContext, **kwargs):
    await state.clear()
    await message.answer("❌ Request changes cancelled.")


@router.message(RequestChangesStates.waiting_comment, F.text)
async def mod_changes_comment(message: Message, state: FSMContext, session: AsyncSession, **kwargs):
    actor = _actor(kwargs)
    if not _can_moderate(kwargs):
        return
    
    data = await state.get_data()
    entity = data.get("mod_entity")
    entity_id = data.get("mod_id")
    await state.clear()
    
    if entity == "bank":
        result = await session.execute(select(SellerBank).where(SellerBank.id == entity_id))
        bank = result.scalar_one_or_none()
        if bank:
            bank.moderation_status = "changes_requested"
            bank.moderation_comment = message.text.strip()
            bank.moderated_at = datetime.now(timezone.utc)
            bank.moderated_by = message.from_user.id
            await _log_moderation_audit(
                session,
                action="seller_bank_moderation_changes_requested",
                entity_type="seller_bank",
                entity_id=bank.id,
                seller_id=bank.seller_id,
                source="support_bot",
                actor=actor,
                actor_telegram_id=message.from_user.id,
                payload={
                    "bank_name": bank.bank_name,
                    "bank_code": bank.bank_code,
                    "upload_batch_id": getattr(bank, "upload_batch_id", None),
                    "moderation_status": bank.moderation_status,
                    "comment": bank.moderation_comment,
                },
            )
            await session.commit()
            await SellerUploadBatchService.recalc_batch_status(session, bank.upload_batch_id, "bank")
        await message.answer("📝 Changes requested. Seller will be notified.")
    elif entity == "cc":
        result = await session.execute(select(SellerCCItem).where(SellerCCItem.id == entity_id))
        item = result.scalar_one_or_none()
        if item:
            item.moderation_status = "changes_requested"
            item.moderation_comment = message.text.strip()
            item.moderated_at = datetime.now(timezone.utc)
            item.moderated_by = message.from_user.id
            await _log_moderation_audit(
                session,
                action="seller_cc_moderation_changes_requested",
                entity_type="seller_cc_item",
                entity_id=item.id,
                seller_id=item.seller_id,
                source="support_bot",
                actor=actor,
                actor_telegram_id=message.from_user.id,
                payload={
                    "item_name": item.item_name,
                    "cc_code": item.cc_code,
                    "upload_batch_id": getattr(item, "upload_batch_id", None),
                    "moderation_status": item.moderation_status,
                    "comment": item.moderation_comment,
                },
            )
            await session.commit()
            await SellerUploadBatchService.recalc_batch_status(session, item.upload_batch_id, "cc")
        await message.answer("📝 Changes requested. Seller will be notified.")
    elif entity == "nfc":
        item = await session.scalar(select(SellerNFCItem).where(SellerNFCItem.id == entity_id))
        if item:
            item.moderation_status = "changes_requested"
            item.moderation_comment = message.text.strip()
            item.moderated_at = datetime.now(timezone.utc)
            item.moderated_by = message.from_user.id
            await _log_moderation_audit(
                session,
                action="seller_nfc_item_moderation_changes_requested",
                entity_type="seller_nfc_item",
                entity_id=item.id,
                seller_id=item.seller_id,
                source="support_bot",
                actor=actor,
                actor_telegram_id=message.from_user.id,
                payload=_special_item_payload(item, comment=item.moderation_comment),
            )
            await session.commit()
            await SellerUploadBatchService.recalc_batch_status(session, item.upload_batch_id, "nfc")
        await message.answer("📝 Changes requested. Seller will be notified.")
    elif entity == "otp":
        item = await session.scalar(select(SellerOTPItem).where(SellerOTPItem.id == entity_id))
        if item:
            item.moderation_status = "changes_requested"
            item.moderation_comment = message.text.strip()
            item.moderated_at = datetime.now(timezone.utc)
            item.moderated_by = message.from_user.id
            await _log_moderation_audit(
                session,
                action="seller_otp_item_moderation_changes_requested",
                entity_type="seller_otp_item",
                entity_id=item.id,
                seller_id=item.seller_id,
                source="support_bot",
                actor=actor,
                actor_telegram_id=message.from_user.id,
                payload=_special_item_payload(item, comment=item.moderation_comment),
            )
            await session.commit()
            await SellerUploadBatchService.recalc_batch_status(session, item.upload_batch_id, "otp")
        await message.answer("📝 Changes requested. Seller will be notified.")
    elif entity == "selfreg_cc":
        item = await session.scalar(select(SellerSelfregCCItem).where(SellerSelfregCCItem.id == entity_id))
        if item:
            item.moderation_status = "changes_requested"
            item.moderation_comment = message.text.strip()
            item.moderated_at = datetime.now(timezone.utc)
            item.moderated_by = message.from_user.id
            await _log_moderation_audit(
                session,
                action="seller_selfreg_cc_item_moderation_changes_requested",
                entity_type="seller_selfreg_cc_item",
                entity_id=item.id,
                seller_id=item.seller_id,
                source="support_bot",
                actor=actor,
                actor_telegram_id=message.from_user.id,
                payload=_special_item_payload(item, comment=item.moderation_comment),
            )
            await session.commit()
            await SellerUploadBatchService.recalc_batch_status(session, item.upload_batch_id, "selfreg_cc")
        await message.answer("📝 Changes requested. Seller will be notified.")
    elif entity == "enroll":
        item = await session.scalar(select(SellerEnrollItem).where(SellerEnrollItem.id == entity_id))
        if item:
            item.moderation_status = "changes_requested"
            item.moderation_comment = message.text.strip()
            item.moderated_at = datetime.now(timezone.utc)
            item.moderated_by = message.from_user.id
            await _log_moderation_audit(
                session,
                action="seller_enroll_item_moderation_changes_requested",
                entity_type="seller_enroll_item",
                entity_id=item.id,
                seller_id=item.seller_id,
                source="support_bot",
                actor=actor,
                actor_telegram_id=message.from_user.id,
                payload=_special_item_payload(item, comment=item.moderation_comment),
            )
            await session.commit()
        await message.answer("📝 Changes requested. Seller will be notified.")
    elif entity == "selfreg_ba":
        # SellerSelfregBAItem was removed — selfreg_ba merged with bank items.
        # This entity type no longer exists; inform the moderator.
        await message.answer("⚠️ Entity type 'selfreg_ba' is no longer supported (merged into bank items).")
    elif entity == "logs":
        item = await session.scalar(select(SellerLogsItem).where(SellerLogsItem.id == entity_id))
        if item:
            item.moderation_status = "changes_requested"
            item.moderation_comment = message.text.strip()
            item.moderated_at = datetime.now(timezone.utc)
            item.moderated_by = message.from_user.id
            await _log_moderation_audit(
                session,
                action="seller_logs_item_moderation_changes_requested",
                entity_type="seller_logs_item",
                entity_id=item.id,
                seller_id=item.seller_id,
                source="support_bot",
                actor=actor,
                actor_telegram_id=message.from_user.id,
                payload=_special_item_payload(item, comment=item.moderation_comment),
            )
            await session.commit()
        await message.answer("📝 Changes requested. Seller will be notified.")
    elif entity == "check":
        item = await session.scalar(select(SellerCheckItem).where(SellerCheckItem.id == entity_id))
        if item:
            item.moderation_status = "changes_requested"
            item.moderation_comment = message.text.strip()
            item.moderated_at = datetime.now(timezone.utc)
            item.moderated_by = message.from_user.id
            await _log_moderation_audit(
                session,
                action="seller_check_item_moderation_changes_requested",
                entity_type="seller_check_item",
                entity_id=item.id,
                seller_id=item.seller_id,
                source="support_bot",
                actor=actor,
                actor_telegram_id=message.from_user.id,
                payload=_special_item_payload(item, comment=item.moderation_comment),
            )
            await session.commit()
            await SellerUploadBatchService.recalc_batch_status(session, item.upload_batch_id, "check")
        await message.answer("📝 Changes requested. Seller will be notified.")


@router.callback_query(F.data == "mod_cc_list")
async def mod_cc_list(callback: CallbackQuery, session: AsyncSession, **kwargs):
    if not _can_moderate(kwargs):
        await callback.answer("❌ Admin only", show_alert=True)
        return
    
    result = await session.execute(
        select(SellerCCItem, Seller).join(Seller, SellerCCItem.seller_id == Seller.id).where(
            SellerCCItem.moderation_status == "pending_moderation",
            SellerCCItem.is_active == True
        ).order_by(SellerCCItem.created_at.desc()).limit(15)
    )
    rows = list(result.all())
    
    if not rows:
        await callback.message.edit_text("No CC items pending moderation.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Search CC", callback_data="mod_cc_search")],
            [InlineKeyboardButton(text="⬅️ Back", callback_data="mod_back")]
        ]))
        await callback.answer()
        return
    
    text = "💳 <b>CC items pending moderation</b>\n\n"
    buttons = []
    for item, seller in rows:
        batch_text = f" | batch #{item.upload_batch_id}" if getattr(item, "upload_batch_id", None) else ""
        text += f"• #{item.id} {item.item_name} | ${item.seller_price} | {seller.display_name or '?'}{batch_text}\n"
        buttons.append([
            InlineKeyboardButton(text=f"#{item.id} {item.item_name}", callback_data=f"mod_cc:{item.id}")
        ])
    buttons.append([InlineKeyboardButton(text="🔍 Search CC", callback_data="mod_cc_search")])
    buttons.append([InlineKeyboardButton(text="⬅️ Back", callback_data="mod_back")])
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()


@router.callback_query(F.data == "mod_cc_search")
async def mod_cc_search_start(callback: CallbackQuery, state: FSMContext, **kwargs):
    if not _can_moderate(kwargs):
        await callback.answer("❌ Admin only", show_alert=True)
        return
    await state.set_state(ModCCSearchStates.waiting_query)
    await callback.message.edit_text(
        "🔍 <b>Search CC Items</b>\n\n"
        "Enter search query — matches against:\n"
        "• BIN prefix (first 6 digits)\n"
        "• Bank name\n"
        "• Card brand (Visa, Mastercard, Amex…)\n"
        "• Card type (CREDIT, DEBIT)\n\n"
        "Send your query or /cancel to go back.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Cancel", callback_data="mod_cc_list")]
        ]),
    )
    await callback.answer()


@router.message(ModCCSearchStates.waiting_query, Command("cancel"))
async def mod_cc_search_cancel(message: Message, state: FSMContext, **kwargs):
    await state.clear()
    await message.answer("Search cancelled.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Back", callback_data="mod_cc_list")]
    ]))


@router.message(ModCCSearchStates.waiting_query, F.text)
async def mod_cc_search_results(message: Message, state: FSMContext, session: AsyncSession, **kwargs):
    if not _can_moderate(kwargs):
        await message.answer("❌ Admin only")
        return
    await state.clear()
    q = message.text.strip()

    conds = [SellerCCItem.is_active == True]
    if q.isdigit() and len(q) >= 4:
        conds.append(SellerCCItem.card_bin.startswith(q[:6]))
    else:
        like_q = f"%{q}%"
        conds.append(or_(
            SellerCCItem.bank_name.ilike(like_q),
            SellerCCItem.card_brand.ilike(like_q),
            SellerCCItem.card_type.ilike(like_q),
            SellerCCItem.item_name.ilike(like_q),
        ))

    result = await session.execute(
        select(SellerCCItem, Seller).join(Seller, SellerCCItem.seller_id == Seller.id)
        .where(and_(*conds))
        .order_by(SellerCCItem.created_at.desc())
        .limit(15)
    )
    rows = list(result.all())
    if not rows:
        await message.answer(
            f"🔍 No CC items found for <b>{q}</b>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔍 Search again", callback_data="mod_cc_search")],
                [InlineKeyboardButton(text="⬅️ Back", callback_data="mod_cc_list")],
            ]),
        )
        return

    text = f"🔍 <b>CC search results for '{q}'</b>\n\n"
    buttons = []
    for item, seller in rows:
        bin_str = f"BIN:{item.card_bin} " if item.card_bin else ""
        brand_str = f"{item.card_brand or ''} "
        bank_str = f"{item.bank_name or ''} "
        badge = item.moderation_status[:3].upper()
        text += f"• [{badge}] #{item.id} {bin_str}{brand_str}{bank_str}| ${item.seller_price}\n"
        buttons.append([
            InlineKeyboardButton(text=f"#{item.id} {item.item_name}"[:50], callback_data=f"mod_cc:{item.id}")
        ])
    buttons.append([InlineKeyboardButton(text="🔍 Search again", callback_data="mod_cc_search")])
    buttons.append([InlineKeyboardButton(text="⬅️ Back", callback_data="mod_cc_list")])
    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("mod_cc:"))
async def mod_cc_detail(callback: CallbackQuery, session: AsyncSession, **kwargs):
    if not _can_moderate(kwargs):
        await callback.answer("❌ Admin only", show_alert=True)
        return
    
    item_id = int(callback.data.split(":")[1])
    result = await session.execute(
        select(SellerCCItem, Seller).join(Seller, SellerCCItem.seller_id == Seller.id).where(SellerCCItem.id == item_id)
    )
    row = result.one_or_none()
    if not row:
        await callback.answer("Not found", show_alert=True)
        return
    
    item, seller = row
    
    extra = f"\nExtra: {item.extra_data}" if getattr(item, 'extra_data', None) else ""
    
    text = (
        f"💳 <b>CC Item #{item.id}</b>\n\n"
        f"Name: {item.item_name}\n"
        f"Code: {item.cc_code}\n"
        f"Product: {cc_item_badge(getattr(item, 'product_subtype', 'with_fullz'))}\n"
        f"Category: {item.category_code}\n"
        f"Batch: #{item.upload_batch_id or '-'}\n"
        f"Seller price: ${item.seller_price}\n"
        f"Base price: ${getattr(item, 'base_price', item.seller_price)}\n"
        f"Final price: ${getattr(item, 'final_price', item.buyer_price)}\n"
        f"Markup: {getattr(item, 'markup_code', '-')}\n"
        f"Seller: {seller.display_name or seller.username} (@{seller.username or 'N/A'})\n"
        f"Description: {item.description or '-'}\n"
        f"Instruction: {getattr(item, 'instruction', None) or '-'}{extra}\n"
        f"Status: {item.moderation_status}\n"
        f"Created: {item.created_at.strftime('%Y-%m-%d %H:%M')}\n"
    )
    
    if item.moderation_status == "pending_moderation":
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Approve base price", callback_data=f"mod_cc_approve:{item.id}")],
            *_cc_rule_rows(item.id),
            [InlineKeyboardButton(text="❌ Reject", callback_data=f"mod_cc_reject:{item.id}")],
            [InlineKeyboardButton(text="📝 Request changes", callback_data=f"mod_cc_changes:{item.id}")],
            [InlineKeyboardButton(text="⬅️ Back", callback_data="mod_cc_list")]
        ])
    else:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Back", callback_data="mod_cc_list")]
        ])
    
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("mod_cc_approve:"))
async def mod_cc_approve(callback: CallbackQuery, session: AsyncSession, **kwargs):
    actor = _actor(kwargs)
    if not _can_moderate(kwargs):
        await callback.answer("❌ Admin only", show_alert=True)
        return
    
    item_id = int(callback.data.split(":")[1])
    rule_code = _selected_rule(callback.data)
    result = await session.execute(select(SellerCCItem).where(SellerCCItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        await callback.answer("Not found", show_alert=True)
        return
    
    rule = apply_cc_markup(item, rule_code=rule_code)
    item.moderation_status = "approved"
    item.is_approved = True
    item.moderated_at = datetime.now(timezone.utc)
    item.moderated_by = callback.from_user.id
    item.moderation_comment = None
    await _log_moderation_audit(
        session,
        action="seller_cc_moderation_approve",
        entity_type="seller_cc_item",
        entity_id=item.id,
        seller_id=item.seller_id,
        source="support_bot",
        actor=actor,
        actor_telegram_id=callback.from_user.id,
        payload={
            "item_name": item.item_name,
            "cc_code": item.cc_code,
            "upload_batch_id": getattr(item, "upload_batch_id", None),
            "base_price": float(item.base_price or 0),
            "final_price": float(getattr(item, "final_price", item.buyer_price) or 0),
            "buyer_price": float(item.buyer_price or 0),
            "markup_code": rule.code if rule else None,
            "moderation_status": item.moderation_status,
        },
    )
    await session.commit()
    await SellerUploadBatchService.recalc_batch_status(session, item.upload_batch_id, "cc")
    
    approval_label = rule.label if rule else "base price"
    await callback.answer(f"✅ Approved with {approval_label}", show_alert=True)
    callback.data = "mod_cc_list"
    await mod_cc_list(callback, session, **kwargs)


@router.callback_query(F.data.startswith("mod_cc_reject:"))
async def mod_cc_reject(callback: CallbackQuery, session: AsyncSession, **kwargs):
    actor = _actor(kwargs)
    if not _can_moderate(kwargs):
        await callback.answer("❌ Admin only", show_alert=True)
        return
    
    item_id = int(callback.data.split(":")[1])
    result = await session.execute(select(SellerCCItem).where(SellerCCItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        await callback.answer("Not found", show_alert=True)
        return
    
    item.moderation_status = "rejected"
    item.moderated_at = datetime.now(timezone.utc)
    item.moderated_by = callback.from_user.id
    await _log_moderation_audit(
        session,
        action="seller_cc_moderation_reject",
        entity_type="seller_cc_item",
        entity_id=item.id,
        seller_id=item.seller_id,
        source="support_bot",
        actor=actor,
        actor_telegram_id=callback.from_user.id,
        payload={
            "item_name": item.item_name,
            "cc_code": item.cc_code,
            "upload_batch_id": getattr(item, "upload_batch_id", None),
            "moderation_status": item.moderation_status,
        },
    )
    await session.commit()
    await SellerUploadBatchService.recalc_batch_status(session, item.upload_batch_id, "cc")
    
    await callback.answer("❌ Rejected", show_alert=True)
    callback.data = "mod_cc_list"
    await mod_cc_list(callback, session, **kwargs)


@router.callback_query(F.data.startswith("mod_cc_changes:"))
async def mod_cc_changes_start(callback: CallbackQuery, state: FSMContext, **kwargs):
    if not _can_moderate(kwargs):
        await callback.answer("❌ Admin only", show_alert=True)
        return
    
    item_id = int(callback.data.split(":")[1])
    await state.set_state(RequestChangesStates.waiting_comment)
    await state.update_data(mod_entity="cc", mod_id=item_id)
    await callback.message.edit_text(
        "📝 Enter the comment for the seller (what to fix):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancel", callback_data=f"mod_cc:{item_id}")]
        ])
    )
    await callback.answer()


async def _mod_special_list(callback: CallbackQuery, session: AsyncSession, model, label: str, callback_prefix: str, *, pending_status: str = "pending_moderation", **kwargs):
    if not _can_moderate(kwargs):
        await callback.answer("❌ Admin only", show_alert=True)
        return
    rows = list((await session.execute(
        select(model, Seller).join(Seller, model.seller_id == Seller.id).where(
            model.moderation_status == pending_status,
            model.is_active == True,
        ).order_by(model.created_at.desc()).limit(15)
    )).all())
    if not rows:
        await callback.message.edit_text(
            f"No {label} pending moderation.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back", callback_data="mod_back")]]),
        )
        await callback.answer()
        return
    text = f"{label} pending moderation\n\n"
    buttons = []
    for item, seller in rows:
        item_name = getattr(item, "item_name", getattr(item, "bank_name", getattr(item, "bank", getattr(item, "portal", str(item.id)))))
        text += f"• #{item.id} {item_name} | ${getattr(item, 'seller_price', getattr(item, 'price', 0))} | {seller.display_name or seller.username or '?'}\n"
        buttons.append([InlineKeyboardButton(text=f"#{item.id} {item_name}", callback_data=f"{callback_prefix}:{item.id}")])
    buttons.append([InlineKeyboardButton(text="⬅️ Back", callback_data="mod_back")])
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()


def _markup_rule_rows(item_id: int, prefix: str) -> list[list[InlineKeyboardButton]]:
    """Кнопки выбора наценки для модератора: % и $ варианты."""
    return [
        [
            InlineKeyboardButton(text="📊 +15%", callback_data=f"{prefix}_approve:{item_id}:p15"),
            InlineKeyboardButton(text="📊 +20%", callback_data=f"{prefix}_approve:{item_id}:p20"),
            InlineKeyboardButton(text="📊 +25%", callback_data=f"{prefix}_approve:{item_id}:p25"),
        ],
        [
            InlineKeyboardButton(text="💵 +$10", callback_data=f"{prefix}_approve:{item_id}:f10"),
            InlineKeyboardButton(text="💵 +$15", callback_data=f"{prefix}_approve:{item_id}:f15"),
            InlineKeyboardButton(text="💵 +$20", callback_data=f"{prefix}_approve:{item_id}:f20"),
            InlineKeyboardButton(text="💵 +$25", callback_data=f"{prefix}_approve:{item_id}:f25"),
        ],
        [
            InlineKeyboardButton(text="✅ Base price (0%)", callback_data=f"{prefix}_approve:{item_id}:base"),
        ],
    ]


async def _mod_special_detail(callback: CallbackQuery, session: AsyncSession, model, item_id: int, label: str, badge_text: str, prefix: str, summary_builder, **kwargs):
    if not _can_moderate(kwargs):
        await callback.answer("❌ Admin only", show_alert=True)
        return
    row = (await session.execute(select(model, Seller).join(Seller, model.seller_id == Seller.id).where(model.id == item_id))).one_or_none()
    if not row:
        await callback.answer("Not found", show_alert=True)
        return
    item, seller = row
    seller_price = float(getattr(item, 'seller_price', getattr(item, 'price', 0)) or 0)
    
    # Базовая информация
    text = (
        f"<b>{label} #{item.id}</b>\n\n"
        f"Name: {getattr(item, 'item_name', getattr(item, 'bank_name', getattr(item, 'bank', getattr(item, 'portal', '-'))))}\n"
        f"Product: {badge_text}\n"
        f"Batch: #{getattr(item, 'upload_batch_id', None) or '-'}\n"
    )
    
    # Детали товара (зависит от типа)
    if hasattr(item, 'nfc_type'):  # NFC
        text += f"NFC Type: {item.nfc_type}\n"
        text += f"Bank: {item.bank_name}\n"
        text += f"Country: {item.country}\n"
        text += f"State: {item.state or '-'}\n"
        text += f"ZIP: {item.zip or '-'}\n"
    elif hasattr(item, 'sms_access_type'):  # OTP
        text += f"Bank: {item.bank_name}\n"
        text += f"Balance: ${float(item.balance):.2f}\n"
        text += f"Has Fullz: {'✅' if item.has_fullz else '❌'}\n"
        text += f"SMS Access: {item.sms_access_type}\n"
    elif hasattr(item, 'check_type'):  # Checks
        text += f"Check Type: {item.check_type}\n"
        text += f"Bank: {item.bank_name}\n"
        text += f"Amount: ${float(item.amount):.2f}\n"
        text += f"State: {item.state or '-'}\n"
        text += f"ZIP: {item.zip or '-'}\n"
        text += f"Has Holder Name: {'✅' if item.has_holder_name else '❌'}\n"
        text += f"Has Address: {'✅' if item.has_address else '❌'}\n"
    elif hasattr(item, 'portal'):  # Enroll
        text += f"Portal: {item.portal}\n"
        text += f"Bank: {item.bank_name or '-'}\n"
        text += f"Balance: ${float(item.balance):.2f}\n"
        text += f"Card State: {item.card_state or '-'}\n"
        text += f"Card ZIP: {item.card_zip or '-'}\n"
        text += f"Has SSN: {'✅' if item.has_ssn else '❌'}\n"
        text += f"Has DOB: {'✅' if item.has_dob else '❌'}\n"
        text += f"Has Address: {'✅' if item.has_address else '❌'}\n"
        text += f"Has Docs: {'✅' if item.has_docs else '❌'}\n"
    elif hasattr(item, 'total_balance'):  # Logs
        text += f"Bank: {item.bank}\n"
        text += f"Total Balance: ${float(item.total_balance):.2f}\n"
        text += f"Has CVV: {'✅' if item.has_cvv else '❌'}\n"
        text += f"BT Available: {'✅' if item.bt_available else '❌'}\n"
        text += f"Zelle Enroll: {'✅' if item.zelle_enroll else '❌'}\n"
        text += f"Has Cookies: {'✅' if getattr(item, 'has_cookies', False) else '❌'}\n"
    elif hasattr(item, 'phone_days_remaining'):  # Selfreg BA
        text += f"Bank: {item.bank}\n"
        text += f"Balance: ${float(item.balance):.2f}\n"
        text += f"State: {item.state or '-'}\n"
        text += f"Has Phone: {'✅' if item.has_phone else '❌'}\n"
        if item.has_phone and item.phone_days_remaining:
            text += f"Phone Days: {item.phone_days_remaining}\n"
        text += f"Email Access: {'✅' if item.email_access else '❌'}\n"
        text += f"Has SSN: {'✅' if item.has_ssn else '❌'}\n"
        text += f"Has Docs: {'✅' if item.has_docs else '❌'}\n"
    elif hasattr(item, 'bank_name') and hasattr(item, 'credit_limit'):  # Selfreg CC
        text += f"Bank: {item.bank_name}\n"
        text += f"Credit Limit: ${float(item.credit_limit or 0):.2f}\n"
        text += f"VCC Limit: ${float(item.vcc_limit or 0):.2f}\n"
        text += f"State: {item.state or '-'}\n"
        text += f"Has Phone: {'✅' if item.has_phone else '❌'}\n"
        text += f"Has SSN: {'✅' if item.has_ssn else '❌'}\n"
    
    # Файлы
    files_text = ""
    if hasattr(item, 'data_file_path') and item.data_file_path:
        files_text += f"📎 Data File: <code>{item.data_file_path}</code>\n"
    if hasattr(item, 'scan_file_path') and item.scan_file_path:
        files_text += f"📎 Scan File: <code>{item.scan_file_path}</code>\n"
    if hasattr(item, 'template_file_path') and item.template_file_path:
        files_text += f"📎 Template File: <code>{item.template_file_path}</code>\n"
    if hasattr(item, 'sample_file_path') and item.sample_file_path:
        files_text += f"📎 Sample File: <code>{item.sample_file_path}</code>\n"
    
    if files_text:
        text += f"\n{files_text}"
    
    # Цены и описание
    text += (
        f"\n💰 Seller price: <b>${seller_price:.2f}</b>\n"
        f"Seller: {seller.display_name or seller.username} (@{seller.username or 'N/A'})\n"
    )
    
    if hasattr(item, 'description') and item.description:
        text += f"Description: {item.description[:200]}{'...' if len(item.description) > 200 else ''}\n"
    if hasattr(item, 'seller_description') and item.seller_description:
        text += f"Description: {item.seller_description[:200]}{'...' if len(item.seller_description) > 200 else ''}\n"
    if hasattr(item, 'instruction') and item.instruction:
        text += f"Instruction: {item.instruction[:200]}{'...' if len(item.instruction) > 200 else ''}\n"
    
    text += (
        f"Status: {item.moderation_status}\n"
        f"Created: {item.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
        f"<b>Выберите наценку для покупателя:</b>"
    )
    
    buttons = _markup_rule_rows(item.id, prefix)
    buttons.append([
        InlineKeyboardButton(text="❌ Reject", callback_data=f"{prefix}_reject:{item.id}"),
    ])
    buttons.append([InlineKeyboardButton(text="📝 Request changes", callback_data=f"{prefix}_changes:{item.id}")])
    buttons.append([InlineKeyboardButton(text="⬅️ Back", callback_data=f"{prefix}_list")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


def _parse_custom_markup(markup_code: str):
    """Разбирает кастомную наценку из callback: p15 → (percent, 15), f20 → (flat, 20), base → (base, 0)."""
    from shared.services.moderation_pricing_service import ModerationMarkupRule, _apply_rule, apply_base_price, normalize_base_price
    from decimal import Decimal

    if markup_code == "base":
        return None
    if markup_code.startswith("p"):
        value = Decimal(markup_code[1:])
        return ModerationMarkupRule(code=f"custom_percent_{value}", label=f"+{value}%", kind="percent", value=value)
    if markup_code.startswith("f"):
        value = Decimal(markup_code[1:])
        return ModerationMarkupRule(code=f"custom_flat_{value}", label=f"+${value}", kind="flat", value=value)
    return None


async def _mod_special_approve(callback: CallbackQuery, session: AsyncSession, model, item_id: int, apply_markup, entity_type: str, item_type: str, list_callback: str, **kwargs):
    from shared.services.moderation_pricing_service import _apply_rule, apply_base_price

    actor = _actor(kwargs)
    if not _can_moderate(kwargs):
        await callback.answer("❌ Admin only", show_alert=True)
        return
    item = await session.scalar(select(model).where(model.id == item_id))
    if not item:
        await callback.answer("Not found", show_alert=True)
        return

    parts = callback.data.split(":")
    custom_code = parts[2] if len(parts) > 2 and parts[2] else None

    if custom_code and custom_code == "base":
        apply_base_price(item)
        markup_label = "Base price"
        markup_code = "base"
    elif custom_code:
        custom_rule = _parse_custom_markup(custom_code)
        if custom_rule:
            _apply_rule(item, custom_rule)
            markup_label = custom_rule.label
            markup_code = custom_rule.code
        else:
            rule = apply_markup(item)
            markup_label = rule.label if hasattr(rule, 'label') else "default"
            markup_code = rule.code if hasattr(rule, 'code') else "default"
    else:
        rule = apply_markup(item)
        markup_label = rule.label if hasattr(rule, 'label') else "default"
        markup_code = rule.code if hasattr(rule, 'code') else "default"

    item.moderation_status = "approved"
    item.moderated_at = datetime.now(timezone.utc)
    item.moderated_by = callback.from_user.id
    await _log_moderation_audit(
        session,
        action=f"{entity_type}_moderation_approve",
        entity_type=entity_type,
        entity_id=item.id,
        seller_id=item.seller_id,
        source="support_bot",
        actor=actor,
        actor_telegram_id=callback.from_user.id,
        payload={**_special_item_payload(item), "markup_code": markup_code},
    )
    await session.commit()
    await SellerUploadBatchService.recalc_batch_status(session, item.upload_batch_id, item_type)
    final = float(getattr(item, 'buyer_price', getattr(item, 'final_price', 0)) or 0)
    await callback.answer(f"✅ Approved: {markup_label} → ${final:.2f}", show_alert=True)
    callback_prefix = list_callback.removesuffix("_list")
    await _mod_special_list(callback, session, model, f"{item_type} items", callback_prefix, **kwargs)


async def _mod_special_reject(callback: CallbackQuery, session: AsyncSession, model, item_id: int, item_type: str, entity_type: str, list_callback: str, **kwargs):
    actor = _actor(kwargs)
    if not _can_moderate(kwargs):
        await callback.answer("❌ Admin only", show_alert=True)
        return
    item = await session.scalar(select(model).where(model.id == item_id))
    if not item:
        await callback.answer("Not found", show_alert=True)
        return
    item.moderation_status = "rejected"
    item.moderated_at = datetime.now(timezone.utc)
    item.moderated_by = callback.from_user.id
    await _log_moderation_audit(
        session,
        action=f"{entity_type}_moderation_reject",
        entity_type=entity_type,
        entity_id=item.id,
        seller_id=item.seller_id,
        source="support_bot",
        actor=actor,
        actor_telegram_id=callback.from_user.id,
        payload=_special_item_payload(item),
    )
    await session.commit()
    await SellerUploadBatchService.recalc_batch_status(session, item.upload_batch_id, item_type)
    await callback.answer("❌ Rejected", show_alert=True)
    callback_prefix = list_callback.removesuffix("_list")
    await _mod_special_list(callback, session, model, f"{item_type} items", callback_prefix, **kwargs)


@router.callback_query(F.data == "mod_nfc_list")
async def mod_nfc_list(callback: CallbackQuery, session: AsyncSession, **kwargs):
    await _mod_special_list(callback, session, SellerNFCItem, "NFC items", "mod_nfc", **kwargs)


@router.callback_query(F.data == "mod_otp_list")
async def mod_otp_list(callback: CallbackQuery, session: AsyncSession, **kwargs):
    await _mod_special_list(callback, session, SellerOTPItem, "OTP items", "mod_otp", **kwargs)


@router.callback_query(F.data == "mod_enroll_list")
async def mod_enroll_list(callback: CallbackQuery, session: AsyncSession, **kwargs):
    await _mod_special_list(callback, session, SellerEnrollItem, "Enroll items", "mod_enroll", pending_status="pending_moderation", **kwargs)


# Note: mod_selfreg_ba_list removed - selfreg_ba merged with bank items

@router.callback_query(F.data == "mod_logs_list")
async def mod_logs_list(callback: CallbackQuery, session: AsyncSession, **kwargs):
    await _mod_special_list(callback, session, SellerLogsItem, "Logs items", "mod_logs", pending_status="pending_moderation", **kwargs)


@router.callback_query(F.data == "mod_selfreg_cc_list")
async def mod_selfreg_cc_list(callback: CallbackQuery, session: AsyncSession, **kwargs):
    await _mod_special_list(callback, session, SellerSelfregCCItem, "Selfreg CC items", "mod_selfreg_cc", **kwargs)


@router.callback_query(F.data == "mod_checks_list")
@router.callback_query(F.data == "mod_check_list")
async def mod_checks_list(callback: CallbackQuery, session: AsyncSession, **kwargs):
    await _mod_special_list(callback, session, SellerCheckItem, "Check items", "mod_check", **kwargs)


@router.callback_query(F.data.startswith("mod_nfc:"))
async def mod_nfc_detail(callback: CallbackQuery, session: AsyncSession, **kwargs):
    await _mod_special_detail(callback, session, SellerNFCItem, int(callback.data.split(":")[1]), "NFC item", "NFC", "mod_nfc", lambda item: f"{item.nfc_type.upper()} | {item.bank_name} | {item.country} {item.state or ''} {item.zip or ''}".strip(), **kwargs)


@router.callback_query(F.data.startswith("mod_otp:"))
async def mod_otp_detail(callback: CallbackQuery, session: AsyncSession, **kwargs):
    await _mod_special_detail(callback, session, SellerOTPItem, int(callback.data.split(":")[1]), "OTP item", "OTP", "mod_otp", lambda item: f"{item.bank_name} | ${float(item.balance):.2f} | {item.sms_access_type}", **kwargs)


@router.callback_query(F.data.startswith("mod_enroll:"))
async def mod_enroll_detail(callback: CallbackQuery, session: AsyncSession, **kwargs):
    await _mod_special_detail(callback, session, SellerEnrollItem, int(callback.data.split(":")[1]), "Enroll item", "Enroll", "mod_enroll", lambda item: f"{item.portal} | balance ${float(item.balance):.2f} | ssn {'yes' if item.has_ssn else 'no'}", **kwargs)


# Note: mod_selfreg_ba_detail removed - selfreg_ba merged with bank items

@router.callback_query(F.data.startswith("mod_logs:"))
async def mod_logs_detail(callback: CallbackQuery, session: AsyncSession, **kwargs):
    await _mod_special_detail(callback, session, SellerLogsItem, int(callback.data.split(":")[1]), "Logs item", "Logs", "mod_logs", lambda item: f"{item.bank} | total ${float(item.total_balance):.2f} | cookies {'yes' if item.has_cookies else 'no'} | cvv {'yes' if item.has_cvv else 'no'}", **kwargs)


@router.callback_query(F.data.startswith("mod_selfreg_cc:"))
async def mod_selfreg_cc_detail(callback: CallbackQuery, session: AsyncSession, **kwargs):
    await _mod_special_detail(callback, session, SellerSelfregCCItem, int(callback.data.split(":")[1]), "Selfreg CC item", "Selfreg CC", "mod_selfreg_cc", lambda item: f"{item.bank_name} | credit ${float(item.credit_limit or 0):.2f} | vcc ${float(item.vcc_limit or 0):.2f}", **kwargs)


@router.callback_query(F.data.startswith("mod_check:"))
async def mod_check_detail(callback: CallbackQuery, session: AsyncSession, **kwargs):
    await _mod_special_detail(callback, session, SellerCheckItem, int(callback.data.split(":")[1]), "Check item", "Check", "mod_check", lambda item: f"{item.check_type} | {item.bank_name} | ${float(item.amount):.2f}", **kwargs)


@router.callback_query(F.data.startswith("mod_nfc_approve:"))
async def mod_nfc_approve(callback: CallbackQuery, session: AsyncSession, **kwargs):
    await _mod_special_approve(callback, session, SellerNFCItem, int(callback.data.split(":")[1]), apply_nfc_markup, "seller_nfc_item", "nfc", "mod_nfc_list", **kwargs)


@router.callback_query(F.data.startswith("mod_otp_approve:"))
async def mod_otp_approve(callback: CallbackQuery, session: AsyncSession, **kwargs):
    await _mod_special_approve(callback, session, SellerOTPItem, int(callback.data.split(":")[1]), apply_otp_markup, "seller_otp_item", "otp", "mod_otp_list", **kwargs)


@router.callback_query(F.data.startswith("mod_enroll_approve:"))
async def mod_enroll_approve(callback: CallbackQuery, session: AsyncSession, **kwargs):
    await _mod_special_approve(callback, session, SellerEnrollItem, int(callback.data.split(":")[1]), apply_enroll_markup, "seller_enroll_item", "enroll", "mod_enroll_list", **kwargs)


# Note: mod_selfreg_ba handlers removed - selfreg_ba merged with bank items

@router.callback_query(F.data.startswith("mod_logs_approve:"))
async def mod_logs_approve(callback: CallbackQuery, session: AsyncSession, **kwargs):
    await _mod_special_approve(callback, session, SellerLogsItem, int(callback.data.split(":")[1]), apply_logs_markup, "seller_logs_item", "logs", "mod_logs_list", **kwargs)


@router.callback_query(F.data.startswith("mod_selfreg_cc_approve:"))
async def mod_selfreg_cc_approve(callback: CallbackQuery, session: AsyncSession, **kwargs):
    await _mod_special_approve(callback, session, SellerSelfregCCItem, int(callback.data.split(":")[1]), apply_selfreg_cc_markup, "seller_selfreg_cc_item", "selfreg_cc", "mod_selfreg_cc_list", **kwargs)


@router.callback_query(F.data.startswith("mod_check_approve:"))
async def mod_check_approve(callback: CallbackQuery, session: AsyncSession, **kwargs):
    await _mod_special_approve(callback, session, SellerCheckItem, int(callback.data.split(":")[1]), apply_check_markup, "seller_check_item", "check", "mod_check_list", **kwargs)


@router.callback_query(F.data.startswith("mod_nfc_reject:"))
async def mod_nfc_reject(callback: CallbackQuery, session: AsyncSession, **kwargs):
    await _mod_special_reject(callback, session, SellerNFCItem, int(callback.data.split(":")[1]), "nfc", "seller_nfc_item", "mod_nfc_list", **kwargs)


@router.callback_query(F.data.startswith("mod_otp_reject:"))
async def mod_otp_reject(callback: CallbackQuery, session: AsyncSession, **kwargs):
    await _mod_special_reject(callback, session, SellerOTPItem, int(callback.data.split(":")[1]), "otp", "seller_otp_item", "mod_otp_list", **kwargs)


@router.callback_query(F.data.startswith("mod_enroll_reject:"))
async def mod_enroll_reject(callback: CallbackQuery, session: AsyncSession, **kwargs):
    await _mod_special_reject(callback, session, SellerEnrollItem, int(callback.data.split(":")[1]), "enroll", "seller_enroll_item", "mod_enroll_list", **kwargs)


# Note: mod_selfreg_ba_reject removed - selfreg_ba merged with bank items

@router.callback_query(F.data.startswith("mod_logs_reject:"))
async def mod_logs_reject(callback: CallbackQuery, session: AsyncSession, **kwargs):
    await _mod_special_reject(callback, session, SellerLogsItem, int(callback.data.split(":")[1]), "logs", "seller_logs_item", "mod_logs_list", **kwargs)


@router.callback_query(F.data.startswith("mod_selfreg_cc_reject:"))
async def mod_selfreg_cc_reject(callback: CallbackQuery, session: AsyncSession, **kwargs):
    await _mod_special_reject(callback, session, SellerSelfregCCItem, int(callback.data.split(":")[1]), "selfreg_cc", "seller_selfreg_cc_item", "mod_selfreg_cc_list", **kwargs)


@router.callback_query(F.data.startswith("mod_check_reject:"))
async def mod_check_reject(callback: CallbackQuery, session: AsyncSession, **kwargs):
    await _mod_special_reject(callback, session, SellerCheckItem, int(callback.data.split(":")[1]), "check", "seller_check_item", "mod_check_list", **kwargs)


@router.callback_query(F.data.startswith("mod_nfc_changes:"))
async def mod_nfc_changes_start(callback: CallbackQuery, state: FSMContext, **kwargs):
    if not _can_moderate(kwargs):
        await callback.answer("❌ Admin only", show_alert=True)
        return
    await state.set_state(RequestChangesStates.waiting_comment)
    await state.update_data(mod_entity="nfc", mod_id=int(callback.data.split(":")[1]))
    await callback.message.edit_text("📝 Enter the comment for the seller:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Cancel", callback_data="mod_nfc_list")]]))
    await callback.answer()


@router.callback_query(F.data.startswith("mod_otp_changes:"))
async def mod_otp_changes_start(callback: CallbackQuery, state: FSMContext, **kwargs):
    if not _can_moderate(kwargs):
        await callback.answer("❌ Admin only", show_alert=True)
        return
    await state.set_state(RequestChangesStates.waiting_comment)
    await state.update_data(mod_entity="otp", mod_id=int(callback.data.split(":")[1]))
    await callback.message.edit_text("📝 Enter the comment for the seller:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Cancel", callback_data="mod_otp_list")]]))
    await callback.answer()


@router.callback_query(F.data.startswith("mod_enroll_changes:"))
async def mod_enroll_changes_start(callback: CallbackQuery, state: FSMContext, **kwargs):
    if not _can_moderate(kwargs):
        await callback.answer("❌ Admin only", show_alert=True)
        return
    await state.set_state(RequestChangesStates.waiting_comment)
    await state.update_data(mod_entity="enroll", mod_id=int(callback.data.split(":")[1]))
    await callback.message.edit_text("📝 Enter the comment for the seller:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Cancel", callback_data="mod_enroll_list")]]))
    await callback.answer()


# Note: mod_selfreg_ba_changes removed - selfreg_ba merged with bank items

@router.callback_query(F.data.startswith("mod_logs_changes:"))
async def mod_logs_changes_start(callback: CallbackQuery, state: FSMContext, **kwargs):
    if not _can_moderate(kwargs):
        await callback.answer("❌ Admin only", show_alert=True)
        return
    await state.set_state(RequestChangesStates.waiting_comment)
    await state.update_data(mod_entity="logs", mod_id=int(callback.data.split(":")[1]))
    await callback.message.edit_text("📝 Enter the comment for the seller:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Cancel", callback_data="mod_logs_list")]]))
    await callback.answer()


@router.callback_query(F.data.startswith("mod_selfreg_cc_changes:"))
async def mod_selfreg_cc_changes_start(callback: CallbackQuery, state: FSMContext, **kwargs):
    if not _can_moderate(kwargs):
        await callback.answer("❌ Admin only", show_alert=True)
        return
    await state.set_state(RequestChangesStates.waiting_comment)
    await state.update_data(mod_entity="selfreg_cc", mod_id=int(callback.data.split(":")[1]))
    await callback.message.edit_text("📝 Enter the comment for the seller:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Cancel", callback_data="mod_selfreg_cc_list")]]))
    await callback.answer()


@router.callback_query(F.data.startswith("mod_check_changes:"))
async def mod_check_changes_start(callback: CallbackQuery, state: FSMContext, **kwargs):
    if not _can_moderate(kwargs):
        await callback.answer("❌ Admin only", show_alert=True)
        return
    await state.set_state(RequestChangesStates.waiting_comment)
    await state.update_data(mod_entity="check", mod_id=int(callback.data.split(":")[1]))
    await callback.message.edit_text("📝 Enter the comment for the seller:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Cancel", callback_data="mod_check_list")]]))
    await callback.answer()


@router.callback_query(F.data == "mod_back")
async def mod_back(callback: CallbackQuery, session: AsyncSession, **kwargs):
    if not _can_moderate(kwargs):
        await callback.answer("❌ Admin only", show_alert=True)
        return
    await callback.answer()
    await cmd_seller_moderation(callback.message, session, **kwargs)
