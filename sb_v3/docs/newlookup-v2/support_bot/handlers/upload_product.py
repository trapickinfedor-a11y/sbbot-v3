from __future__ import annotations

"""
Единый хэндлер загрузки товаров воркерами (с правом can_load_products).

Один flow «📤 Загрузить товар» показывает все доступные категории:
  - PROS & FULLZ → загрузка файла (Product), 1 штука за раз
  - Subscriptions / Accounts → загрузка credentials (AccountInventory)
  - eSIM / GV → загрузка credentials (AccountInventory)

Воркер также может просматривать и удалять свои загруженные товары.
"""

import os
import uuid
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from support_bot.services.access_service import SupportBotActor
from support_bot.services.worker_service import WorkerService
from support_bot.keyboards.inline import back_to_menu_keyboard
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from shared.services.product_catalog_service import ProductCatalogManager
from shared.services.product_audit_service import log_product_action
from shared.database.models import (
    AccountCategory, AccountItem, AccountInventory, Product,
)
from web_panel.constants.categories import (
    ORDER_CATEGORY_TO_PRODUCT_KEY,
    ORDER_CATEGORY_TO_ACCOUNT_CODES,
    SELLER_ONLY_CATALOG_CATEGORIES,
)
from mirror_bot.constants.prices import ServicePrices

logger = logging.getLogger(__name__)

FULLZ_SERVICE_PRICE_MAP: dict[str, float] = {
    "fullz_700plus": float(ServicePrices.FULLZ_700_PLUS),
    "fullz_800plus": float(ServicePrices.FULLZ_800_PLUS_PROFILE),
    "fullz_under18": float(ServicePrices.FULLZ_UNDER_18),
    "fullz_immigrant": float(ServicePrices.FULLZ_IMMIGRANT),
    "fullz_zero_bank": float(ServicePrices.FULLZ_ZERO_BANK),
    "personal_random": float(ServicePrices.FULLZ_BASE),
}
FULLZ_STATE_SURCHARGE = float(ServicePrices.FULLZ_STATE_SURCHARGE)
router = Router(name="upload_product")

PRODUCTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "uploads", "products",
)
os.makedirs(PRODUCTS_DIR, exist_ok=True)

ALLOWED_FILE_TYPES = {
    "text/plain": "txt",
    "application/zip": "zip",
    "application/x-zip-compressed": "zip",
    "application/pdf": "pdf",
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/png": "png",
    "image/gif": "gif",
    "image/webp": "webp",
}

US_STATES = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
]

# ─────────────────────────────────────────────────────────────────
#  FSM States
# ─────────────────────────────────────────────────────────────────

class UploadProductStates(StatesGroup):
    category = State()     # выбор категории файлового товара (Product)
    service = State()      # выбор сервиса
    state = State()        # выбор штата
    name = State()         # ввод названия
    description = State()  # ввод описания
    file = State()         # отправка файла
    confirm = State()      # подтверждение перед сохранением


class UploadAccountStates(StatesGroup):
    select_item = State()       # выбор позиции из списка
    input_credentials = State() # отправка данных (1 строка = 1 аккаунт)


# ─────────────────────────────────────────────────────────────────
#  Helpers — permissions & data
# ─────────────────────────────────────────────────────────────────

def _worker_upload_sections(worker) -> dict:
    """Определяет какие секции загрузки доступны воркеру.

    Returns dict с ключами:
        'product_keys': set  — category_key для Product upload (e.g. {'pros_fullz'})
        'account_codes': set — AccountCategory.code для credentials upload
    """
    if not worker or not getattr(worker, "can_load_products", False):
        return {"product_keys": set(), "account_codes": set()}

    cats = set(worker.categories or [])
    product_keys = set()
    account_codes = set()

    for order_cat, product_key in ORDER_CATEGORY_TO_PRODUCT_KEY.items():
        if order_cat in cats:
            product_keys.add(product_key)

    for order_cat, acc_codes in ORDER_CATEGORY_TO_ACCOUNT_CODES.items():
        if order_cat in cats:
            account_codes.update(acc_codes)

    return {"product_keys": product_keys, "account_codes": account_codes}


def _admin_can_upload(actor: SupportBotActor | None) -> bool:
    if not actor or not actor.can_upload_catalogs:
        return False
    return actor.source == "system_admin" or bool(actor.allowed_catalogs)


async def _get_worker_account_items(
    session: AsyncSession, account_codes: set[str]
) -> list[tuple[AccountItem, str]]:
    """Returns active AccountItems filtered by allowed category codes."""
    if not account_codes:
        return []

    cats_result = await session.execute(
        select(AccountCategory)
        .where(AccountCategory.is_active == True, AccountCategory.code.in_(account_codes))
        .order_by(AccountCategory.position)
    )
    cats = {c.code: c.name for c in cats_result.scalars().all()}
    if not cats:
        return []

    items_result = await session.execute(
        select(AccountItem)
        .where(AccountItem.is_active == True, AccountItem.category_code.in_(cats.keys()))
        .order_by(AccountItem.category_code, AccountItem.position)
    )
    return [(i, cats.get(i.category_code, i.category_code)) for i in items_result.scalars().all()]


async def _get_stock_counts(session: AsyncSession, item_ids: list[int]) -> dict[int, int]:
    if not item_ids:
        return {}
    rows = await session.execute(
        select(AccountInventory.item_id, func.count(AccountInventory.id))
        .where(AccountInventory.item_id.in_(item_ids), AccountInventory.is_sold == False)
        .group_by(AccountInventory.item_id)
    )
    return dict(rows.all())


async def get_allowed_catalog(
    session: AsyncSession,
    worker=None,
    actor: SupportBotActor | None = None,
) -> dict:
    """Return product catalog categories/services the worker can upload files to."""
    await ProductCatalogManager.ensure_defaults(session)
    categories = await ProductCatalogManager.get_categories_payload(session, active_only=True)

    if worker is None:
        if _admin_can_upload(actor):
            return categories
        return {}

    sections = _worker_upload_sections(worker)
    filtered = {}
    for category_code, category_data in categories.items():
        if category_code in SELLER_ONLY_CATALOG_CATEGORIES:
            continue
        if category_code not in sections["product_keys"]:
            continue
        if category_data.get("services"):
            filtered[category_code] = category_data
    return filtered


# ─────────────────────────────────────────────────────────────────
#  Keyboards
# ─────────────────────────────────────────────────────────────────

def _upload_main_keyboard(
    product_categories: dict,
    has_account_items: bool,
    has_own_products: bool,
) -> InlineKeyboardMarkup:
    """Единое меню загрузки: файловые категории + аккаунты + мои товары."""
    rows: list[list[InlineKeyboardButton]] = []

    for k, v in product_categories.items():
        rows.append([InlineKeyboardButton(
            text=f"📂 {v['name']}  (файл)",
            callback_data=f"upload_cat:{k}",
        )])

    if has_account_items:
        rows.append([InlineKeyboardButton(
            text="📦 Загрузить аккаунты / credentials",
            callback_data="upload_acc_list",
        )])

    if has_own_products:
        rows.append([InlineKeyboardButton(
            text="🗂 Мои загруженные товары",
            callback_data="my_uploads",
        )])

    rows.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _acc_items_keyboard(
    items_with_cats: list[tuple[AccountItem, str]],
    counts: dict[int, int] | None = None,
) -> InlineKeyboardMarkup:
    counts = counts or {}
    rows: list[list[InlineKeyboardButton]] = []
    current_cat = None
    for item, cat_name in items_with_cats:
        if cat_name != current_cat:
            current_cat = cat_name
            rows.append([InlineKeyboardButton(text=f"── {cat_name} ──", callback_data="noop")])
        stock = counts.get(item.id, 0)
        stock_label = f"[{stock}]" if stock else "—"
        rows.append([InlineKeyboardButton(
            text=f"{item.name} — ${item.price}  {stock_label}",
            callback_data=f"accup_item:{item.id}",
        )])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="worker_upload_product")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _acc_done_keyboard(item_id: int, item_name: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"➕ Ещё в «{item_name}»", callback_data=f"accup_item:{item_id}")],
        [InlineKeyboardButton(text="📋 Другая позиция", callback_data="upload_acc_list")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")],
    ])


def _service_keyboard(category: str, product_categories: dict) -> InlineKeyboardMarkup:
    services = product_categories.get(category, {}).get("services", {})
    buttons = [
        [InlineKeyboardButton(text=name, callback_data=f"upload_svc:{svc}")]
        for svc, name in services.items()
    ]
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="worker_upload_product")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _state_keyboard() -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = []
    buttons.append([InlineKeyboardButton(
        text="🎲 ANY — $0", callback_data="upload_state:ANY",
    )])
    row: list[InlineKeyboardButton] = []
    for s in US_STATES:
        row.append(InlineKeyboardButton(
            text=f"{s} +${FULLZ_STATE_SURCHARGE:.0f}",
            callback_data=f"upload_state:{s}",
        ))
        if len(row) == 5:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="worker_upload_product")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_product_upload")],
    ])


# ─────────────────────────────────────────────────────────────────
#  Entry point — unified «Загрузить товар»
# ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "worker_upload_product")
async def start_upload(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    support_bot_actor: SupportBotActor | None = None,
):
    worker = await WorkerService.get_worker(session, callback.from_user.id)
    if not worker or not getattr(worker, "can_load_products", False):
        if not _admin_can_upload(support_bot_actor):
            await callback.answer("❌ Нет доступа к загрузке товаров", show_alert=True)
            return

    await state.clear()

    sections = _worker_upload_sections(worker) if worker else {"product_keys": set(), "account_codes": set()}
    product_categories = await get_allowed_catalog(session, worker, support_bot_actor)
    acc_items = await _get_worker_account_items(session, sections["account_codes"])

    has_own = False
    if worker:
        uploader_tag = f"worker:{callback.from_user.id}"
        cnt = await session.scalar(
            select(func.count(Product.id))
            .where(Product.uploaded_by == uploader_tag, Product.is_available == True, Product.is_active == True)
        )
        has_own = (cnt or 0) > 0

    if not product_categories and not acc_items:
        await callback.answer("❌ Для вас нет доступных категорий загрузки", show_alert=True)
        return

    await callback.message.edit_text(
        "📤 <b>Загрузка товара</b>\n\nВыберите категорию:",
        parse_mode="HTML",
        reply_markup=_upload_main_keyboard(product_categories, bool(acc_items), has_own),
    )
    await callback.answer()


# Keep old callback alive for backward compatibility
@router.callback_query(F.data == "worker_upload_accounts")
async def start_upload_accounts_redirect(callback: CallbackQuery, session: AsyncSession, state: FSMContext, support_bot_actor: SupportBotActor | None = None):
    callback.data = "worker_upload_product"
    await start_upload(callback, session, state, support_bot_actor)


@router.callback_query(F.data == "cancel_product_upload")
async def cancel_product_upload(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    temp_path = data.get("temp_file_path")
    if temp_path and os.path.exists(temp_path):
        try:
            os.remove(temp_path)
        except OSError:
            pass
    await state.clear()
    await callback.answer("❌ Загрузка отменена")
    await callback.message.edit_text("🏠 Загрузка отменена.", reply_markup=back_to_menu_keyboard())


# ─────────────────────────────────────────────────────────────────
#  Account Inventory Upload
# ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "upload_acc_list")
async def upload_acc_list(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    support_bot_actor: SupportBotActor | None = None,
):
    worker = await WorkerService.get_worker(session, callback.from_user.id)
    if not worker or not getattr(worker, "can_load_products", False):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    sections = _worker_upload_sections(worker)
    items = await _get_worker_account_items(session, sections["account_codes"])
    if not items:
        await callback.answer("❌ Нет доступных позиций для загрузки", show_alert=True)
        return

    counts = await _get_stock_counts(session, [i.id for i, _ in items])

    await state.clear()
    await state.set_state(UploadAccountStates.select_item)
    await callback.message.edit_text(
        "📦 <b>Загрузка аккаунтов</b>\n\nВыберите позицию — в скобках текущий остаток:",
        reply_markup=_acc_items_keyboard(items, counts),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("accup_item:"))
async def accup_select_item(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
):
    worker = await WorkerService.get_worker(session, callback.from_user.id)
    if not worker or not getattr(worker, "can_load_products", False):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    item_id = int(callback.data.split(":", 1)[1])
    item = await session.get(AccountItem, item_id)
    if not item:
        await callback.answer("❌ Позиция не найдена", show_alert=True)
        return

    sections = _worker_upload_sections(worker)
    if item.category_code not in sections["account_codes"]:
        await callback.answer("❌ У вас нет доступа к этой категории", show_alert=True)
        return

    count = await session.scalar(
        select(func.count(AccountInventory.id))
        .where(AccountInventory.item_id == item_id, AccountInventory.is_sold == False)
    )

    await state.update_data(item_id=item_id, item_name=item.name)
    await state.set_state(UploadAccountStates.input_credentials)
    await callback.message.edit_text(
        f"📦 <b>{item.name}</b>  💰 ${item.price}\n"
        f"📊 В наличии: <b>{count or 0}</b>\n\n"
        f"📌 <b>Правила загрузки:</b>\n"
        f"• Одна строка = один аккаунт / credentials\n"
        f"• Минимум 3 символа на строку\n"
        f"• Можно отправить несколько строк за раз\n"
        f"• Не включайте свои контактные данные\n\n"
        f"Отправьте данные:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад к списку", callback_data="upload_acc_list")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_product_upload")],
        ]),
    )
    await callback.answer()


@router.message(UploadAccountStates.input_credentials, F.text)
async def accup_receive_credentials(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
):
    worker = await WorkerService.get_worker(session, message.from_user.id)
    if not worker or not getattr(worker, "can_load_products", False):
        return

    data = await state.get_data()
    item_id = data.get("item_id")
    item_name = data.get("item_name", "Unknown")

    if not item_id:
        await message.answer("❌ Ошибка сессии, начните заново", reply_markup=back_to_menu_keyboard())
        await state.clear()
        return

    item = await session.get(AccountItem, item_id)
    if not item or not item.is_active:
        await message.answer("❌ Позиция была удалена или деактивирована.", reply_markup=back_to_menu_keyboard())
        await state.clear()
        return

    raw_lines = message.text.strip().splitlines()
    lines = [l.strip() for l in raw_lines if l.strip()]
    if not lines:
        await message.answer("❌ Пустое сообщение — отправьте данные аккаунтов")
        return

    MIN_CRED_LENGTH = 3
    skipped = 0
    valid_lines = []
    for line in lines:
        if len(line) < MIN_CRED_LENGTH:
            skipped += 1
            continue
        valid_lines.append(line)

    if not valid_lines:
        await message.answer(
            f"❌ Все строки слишком короткие (мин. {MIN_CRED_LENGTH} символов).\n"
            f"Отправьте корректные данные."
        )
        return

    uploaded_by = f"worker:{message.from_user.id}"
    added = 0
    for line in valid_lines:
        inv = AccountInventory(
            item_id=item_id,
            credentials={"data": line},
            uploaded_by=uploaded_by,
        )
        session.add(inv)
        added += 1

    try:
        await session.commit()
    except Exception as e:
        await session.rollback()
        logger.error("Account inventory upload error: %s", e)
        await message.answer(f"❌ Ошибка сохранения: {e}")
        await state.clear()
        return

    total = await session.scalar(
        select(func.count(AccountInventory.id))
        .where(AccountInventory.item_id == item_id, AccountInventory.is_sold == False)
    )

    skip_text = f"\n⚠️ Пропущено строк (слишком короткие): {skipped}" if skipped else ""
    await state.clear()
    await message.answer(
        f"✅ <b>Загружено: {added}</b>{skip_text}\n"
        f"📦 <b>{item_name}</b>\n"
        f"📊 В наличии: <b>{total}</b>",
        parse_mode="HTML",
        reply_markup=_acc_done_keyboard(item_id, item_name),
    )


# ─────────────────────────────────────────────────────────────────
#  Product (File) Upload
# ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("upload_cat:"))
async def select_category(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    support_bot_actor: SupportBotActor | None = None,
):
    worker = await WorkerService.get_worker(session, callback.from_user.id)
    if not ((worker and getattr(worker, "can_load_products", False)) or _admin_can_upload(support_bot_actor)):
        await callback.answer("Access denied", show_alert=True)
        return
    product_categories = await get_allowed_catalog(session, worker, support_bot_actor)
    cat = callback.data.split(":")[1]
    if cat not in product_categories:
        await callback.answer("Неверная категория", show_alert=True)
        return
    await state.update_data(category=cat)
    await state.set_state(UploadProductStates.service)
    await callback.message.edit_text(
        f"📤 Категория: <b>{product_categories[cat]['name']}</b>\n\nВыберите сервис:",
        reply_markup=_service_keyboard(cat, product_categories),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("upload_svc:"))
async def select_service(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    support_bot_actor: SupportBotActor | None = None,
):
    worker = await WorkerService.get_worker(session, callback.from_user.id)
    if not ((worker and getattr(worker, "can_load_products", False)) or _admin_can_upload(support_bot_actor)):
        await callback.answer("Access denied", show_alert=True)
        return
    svc = callback.data.split(":")[1]
    product_categories = await get_allowed_catalog(session, worker, support_bot_actor)
    current = await state.get_data()
    category = current.get("category")
    if not category or svc not in product_categories.get(category, {}).get("services", {}):
        await callback.answer("Сервис не назначен этому воркеру", show_alert=True)
        return
    catalog_svc = await ProductCatalogManager.get_service(session, svc)
    if not catalog_svc or not catalog_svc.is_active or catalog_svc.category_key != category:
        await callback.answer("❌ Сервис не найден или неактивен", show_alert=True)
        return
    await state.update_data(service=svc)
    await state.set_state(UploadProductStates.state)
    await callback.message.edit_text(
        f"📤 Сервис: <b>{product_categories[category]['services'][svc]}</b>\n\nВыберите штат:",
        reply_markup=_state_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("upload_state:"))
async def select_state(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    support_bot_actor: SupportBotActor | None = None,
):
    worker = await WorkerService.get_worker(session, callback.from_user.id)
    if not ((worker and getattr(worker, "can_load_products", False)) or _admin_can_upload(support_bot_actor)):
        await callback.answer("Access denied", show_alert=True)
        return
    st = callback.data.split(":")[1]
    data = await state.get_data()
    svc_code = data.get("service", "")

    base_price = FULLZ_SERVICE_PRICE_MAP.get(svc_code)
    if base_price is None:
        await callback.answer("❌ Не удалось определить цену для этого сервиса", show_alert=True)
        return

    final_price = base_price + (FULLZ_STATE_SURCHARGE if st != "ANY" else 0)
    state_label = st if st != "ANY" else "ANY (любой)"
    surcharge_note = f" (+${FULLZ_STATE_SURCHARGE:.0f} за штат)" if st != "ANY" else ""

    await state.update_data(state=st, price=final_price)
    await state.set_state(UploadProductStates.name)
    await callback.message.edit_text(
        f"📤 Штат: <b>{state_label}</b>\n"
        f"💰 Цена: <b>${final_price:.2f}</b>{surcharge_note}\n\n"
        f"Введите название товара:",
        reply_markup=_cancel_kb(),
        parse_mode="HTML",
    )
    await callback.answer()



@router.message(UploadProductStates.name, F.text)
async def input_name(message: Message, session: AsyncSession, state: FSMContext, support_bot_actor: SupportBotActor | None = None):
    worker = await WorkerService.get_worker(session, message.from_user.id)
    if not ((worker and getattr(worker, "can_load_products", False)) or _admin_can_upload(support_bot_actor)):
        return
    await state.update_data(name=message.text.strip())
    await state.set_state(UploadProductStates.description)
    await message.answer("Введите описание (или /skip чтобы пропустить):", reply_markup=_cancel_kb())


@router.message(UploadProductStates.description, F.text)
async def input_description(message: Message, session: AsyncSession, state: FSMContext, support_bot_actor: SupportBotActor | None = None):
    worker = await WorkerService.get_worker(session, message.from_user.id)
    if not ((worker and getattr(worker, "can_load_products", False)) or _admin_can_upload(support_bot_actor)):
        return
    desc = message.text.strip() if message.text != "/skip" else ""
    await state.update_data(description=desc)
    await state.set_state(UploadProductStates.file)
    await message.answer(
        "📎 <b>Отправьте файл товара</b>\n\n"
        "📌 <b>Правила загрузки:</b>\n"
        "• 1 файл = 1 товар (одна фулка / один документ)\n"
        "• Допустимые форматы: TXT, ZIP, PDF, JPG, PNG, GIF, WEBP\n"
        "• Макс. размер: 20 MB (лимит Telegram)\n"
        "• TXT-файл не должен быть пустым (мин. 10 символов)\n"
        "• Не включайте свои контактные данные в файл\n\n"
        "Отправьте файл или фото:",
        reply_markup=_cancel_kb(),
        parse_mode="HTML",
    )


@router.message(UploadProductStates.file, F.document | F.photo)
async def input_file(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    support_bot_actor: SupportBotActor | None = None,
):
    worker = await WorkerService.get_worker(session, message.from_user.id)
    if not ((worker and getattr(worker, "can_load_products", False)) or _admin_can_upload(support_bot_actor)):
        return

    file = message.document or (message.photo[-1] if message.photo else None)
    if not file:
        await message.answer("❌ Отправьте файл")
        return

    if message.document:
        mime = message.document.mime_type or ""
        ext = ALLOWED_FILE_TYPES.get(mime)
        original_name = message.document.file_name or f"file.{ext or 'bin'}"
    else:
        ext = "jpg"
        original_name = f"photo.{ext}"
    if not ext:
        await message.answer(f"❌ Неподдерживаемый формат. Разрешены: {', '.join(set(ALLOWED_FILE_TYPES.values()))}")
        return

    data = await state.get_data()
    unique_filename = f"{uuid.uuid4()}.{ext}"
    file_path = os.path.join(PRODUCTS_DIR, unique_filename)

    try:
        tg_file = await message.bot.get_file(file.file_id)
        await message.bot.download_file(tg_file.file_path, file_path)

        if ext in ("txt", "text"):
            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                content_stripped = content.strip()
                if not content_stripped or len(content_stripped) < 10:
                    os.remove(file_path)
                    await message.answer(
                        "❌ TXT-файл пустой или содержит менее 10 символов.\n"
                        "Отправьте корректный файл."
                    )
                    return
            except Exception:
                os.remove(file_path)
                await message.answer("❌ Не удалось прочитать TXT-файл. Проверьте кодировку (UTF-8).")
                return

        file_size = os.path.getsize(file_path)

        await state.update_data(
            temp_file_path=file_path,
            file_name=original_name,
            file_ext=ext,
            file_size=file_size,
        )
        await state.set_state(UploadProductStates.confirm)

        size_kb = file_size / 1024
        size_label = f"{size_kb:.1f} KB" if size_kb < 1024 else f"{size_kb / 1024:.2f} MB"
        await message.answer(
            f"📋 <b>Подтвердите загрузку</b>\n\n"
            f"📂 Категория: <b>{data.get('category', '?')}</b>\n"
            f"🔧 Сервис: <b>{data.get('service', '?')}</b>\n"
            f"📍 Штат: <b>{data.get('state', '?')}</b>\n"
            f"💰 Цена: <b>${data.get('price', 0):.2f}</b>\n"
            f"📝 Название: <b>{data.get('name', '?')}</b>\n"
            f"📎 Файл: <b>{original_name}</b> ({size_label})\n\n"
            f"Всё верно?",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Подтвердить", callback_data="upload_confirm_yes")],
                [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_product_upload")],
            ]),
        )
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        await message.answer(f"❌ Ошибка: {str(e)}")
        await state.clear()


@router.callback_query(F.data == "upload_confirm_yes", UploadProductStates.confirm)
async def confirm_upload(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    support_bot_actor: SupportBotActor | None = None,
):
    worker = await WorkerService.get_worker(session, callback.from_user.id)
    if not ((worker and getattr(worker, "can_load_products", False)) or _admin_can_upload(support_bot_actor)):
        await callback.answer("Access denied", show_alert=True)
        return

    data = await state.get_data()
    file_path = data.get("temp_file_path")
    if not file_path or not os.path.exists(file_path):
        await callback.answer("❌ Файл не найден, начните заново", show_alert=True)
        await state.clear()
        return

    try:
        from decimal import Decimal

        uploader = f"worker:{callback.from_user.id}" if worker else (
            f"admin:{support_bot_actor.admin_id or callback.from_user.id}" if support_bot_actor else f"unknown:{callback.from_user.id}"
        )

        product = Product(
            name=data["name"],
            description=data.get("description") or None,
            category=data["category"],
            service=data["service"],
            state=data["state"].upper(),
            price=Decimal(str(data["price"])),
            file_path=file_path,
            file_name=data.get("file_name", "file"),
            file_type=data.get("file_ext", "txt"),
            uploaded_by=uploader,
        )
        session.add(product)
        await session.commit()
        await session.refresh(product)

        try:
            await log_product_action(
                session,
                action="upload",
                actor_type="worker" if worker else "admin",
                actor_id=callback.from_user.id,
                product=product,
                details={
                    "category": product.category,
                    "service": product.service,
                    "state": product.state,
                    "file_name": product.file_name,
                },
            )
        except Exception:
            pass

        await state.clear()
        await callback.message.edit_text(
            f"✅ <b>Товар загружен!</b>\n\n"
            f"ID: {product.id}\n"
            f"Название: {product.name}\n"
            f"Цена: ${product.price}",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📤 Загрузить ещё", callback_data="worker_upload_product")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")],
            ]),
        )
        await callback.answer("✅ Загружено!")
    except Exception as e:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        await callback.message.edit_text(f"❌ Ошибка: {str(e)}", reply_markup=back_to_menu_keyboard())
        await state.clear()


# ─────────────────────────────────────────────────────────────────
#  My Uploads — view & delete own products
# ─────────────────────────────────────────────────────────────────

MY_UPLOADS_PAGE_SIZE = 10


@router.callback_query(F.data.startswith("my_uploads"))
async def my_uploads(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
):
    worker = await WorkerService.get_worker(session, callback.from_user.id)
    if not worker:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    await state.clear()
    uploader_tag = f"worker:{callback.from_user.id}"

    page = 0
    if ":" in callback.data and callback.data != "my_uploads":
        parts = callback.data.split(":")
        if len(parts) == 2 and parts[1].isdigit():
            page = int(parts[1])

    total = await session.scalar(
        select(func.count(Product.id))
        .where(Product.uploaded_by == uploader_tag, Product.is_available == True, Product.is_active == True)
    )
    total = total or 0

    if total == 0:
        await callback.message.edit_text(
            "🗂 <b>Мои товары</b>\n\nУ вас нет загруженных товаров.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📤 Загрузить товар", callback_data="worker_upload_product")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")],
            ]),
        )
        await callback.answer()
        return

    offset = page * MY_UPLOADS_PAGE_SIZE
    products = (await session.execute(
        select(Product)
        .where(Product.uploaded_by == uploader_tag, Product.is_available == True, Product.is_active == True)
        .order_by(Product.created_at.desc())
        .offset(offset).limit(MY_UPLOADS_PAGE_SIZE)
    )).scalars().all()

    rows: list[list[InlineKeyboardButton]] = []
    for p in products:
        status = "✅" if p.moderation_status == "approved" else ("⏳" if p.moderation_status == "pending_moderation" else "❌")
        rows.append([InlineKeyboardButton(
            text=f"{status} {p.name} — ${p.price} ({p.state})",
            callback_data=f"my_prod:{p.id}",
        )])

    nav_row: list[InlineKeyboardButton] = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️", callback_data=f"my_uploads:{page - 1}"))
    total_pages = (total + MY_UPLOADS_PAGE_SIZE - 1) // MY_UPLOADS_PAGE_SIZE
    nav_row.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="noop"))
    if page + 1 < total_pages:
        nav_row.append(InlineKeyboardButton(text="➡️", callback_data=f"my_uploads:{page + 1}"))
    if nav_row:
        rows.append(nav_row)

    rows.append([InlineKeyboardButton(text="📤 Загрузить товар", callback_data="worker_upload_product")])
    rows.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")])

    await callback.message.edit_text(
        f"🗂 <b>Мои товары</b>  ({total} шт.)\n\n"
        f"✅ = одобрен  ⏳ = на модерации  ❌ = отклонён",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("my_prod:"))
async def my_prod_detail(
    callback: CallbackQuery,
    session: AsyncSession,
):
    worker = await WorkerService.get_worker(session, callback.from_user.id)
    if not worker:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    product_id = int(callback.data.split(":")[1])
    uploader_tag = f"worker:{callback.from_user.id}"
    product = await session.get(Product, product_id)

    if not product or product.uploaded_by != uploader_tag:
        await callback.answer("❌ Товар не найден или не ваш", show_alert=True)
        return

    status_map = {
        "approved": "✅ Одобрен",
        "pending_moderation": "⏳ На модерации",
        "rejected": "❌ Отклонён",
        "changes_requested": "🔄 Требуются изменения",
    }
    status_text = status_map.get(product.moderation_status, product.moderation_status)

    text = (
        f"🗂 <b>{product.name}</b>\n\n"
        f"📂 Категория: {product.category}\n"
        f"🔧 Сервис: {product.service}\n"
        f"📍 Штат: {product.state}\n"
        f"💰 Цена: ${product.price}\n"
        f"📄 Файл: {product.file_type}\n"
        f"📋 Статус: {status_text}\n"
        f"📅 Загружен: {product.created_at.strftime('%d.%m.%Y %H:%M')}\n"
    )
    if product.moderation_comment:
        text += f"💬 Комментарий: {product.moderation_comment}\n"

    rows = []
    if product.is_available and product.is_active:
        rows.append([InlineKeyboardButton(text="🗑 Удалить товар", callback_data=f"del_prod:{product.id}")])
    rows.append([InlineKeyboardButton(text="⬅️ Назад к списку", callback_data="my_uploads")])
    rows.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")])

    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    await callback.answer()


@router.callback_query(F.data.startswith("del_prod:"))
async def delete_product_confirm(callback: CallbackQuery, session: AsyncSession):
    worker = await WorkerService.get_worker(session, callback.from_user.id)
    if not worker:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    product_id = int(callback.data.split(":")[1])
    uploader_tag = f"worker:{callback.from_user.id}"
    product = await session.get(Product, product_id)

    if not product or product.uploaded_by != uploader_tag:
        await callback.answer("❌ Товар не найден или не ваш", show_alert=True)
        return

    await callback.message.edit_text(
        f"🗑 Удалить товар <b>{product.name}</b> (${product.price}, {product.state})?\n\n"
        f"Это действие нельзя отменить.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"del_prod_yes:{product.id}")],
            [InlineKeyboardButton(text="❌ Нет, отмена", callback_data=f"my_prod:{product.id}")],
        ]),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("del_prod_yes:"))
async def delete_product_execute(callback: CallbackQuery, session: AsyncSession):
    worker = await WorkerService.get_worker(session, callback.from_user.id)
    if not worker:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    product_id = int(callback.data.split(":")[1])
    uploader_tag = f"worker:{callback.from_user.id}"
    product = await session.get(Product, product_id)

    if not product or product.uploaded_by != uploader_tag:
        await callback.answer("❌ Товар не найден или не ваш", show_alert=True)
        return

    product.is_active = False
    product.is_available = False
    await session.commit()

    try:
        await log_product_action(
            session,
            action="delete",
            actor_type="worker",
            actor_id=callback.from_user.id,
            product=product,
            details={"reason": "worker_self_delete"},
        )
    except Exception:
        pass

    if product.file_path and os.path.exists(product.file_path):
        try:
            os.remove(product.file_path)
        except OSError:
            pass

    await callback.message.edit_text(
        f"✅ Товар <b>{product.name}</b> удалён.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🗂 Мои товары", callback_data="my_uploads")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")],
        ]),
    )
    await callback.answer()
