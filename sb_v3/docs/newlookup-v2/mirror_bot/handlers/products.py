"""
Handlers для работы с товарами.
"""
from __future__ import annotations

import os
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from mirror_bot.keyboards.inline import InlineKeyboardMarkup, InlineKeyboardButton
from mirror_bot.utils.message_utils import safe_edit_message, safe_answer_callback
from mirror_bot.services.product_service import ProductService
from mirror_bot.states.profile import ProfileStates
from mirror_bot.constants.buttons_en import ButtonTexts
from mirror_bot.constants.language_loader import get_texts
from shared.services.product_audit_service import log_product_action
from shared.services.product_catalog_service import ProductCatalogManager
from shared.services.guarantee_policy_service import format_guarantee_window, is_guarantee_active
import logging

logger = logging.getLogger(__name__)
router = Router()

async def get_service_display_name(session: AsyncSession, category: str, service: str) -> str:
    catalog_service = await ProductCatalogManager.get_service(session, service)
    if catalog_service and catalog_service.category_key == category:
        return catalog_service.name
    return ProductCatalogManager.format_service_label(service)


def create_products_keyboard(products_data: dict, category: str, service: str, state: str) -> InlineKeyboardMarkup:
    """Создать клавиатуру со списком товаров"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    products = products_data["products"]
    
    # Добавляем товары
    for product in products:
        price_text = f"${product['price']:.2f}"
        file_type_emoji = {
            'txt': '📄',
            'pdf': '📋', 
            'zip': '📦',
            'jpg': '🖼️',
            'png': '🖼️',
            'gif': '🖼️',
            'webp': '🖼️'
        }.get(product['file_type'], '📄')
        
        button_text = f"{file_type_emoji} {product['name']} - {price_text}"
        callback_data = f"product_view:{product['id']}"
        
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text=button_text, callback_data=callback_data)
        ])
    
    # Пагинация
    pagination_row = []
    if products_data["has_prev"]:
        pagination_row.append(
            InlineKeyboardButton(
                text="⬅️ Prev",
                callback_data=f"products_page:{category}:{service}:{state}:{products_data['page'] - 1}"
            )
        )

    if products_data["has_next"]:
        pagination_row.append(
            InlineKeyboardButton(
                text="Next ➡️",
                callback_data=f"products_page:{category}:{service}:{state}:{products_data['page'] + 1}"
            )
        )
    
    if pagination_row:
        keyboard.inline_keyboard.append(pagination_row)
    
    # Информация о странице
    page_info = f"Page {products_data['page']}/{products_data['total_pages']} ({products_data['total']} items)"
    keyboard.inline_keyboard.append([
        InlineKeyboardButton(text=page_info, callback_data="noop")
    ])
    
    # Кнопка назад
    from mirror_bot.constants.language_loader import get_texts
    temp_texts = get_texts('en')  # Fallback
    keyboard.inline_keyboard.append([
        InlineKeyboardButton(text=temp_texts.BACK_TO_STATES_BUTTON, callback_data=f"back_to_states:{category}:{service}")
    ])
    
    return keyboard


def create_product_detail_keyboard(product_id: int) -> InlineKeyboardMarkup:
    """Создать клавиатуру для детального просмотра товара"""
    
    from mirror_bot.constants.language_loader import get_texts
    temp_texts = get_texts('en')  # Fallback
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=temp_texts.BUY_NOW_BUTTON, callback_data=f"product_buy:{product_id}")],
        [InlineKeyboardButton(text=temp_texts.BACK_TO_LIST_BUTTON, callback_data=f"product_back:{product_id}")]
    ])


def create_product_confirm_keyboard(product_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Confirm", callback_data=f"product_buy_confirm:{product_id}")],
        [InlineKeyboardButton(text="❌ Cancel", callback_data=f"product_view:{product_id}")],
    ])


def create_product_access_keyboard(purchase_id: int, file_type: str) -> InlineKeyboardMarkup:
    button_text = "📦 Download ZIP" if file_type.lower() == "zip" else "🔓 Open Data"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=button_text, callback_data=f"product_access:{purchase_id}")],
    ])


def create_product_feedback_keyboard(
    purchase_id: int,
    *,
    can_report: bool,
    is_worker_product: bool = False,
) -> InlineKeyboardMarkup:
    rows: list = []
    if not is_worker_product:
        rows.append([InlineKeyboardButton(text="👍 Like", callback_data=f"product_rate:{purchase_id}:like")])
        rows.append([InlineKeyboardButton(text="👎 Dislike", callback_data=f"product_rate:{purchase_id}:dislike")])
        if can_report:
            rows.append([InlineKeyboardButton(text="💬 What is wrong?", callback_data=f"product_report:{purchase_id}")])
    rows.append([InlineKeyboardButton(text="⬅️ Back", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def create_purchase_detail_keyboard(
    purchase_id: int,
    *,
    delivered: bool,
    can_report: bool,
    back_callback: str,
    texts,
    is_worker_product: bool = False,
) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text="🔓 Open Data", callback_data=f"product_access:{purchase_id}")]]
    if delivered and not is_worker_product:
        rows.extend(
            [
                [InlineKeyboardButton(text="👍 Like", callback_data=f"product_rate:{purchase_id}:like")],
                [InlineKeyboardButton(text="👎 Dislike", callback_data=f"product_rate:{purchase_id}:dislike")],
            ]
        )
        if can_report:
            rows.append([InlineKeyboardButton(text="💬 What is wrong?", callback_data=f"product_report:{purchase_id}")])
    rows.append([InlineKeyboardButton(text=getattr(texts, "BACK", "⬅️ Back"), callback_data=back_callback)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _history_filter_context(filter_kind: str | None, filter_value: str | None) -> tuple[str, str]:
    normalized_kind = (filter_kind or "all").strip().lower()
    normalized_value = (filter_value or "all").strip()
    if normalized_kind not in {"all", "category", "seller"}:
        normalized_kind = "all"
    if normalized_kind == "all":
        normalized_value = "all"
    return normalized_kind, normalized_value or "all"


def _history_filter_label(texts, filter_kind: str, filter_value: str) -> str:
    if filter_kind == "category" and filter_value != "all":
        return f"{getattr(texts, 'PURCHASE_HISTORY_FILTER_CATEGORY', '🗂 By Categories')}: {filter_value}"
    if filter_kind == "seller" and filter_value != "all":
        return f"{getattr(texts, 'PURCHASE_HISTORY_FILTER_SELLER', '👨‍💼 By Sellers')}: {filter_value}"
    return getattr(texts, "HISTORY_FILTER_ALL", "📋 All Categories")


def _build_purchase_history_keyboard(history: dict, texts, *, filter_kind: str, filter_value: str) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(
                text=getattr(texts, "PURCHASE_HISTORY_FILTER_CATEGORY", "🗂 By Categories"),
                callback_data="history_filter:category",
            )
        ],
        [
            InlineKeyboardButton(
                text=getattr(texts, "PURCHASE_HISTORY_FILTER_SELLER", "👨‍💼 By Sellers"),
                callback_data="history_filter:seller",
            )
        ],
    ]
    for item in history["items"]:
        rows.append(
            [
                InlineKeyboardButton(
                    text=(
                        f"#{item['id']} | {item['product']['name'][:18]} | ${item['amount']:.2f}"
                    ),
                    callback_data=(
                        f"purchase_history_detail:{item['id']}:{history['page']}:{filter_kind}:{filter_value}"
                    ),
                )
            ]
        )
        rows.append(
            [
                InlineKeyboardButton(
                    text=getattr(texts, "PURCHASE_HISTORY_DETAILS", "Details"),
                    callback_data=(
                        f"purchase_history_detail:{item['id']}:{history['page']}:{filter_kind}:{filter_value}"
                    ),
                )
            ]
        )

    pagination_row: list[InlineKeyboardButton] = []
    if history["page"] > 1:
        pagination_row.append(
            InlineKeyboardButton(
                text="<<",
                callback_data=f"history_page:{history['page'] - 1}:{filter_kind}:{filter_value}",
            )
        )
    if history["page"] * history["limit"] < history["total"]:
        pagination_row.append(
            InlineKeyboardButton(
                text=">>",
                callback_data=f"history_page:{history['page'] + 1}:{filter_kind}:{filter_value}",
            )
        )
    if pagination_row:
        rows.append(pagination_row)
    rows.append([InlineKeyboardButton(text=getattr(texts, "BACK", "⬅️ Back"), callback_data="back_to_profile")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _build_filter_options_keyboard(kind: str, options: list[dict], texts) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(
                text=getattr(texts, "HISTORY_FILTER_ALL", "📋 All Categories"),
                callback_data=f"history_filter_apply:{kind}:all",
            )
        ]
    ]
    for option in options:
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{option['name']} [{option['count']}]",
                    callback_data=f"history_filter_apply:{kind}:{option['id']}",
                )
            ]
        )
    rows.append([InlineKeyboardButton(text=getattr(texts, "BACK", "⬅️ Back"), callback_data="product_purchase_history")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _render_purchase_history_text(history: dict, texts, *, filter_kind: str, filter_value: str) -> str:
    title = getattr(texts, "PURCHASE_HISTORY_TITLE", "📦 My Purchases")
    lines = [f"<b>{title}</b>", "", _history_filter_label(texts, filter_kind, filter_value), ""]
    if not history["items"]:
        lines.append(getattr(texts, "PURCHASE_HISTORY_EMPTY", "You do not have any purchases yet."))
        return "\n".join(lines)
    for item in history["items"]:
        lines.extend(
            [
                f"#{item['id']} | <b>{item['product']['name']}</b>",
                f"${item['amount']:.2f} | {item['status']} | {item['created_at'].strftime('%Y-%m-%d %H:%M')}",
                f"{item['seller']['name']} | {item['product']['category_id']}/{item['product']['service_name']}",
                "",
            ]
        )
    return "\n".join(lines).strip()


async def _load_purchase_history(
    session: AsyncSession,
    *,
    user_id: int,
    mirror_bot_id: int,
    page: int,
    filter_kind: str,
    filter_value: str,
) -> dict:
    kwargs = {
        "user_id": user_id,
        "mirror_bot_id": mirror_bot_id,
        "page": page,
        "limit": 10,
    }
    if filter_kind == "category" and filter_value != "all":
        kwargs["category_id"] = filter_value
    if filter_kind == "seller" and filter_value != "all":
        kwargs["seller_id"] = int(filter_value)
    return await ProductService.get_user_purchase_history(session, **kwargs)


async def _show_purchase_history(
    callback: CallbackQuery,
    session: AsyncSession,
    mirror_bot_id: int,
    texts,
    *,
    page: int = 1,
    filter_kind: str = "all",
    filter_value: str = "all",
) -> None:
    filter_kind, filter_value = _history_filter_context(filter_kind, filter_value)
    history = await _load_purchase_history(
        session,
        user_id=callback.from_user.id,
        mirror_bot_id=mirror_bot_id,
        page=page,
        filter_kind=filter_kind,
        filter_value=filter_value,
    )
    await safe_edit_message(
        callback,
        _render_purchase_history_text(history, texts, filter_kind=filter_kind, filter_value=filter_value),
        _build_purchase_history_keyboard(history, texts, filter_kind=filter_kind, filter_value=filter_value),
        parse_mode="HTML",
    )


def _extract_forwarded_channel_id(message: Message) -> int | None:
    forward_from_chat = getattr(message, "forward_from_chat", None)
    if forward_from_chat and getattr(forward_from_chat, "type", None) == "channel":
        return int(forward_from_chat.id)
    forward_origin = getattr(message, "forward_origin", None)
    chat = getattr(forward_origin, "chat", None)
    if chat and getattr(chat, "type", None) == "channel":
        return int(chat.id)
    return None


def _format_purchase_status(purchase) -> str:
    if getattr(purchase, "report_status", None) == "reported":
        return "reported"
    if getattr(purchase, "delivered_at", None):
        return "delivered"
    return "purchased"


@router.message(F.text.in_(ButtonTexts.get_all_variants("MY_PURCHASES")))
async def my_purchases_message(message: Message, session: AsyncSession, mirror_bot_id: int, texts, buttons):
    history = await ProductService.get_user_purchase_history(
        session,
        user_id=message.from_user.id,
        mirror_bot_id=mirror_bot_id,
        page=1,
        limit=10,
    )
    await message.answer(
        _render_purchase_history_text(history, texts, filter_kind="all", filter_value="all"),
        reply_markup=_build_purchase_history_keyboard(history, texts, filter_kind="all", filter_value="all"),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "product_purchase_history")
async def my_purchases_callback(callback: CallbackQuery, session: AsyncSession, mirror_bot_id: int, texts, buttons):
    await _show_purchase_history(callback, session, mirror_bot_id, texts, page=1)
    await safe_answer_callback(callback)


@router.callback_query(F.data.startswith("history_page:"))
async def purchase_history_page(callback: CallbackQuery, session: AsyncSession, mirror_bot_id: int, texts, buttons):
    _, _, page_raw, filter_kind, filter_value = callback.data.split(":", 4)
    await _show_purchase_history(
        callback,
        session,
        mirror_bot_id,
        texts,
        page=int(page_raw),
        filter_kind=filter_kind,
        filter_value=filter_value,
    )
    await safe_answer_callback(callback)


@router.callback_query(F.data.startswith("history_filter:"))
async def purchase_history_filter(callback: CallbackQuery, session: AsyncSession, mirror_bot_id: int, texts, buttons):
    filter_kind = callback.data.split(":", 1)[1]
    options = await ProductService.get_user_purchase_filters(
        session,
        user_id=callback.from_user.id,
        mirror_bot_id=mirror_bot_id,
    )
    if filter_kind == "category":
        text = getattr(texts, "PURCHASE_HISTORY_SELECT_CATEGORY", "Choose a category filter:")
        keyboard = _build_filter_options_keyboard("category", options["categories"], texts)
    else:
        text = getattr(texts, "PURCHASE_HISTORY_SELECT_SELLER", "Choose a seller filter:")
        keyboard = _build_filter_options_keyboard("seller", options["sellers"], texts)
    await safe_edit_message(callback, text, keyboard, parse_mode=None)
    await safe_answer_callback(callback)


@router.callback_query(F.data.startswith("history_filter_apply:"))
async def purchase_history_filter_apply(callback: CallbackQuery, session: AsyncSession, mirror_bot_id: int, texts, buttons):
    _, _, filter_kind, filter_value = callback.data.split(":", 3)
    await _show_purchase_history(
        callback,
        session,
        mirror_bot_id,
        texts,
        page=1,
        filter_kind=filter_kind,
        filter_value=filter_value,
    )
    await safe_answer_callback(callback)


@router.callback_query(F.data.startswith("purchase_history_detail:"))
async def purchase_history_detail(callback: CallbackQuery, session: AsyncSession, mirror_bot_id: int, texts, buttons):
    _, _, purchase_id_raw, page_raw, filter_kind, filter_value = callback.data.split(":", 5)
    purchase_id = int(purchase_id_raw)
    purchase = await ProductService.get_purchase(session, purchase_id, user_id=callback.from_user.id)
    if not purchase:
        await safe_answer_callback(callback, getattr(texts, "PRODUCT_NOT_FOUND", "Purchase not found"), show_alert=True)
        return
    product = purchase.product
    _up = getattr(product, "uploaded_by", "") or ""
    _is_w = _up.startswith("worker:")
    detail_text = (
        f"<b>#{purchase.id} | {product.name}</b>\n\n"
        f"Category: {product.category}/{product.service}\n"
        f"State: {product.state}\n"
        f"Price: ${float(product.price):.2f}\n"
        f"Status: {_format_purchase_status(purchase)}\n"
        f"Purchased: {purchase.purchased_at.strftime('%Y-%m-%d %H:%M')}\n"
    )
    if not _is_w:
        detail_text += f"Guarantee until: {purchase.guarantee_until.strftime('%Y-%m-%d %H:%M UTC') if purchase.guarantee_until else 'N/A'}"
    await safe_edit_message(
        callback,
        detail_text,
        create_purchase_detail_keyboard(
            purchase_id,
            delivered=bool(purchase.delivered_at),
            can_report=is_guarantee_active(purchase.guarantee_until),
            back_callback=f"history_page:{page_raw}:{filter_kind}:{filter_value}",
            texts=texts,
            is_worker_product=_is_w,
        ),
        parse_mode="HTML",
    )
    await safe_answer_callback(callback)


@router.message(F.text.in_(ButtonTexts.get_all_variants("SETUP_ARCHIVE")))
async def setup_archive_message(message: Message, state: FSMContext, texts):
    await state.set_state(ProfileStates.entering_archive_channel_id)
    await message.answer(getattr(texts, "ARCHIVE_SETUP_INSTRUCTIONS", "Forward a message from your archive channel."), parse_mode=None)


@router.callback_query(F.data == "setup_archive")
async def setup_archive_callback(callback: CallbackQuery, state: FSMContext, texts, buttons):
    await state.set_state(ProfileStates.entering_archive_channel_id)
    await safe_edit_message(
        callback,
        getattr(texts, "ARCHIVE_SETUP_INSTRUCTIONS", "Forward a message from your archive channel."),
        InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=getattr(buttons, "BACK", "⬅️ Back"), callback_data="back_to_profile")]]),
        parse_mode=None,
    )
    await safe_answer_callback(callback)


@router.message(ProfileStates.entering_archive_channel_id)
async def archive_channel_forward_handler(message: Message, state: FSMContext, session: AsyncSession, mirror_bot_id: int, texts):
    channel_id = _extract_forwarded_channel_id(message)
    if not channel_id:
        await message.answer(getattr(texts, "ARCHIVE_SETUP_INVALID", "Forward a message from a channel."), parse_mode=None)
        return

    try:
        me = await message.bot.get_me()
        member = await message.bot.get_chat_member(channel_id, me.id)
        if getattr(member, "status", "") not in {"administrator", "creator"}:
            await message.answer(getattr(texts, "ARCHIVE_SETUP_BOT_NOT_ADMIN", "Bot must be channel admin."), parse_mode=None)
            return
    except Exception:
        await message.answer(getattr(texts, "ARCHIVE_SETUP_BOT_NOT_ADMIN", "Bot must be channel admin."), parse_mode=None)
        return

    updated = await ProductService.set_archive_channel(
        session,
        user_id=message.from_user.id,
        mirror_bot_id=mirror_bot_id,
        channel_id=channel_id,
    )
    if not updated:
        await message.answer(getattr(texts, "USER_NOT_FOUND", "User not found"), parse_mode=None)
        return

    await state.clear()
    await message.answer(getattr(texts, "ARCHIVE_SETUP_SUCCESS", "Archive channel connected successfully."), parse_mode=None)


def _format_guarantee_notice(result: dict) -> str:
    _uploaded_by = result.get("product", {}).get("uploaded_by", "") or ""
    _is_worker = _uploaded_by.startswith("worker:")

    details = [
        "⚠️ Purchase confirmed",
        "",
        f"🛍 Product: {result['product']['name']}",
        f"💰 Paid: ${result['product']['price']:.2f}",
    ]
    if not _is_worker:
        guarantee_until = result.get("guarantee_until")
        expires_at_text = guarantee_until.strftime("%Y-%m-%d %H:%M UTC") if guarantee_until else "N/A"
        details.append(f"🛡 Guarantee window: {format_guarantee_window(int(result['guarantee_minutes']))}")
        details.append(f"⏳ Timer until: {expires_at_text}")
        if result.get("report_requires_video"):
            details.append("📹 Report rule: video proof is required for disputes in this category.")
    details.extend([
        "",
        "Use the button below to reveal the data.",
    ])
    return "\n".join(details)


@router.callback_query(F.data.startswith("show_products:"))
async def show_products_for_state(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Показать товары для выбранного штата"""
    
    try:
        # Парсим callback data: show_products:category:service:state
        parts = callback.data.split(":")
        logger.info(f"[PRODUCTS] Callback data parts: {parts}")

        if len(parts) != 4:
            logger.error(f"[PRODUCTS] Invalid callback data format: {callback.data}")
            await safe_answer_callback(callback, "Invalid data format", show_alert=True)
            return

        category, service, selected_state = parts[1], parts[2], parts[3]
        logger.info(f"[PRODUCTS] Loading products for category={category}, service={service}, state={selected_state}")

        # Получаем товары
        products_data = await ProductService.get_products_by_category_service_state(
            session=session,
            category=category,
            service=service,
            state=selected_state,
            page=1,
            per_page=10
        )
        logger.info(f"[PRODUCTS] Loaded {products_data['total']} products")
        
        if products_data["total"] == 0:
            from mirror_bot.constants.language_loader import get_texts
            temp_texts = get_texts('en')
            await safe_edit_message(
                callback,
                f"{temp_texts.NO_PRODUCTS_AVAILABLE if hasattr(temp_texts, 'NO_PRODUCTS_AVAILABLE') else '❌ No products available'}\n\n"
                f"Category: {await get_service_display_name(session, category, service)}\n"
                f"State: {selected_state}\n\n"
                "Please try another state.",
                InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⬅️ Back", callback_data=f"back_to_states:{category}:{service}")]
                ])
            )
            await safe_answer_callback(callback)
            return
        
        # Показываем список товаров
        from mirror_bot.constants.language_loader import get_texts
        texts = get_texts('en')  # Fallback, ideally should be passed as parameter
        service_name = await get_service_display_name(session, category, service)

        text = f"📦 **Available Products**\n\n"
        text += f"Category: {service_name}\n"
        text += f"State: {selected_state}\n"
        text += f"⏱ ETA: Instant ⚡\n"
        text += f"Total: {products_data['total']} products\n\n"
        text += f"💡 *Select a product to view details and purchase*"
        
        await safe_edit_message(
            callback,
            text,
            create_products_keyboard(products_data, category, service, selected_state),
            parse_mode="Markdown"
        )
        await safe_answer_callback(callback)
        
    except Exception as e:
        logger.error(f"[PRODUCTS] Error showing products: {e}", exc_info=True)
        try:
            await safe_answer_callback(callback, "❌ Error loading products. Please try again.", show_alert=True)
        except Exception as callback_error:
            logger.error(f"[PRODUCTS] Failed to send error callback: {callback_error}")


@router.callback_query(F.data.startswith("products_page:"))
async def handle_products_pagination(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Обработать пагинацию товаров"""
    
    try:
        # Парсим callback data: products_page:category:service:state:page
        parts = callback.data.split(":")
        if len(parts) != 5:
            from mirror_bot.constants.language_loader import get_texts
            temp_texts = get_texts('en')
            await safe_answer_callback(callback, temp_texts.INVALID_DATA_FORMAT_SHORT, show_alert=True)
            return
            
        category, service, selected_state, page = parts[1], parts[2], parts[3], int(parts[4])
        
        # Получаем товары для новой страницы
        products_data = await ProductService.get_products_by_category_service_state(
            session=session,
            category=category,
            service=service,
            state=selected_state,
            page=page,
            per_page=10
        )
        
        # Обновляем сообщение
        from mirror_bot.constants.language_loader import get_texts
        texts = get_texts('en')  # Fallback
        service_name = await get_service_display_name(session, category, service)
        text = f"{texts.AVAILABLE_PRODUCTS}\n\n"
        text += f"{texts.CATEGORY_LABEL} {service_name}\n"
        text += f"{texts.STATE_LABEL} {selected_state}\n"
        text += f"{texts.TOTAL_LABEL} {texts.PRODUCTS_COUNT.format(total=products_data['total'])}\n\n"
        text += f"💡 *{texts.SELECT_A_PRODUCT_NOTE}*"
        
        await safe_edit_message(
            callback,
            text,
            create_products_keyboard(products_data, category, service, selected_state),
            parse_mode="Markdown"
        )
        await safe_answer_callback(callback)
        
    except Exception as e:
        logger.error(f"Error handling pagination: {e}")
        from mirror_bot.constants.language_loader import get_texts
        temp_texts = get_texts('en')
        await safe_answer_callback(callback, temp_texts.ERROR_LOADING_PAGE, show_alert=True)


@router.callback_query(F.data.startswith("product_view:"))
async def view_product_details(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Показать детали товара"""
    
    try:
        product_id = int(callback.data.split(":")[1])
        logger.info(f"[PRODUCT_VIEW] User {callback.from_user.id} viewing product {product_id}")
        
        # Получаем товар
        product = await ProductService.get_product_by_id(session, product_id)
        if not product:
            logger.warning(f"[PRODUCT_VIEW] Product {product_id} not found in database")
            from mirror_bot.constants.language_loader import get_texts
            temp_texts = get_texts('en')
            await safe_answer_callback(callback, temp_texts.PRODUCT_NOT_FOUND, show_alert=True)
            return
        
        logger.info(f"[PRODUCT_VIEW] Product found: {product.name}, category: {product.category}, service: {product.service}")
        try:
            await log_product_action(
                session,
                action="view",
                actor_type="user",
                actor_id=callback.from_user.id,
                product=product,
                details={
                    "category": product.category,
                    "service": product.service,
                    "state": product.state,
                },
                notify_if_stale=True,
            )
        except Exception:
            pass
        
        # Формируем описание
        from mirror_bot.constants.language_loader import get_texts
        temp_texts = get_texts('en')  # Fallback
        
        file_type_emoji = {
            'txt': '📄',
            'pdf': '📋', 
            'zip': '📦',
            'jpg': '🖼️',
            'png': '🖼️',
            'gif': '🖼️',
            'webp': '🖼️'
        }.get(product.file_type, '📄')
        
        text = f"🛍️ **{product.name}**\n\n"
        
        if product.description:
            text += f"{temp_texts.DESCRIPTION_LABEL}\n{product.description}\n\n"
        text += f"{temp_texts.PRICE_LABEL} ${product.price:.2f}\n"
        
        # Безопасная обработка категории и сервиса
        try:
            service_display = await get_service_display_name(session, product.category, product.service)
            text += f"{temp_texts.CATEGORY_LABEL} {service_display}\n"
        except Exception as cat_error:
            logger.error(f"[PRODUCT_VIEW] Error getting category/service mapping: {cat_error}")
            text += f"{temp_texts.CATEGORY_LABEL} {product.service}\n"
        
        text += f"{temp_texts.STATE_LABEL} {product.state}\n"
        text += f"{file_type_emoji} {temp_texts.FILE_TYPE_LABEL} {product.file_type.upper()}\n\n"
        text += f"💡 *{temp_texts.CLICK_BUY_NOW_NOTE}*"
        
        logger.info(f"[PRODUCT_VIEW] Sending product details to user")
        
        await safe_edit_message(
            callback,
            text,
            create_product_detail_keyboard(product_id)
        )
        await safe_answer_callback(callback)
        
    except Exception as e:
        logger.error(f"[PRODUCT_VIEW] Error viewing product: {e}", exc_info=True)
        from mirror_bot.constants.language_loader import get_texts
        temp_texts = get_texts('en')
        await safe_answer_callback(callback, temp_texts.ERROR_LOADING_PRODUCT, show_alert=True)


@router.callback_query(F.data.startswith("product_buy:"))
async def buy_product(callback: CallbackQuery, state: FSMContext, session: AsyncSession, mirror_bot_id: int):
    """Шаг подтверждения покупки товара."""

    try:
        product_id = int(callback.data.split(":")[1])
        product = await ProductService.get_product_by_id(session, product_id)
        if not product:
            await safe_answer_callback(callback, "Product not found", show_alert=True)
            return

        await safe_edit_message(
            callback,
            (
                "⚠️ Confirm purchase?\n\n"
                f"🛍 {product.name}\n"
                f"💵 ${float(product.price):.2f} will be deducted from your balance."
            ),
            create_product_confirm_keyboard(product_id),
            parse_mode=None,
        )
        await safe_answer_callback(callback)
    except Exception as e:
        logger.error(f"Error buying product: {e}")
        await safe_answer_callback(callback, "Error processing purchase", show_alert=True)


@router.callback_query(F.data.startswith("product_buy_confirm:"))
async def confirm_product_purchase(callback: CallbackQuery, session: AsyncSession, mirror_bot_id: int):
    try:
        product_id = int(callback.data.split(":")[1])
        user_id = callback.from_user.id

        result = await ProductService.purchase_product(
            session=session,
            product_id=product_id,
            user_id=user_id,
            mirror_bot_id=mirror_bot_id,
        )
        if not result["success"]:
            if result["error"] == "Insufficient balance":
                text = (
                    "❌ INSUFFICIENT BALANCE\n\n"
                    f"Required: ${result['required']:.2f}\n"
                    f"Available: ${result['available']:.2f}\n"
                    f"Need: ${result['required'] - result['available']:.2f}"
                )
            else:
                text = f"❌ Purchase failed\n\n{result['error']}"
            await safe_edit_message(callback, text, parse_mode=None)
            await safe_answer_callback(callback, "Purchase failed", show_alert=True)
            return

        try:
            from shared.services.admin_notification_service import AdminNotificationService

            await AdminNotificationService.notify_product_purchased(
                purchase_id=result["purchase_id"],
                product_id=result["product"]["id"],
                product_name=result["product"]["name"],
                category=result["product"].get("category", "product"),
                service=result["product"].get("service", ""),
                user_id=user_id,
                price=float(result["product"]["price"]),
                mirror_bot_id=mirror_bot_id,
            )
        except Exception as exc:
            logger.warning("Failed to send product purchase notification: %s", exc)

        await safe_edit_message(
            callback,
            _format_guarantee_notice(result),
            create_product_access_keyboard(result["purchase_id"], result["product"]["file_type"]),
            parse_mode=None,
        )
        await safe_answer_callback(callback, "Purchase confirmed")
    except Exception as exc:
        logger.error("Error confirming product purchase: %s", exc, exc_info=True)
        await safe_answer_callback(callback, "Error processing purchase", show_alert=True)


@router.callback_query(F.data.startswith("product_access:"))
async def access_product_data(callback: CallbackQuery, session: AsyncSession):
    try:
        purchase_id = int(callback.data.split(":")[1])
        purchase = await ProductService.get_purchase(session, purchase_id, user_id=callback.from_user.id)
        if not purchase:
            await safe_answer_callback(callback, "Purchase not found", show_alert=True)
            return

        delivery_result = await ProductService.deliver_product_file(session=session, purchase_id=purchase_id)
        if not delivery_result["success"]:
            await safe_answer_callback(callback, delivery_result["error"], show_alert=True)
            return

        file_path = delivery_result["file_path"]
        file_type = delivery_result["file_type"].lower()
        file_name = delivery_result["file_name"]
        product_name = purchase.product.name
        _uploaded_by = getattr(purchase.product, "uploaded_by", "") or ""
        _is_worker = _uploaded_by.startswith("worker:")

        if not os.path.exists(file_path):
            await safe_answer_callback(callback, "File not found on server", show_alert=True)
            return

        def _fb_kb():
            return create_product_feedback_keyboard(
                purchase_id,
                can_report=is_guarantee_active(purchase.guarantee_until),
                is_worker_product=_is_worker,
            )

        sent_message = None
        delivery_error = None
        if file_type in {"txt", "text"}:
            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as file:
                    content = file.read()
            except Exception:
                content = ""
            if not content or not content.strip():
                await safe_answer_callback(callback, "File is empty or unreadable", show_alert=True)
                return
            try:
                if len(content) <= 3000:
                    sent_message = await callback.message.answer(
                        f"🔓 {product_name}\n\n{content}",
                        parse_mode=None,
                        reply_markup=_fb_kb(),
                    )
                else:
                    sent_message = await callback.message.answer_document(
                        document=FSInputFile(file_path, filename=file_name),
                        caption=f"🔓 {product_name}",
                        reply_markup=_fb_kb(),
                        parse_mode=None,
                    )
            except Exception as send_exc:
                delivery_error = str(send_exc)
                logger.error("Failed to send txt product %s: %s", purchase_id, send_exc)
        elif file_type in {"jpg", "jpeg", "png", "gif", "webp"}:
            try:
                sent_message = await callback.message.answer_photo(
                    photo=FSInputFile(file_path),
                    caption=f"🔓 {product_name}",
                    reply_markup=_fb_kb(),
                    parse_mode=None,
                )
            except Exception as send_exc:
                delivery_error = str(send_exc)
                logger.error("Failed to send image product %s: %s", purchase_id, send_exc)
        else:
            try:
                sent_message = await callback.message.answer_document(
                    document=FSInputFile(file_path, filename=file_name),
                    caption=f"🔓 {product_name}",
                    reply_markup=_fb_kb(),
                    parse_mode=None,
                )
            except Exception as send_exc:
                delivery_error = str(send_exc)
                logger.error("Failed to send document product %s: %s", purchase_id, send_exc)

        if delivery_error and not sent_message:
            await safe_answer_callback(
                callback,
                "Failed to deliver the file. Please try again or contact support.",
                show_alert=True,
            )
            return

        await ProductService.mark_product_delivered(session=session, purchase_id=purchase_id)
        delivery_notes: list[str] = []
        purchase_texts = get_texts(getattr(getattr(purchase, "user", None), "language", "en"))
        if sent_message:
            try:
                await callback.bot.pin_chat_message(
                    chat_id=callback.message.chat.id,
                    message_id=sent_message.message_id,
                    disable_notification=True,
                )
                delivery_notes.append(
                    getattr(purchase_texts, "PURCHASE_PINNED", "📌 Order #{order_id} data pinned in chat.").format(
                        order_id=purchase_id
                    )
                )
            except Exception as exc:
                logger.warning("Failed to pin purchase %s: %s", purchase_id, exc)

            archive_channel_id = getattr(getattr(purchase, "user", None), "archive_channel_id", None)
            if archive_channel_id:
                try:
                    await callback.bot.forward_message(
                        chat_id=archive_channel_id,
                        from_chat_id=callback.message.chat.id,
                        message_id=sent_message.message_id,
                    )
                    delivery_notes.append(
                        getattr(purchase_texts, "PURCHASE_ARCHIVED", "📢 Data also sent to your archive channel.")
                    )
                except Exception as exc:
                    logger.warning("Failed to archive purchase %s: %s", purchase_id, exc)

        if _is_worker:
            summary_text = "✅ Data delivered."
        else:
            summary_text = "✅ Data access granted.\n\nRate the product or open a report while the guarantee window is active."
        if delivery_notes:
            summary_text = f"{summary_text}\n\n" + "\n".join(note for note in delivery_notes if note)
        await safe_edit_message(
            callback,
            summary_text,
            _fb_kb(),
            parse_mode=None,
        )
        await safe_answer_callback(callback, "Data opened")
    except Exception as exc:
        logger.error("Error revealing product data: %s", exc, exc_info=True)
        await safe_answer_callback(callback, "Error opening data", show_alert=True)


@router.callback_query(F.data.startswith("product_rate:"))
async def product_rate(callback: CallbackQuery, session: AsyncSession):
    try:
        _, _, purchase_id_raw, rating = callback.data.split(":", 3)
        purchase_id = int(purchase_id_raw)
        saved = await ProductService.save_rating(
            session=session,
            purchase_id=purchase_id,
            user_id=callback.from_user.id,
            rating=rating,
        )
        if not saved:
            await safe_answer_callback(callback, "Rating unavailable", show_alert=True)
            return

        await safe_edit_message(
            callback,
            "⭐ Feedback saved.",
            InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Back", callback_data="back_main")]
            ]),
            parse_mode=None,
        )
        await safe_answer_callback(callback, "Rating saved")
    except Exception as exc:
        logger.error("Error saving product rating: %s", exc, exc_info=True)
        await safe_answer_callback(callback, "Error saving rating", show_alert=True)


@router.callback_query(F.data.startswith("product_report:"))
async def product_report(callback: CallbackQuery, session: AsyncSession, mirror_bot_id: int):
    try:
        purchase_id = int(callback.data.split(":")[1])
        result = await ProductService.create_report(
            session=session,
            purchase_id=purchase_id,
            user_id=callback.from_user.id,
            mirror_bot_id=mirror_bot_id,
        )
        if not result["success"]:
            await safe_answer_callback(callback, result["error"], show_alert=True)
            return

        await safe_edit_message(
            callback,
            f"💬 Report created successfully.\n\nTicket id: #{result['report_id']}",
            InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Back", callback_data="back_main")]
            ]),
            parse_mode=None,
        )
        await safe_answer_callback(callback, "Report created")
    except Exception as exc:
        logger.error("Error creating product report: %s", exc, exc_info=True)
        await safe_answer_callback(callback, "Error creating report", show_alert=True)


@router.callback_query(F.data.startswith("product_back:"))
async def back_to_product_list(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Вернуться к списку товаров"""
    
    try:
        product_id = int(callback.data.split(":")[1])
        
        # Получаем товар для определения категории, сервиса и штата
        product = await ProductService.get_product_by_id(session, product_id)
        if not product:
            from mirror_bot.constants.language_loader import get_texts
            temp_texts = get_texts('en')
            await safe_answer_callback(callback, temp_texts.PRODUCT_NOT_FOUND, show_alert=True)
            return
        
        # Создаем временный callback с данными для показа списка товаров
        class TempCallback:
            def __init__(self, original_callback, new_data):
                self.data = new_data
                self.message = original_callback.message
                self.from_user = original_callback.from_user
                self.bot = original_callback.bot
                
            async def answer(self, *args, **kwargs):
                return await callback.answer(*args, **kwargs)
        
        temp_callback = TempCallback(callback, f"show_products:{product.category}:{product.service}:{product.state}")
        
        # Перенаправляем на список товаров
        await show_products_for_state(temp_callback, state, session)
        
    except Exception as e:
        logger.error(f"Error going back: {e}")
        from mirror_bot.constants.language_loader import get_texts
        temp_texts = get_texts('en')
        await safe_answer_callback(callback, temp_texts.ERROR_LOADING_PRODUCTS, show_alert=True)


@router.callback_query(F.data.startswith("back_to_states:"))
async def back_to_states_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, texts, buttons):
    """Вернуться к выбору штатов"""
    
    try:
        # Парсим callback data: back_to_states:category:service
        parts = callback.data.split(":")
        if len(parts) != 3:
            from mirror_bot.constants.language_loader import get_texts
            temp_texts = get_texts('en')
            await safe_answer_callback(callback, temp_texts.INVALID_DATA_FORMAT_SHORT, show_alert=True)
            return
            
        category, service = parts[1], parts[2]
        
        # Перенаправляем на соответствующий handler выбора штатов
        if category == "docs":
            # Маппинг обратно на doc types
            doc_type_mapping = {
                "dl_front_back": "dl",
                "dl_selfie": "dl_selfie",
                "passport": "passport", 
                "business_docs": "biz"
            }
            
            doc_type = doc_type_mapping.get(service, service)
            
            # Создаем временный callback с нужными данными
            class TempCallback:
                def __init__(self, original_callback, new_data):
                    self.data = new_data
                    self.message = original_callback.message
                    self.from_user = original_callback.from_user
                    self.bot = original_callback.bot
                    
                async def answer(self, *args, **kwargs):
                    return await callback.answer(*args, **kwargs)
            
            temp_callback = TempCallback(callback, f"doc_photo_{doc_type}")
            
            # Импортируем и вызываем documents handler
            from mirror_bot.handlers.documents import doc_photo_handler
            await doc_photo_handler(temp_callback, texts, buttons)
            
        elif category == "pros_fullz":
            # Создаем временный callback с нужными данными
            class TempCallback:
                def __init__(self, original_callback, new_data):
                    self.data = new_data
                    self.message = original_callback.message
                    self.from_user = original_callback.from_user
                    self.bot = original_callback.bot
                    
                async def answer(self, *args, **kwargs):
                    return await callback.answer(*args, **kwargs)
            
            temp_callback = TempCallback(callback, "fullz_personal")
            
            # Импортируем и вызываем fullz handler
            from mirror_bot.handlers.fullz import fullz_personal_handler
            await fullz_personal_handler(temp_callback, state, texts, buttons)
        
    except Exception as e:
        logger.error(f"Error going back to states: {e}")
        from mirror_bot.constants.language_loader import get_texts
        temp_texts = get_texts('en')
        await safe_answer_callback(callback, temp_texts.ERROR_LOADING_STATES, show_alert=True)
