from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import ValidationError
from mirror_bot.states.order import OrderStates
from mirror_bot.services.validator import SSNLookupData
from mirror_bot.services.parser import DataParser
from mirror_bot.services.order_service import OrderService
from mirror_bot.services.checkout_coupon_service import CheckoutCouponService
from mirror_bot.services.user_service import UserService
from mirror_bot.constants.service_eta import ServiceETA
from mirror_bot.constants.prices import ServicePrices
from mirror_bot.middlewares.language import LanguageHelper
from mirror_bot.keyboards.inline import confirm_keyboard, bulk_confirmation_keyboard, order_type_keyboard
from mirror_bot.config import mirror_bot_config
from mirror_bot.filters.service_filter import ServiceFilter
from mirror_bot.utils.message_utils import safe_edit_message
from mirror_bot.utils.product_translations import ProductTranslations

router = Router()

# ВСЕ примеры теперь берутся из texts_*.py


@router.callback_query(F.data == "lookup_ssn")
async def ssn_lookup_start(callback: CallbackQuery, state: FSMContext, texts, buttons):
    await state.update_data(service="lookup_ssn", service_name="SSN & DOB")
    await state.set_state(OrderStates.waiting_data)
    
    from mirror_bot.keyboards.inline import bulk_order_keyboard
    
    bulk_price = ServicePrices.get_service_price("lookup_ssn", is_bulk=True)
    await safe_edit_message(callback,
        texts.SSN_LOOKUP_FORMAT.format(price=ServicePrices.LOOKUP_SSN_DOB, example=texts.SSN_SINGLE_EXAMPLE),
        reply_markup=bulk_order_keyboard(buttons, bulk_price),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "bulk_order", OrderStates.waiting_data)
async def universal_bulk_order_start(callback: CallbackQuery, state: FSMContext, texts, buttons):
    """Универсальный обработчик bulk кнопки для всех сервисов"""
    data = await state.get_data()
    service = data.get("service")
    
    if service == "lookup_ssn":
        await state.set_state(OrderStates.waiting_bulk_data)
        
        await safe_edit_message(callback,
            texts.SSN_BULK_FORMAT.format(price=ServicePrices.LOOKUP_SSN_DOB_BULK, example=texts.SSN_BULK_EXAMPLE),
            parse_mode="Markdown"
        )
    
    elif service == "lookup_bg":
        await state.set_state(OrderStates.waiting_bulk_data)
        
        await safe_edit_message(callback,
            texts.BG_BULK_FORMAT.format(price=ServicePrices.LOOKUP_BG_BULK, example=texts.BG_BULK_EXAMPLE),
            parse_mode="Markdown"
        )
    
    elif service == "lookup_dl":
        await state.set_state(OrderStates.waiting_bulk_data)
        
        await safe_edit_message(callback,
            texts.DL_BULK_FORMAT.format(price=ServicePrices.LOOKUP_DL_BULK, example=texts.DL_BULK_EXAMPLE),
            parse_mode="Markdown"
        )
    
    elif service == "lookup_credit":
        await state.set_state(OrderStates.waiting_bulk_data)
        
        await safe_edit_message(callback,
            texts.CS_BULK_FORMAT.format(price=ServicePrices.LOOKUP_CREDIT_SCORE_BULK, example=texts.CS_BULK_EXAMPLE),
            parse_mode="Markdown"
        )
    
    elif service == "lookup_mvr":
        await state.set_state(OrderStates.waiting_bulk_data)
        
        await safe_edit_message(callback,
            texts.MVR_BULK_FORMAT.format(price=ServicePrices.LOOKUP_MVR_BULK, example=texts.MVR_BULK_EXAMPLE),
            parse_mode="Markdown"
        )
    
    elif service == "lookup_fullmvr":
        await state.set_state(OrderStates.waiting_bulk_data)
        
        await safe_edit_message(callback,
            texts.FULL_MVR_LOOKUP_FORMAT.format(price=ServicePrices.LOOKUP_FULL_MVR_BULK, example=texts.MVR_BULK_EXAMPLE),
            parse_mode="Markdown"
        )
    
    elif service == "credit_report":
        service_name = data.get("service_name")
        bulk_price = data.get("bulk_price")

        await state.set_state(OrderStates.waiting_bulk_data)

        await safe_edit_message(callback,
            f"📈 {service_name} Credit Report\n\n"
            f"💰 Bulk (2-20): ${bulk_price} per entry\n⏱ ETA: 4-30 minutes\n\n"
            f"{texts.CR_BULK_EXAMPLE}",
            parse_mode="Markdown"
        )
    
    elif service == "lookup_mmn":
        await state.set_state(OrderStates.waiting_bulk_data)
        
        await safe_edit_message(callback,
            texts.MMN_BULK_FORMAT.format(price=ServicePrices.LOOKUP_MMN, example=texts.MMN_BULK_EXAMPLE),
            parse_mode="Markdown"
        )
    
    elif service == "lookup_ein":
        await state.set_state(OrderStates.waiting_bulk_data)
        
        await safe_edit_message(callback,
            texts.EIN_BULK_FORMAT.format(price=ServicePrices.LOOKUP_EIN, example=texts.EIN_BULK_EXAMPLE),
            parse_mode="Markdown"
        )
    
    await callback.answer()


@router.message(OrderStates.waiting_data, ServiceFilter("lookup_ssn"), F.text)
async def ssn_data_handler(message: Message, state: FSMContext, session: AsyncSession, mirror_bot_id: int, texts, buttons):
    """Универсальный обработчик - автоматически определяет single или bulk"""
    text = message.text.strip()
    
    # Проверяем, есть ли множественные записи (двойной перенос)
    entries = DataParser.parse_bulk_entries(text)
    
    if len(entries) == 1:
        # Single order
        await handle_single_ssn(message, state, session, mirror_bot_id, text, texts, buttons)
    elif 2 <= len(entries) <= mirror_bot_config.max_bulk_items:
        # Bulk order
        await handle_bulk_ssn(message, state, session, mirror_bot_id, text, texts, buttons)
    elif len(entries) > mirror_bot_config.max_bulk_items:
        await message.answer(texts.MAXIMUM_ENTRIES_FOR_BULK.format(max_items=mirror_bot_config.max_bulk_items))
    else:
        await message.answer(texts.INVALID_FORMAT_TRY_AGAIN)


async def handle_single_ssn(message: Message, state: FSMContext, session: AsyncSession, mirror_bot_id: int, text: str, texts, buttons):
    parsed_data = DataParser.smart_parse_address_data(text, require_dob=False)
    
    if parsed_data['issues']:
        issues_text = "\n".join([f"• {issue}" for issue in parsed_data['issues']])
        await message.answer(
            texts.INVALID_DATA_FORMAT_WITH_EXAMPLE.format(issues_text=issues_text, example=texts.SSN_SINGLE_EXAMPLE)
        )
        return
    
    try:
        # Маппинг полей парсера на поля модели
        model_data = {
            'first_name': parsed_data['first'],
            'last_name': parsed_data['last'],
            'address': parsed_data['address'],
            'city': parsed_data['city'],
            'state': parsed_data['state'],
            'zip_code': parsed_data['zip'],
            'dob': parsed_data['dob']
        }
        
        validated_data = SSNLookupData(**model_data)
        
        await state.update_data(
            validated_data=[validated_data.dict()],
            is_bulk=False
        )
        await state.set_state(OrderStates.confirmation)
        
        # Формируем ПОЛНУЮ информацию о введенных данных
        info_lines = [
            f"👤 {validated_data.first_name} {validated_data.last_name}",
            f"📍 {validated_data.address}",
            f"🏙️ {validated_data.city}, {validated_data.state} {validated_data.zip_code}",
        ]
        
        # Добавляем SSN если есть (для SSN Lookup он всегда есть, но может быть в других сервисах)
        if hasattr(validated_data, 'ssn') and validated_data.ssn:
            info_lines.append(f"🆔 SSN: `{validated_data.ssn}`")
        
        if validated_data.dob:
            info_lines.append(f"🎂 DOB: `{validated_data.dob}`")
        
        confirmation_text = texts.ORDER_CONFIRMATION.format(
            service_name="SSN & DOB Lookup",
            price=ServicePrices.LOOKUP_SSN_DOB
        ) + "\n\n" + "\n".join(info_lines)
        await state.update_data(
            checkout_category="lookup",
            checkout_service_name="ssn_dob",
            checkout_base_price=str(ServicePrices.LOOKUP_SSN_DOB),
            checkout_confirm_text=confirmation_text,
            checkout_keyboard_type="confirm",
            checkout_keyboard_suffix="_ssn",
            checkout_parse_mode="Markdown",
            selected_coupon_code=None,
            selected_user_coupon_id=None,
        )
        await message.answer(confirmation_text, reply_markup=confirm_keyboard(buttons, suffix="_ssn"), parse_mode="Markdown")
    
    except ValidationError as e:
        errors = "\n".join([f"• {err['msg']}" for err in e.errors()])
        await message.answer(
            texts.INVALID_DATA.format(
                error_message=errors,
                example=texts.SSN_SINGLE_EXAMPLE
            )
        )


async def handle_bulk_ssn(message: Message, state: FSMContext, session: AsyncSession, mirror_bot_id: int, text: str, texts, buttons):
    try:
        entries = DataParser.parse_bulk_entries(text)
        
        if len(entries) < mirror_bot_config.min_bulk_items:
            await message.answer(texts.MIN_ENTRIES_REQUIRED.format(min_items=mirror_bot_config.min_bulk_items))
            return
        
        if len(entries) > mirror_bot_config.max_bulk_items:
            await message.answer(texts.MAX_ENTRIES_ALLOWED.format(max_items=mirror_bot_config.max_bulk_items))
            return
        
        validated_entries = []
        for i, entry in enumerate(entries, 1):
            # Используем новый универсальный парсер (как в single заказах)
            from mirror_bot.services.validator import parse_freeform_text
            
            parsed_data = parse_freeform_text(entry, required_fields=["first_name", "last_name"])
            
            if not parsed_data['valid'] or parsed_data['errors']:
                errors_text = "\n".join([f"• {err}" for err in parsed_data['errors']])
                await message.answer(texts.ERROR_IN_ENTRY.format(entry=i, issues=errors_text, example=texts.SSN_BULK_EXAMPLE))
                return
            
            try:
                # Создаем модель данных для валидации
                model_data = {
                    'first_name': parsed_data['first_name'],
                    'last_name': parsed_data['last_name'],
                    'address': parsed_data.get('address'),
                    'city': parsed_data.get('city'),
                    'state': parsed_data.get('state'),
                    'zip_code': parsed_data.get('zip'),
                    'dob': parsed_data.get('dob'),
                    'ssn': parsed_data.get('ssn')
                }
                
                validated = SSNLookupData(**model_data)
                validated_entries.append(validated.dict())
            except ValidationError as e:
                errors = "\n".join([f"• {err['msg']}" for err in e.errors()])
                await message.answer(texts.ERROR_IN_ENTRY.format(entry=i, issues=errors, example=texts.SSN_BULK_EXAMPLE))
                return
        
        unit_price = ServicePrices.get_service_price("lookup_ssn", is_bulk=True)
        final_price = unit_price * len(validated_entries)
        
        summary = f"✅ {len(validated_entries)} entries validated!\n\n"
        for i, entry in enumerate(validated_entries, 1):
            summary += f"📋 **Entry #{i}:**\n"
            summary += f"👤 {entry['first_name']} {entry['last_name']}\n"
            summary += f"📍 {entry['address']}\n"
            summary += f"🏙️ {entry['city']}, {entry['state']} {entry['zip_code']}\n"
            
            # Добавляем SSN если есть
            if entry.get('ssn'):
                summary += f"🆔 SSN: `{entry['ssn']}`\n"
            
            # Добавляем DOB если есть
            if entry.get('dob'):
                summary += f"🎂 DOB: `{entry['dob']}`\n"
            
            summary += "\n"
        
        summary += texts.BULK_PRICE_PER_ITEM.format(price=unit_price)
        summary += texts.TOTAL_WITH_CONFIRM.format(total=final_price)
        await state.update_data(
            validated_data=validated_entries,
            is_bulk=True,
            total_price=final_price,
            checkout_category="lookup",
            checkout_service_name="ssn_dob",
            checkout_base_price=str(final_price),
            checkout_confirm_text=summary,
            checkout_keyboard_type="bulk",
            checkout_keyboard_suffix="_ssn",
            checkout_parse_mode="Markdown",
            selected_coupon_code=None,
            selected_user_coupon_id=None,
        )
        await state.set_state(OrderStates.confirmation)
        await message.answer(summary, reply_markup=bulk_confirmation_keyboard(buttons, suffix="_ssn"), parse_mode="Markdown")
    
    except Exception as e:
        await message.answer(texts.ERROR_PROCESSING_BULK.format(error=str(e)))


@router.message(OrderStates.waiting_bulk_data, ServiceFilter("lookup_ssn"), F.text)
async def ssn_bulk_data_handler(message: Message, state: FSMContext, session: AsyncSession, mirror_bot_id: int, texts, buttons):
    """Обработчик bulk данных для SSN lookup"""
    text = message.text.strip()
    await handle_bulk_ssn(message, state, session, mirror_bot_id, text, texts, buttons)


@router.callback_query(F.data == "confirm_yes_ssn", OrderStates.confirmation)
@router.callback_query(F.data == "bulk_confirm_ssn", OrderStates.confirmation)
async def confirm_order(callback: CallbackQuery, state: FSMContext, session: AsyncSession, mirror_bot_id: int, texts, buttons):
    data = await state.get_data()
    validated_data = data.get("validated_data")
    is_bulk = data.get("is_bulk", False)
    service_name = data.get("service_name")
    
    if is_bulk:
        price = data.get("total_price")
        bulk_items = validated_data
        input_data = {"count": len(validated_data)}
    else:
        price = ServicePrices.LOOKUP_SSN_DOB
        bulk_items = None
        input_data = validated_data[0] if validated_data and isinstance(validated_data, list) and len(validated_data) > 0 else validated_data if validated_data else {}
    
    user = await UserService.get_user(session, callback.from_user.id, mirror_bot_id)
    pricing = await CheckoutCouponService.get_checkout_pricing(
        session,
        telegram_user_id=callback.from_user.id,
        state_data=data,
    )
    
    if user.balance < pricing.final_amount:
        await safe_edit_message(callback,
            texts.INSUFFICIENT_BALANCE.format(
                balance=user.balance,
                price=pricing.final_amount
            )
        )
        await state.clear()
        await callback.answer()
        return
    
    success = await OrderService.deduct_balance(session, callback.from_user.id, pricing.final_amount)
    
    if not success:
        await callback.answer(texts.INSUFFICIENT_BALANCE_ALERT, show_alert=True)
        return
    
    order = await OrderService.create_order(
        session,
        user_id=callback.from_user.id,
        mirror_bot_id=mirror_bot_id,
        category="lookup",
        service_name="ssn_dob",
        input_data=input_data,
        price=pricing.final_amount,
        original_price=pricing.original_amount,
        coupon_code=pricing.code,
        discount_amount=pricing.discount_amount,
        coupon_application=pricing,
        bulk_items=bulk_items,
        notify_workers=False,
        notify_channel=True,
    )

    # Trigger SSN automation (tries usfull API first; falls back to workers if not found)
    from mirror_bot.services.ssn_dl_automation import get_ssn_dl_runner
    ssndl_runner = get_ssn_dl_runner(mirror_bot_id)
    if ssndl_runner:
        await ssndl_runner.enqueue_order(order.id, "lookup_ssn")

    user = await UserService.get_user(session, callback.from_user.id, mirror_bot_id)

    # Получаем информацию о категории и сервисе
    user_language = user.language if user and hasattr(user, 'language') else 'en'
    category_name = ProductTranslations.get_category_name(
        "lookup",
        user_language
    )
    service_name = ProductTranslations.get_service_name(
        "ssn_dob",
        user_language
    )
    
    # Формируем название продукта
    product_name = service_name
    if data.get('state'):
        product_name += f" - {data.get('state')}"
    
    # Добавляем количество если bulk заказ
    if is_bulk and bulk_items:
        count = len(bulk_items)
        if count > 1:
            product_name += f" x{count}"
    
    # Получаем ETA
    eta = ServiceETA.get_eta("ssn_dob")
    
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
    await callback.answer(texts.ORDER_CREATED_SUCCESS)


@router.callback_query(F.data == "confirm_no_ssn", OrderStates.confirmation)
@router.callback_query(F.data == "bulk_cancel_ssn", OrderStates.confirmation)
async def cancel_order(callback: CallbackQuery, state: FSMContext, texts):
    await safe_edit_message(callback, texts.ORDER_CANCELLED)
    await state.clear()
    await callback.answer()

