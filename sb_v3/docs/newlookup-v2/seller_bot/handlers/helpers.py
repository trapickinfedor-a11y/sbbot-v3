from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from seller_bot.keyboards.inline import (
    seller_helper_accept_keyboard,
    seller_helper_detail_keyboard,
    seller_helper_role_keyboard,
    seller_helpers_list_keyboard,
    seller_helpers_menu_keyboard,
    seller_main_menu,
)
from shared.services.seller_helper_service import SellerHelperService

router = Router(name="seller_helpers")


class SellerHelperStates(StatesGroup):
    waiting_role = State()
    waiting_telegram_id = State()


def _owner_only(actor) -> bool:
    return bool(actor and actor.can_manage_helpers())


@router.callback_query(F.data == "seller_helpers")
async def seller_helpers_menu(callback: CallbackQuery, seller_actor=None, **kwargs):
    if not _owner_only(seller_actor):
        await callback.answer("Owner only", show_alert=True)
        return
    await callback.message.edit_text(
        "👥 <b>Helpers</b>\n\nManage your upload and support helpers.",
        reply_markup=seller_helpers_menu_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "seller_helper_add")
async def seller_helper_add_start(callback: CallbackQuery, state: FSMContext, seller_actor=None, **kwargs):
    if not _owner_only(seller_actor):
        await callback.answer("Owner only", show_alert=True)
        return
    await state.set_state(SellerHelperStates.waiting_role)
    await callback.message.edit_text(
        "Select helper role:",
        reply_markup=seller_helper_role_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("seller_helper_role:"), SellerHelperStates.waiting_role)
async def seller_helper_role_selected(callback: CallbackQuery, state: FSMContext, session: AsyncSession, seller_actor=None, **kwargs):
    if not _owner_only(seller_actor):
        await callback.answer("Owner only", show_alert=True)
        return
    role = callback.data.split(":", 1)[1]
    data = await state.get_data()
    helper_id = data.get("change_helper_id")
    if helper_id:
        helper = await SellerHelperService.get_helper(session, helper_id, seller_actor.seller.id)
        if not helper:
            await callback.answer("Helper not found", show_alert=True)
            return
        await SellerHelperService.change_role(session, helper, role=role)
        await state.clear()
        await callback.answer("Role updated")
        await seller_helper_detail(callback, session, seller_actor=seller_actor, **kwargs)
        return
    await state.update_data(helper_role=role)
    await state.set_state(SellerHelperStates.waiting_telegram_id)
    await callback.message.edit_text(
        "Send helper Telegram ID.\n\nExample: <code>123456789</code>",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(SellerHelperStates.waiting_telegram_id)
async def seller_helper_create(message: Message, state: FSMContext, session: AsyncSession, seller_actor=None, **kwargs):
    if not _owner_only(seller_actor):
        await state.clear()
        await message.answer("Owner only.")
        return
    raw = (message.text or "").strip()
    if not raw.isdigit():
        await message.answer("Send numeric Telegram ID.")
        return
    data = await state.get_data()
    helper = await SellerHelperService.create_invite(
        session,
        seller=seller_actor.seller,
        telegram_id=int(raw),
        username=None,
        display_name=None,
        role=data.get("helper_role", "support_helper"),
    )
    await state.clear()
    await message.answer(
        f"✅ Helper invite created.\n\nID: <code>{helper.telegram_id}</code>\nRole: <b>{helper.role}</b>\nStatus: <b>{helper.status}</b>",
        reply_markup=seller_helpers_menu_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "seller_helpers_active")
async def seller_helpers_active(callback: CallbackQuery, session: AsyncSession, seller_actor=None, **kwargs):
    if not _owner_only(seller_actor):
        await callback.answer("Owner only", show_alert=True)
        return
    helpers = [h for h in await SellerHelperService.list_helpers(session, seller_actor.seller.id) if h.status == "active"]
    await callback.message.edit_text(
        "👥 <b>Active Helpers</b>",
        reply_markup=seller_helpers_list_keyboard(helpers, list_type="active"),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "seller_helpers_pending")
async def seller_helpers_pending(callback: CallbackQuery, session: AsyncSession, seller_actor=None, **kwargs):
    if not _owner_only(seller_actor):
        await callback.answer("Owner only", show_alert=True)
        return
    helpers = [h for h in await SellerHelperService.list_helpers(session, seller_actor.seller.id) if h.status == "pending"]
    await callback.message.edit_text(
        "🕓 <b>Pending Invites</b>",
        reply_markup=seller_helpers_list_keyboard(helpers, list_type="pending"),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("seller_helper:"))
async def seller_helper_detail(callback: CallbackQuery, session: AsyncSession, seller_actor=None, **kwargs):
    if not _owner_only(seller_actor):
        await callback.answer("Owner only", show_alert=True)
        return
    helper_id = int(callback.data.split(":")[1])
    helper = await SellerHelperService.get_helper(session, helper_id, seller_actor.seller.id)
    if not helper:
        await callback.answer("Helper not found", show_alert=True)
        return
    await callback.message.edit_text(
        f"👤 <b>{helper.display_name or helper.username or helper.telegram_id}</b>\n\n"
        f"Role: <b>{helper.role}</b>\n"
        f"Status: <b>{helper.status}</b>\n"
        f"Telegram ID: <code>{helper.telegram_id}</code>",
        reply_markup=seller_helper_detail_keyboard(helper.id),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("seller_helper_block:"))
async def seller_helper_block(callback: CallbackQuery, session: AsyncSession, seller_actor=None, **kwargs):
    if not _owner_only(seller_actor):
        await callback.answer("Owner only", show_alert=True)
        return
    helper_id = int(callback.data.split(":")[1])
    helper = await SellerHelperService.get_helper(session, helper_id, seller_actor.seller.id)
    if not helper:
        await callback.answer("Helper not found", show_alert=True)
        return
    await SellerHelperService.change_status(session, helper, status="blocked")
    await callback.answer("Helper blocked")
    await seller_helper_detail(callback, session, seller_actor=seller_actor, **kwargs)


@router.callback_query(F.data.startswith("seller_helper_remove:"))
async def seller_helper_remove(callback: CallbackQuery, session: AsyncSession, seller_actor=None, **kwargs):
    if not _owner_only(seller_actor):
        await callback.answer("Owner only", show_alert=True)
        return
    helper_id = int(callback.data.split(":")[1])
    helper = await SellerHelperService.get_helper(session, helper_id, seller_actor.seller.id)
    if not helper:
        await callback.answer("Helper not found", show_alert=True)
        return
    await SellerHelperService.change_status(session, helper, status="removed")
    await callback.message.edit_text(
        "🗑 Helper removed.",
        reply_markup=seller_helpers_menu_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("seller_helper_change_role:"))
async def seller_helper_change_role_start(callback: CallbackQuery, state: FSMContext, session: AsyncSession, seller_actor=None, **kwargs):
    if not _owner_only(seller_actor):
        await callback.answer("Owner only", show_alert=True)
        return
    helper_id = int(callback.data.split(":")[1])
    helper = await SellerHelperService.get_helper(session, helper_id, seller_actor.seller.id)
    if not helper:
        await callback.answer("Helper not found", show_alert=True)
        return
    await state.update_data(change_helper_id=helper.id)
    await state.set_state(SellerHelperStates.waiting_role)
    await callback.message.edit_text("Select new helper role:", reply_markup=seller_helper_role_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("seller_helper_accept:"))
async def seller_helper_accept(callback: CallbackQuery, session: AsyncSession, seller_actor=None, buttons=None, **kwargs):
    helper_id = int(callback.data.split(":")[1])
    if not seller_actor or not seller_actor.is_helper or not seller_actor.helper or seller_actor.helper.id != helper_id:
        await callback.answer("Invite not found", show_alert=True)
        return
    helper = await SellerHelperService.accept_invite(
        session,
        seller_actor.helper,
        username=callback.from_user.username,
        display_name=callback.from_user.full_name,
    )
    await callback.message.edit_text(
        f"✅ Invite accepted.\n\nYou joined seller workspace as <b>{helper.role}</b>.",
        reply_markup=seller_main_menu(buttons=buttons, actor_role=helper.role),
        parse_mode="HTML",
    )
    await callback.answer()


async def render_pending_helper_invite(message_or_callback, seller_actor, buttons=None):
    helper = seller_actor.helper if seller_actor else None
    if not helper:
        return False
    text = (
        f"👥 <b>Seller helper invite</b>\n\n"
        f"Workspace seller ID: <code>{seller_actor.seller.id}</code>\n"
        f"Role: <b>{helper.role}</b>\n\n"
        f"Accept invite to continue."
    )
    if hasattr(message_or_callback, "edit_text"):
        await message_or_callback.edit_text(text, reply_markup=seller_helper_accept_keyboard(helper.id), parse_mode="HTML")
    else:
        await message_or_callback.answer(text, reply_markup=seller_helper_accept_keyboard(helper.id), parse_mode="HTML")
    return True
