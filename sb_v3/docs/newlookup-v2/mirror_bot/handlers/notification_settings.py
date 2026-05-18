from __future__ import annotations

"""Mirror Bot — User notification preferences in profile."""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession

from mirror_bot.services.user_service import UserService

logger = logging.getLogger(__name__)
router = Router(name="notification_settings")

NOTIF_SETTINGS = [
    ("notif_order_updates", "📦 Order updates"),
    ("notif_promo", "🎁 Promotions & bonuses"),
    ("notif_price_drops", "📉 Price drop alerts"),
    ("notif_dispute_updates", "⚖️ Dispute updates"),
]


def _notif_keyboard(user) -> InlineKeyboardMarkup:
    buttons = []
    for field, label in NOTIF_SETTINGS:
        enabled = getattr(user, field, True)
        icon = "✅" if enabled else "🔕"
        buttons.append([InlineKeyboardButton(
            text=f"{icon} {label}",
            callback_data=f"notif_toggle:{field}",
        )])
    buttons.append([InlineKeyboardButton(text="⬅️ Back to Profile", callback_data="back_profile")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.callback_query(F.data == "notification_settings")
async def cb_notification_settings(
    callback: CallbackQuery,
    session: AsyncSession,
    mirror_bot_id: int = 0,
    **kwargs,
):
    user = await UserService.get_user(session, callback.from_user.id, mirror_bot_id)
    if not user:
        await callback.answer("User not found", show_alert=True)
        return
    await callback.message.edit_text(
        "🔔 <b>Notification Settings</b>\n\n"
        "Choose which notifications you want to receive:",
        parse_mode="HTML",
        reply_markup=_notif_keyboard(user),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("notif_toggle:"))
async def cb_notif_toggle(
    callback: CallbackQuery,
    session: AsyncSession,
    mirror_bot_id: int = 0,
    **kwargs,
):
    field = callback.data.split(":", 1)[1]
    valid_fields = {f for f, _ in NOTIF_SETTINGS}
    if field not in valid_fields:
        await callback.answer("Invalid setting", show_alert=True)
        return

    user = await UserService.get_user(session, callback.from_user.id, mirror_bot_id)
    if not user:
        await callback.answer("User not found", show_alert=True)
        return

    current = getattr(user, field, True)
    setattr(user, field, not current)
    await session.commit()

    await callback.message.edit_reply_markup(reply_markup=_notif_keyboard(user))
    status = "enabled" if not current else "disabled"
    await callback.answer(f"Notification {status} ✓")
