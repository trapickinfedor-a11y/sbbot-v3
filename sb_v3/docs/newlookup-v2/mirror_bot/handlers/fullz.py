import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal
from mirror_bot.keyboards.inline import InlineKeyboardMarkup, InlineKeyboardButton, confirm_keyboard
from mirror_bot.states.fullz import FullzStates
from mirror_bot.states.order import RandomFullzStates
from mirror_bot.constants.prices import ServicePrices, BulkDiscounts
from mirror_bot.constants.service_eta import ServiceETA
from mirror_bot.constants.states_data import US_STATES, STATES_PAGES
from mirror_bot.services.order_service import OrderService
from mirror_bot.services.checkout_coupon_service import CheckoutCouponService
from mirror_bot.services.user_service import UserService
from mirror_bot.middlewares.language import LanguageHelper
from mirror_bot.constants.language_loader import get_texts
from mirror_bot.constants.buttons_en import ButtonTexts
from mirror_bot.utils.message_utils import safe_edit_message
from mirror_bot.utils.product_translations import ProductTranslations
from mirror_bot.services.menu_counts_service import MenuCountService
from mirror_bot.utils.media_library import resolve_bot_photo

logger = logging.getLogger(__name__)
router = Router()

def fullz_main_keyboard(buttons, counts=None):
    """Клавиатура главного меню FULLZ"""
    counts = counts or {}
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=ButtonTexts.with_count(buttons.FULLZ_PERSONAL, counts.get("personal")), callback_data="fullz_personal")],
        [InlineKeyboardButton(text=ButtonTexts.with_count(buttons.FULLZ_BUSINESS, counts.get("business")), callback_data="fullz_business")],
        [InlineKeyboardButton(text=buttons.BACK, callback_data="back_main")]
    ])


FIXED_PROFILES = [
    {"code": "700plus", "price_attr": "FULLZ_700_PLUS"},
    {"code": "800plus", "price_attr": "FULLZ_800_PLUS_PROFILE"},
    {"code": "under18", "price_attr": "FULLZ_UNDER_18"},
    {"code": "immigrant", "price_attr": "FULLZ_IMMIGRANT"},
    {"code": "zero_bank", "price_attr": "FULLZ_ZERO_BANK"},
]

FIXED_PROFILE_BUTTON_ATTR = {
    "700plus": "FULLZ_700_PLUS",
    "800plus": "FULLZ_800_PLUS",
    "under18": "FULLZ_UNDER_18",
    "immigrant": "FULLZ_IMMIGRANT",
    "zero_bank": "FULLZ_ZERO_BANK",
}

FIXED_PROFILE_SERVICE_NAME = {
    "700plus": "fullz_700plus",
    "800plus": "fullz_800plus",
    "under18": "fullz_under18",
    "immigrant": "fullz_immigrant",
    "zero_bank": "fullz_zero_bank",
}


def fullz_personal_profiles_keyboard(buttons, counts=None):
    """Клавиатура выбора профиля Personal FULLZ — фиксированные позиции"""
    counts = counts or {}
    rows = [
        [InlineKeyboardButton(text=buttons.FULLZ_WITH_CS_CR, callback_data="fullz_prof:cscr")],
    ]
    for prof in FIXED_PROFILES:
        btn_attr = FIXED_PROFILE_BUTTON_ATTR[prof["code"]]
        label = getattr(buttons, btn_attr, prof["code"].upper())
        price = getattr(ServicePrices, prof["price_attr"])
        rows.append([InlineKeyboardButton(
            text=f"{label} — ${price}",
            callback_data=f"fullz_fixed:{prof['code']}",
        )])
    rows.append([InlineKeyboardButton(text=buttons.FULLZ_RANDOM, callback_data="fullz_prof:random")])
    rows.append([InlineKeyboardButton(text=buttons.FULLZ_SUPPORT, callback_data="fullz_support")])
    rows.append([InlineKeyboardButton(text=buttons.BACK, callback_data="fullz_back_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def fullz_states_keyboard(page=0, button_texts=None):
    """
    Создает клавиатуру с штатами с пагинацией.
    page: номер страницы (0-3)
    button_texts: объект с текстами кнопок (опционально для обратной совместимости)
    """
    keyboard_buttons = []
    surcharge = ServicePrices.FULLZ_STATE_SURCHARGE
    keyboard_buttons.append([InlineKeyboardButton(text="🎲 ANY STATE — $0", callback_data="fullz_state:ANY")])
    
    current_page = STATES_PAGES[page]
    
    states_row = []
    for i, (name, code) in enumerate(current_page, 1):
        states_row.append(InlineKeyboardButton(text=f"{name}, {code} +${surcharge:.0f}", callback_data=f"fullz_state:{code}"))
        if i % 3 == 0:
            keyboard_buttons.append(states_row)
            states_row = []
    if states_row:
        keyboard_buttons.append(states_row)
    
    # Навигация
    nav_row = []
    if button_texts:
        if page > 0:
            nav_row.append(InlineKeyboardButton(text=button_texts.PREV, callback_data=f"fullz_state_page:{page-1}"))
        nav_row.append(InlineKeyboardButton(text=f"📄 {page+1}/4", callback_data="fullz_state_noop"))
        if page < 3:
            nav_row.append(InlineKeyboardButton(text=button_texts.NEXT, callback_data=f"fullz_state_page:{page+1}"))
    keyboard_buttons.append(nav_row)
    
    back_text = button_texts.BACK_FULLZ if button_texts and hasattr(button_texts, 'BACK_FULLZ') else "⬅️ Back"
    keyboard_buttons.append([InlineKeyboardButton(text=back_text, callback_data="fullz_back_prof")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)


def fullz_company_type_keyboard(buttons):
    """Клавиатура выбора типа компании (цены из prices.py)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🏢 LLC — +${ServicePrices.FULLZ_BIZ_LLC}", callback_data="fullz_company:llc")],
        [InlineKeyboardButton(text=f"🏛️ CORP — +${ServicePrices.FULLZ_BIZ_CORP}", callback_data="fullz_company:corp")],
        [InlineKeyboardButton(text="👤 Sole Proprietor — $0", callback_data="fullz_company:sole")],
        [InlineKeyboardButton(text=buttons.BACK_FULLZ_SHORT, callback_data="fullz_back_state")]
    ])

def fullz_ceo_cs_keyboard(buttons):
    """Клавиатура выбора CS CEO (цены из prices.py)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"⭐ 800+ — +${ServicePrices.FULLZ_CS_800_PLUS}", callback_data="fullz_cs:800+")],
        [InlineKeyboardButton(text=f"✨ 700+ — +${ServicePrices.FULLZ_CS_700_PLUS}", callback_data="fullz_cs:700+")],
        [InlineKeyboardButton(text="📊 ANY — $0", callback_data="fullz_cs:any")],
        [InlineKeyboardButton(text=buttons.BACK_FULLZ_SHORT, callback_data="fullz_back_company")]
    ])

def fullz_loan_size_keyboard(buttons):
    """Клавиатура выбора размера займа (цены из prices.py)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"💰 $25k–$200k — +${ServicePrices.FULLZ_BIZ_LOAN_25_200}", callback_data="fullz_loan:25k-200k")],
        [InlineKeyboardButton(text=f"💰 $200k–$500k — +${ServicePrices.FULLZ_BIZ_LOAN_200_500}", callback_data="fullz_loan:200k-500k")],
        [InlineKeyboardButton(text=f"💰 $500k+ — +${ServicePrices.FULLZ_BIZ_LOAN_500_PLUS}", callback_data="fullz_loan:500k+")],
        [InlineKeyboardButton(text="📊 Any — $0", callback_data="fullz_loan:any")],
        [InlineKeyboardButton(text=buttons.BACK_FULLZ_SHORT, callback_data="fullz_back_company")]
    ])

def fullz_business_cs_keyboard(buttons):
    """Клавиатура выбора Business CS (цены из prices.py)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"⭐ 800+ — +${ServicePrices.FULLZ_CS_800_PLUS}", callback_data="fullz_cs:800+")],
        [InlineKeyboardButton(text=f"✨ 700+ — +${ServicePrices.FULLZ_CS_700_PLUS}", callback_data="fullz_cs:700+")],
        [InlineKeyboardButton(text=f"💠 500+ — ${ServicePrices.FULLZ_CS_500_PLUS}", callback_data="fullz_cs:500+")],
        [InlineKeyboardButton(text="🔘 Any — $0", callback_data="fullz_cs:any")],
        [InlineKeyboardButton(text=buttons.BACK_FULLZ_SHORT, callback_data="fullz_back_loan")]
    ])

def fullz_business_report_keyboard(buttons):
    """Клавиатура выбора отчёта Business (цены из prices.py)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"💼 Basic — ${ServicePrices.FULLZ_REPORT_BASIC}", callback_data="fullz_report:basic")],
        [InlineKeyboardButton(text=f"📘 With CR — +${ServicePrices.FULLZ_BIZ_REPORT_CR}", callback_data="fullz_report:cr")],
        [InlineKeyboardButton(text=f"🪪 CR & DL — +${ServicePrices.FULLZ_REPORT_CR_DL}", callback_data="fullz_report:cr_dl")],
        [InlineKeyboardButton(text=f"🛰️ CR, DL & MVR — +${ServicePrices.FULLZ_REPORT_CR_DL_MVR}", callback_data="fullz_report:cr_dl_mvr")],
        [InlineKeyboardButton(text=f"🏁 CR, DL & FULL MVR — +${ServicePrices.FULLZ_REPORT_CR_DL_FULLMVR}", callback_data="fullz_report:cr_dl_fullmvr")],
        [InlineKeyboardButton(text=buttons.BACK_FULLZ_SHORT, callback_data="fullz_back_cs")]
    ])

def fullz_business_quantity_keyboard(buttons):
    """Клавиатура выбора количества Business FULLZ (динамические скидки из prices.py)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1", callback_data="fullz_qty:1"),
         InlineKeyboardButton(text=f"3 (-{BulkDiscounts.ESIM_QTY_3}%)", callback_data="fullz_qty:3"),
         InlineKeyboardButton(text=f"5 (-{BulkDiscounts.ESIM_QTY_5}%)", callback_data="fullz_qty:5")],
        [InlineKeyboardButton(text=f"10 (-{BulkDiscounts.ESIM_QTY_10}%)", callback_data="fullz_qty:10"),
         InlineKeyboardButton(text=buttons.CUSTOM_QUANTITY, callback_data="fullz_qty:custom")],
        [InlineKeyboardButton(text=buttons.BACK_FULLZ_SHORT, callback_data="fullz_back_report")]
    ])

def fullz_business_final_keyboard(buttons):
    """Клавиатура финального шага Business FULLZ (цены из prices.py)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{buttons.TEXT_ORDER} — ${ServicePrices.FULLZ_BIZ_BASE}", callback_data="fullz_business:text")],
        [InlineKeyboardButton(text=buttons.CONFIRM_BUSINESS, callback_data="fullz_business:confirm")],
        [InlineKeyboardButton(text=buttons.BUY_ANY, callback_data="fullz_business:buy_any")],
        [InlineKeyboardButton(text=buttons.CUSTOMISE, callback_data="fullz_business:customise")],
        [InlineKeyboardButton(text=buttons.BACK, callback_data="fullz_back_loan")]
    ])

def fullz_cs_keyboard(buttons):
    """Клавиатура выбора Credit Score (цены из prices.py)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"⭐ 800+ — +${ServicePrices.FULLZ_CS_800_PLUS}", callback_data="fullz_cs:800+")],
        [InlineKeyboardButton(text=f"✨ 700+ — +${ServicePrices.FULLZ_CS_700_PLUS}", callback_data="fullz_cs:700+")],
        [InlineKeyboardButton(text=f"💠 500+ — ${ServicePrices.FULLZ_CS_500_PLUS}", callback_data="fullz_cs:500+")],
        [InlineKeyboardButton(text="🔘 Any — $0", callback_data="fullz_cs:any")],
        [InlineKeyboardButton(text=buttons.BACK_FULLZ, callback_data="fullz_back_state")]
    ])


def fullz_age_keyboard(buttons):
    """Клавиатура выбора возраста (цены из prices.py)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🧒 18–25 — +${ServicePrices.FULLZ_AGE_18_25}", callback_data="fullz_age:18-25")],
        [InlineKeyboardButton(text=f"👨 26–35 — +${ServicePrices.FULLZ_AGE_26_35}", callback_data="fullz_age:26-35")],
        [InlineKeyboardButton(text=f"🧓 36+ — +${ServicePrices.FULLZ_AGE_36_PLUS}", callback_data="fullz_age:36+")],
        [InlineKeyboardButton(text="🎲 Any — $0", callback_data="fullz_age:any")],
        [InlineKeyboardButton(text=buttons.BACK_FULLZ, callback_data="fullz_back_cs")]
    ])


def fullz_gender_keyboard(buttons):
    """Клавиатура выбора пола (цены из prices.py)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"👨 Male — +${ServicePrices.FULLZ_GENDER_MALE}", callback_data="fullz_gender:male")],
        [InlineKeyboardButton(text=f"👩 Female — +${ServicePrices.FULLZ_GENDER_FEMALE}", callback_data="fullz_gender:female")],
        [InlineKeyboardButton(text="🎲 Any — $0", callback_data="fullz_gender:any")],
        [InlineKeyboardButton(text=buttons.BACK_FULLZ, callback_data="fullz_back_age")]
    ])


def fullz_carrier_exclusion_keyboard(buttons):
    """Клавиатура исключения оператора — +$10"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🚫 Without Verizon — +${ServicePrices.FULLZ_NO_CARRIER}", callback_data="fullz_carrier:verizon")],
        [InlineKeyboardButton(text=f"🚫 Without AT&T — +${ServicePrices.FULLZ_NO_CARRIER}", callback_data="fullz_carrier:att")],
        [InlineKeyboardButton(text=f"🚫 Without T-Mobile — +${ServicePrices.FULLZ_NO_CARRIER}", callback_data="fullz_carrier:tmobile")],
        [InlineKeyboardButton(text="✅ Any Carrier — $0", callback_data="fullz_carrier:any")],
        [InlineKeyboardButton(text=buttons.BACK_FULLZ, callback_data="fullz_back_gender")]
    ])


def fullz_bank_exclusion_keyboard(buttons):
    """Клавиатура исключения банка — +$10-15"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🚫 Without Chase — +${ServicePrices.FULLZ_NO_BANK_SINGLE}", callback_data="fullz_bank:chase")],
        [InlineKeyboardButton(text=f"🚫 Without Citi — +${ServicePrices.FULLZ_NO_BANK_SINGLE}", callback_data="fullz_bank:citi")],
        [InlineKeyboardButton(text=f"🚫 Without Capital One — +${ServicePrices.FULLZ_NO_BANK_SINGLE}", callback_data="fullz_bank:cap1")],
        [InlineKeyboardButton(text=f"🚫 Without Wells Fargo — +${ServicePrices.FULLZ_NO_BANK_SINGLE}", callback_data="fullz_bank:wells")],
        [InlineKeyboardButton(text=f"🚫 Without TD Bank — +${ServicePrices.FULLZ_NO_BANK_SINGLE}", callback_data="fullz_bank:td")],
        [InlineKeyboardButton(text=f"🚫 Without Any Bank — +${ServicePrices.FULLZ_NO_BANK_ANY}", callback_data="fullz_bank:any_bank")],
        [InlineKeyboardButton(text="✅ Any Bank — $0", callback_data="fullz_bank:any")],
        [InlineKeyboardButton(text=buttons.BACK_FULLZ, callback_data="fullz_back_carrier")]
    ])


def fullz_report_keyboard(buttons):
    """Клавиатура выбора отчёта Personal FULLZ (цены из prices.py)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"💼 Basic — ${ServicePrices.FULLZ_REPORT_BASIC}", callback_data="fullz_report:basic")],
        [InlineKeyboardButton(text=f"📘 With CR — +${ServicePrices.FULLZ_REPORT_CR}", callback_data="fullz_report:cr")],
        [InlineKeyboardButton(text=f"🪪 CR & DL — +${ServicePrices.FULLZ_REPORT_CR_DL}", callback_data="fullz_report:cr_dl")],
        [InlineKeyboardButton(text=f"🛰️ CR, DL & MVR — +${ServicePrices.FULLZ_REPORT_CR_DL_MVR}", callback_data="fullz_report:cr_dl_mvr")],
        [InlineKeyboardButton(text=f"🏁 CR, DL & FULL MVR — +${ServicePrices.FULLZ_REPORT_CR_DL_FULLMVR}", callback_data="fullz_report:cr_dl_fullmvr")],
        [InlineKeyboardButton(text=buttons.BACK_FULLZ, callback_data="fullz_back_bank")]
    ])


def fullz_quantity_keyboard(buttons):
    """Клавиатура выбора количества FULLZ (динамические скидки из prices.py)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1", callback_data="fullz_qty:1"),
         InlineKeyboardButton(text=f"3 (-{BulkDiscounts.ESIM_QTY_3}%)", callback_data="fullz_qty:3"),
         InlineKeyboardButton(text=f"5 (-{BulkDiscounts.ESIM_QTY_5}%)", callback_data="fullz_qty:5")],
        [InlineKeyboardButton(text=f"10 (-{BulkDiscounts.ESIM_QTY_10}%)", callback_data="fullz_qty:10"),
         InlineKeyboardButton(text=buttons.CUSTOM_QUANTITY, callback_data="fullz_qty:custom")],
        [InlineKeyboardButton(text=buttons.BACK_FULLZ, callback_data="fullz_back_report")]
    ])


@router.message(F.text.func(lambda value: ButtonTexts.matches("PROS_FULLZ", value)))
async def fullz_main_handler(message: Message, state: FSMContext, session: AsyncSession, texts, buttons):
    await state.clear()
    counts = await MenuCountService.get_fullz_counts(session)
    fullz_photo = resolve_bot_photo("fullz", fallback_path="media/Fullz.jpg")
    try:
        if fullz_photo:
            await message.answer_photo(
                photo=fullz_photo,
                caption=texts.FULLZ_MAIN,
                reply_markup=fullz_main_keyboard(buttons, {"personal": counts["personal_total"], "business": counts["business_total"]})
            )
        else:
            raise RuntimeError("Fullz photo is not configured")
    except Exception:
        await message.answer(
            texts.FULLZ_MAIN,
            reply_markup=fullz_main_keyboard(buttons, {"personal": counts["personal_total"], "business": counts["business_total"]}),
        )


@router.callback_query(F.data == "fullz_personal")
async def fullz_personal_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, texts, buttons):
    await state.set_state(FullzStates.select_type)
    await state.update_data(fullz_type="personal", base_price=ServicePrices.FULLZ_BASE)
    await safe_edit_message(callback,
        texts.FULLZ_PERSONAL_PROFILES,
        reply_markup=fullz_personal_profiles_keyboard(buttons)
    )
    await callback.answer()


@router.callback_query(F.data == "fullz_business")
async def fullz_business_handler(callback: CallbackQuery, state: FSMContext, texts, buttons):
    await state.set_state(FullzStates.select_state)
    await state.update_data(fullz_type="business", base_price=ServicePrices.FULLZ_BIZ_BASE)
    await safe_edit_message(callback,
        texts.FULLZ_BUSINESS_MAIN,
        reply_markup=fullz_states_keyboard(page=0, button_texts=buttons)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("fullz_prof:"))
async def fullz_profile_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, mirror_bot_id: int, texts, buttons):
    profile = callback.data.split(":")[1]

    if profile == "random":
        await handle_random_fullz_order(callback, state, session, mirror_bot_id, texts, buttons)
        return

    # WITH CS/CR — custom order flow
    if profile == "cscr":
        await state.update_data(profile=profile, fullz_type="personal_cs")
        await state.set_state(FullzStates.select_state)
        await safe_edit_message(callback,
            texts.FULLZ_PROFILE_SELECT_STATE.format(profile="CUSTOM CS/CR"),
            reply_markup=fullz_states_keyboard(page=0, button_texts=buttons)
        )
        await callback.answer()
        return

    await callback.answer()


@router.callback_query(F.data.startswith("fullz_state:"))
async def fullz_state_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, mirror_bot_id: int, texts, buttons):
    selected_state = callback.data.split(":")[1]
    await state.update_data(state=selected_state)

    data = await state.get_data()
    fullz_type = data.get("fullz_type", "personal")

    # Fixed profiles (700+, 800+, etc.) → order + upload
    if data.get("fixed_profile"):
        # Reuse the fixed-state handler logic inline
        callback.data = f"fullz_fixed_state:{selected_state}"
        await fullz_fixed_state_handler(callback, state, session, mirror_bot_id, texts, buttons)
        return

    if fullz_type == "business":
        await state.set_state(FullzStates.select_company_type)
        await safe_edit_message(callback,
            texts.FULLZ_STATE_SELECT_COMPANY.format(state=selected_state),
            reply_markup=fullz_company_type_keyboard(buttons)
        )
    else:
        await state.set_state(FullzStates.select_credit_score)
        await safe_edit_message(callback,
            texts.FULLZ_STATE_SELECT_CS.format(state=selected_state),
            reply_markup=fullz_cs_keyboard(buttons)
        )
    await callback.answer()


@router.callback_query(F.data.startswith("fullz_state_page:"))
async def fullz_state_page_handler(callback: CallbackQuery, state: FSMContext, texts, buttons):
    """Обработчик навигации по страницам штатов"""
    page = int(callback.data.split(":")[1])
    data = await state.get_data()
    
    # Определяем текст в зависимости от типа fullz
    if data.get("fullz_type") == "business":
        text = texts.FULLZ_BUSINESS_SELECT_STATE
    elif "profile" in data:
        profile = data.get("profile")
        text = texts.FULLZ_PROFILE_SELECT_STATE.format(profile=profile.upper())
    else:
        text = texts.FULLZ_SELECT_STATE
    
    await safe_edit_message(callback,
        text,
        reply_markup=fullz_states_keyboard(page=page, button_texts=buttons)
    )
    await callback.answer()


@router.callback_query(F.data == "fullz_state_noop")
async def fullz_state_noop_handler(callback: CallbackQuery):
    """Заглушка для кнопки с номером страницы"""
    await callback.answer()


# ==================== FIXED PROFILE ORDERS ====================


@router.callback_query(F.data.startswith("fullz_fixed:"))
async def fullz_fixed_profile_handler(callback: CallbackQuery, state: FSMContext, texts, buttons):
    """Фиксированный профиль → выбор штата (потом order+upload)"""
    profile_code = callback.data.split(":")[1]

    prof = next((p for p in FIXED_PROFILES if p["code"] == profile_code), None)
    if not prof:
        await callback.answer("Unknown profile", show_alert=True)
        return

    btn_attr = FIXED_PROFILE_BUTTON_ATTR[profile_code]
    label = getattr(buttons, btn_attr, profile_code.upper())

    await state.update_data(
        fullz_type="personal",
        profile=profile_code,
        fixed_profile=True,
    )
    await state.set_state(FullzStates.select_state)
    await safe_edit_message(callback,
        texts.FULLZ_PROFILE_SELECT_STATE.format(profile=label),
        reply_markup=fullz_states_keyboard(page=0, button_texts=buttons)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("fullz_fixed_state:"))
async def fullz_fixed_state_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, mirror_bot_id: int, texts, buttons):
    """После выбора штата — показываем экран выбора количества с инфо о наличии"""
    selected_state = callback.data.split(":")[1]
    await state.update_data(state=selected_state)
    data = await state.get_data()
    profile_code = data.get("profile", "")

    service_name = FIXED_PROFILE_SERVICE_NAME.get(profile_code, f"fullz_{profile_code}")
    prof = next((p for p in FIXED_PROFILES if p["code"] == profile_code), None)
    if not prof:
        await callback.answer("Unknown profile", show_alert=True)
        return

    from mirror_bot.services.product_service import ProductService
    products_data = await ProductService.get_products_by_category_service_state(
        session=session, category="pros_fullz", service=service_name,
        state=selected_state, page=1, per_page=1,
    )
    stock = products_data["total"]

    price = getattr(ServicePrices, prof["price_attr"])
    if selected_state != "ANY":
        price = price + ServicePrices.FULLZ_STATE_SURCHARGE
    btn_attr = FIXED_PROFILE_BUTTON_ATTR[profile_code]
    label = getattr(buttons, btn_attr, profile_code.upper())
    state_label = selected_state if selected_state != "ANY" else "ANY STATE"

    await state.update_data(service_name=service_name, price=float(price), fixed_stock=stock)
    await state.set_state(FullzStates.select_fixed_quantity)

    stock_line = f"📊 **In stock:** {stock}" if stock > 0 else "📊 **In stock:** 0 (worker order)"
    eta_instant = ServiceETA.FULLZ_INSTANT if stock > 0 else ""
    eta_worker = ServiceETA.get_eta(service_name)

    text = (
        f"📦 **{label} — {state_label}**\n"
        f"💰 Price per item: ${price}\n\n"
        f"{stock_line}\n"
    )
    if stock > 0:
        text += f"⚡ In-stock items: **{eta_instant}**\n"
    text += f"⏱ Worker order items: **{eta_worker}**\n\n"
    text += "🔢 **Select quantity:**"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="1", callback_data="fullz_fqty:1"),
            InlineKeyboardButton(text="3", callback_data="fullz_fqty:3"),
            InlineKeyboardButton(text="5", callback_data="fullz_fqty:5"),
        ],
        [
            InlineKeyboardButton(text="10", callback_data="fullz_fqty:10"),
            InlineKeyboardButton(text=getattr(buttons, 'CUSTOM_QUANTITY', '✏️ Custom'), callback_data="fullz_fqty:custom"),
        ],
        [InlineKeyboardButton(text=buttons.BACK_FULLZ, callback_data="fullz_back_state")],
    ])

    await safe_edit_message(callback, text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "fullz_support")
async def fullz_support_handler(callback: CallbackQuery, state: FSMContext, texts, buttons):
    """Показ описания FULLZ Support с контактом продавца"""
    await safe_edit_message(callback,
        texts.FULLZ_SUPPORT_INFO,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=buttons.BACK, callback_data="fullz_back_prof")]
        ]),
        parse_mode="Markdown"
    )
    await callback.answer()


# ==================== FIXED PROFILE QTY + SPLIT PURCHASE ====================


@router.callback_query(F.data.startswith("fullz_fqty:"))
async def fullz_fixed_qty_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, mirror_bot_id: int, texts, buttons):
    """Выбрано количество для фиксированного профиля — показываем подтверждение со split"""
    qty_str = callback.data.split(":")[1]

    if qty_str == "custom":
        await state.set_state(FullzStates.waiting_fixed_custom_qty)
        await safe_edit_message(callback, getattr(texts, 'ENTER_CUSTOM_QUANTITY', "Enter quantity (1-100):"))
        await callback.answer()
        return

    quantity = int(qty_str)
    await _show_fixed_confirmation(callback, state, session, mirror_bot_id, texts, buttons, quantity)
    await callback.answer()


@router.message(FullzStates.waiting_fixed_custom_qty, F.text)
async def fullz_fixed_custom_qty_input(message: Message, state: FSMContext, session: AsyncSession, mirror_bot_id: int, texts, buttons):
    """Ввод custom quantity для фиксированного профиля"""
    try:
        quantity = int(message.text.strip())
        if quantity < 1 or quantity > 100:
            await message.answer(getattr(texts, 'INVALID_QUANTITY', "❌ Enter a number between 1 and 100"))
            return
        await _show_fixed_confirmation(message, state, session, mirror_bot_id, texts, buttons, quantity, is_message=True)
    except ValueError:
        await message.answer(getattr(texts, 'INVALID_QUANTITY', "❌ Enter a valid number"))


async def _show_fixed_confirmation(event, state, session, mirror_bot_id, texts, buttons, quantity, is_message=False):
    """Формирует подтверждение split-покупки (catalog + worker)"""
    data = await state.get_data()
    profile_code = data.get("profile", "")
    selected_state = data.get("state", "ANY")
    service_name = data.get("service_name", "")
    unit_price = Decimal(str(data.get("price", 0)))

    from mirror_bot.services.product_service import ProductService
    fresh = await ProductService.get_products_by_category_service_state(
        session=session, category="pros_fullz", service=service_name,
        state=selected_state, page=1, per_page=1,
    )
    stock = fresh["total"]
    await state.update_data(fixed_stock=stock)

    if profile_code == "random":
        label = getattr(buttons, 'FULLZ_RANDOM', '🎲 RANDOM')
    else:
        btn_attr = FIXED_PROFILE_BUTTON_ATTR.get(profile_code, "")
        label = getattr(buttons, btn_attr, profile_code.upper()) if btn_attr else profile_code.upper()
    state_label = selected_state if selected_state != "ANY" else "ANY STATE"

    from_catalog = min(quantity, stock)
    from_worker = quantity - from_catalog
    
    discount = ServicePrices.get_bulk_discount(quantity)
    total_price = unit_price * quantity * (1 - discount)

    user_id = event.from_user.id
    user = await UserService.get_user(session, user_id, mirror_bot_id)
    if not user:
        msg = texts.USER_NOT_FOUND
        if is_message:
            await event.answer(msg)
        else:
            await safe_edit_message(event, msg)
        return

    if user.balance < total_price:
        msg = texts.INSUFFICIENT_BALANCE.format(balance=user.balance, price=total_price)
        if is_message:
            await event.answer(msg)
        else:
            await safe_edit_message(event, msg)
        return

    new_balance = user.balance - total_price

    lines = [
        f"📦 **{label} — {state_label}**\n",
        f"🔢 **Quantity:** {quantity}",
        f"💰 **Price per item:** ${unit_price}",
        f"💵 **Total:** ${total_price}\n",
    ]
    if from_catalog > 0:
        lines.append(f"⚡ **From catalog (Instant):** {from_catalog}")
    if from_worker > 0:
        eta_worker = ServiceETA.get_eta(service_name)
        lines.append(f"⏱ **Worker order ({eta_worker}):** {from_worker}")
    lines.append(f"\n📊 Balance: ${user.balance:.2f}")
    lines.append(f"📉 New balance: ${new_balance:.2f}")
    lines.append(f"\n❓ **Confirm purchase?**")

    confirmation_text = "\n".join(lines)

    await state.update_data(
        quantity=quantity,
        total_price=float(total_price),
        fixed_from_catalog=from_catalog,
        fixed_from_worker=from_worker,
    )
    await state.set_state(FullzStates.fixed_confirmation)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=getattr(buttons, 'CONFIRM_PAY', '✅ Confirm & Pay'), callback_data="confirm_yes_fixed")],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="confirm_no_fixed")],
    ])

    if is_message:
        await event.answer(confirmation_text, reply_markup=kb, parse_mode="Markdown")
    else:
        await safe_edit_message(event, confirmation_text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data == "confirm_yes_fixed", FullzStates.fixed_confirmation)
async def fullz_fixed_confirm_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, mirror_bot_id: int, texts, buttons):
    """Выполняем split-покупку: catalog + worker order"""
    data = await state.get_data()
    profile_code = data.get("profile", "")
    selected_state = data.get("state", "ANY")
    service_name = data.get("service_name", "")
    unit_price = Decimal(str(data.get("price", 0)))
    quantity = data.get("quantity", 1)
    from_catalog = data.get("fixed_from_catalog", 0)
    from_worker = data.get("fixed_from_worker", 0)
    total_price = Decimal(str(data.get("total_price", 0)))

    if profile_code == "random":
        label = getattr(buttons, 'FULLZ_RANDOM', '🎲 RANDOM')
    else:
        btn_attr = FIXED_PROFILE_BUTTON_ATTR.get(profile_code, "")
        label = getattr(buttons, btn_attr, profile_code.upper()) if btn_attr else profile_code.upper()

    try:
        user = await UserService.get_user(session, callback.from_user.id, mirror_bot_id)
        if not user or user.balance < total_price:
            await callback.answer(getattr(texts, 'INSUFFICIENT_BALANCE_ALERT', "Insufficient balance"), show_alert=True)
            return

        catalog_results = []
        worker_order = None
        actual_catalog_count = 0

        # 1) Buy from catalog
        if from_catalog > 0:
            from mirror_bot.services.product_service import ProductService
            catalog_results_data = await ProductService.purchase_multiple_by_criteria(
                session=session,
                category="pros_fullz",
                service=service_name,
                state=selected_state,
                quantity=from_catalog,
                user_id=callback.from_user.id,
                mirror_bot_id=mirror_bot_id,
                override_unit_price=unit_price,
            )
            catalog_results = catalog_results_data.get("purchased", [])
            actual_catalog_count = len(catalog_results)

        # If some catalog items failed (e.g. sold between check and buy),
        # increase worker order by the shortfall
        actual_from_worker = from_worker + (from_catalog - actual_catalog_count)

        # 2) Create worker order for remainder
        if actual_from_worker > 0:
            worker_price = unit_price * actual_from_worker
            success = await OrderService.deduct_balance(session, callback.from_user.id, worker_price)
            if success:
                worker_order = await OrderService.create_order(
                    session,
                    user_id=callback.from_user.id,
                    mirror_bot_id=mirror_bot_id,
                    category="fullz",
                    service_name=service_name,
                    input_data={
                        "profile": profile_code,
                        "state": selected_state,
                        "quantity": actual_from_worker,
                        "fullz_type": "personal",
                    },
                    price=worker_price,
                    original_price=worker_price,
                )

        if not catalog_results and not worker_order:
            await callback.answer("❌ Order failed — please try again.", show_alert=True)
            return

        user = await UserService.get_user(session, callback.from_user.id, mirror_bot_id)
        balance = user.balance if user else Decimal("0")

        lines = [f"✅ **Order Complete — {label}**\n"]
        if catalog_results:
            lines.append(f"⚡ **Instant delivery:** {actual_catalog_count} items")
            lines.append(f"   Purchase IDs: {', '.join(f'#{pid}' for pid in catalog_results)}")
        if worker_order:
            eta = ServiceETA.get_eta(service_name)
            lines.append(f"⏱ **Worker order:** {actual_from_worker} items (ETA: {eta})")
            lines.append(f"   Order ID: #{worker_order.id}")
        lines.append(f"\n💳 **Balance:** ${balance:.2f}")

        await safe_edit_message(callback, "\n".join(lines), parse_mode="Markdown")
        await state.clear()
        await callback.answer(getattr(texts, 'ORDER_CREATED_SUCCESS', "✅ Order created!"))

    except Exception as e:
        logger.error(f"Error in fixed split purchase: {e}", exc_info=True)
        await callback.answer("Error processing order. Please contact support.", show_alert=True)


@router.callback_query(F.data == "confirm_no_fixed", FullzStates.fixed_confirmation)
async def fullz_fixed_cancel_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, texts, buttons):
    await state.clear()
    counts = await MenuCountService.get_fullz_counts(session)
    await safe_edit_message(callback,
        getattr(texts, 'ORDER_CANCELLED', '❌ Order cancelled.'),
        reply_markup=fullz_main_keyboard(buttons, {"personal": counts["personal_total"], "business": counts["business_total"]}),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("fullz_company:"))
async def fullz_company_handler(callback: CallbackQuery, state: FSMContext, texts, buttons):
    company_type = callback.data.split(":")[1]
    await state.update_data(company_type=company_type)
    
    # Переходим к выбору Loan Size
    await state.set_state(FullzStates.select_loan_size)
    await safe_edit_message(callback,
        texts.FULLZ_COMPANY_SELECT_LOAN.format(company_type=company_type.upper()),
        reply_markup=fullz_loan_size_keyboard(buttons)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("fullz_cs:"))
async def fullz_cs_handler(callback: CallbackQuery, state: FSMContext, texts, buttons):
    cs = callback.data.split(":")[1]
    await state.update_data(credit_score=cs)
    
    data = await state.get_data()
    if data.get("fullz_type") == "business":
        # Для Business переходим к Report Group
        await state.set_state(FullzStates.select_report_group)
        await safe_edit_message(callback, 
            texts.FULLZ_CS_SELECT_REPORT.format(cs=cs.upper()),
            reply_markup=fullz_business_report_keyboard(buttons))
    else:
        await state.set_state(FullzStates.select_age)
        await safe_edit_message(callback, texts.FULLZ_SELECT_AGE, reply_markup=fullz_age_keyboard(buttons))
    await callback.answer()


@router.callback_query(F.data.startswith("fullz_loan:"))
async def fullz_loan_handler(callback: CallbackQuery, state: FSMContext, texts, buttons):
    loan_size = callback.data.split(":")[1]
    await state.update_data(loan_size=loan_size)
    
    # После Loan Size переходим к Credit Score
    await state.set_state(FullzStates.select_credit_score)
    await safe_edit_message(callback,
        texts.FULLZ_LOAN_SELECT_CS.format(loan_size=loan_size.replace('-', '–').upper()),
        reply_markup=fullz_business_cs_keyboard(buttons)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("fullz_age:"))
async def fullz_age_handler(callback: CallbackQuery, state: FSMContext, texts, buttons):
    age = callback.data.split(":")[1]
    await state.update_data(age=age)
    await state.set_state(FullzStates.select_gender)
    await safe_edit_message(callback, texts.FULLZ_SELECT_GENDER, reply_markup=fullz_gender_keyboard(buttons))
    await callback.answer()


@router.callback_query(F.data.startswith("fullz_gender:"))
async def fullz_gender_handler(callback: CallbackQuery, state: FSMContext, texts, buttons):
    gender = callback.data.split(":")[1]
    await state.update_data(gender=gender)
    await state.set_state(FullzStates.select_carrier_exclusion)
    await safe_edit_message(callback,
        getattr(texts, 'FULLZ_SELECT_CARRIER_EXCLUSION', "📱 **Carrier Exclusion**\n\nExclude a specific carrier from the fullz? This costs extra."),
        reply_markup=fullz_carrier_exclusion_keyboard(buttons),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("fullz_carrier:"))
async def fullz_carrier_handler(callback: CallbackQuery, state: FSMContext, texts, buttons):
    carrier = callback.data.split(":")[1]
    await state.update_data(carrier_exclusion=carrier)
    await state.set_state(FullzStates.select_bank_exclusion)
    await safe_edit_message(callback,
        getattr(texts, 'FULLZ_SELECT_BANK_EXCLUSION', "🏦 **Bank Exclusion**\n\nExclude a specific bank from the fullz? This costs extra."),
        reply_markup=fullz_bank_exclusion_keyboard(buttons),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("fullz_bank:"))
async def fullz_bank_handler(callback: CallbackQuery, state: FSMContext, texts, buttons):
    bank = callback.data.split(":")[1]
    await state.update_data(bank_exclusion=bank)
    await state.set_state(FullzStates.select_report_group)
    await safe_edit_message(callback, texts.FULLZ_SELECT_REPORT_GROUP, reply_markup=fullz_report_keyboard(buttons))
    await callback.answer()


@router.callback_query(F.data.startswith("fullz_report:"))
async def fullz_report_handler(callback: CallbackQuery, state: FSMContext, texts, buttons):
    report = callback.data.split(":")[1]
    await state.update_data(report_group=report)
    
    data = await state.get_data()
    if data.get("fullz_type") == "business":
        # Для Business переходим к количеству
        await state.set_state(FullzStates.select_quantity)
        await safe_edit_message(callback, 
            texts.FULLZ_REPORT_SELECT_QUANTITY.format(report=report.upper()),
            reply_markup=fullz_business_quantity_keyboard(buttons))
    else:
        # Для Personal
        await state.set_state(FullzStates.select_quantity)
        await safe_edit_message(callback, texts.FULLZ_SELECT_QUANTITY, reply_markup=fullz_quantity_keyboard(buttons))
    await callback.answer()


@router.callback_query(F.data.startswith("fullz_qty:"))
async def fullz_qty_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, mirror_bot_id: int, texts, buttons):
    logger.info(f"[FULLZ] Quantity handler called: {callback.data}")
    qty_str = callback.data.split(":")[1]
    
    if qty_str == "custom":
        await state.set_state(FullzStates.waiting_custom_qty)
        await safe_edit_message(callback, texts.ENTER_CUSTOM_QUANTITY)
        await callback.answer()
        return
    
    quantity = int(qty_str)
    data = await state.get_data()
    
    # Получаем текущий баланс пользователя
    user = await UserService.get_user(session, callback.from_user.id, mirror_bot_id)
    current_balance = float(user.balance) if user else 0.0
    
    if data.get("fullz_type") == "business":
        config = {
            "state": data.get("state", "ANY"),
            "company_type": data.get("company_type", "sole"),
            "loan_size": data.get("loan_size", "any"),
            "credit_score": data.get("credit_score", "any"),
            "report_group": data.get("report_group", "basic"),
            "quantity": quantity
        }
        
        total_price = float(ServicePrices.calculate_business_fullz_price(config))
        new_balance = current_balance - total_price
        
        # Calculate discount info
        discount_percent = ServicePrices.get_bulk_discount(quantity)
        discount_text = ""
        if discount_percent > 0:
            discount_percentage = int(discount_percent * 100)
            config_no_discount = config.copy()
            config_no_discount['quantity'] = 1
            price_per_item = float(ServicePrices.calculate_business_fullz_price(config_no_discount))
            original_total = price_per_item * quantity
            savings = original_total - total_price
            discount_text = f"\n{texts.FULLZ_ORDER_DISCOUNT} -{discount_percentage}% ({texts.FULLZ_ORDER_DISCOUNT_SAVE} ${savings:.2f}!)"
        
        summary = f"""{texts.FULLZ_BUSINESS_ORDER_TITLE}

{texts.FULLZ_ORDER_QUANTITY} {quantity}
{texts.FULLZ_ORDER_STATE} {data.get('state', 'ANY')}
{texts.FULLZ_ORDER_COMPANY_TYPE} {config['company_type'].upper()}
{texts.FULLZ_ORDER_LOAN_SIZE} {config['loan_size'].replace('-', '–').upper()}
{texts.FULLZ_ORDER_CREDIT_SCORE} {config['credit_score'].upper()}
{texts.FULLZ_ORDER_REPORT_GROUP} {config['report_group'].upper()}{discount_text}

{texts.FULLZ_ORDER_TOTAL_COST} ${total_price:.2f}
{texts.FULLZ_ORDER_CURRENT_BALANCE} ${current_balance:.2f}
{texts.FULLZ_ORDER_NEW_BALANCE} ${new_balance:.2f}

❓ **{texts.CONFIRM_PURCHASE_QUESTION}**"""
        
        confirm_text = buttons.CONFIRM_PAY
        await safe_edit_message(callback,
            summary,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=confirm_text, callback_data="fullz_confirm")],
                [InlineKeyboardButton(text=buttons.EDIT_FULLZ if hasattr(buttons, 'EDIT_FULLZ') else "✏️ Edit", callback_data="fullz_back_report")],
                [InlineKeyboardButton(text="⬅️ Menu", callback_data="fullz_back_main")]
            ]),
            parse_mode="Markdown"
        )
    else:
        config = {
            "state": data.get("state", "ANY"),
            "credit_score": data.get("credit_score", "any"),
            "age": data.get("age", "any"),
            "gender": data.get("gender", "any"),
            "carrier_exclusion": data.get("carrier_exclusion", "any"),
            "bank_exclusion": data.get("bank_exclusion", "any"),
            "report_group": data.get("report_group", "basic"),
            "quantity": quantity
        }
        
        total_price = float(ServicePrices.calculate_fullz_price(config))
        new_balance = current_balance - total_price
        
        # Calculate discount info
        discount_percent = ServicePrices.get_bulk_discount(quantity)
        discount_text = ""
        if discount_percent > 0:
            discount_percentage = int(discount_percent * 100)
            config_no_discount = config.copy()
            config_no_discount['quantity'] = 1
            price_per_item = float(ServicePrices.calculate_fullz_price(config_no_discount))
            original_total = price_per_item * quantity
            savings = original_total - total_price
            discount_text = f"\n{texts.FULLZ_ORDER_DISCOUNT} -{discount_percentage}% ({texts.FULLZ_ORDER_DISCOUNT_SAVE} ${savings:.2f}!)"

        carrier_val = data.get("carrier_exclusion", "any")
        carrier_label = f"Without {carrier_val.upper()}" if carrier_val != "any" else "Any"
        bank_val = data.get("bank_exclusion", "any")
        bank_labels = {"chase": "Chase", "citi": "Citi", "cap1": "Capital One", "wells": "Wells Fargo", "td": "TD Bank", "any_bank": "Any Bank"}
        bank_label = f"Without {bank_labels.get(bank_val, bank_val.upper())}" if bank_val != "any" else "Any"

        summary = f"""{texts.FULLZ_PERSONAL_ORDER_TITLE}

{texts.FULLZ_ORDER_QUANTITY} {quantity}
{texts.FULLZ_ORDER_STATE} {data.get('state', 'ANY')}
{texts.FULLZ_ORDER_CREDIT_SCORE} {data.get('credit_score', 'any')}
{texts.FULLZ_ORDER_AGE} {data.get('age', 'any')}
{texts.FULLZ_ORDER_GENDER} {data.get('gender', 'any')}
📱 Carrier: {carrier_label}
🏦 Bank: {bank_label}
{texts.FULLZ_ORDER_REPORT_GROUP} {data.get('report_group', 'basic')}{discount_text}

{texts.FULLZ_ORDER_TOTAL_COST} ${total_price:.2f}
{texts.FULLZ_ORDER_CURRENT_BALANCE} ${current_balance:.2f}
{texts.FULLZ_ORDER_NEW_BALANCE} ${new_balance:.2f}

❓ **{texts.CONFIRM_PURCHASE_QUESTION}**"""
        
        profile = data.get("profile", "")
        if profile in FIXED_PROFILE_SERVICE_NAME:
            svc_name = FIXED_PROFILE_SERVICE_NAME[profile]
        elif data.get("fullz_type") == "personal_cs" or profile == "cscr":
            svc_name = "fullz_cs"
        else:
            svc_name = "fullz_personal"

        await state.update_data(
            checkout_category="fullz",
            checkout_service_name=svc_name,
            checkout_base_price=str(total_price),
            checkout_confirm_text=summary,
            checkout_keyboard_type="confirm",
            checkout_keyboard_suffix="_fullz",
            checkout_parse_mode="Markdown",
            selected_coupon_code=None,
            selected_user_coupon_id=None,
        )
        await safe_edit_message(callback, summary, reply_markup=confirm_keyboard(buttons, suffix="_fullz"), parse_mode="Markdown")
    
    await state.update_data(quantity=quantity, total_price=total_price)
    await state.set_state(FullzStates.confirmation)
    logger.info(f"[FULLZ] State set to confirmation, total_price={total_price}")
    await callback.answer()


@router.callback_query(F.data.in_(["confirm_yes_fullz", "fullz_confirm"]), FullzStates.confirmation)
async def fullz_confirm_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, mirror_bot_id: int, texts, buttons):
    logger.info(f"[FULLZ] Confirm handler called for user {callback.from_user.id}")
    data = await state.get_data()
    logger.info(f"[FULLZ] State data: {data}")
    total_price = data.get("total_price")

    try:
        user = await UserService.get_user(session, callback.from_user.id, mirror_bot_id)
        fullz_type = data.get('fullz_type')
        profile = data.get('profile', '')

        if profile in FIXED_PROFILE_SERVICE_NAME:
            order_service_name = FIXED_PROFILE_SERVICE_NAME[profile]
        elif fullz_type == "personal_cs" or profile == "cscr":
            order_service_name = "fullz_cs"
        elif fullz_type == "business":
            order_service_name = "fullz_business"
        elif fullz_type:
            order_service_name = f"fullz_{fullz_type}"
        else:
            order_service_name = "fullz_personal"

        pricing = await OrderService.get_order_pricing(
            session,
            user_id=callback.from_user.id,
            category="fullz",
            service_name=order_service_name,
            amount=Decimal(str(total_price)),
            coupon_code=data.get("selected_coupon_code"),
            allow_auto_coupon=False,
        )

        if not user or user.balance < pricing.final_amount:
            await callback.answer(texts.INSUFFICIENT_BALANCE_ALERT, show_alert=True)
            return

        success = await OrderService.deduct_balance(session, callback.from_user.id, pricing.final_amount)
        if not success:
            await callback.answer(texts.INSUFFICIENT_BALANCE_ALERT, show_alert=True)
            return

        # Конвертируем Decimal в float для JSON сериализации
        serializable_data = {}
        for key, value in data.items():
            if isinstance(value, Decimal):
                serializable_data[key] = float(value)
            else:
                serializable_data[key] = value

        order = await OrderService.create_order(
            session,
            user_id=callback.from_user.id,
            mirror_bot_id=mirror_bot_id,
            category="fullz",
            service_name=order_service_name,
            input_data=serializable_data,
            price=pricing.final_amount,
            original_price=pricing.original_amount,
            coupon_code=pricing.code,
            discount_amount=pricing.discount_amount,
            coupon_application=pricing,
        )

        user = await UserService.get_user(session, callback.from_user.id, mirror_bot_id)

        # Получаем информацию о категории и сервисе
        user_language = user.language if user and hasattr(user, 'language') else 'en'

        category_name = ProductTranslations.get_category_name(
            "fullz",
            user_language
        )
        service_name = ProductTranslations.get_service_name(
            order_service_name,  # Используем то же имя, что и при создании заказа
            user_language
        )

        # Формируем название продукта - используем переведённое имя
        product_name = service_name
        if data.get('state'):
            product_name += f" - {data.get('state')}"

        # Добавляем количество если > 1
        quantity = data.get('quantity', 1)
        if quantity > 1:
            product_name += f" x{quantity}"

        # Получаем ETA на основе order_service_name
        eta = ServiceETA.get_eta(order_service_name)

        await safe_edit_message(
            callback,
            texts.ORDER_CREATED.format(
                product=product_name,
                price=order.price,
                balance=user.balance,
                eta=eta
            ),
            parse_mode="Markdown"
        )
        await state.clear()
        await callback.answer(texts.ORDER_CREATED_SUCCESS)
    except Exception as e:
        logger.error(f"Error confirming fullz order: {e}", exc_info=True)
        await callback.answer("Error processing order. Please contact support.", show_alert=True)


@router.callback_query(F.data == "confirm_no_fullz", FullzStates.confirmation)
async def fullz_cancel_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, texts, buttons):
    await state.clear()
    counts = await MenuCountService.get_fullz_counts(session)
    await safe_edit_message(
        callback,
        texts.ORDER_CANCELLED,
        reply_markup=fullz_main_keyboard(buttons, {"personal": counts["personal_total"], "business": counts["business_total"]}),
    )
    await callback.answer()


@router.callback_query(F.data == "fullz_back_main")
async def fullz_back_main_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, texts, buttons):
    await state.clear()
    counts = await MenuCountService.get_fullz_counts(session)
    fullz_photo = resolve_bot_photo("fullz", fallback_path="media/Fullz.jpg")
    # Для возврата в fullz всегда отправляем с фото
    try:
        await callback.message.delete()
        if fullz_photo:
            await callback.bot.send_photo(
                chat_id=callback.message.chat.id,
                photo=fullz_photo,
                caption=texts.FULLZ_MAIN,
                reply_markup=fullz_main_keyboard(buttons, {"personal": counts["personal_total"], "business": counts["business_total"]})
            )
        else:
            raise RuntimeError("Fullz photo is not configured")
    except Exception:
        # Fallback без фото
        await safe_edit_message(
            callback, 
            texts.FULLZ_MAIN, 
            reply_markup=fullz_main_keyboard(buttons, {"personal": counts["personal_total"], "business": counts["business_total"]})
        )
    await callback.answer()


@router.callback_query(F.data == "fullz_back_prof")
async def fullz_back_prof_handler(callback: CallbackQuery, state: FSMContext, texts, buttons):
    await state.set_state(FullzStates.select_type)
    await safe_edit_message(callback,
        texts.FULLZ_PERSONAL_PROFILES,
        reply_markup=fullz_personal_profiles_keyboard(buttons)
    )
    await callback.answer()


@router.callback_query(F.data == "fullz_back_state")
async def fullz_back_state_handler(callback: CallbackQuery, state: FSMContext, texts, buttons):
    data = await state.get_data()
    profile = data.get("profile", "")
    fullz_type = data.get("fullz_type", "personal")

    await state.set_state(FullzStates.select_state)

    if fullz_type == "business":
        await safe_edit_message(callback,
            texts.FULLZ_BUSINESS_MAIN,
            reply_markup=fullz_states_keyboard(page=0, button_texts=buttons)
        )
    elif profile == "cscr":
        await safe_edit_message(callback,
            texts.FULLZ_PROFILE_SELECT_STATE.format(profile="CUSTOM CS/CR"),
            reply_markup=fullz_states_keyboard(page=0, button_texts=buttons)
        )
    else:
        await safe_edit_message(callback,
            texts.FULLZ_SELECT_STATE,
            reply_markup=fullz_states_keyboard(page=0, button_texts=buttons)
        )
    await callback.answer()


@router.callback_query(F.data == "fullz_back_cs")
async def fullz_back_cs_handler(callback: CallbackQuery, state: FSMContext, texts, buttons):
    data = await state.get_data()
    selected_state = data.get("state", "ANY")
    fullz_type = data.get("fullz_type", "personal")
    
    await state.set_state(FullzStates.select_credit_score)
    
    if fullz_type == "business":
        await safe_edit_message(callback,
            texts.FULLZ_STATE_SELECT_CS.format(state=selected_state),
            reply_markup=fullz_business_cs_keyboard(buttons)
        )
    else:
        await safe_edit_message(callback,
            texts.FULLZ_STATE_SELECT_CS.format(state=selected_state),
            reply_markup=fullz_cs_keyboard(buttons)
        )
    await callback.answer()


@router.callback_query(F.data == "fullz_back_age")
async def fullz_back_age_handler(callback: CallbackQuery, state: FSMContext, texts, buttons):
    await state.set_state(FullzStates.select_age)
    await safe_edit_message(callback, texts.FULLZ_SELECT_AGE, reply_markup=fullz_age_keyboard(buttons))
    await callback.answer()


@router.callback_query(F.data == "fullz_back_gender")
async def fullz_back_gender_handler(callback: CallbackQuery, state: FSMContext, texts, buttons):
    await state.set_state(FullzStates.select_gender)
    await safe_edit_message(callback, texts.FULLZ_SELECT_GENDER, reply_markup=fullz_gender_keyboard(buttons))
    await callback.answer()


@router.callback_query(F.data == "fullz_back_carrier")
async def fullz_back_carrier_handler(callback: CallbackQuery, state: FSMContext, texts, buttons):
    await state.set_state(FullzStates.select_carrier_exclusion)
    await safe_edit_message(callback,
        getattr(texts, 'FULLZ_SELECT_CARRIER_EXCLUSION', "📱 **Carrier Exclusion**\n\nExclude a specific carrier from the fullz? This costs extra."),
        reply_markup=fullz_carrier_exclusion_keyboard(buttons),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data == "fullz_back_bank")
async def fullz_back_bank_handler(callback: CallbackQuery, state: FSMContext, texts, buttons):
    await state.set_state(FullzStates.select_bank_exclusion)
    await safe_edit_message(callback,
        getattr(texts, 'FULLZ_SELECT_BANK_EXCLUSION', "🏦 **Bank Exclusion**\n\nExclude a specific bank from the fullz? This costs extra."),
        reply_markup=fullz_bank_exclusion_keyboard(buttons),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data == "fullz_back_report")
async def fullz_back_report_handler(callback: CallbackQuery, state: FSMContext, texts, buttons):
    data = await state.get_data()
    await state.set_state(FullzStates.select_report_group)
    if data.get("fullz_type") == "business":
        cs = data.get("credit_score", "any")
        await safe_edit_message(callback,
            texts.FULLZ_CS_SELECT_REPORT.format(cs=cs.upper()),
            reply_markup=fullz_business_report_keyboard(buttons))
    else:
        await safe_edit_message(callback, texts.FULLZ_SELECT_REPORT_GROUP, reply_markup=fullz_report_keyboard(buttons))
    await callback.answer()


@router.callback_query(F.data == "fullz_back_company")
async def fullz_back_company_handler(callback: CallbackQuery, state: FSMContext, texts, buttons):
    """Возврат к выбору Company Type"""
    data = await state.get_data()
    selected_state = data.get("state", "N/A")
    
    await state.set_state(FullzStates.select_company_type)
    await safe_edit_message(callback,
        texts.FULLZ_STATE_SELECT_COMPANY.format(state=selected_state),
        reply_markup=fullz_company_type_keyboard(buttons)
    )
    await callback.answer()


@router.callback_query(F.data == "fullz_back_ceo_cs")
async def fullz_back_ceo_cs_handler(callback: CallbackQuery, state: FSMContext, texts, buttons):
    """Возврат к выбору CEO CS"""
    data = await state.get_data()
    company_type = data.get("company_type", "any")
    
    await state.set_state(FullzStates.select_credit_score)
    await safe_edit_message(callback,
        texts.FULLZ_COMPANY_SELECT_CEO_CS.format(company_type=company_type.upper()),
        reply_markup=fullz_ceo_cs_keyboard(buttons)
    )
    await callback.answer()


@router.callback_query(F.data == "fullz_back_loan")
async def fullz_back_loan_handler(callback: CallbackQuery, state: FSMContext, texts, buttons):
    """Возврат к выбору Loan Size"""
    data = await state.get_data()
    ceo_cs = data.get("credit_score", "any")
    
    await state.set_state(FullzStates.select_loan_size)
    await safe_edit_message(callback, 
        texts.FULLZ_CEO_CS_SELECT_LOAN.format(ceo_cs=ceo_cs.upper()),
        reply_markup=fullz_loan_size_keyboard(buttons)
    )
    await callback.answer()


async def handle_random_fullz_order(callback: CallbackQuery, state: FSMContext, session: AsyncSession, mirror_bot_id: int, texts, buttons):
    """Random Personal FULLZ — показываем qty экран с инфо о наличии (аналогично fixed profiles)"""
    try:
        from mirror_bot.services.product_service import ProductService

        products_data = await ProductService.get_products_by_category_service_state(
            session=session, category="pros_fullz", service="personal_random",
            state="ANY", page=1, per_page=1,
        )
        stock = products_data["total"]
        price = ServicePrices.FULLZ_BASE

        await state.update_data(
            fullz_type="personal",
            profile="random",
            fixed_profile=True,
            state="ANY",
            service_name="personal_random",
            price=float(price),
            fixed_stock=stock,
        )
        await state.set_state(FullzStates.select_fixed_quantity)

        stock_line = f"📊 **In stock:** {stock}" if stock > 0 else "📊 **In stock:** 0 (worker order)"
        eta_worker = ServiceETA.get_eta("personal_random")

        text = (
            f"🎲 **RANDOM FULLZ — ANY STATE**\n"
            f"💰 Price per item: ${price}\n\n"
            f"{stock_line}\n"
        )
        if stock > 0:
            text += f"⚡ In-stock items: **{ServiceETA.FULLZ_INSTANT}**\n"
        text += f"⏱ Worker order items: **{eta_worker}**\n\n"
        text += "🔢 **Select quantity:**"

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="1", callback_data="fullz_fqty:1"),
                InlineKeyboardButton(text="3", callback_data="fullz_fqty:3"),
                InlineKeyboardButton(text="5", callback_data="fullz_fqty:5"),
            ],
            [
                InlineKeyboardButton(text="10", callback_data="fullz_fqty:10"),
                InlineKeyboardButton(text=getattr(buttons, 'CUSTOM_QUANTITY', '✏️ Custom'), callback_data="fullz_fqty:custom"),
            ],
            [InlineKeyboardButton(text=buttons.BACK, callback_data="fullz_back_prof")],
        ])

        await safe_edit_message(callback, text, reply_markup=kb, parse_mode="Markdown")
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in random fullz order: {e}", exc_info=True)
        await safe_edit_message(callback, texts.ORDER_CREATION_ERROR)
        await callback.answer()
        await state.clear()


@router.message(FullzStates.waiting_custom_qty, F.text)
async def fullz_custom_qty_input(message: Message, state: FSMContext, session: AsyncSession, mirror_bot_id: int, texts, buttons):
    """Обработка ввода custom quantity для FULLZ"""
    data = await state.get_data()
    
    try:
        quantity = int(message.text.strip())
        
        if quantity < 1 or quantity > 100:
            await message.answer(texts.INVALID_QUANTITY)
            return
        
        # Получаем текущий баланс пользователя
        user = await UserService.get_user(session, message.from_user.id, mirror_bot_id)
        current_balance = float(user.balance) if user else 0.0
        
        if data.get("fullz_type") == "business":
            config = {
                "state": data.get("state", "ANY"),
                "company_type": data.get("company_type", "sole"),
                "loan_size": data.get("loan_size", "any"),
                "credit_score": data.get("credit_score", "any"),
                "report_group": data.get("report_group", "basic"),
                "quantity": quantity
            }
            
            total_price = float(ServicePrices.calculate_business_fullz_price(config))
            new_balance = current_balance - total_price
            
            # Calculate discount info
            discount_percent = ServicePrices.get_bulk_discount(quantity)
            discount_text = ""
            if discount_percent > 0:
                discount_percentage = int(discount_percent * 100)
                config_no_discount = config.copy()
                config_no_discount['quantity'] = 1
                price_per_item = float(ServicePrices.calculate_business_fullz_price(config_no_discount))
                original_total = price_per_item * quantity
                savings = original_total - total_price
                discount_text = f"\n{texts.FULLZ_ORDER_DISCOUNT} -{discount_percentage}% ({texts.FULLZ_ORDER_DISCOUNT_SAVE} ${savings:.2f}!)"
            
            summary = f"""{texts.FULLZ_BUSINESS_ORDER_TITLE}

{texts.FULLZ_ORDER_QUANTITY} {quantity}
{texts.FULLZ_ORDER_STATE} {data.get('state', 'ANY')}
{texts.FULLZ_ORDER_COMPANY_TYPE} {config['company_type'].upper()}
{texts.FULLZ_ORDER_LOAN_SIZE} {config['loan_size'].replace('-', '–').upper()}
{texts.FULLZ_ORDER_CREDIT_SCORE} {config['credit_score'].upper()}
{texts.FULLZ_ORDER_REPORT_GROUP} {config['report_group'].upper()}{discount_text}

{texts.FULLZ_ORDER_TOTAL_COST} ${total_price:.2f}
{texts.FULLZ_ORDER_CURRENT_BALANCE} ${current_balance:.2f}
{texts.FULLZ_ORDER_NEW_BALANCE} ${new_balance:.2f}

❓ **{texts.CONFIRM_PURCHASE_QUESTION}**"""
            
            confirm_text = buttons.CONFIRM_PAY
            await message.answer(
                summary,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=confirm_text, callback_data="fullz_confirm")],
                    [InlineKeyboardButton(text=buttons.EDIT_FULLZ if hasattr(buttons, 'EDIT_FULLZ') else "✏️ Edit", callback_data="fullz_back_report")],
                    [InlineKeyboardButton(text="⬅️ Menu", callback_data="fullz_back_main")]
                ]),
                parse_mode="Markdown"
            )
        else:
            config = {
                "state": data.get("state", "ANY"),
                "credit_score": data.get("credit_score", "any"),
                "age": data.get("age", "any"),
                "gender": data.get("gender", "any"),
                "carrier_exclusion": data.get("carrier_exclusion", "any"),
                "bank_exclusion": data.get("bank_exclusion", "any"),
                "report_group": data.get("report_group", "basic"),
                "quantity": quantity
            }
            
            total_price = float(ServicePrices.calculate_fullz_price(config))
            new_balance = current_balance - total_price
            
            # Calculate discount info
            discount_percent = ServicePrices.get_bulk_discount(quantity)
            discount_text = ""
            if discount_percent > 0:
                discount_percentage = int(discount_percent * 100)
                config_no_discount = config.copy()
                config_no_discount['quantity'] = 1
                price_per_item = float(ServicePrices.calculate_fullz_price(config_no_discount))
                original_total = price_per_item * quantity
                savings = original_total - total_price
                discount_text = f"\n{texts.FULLZ_ORDER_DISCOUNT} -{discount_percentage}% ({texts.FULLZ_ORDER_DISCOUNT_SAVE} ${savings:.2f}!)"

            carrier_val = data.get("carrier_exclusion", "any")
            carrier_label = f"Without {carrier_val.upper()}" if carrier_val != "any" else "Any"
            bank_val = data.get("bank_exclusion", "any")
            bank_labels = {"chase": "Chase", "citi": "Citi", "cap1": "Capital One", "wells": "Wells Fargo", "td": "TD Bank", "any_bank": "Any Bank"}
            bank_label = f"Without {bank_labels.get(bank_val, bank_val.upper())}" if bank_val != "any" else "Any"

            summary = f"""{texts.FULLZ_PERSONAL_ORDER_TITLE}

{texts.FULLZ_ORDER_QUANTITY} {quantity}
{texts.FULLZ_ORDER_STATE} {data.get('state', 'ANY')}
{texts.FULLZ_ORDER_CREDIT_SCORE} {data.get('credit_score', 'any')}
{texts.FULLZ_ORDER_AGE} {data.get('age', 'any')}
{texts.FULLZ_ORDER_GENDER} {data.get('gender', 'any')}
📱 Carrier: {carrier_label}
🏦 Bank: {bank_label}
{texts.FULLZ_ORDER_REPORT_GROUP} {data.get('report_group', 'basic')}{discount_text}

{texts.FULLZ_ORDER_TOTAL_COST} ${total_price:.2f}
{texts.FULLZ_ORDER_CURRENT_BALANCE} ${current_balance:.2f}
{texts.FULLZ_ORDER_NEW_BALANCE} ${new_balance:.2f}

❓ **{texts.CONFIRM_PURCHASE_QUESTION}**"""
            
            profile = data.get("profile", "")
            if profile in FIXED_PROFILE_SERVICE_NAME:
                svc_name = FIXED_PROFILE_SERVICE_NAME[profile]
            elif data.get("fullz_type") == "personal_cs" or profile == "cscr":
                svc_name = "fullz_cs"
            else:
                svc_name = "fullz_personal"

            await state.update_data(
                checkout_category="fullz",
                checkout_service_name=svc_name,
                checkout_base_price=str(total_price),
                checkout_confirm_text=summary,
                checkout_keyboard_type="confirm",
                checkout_keyboard_suffix="_fullz",
                checkout_parse_mode="Markdown",
                selected_coupon_code=None,
                selected_user_coupon_id=None,
            )
            await message.answer(summary, reply_markup=confirm_keyboard(buttons, suffix="_fullz"), parse_mode="Markdown")
        
        # Сохраняем quantity и total_price в state
        await state.update_data(quantity=quantity, total_price=total_price)
        await state.set_state(FullzStates.confirmation)
        
    except ValueError:
        await message.answer(texts.INVALID_QUANTITY)
        return
    except Exception as e:
        logger.error(f"Error processing custom FULLZ quantity: {e}")
        await message.answer(texts.ORDER_CREATION_ERROR)
        await state.clear()


@router.callback_query(F.data == "confirm_yes_randomfullz", RandomFullzStates.confirmation)
async def random_fullz_confirm_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, mirror_bot_id: int, texts):
    """Подтверждение заказа Random FULLZ"""
    try:
        data = await state.get_data()
        price = Decimal(str(data.get("price")))
        
        # Получаем пользователя
        user = await UserService.get_user(session, callback.from_user.id, mirror_bot_id)
        
        if not user:
            await callback.message.answer(texts.USER_NOT_FOUND_CONTACT_SUPPORT)
            await state.clear()
            await callback.answer()
            return
        
        # Проверяем баланс
        pricing = await CheckoutCouponService.get_checkout_pricing(
            session,
            telegram_user_id=callback.from_user.id,
            state_data=data,
        )
        if user.balance < pricing.final_amount:
            await callback.message.answer(
                texts.INSUFFICIENT_BALANCE.format(balance=user.balance, price=pricing.final_amount)
            )
            await state.clear()
            await callback.answer()
            return
        
        # Списываем деньги
        success = await OrderService.deduct_balance(session, callback.from_user.id, pricing.final_amount)
        if not success:
            await callback.message.answer(texts.INSUFFICIENT_BALANCE.format(balance=user.balance, price=price))
            await state.clear()
            await callback.answer()
            return
        
        # Создаем заказ
        order = await OrderService.create_order(
            session,
            user_id=callback.from_user.id,
            mirror_bot_id=mirror_bot_id,
            category="fullz",
            service_name=data.get("service_name", "personal_random"),
            input_data={
                "profile": "random",
                "state": "ANY",
                "fullz_type": "personal"
            },
            price=pricing.final_amount,
            original_price=pricing.original_amount,
            coupon_code=pricing.code,
            discount_amount=pricing.discount_amount,
            coupon_application=pricing,
        )
        
        # Получаем обновленный баланс
        user = await UserService.get_user(session, callback.from_user.id, mirror_bot_id)
        
        # Получаем ETA
        eta = ServiceETA.get_eta("fullz_personal")
        
        # Отправляем подтверждение
        await safe_edit_message(callback,
            texts.FULLZ_RANDOM_ORDER_CREATED.format(
                price=price,
                order_id=order.id,
                balance=user.balance,
                eta=eta
            ),
            parse_mode="Markdown"
        )
        
        await state.clear()
        await callback.answer(texts.ORDER_CREATED_SUCCESS)
        
    except Exception as e:
        logger.error(f"Error confirming random fullz order: {e}")
        await callback.message.answer(texts.ORDER_CREATION_ERROR)
        await state.clear()
        await callback.answer()


@router.callback_query(F.data == "confirm_no_randomfullz", RandomFullzStates.confirmation)
async def random_fullz_cancel_handler(callback: CallbackQuery, state: FSMContext, texts):
    """Отмена заказа Random FULLZ"""
    await safe_edit_message(callback, texts.CANCELLED, parse_mode=None)
    await state.clear()
    await callback.answer()



