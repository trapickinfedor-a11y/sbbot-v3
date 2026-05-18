from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from mirror_bot.keyboards.inline import rules_accept_keyboard
from mirror_bot.keyboards.reply import main_menu_keyboard
from mirror_bot.middlewares.language import LanguageHelper
from mirror_bot.constants.language_loader import get_buttons, get_texts
from mirror_bot.services.user_service import UserService
from mirror_bot.services.menu_counts_service import MenuCountService
from mirror_bot.utils.media_library import resolve_bot_photo
from shared.services.menu_category_service import MenuCategoryService

router = Router()

def detect_user_language(language_code: Optional[str]) -> str:
    """Map Telegram language code to supported project languages."""
    code = (language_code or "").lower()
    if code.startswith("ru"):
        return "ru"
    if code.startswith("zh"):
        return "zh"
    if code.startswith("es"):
        return "es"
    return "en"


@router.message(CommandStart())
async def start_handler(message: Message, session: AsyncSession, mirror_bot_id: int, texts, buttons):
    referral_code = None
    if message.text and len(message.text.split()) > 1:
        referral_code = message.text.split()[1]
    
    referrer_id = None
    if referral_code and referral_code.startswith("ref_"):
        referrer = await UserService.get_user_by_referral(session, referral_code)
        if referrer:
            referrer_id = referrer.user_id
    
    detected_language = detect_user_language(message.from_user.language_code)
    user, created = await UserService.get_or_create_user(
        session,
        message.from_user.id,
        mirror_bot_id,
        referrer_id,
        message.from_user.username,
        detected_language,
        return_created=True,
    )

    if not user.language or (user.language == "en" and detected_language != "en" and not user.rules_accepted):
        await UserService.update_language(session, user.user_id, mirror_bot_id, detected_language)
        user.language = detected_language

    effective_language = user.language or detected_language
    effective_texts = get_texts(effective_language)
    effective_buttons = get_buttons(effective_language)

    if not user.rules_accepted:
        await show_rules_acceptance(message, effective_texts, effective_buttons)
    else:
        await show_main_menu(message, session, effective_texts, effective_buttons)


@router.callback_query(F.data.startswith("lang_"))
async def language_handler(callback: CallbackQuery, session: AsyncSession, mirror_bot_id: int, texts, buttons):
    language = callback.data.split("_")[1]

    await UserService.update_language(session, callback.from_user.id, mirror_bot_id, language)

    try:
        await callback.message.delete()
    except Exception:
        pass

    user = await UserService.get_user(session, callback.from_user.id, mirror_bot_id)

    from mirror_bot.constants.language_loader import get_texts, get_buttons
    new_texts = get_texts(language)
    new_buttons = get_buttons(language)

    if user and user.rules_accepted:
        await show_main_menu(callback.message, session, new_texts, new_buttons)
    else:
        await show_rules_acceptance(callback.message, new_texts, new_buttons)

    await callback.answer(new_texts.LANGUAGE_SAVED if hasattr(new_texts, 'LANGUAGE_SAVED') else texts.LANGUAGE_SAVED)


@router.callback_query(F.data == "rules_accept")
async def rules_accept_handler(callback: CallbackQuery, session: AsyncSession, mirror_bot_id: int, texts, buttons):
    user = await UserService.get_user(session, callback.from_user.id, mirror_bot_id)
    if user:
        user.rules_accepted = True
        await session.commit()

    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.message.answer(texts.RULES_ACCEPTED_SUCCESS)

    # Welcome bonus notification for new users + onboarding tour offer
    if user and float(getattr(user, "balance", 0) or 0) <= 0.50:
        try:
            await callback.message.answer(
                "🎁 <b>Welcome Bonus!</b>\n\n"
                "✅ <b>+$0.50</b> added to your balance as a welcome gift!\n"
                "Use it toward your first purchase. 🛍️",
                parse_mode="HTML",
            )
        except Exception:
            pass

        try:
            await callback.message.answer(
                "🎟 <b>Your coupon code:</b> <code>WELCOME10</code>\n"
                "Use it for <b>10% off</b> your first purchase! (valid 30 days)",
                parse_mode="HTML",
            )
        except Exception:
            pass

        try:
            await callback.message.answer(
                "👋 <b>New here?</b> Take a quick 3-step tour to learn how everything works!",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🚀 Start Tour", callback_data="tour:start"),
                     InlineKeyboardButton(text="⏭ Skip", callback_data="tour:skip")]
                ])
            )
        except Exception:
            pass

    await show_main_menu(callback.message, session, texts, buttons)
    await callback.answer()


@router.callback_query(F.data == "rules_decline")
async def rules_decline_handler(callback: CallbackQuery, texts, buttons):
    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.message.answer(texts.RULES_DECLINED_MESSAGE)
    await callback.answer()


@router.callback_query(F.data == "back_main")
async def back_to_main_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, texts, buttons):
    await state.clear()
    try:
        await callback.message.delete()
    except Exception:
        pass

    main_photo = resolve_bot_photo("main", fallback_path="media/main.jpg")
    main_menu_counts = await MenuCountService.get_main_menu_counts(session)
    menu_categories = await MenuCategoryService.get_keyboard_payload(
        session,
        language="en",
        active_only=True,
    )
    try:
        if main_photo:
            await callback.bot.send_photo(
                chat_id=callback.message.chat.id,
                photo=main_photo,
                caption=texts.MAIN_MENU_TEXT,
                reply_markup=main_menu_keyboard(menu_categories, main_menu_counts)
            )
        else:
            raise RuntimeError("Main photo is not configured")
    except Exception:
        await callback.bot.send_message(
            chat_id=callback.message.chat.id,
            text=texts.MAIN_MENU_TEXT,
            reply_markup=main_menu_keyboard(menu_categories, main_menu_counts)
        )

    await callback.answer()


@router.callback_query(F.data.startswith("reorder:"))
async def reorder_handler(callback: CallbackQuery, session: AsyncSession, texts, buttons):
    """Route user back to the service category for reorder"""
    category = callback.data.split(":")[1]

    CATEGORY_BUTTONS = {
        "lookup": buttons.SEARCH,
        "credit": buttons.CREDIT_REPORTS,
        "fullz": buttons.PROS_FULLZ,
        "documents": buttons.DOCUMENTS,
        "banks": buttons.BANKS,
        "cc": buttons.CC,
        "esim": buttons.ESIM,
        "accounts": buttons.SUBSCRIPTIONS_ACCOUNTS,
        "addinfo": buttons.ADD_INFO_CR,
        "education": buttons.EDUCATION,
    }

    button_text = CATEGORY_BUTTONS.get(category)
    if not button_text:
        await callback.answer()
        return

    try:
        await callback.message.delete()
    except Exception:
        pass

    fake_message = callback.message
    fake_message.text = button_text
    fake_message.from_user = callback.from_user

    from aiogram.types import Chat
    if not fake_message.chat:
        fake_message.chat = Chat(id=callback.from_user.id, type="private")

    menu_categories = await MenuCategoryService.get_keyboard_payload(
        session,
        language="en",
        active_only=True,
    )
    await callback.bot.send_message(
        chat_id=callback.message.chat.id,
        text=f"🔄 {button_text}",
        reply_markup=main_menu_keyboard(menu_categories)
    )
    await callback.answer()


@router.message(Command("menu"))
async def menu_command_handler(message: Message, session: AsyncSession, texts, buttons):
    await show_main_menu(message, session, texts, buttons)


async def show_rules_acceptance(message: Message, texts, buttons):
    rules_photo = resolve_bot_photo("rules", "правила", fallback_path="media/правила.jpg")
    try:
        if rules_photo:
            await message.answer_photo(
                photo=rules_photo,
                caption=texts.RULES_ACCEPT_PROMPT,
                parse_mode=None
            )
    except Exception:
        pass

    await message.answer(
        texts.RULES_TEXT,
        reply_markup=rules_accept_keyboard(buttons),
        parse_mode="Markdown"
    )


async def show_main_menu(message: Message, session: AsyncSession, texts, buttons):
    main_photo = resolve_bot_photo("main", fallback_path="media/main.jpg")
    main_menu_counts = await MenuCountService.get_main_menu_counts(session)
    menu_categories = await MenuCategoryService.get_keyboard_payload(
        session,
        language="en",
        active_only=True,
    )
    try:
        if main_photo:
            await message.answer_photo(
                photo=main_photo,
                caption=texts.MAIN_MENU_TEXT,
                reply_markup=main_menu_keyboard(menu_categories, main_menu_counts)
            )
        else:
            raise RuntimeError("Main photo is not configured")
    except Exception:
        await message.answer(
            texts.MAIN_MENU_TEXT,
            reply_markup=main_menu_keyboard(menu_categories, main_menu_counts)
        )
