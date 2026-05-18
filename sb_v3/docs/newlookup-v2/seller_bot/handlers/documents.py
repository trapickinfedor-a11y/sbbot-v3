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

router = Router(name="seller_documents")

# ─────────────────────────────────────────────────────────────────────────────
# Own keyboards — defined inside this module (Своя клавиатура)
# ─────────────────────────────────────────────────────────────────────────────

_DOC_TYPE_LABELS_RU: dict[str, str] = {
    "dl_front_back": "🪪 Права (Перед+Зад)",
    "dl_selfie":     "🤳 Права + Селфи",
    "passport":      "🛂 Паспорт",
    "business_docs": "🏢 Бизнес-документы",
}
_DOC_TYPE_LABELS_EN: dict[str, str] = {
    "dl_front_back": "🪪 Driver's License (Front+Back)",
    "dl_selfie":     "🤳 Driver's License + Selfie",
    "passport":      "🛂 Passport",
    "business_docs": "🏢 Business Docs",
}


def _doc_label(subtype: str, lang: str = "en") -> str:
    if lang == "ru":
        return _DOC_TYPE_LABELS_RU.get(subtype, subtype)
    return _DOC_TYPE_LABELS_EN.get(subtype, subtype)


def _doc_type_keyboard(buttons=None) -> InlineKeyboardMarkup:
    if buttons and getattr(buttons, "DOC_TYPE_DL", None):
        rows = [
            [InlineKeyboardButton(text=buttons.DOC_TYPE_DL,       callback_data="seller_doc_type:dl_front_back")],
            [InlineKeyboardButton(text=buttons.DOC_TYPE_DL_SELFIE, callback_data="seller_doc_type:dl_selfie")],
            [InlineKeyboardButton(text=buttons.DOC_TYPE_PASSPORT,  callback_data="seller_doc_type:passport")],
            [InlineKeyboardButton(text=buttons.DOC_TYPE_BUSINESS,  callback_data="seller_doc_type:business_docs")],
        ]
    else:
        rows = [
            [InlineKeyboardButton(text="🪪 Права (Перед+Зад)",  callback_data="seller_doc_type:dl_front_back")],
            [InlineKeyboardButton(text="🤳 Права + Селфи",      callback_data="seller_doc_type:dl_selfie")],
            [InlineKeyboardButton(text="🛂 Паспорт",             callback_data="seller_doc_type:passport")],
            [InlineKeyboardButton(text="🏢 Бизнес-документы",   callback_data="seller_doc_type:business_docs")],
        ]
    rows.append([InlineKeyboardButton(text="❌ Отмена", callback_data="seller_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _doc_quality_keyboard(buttons=None) -> InlineKeyboardMarkup:
    std = (buttons and getattr(buttons, "DOC_QUALITY_STANDARD", None)) or "⭐ Стандарт"
    pre = (buttons and getattr(buttons, "DOC_QUALITY_PREMIUM",  None)) or "💎 Премиум"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=std, callback_data="seller_doc_quality:standard")],
        [InlineKeyboardButton(text=pre, callback_data="seller_doc_quality:premium")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="seller_menu")],
    ])


def _yes_no_keyboard(prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да",    callback_data=f"{prefix}:yes"),
            InlineKeyboardButton(text="❌ Нет",   callback_data=f"{prefix}:no"),
        ],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="seller_menu")],
    ])


def _cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="seller_menu")],
    ])


def _skip_cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭ Пропустить", callback_data="seller_doc_skip_desc")],
        [InlineKeyboardButton(text="❌ Отмена",     callback_data="seller_menu")],
    ])


def _doc_list_keyboard(items: list, lang: str = "en") -> InlineKeyboardMarkup:
    rows = []
    for item in items:
        label = _doc_label(item.product_subtype, lang)
        stock = "✅" if item.is_in_stock else "❌"
        rows.append([InlineKeyboardButton(
            text=f"{stock} {label} | {item.state or 'ANY'} | ${item.seller_price}",
            callback_data=f"seller_doc_detail:{item.id}",
        )])
    add_text  = "➕ Добавить документ" if lang == "ru" else "➕ Add Document"
    back_text = "⬅️ Назад" if lang == "ru" else "⬅️ Back"
    rows.append([InlineKeyboardButton(text=add_text,  callback_data="seller_add_doc")])
    rows.append([InlineKeyboardButton(text=back_text, callback_data="seller_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _doc_detail_keyboard(item_id: int, is_in_stock: bool, lang: str = "en") -> InlineKeyboardMarkup:
    if lang == "ru":
        toggle = "❌ Снять с продажи" if is_in_stock else "✅ Выставить на продажу"
        delete_text = "🗑 Удалить"
        back_text   = "⬅️ К документам"
    else:
        toggle      = "❌ Set Out of Stock" if is_in_stock else "✅ Set In Stock"
        delete_text = "🗑 Delete"
        back_text   = "⬅️ Back to Docs"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=toggle,     callback_data=f"seller_doc_toggle:{item_id}")],
        [InlineKeyboardButton(text=delete_text, callback_data=f"seller_doc_delete:{item_id}")],
        [InlineKeyboardButton(text=back_text,   callback_data="seller_my_docs")],
    ])


# ─────────────────────────────────────────────────────────────────────────────
# FSM states
# ─────────────────────────────────────────────────────────────────────────────

class AddDocumentStates(StatesGroup):
    waiting_doc_type     = State()
    waiting_state        = State()
    waiting_quality      = State()
    waiting_has_hologram = State()
    waiting_has_selfie   = State()
    waiting_description  = State()
    waiting_price        = State()
    waiting_sample       = State()


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
    """Fetch UI string: DB translation → texts class attr → hardcoded default."""
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
            "❌ Для загрузки документов необходим депозит пакета Bank."
            if lang == "ru" else
            "❌ Bank package deposit is required to upload documents."
        )
    return None


def _lang(kwargs: dict) -> str:
    return getattr(kwargs.get("seller"), "language", None) or "en"


# ─────────────────────────────────────────────────────────────────────────────
# My Documents list
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "seller_my_docs")
async def my_docs_handler(callback: CallbackQuery, session: AsyncSession, seller, ui_texts, texts, **kwargs):
    if not seller:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    lang = _lang(kwargs)
    from sqlalchemy import select as _sel
    from shared.database.models import SellerDocumentItem
    q = await session.execute(
        _sel(SellerDocumentItem)
        .where(SellerDocumentItem.seller_id == seller.id, SellerDocumentItem.is_active == True)
        .order_by(SellerDocumentItem.created_at.desc())
        .limit(30)
    )
    items = q.scalars().all()
    header = await _t(ui_texts, "seller.docs.list_header",
                      "📄 <b>My Documents</b>\n\nYour uploaded document templates:",
                      texts=texts)
    await callback.message.edit_text(
        header, reply_markup=_doc_list_keyboard(items, lang), parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("seller_doc_detail:"))
async def doc_detail_handler(callback: CallbackQuery, session: AsyncSession, seller, texts, **kwargs):
    lang = _lang(kwargs)
    item_id = int(callback.data.split(":")[1])
    from sqlalchemy import select as _sel
    from shared.database.models import SellerDocumentItem
    q = await session.execute(_sel(SellerDocumentItem).where(SellerDocumentItem.id == item_id))
    item = q.scalar_one_or_none()
    if not item or item.seller_id != seller.id:
        err = getattr(texts, "DOC_NOT_FOUND", "❌ Товар не найден")
        await callback.answer(err, show_alert=True)
        return
    label = _doc_label(item.product_subtype, lang)
    mod = item.moderation_status.replace("_", " ").title()
    if lang == "ru":
        body = (
            f"📄 <b>{label}</b>\n\n"
            f"🗺 Штат: <b>{item.state or 'ЛЮБОЙ'}</b>\n"
            f"⭐ Качество: <b>{item.quality.title()}</b>\n"
            f"🔒 Голограмма: {'✅' if item.has_hologram else '❌'}\n"
            f"🤳 Селфи: {'✅' if item.has_selfie else '❌'}\n"
            f"💰 Цена продавца: <b>${item.seller_price}</b>\n"
            f"🏷 Цена покупателя: <b>${item.buyer_price}</b>\n"
            f"📋 Статус: <b>{mod}</b>\n"
            f"📦 В наличии: {'✅' if item.is_in_stock else '❌'}"
        )
    else:
        body = (
            f"📄 <b>{label}</b>\n\n"
            f"🗺 State: <b>{item.state or 'ANY'}</b>\n"
            f"⭐ Quality: <b>{item.quality.title()}</b>\n"
            f"🔒 Hologram: {'✅' if item.has_hologram else '❌'}\n"
            f"🤳 Selfie: {'✅' if item.has_selfie else '❌'}\n"
            f"💰 Seller price: <b>${item.seller_price}</b>\n"
            f"🏷 Buyer price: <b>${item.buyer_price}</b>\n"
            f"📋 Status: <b>{mod}</b>\n"
            f"📦 In stock: {'✅' if item.is_in_stock else '❌'}"
        )
    if item.seller_description:
        body += f"\n📝 {item.seller_description}"
    await callback.message.edit_text(
        body, reply_markup=_doc_detail_keyboard(item.id, item.is_in_stock, lang), parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("seller_doc_toggle:"))
async def doc_toggle_handler(callback: CallbackQuery, session: AsyncSession, seller, texts, **kwargs):
    lang = _lang(kwargs)
    item_id = int(callback.data.split(":")[1])
    from sqlalchemy import select as _sel
    from shared.database.models import SellerDocumentItem
    q = await session.execute(_sel(SellerDocumentItem).where(SellerDocumentItem.id == item_id))
    item = q.scalar_one_or_none()
    if not item or item.seller_id != seller.id:
        await callback.answer(getattr(texts, "DOC_NOT_FOUND", "❌ Товар не найден"), show_alert=True)
        return
    item.is_in_stock = not item.is_in_stock
    await session.commit()
    status = ("✅ В наличии" if item.is_in_stock else "❌ Нет в наличии") if lang == "ru" \
             else ("✅ In Stock" if item.is_in_stock else "❌ Out of Stock")
    await callback.answer(status)
    await callback.message.edit_reply_markup(
        reply_markup=_doc_detail_keyboard(item.id, item.is_in_stock, lang)
    )


@router.callback_query(F.data.startswith("seller_doc_delete:"))
async def doc_delete_handler(callback: CallbackQuery, session: AsyncSession, seller, ui_texts, texts, **kwargs):
    item_id = int(callback.data.split(":")[1])
    from sqlalchemy import select as _sel
    from shared.database.models import SellerDocumentItem
    q = await session.execute(_sel(SellerDocumentItem).where(SellerDocumentItem.id == item_id))
    item = q.scalar_one_or_none()
    if not item or item.seller_id != seller.id:
        await callback.answer(getattr(texts, "DOC_NOT_FOUND", "❌ Товар не найден"), show_alert=True)
        return
    item.is_active = False
    item.is_in_stock = False
    await session.commit()
    await callback.answer(getattr(texts, "DOC_DELETED", "🗑 Удалено"))
    await my_docs_handler(callback, session, seller, ui_texts, texts, **kwargs)


# ─────────────────────────────────────────────────────────────────────────────
# Add Document FSM
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "seller_add_doc")
async def add_doc_start(callback: CallbackQuery, state: FSMContext, seller, ui_texts, texts, buttons, **kwargs):
    lang = _lang(kwargs)
    error = _check_deposit(seller, kwargs.get("seller_actor"), lang)
    if error:
        await callback.answer(error, show_alert=True)
        return
    await state.clear()
    await state.set_state(AddDocumentStates.waiting_doc_type)
    prompt = await _t(ui_texts, "seller.docs.select_type",
                      "📄 <b>Добавить шаблон документа</b>\n\nВыберите тип документа:",
                      texts=texts)
    await callback.message.edit_text(
        prompt, reply_markup=_doc_type_keyboard(buttons), parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("seller_doc_type:"), AddDocumentStates.waiting_doc_type)
async def add_doc_type(callback: CallbackQuery, state: FSMContext, ui_texts, texts, **kwargs):
    doc_type = callback.data.split(":")[1]
    await state.update_data(doc_type=doc_type)
    await state.set_state(AddDocumentStates.waiting_state)
    prompt = await _t(ui_texts, "seller.docs.enter_state",
                      "Введите штат США (напр. <code>CA</code>, <code>NY</code>) "
                      "или <code>-</code> для любого штата:",
                      texts=texts)
    await callback.message.edit_text(prompt, reply_markup=_cancel_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.message(AddDocumentStates.waiting_state, F.text)
async def add_doc_state(message: Message, state: FSMContext, ui_texts, texts, buttons, **kwargs):
    raw = message.text.strip()
    await state.update_data(state=None if raw == "-" else raw.upper()[:2])
    await state.set_state(AddDocumentStates.waiting_quality)
    prompt = await _t(ui_texts, "seller.docs.select_quality",
                      "Выберите качество документа:", texts=texts)
    await message.answer(prompt, reply_markup=_doc_quality_keyboard(buttons))


@router.callback_query(F.data.startswith("seller_doc_quality:"), AddDocumentStates.waiting_quality)
async def add_doc_quality(callback: CallbackQuery, state: FSMContext, ui_texts, texts, **kwargs):
    quality = callback.data.split(":")[1]
    await state.update_data(quality=quality)
    await state.set_state(AddDocumentStates.waiting_has_hologram)
    prompt = await _t(ui_texts, "seller.docs.has_hologram",
                      "Документ содержит голограмму / защитный элемент?", texts=texts)
    await callback.message.edit_text(prompt, reply_markup=_yes_no_keyboard("seller_doc_hologram"))
    await callback.answer()


@router.callback_query(F.data.startswith("seller_doc_hologram:"), AddDocumentStates.waiting_has_hologram)
async def add_doc_hologram(callback: CallbackQuery, state: FSMContext, ui_texts, texts, **kwargs):
    has_hologram = callback.data.split(":")[1] == "yes"
    await state.update_data(has_hologram=has_hologram)
    data = await state.get_data()
    if data.get("doc_type") == "dl_selfie":
        await state.set_state(AddDocumentStates.waiting_has_selfie)
        prompt = await _t(ui_texts, "seller.docs.has_selfie",
                          "Включено живое селфи владельца?", texts=texts)
        await callback.message.edit_text(prompt, reply_markup=_yes_no_keyboard("seller_doc_selfie"))
    else:
        await state.update_data(has_selfie=False)
        await state.set_state(AddDocumentStates.waiting_description)
        prompt = await _t(ui_texts, "seller.docs.description",
                          "Введите краткое описание (или нажмите Пропустить):", texts=texts)
        await callback.message.edit_text(prompt, reply_markup=_skip_cancel_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("seller_doc_selfie:"), AddDocumentStates.waiting_has_selfie)
async def add_doc_selfie(callback: CallbackQuery, state: FSMContext, ui_texts, texts, **kwargs):
    await state.update_data(has_selfie=callback.data.split(":")[1] == "yes")
    await state.set_state(AddDocumentStates.waiting_description)
    prompt = await _t(ui_texts, "seller.docs.description",
                      "Введите краткое описание (или нажмите Пропустить):", texts=texts)
    await callback.message.edit_text(prompt, reply_markup=_skip_cancel_keyboard())
    await callback.answer()


@router.callback_query(F.data == "seller_doc_skip_desc", AddDocumentStates.waiting_description)
async def add_doc_skip_desc(callback: CallbackQuery, state: FSMContext, ui_texts, texts, **kwargs):
    await state.update_data(seller_description=None)
    await state.set_state(AddDocumentStates.waiting_price)
    prompt = await _t(ui_texts, "seller.docs.enter_price",
                      "Введите вашу базовую цену в USD (напр. <code>25</code>):", texts=texts)
    await callback.message.edit_text(prompt, reply_markup=_cancel_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.message(AddDocumentStates.waiting_description, F.text)
async def add_doc_description(message: Message, state: FSMContext, ui_texts, texts, **kwargs):
    await state.update_data(seller_description=message.text.strip())
    await state.set_state(AddDocumentStates.waiting_price)
    prompt = await _t(ui_texts, "seller.docs.enter_price",
                      "Введите вашу базовую цену в USD (напр. <code>25</code>):", texts=texts)
    await message.answer(prompt, reply_markup=_cancel_keyboard(), parse_mode="HTML")


@router.message(AddDocumentStates.waiting_price, F.text)
async def add_doc_price(message: Message, state: FSMContext, ui_texts, texts, **kwargs):
    price = _parse_price(message.text)
    if price is None:
        err = getattr(texts, "INVALID_PRICE",
                      "❌ Некорректная цена. Введите положительное число.")
        await message.answer(err)
        return
    await state.update_data(seller_price=str(price))
    await state.set_state(AddDocumentStates.waiting_sample)
    prompt = await _t(ui_texts, "seller.docs.upload_sample",
                      "Загрузите пример документа (фото или файл).\n"
                      "Используется только для проверки администратором.", texts=texts)
    await message.answer(prompt, reply_markup=_cancel_keyboard())


@router.message(AddDocumentStates.waiting_sample, F.photo | F.document)
async def add_doc_sample(message: Message, state: FSMContext, session: AsyncSession,
                         seller, ui_texts, texts, **kwargs):
    data = await state.get_data()
    lang = _lang(kwargs)
    file_id  = message.document.file_id if message.document else message.photo[-1].file_id
    doc_type = data["doc_type"]
    label    = _doc_label(doc_type, lang)
    state_str = data.get("state") or "ANY"
    price    = Decimal(str(data["seller_price"]))
    item_name = f"{label} | {state_str} | {data.get('quality', 'standard').title()}"

    batch = await SellerUploadBatchService.create_batch(
        session,
        seller_id=seller.id,
        item_type="document",
        upload_mode="single",
        title=item_name,
        total_items=1,
    )
    item = await SpecialStockService.add_document_item(
        session,
        seller_id=seller.id,
        upload_batch_id=batch.id,
        item_name=item_name,
        product_type="docs",
        product_subtype=doc_type,
        state=data.get("state"),
        quality=data.get("quality", "standard"),
        has_hologram=bool(data.get("has_hologram")),
        has_selfie=bool(data.get("has_selfie")),
        seller_description=data.get("seller_description"),
        sample_file_path=file_id,
        seller_price=price,
        base_price=price,
        buyer_price=price,
        moderation_status="pending_moderation",
        is_in_stock=True,
        is_active=True,
    )
    await state.clear()
    confirm = await _t(
        ui_texts, "seller.docs.created",
        "✅ Шаблон документа отправлен на модерацию.\n\n"
        "📄 Товар: {item_name}\n📋 Партия: #{batch_id}",
        texts=texts,
        item_name=item.item_name,
        batch_id=batch.id,
    )
    await message.answer(confirm)


@router.message(AddDocumentStates.waiting_sample)
async def add_doc_sample_invalid(message: Message, **kwargs):
    await message.answer(
        "❌ Please send a photo or document file, or press Cancel.",
        reply_markup=_cancel_keyboard(),
    )
