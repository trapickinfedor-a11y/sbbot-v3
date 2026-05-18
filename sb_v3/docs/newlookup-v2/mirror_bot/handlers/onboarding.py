from __future__ import annotations

"""Mirror Bot — Interactive 3-step onboarding tour."""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message
from aiogram.fsm.context import FSMContext

logger = logging.getLogger(__name__)
router = Router(name="onboarding")

TOUR_STEPS = [
    {
        "step": 1,
        "emoji": "🛍️",
        "title": "Step 1: Browse the Catalog",
        "text": (
            "Use the <b>🗂️ Catalog</b> button to explore all available products.\n\n"
            "You can also use <b>🔍 /search</b> to instantly find what you need using smart fuzzy search.\n\n"
            "<i>Tip: Use keywords like 'chase ca' or 'bank of america'.</i>"
        ),
        "image": None,
    },
    {
        "step": 2,
        "emoji": "💰",
        "title": "Step 2: Fund Your Balance",
        "text": (
            "Before purchasing, <b>top up your balance</b>.\n\n"
            "Go to <b>💳 Top Up</b> and choose your preferred payment method.\n\n"
            "✅ You already have a <b>$0.50 welcome bonus</b> on your account!\n\n"
            "<i>Your balance is shown in the main menu.</i>"
        ),
        "image": None,
    },
    {
        "step": 3,
        "emoji": "⚡",
        "title": "Step 3: Buy & Get Instantly",
        "text": (
            "Once funded, tap <b>✅ Buy</b> on any product.\n\n"
            "• <b>In-Stock</b> items are delivered <u>immediately</u>.\n"
            "• <b>Per-Order</b> items are completed by workers — usually in 5-30 minutes.\n\n"
            "Need help? Use <b>🆘 Support</b> or open a <b>dispute</b> if something's wrong.\n\n"
            "🎉 <b>You're all set! Happy shopping!</b>"
        ),
        "image": None,
    },
]


def _tour_keyboard(step: int, total: int) -> InlineKeyboardMarkup:
    buttons = []
    nav = []
    if step > 1:
        nav.append(InlineKeyboardButton(text="◀ Back", callback_data=f"tour:{step - 1}"))
    if step < total:
        nav.append(InlineKeyboardButton(text="Next ▶", callback_data=f"tour:{step + 1}"))
    else:
        nav.append(InlineKeyboardButton(text="✅ Done!", callback_data="tour:done"))
    if nav:
        buttons.append(nav)
    buttons.append([InlineKeyboardButton(text="⏭ Skip Tour", callback_data="tour:skip")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _tour_text(step_data: dict, step: int, total: int) -> str:
    progress = "·" * (step - 1) + "●" + "·" * (total - step)
    return (
        f"{step_data['emoji']} <b>{step_data['title']}</b> [{progress}]\n\n"
        f"{step_data['text']}"
    )


@router.callback_query(F.data == "tour:start")
async def cb_tour_start(callback: CallbackQuery, **kwargs):
    step_data = TOUR_STEPS[0]
    await callback.message.edit_text(
        _tour_text(step_data, 1, len(TOUR_STEPS)),
        parse_mode="HTML",
        reply_markup=_tour_keyboard(1, len(TOUR_STEPS)),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("tour:"))
async def cb_tour_navigate(callback: CallbackQuery, **kwargs):
    action = callback.data.split(":", 1)[1]

    if action in ("skip", "done"):
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(
            "🏠 <b>Welcome to the platform!</b>\n\n"
            "Use the menu below to get started. Type /help anytime.",
            parse_mode="HTML",
        )
        await callback.answer("Tour complete!" if action == "done" else "Tour skipped.")
        return

    try:
        step = int(action)
    except ValueError:
        await callback.answer()
        return

    if 1 <= step <= len(TOUR_STEPS):
        step_data = TOUR_STEPS[step - 1]
        await callback.message.edit_text(
            _tour_text(step_data, step, len(TOUR_STEPS)),
            parse_mode="HTML",
            reply_markup=_tour_keyboard(step, len(TOUR_STEPS)),
        )
    await callback.answer()
