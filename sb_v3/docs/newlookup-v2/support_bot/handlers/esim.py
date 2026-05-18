from __future__ import annotations

"""
Панель управления тарифами eSIM — support_bot.

  • SMS-тарифы  — матрица оператор × период  (ServicePrice в БД)
  • Data-тарифы — колонка ГБ                 (ServicePrice в БД)
  • Google Voice — список продуктовых позиций (AccountItem в БД)
  • Редактирование SMS/Data цен через FSM
  • Засев SMS/Data и GV тарифов отдельными кнопками

Своя клавиатура — весь inline_keyboard определён прямо здесь.
Свои константы: support_bot/constants/buttons_esim.py
Доступ: только actor.is_admin_like.
"""

import logging
from decimal import Decimal, InvalidOperation

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from support_bot.services.access_service import SupportBotActor
from support_bot.constants.buttons_esim import ESIMAdminBtns
from shared.database.models import ServicePrice, AccountCategory, AccountItem, AccountInventory

logger = logging.getLogger(__name__)
router = Router(name="admin_esim")


# ─── FSM ──────────────────────────────────────────────────────────────────────

class ESIMAdminStates(StatesGroup):
    editing_price = State()


# ─── Константы ────────────────────────────────────────────────────────────────

_OPERATORS   = ["verizon", "att", "tmobile"]
_OP_LABELS   = {"verizon": "Verizon", "att": "AT&T", "tmobile": "T-Mobile"}
_SMS_PERIODS = ["1", "3", "6"]
_DATA_GBS    = ["5", "10", "15"]

# SMS + Data дефолты → засеиваются кнопкой «Заполнить SMS/Data тарифы»
_ESIM_DEFAULTS: dict[str, tuple[str, float]] = {
    "esim_verizon_1m": ("Verizon SMS 1 месяц",    45.0),
    "esim_verizon_3m": ("Verizon SMS 3 месяца",   90.0),
    "esim_verizon_6m": ("Verizon SMS 6 месяцев", 160.0),
    "esim_att_1m":     ("AT&T SMS 1 месяц",        40.0),
    "esim_att_3m":     ("AT&T SMS 3 месяца",       80.0),
    "esim_att_6m":     ("AT&T SMS 6 месяцев",     145.0),
    "esim_tmobile_1m": ("T-Mobile SMS 1 месяц",    38.0),
    "esim_tmobile_3m": ("T-Mobile SMS 3 месяца",   75.0),
    "esim_tmobile_6m": ("T-Mobile SMS 6 месяцев", 135.0),
    "esim_data_5gb":   ("eSIM Data 5 ГБ",          25.0),
    "esim_data_10gb":  ("eSIM Data 10 ГБ",         45.0),
    "esim_data_15gb":  ("eSIM Data 15 ГБ",         60.0),
}

# GV — код категории в AccountCategory
_GV_CAT_CODE = "gv"

# GV дефолтные позиции → засеиваются кнопкой «Заполнить GV тарифы»
_GV_ITEM_DEFAULTS = [
    {"code": "gv_gmail_3m6m",      "name": "Google Voice | Old Gmail (3m-6m)",              "price": 10.0, "position": 1},
    {"code": "gv_gmail_2fa",       "name": "Google Voice (With 2FA) | Old Gmail (3m-9m)",   "price": 12.0, "position": 2},
    {"code": "gv_area_code",       "name": "Specific Area Code GV | Old Gmail (6m-1y)",     "price": 15.0, "position": 3},
    {"code": "gv_gmail_2005_2014", "name": "Google Voice | Old Gmail (2005-2014)",           "price": 22.0, "position": 4},
]

# eSIM SMS — категория + позиции (AccountCategory + AccountItem)
_ESIM_SMS_CAT_CODE = "esim_sms"
_ESIM_SMS_ITEM_DEFAULTS = [
    {"code": "esim_sms_verizon_1m",  "name": "Verizon SMS — 1 month",   "price": 20.0, "position": 1},
    {"code": "esim_sms_verizon_3m",  "name": "Verizon SMS — 3 months",  "price": 50.0, "position": 2},
    {"code": "esim_sms_verizon_6m",  "name": "Verizon SMS — 6 months",  "price": 70.0, "position": 3},
    {"code": "esim_sms_att_1m",      "name": "AT&T SMS — 1 month",      "price": 35.0, "position": 4},
    {"code": "esim_sms_att_3m",      "name": "AT&T SMS — 3 months",     "price": 50.0, "position": 5},
    {"code": "esim_sms_att_6m",      "name": "AT&T SMS — 6 months",     "price": 70.0, "position": 6},
    {"code": "esim_sms_tmobile_1m",  "name": "T-Mobile SMS — 1 month",  "price": 35.0, "position": 7},
    {"code": "esim_sms_tmobile_3m",  "name": "T-Mobile SMS — 3 months", "price": 50.0, "position": 8},
    {"code": "esim_sms_tmobile_6m",  "name": "T-Mobile SMS — 6 months", "price": 70.0, "position": 9},
]

# eSIM Data — категория + позиции
_ESIM_DATA_CAT_CODE = "esim_data"
_ESIM_DATA_ITEM_DEFAULTS = [
    {"code": "esim_data_verizon_5gb",   "name": "Verizon Data — 5 GB",   "price": 25.0, "position": 1},
    {"code": "esim_data_verizon_10gb",  "name": "Verizon Data — 10 GB",  "price": 40.0, "position": 2},
    {"code": "esim_data_verizon_15gb",  "name": "Verizon Data — 15 GB",  "price": 50.0, "position": 3},
    {"code": "esim_data_att_5gb",       "name": "AT&T Data — 5 GB",      "price": 25.0, "position": 4},
    {"code": "esim_data_att_10gb",      "name": "AT&T Data — 10 GB",     "price": 40.0, "position": 5},
    {"code": "esim_data_att_15gb",      "name": "AT&T Data — 15 GB",     "price": 50.0, "position": 6},
    {"code": "esim_data_tmobile_5gb",   "name": "T-Mobile Data — 5 GB",  "price": 25.0, "position": 7},
    {"code": "esim_data_tmobile_10gb",  "name": "T-Mobile Data — 10 GB", "price": 40.0, "position": 8},
    {"code": "esim_data_tmobile_15gb",  "name": "T-Mobile Data — 15 GB", "price": 50.0, "position": 9},
]


# ─── Своя клавиатура ──────────────────────────────────────────────────────────

def _main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=ESIMAdminBtns.SMS_PRICES,    callback_data="admin_esim_sms")],
        [InlineKeyboardButton(text=ESIMAdminBtns.DATA_PRICES,   callback_data="admin_esim_data")],
        [InlineKeyboardButton(text=ESIMAdminBtns.GV_PRICES,     callback_data="admin_esim_gv")],
        [InlineKeyboardButton(text=ESIMAdminBtns.SEED_DEFAULTS, callback_data="admin_esim_seed")],
        [InlineKeyboardButton(text="🌱 Заполнить SMS позиции",  callback_data="admin_esim_sms_seed")],
        [InlineKeyboardButton(text="🌱 Заполнить Data позиции", callback_data="admin_esim_data_seed")],
        [InlineKeyboardButton(text=ESIMAdminBtns.MAIN_MENU,     callback_data="main_menu")],
    ])


def _sms_kb(prices: dict[str, ServicePrice]) -> InlineKeyboardMarkup:
    """Матрица оператор × период. Каждая ячейка с ценой нажимаема для редактирования."""
    rows: list[list[InlineKeyboardButton]] = []

    rows.append([
        InlineKeyboardButton(text="·", callback_data="esim_admin_noop"),
        *[InlineKeyboardButton(text=f"{p}мес", callback_data="esim_admin_noop") for p in _SMS_PERIODS],
    ])
    for op in _OPERATORS:
        row = [InlineKeyboardButton(text=_OP_LABELS[op], callback_data="esim_admin_noop")]
        for period in _SMS_PERIODS:
            key = f"esim_{op}_{period}m"
            p = prices.get(key)
            label = f"${float(p.price):.0f}" if p else "—"
            pid = p.id if p else 0
            row.append(InlineKeyboardButton(
                text=label,
                callback_data=f"admin_esim_edit:{pid}:{key}",
            ))
        rows.append(row)

    rows.append([
        InlineKeyboardButton(text=ESIMAdminBtns.REFRESH, callback_data="admin_esim_sms"),
        InlineKeyboardButton(text=ESIMAdminBtns.BACK,    callback_data="admin_esim_menu"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _data_kb(prices: dict[str, ServicePrice]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for gb in _DATA_GBS:
        key = f"esim_data_{gb}gb"
        p = prices.get(key)
        label = f"${float(p.price):.0f}" if p else "—"
        pid = p.id if p else 0
        rows.append([
            InlineKeyboardButton(text=f"Data {gb} ГБ", callback_data="esim_admin_noop"),
            InlineKeyboardButton(text=label, callback_data=f"admin_esim_edit:{pid}:{key}"),
        ])
    rows.append([
        InlineKeyboardButton(text=ESIMAdminBtns.REFRESH, callback_data="admin_esim_data"),
        InlineKeyboardButton(text=ESIMAdminBtns.BACK,    callback_data="admin_esim_menu"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _gv_kb(items_with_counts: list[tuple]) -> InlineKeyboardMarkup:
    """Список GV-продуктов с остатками + своя кнопка засева."""
    rows: list[list[InlineKeyboardButton]] = []
    for item, avail, total in items_with_counts:
        status = "✅" if item.is_active else "⏸"
        rows.append([InlineKeyboardButton(
            text=f"{status} {item.name} — ${item.price}  [{avail}/{total}]",
            callback_data=f"admin_accounts_item:{item.id}",
        )])
    rows.append([
        InlineKeyboardButton(text=ESIMAdminBtns.GV_SEED, callback_data="admin_esim_gv_seed"),
    ])
    rows.append([
        InlineKeyboardButton(text=ESIMAdminBtns.REFRESH, callback_data="admin_esim_gv"),
        InlineKeyboardButton(text=ESIMAdminBtns.BACK,    callback_data="admin_esim_menu"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _cancel_edit_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=ESIMAdminBtns.CANCEL, callback_data="admin_esim_cancel_edit")],
    ])


def _after_edit_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=ESIMAdminBtns.SMS_PRICES,  callback_data="admin_esim_sms")],
        [InlineKeyboardButton(text=ESIMAdminBtns.DATA_PRICES, callback_data="admin_esim_data")],
        [InlineKeyboardButton(text=ESIMAdminBtns.BACK,        callback_data="admin_esim_menu")],
    ])


# ─── Проверка доступа ─────────────────────────────────────────────────────────

def _is_admin(actor: SupportBotActor | None) -> bool:
    return actor is not None and actor.is_admin_like


# ─── Вспомогательные функции ──────────────────────────────────────────────────

async def _load_prices(session: AsyncSession) -> dict[str, ServicePrice]:
    result = await session.execute(
        select(ServicePrice).where(ServicePrice.category == "esim")
    )
    return {p.key: p for p in result.scalars().all()}


async def _load_gv_items(session: AsyncSession) -> list[tuple]:
    """Загружает GV-позиции из AccountItem с подсчётом остатков."""
    items_result = await session.execute(
        select(AccountItem)
        .where(AccountItem.category_code == _GV_CAT_CODE)
        .order_by(AccountItem.position, AccountItem.id)
    )
    items = items_result.scalars().all()

    out: list[tuple] = []
    for item in items:
        avail = await session.scalar(
            select(func.count(AccountInventory.id))
            .where(AccountInventory.item_id == item.id, AccountInventory.is_sold == False)
        ) or 0
        total = await session.scalar(
            select(func.count(AccountInventory.id))
            .where(AccountInventory.item_id == item.id)
        ) or 0
        out.append((item, avail, total))
    return out


# ─── Хэндлеры ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_esim_menu")
async def esim_menu(
    callback: CallbackQuery,
    session: AsyncSession,
    support_bot_actor: SupportBotActor | None = None,
):
    if not _is_admin(support_bot_actor):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    prices = await _load_prices(session)
    seeded = len(prices) > 0
    seed_hint = "✅ Тарифы загружены" if seeded else "⚠️ Тарифов нет — нажмите «Заполнить SMS/Data тарифы»"

    gv_count = await session.scalar(
        select(func.count(AccountItem.id))
        .where(AccountItem.category_code == _GV_CAT_CODE, AccountItem.is_active == True)
    ) or 0

    text = (
        "📶 <b>Панель eSIM</b>\n\n"
        f"💾 Записей SMS/Data тарифов в БД: <b>{len(prices)}</b>\n"
        f"📞 GV позиций: <b>{gv_count}</b>\n"
        f"{seed_hint}"
    )
    await callback.message.edit_text(text, reply_markup=_main_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_esim_sms")
async def esim_sms_prices(
    callback: CallbackQuery,
    session: AsyncSession,
    support_bot_actor: SupportBotActor | None = None,
):
    if not _is_admin(support_bot_actor):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    prices = await _load_prices(session)
    text = (
        "📱 <b>SMS тарифы</b>\n\n"
        "Нажмите на цену чтобы изменить.\n"
        "Таблица: <i>оператор × месяцы</i>"
    )
    await callback.message.edit_text(text, reply_markup=_sms_kb(prices), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_esim_data")
async def esim_data_prices(
    callback: CallbackQuery,
    session: AsyncSession,
    support_bot_actor: SupportBotActor | None = None,
):
    if not _is_admin(support_bot_actor):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    prices = await _load_prices(session)
    text = "💾 <b>Data тарифы</b>\n\nНажмите на цену чтобы изменить."
    await callback.message.edit_text(text, reply_markup=_data_kb(prices), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_esim_gv")
async def esim_gv_prices(
    callback: CallbackQuery,
    session: AsyncSession,
    support_bot_actor: SupportBotActor | None = None,
):
    if not _is_admin(support_bot_actor):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    items_with_counts = await _load_gv_items(session)

    if not items_with_counts:
        seed_hint = "⚠️ Позиций нет — нажмите «Заполнить GV тарифы»"
    else:
        total_avail = sum(a for _, a, _ in items_with_counts)
        seed_hint = f"✅ {len(items_with_counts)} позиций, {total_avail} шт. в наличии"

    text = (
        "📞 <b>Google Voice — позиции</b>\n\n"
        f"{seed_hint}\n\n"
        "Нажмите на позицию для просмотра деталей и остатков."
    )
    await callback.message.edit_text(text, reply_markup=_gv_kb(items_with_counts), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_esim_gv_seed")
async def esim_gv_seed(
    callback: CallbackQuery,
    session: AsyncSession,
    support_bot_actor: SupportBotActor | None = None,
):
    if not _is_admin(support_bot_actor):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    # Создаём категорию GV если не существует
    cat_result = await session.execute(
        select(AccountCategory).where(AccountCategory.code == _GV_CAT_CODE)
    )
    if not cat_result.scalar_one_or_none():
        session.add(AccountCategory(
            code=_GV_CAT_CODE,
            name="Google Voice",
            category_type="gv",
            position=10,
            is_active=True,
        ))
        await session.flush()

    # Создаём позиции которых ещё нет
    created = 0
    for item_data in _GV_ITEM_DEFAULTS:
        existing = await session.execute(
            select(AccountItem).where(AccountItem.code == item_data["code"])
        )
        if not existing.scalar_one_or_none():
            session.add(AccountItem(
                code=item_data["code"],
                name=item_data["name"],
                category_code=_GV_CAT_CODE,
                price=item_data["price"],
                position=item_data["position"],
                is_active=True,
            ))
            created += 1

    await session.commit()
    await callback.answer(
        f"✅ GV: создано {created} позиций (уже существующие пропущены)",
        show_alert=True,
    )


@router.callback_query(F.data == "admin_esim_seed")
async def esim_seed(
    callback: CallbackQuery,
    session: AsyncSession,
    support_bot_actor: SupportBotActor | None = None,
):
    if not _is_admin(support_bot_actor):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    created = 0
    for i, (key, (display_name, price)) in enumerate(_ESIM_DEFAULTS.items()):
        existing = await session.execute(select(ServicePrice).where(ServicePrice.key == key))
        if not existing.scalar_one_or_none():
            session.add(ServicePrice(
                key=key, category="esim",
                display_name=display_name,
                price=price, position=i,
            ))
            created += 1
    await session.commit()
    await callback.answer(
        f"✅ Добавлено {created} SMS/Data записей (уже существующие пропущены)",
        show_alert=True,
    )


@router.callback_query(F.data.startswith("admin_esim_edit:"))
async def esim_start_edit(
    callback: CallbackQuery,
    state: FSMContext,
    support_bot_actor: SupportBotActor | None = None,
):
    if not _is_admin(support_bot_actor):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    parts = callback.data.split(":")
    price_id = int(parts[1])
    price_key = parts[2]

    if price_id == 0:
        await callback.answer(
            "⚠️ Тариф ещё не в БД — сначала нажмите «Заполнить SMS/Data тарифы»",
            show_alert=True,
        )
        return

    await state.update_data(edit_price_id=price_id, edit_price_key=price_key)
    await state.set_state(ESIMAdminStates.editing_price)
    await callback.message.edit_text(
        f"✏️ <b>Редактирование цены</b>\n\n"
        f"Ключ: <code>{price_key}</code>\n\n"
        f"Введите новую цену (например: <code>45</code> или <code>45.50</code>):",
        reply_markup=_cancel_edit_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "admin_esim_cancel_edit")
async def esim_cancel_edit(
    callback: CallbackQuery,
    state: FSMContext,
    support_bot_actor: SupportBotActor | None = None,
):
    await state.clear()
    await callback.message.edit_text(
        "📶 <b>Панель eSIM</b>\n\n<i>Редактирование отменено.</i>",
        reply_markup=_main_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(ESIMAdminStates.editing_price, F.text)
async def esim_receive_price(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    support_bot_actor: SupportBotActor | None = None,
):
    if not _is_admin(support_bot_actor):
        return

    data = await state.get_data()
    price_id: int = data.get("edit_price_id")
    price_key: str = data.get("edit_price_key", "")

    try:
        new_price = Decimal(message.text.strip().replace(",", "."))
        if new_price <= 0:
            await message.answer("❌ Цена должна быть больше 0, попробуйте снова:")
            return
    except InvalidOperation:
        await message.answer(
            "❌ Неверный формат — введите число, например <code>45</code> или <code>45.50</code>",
            parse_mode="HTML",
        )
        return

    result = await session.execute(select(ServicePrice).where(ServicePrice.id == price_id))
    price_row = result.scalar_one_or_none()
    if not price_row:
        await message.answer(
            "❌ Запись тарифа не найдена — возможно, была удалена.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=ESIMAdminBtns.BACK, callback_data="admin_esim_menu")]
            ]),
        )
        await state.clear()
        return

    old_price = price_row.price
    price_row.price = new_price
    await session.commit()
    await state.clear()

    await message.answer(
        f"✅ <b>Цена обновлена</b>\n\n"
        f"🔑 Ключ: <code>{price_key}</code>\n"
        f"📉 Было: <b>${float(old_price):.2f}</b>\n"
        f"📈 Стало: <b>${float(new_price):.2f}</b>",
        parse_mode="HTML",
        reply_markup=_after_edit_kb(),
    )


@router.callback_query(F.data == "admin_esim_sms_seed")
async def esim_sms_seed(
    callback: CallbackQuery,
    session: AsyncSession,
    support_bot_actor: SupportBotActor | None = None,
):
    if not _is_admin(support_bot_actor):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    cat_result = await session.execute(
        select(AccountCategory).where(AccountCategory.code == _ESIM_SMS_CAT_CODE)
    )
    if not cat_result.scalar_one_or_none():
        session.add(AccountCategory(
            code=_ESIM_SMS_CAT_CODE,
            name="eSIM SMS",
            category_type="esim_sms",
            position=20,
            is_active=True,
        ))
        await session.flush()

    created = 0
    for item_data in _ESIM_SMS_ITEM_DEFAULTS:
        existing = await session.execute(
            select(AccountItem).where(AccountItem.code == item_data["code"])
        )
        if not existing.scalar_one_or_none():
            session.add(AccountItem(
                code=item_data["code"],
                name=item_data["name"],
                category_code=_ESIM_SMS_CAT_CODE,
                price=item_data["price"],
                position=item_data["position"],
                is_active=True,
            ))
            created += 1

    await session.commit()
    await callback.answer(
        f"✅ eSIM SMS: создано {created} позиций (уже существующие пропущены)",
        show_alert=True,
    )


@router.callback_query(F.data == "admin_esim_data_seed")
async def esim_data_seed(
    callback: CallbackQuery,
    session: AsyncSession,
    support_bot_actor: SupportBotActor | None = None,
):
    if not _is_admin(support_bot_actor):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    cat_result = await session.execute(
        select(AccountCategory).where(AccountCategory.code == _ESIM_DATA_CAT_CODE)
    )
    if not cat_result.scalar_one_or_none():
        session.add(AccountCategory(
            code=_ESIM_DATA_CAT_CODE,
            name="eSIM Data",
            category_type="esim_data",
            position=21,
            is_active=True,
        ))
        await session.flush()

    created = 0
    for item_data in _ESIM_DATA_ITEM_DEFAULTS:
        existing = await session.execute(
            select(AccountItem).where(AccountItem.code == item_data["code"])
        )
        if not existing.scalar_one_or_none():
            session.add(AccountItem(
                code=item_data["code"],
                name=item_data["name"],
                category_code=_ESIM_DATA_CAT_CODE,
                price=item_data["price"],
                position=item_data["position"],
                is_active=True,
            ))
            created += 1

    await session.commit()
    await callback.answer(
        f"✅ eSIM Data: создано {created} позиций (уже существующие пропущены)",
        show_alert=True,
    )


@router.callback_query(F.data == "esim_admin_noop")
async def esim_noop(callback: CallbackQuery):
    await callback.answer()
