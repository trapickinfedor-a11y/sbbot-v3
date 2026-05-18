from __future__ import annotations

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from mirror_bot.keyboards.inline import InlineKeyboardMarkup, InlineKeyboardButton
from mirror_bot.constants.addinfo_data import AddInfoData
from mirror_bot.constants.service_eta import ServiceETA
from mirror_bot.services.order_service import OrderService
from mirror_bot.services.checkout_coupon_service import CheckoutCouponService
from mirror_bot.services.user_service import UserService
from mirror_bot.constants.language_loader import get_texts
from mirror_bot.constants.buttons_en import ButtonTexts
from mirror_bot.states.order import OrderStates
from mirror_bot.utils.message_utils import safe_edit_message
from mirror_bot.utils.product_translations import ProductTranslations
from mirror_bot.middlewares.language import LanguageHelper
from mirror_bot.utils.media_library import resolve_bot_photo

router = Router()

ADDINFO_PHOTO = resolve_bot_photo("addinfo", "add_info_in_cr", fallback_path="media/Add info in cr.jpg")


def addinfo_main_keyboard(buttons):
    """Клавиатура главного меню добавления информации"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=buttons.ADDINFO_CR, callback_data="addinfo_addcr")],
        [InlineKeyboardButton(text=buttons.ADDINFO_BG, callback_data="addinfo_addbg")],
        [InlineKeyboardButton(text=buttons.ADDINFO_EMPLOYER, callback_data="addinfo_employer")],
        [InlineKeyboardButton(text=buttons.ADDINFO_UNFREEZE, callback_data="addinfo_unfreeze")],
        [InlineKeyboardButton(text=buttons.BACK, callback_data="back_main")]
    ])


def addinfo_catalog_keyboard(category: str, items: list, buttons):
    """Клавиатура каталога услуг добавления информации"""
    keyboard_buttons = []
    for item in items:
        keyboard_buttons.append([InlineKeyboardButton(
            text=f"{item['name']} — ${item['price']}",
            callback_data=f"addinfo_item:{item['id']}"
        )])
    
    keyboard_buttons.append([InlineKeyboardButton(text=buttons.BACK, callback_data="addinfo_main")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)


def addinfo_item_keyboard(item_id: str, buttons):
    """Клавиатура для отдельного элемента add info"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=buttons.CONTINUE, callback_data=f"addinfo_buy:{item_id}")],
        [InlineKeyboardButton(text=buttons.BACK_TO_LIST, callback_data=f"addinfo_back:{item_id}")]
    ])


def confirm_keyboard(buttons):
    """Клавиатура подтверждения для add info"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=buttons.CONFIRM, callback_data="addinfo_confirm_yes")],
        [InlineKeyboardButton(text=buttons.CANCEL, callback_data="addinfo_confirm_no")]
    ])


@router.message(F.text.in_(ButtonTexts.get_all_variants("ADD_INFO_CR")))
async def addinfo_main_handler(message: Message, texts, buttons):
    try:
        await message.answer_photo(
            photo=ADDINFO_PHOTO,
            caption=texts.ADDINFO_MAIN,
            reply_markup=addinfo_main_keyboard(buttons)
        )
    except Exception:
        await message.answer(texts.ADDINFO_MAIN, reply_markup=addinfo_main_keyboard(buttons))


@router.callback_query(F.data == "addinfo_main")
async def addinfo_main_callback(callback: CallbackQuery, texts, buttons):
    # Для возврата в addinfo всегда отправляем с фото
    try:
        await callback.message.delete()
        await callback.bot.send_photo(
            chat_id=callback.message.chat.id,
            photo=ADDINFO_PHOTO,
            caption=texts.ADDINFO_MAIN,
            reply_markup=addinfo_main_keyboard(buttons)
        )
    except Exception:
        # Fallback без фото
        await safe_edit_message(
            callback,
            texts.ADDINFO_MAIN,
            reply_markup=addinfo_main_keyboard(buttons)
        )
    await callback.answer()


@router.callback_query(F.data.startswith("addinfo_addcr") | F.data.startswith("addinfo_addbg") | F.data.startswith("addinfo_employer") | F.data.startswith("addinfo_unfreeze"))
async def addinfo_category_handler(callback: CallbackQuery, texts, buttons):
    category = callback.data.replace("addinfo_", "")
    items = AddInfoData.get_category_items(category)
    category_name = AddInfoData.CATEGORIES[category]["name"]
    
    await safe_edit_message(
        callback,
        f"{category_name}\n\n{texts.SELECT_A_SERVICE}",
        reply_markup=addinfo_catalog_keyboard(category, items, buttons)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("addinfo_item:"))
async def addinfo_item_detail(callback: CallbackQuery, texts, buttons):
    item_id = callback.data.split(":")[1]
    item = AddInfoData.get_item_by_id(item_id)
    
    if not item:
        await callback.answer(texts.ITEM_NOT_FOUND, show_alert=True)
        return
    
    text = f"""✍️ {item['name']}

{texts.PRICE_LABEL} ${item['price']}
{texts.PROCESSING_LABEL} {texts.MANUAL_PROCESSING}

{texts.NOTE_LABEL} {texts.REQUIRED_FIELDS_NOTE}

{texts.STATUS_AVAILABLE}
{texts.PAYMENT_CONFIRMATION_NOTE}

{texts.PRESS_BUY_NOW}"""
    
    await safe_edit_message(callback, text, reply_markup=addinfo_item_keyboard(item_id, buttons))
    await callback.answer()


@router.callback_query(F.data.startswith("addinfo_buy:"))
async def addinfo_buy_handler(callback: CallbackQuery, state: FSMContext, texts, buttons):
    item_id = callback.data.split(":")[1]
    
    item = AddInfoData.get_item_by_id(item_id)
    if not item:
        await callback.answer(texts.ITEM_NOT_FOUND, show_alert=True)
        return
    
    await state.set_state(OrderStates.waiting_data)
    await state.update_data(
        service="addinfo",
        item_id=item_id,
        item_name=item['name'],
        price=item['price']
    )
    
    # Маппинг item_id к соответствующим форматам
    format_map = {
        # TU services
        "addcr_phone_tu": texts.ADDINFO_TU_FORMAT,
        "addcr_addr_tu": texts.ADDINFO_TU_FORMAT,
        "addemp_tu": texts.ADD_EMPLOYER_FORMAT,
        "unfreeze_tu": texts.UNFREEZE_TU_FORMAT,
        
        # EX services  
        "addcr_phone_ex": texts.ADDINFO_EX_FORMAT,
        "addcr_addr_ex": texts.ADDINFO_EX_FORMAT,
        "unfreeze_ex": texts.UNFREEZE_EX_FORMAT,
        
        # ALL services
        "addcr_all": texts.ADDINFO_ALL_FORMAT,
        "addcr_phone_addr": texts.ADDINFO_ALL_FORMAT,
        "addcr_phone_all": texts.ADDINFO_ALL_FORMAT,
        "addcr_addr_all": texts.ADDINFO_ALL_FORMAT,
        
        # BG services
        "addbg_phone_addr": texts.ADDINFO_BG_FORMAT,
        "addbg_phone": texts.ADDINFO_BG_FORMAT,
        "addbg_addr": texts.ADDINFO_BG_FORMAT,
        
        # Employer services (other than TU)
        "addemp_update": texts.ADD_EMPLOYER_FORMAT,
        "addemp_remove": texts.ADD_EMPLOYER_FORMAT,
    }
    
    # Получаем соответствующий формат или используем базовый
    format_text = format_map.get(item_id)
    
    if format_text:
        # Используем готовый формат с инструкциями
        example = f"John Doe\n123 Main St, Los Angeles, CA 90001\n123-45-6789\n01/15/1990"
        message_text = format_text.format(price=item['price'], example=example)
        parse_mode = "Markdown"
    else:
        # Fallback для неизвестных items
        message_text = f"✍️ {item['name']} — ${item['price']}\n\n{texts.PLEASE_ENTER_YOUR_DATA}\n\n{texts.EXAMPLE_LABEL}\nJohn Doe\n123 Main St, Los Angeles, CA 90001\n123-45-6789\n01/15/1990\n\n{texts.NO_VALIDATION_NOTE}"
        parse_mode = None
    
    await safe_edit_message(
        callback,
        message_text,
        parse_mode=parse_mode
    )
    await callback.answer()


@router.message(OrderStates.waiting_data, F.text)
async def addinfo_data_handler(message: Message, state: FSMContext, session: AsyncSession, mirror_bot_id: int, texts, buttons):
    data = await state.get_data()
    service = data.get("service")

    if service != "addinfo":
        return

    raw_data = message.text.strip()
    item_id = data.get("item_id")
    item_name = data.get("item_name")
    price = data.get("price")

    if not raw_data:
        await message.answer(texts.PLEASE_ENTER_DATA.format(example=""))
        return

    confirmation_text = texts.ORDER_CONFIRMATION.format(
        service_name=item_name,
        price=price
    ) + f"\n\n{texts.DATA_RECEIVED_LABEL}\n{raw_data[:200]}{'...' if len(raw_data) > 200 else ''}"

    await state.update_data(
        validated_data={"raw_data": raw_data},
        checkout_category="addinfo",
        checkout_service_name=item_id,
        checkout_base_price=str(price),
        checkout_confirm_text=confirmation_text,
        checkout_keyboard_type="custom",
        checkout_confirm_callback="addinfo_confirm_yes",
        checkout_cancel_callback="addinfo_confirm_no",
        checkout_parse_mode="Markdown",
        selected_coupon_code=None,
        selected_user_coupon_id=None,
    )
    await state.set_state(OrderStates.confirmation)
    await message.answer(confirmation_text, reply_markup=confirm_keyboard(buttons), parse_mode="Markdown")


@router.callback_query(F.data == "addinfo_confirm_yes", OrderStates.confirmation)
async def addinfo_confirm_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, mirror_bot_id: int, texts, buttons):
    data = await state.get_data()
    service = data.get("service")
    
    if service != "addinfo":
        return
    
    item_id = data.get("item_id")
    validated_data = data.get("validated_data")
    price = data.get("price")
    
    user = await UserService.get_user(session, callback.from_user.id, mirror_bot_id)
    pricing = await CheckoutCouponService.get_checkout_pricing(
        session,
        telegram_user_id=callback.from_user.id,
        state_data=data,
    )
    
    if not user or user.balance < pricing.final_amount:
        await safe_edit_message(
            callback,
            texts.INSUFFICIENT_BALANCE.format(balance=user.balance if user else 0, price=pricing.final_amount)
        )
        await state.clear()
        await callback.answer()
        return
    
    success = await OrderService.deduct_balance(session, callback.from_user.id, pricing.final_amount)
    if not success:
        await safe_edit_message(callback, texts.INSUFFICIENT_BALANCE.format(balance=user.balance if user else 0, price=pricing.final_amount))
        await state.clear()
        await callback.answer()
        return
    
    order = await OrderService.create_order(
        session,
        user_id=callback.from_user.id,
        mirror_bot_id=mirror_bot_id,
        category="addinfo",
        service_name=item_id,
        input_data=validated_data,
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
        "addinfo", 
        user_language
    )
    service_name = ProductTranslations.get_service_name(
        item_id,
        user_language
    )
    
    # Получаем информацию о товаре
    item = AddInfoData.get_item_by_id(item_id)
    product_name = item['name'] if item else item_id
    
    # Получаем ETA для Additional Info
    eta = ServiceETA.get_eta("addinfo")
    
    await safe_edit_message(
        callback,
        texts.ORDER_CREATED.format(
            product=product_name,
            price=pricing.final_amount,
            balance=user.balance,
            eta=eta
        ),
        parse_mode="Markdown"
    )
    await state.clear()
    await callback.answer(texts.ORDER_CREATED_ALERT)


@router.callback_query(F.data == "confirm_no_addinfo", OrderStates.confirmation)
async def addinfo_cancel_handler_alt(callback: CallbackQuery, state: FSMContext, texts, buttons):
    data = await state.get_data()
    service = data.get("service")
    
    if service != "add_info":
        return
    
    await safe_edit_message(callback, texts.ORDER_CANCELLED)
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "addinfo_confirm_no", OrderStates.confirmation)
async def addinfo_cancel_handler(callback: CallbackQuery, state: FSMContext, texts):
    """Отмена заказа Add Info"""
    await safe_edit_message(callback, texts.ORDER_CANCELLED)
    await state.clear()
    await callback.answer()


@router.callback_query(F.data.startswith("addinfo_back:"))
async def addinfo_back_handler(callback: CallbackQuery, texts, buttons):
    item_id = callback.data.split(":")[1]
    
    category = None
    for cat_key, cat_data in AddInfoData.CATEGORIES.items():
        for item in cat_data["items"]:
            if item["id"] == item_id:
                category = cat_key
                break
        if category:
            break
    
    if not category:
        await callback.answer(texts.ERROR_GENERAL, show_alert=True)
        return
    
    items = AddInfoData.get_category_items(category)
    category_name = AddInfoData.CATEGORIES[category]["name"]
    
    await safe_edit_message(callback, f"{category_name}\n\nSelect a service:", reply_markup=addinfo_catalog_keyboard(category, items, buttons))
    await callback.answer()

