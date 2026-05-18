"""
Other Services — загружаются из БД (AnotherServiceButton).
Поддерживает три типа кнопок: url, callback, info.
Язык-зависимые тексты кнопок (text_en / text_ru / text_zh).
"""

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from shared.database.models import AnotherServiceButton
from mirror_bot.utils.message_utils import safe_edit_message
from mirror_bot.constants.buttons_en import ButtonTexts

logger = logging.getLogger(__name__)
router = Router()

# Текст по умолчанию если БД пустая
_DEFAULT_TEXT = (
    "📞 *Other Services*\n\n"
    "Additional services and tools.\n"
    "For questions contact Support."
)


def _get_btn_text(btn: AnotherServiceButton, language: str) -> str:
    if language == "ru" and btn.text_ru:
        return btn.text_ru
    if language == "zh" and btn.text_zh:
        return btn.text_zh
    return btn.text_en


async def _load_buttons(session: AsyncSession):
    result = await session.execute(
        select(AnotherServiceButton)
        .where(AnotherServiceButton.is_active == True)
        .order_by(AnotherServiceButton.position)
    )
    return result.scalars().all()


def _build_keyboard(btns, language: str, buttons) -> InlineKeyboardMarkup:
    rows = []
    for btn in btns:
        text = _get_btn_text(btn, language)
        if btn.button_type == "url" and btn.url:
            rows.append([InlineKeyboardButton(text=text, url=btn.url)])
        elif btn.button_type == "callback" and btn.callback_data:
            rows.append([InlineKeyboardButton(text=text, callback_data=btn.callback_data)])
        elif btn.button_type == "info":
            # Info кнопка — отправляет callback для показа текста
            rows.append([InlineKeyboardButton(text=text, callback_data=f"as_info:{btn.id}")])
    rows.append([InlineKeyboardButton(text=buttons.BACK, callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _show_another_services(target, session: AsyncSession, texts, buttons, language: str):
    """Вспомогательная функция — отображает раздел для Message или CallbackQuery."""
    btns = await _load_buttons(session)
    main_text = getattr(texts, "ANOTHER_SERVICES_MAIN", None) or _DEFAULT_TEXT

    if not btns:
        # Нет кнопок из БД — показываем заглушку
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📞 Support", callback_data="support")],
            [InlineKeyboardButton(text=buttons.BACK, callback_data="back_main")],
        ])
    else:
        keyboard = _build_keyboard(btns, language, buttons)

    if isinstance(target, Message):
        await target.answer(main_text, reply_markup=keyboard, parse_mode="Markdown")
    else:
        await safe_edit_message(target, main_text, reply_markup=keyboard, parse_mode="Markdown")
        await target.answer()


# ─── Handlers ─────────────────────────────────────────────────────────────────

@router.message(F.text.in_(ButtonTexts.get_all_variants("ANOTHER_SERVICES")))
async def another_services_handler(message: Message, session: AsyncSession, texts, buttons):
    language = getattr(message, "_user_language", "en") or "en"
    await _show_another_services(message, session, texts, buttons, language)


@router.callback_query(F.data == "another_services_main")
async def another_services_callback(callback: CallbackQuery, session: AsyncSession, texts, buttons):
    language = getattr(callback, "_user_language", "en") or "en"
    await _show_another_services(callback, session, texts, buttons, language)


@router.callback_query(F.data.startswith("as_info:"))
async def another_service_info_handler(callback: CallbackQuery, session: AsyncSession, buttons):
    """Показывает информационный текст кнопки типа 'info'."""
    btn_id = int(callback.data.split(":", 1)[1])
    result = await session.execute(
        select(AnotherServiceButton).where(AnotherServiceButton.id == btn_id)
    )
    btn = result.scalar_one_or_none()
    if not btn:
        await callback.answer("Not found", show_alert=True)
        return

    language = getattr(callback, "_user_language", "en") or "en"
    text = _get_btn_text(btn, language)
    # Для info-кнопок текст кнопки используется как заголовок, callback_data как тело
    info_text = btn.callback_data or text

    await safe_edit_message(
        callback,
        f"ℹ️ *{text}*\n\n{info_text}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Back", callback_data="another_services_main")]
        ]),
        parse_mode="Markdown",
    )
    await callback.answer()
