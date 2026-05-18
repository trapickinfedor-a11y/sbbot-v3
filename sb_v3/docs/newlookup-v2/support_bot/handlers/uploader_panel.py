from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from support_bot.services.access_service import SupportBotActor

router = Router(name="uploader_panel")

CATALOG_LABELS = {
    "products": "Products / Logs",
    "banks": "Banks",
    "brute_bank": "Brute Bank",
    "accounts": "Accounts",
    "esim": "eSIM",
    "cc": "CC",
    "education": "Education",
    "another-services": "Another Services",
}


def _uploader_allowed_catalogs(actor: SupportBotActor | None) -> list[str]:
    if not actor or not actor.can_upload_catalogs:
        return []
    if actor.source == "system_admin":
        return list(CATALOG_LABELS.keys())
    return [code for code in (actor.allowed_catalogs or []) if code in CATALOG_LABELS]


def _uploader_menu_keyboard(catalogs: list[str]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if "products" in catalogs:
        rows.append([InlineKeyboardButton(text="📤 Upload Product", callback_data="worker_upload_product")])
    rows.append([InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data == "uploader_menu")
async def uploader_menu(callback: CallbackQuery, support_bot_actor: SupportBotActor | None = None):
    catalogs = _uploader_allowed_catalogs(support_bot_actor)
    if not catalogs:
        await callback.answer("❌ No uploader access", show_alert=True)
        return

    catalog_lines = "\n".join(
        f"• {CATALOG_LABELS.get(code, code)}" for code in catalogs
    )
    text = (
        "📤 <b>Uploader Panel</b>\n\n"
        "Assigned catalogs:\n"
        f"{catalog_lines}\n\n"
        "Use this panel to work only inside the catalogs assigned to your role."
    )
    if "products" not in catalogs:
        text += "\n\nChat upload flow is currently enabled for the `products` catalog."

    await callback.message.edit_text(
        text,
        reply_markup=_uploader_menu_keyboard(catalogs),
    )
    await callback.answer()
