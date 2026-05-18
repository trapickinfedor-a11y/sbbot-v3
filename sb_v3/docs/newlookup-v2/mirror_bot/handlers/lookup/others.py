from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import ValidationError
from mirror_bot.states.order import OrderStates
from mirror_bot.services.validator import DLLookupData, BGLookupData, MMNLookupData, CreditScoreLookupData, MVRLookupData, FullMVRLookupData, EINLookupData
from mirror_bot.services.parser import DataParser
from mirror_bot.services.order_service import OrderService
from mirror_bot.services.checkout_coupon_service import CheckoutCouponService
from mirror_bot.services.user_service import UserService
from mirror_bot.constants.prices import ServicePrices
from mirror_bot.constants.service_eta import ServiceETA
from mirror_bot.middlewares.language import LanguageHelper
from mirror_bot.keyboards.inline import confirm_keyboard, order_type_keyboard, bulk_confirmation_keyboard, bulk_order_keyboard
from mirror_bot.filters.service_filter import ServiceFilter
from mirror_bot.config import mirror_bot_config
from mirror_bot.services.parser import DataParser as BulkParser
from mirror_bot.utils.message_utils import safe_edit_message
from mirror_bot.utils.product_translations import ProductTranslations
from shared.database.models import Order, BulkOrderItem

router = Router()

# ВСЕ примеры и тексты теперь берутся из texts_*.py - они уже мультиязычные!


@router.callback_query(F.data == "lookup_dl")
async def dl_lookup_start(callback: CallbackQuery, state: FSMContext, texts, buttons):
    await state.update_data(service="lookup_dl", service_name="DL Lookup")
    await state.set_state(OrderStates.waiting_data)
    
    bulk_price = ServicePrices.get_service_price("lookup_dl", is_bulk=True)
    await safe_edit_message(callback,
        texts.DL_LOOKUP_FORMAT.format(price=ServicePrices.LOOKUP_DL, example=texts.DL_SINGLE_EXAMPLE),
        reply_markup=bulk_order_keyboard(buttons, bulk_price),
        parse_mode="Markdown"
    )
    await callback.answer()


# DEPRECATED: Старые DL handler'ы удалены - используется универсальная система


@router.callback_query(F.data == "lookup_mvr")
async def mvr_lookup_start(callback: CallbackQuery, state: FSMContext, texts, buttons):
    await state.update_data(service="lookup_mvr", service_name="MVR Lookup")
    await state.set_state(OrderStates.waiting_data)
    
    bulk_price = ServicePrices.get_service_price("lookup_mvr", is_bulk=True)
    await safe_edit_message(callback,
        texts.MVR_LOOKUP_FORMAT.format(price=ServicePrices.LOOKUP_MVR, example=texts.MVR_SINGLE_EXAMPLE),
        reply_markup=bulk_order_keyboard(buttons, bulk_price),
        parse_mode="Markdown"
    )
    await callback.answer()


# DEPRECATED: Старые MVR handler'ы удалены - используется универсальная система


@router.callback_query(F.data == "lookup_fullmvr")
async def full_mvr_lookup_start(callback: CallbackQuery, state: FSMContext, texts, buttons):
    await state.update_data(service="lookup_fullmvr", service_name="Full MVR Lookup")
    await state.set_state(OrderStates.waiting_data)
    
    bulk_price = ServicePrices.get_service_price("lookup_fullmvr", is_bulk=True)
    await safe_edit_message(callback,
        texts.FULL_MVR_LOOKUP_FORMAT.format(price=ServicePrices.LOOKUP_FULL_MVR, example=texts.MVR_SINGLE_EXAMPLE),
        reply_markup=bulk_order_keyboard(buttons, bulk_price),
        parse_mode="Markdown"
    )
    await callback.answer()


# DEPRECATED: Старые Full MVR handler'ы удалены - используется универсальная система


@router.callback_query(F.data == "lookup_credit")
async def credit_score_lookup_start(callback: CallbackQuery, state: FSMContext, texts, buttons):
    await state.update_data(service="lookup_credit", service_name="Credit Score Lookup")
    await state.set_state(OrderStates.waiting_data)
    
    bulk_price = ServicePrices.get_service_price("lookup_credit_score", is_bulk=True)
    await safe_edit_message(callback,
        texts.CREDIT_SCORE_LOOKUP_FORMAT.format(price=ServicePrices.LOOKUP_CREDIT_SCORE, example=texts.CS_SINGLE_EXAMPLE),
        reply_markup=bulk_order_keyboard(buttons, bulk_price),
        parse_mode="Markdown"
    )
    await callback.answer()


# DEPRECATED: Старые Credit Score handler'ы удалены - используется универсальная система


@router.callback_query(F.data == "lookup_bg")
async def bg_lookup_start(callback: CallbackQuery, state: FSMContext, texts, buttons):
    await state.update_data(service="lookup_bg", service_name="Background Lookup")
    await state.set_state(OrderStates.waiting_data)
    
    bulk_price = ServicePrices.get_service_price("lookup_bg", is_bulk=True)
    await safe_edit_message(callback,
        texts.BACKGROUND_LOOKUP_FORMAT.format(price=ServicePrices.LOOKUP_BG, example=texts.BG_SINGLE_EXAMPLE),
        reply_markup=bulk_order_keyboard(buttons, bulk_price),
        parse_mode="Markdown"
    )
    await callback.answer()


# DEPRECATED: Старые handler'ы удалены - теперь используется универсальная система как в SSN Lookup


@router.callback_query(F.data == "lookup_mmn")
async def mmn_lookup_start(callback: CallbackQuery, state: FSMContext, texts, buttons):
    await state.set_state(OrderStates.waiting_data)
    await state.update_data(service="lookup_mmn", service_name="MMN Lookup")
    
    bulk_price = ServicePrices.get_service_price("lookup_mmn", is_bulk=True)
    await safe_edit_message(callback,
        texts.MMN_LOOKUP_FORMAT.format(price=ServicePrices.LOOKUP_MMN, example=texts.MMN_SINGLE_EXAMPLE),
        reply_markup=bulk_order_keyboard(buttons, bulk_price),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "lookup_ein")
async def ein_lookup_start(callback: CallbackQuery, state: FSMContext, texts, buttons):
    await state.set_state(OrderStates.waiting_data)
    await state.update_data(service="lookup_ein", service_name="EIN Lookup")
    
    bulk_price = ServicePrices.get_service_price("lookup_ein", is_bulk=True)
    await safe_edit_message(callback,
        texts.EIN_LOOKUP_FORMAT.format(price=ServicePrices.LOOKUP_EIN, example=texts.EIN_SINGLE_EXAMPLE),
        reply_markup=bulk_order_keyboard(buttons, bulk_price),
        parse_mode="Markdown"
    )
    await callback.answer()




@router.message(OrderStates.waiting_data, ServiceFilter(["lookup_dl", "lookup_credit", "lookup_bg", "lookup_mmn", "lookup_ein", "lookup_mvr", "lookup_fullmvr"]), F.text)
async def lookup_data_handler(message: Message, state: FSMContext, session: AsyncSession, mirror_bot_id: int, texts, buttons):
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"[OTHERS HANDLER] Triggered! User: {message.from_user.id}")
    
    data = await state.get_data()
    service = data.get("service")
    
    logger.info(f"[OTHERS HANDLER] Service: {service}")
    
    # Использует глобальный MVR_EXAMPLE который уже обновлен
    
    validator_map = {
        "lookup_dl": (DLLookupData, ServicePrices.LOOKUP_DL, texts.DL_SINGLE_EXAMPLE, True),
        "lookup_credit": (CreditScoreLookupData, ServicePrices.LOOKUP_CREDIT_SCORE, texts.CS_SINGLE_EXAMPLE, True),
        "lookup_bg": (BGLookupData, ServicePrices.LOOKUP_BG, texts.BG_SINGLE_EXAMPLE, False),
        "lookup_mmn": (MMNLookupData, ServicePrices.LOOKUP_MMN, texts.MMN_SINGLE_EXAMPLE, False),
        "lookup_ein": (EINLookupData, ServicePrices.LOOKUP_EIN, texts.EIN_SINGLE_EXAMPLE, False),
        "lookup_mvr": (MVRLookupData, ServicePrices.LOOKUP_MVR, texts.MVR_SINGLE_EXAMPLE, True),
        "lookup_fullmvr": (FullMVRLookupData, ServicePrices.LOOKUP_FULL_MVR, texts.MVR_SINGLE_EXAMPLE, True)
    }
    
    validator_class, price, example, require_dob = validator_map[service]
    
    # Примеры уже мультиязычные из texts
    localized_example = example
    
    # Для сервисов без валидации (MVR, Full MVR, EIN) просто сохраняем RAW текст
    if service in ["lookup_mvr", "lookup_fullmvr", "lookup_ein"]:
        # БЕЗ ПАРСИНГА - принимаем любой текст как есть
        raw_text = message.text.strip()
        
        logger.info(f"[OTHERS HANDLER] No validation service - accepting raw text: {raw_text[:100]}")
        
        # Создаем простой объект с raw данными - БЕЗ СТРУКТУРЫ
        class RawData:
            def __init__(self, raw_input):
                self.raw_input = raw_input
            def dict(self):
                return {"raw_input": self.raw_input}
        
        validated_data = RawData(raw_text)
        
        # Сохраняем и показываем подтверждение
        await state.update_data(validated_data=validated_data.dict(), price=price)
        await state.set_state(OrderStates.confirmation)
        
        confirmation_text = texts.ORDER_CONFIRMATION.format(
            service_name=data.get("service_name"),
            price=price
        ) + f"\n\n{texts.YOUR_DATA_LABEL}\n`{raw_text}`"
        await state.update_data(
            checkout_category="lookup",
            checkout_service_name=service,
            checkout_base_price=str(price),
            checkout_confirm_text=confirmation_text,
            checkout_keyboard_type="confirm",
            checkout_keyboard_suffix="_others",
            checkout_parse_mode="Markdown",
            selected_coupon_code=None,
            selected_user_coupon_id=None,
        )
        await message.answer(confirmation_text, reply_markup=confirm_keyboard(buttons, suffix="_others"), parse_mode="Markdown")
        return
    
    # Для остальных сервисов используем валидацию и парсинг
    parsed_data = DataParser.smart_parse_address_data(message.text.strip(), require_dob=require_dob)
    
    logger.info(f"[OTHERS HANDLER] Parsed data: {parsed_data}")
    
    if parsed_data['issues']:
        issues_text = "\n".join([f"• {issue}" for issue in parsed_data['issues']])
        await message.answer(texts.INVALID_DATA_FORMAT.format(issues_text=issues_text, example=localized_example))
        return
    
    # Маппинг полей парсера на поля модели
    model_data = {
        'first_name': parsed_data.get('first'),
        'last_name': parsed_data.get('last'),
        'address': parsed_data.get('address'),
        'city': parsed_data.get('city'),
        'state': parsed_data.get('state'),
        'zip_code': parsed_data.get('zip'),
        'dob': parsed_data.get('dob'),
        'ssn': parsed_data.get('ssn'),
        'dl': parsed_data.get('dl', 'DL123456')  # Fallback для тестирования
    }
    
    logger.info(f"[OTHERS HANDLER] Model data: {model_data}")
    
    # Валидация для сервисов с требованиями
    try:
        if service == "lookup_dl":
            validated_data = DLLookupData(**model_data)
        elif service == "lookup_credit":
            validated_data = CreditScoreLookupData(**model_data)
        elif service == "lookup_bg":
            validated_data = BGLookupData(**model_data)
        elif service == "lookup_mmn":
            # MMN не требует DOB, но нужны все остальные поля
            mmn_data = model_data.copy()
            mmn_data.pop('dob', None)  # Удаляем dob если есть
            logger.info(f"[OTHERS HANDLER] MMN data before validation: {mmn_data}")
            validated_data = MMNLookupData(**mmn_data)
    except ValidationError as e:
        errors = "\n".join([f"• {err['msg']}" for err in e.errors()])
        await message.answer(texts.VALIDATION_ERROR.format(errors=errors, example=localized_example))
        return
        
    await state.update_data(validated_data=validated_data.dict(), price=price)
    await state.set_state(OrderStates.confirmation)
    
    # Формируем ПОЛНУЮ информацию о введенных данных
    info_lines = [
        f"👤 {getattr(validated_data, 'first_name', '')} {getattr(validated_data, 'last_name', '')}",
        f"📍 {getattr(validated_data, 'address', '')}",
        f"🏙️ {getattr(validated_data, 'city', 'N/A')}, {getattr(validated_data, 'state', '')} {getattr(validated_data, 'zip_code', '')}",
    ]
    
    # Добавляем SSN если есть
    if hasattr(validated_data, 'ssn') and getattr(validated_data, 'ssn', None):
        info_lines.append(f"🆔 SSN: `{validated_data.ssn}`")
    
    # Добавляем DOB если есть
    if hasattr(validated_data, 'dob') and getattr(validated_data, 'dob', None):
        info_lines.append(f"🎂 DOB: `{validated_data.dob}`")
    
    # Добавляем DL номер если есть (для MVR/Full MVR)
    if hasattr(validated_data, 'dl') and getattr(validated_data, 'dl', None):
        info_lines.append(f"🚗 DL: {validated_data.dl}")
    
    # Добавляем телефон если есть
    if hasattr(validated_data, 'phone') and getattr(validated_data, 'phone', None):
        info_lines.append(f"📞 Phone: {validated_data.phone}")
    
    # Добавляем email если есть
    if hasattr(validated_data, 'email') and getattr(validated_data, 'email', None):
        info_lines.append(f"📧 Email: {validated_data.email}")
    
    confirmation_text = texts.ORDER_CONFIRMATION.format(
        service_name=data.get("service_name"),
        price=price
    ) + "\n\n" + "\n".join(info_lines)
    await state.update_data(
        checkout_category="lookup",
        checkout_service_name=service,
        checkout_base_price=str(price),
        checkout_confirm_text=confirmation_text,
        checkout_keyboard_type="confirm",
        checkout_keyboard_suffix="_others",
        checkout_parse_mode="Markdown",
        selected_coupon_code=None,
        selected_user_coupon_id=None,
    )
    await message.answer(confirmation_text, reply_markup=confirm_keyboard(buttons, suffix="_others"), parse_mode="Markdown")
    

@router.message(OrderStates.waiting_bulk_data, ServiceFilter(["lookup_dl", "lookup_credit", "lookup_bg", "lookup_mvr", "lookup_fullmvr", "lookup_mmn", "lookup_ein"]), F.text)
async def lookup_bulk_data_handler(message: Message, state: FSMContext, session: AsyncSession, mirror_bot_id: int, texts, buttons):
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"[OTHERS BULK HANDLER] Triggered! User: {message.from_user.id}")
    
    data = await state.get_data()
    service = data.get("service")
    price_per_item = data.get("price_per_item")
    service_name = data.get("service_name")
    
    logger.info(f"[OTHERS BULK HANDLER] Service: {service}, Price per item: ${price_per_item}")
    
    try:
        entries = BulkParser.parse_bulk_entries(message.text.strip())
        
        logger.info(f"[OTHERS BULK HANDLER] Parsed {len(entries)} entries")
        logger.info(f"[OTHERS BULK HANDLER] First entry sample: {entries[0][:50] if entries else 'NONE'}")
        
        if len(entries) < mirror_bot_config.min_bulk_items:
            await message.answer(texts.MIN_ENTRIES_REQUIRED.format(min_items=mirror_bot_config.min_bulk_items))
            return
        
        if len(entries) > mirror_bot_config.max_bulk_items:
            await message.answer(texts.MAX_ENTRIES_ALLOWED.format(max_items=mirror_bot_config.max_bulk_items))
            return
        
        validated_entries = []
        validator_map = {
            "lookup_dl": (DLLookupData, True),
            "lookup_credit": (CreditScoreLookupData, True),
            "lookup_bg": (BGLookupData, False),
            "lookup_mvr": (MVRLookupData, True),
            "lookup_fullmvr": (FullMVRLookupData, True),
            "lookup_mmn": (MMNLookupData, False),
            "lookup_ein": (EINLookupData, False)
        }
        
        validator_class, require_dob = validator_map[service]
        
        for i, entry in enumerate(entries, 1):
            if not entry.strip():
                await message.answer(texts.EMPTY_DATA_ENTRY.format(entry_num=i))
                return
            
            # Для сервисов без валидации просто сохраняем RAW текст
            if service in ["lookup_mvr", "lookup_fullmvr", "lookup_ein"]:
                # БЕЗ ПАРСИНГА - принимаем любой текст как есть
                class RawData:
                    def __init__(self, raw_input):
                        self.raw_input = raw_input
                    def dict(self):
                        return {"raw_input": self.raw_input}
                
                validated = RawData(entry.strip())
                validated_entries.append(validated.dict())
            else:
                # Для остальных сервисов используем парсинг и валидацию
                from mirror_bot.services.validator import parse_freeform_text
                
                parsed_data = parse_freeform_text(entry, required_fields=["first_name", "last_name"])
                
                if not parsed_data['valid'] or parsed_data['errors']:
                    errors_text = "\n".join([f"• {err}" for err in parsed_data['errors']])
                    await message.answer(texts.ENTRY_ISSUES.format(entry_num=i, issues_text=errors_text))
                    return
                
                # Маппинг полей парсера на поля модели
                model_data = {
                    'first_name': parsed_data['first_name'],
                    'last_name': parsed_data['last_name'],
                    'address': parsed_data.get('address'),
                    'city': parsed_data.get('city'),
                    'state': parsed_data.get('state'),
                    'zip_code': parsed_data.get('zip'),
                    'dob': parsed_data.get('dob'),
                    'ssn': parsed_data.get('ssn'),
                    'dl': parsed_data.get('dl', 'DL123456')  # Fallback для тестирования
                }
                
                # Валидация для сервисов с требованиями
                try:
                    if service == "lookup_dl":
                        validated = DLLookupData(**model_data)
                    elif service == "lookup_credit":
                        validated = CreditScoreLookupData(**model_data)
                    elif service == "lookup_bg":
                        validated = BGLookupData(**model_data)
                    elif service == "lookup_mmn":
                        # MMN не требует DOB
                        mmn_data = {k: v for k, v in model_data.items() if k != 'dob'}
                        validated = MMNLookupData(**mmn_data)
                    
                    validated_entries.append(validated.dict())
                except ValidationError as e:
                    await message.answer(texts.ENTRY_VALIDATION_ERROR.format(entry_num=i, error_msg=e.errors()[0]['msg']))
                    return
        
        unit_price = ServicePrices.get_service_price(service, is_bulk=True)
        final_price = unit_price * len(validated_entries)
        
        summary = texts.ENTRIES_VALIDATED.format(count=len(validated_entries))
        for i, entry in enumerate(validated_entries, 1):
            summary += f"📋 **Entry #{i}:**\n"
            
            # Проверяем, есть ли raw_input (для no-validation сервисов)
            if 'raw_input' in entry:
                # MVR/Full MVR/EIN - показываем RAW данные
                summary += f"📄 `{entry['raw_input'][:100]}`\n\n"
            elif 'raw_data' in entry:
                # Старый формат - показываем полные данные
                summary += f"📄 Data: {entry['raw_data']}\n\n"
            else:
                # Остальные сервисы - показываем все поля
                summary += f"👤 {entry['first_name']} {entry['last_name']}\n"
                summary += f"📍 {entry['address']}\n"
                summary += f"🏙️ {entry['city']}, {entry['state']} {entry['zip_code']}\n"
                
                # Добавляем SSN если есть
                if entry.get('ssn'):
                    summary += f"🆔 SSN: `{entry['ssn']}`\n"
                
                # Добавляем DOB если есть
                if entry.get('dob'):
                    summary += f"🎂 DOB: `{entry['dob']}`\n"
                
                # Добавляем телефон если есть
                if entry.get('phone'):
                    summary += f"📞 Phone: {entry['phone']}\n"
                
                # Добавляем email если есть
                if entry.get('email'):
                    summary += f"📧 Email: {entry['email']}\n"
                
                summary += "\n"
        
        summary += texts.BULK_PRICE_PER_ITEM.format(price=unit_price)
        summary += texts.BULK_TOTAL_CONFIRM.format(price=final_price)
        await state.update_data(
            validated_data=validated_entries,
            is_bulk=True,
            total_price=final_price,
            checkout_category="lookup",
            checkout_service_name=service,
            checkout_base_price=str(final_price),
            checkout_confirm_text=summary,
            checkout_keyboard_type="bulk",
            checkout_keyboard_suffix="_others",
            checkout_parse_mode="Markdown",
            selected_coupon_code=None,
            selected_user_coupon_id=None,
        )
        await state.set_state(OrderStates.confirmation)
        await message.answer(summary, reply_markup=bulk_confirmation_keyboard(buttons, suffix="_others"), parse_mode="Markdown")
    
    except Exception as e:
        logger.error(f"[OTHERS BULK HANDLER] Error: {e}", exc_info=True)
        # Используем parse_mode=None чтобы избежать ошибок HTML парсинга
        import html
        error_text = html.escape(str(e))
        await message.answer(texts.BULK_PROCESSING_ERROR.format(error=error_text), parse_mode=None)


@router.callback_query(F.data == "confirm_yes_others", OrderStates.confirmation)
@router.callback_query(F.data == "bulk_confirm_others", OrderStates.confirmation)
async def confirm_lookup_order(callback: CallbackQuery, state: FSMContext, session: AsyncSession, mirror_bot_id: int, texts, buttons):
    data = await state.get_data()
    service = data.get("service")
    
    if service not in ["lookup_dl", "lookup_credit", "lookup_bg", "lookup_mmn", "lookup_ein", "lookup_mvr", "lookup_fullmvr"]:
        return
    
    validated_data = data.get("validated_data")
    is_bulk = data.get("is_bulk", False)
    service_name = data.get("service_name")
    
    if is_bulk:
        price = data.get("total_price")
        bulk_items = validated_data
        input_data = {"count": len(validated_data)}
    else:
        price = data.get("price")
        bulk_items = None
        input_data = validated_data
    
    user = await UserService.get_user(session, callback.from_user.id, mirror_bot_id)
    pricing = await CheckoutCouponService.get_checkout_pricing(
        session,
        telegram_user_id=callback.from_user.id,
        state_data=data,
    )
    
    if user.balance < pricing.final_amount:
        await safe_edit_message(callback,
            texts.INSUFFICIENT_BALANCE.format(balance=user.balance, price=pricing.final_amount)
        )
        await state.clear()
        await callback.answer()
        return
    
    success = await OrderService.deduct_balance(session, callback.from_user.id, pricing.final_amount)
    
    if not success:
        await callback.answer(texts.INSUFFICIENT_BALANCE_ALERT, show_alert=True)
        return
    
    # SSN/DL automation handles worker notification internally
    _auto_services = {"lookup_credit", "lookup_dl"}
    order = await OrderService.create_order(
        session,
        user_id=callback.from_user.id,
        mirror_bot_id=mirror_bot_id,
        category="lookup",
        service_name=service,
        input_data=input_data,
        price=pricing.final_amount,
        original_price=pricing.original_amount,
        coupon_code=pricing.code,
        discount_amount=pricing.discount_amount,
        coupon_application=pricing,
        bulk_items=bulk_items,
        notify_workers=service not in _auto_services,
        notify_channel=True,
    )

    if service == "lookup_credit":
        from mirror_bot.services.cs_automation import get_cs_runner

        runner = get_cs_runner(mirror_bot_id)
        if runner:
            await runner.enqueue_order(order.id)

    elif service == "lookup_dl":
        from mirror_bot.services.ssn_dl_automation import get_ssn_dl_runner

        ssndl_runner = get_ssn_dl_runner(mirror_bot_id)
        if ssndl_runner:
            await ssndl_runner.enqueue_order(order.id, "lookup_dl")
    
    user = await UserService.get_user(session, callback.from_user.id, mirror_bot_id)
    
    # Получаем информацию о категории и сервисе
    user_language = user.language if user and hasattr(user, 'language') else 'en'
    category_name = ProductTranslations.get_category_name(
        "lookup",
        user_language
    )
    # Используем полное имя сервиса с префиксом
    service_name = ProductTranslations.get_service_name(
        service,
        user_language
    )

    # Формируем название продукта используя переведённое имя сервиса
    product_name = service_name
    if data.get('state'):
        product_name += f" - {data.get('state')}"

    # Добавляем количество если bulk заказ
    if is_bulk and bulk_items:
        count = len(bulk_items)
        if count > 1:
            product_name += f" x{count}"

    # Получаем ETA на основе полного имени сервиса
    eta = ServiceETA.get_eta(service)
    automation_note = ""
    if service == "lookup_credit":
        automation_note = {
            "ru": "\n\n🤖 CS automation запущена.",
            "zh": "\n\n🤖 CS automation 已启动。",
            "en": "\n\n🤖 CS automation started.",
        }.get(user_language, "\n\n🤖 CS automation started.")
    
    await safe_edit_message(
        callback,
        texts.ORDER_CREATED.format(
            product=product_name,
            price=pricing.final_amount,
            balance=user.balance,
            eta=eta
        ) + automation_note,
        parse_mode="Markdown"
    )
    await state.clear()
    await callback.answer(texts.ORDER_CREATED_SUCCESS)


@router.callback_query(F.data == "bulk_edit_others", OrderStates.confirmation)
async def edit_bulk_order(callback: CallbackQuery, state: FSMContext, texts, buttons):
    """Обработчик кнопки Edit для bulk заказов"""
    data = await state.get_data()
    service = data.get("service")
    
    # Возвращаем пользователя к вводу bulk данных
    await state.set_state(OrderStates.waiting_bulk_data)
    
    # Получаем пример для конкретного сервиса
    examples = {
        "lookup_dl": texts.DL_BULK_EXAMPLE,
        "lookup_credit": texts.CS_BULK_EXAMPLE, 
        "lookup_bg": texts.BG_BULK_EXAMPLE,
        "lookup_mvr": texts.MVR_BULK_EXAMPLE,
        "lookup_fullmvr": texts.MVR_BULK_EXAMPLE,
    }
    
    localized_example = examples.get(service, "Enter your data...")
    
    service_names = {
        "lookup_dl": "DL Lookup",
        "lookup_credit": "Credit Score Lookup",
        "lookup_bg": "Background Lookup", 
        "lookup_mvr": "MVR Lookup",
        "lookup_fullmvr": "Full MVR Lookup",
    }
    
    service_name = service_names.get(service, "Lookup")
    bulk_price = ServicePrices.get_service_price(service, is_bulk=True)
    
    await safe_edit_message(callback,
        f"{texts.SERVICE_BULK_ORDER_HEADER.format(service_name=service_name)}\n"
        f"{texts.SERVICE_PRICE_PER_ENTRY.format(price=bulk_price)}\n\n"
        f"{localized_example}"
    )
    await callback.answer()


@router.callback_query(F.data == "confirm_no_others", OrderStates.confirmation)
@router.callback_query(F.data == "bulk_cancel_others", OrderStates.confirmation)
async def cancel_lookup_order(callback: CallbackQuery, state: FSMContext, texts, buttons):
    data = await state.get_data()
    service = data.get("service")
    
    if service not in ["lookup_dl", "lookup_credit", "lookup_bg", "lookup_mmn", "lookup_ein", "lookup_mvr", "lookup_fullmvr"]:
        return
    
    await safe_edit_message(callback, texts.ORDER_CANCELLED)
    await state.clear()
    await callback.answer()


@router.callback_query(F.data.startswith("cs_retry_order:"))
@router.callback_query(F.data.startswith("cs_retry_item:"))
async def retry_cs_automation(callback: CallbackQuery, session: AsyncSession, mirror_bot_id: int, texts, buttons):
    parts = callback.data.split(":")
    retry_item = parts[0] == "cs_retry_item"
    order_id = int(parts[1])
    item_number = int(parts[2]) if retry_item and len(parts) > 2 else None

    result = await session.execute(
        select(Order).where(
            Order.id == order_id,
            Order.user_id == callback.from_user.id,
            Order.mirror_bot_id == mirror_bot_id,
            Order.service_name == "lookup_credit",
        )
    )
    source_order = result.scalar_one_or_none()
    if not source_order:
        await callback.answer("Order not found", show_alert=True)
        return

    input_data = source_order.input_data or {}
    retry_price = source_order.price
    if retry_item:
        item_result = await session.execute(
            select(BulkOrderItem).where(
                BulkOrderItem.order_id == source_order.id,
                BulkOrderItem.item_number == item_number,
            )
        )
        source_item = item_result.scalar_one_or_none()
        if not source_item:
            await callback.answer("Item not found", show_alert=True)
            return
        input_data = source_item.input_data or {}
        retry_price = source_order.price / max(source_order.bulk_count or 1, 1)

    user = await UserService.get_user(session, callback.from_user.id, mirror_bot_id)
    if not user or user.balance < retry_price:
        await callback.answer(texts.INSUFFICIENT_BALANCE_ALERT, show_alert=True)
        return

    success = await OrderService.deduct_balance(session, callback.from_user.id, retry_price)
    if not success:
        await callback.answer(texts.INSUFFICIENT_BALANCE_ALERT, show_alert=True)
        return

    new_order = await OrderService.create_order(
        session,
        user_id=callback.from_user.id,
        mirror_bot_id=mirror_bot_id,
        category="lookup",
        service_name="lookup_credit",
        input_data=input_data,
        price=retry_price,
        bulk_items=None,
        notify_workers=False,
        notify_channel=False,
    )

    from mirror_bot.services.cs_automation import get_cs_runner

    runner = get_cs_runner(mirror_bot_id)
    if runner:
        await runner.enqueue_order(new_order.id)

    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    retry_text = {
        "ru": f"🔄 Повторный CS запуск создан.\n\nЗаказ: `#{new_order.id}`\nСписано: `${float(retry_price):.2f}`",
        "zh": f"🔄 已创建新的 CS 重试。\n\n订单: `#{new_order.id}`\n扣费: `${float(retry_price):.2f}`",
        "en": f"🔄 CS retry created.\n\nOrder: `#{new_order.id}`\nCharged: `${float(retry_price):.2f}`",
    }.get(user.language if user else "en", f"🔄 CS retry created.\n\nOrder: `#{new_order.id}`\nCharged: `${float(retry_price):.2f}`")

    await callback.message.answer(retry_text, parse_mode="Markdown")
    await callback.answer(texts.ORDER_CREATED_SUCCESS)

