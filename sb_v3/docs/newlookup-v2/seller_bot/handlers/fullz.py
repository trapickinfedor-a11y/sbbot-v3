from __future__ import annotations

from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from seller_bot.services.special_stock_service import SpecialStockService
from shared.services.seller_deposit_service import SellerDepositService
from shared.services.seller_upload_batch_service import SellerUploadBatchService

router = Router(name="seller_fullz")

# ─────────────────────────────────────────────────────────────────────────────
# Own keyboards — defined inside this module (Своя клавиатура)
# ─────────────────────────────────────────────────────────────────────────────

def _cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="seller_menu")],
    ])


def _yes_no_kb(prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да",  callback_data=f"{prefix}:yes"),
            InlineKeyboardButton(text="❌ Нет", callback_data=f"{prefix}:no"),
        ],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="seller_menu")],
    ])


def _fullz_type_kb(buttons=None) -> InlineKeyboardMarkup:
    personal = (buttons and getattr(buttons, "FULLZ_TYPE_PERSONAL", None)) or "👤 Персональный"
    business = (buttons and getattr(buttons, "FULLZ_TYPE_BUSINESS", None)) or "🏢 Бизнес"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=personal, callback_data="seller_fullz_ftype:personal")],
        [InlineKeyboardButton(text=business, callback_data="seller_fullz_ftype:business")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="seller_menu")],
    ])


def _cs_kb(back_cb: str, buttons=None) -> InlineKeyboardMarkup:
    cs800 = (buttons and getattr(buttons, "FULLZ_CS_800", None)) or "⭐ 800+"
    cs700 = (buttons and getattr(buttons, "FULLZ_CS_700", None)) or "✨ 700+"
    cs500 = (buttons and getattr(buttons, "FULLZ_CS_500", None)) or "💠 500+"
    any_  = (buttons and getattr(buttons, "FULLZ_CS_ANY",  None)) or "🔘 Любой КС — $0"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=cs800, callback_data="seller_fullz_cs:800+")],
        [InlineKeyboardButton(text=cs700, callback_data="seller_fullz_cs:700+")],
        [InlineKeyboardButton(text=cs500, callback_data="seller_fullz_cs:500+")],
        [InlineKeyboardButton(text=any_,  callback_data="seller_fullz_cs:any")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=back_cb)],
    ])


def _age_kb(buttons=None) -> InlineKeyboardMarkup:
    a18  = (buttons and getattr(buttons, "FULLZ_AGE_18",  None)) or "🧒 18–25"
    a26  = (buttons and getattr(buttons, "FULLZ_AGE_26",  None)) or "👨 26–35"
    a36  = (buttons and getattr(buttons, "FULLZ_AGE_36",  None)) or "🧓 36+"
    any_ = (buttons and getattr(buttons, "FULLZ_AGE_ANY", None)) or "🎲 Любой возраст — $0"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=a18,  callback_data="seller_fullz_age:18-25")],
        [InlineKeyboardButton(text=a26,  callback_data="seller_fullz_age:26-35")],
        [InlineKeyboardButton(text=a36,  callback_data="seller_fullz_age:36+")],
        [InlineKeyboardButton(text=any_, callback_data="seller_fullz_age:any")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="seller_fullz_back_cs")],
    ])


def _gender_kb(buttons=None) -> InlineKeyboardMarkup:
    male   = (buttons and getattr(buttons, "FULLZ_GENDER_MALE",   None)) or "👨 Мужской"
    female = (buttons and getattr(buttons, "FULLZ_GENDER_FEMALE", None)) or "👩 Женский"
    any_   = (buttons and getattr(buttons, "FULLZ_GENDER_ANY",    None)) or "🎲 Любой пол — $0"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=male,   callback_data="seller_fullz_gender:male")],
        [InlineKeyboardButton(text=female, callback_data="seller_fullz_gender:female")],
        [InlineKeyboardButton(text=any_,   callback_data="seller_fullz_gender:any")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="seller_fullz_back_age")],
    ])


def _company_kb(buttons=None) -> InlineKeyboardMarkup:
    sole = (buttons and getattr(buttons, "FULLZ_COMPANY_SOLE", None)) or "👤 ИП (Sole Proprietor)"
    llc  = (buttons and getattr(buttons, "FULLZ_COMPANY_LLC",  None)) or "🏢 LLC"
    corp = (buttons and getattr(buttons, "FULLZ_COMPANY_CORP", None)) or "🏛️ Corp"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=sole, callback_data="seller_fullz_company:sole")],
        [InlineKeyboardButton(text=llc,  callback_data="seller_fullz_company:llc")],
        [InlineKeyboardButton(text=corp, callback_data="seller_fullz_company:corp")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="seller_fullz_back_state")],
    ])


def _loan_kb(buttons=None) -> InlineKeyboardMarkup:
    l25  = (buttons and getattr(buttons, "FULLZ_LOAN_25_200",   None)) or "💰 $25k–$200k"
    l200 = (buttons and getattr(buttons, "FULLZ_LOAN_200_500",  None)) or "💰 $200k–$500k"
    l500 = (buttons and getattr(buttons, "FULLZ_LOAN_500_PLUS", None)) or "💰 $500k+"
    any_ = (buttons and getattr(buttons, "FULLZ_LOAN_ANY",      None)) or "📊 Любой размер — $0"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=l25,  callback_data="seller_fullz_loan:25k-200k")],
        [InlineKeyboardButton(text=l200, callback_data="seller_fullz_loan:200k-500k")],
        [InlineKeyboardButton(text=l500, callback_data="seller_fullz_loan:500k+")],
        [InlineKeyboardButton(text=any_, callback_data="seller_fullz_loan:any")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="seller_fullz_back_company")],
    ])


def _report_kb(back_cb: str, buttons=None) -> InlineKeyboardMarkup:
    basic    = (buttons and getattr(buttons, "FULLZ_REPORT_BASIC",      None)) or "💼 Базовый"
    cr       = (buttons and getattr(buttons, "FULLZ_REPORT_CR",         None)) or "📘 С CR"
    cr_dl    = (buttons and getattr(buttons, "FULLZ_REPORT_CR_DL",      None)) or "🪪 CR и DL"
    cr_mvr   = (buttons and getattr(buttons, "FULLZ_REPORT_CR_DL_MVR",  None)) or "🛰️ CR, DL и MVR"
    full_mvr = (buttons and getattr(buttons, "FULLZ_REPORT_FULL",       None)) or "🏁 CR, DL и FULL MVR"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=basic,    callback_data="seller_fullz_report:basic")],
        [InlineKeyboardButton(text=cr,       callback_data="seller_fullz_report:cr")],
        [InlineKeyboardButton(text=cr_dl,    callback_data="seller_fullz_report:cr_dl")],
        [InlineKeyboardButton(text=cr_mvr,   callback_data="seller_fullz_report:cr_dl_mvr")],
        [InlineKeyboardButton(text=full_mvr, callback_data="seller_fullz_report:cr_dl_fullmvr")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=back_cb)],
    ])


def _fullz_list_kb(items: list, lang: str = "en") -> InlineKeyboardMarkup:
    rows = []
    for item in items:
        stock = "✅" if item.is_in_stock else "❌"
        ftype = ("Персональный" if item.fullz_type == "personal" else "Бизнес") \
                if lang == "ru" else item.fullz_type.title()
        rows.append([InlineKeyboardButton(
            text=f"{stock} {ftype} | {item.state or 'ANY'} | x{item.quantity} | ${item.seller_price}",
            callback_data=f"seller_fullz_detail:{item.id}",
        )])
    add_text  = "➕ Добавить Fullz" if lang == "ru" else "➕ Add Fullz"
    back_text = "⬅️ Назад" if lang == "ru" else "⬅️ Back"
    rows.append([InlineKeyboardButton(text=add_text,  callback_data="seller_add_fullz")])
    rows.append([InlineKeyboardButton(text=back_text, callback_data="seller_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _fullz_detail_kb(item_id: int, is_in_stock: bool, lang: str = "en") -> InlineKeyboardMarkup:
    if lang == "ru":
        toggle    = "❌ Снять с продажи" if is_in_stock else "✅ Выставить на продажу"
        del_text  = "🗑 Удалить"
        back_text = "⬅️ К Fullz"
    else:
        toggle    = "❌ Set Out of Stock" if is_in_stock else "✅ Set In Stock"
        del_text  = "🗑 Delete"
        back_text = "⬅️ Back to Fullz"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=toggle,    callback_data=f"seller_fullz_toggle:{item_id}")],
        [InlineKeyboardButton(text=del_text,  callback_data=f"seller_fullz_delete:{item_id}")],
        [InlineKeyboardButton(text=back_text, callback_data="seller_my_fullz")],
    ])


# ─────────────────────────────────────────────────────────────────────────────
# FSM states
# ─────────────────────────────────────────────────────────────────────────────

class AddFullzStates(StatesGroup):
    waiting_fullz_type   = State()
    waiting_state        = State()
    waiting_credit_score = State()
    waiting_age_range    = State()
    waiting_gender       = State()
    waiting_company_type = State()
    waiting_loan_size    = State()
    waiting_report_group = State()
    waiting_quantity     = State()
    waiting_description  = State()
    waiting_price        = State()
    waiting_data_file    = State()


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _parse_price(text: str) -> Decimal | None:
    try:
        value = Decimal(text.strip().replace("$", "").replace(",", "."))
    except (InvalidOperation, ValueError):
        return None
    return value if value > 0 else None


async def _t(ui_texts, key: str, default: str, texts=None, **fmt) -> str:
    local_default = default
    if texts is not None:
        attr = key.split(".")[-1].upper().replace(".", "_")
        local_default = getattr(texts, attr, default)
    try:
        return await ui_texts.get(key, local_default, **fmt)
    except Exception:
        return local_default.format(**fmt) if fmt else local_default


def _check_deposit(seller, seller_actor, lang: str = "en") -> str | None:
    if not seller or not seller_actor or not seller_actor.can_upload():
        return "❌ Нет доступа" if lang == "ru" else "❌ Not authorized"
    if not SellerDepositService.has_upload_access(seller, "bank"):
        return (
            "❌ Для загрузки fullz необходим депозит пакета Bank."
            if lang == "ru" else
            "❌ Bank package deposit is required to upload fullz."
        )
    return None


def _lang(kwargs: dict) -> str:
    return getattr(kwargs.get("seller"), "language", None) or "en"


def _build_item_name(data: dict, lang: str = "en") -> str:
    ftype   = data.get("fullz_type", "personal")
    state   = data.get("state") or "ANY"
    qty     = data.get("quantity", 1)
    if ftype == "business":
        company = (data.get("company_type") or "any").upper()
        return f"{'Бизнес Fullz' if lang=='ru' else 'Business Fullz'} | {company} | {state} | x{qty}"
    cs     = data.get("credit_score", "any")
    age    = data.get("age_range", "any")
    gender = data.get("gender", "any")
    label  = "Персональный Fullz" if lang == "ru" else "Personal Fullz"
    return f"{label} | CS:{cs} | {age} | {gender} | {state} | x{qty}"


# ─────────────────────────────────────────────────────────────────────────────
# My Fullz list
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "seller_my_fullz")
async def my_fullz_handler(callback: CallbackQuery, session: AsyncSession, seller, ui_texts, texts, **kwargs):
    if not seller:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    lang = _lang(kwargs)
    from sqlalchemy import select as _sel
    from shared.database.models import SellerFullzItem
    q = await session.execute(
        _sel(SellerFullzItem)
        .where(SellerFullzItem.seller_id == seller.id, SellerFullzItem.is_active == True)
        .order_by(SellerFullzItem.created_at.desc())
        .limit(30)
    )
    items = q.scalars().all()
    header = await _t(ui_texts, "seller.fullz.list_header",
                      "🧑‍💼 <b>Мои Fullz</b>\n\nВаши загруженные наборы fullz:", texts=texts)
    await callback.message.edit_text(header, reply_markup=_fullz_list_kb(items, lang), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("seller_fullz_detail:"))
async def fullz_detail_handler(callback: CallbackQuery, session: AsyncSession, seller, texts, **kwargs):
    lang = _lang(kwargs)
    item_id = int(callback.data.split(":")[1])
    from sqlalchemy import select as _sel
    from shared.database.models import SellerFullzItem
    q = await session.execute(_sel(SellerFullzItem).where(SellerFullzItem.id == item_id))
    item = q.scalar_one_or_none()
    if not item or item.seller_id != seller.id:
        await callback.answer(getattr(texts, "FULLZ_NOT_FOUND", "❌ Товар не найден"), show_alert=True)
        return
    mod = item.moderation_status.replace("_", " ").title()
    if lang == "ru":
        type_label = "Персональный" if item.fullz_type == "personal" else "Бизнес"
        if item.fullz_type == "business":
            details = (
                f"🏢 Компания: <b>{(item.company_type or 'any').upper()}</b>\n"
                f"💰 Займ: <b>{item.loan_size or 'any'}</b>\n"
            )
        else:
            details = (
                f"📊 КС: <b>{item.credit_score}</b>\n"
                f"🎂 Возраст: <b>{item.age_range}</b>\n"
                f"⚥ Пол: <b>{item.gender}</b>\n"
            )
        body = (
            f"🧑‍💼 <b>{item.item_name}</b>\n\n"
            f"📋 Тип: <b>{type_label}</b>\n"
            f"🗺 Штат: <b>{item.state or 'ЛЮБОЙ'}</b>\n"
            + details +
            f"📄 Отчёт: <b>{item.report_group}</b>\n"
            f"🔢 Кол-во: <b>{item.quantity}</b>\n"
            f"💰 Цена продавца: <b>${item.seller_price}</b>\n"
            f"🏷 Цена покупателя: <b>${item.buyer_price}</b>\n"
            f"📋 Статус: <b>{mod}</b>\n"
            f"📦 В наличии: {'✅' if item.is_in_stock else '❌'}"
        )
    else:
        if item.fullz_type == "business":
            details = (
                f"🏢 Company: <b>{(item.company_type or 'any').upper()}</b>\n"
                f"💰 Loan: <b>{item.loan_size or 'any'}</b>\n"
            )
        else:
            details = (
                f"📊 Credit Score: <b>{item.credit_score}</b>\n"
                f"🎂 Age: <b>{item.age_range}</b>\n"
                f"⚥ Gender: <b>{item.gender}</b>\n"
            )
        body = (
            f"🧑‍💼 <b>{item.item_name}</b>\n\n"
            f"📋 Type: <b>{item.fullz_type.title()}</b>\n"
            f"🗺 State: <b>{item.state or 'ANY'}</b>\n"
            + details +
            f"📄 Report: <b>{item.report_group}</b>\n"
            f"🔢 Quantity: <b>{item.quantity}</b>\n"
            f"💰 Seller price: <b>${item.seller_price}</b>\n"
            f"🏷 Buyer price: <b>${item.buyer_price}</b>\n"
            f"📋 Status: <b>{mod}</b>\n"
            f"📦 In stock: {'✅' if item.is_in_stock else '❌'}"
        )
    if item.seller_description:
        body += f"\n📝 {item.seller_description}"
    await callback.message.edit_text(body, reply_markup=_fullz_detail_kb(item.id, item.is_in_stock, lang), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("seller_fullz_toggle:"))
async def fullz_toggle_handler(callback: CallbackQuery, session: AsyncSession, seller, texts, **kwargs):
    lang = _lang(kwargs)
    item_id = int(callback.data.split(":")[1])
    from sqlalchemy import select as _sel
    from shared.database.models import SellerFullzItem
    q = await session.execute(_sel(SellerFullzItem).where(SellerFullzItem.id == item_id))
    item = q.scalar_one_or_none()
    if not item or item.seller_id != seller.id:
        await callback.answer(getattr(texts, "FULLZ_NOT_FOUND", "❌ Товар не найден"), show_alert=True)
        return
    item.is_in_stock = not item.is_in_stock
    await session.commit()
    status = ("✅ В наличии" if item.is_in_stock else "❌ Нет в наличии") if lang == "ru" \
             else ("✅ In Stock" if item.is_in_stock else "❌ Out of Stock")
    await callback.answer(status)
    await callback.message.edit_reply_markup(reply_markup=_fullz_detail_kb(item.id, item.is_in_stock, lang))


@router.callback_query(F.data.startswith("seller_fullz_delete:"))
async def fullz_delete_handler(callback: CallbackQuery, session: AsyncSession,
                                seller, ui_texts, texts, **kwargs):
    item_id = int(callback.data.split(":")[1])
    from sqlalchemy import select as _sel
    from shared.database.models import SellerFullzItem
    q = await session.execute(_sel(SellerFullzItem).where(SellerFullzItem.id == item_id))
    item = q.scalar_one_or_none()
    if not item or item.seller_id != seller.id:
        await callback.answer(getattr(texts, "FULLZ_NOT_FOUND", "❌ Товар не найден"), show_alert=True)
        return
    item.is_active = False
    item.is_in_stock = False
    await session.commit()
    await callback.answer(getattr(texts, "FULLZ_DELETED", "🗑 Удалено"))
    await my_fullz_handler(callback, session, seller, ui_texts, texts, **kwargs)


# ─────────────────────────────────────────────────────────────────────────────
# Add Fullz FSM
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "seller_add_fullz")
async def add_fullz_start(callback: CallbackQuery, state: FSMContext,
                           seller, ui_texts, texts, buttons, **kwargs):
    lang = _lang(kwargs)
    error = _check_deposit(seller, kwargs.get("seller_actor"), lang)
    if error:
        await callback.answer(error, show_alert=True)
        return
    await state.clear()
    await state.set_state(AddFullzStates.waiting_fullz_type)
    prompt = await _t(ui_texts, "seller.fullz.select_type",
                      "🧑‍💼 <b>Добавить набор Fullz</b>\n\nВыберите тип fullz:", texts=texts)
    await callback.message.edit_text(prompt, reply_markup=_fullz_type_kb(buttons), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("seller_fullz_ftype:"), AddFullzStates.waiting_fullz_type)
async def add_fullz_type(callback: CallbackQuery, state: FSMContext, ui_texts, texts, **kwargs):
    fullz_type = callback.data.split(":")[1]
    await state.update_data(fullz_type=fullz_type)
    await state.set_state(AddFullzStates.waiting_state)
    prompt = await _t(ui_texts, "seller.fullz.enter_state",
                      "Введите штат США (напр. <code>CA</code>) или <code>-</code> для любого:",
                      texts=texts)
    await callback.message.edit_text(prompt, reply_markup=_cancel_kb(), parse_mode="HTML")
    await callback.answer()


@router.message(AddFullzStates.waiting_state, F.text)
async def add_fullz_state(message: Message, state: FSMContext, ui_texts, texts, buttons, **kwargs):
    raw = message.text.strip()
    selected_state = None if raw == "-" else raw.upper()[:2]
    await state.update_data(state=selected_state)
    data = await state.get_data()
    if data.get("fullz_type") == "business":
        await state.set_state(AddFullzStates.waiting_company_type)
        prompt = await _t(ui_texts, "seller.fullz.select_company",
                          "Выберите тип компании:", texts=texts)
        await message.answer(prompt, reply_markup=_company_kb(buttons))
    else:
        await state.set_state(AddFullzStates.waiting_credit_score)
        prompt = await _t(ui_texts, "seller.fullz.select_cs",
                          "Выберите фильтр по кредитному рейтингу:", texts=texts)
        await message.answer(prompt, reply_markup=_cs_kb("seller_fullz_back_state", buttons))


# ── Personal branch ────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("seller_fullz_cs:"), AddFullzStates.waiting_credit_score)
async def add_fullz_cs(callback: CallbackQuery, state: FSMContext, ui_texts, texts, buttons, **kwargs):
    cs = callback.data.split(":")[1]
    await state.update_data(credit_score=cs)
    data = await state.get_data()
    if data.get("fullz_type") == "business":
        await state.set_state(AddFullzStates.waiting_report_group)
        prompt = await _t(ui_texts, "seller.fullz.select_report",
                          "Выберите тип отчёта, включённого в набор:", texts=texts)
        await callback.message.edit_text(prompt, reply_markup=_report_kb("seller_fullz_back_cs", buttons))
    else:
        await state.set_state(AddFullzStates.waiting_age_range)
        prompt = await _t(ui_texts, "seller.fullz.select_age",
                          "Выберите возрастной диапазон:", texts=texts)
        await callback.message.edit_text(prompt, reply_markup=_age_kb(buttons))
    await callback.answer()


@router.callback_query(F.data.startswith("seller_fullz_age:"), AddFullzStates.waiting_age_range)
async def add_fullz_age(callback: CallbackQuery, state: FSMContext, ui_texts, texts, buttons, **kwargs):
    await state.update_data(age_range=callback.data.split(":")[1])
    await state.set_state(AddFullzStates.waiting_gender)
    prompt = await _t(ui_texts, "seller.fullz.select_gender",
                      "Выберите фильтр по полу:", texts=texts)
    await callback.message.edit_text(prompt, reply_markup=_gender_kb(buttons))
    await callback.answer()


@router.callback_query(F.data.startswith("seller_fullz_gender:"), AddFullzStates.waiting_gender)
async def add_fullz_gender(callback: CallbackQuery, state: FSMContext, ui_texts, texts, buttons, **kwargs):
    await state.update_data(gender=callback.data.split(":")[1])
    await state.set_state(AddFullzStates.waiting_report_group)
    prompt = await _t(ui_texts, "seller.fullz.select_report",
                      "Выберите тип отчёта, включённого в набор:", texts=texts)
    await callback.message.edit_text(prompt, reply_markup=_report_kb("seller_fullz_back_gender", buttons))
    await callback.answer()


# ── Business branch ────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("seller_fullz_company:"), AddFullzStates.waiting_company_type)
async def add_fullz_company(callback: CallbackQuery, state: FSMContext, ui_texts, texts, buttons, **kwargs):
    await state.update_data(company_type=callback.data.split(":")[1])
    await state.set_state(AddFullzStates.waiting_loan_size)
    prompt = await _t(ui_texts, "seller.fullz.select_loan",
                      "Выберите диапазон суммы займа:", texts=texts)
    await callback.message.edit_text(prompt, reply_markup=_loan_kb(buttons))
    await callback.answer()


@router.callback_query(F.data.startswith("seller_fullz_loan:"), AddFullzStates.waiting_loan_size)
async def add_fullz_loan(callback: CallbackQuery, state: FSMContext, ui_texts, texts, buttons, **kwargs):
    await state.update_data(loan_size=callback.data.split(":")[1])
    await state.set_state(AddFullzStates.waiting_credit_score)
    prompt = await _t(ui_texts, "seller.fullz.select_cs_biz",
                      "Выберите кредитный рейтинг генерального директора:", texts=texts)
    await callback.message.edit_text(prompt, reply_markup=_cs_kb("seller_fullz_back_loan", buttons))
    await callback.answer()


# ── Shared: report → quantity → description → price → file ────────────────

@router.callback_query(F.data.startswith("seller_fullz_report:"), AddFullzStates.waiting_report_group)
async def add_fullz_report(callback: CallbackQuery, state: FSMContext, ui_texts, texts, **kwargs):
    await state.update_data(report_group=callback.data.split(":")[1])
    await state.set_state(AddFullzStates.waiting_quantity)
    prompt = await _t(ui_texts, "seller.fullz.enter_quantity",
                      "Сколько полных наборов fullz входит в этот пакет?\n"
                      "(Введите число, напр. <code>1</code>, <code>5</code>)",
                      texts=texts)
    await callback.message.edit_text(prompt, reply_markup=_cancel_kb(), parse_mode="HTML")
    await callback.answer()


@router.message(AddFullzStates.waiting_quantity, F.text)
async def add_fullz_quantity(message: Message, state: FSMContext, ui_texts, texts, **kwargs):
    try:
        qty = int(message.text.strip())
        if qty < 1 or qty > 1000:
            raise ValueError
    except ValueError:
        err = getattr(texts, "FULLZ_INVALID_QUANTITY", "❌ Введите корректное число (1–1000).")
        await message.answer(err)
        return
    await state.update_data(quantity=qty)
    await state.set_state(AddFullzStates.waiting_description)
    prompt = await _t(ui_texts, "seller.fullz.description",
                      "Введите краткое описание (или отправьте <code>-</code> для пропуска):",
                      texts=texts)
    await message.answer(prompt, reply_markup=_cancel_kb(), parse_mode="HTML")


@router.message(AddFullzStates.waiting_description, F.text)
async def add_fullz_description(message: Message, state: FSMContext, ui_texts, texts, **kwargs):
    raw = message.text.strip()
    await state.update_data(seller_description=None if raw == "-" else raw)
    await state.set_state(AddFullzStates.waiting_price)
    prompt = await _t(ui_texts, "seller.fullz.enter_price",
                      "Введите вашу базовую цену в USD (напр. <code>150</code>):", texts=texts)
    await message.answer(prompt, reply_markup=_cancel_kb(), parse_mode="HTML")


@router.message(AddFullzStates.waiting_price, F.text)
async def add_fullz_price(message: Message, state: FSMContext, ui_texts, texts, **kwargs):
    price = _parse_price(message.text)
    if price is None:
        err = getattr(texts, "INVALID_PRICE", "❌ Некорректная цена. Введите положительное число.")
        await message.answer(err)
        return
    await state.update_data(seller_price=str(price))
    await state.set_state(AddFullzStates.waiting_data_file)
    prompt = await _t(ui_texts, "seller.fullz.upload_file",
                      "Загрузите файл с данными fullz (.txt, .csv, .zip).\n"
                      "Файл хранится в защищённом виде и используется для исполнения заказов.",
                      texts=texts)
    await message.answer(prompt, reply_markup=_cancel_kb())


@router.message(AddFullzStates.waiting_data_file, F.document)
async def add_fullz_file(message: Message, state: FSMContext, session: AsyncSession,
                          seller, ui_texts, texts, **kwargs):
    data = await state.get_data()
    lang  = _lang(kwargs)
    price = Decimal(str(data["seller_price"]))
    item_name = _build_item_name(data, lang)

    batch = await SellerUploadBatchService.create_batch(
        session,
        seller_id=seller.id,
        item_type="fullz",
        upload_mode="single",
        title=item_name,
        total_items=data.get("quantity", 1),
    )
    item = await SpecialStockService.add_fullz_item(
        session,
        seller_id=seller.id,
        upload_batch_id=batch.id,
        item_name=item_name,
        product_type="fullz",
        fullz_type=data.get("fullz_type", "personal"),
        state=data.get("state"),
        credit_score=data.get("credit_score", "any"),
        age_range=data.get("age_range", "any"),
        gender=data.get("gender", "any"),
        company_type=data.get("company_type"),
        loan_size=data.get("loan_size"),
        report_group=data.get("report_group", "basic"),
        quantity=data.get("quantity", 1),
        seller_description=data.get("seller_description"),
        data_file_path=message.document.file_id,
        seller_price=price,
        base_price=price,
        buyer_price=price,
        moderation_status="pending_moderation",
        is_in_stock=True,
        is_active=True,
    )
    await state.clear()
    confirm = await _t(
        ui_texts, "seller.fullz.created",
        "✅ Набор fullz отправлен на модерацию.\n\n"
        "🧑‍💼 Товар: {item_name}\n📋 Партия: #{batch_id}",
        texts=texts,
        item_name=item.item_name,
        batch_id=batch.id,
    )
    await message.answer(confirm)


# ─────────────────────────────────────────────────────────────────────────────
# Back navigation callbacks
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "seller_fullz_back_state")
async def fullz_back_state(callback: CallbackQuery, state: FSMContext, ui_texts, texts, **kwargs):
    await state.set_state(AddFullzStates.waiting_state)
    prompt = await _t(ui_texts, "seller.fullz.enter_state",
                      "Введите штат США (напр. <code>CA</code>) или <code>-</code> для любого:",
                      texts=texts)
    await callback.message.edit_text(prompt, reply_markup=_cancel_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "seller_fullz_back_cs")
async def fullz_back_cs(callback: CallbackQuery, state: FSMContext, ui_texts, texts, buttons, **kwargs):
    await state.set_state(AddFullzStates.waiting_credit_score)
    prompt = await _t(ui_texts, "seller.fullz.select_cs",
                      "Выберите фильтр по кредитному рейтингу:", texts=texts)
    await callback.message.edit_text(prompt, reply_markup=_cs_kb("seller_fullz_back_state", buttons))
    await callback.answer()


@router.callback_query(F.data == "seller_fullz_back_age")
async def fullz_back_age(callback: CallbackQuery, state: FSMContext, ui_texts, texts, buttons, **kwargs):
    await state.set_state(AddFullzStates.waiting_age_range)
    prompt = await _t(ui_texts, "seller.fullz.select_age", "Выберите возрастной диапазон:", texts=texts)
    await callback.message.edit_text(prompt, reply_markup=_age_kb(buttons))
    await callback.answer()


@router.callback_query(F.data == "seller_fullz_back_gender")
async def fullz_back_gender(callback: CallbackQuery, state: FSMContext, ui_texts, texts, buttons, **kwargs):
    await state.set_state(AddFullzStates.waiting_gender)
    prompt = await _t(ui_texts, "seller.fullz.select_gender", "Выберите фильтр по полу:", texts=texts)
    await callback.message.edit_text(prompt, reply_markup=_gender_kb(buttons))
    await callback.answer()


@router.callback_query(F.data == "seller_fullz_back_company")
async def fullz_back_company(callback: CallbackQuery, state: FSMContext, ui_texts, texts, buttons, **kwargs):
    await state.set_state(AddFullzStates.waiting_company_type)
    prompt = await _t(ui_texts, "seller.fullz.select_company", "Выберите тип компании:", texts=texts)
    await callback.message.edit_text(prompt, reply_markup=_company_kb(buttons))
    await callback.answer()


@router.callback_query(F.data == "seller_fullz_back_loan")
async def fullz_back_loan(callback: CallbackQuery, state: FSMContext, ui_texts, texts, buttons, **kwargs):
    await state.set_state(AddFullzStates.waiting_loan_size)
    prompt = await _t(ui_texts, "seller.fullz.select_loan", "Выберите диапазон суммы займа:", texts=texts)
    await callback.message.edit_text(prompt, reply_markup=_loan_kb(buttons))
    await callback.answer()
