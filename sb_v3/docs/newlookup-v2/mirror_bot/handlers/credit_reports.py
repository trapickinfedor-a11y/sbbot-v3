from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import ValidationError
import logging
from mirror_bot.states.order import OrderStates
from mirror_bot.services.validator import CreditReportData
from mirror_bot.services.parser import DataParser
from mirror_bot.services.order_service import OrderService
from mirror_bot.services.checkout_coupon_service import CheckoutCouponService
from mirror_bot.services.user_service import UserService
from mirror_bot.constants.prices import ServicePrices
from mirror_bot.constants.service_eta import ServiceETA
from mirror_bot.middlewares.language import LanguageHelper
from mirror_bot.keyboards.inline import credit_reports_keyboard, confirm_keyboard, order_type_keyboard, bulk_confirmation_keyboard
from mirror_bot.filters.service_filter import ServiceFilter
from mirror_bot.config import mirror_bot_config
from mirror_bot.services.parser import DataParser as BulkParser
from mirror_bot.utils.message_utils import safe_edit_message
from mirror_bot.utils.product_translations import ProductTranslations
from mirror_bot.constants.buttons_en import ButtonTexts
from mirror_bot.utils.media_library import resolve_bot_photo
# ServiceDescriptions интегрированы в основные файлы переводов

router = Router()
logger = logging.getLogger(__name__)

CREDIT_REPORTS_PHOTO = resolve_bot_photo("credit_reports", "creditreports", fallback_path="media/creditreports.jpg")
CREDIT_SCORE_PHOTO = resolve_bot_photo("credit_score", "creditscore", fallback_path="media/creditscore.jpg")


@router.message(F.text.in_(ButtonTexts.get_all_variants("CREDIT_REPORTS")))
async def credit_reports_main(message: Message, texts, buttons):
    try:
        await message.answer_photo(
            photo=CREDIT_REPORTS_PHOTO,
            caption=texts.CREDIT_REPORTS_HEADER.format(provider=buttons.CREDIT_REPORTS),
            reply_markup=credit_reports_keyboard(buttons)
        )
    except Exception:
        await message.answer(
            texts.CREDIT_REPORTS_HEADER.format(provider=buttons.CREDIT_REPORTS),
            reply_markup=credit_reports_keyboard(buttons)
        )


SERVICE_MAP = {
    "cr_transunion": ("TransUnion", ServicePrices.CR_TRANSUNION, ServicePrices.CR_TRANSUNION_BULK, "[TransUnion](https://t.me/ONE_TUTORIAL/14)"),
    "cr_experian": ("Experian", ServicePrices.CR_EXPERIAN, ServicePrices.CR_EXPERIAN_BULK, "[Experian](https://t.me/ONE_TUTORIAL/15)"),
    "cr_equifax": ("Equifax", ServicePrices.CR_EQUIFAX, ServicePrices.CR_EQUIFAX, "[Equifax](https://t.me/ONE_TUTORIAL/16)"),  # No bulk price
    "cr_lexisnexis": ("LexisNexis", ServicePrices.CR_LEXISNEXIS, ServicePrices.CR_LEXISNEXIS_BULK, "[LexisNexis](https://t.me/ONE_TUTORIAL/17)"),
    "cr_wallet": ("WalletHub/Credit Karma", ServicePrices.CR_WALLETHUB, ServicePrices.CR_WALLETHUB_BULK, "[WalletHub](https://t.me/ONE_TUTORIAL/18)")
}


@router.callback_query(F.data.in_(["cr_transunion", "cr_experian", "cr_equifax", "cr_lexisnexis", "cr_wallet"]))
async def credit_report_start(callback: CallbackQuery, state: FSMContext, texts, buttons):
    service_type = callback.data
    service_name, single_price, bulk_price, tutorial_link = SERVICE_MAP[service_type]
    
    await state.update_data(
        service="credit_report",
        service_type=service_type,
        service_name=service_name,
        single_price=single_price,
        bulk_price=bulk_price
    )
    await state.set_state(OrderStates.waiting_data)
    
    from mirror_bot.keyboards.inline import bulk_order_keyboard
    
    # Используем стандартный формат из texts
    if service_type == "cr_equifax":
        # Equifax doesn't have bulk pricing, so no bulk price
        await safe_edit_message(callback,
            texts.CREDIT_REPORT_FORMAT.format(
                service_name=service_name,
                single_price=single_price,
                tutorial_link=tutorial_link,
                example_text=texts.CR_SINGLE_EXAMPLE
            ),
            reply_markup=bulk_order_keyboard(buttons),
            parse_mode="Markdown"
        )
    else:
        # Get bulk price for other services
        bulk_price = ServicePrices.get_service_price(service_type, is_bulk=True)
        await safe_edit_message(callback,
            texts.CREDIT_REPORT_FORMAT.format(
                service_name=service_name,
                single_price=single_price,
                tutorial_link=tutorial_link,
                example_text=texts.CR_SINGLE_EXAMPLE
            ),
            reply_markup=bulk_order_keyboard(buttons, bulk_price),
            parse_mode="Markdown"
        )
    
    await callback.answer()




@router.message(OrderStates.waiting_data, ServiceFilter("credit_report"), F.text)
async def credit_report_data_handler(message: Message, state: FSMContext, session: AsyncSession, mirror_bot_id: int, texts, buttons):
    """Универсальный обработчик - автоматически определяет single или bulk"""
    text = message.text.strip()
    data = await state.get_data()
    
    # Проверяем, есть ли множественные записи
    entries = DataParser.parse_bulk_entries(text)
    
    if len(entries) == 1:
        # Single order
        await handle_single_credit_report(message, state, session, mirror_bot_id, text, texts, buttons)
    elif 2 <= len(entries) <= mirror_bot_config.max_bulk_items:
        # Bulk order
        await handle_bulk_credit_report(message, state, session, mirror_bot_id, text, texts, buttons)
    elif len(entries) > mirror_bot_config.max_bulk_items:
        await message.answer(texts.MAXIMUM_ENTRIES_FOR_BULK.format(max_items=mirror_bot_config.max_bulk_items))
    else:
        await message.answer(texts.INVALID_FORMAT_TRY_AGAIN)


async def handle_single_credit_report(message: Message, state: FSMContext, session: AsyncSession, mirror_bot_id: int, text: str, texts, buttons):
    data = await state.get_data()
    service_name = data.get("service_name")
    service_type = data.get("service_type")
    price = data.get("single_price")
    
    # Для WalletHub принимаем ЛЮБОЙ текст без валидации и парсинга
    if service_type == "cr_wallet":
        # БЕЗ ПАРСИНГА - принимаем любой текст как есть
        raw_text = text.strip()
        
        class RawData:
            def __init__(self, raw_input):
                self.raw_input = raw_input
            def dict(self):
                return {"raw_input": self.raw_input}
        
        validated_data = RawData(raw_text)
    else:
        parsed_data = DataParser.smart_parse_address_data(text, require_dob=True)

        if parsed_data['issues']:
            issues_text = "\n".join([f"• {issue}" for issue in parsed_data['issues']])
            await message.answer(texts.INVALID_DATA_FORMAT.format(issues_text=issues_text, example=texts.CR_SINGLE_EXAMPLE))
            return
        
        # Маппинг полей парсера на поля модели
        model_data = {
            'first_name': parsed_data.get('first'),
            'last_name': parsed_data.get('last'),
            'address': parsed_data.get('address'),
            'city': parsed_data.get('city'),
            'state': parsed_data.get('state'),
            'zip_code': parsed_data.get('zip'),
            'ssn': parsed_data.get('ssn'),
            'dob': parsed_data.get('dob')
        }

        try:
            validated_data = CreditReportData(**model_data)
        except ValidationError as e:
            errors = "\n".join([f"• {err['msg']}" for err in e.errors()])
            await message.answer(texts.VALIDATION_ERROR.format(errors=errors, example=texts.CR_SINGLE_EXAMPLE))
            return
    
    await state.update_data(validated_data=validated_data.dict(), price=price)
    await state.set_state(OrderStates.confirmation)
    
    # Для WalletHub показываем RAW данные
    if service_type == "cr_wallet":
        raw_input = validated_data.dict()['raw_input']
        confirmation_text = texts.ORDER_CONFIRMATION.format(
            service_name=f"{service_name} Credit Report",
            price=price
        ) + f"\n\n{texts.YOUR_DATA_LABEL}\n`{raw_input}`"
    else:
        # Для остальных показываем структурированные данные
        info_lines = [
            f"👤 `{validated_data.first_name} {validated_data.last_name}`",
            f"📍 `{validated_data.address}`",
            f"🏙️ `{validated_data.city}, {validated_data.state} {validated_data.zip_code}`",
            f"🆔 SSN: `{validated_data.ssn}`",
            f"🎂 DOB: `{validated_data.dob}`"
        ]
        
        confirmation_text = texts.ORDER_CONFIRMATION.format(
            service_name=f"{service_name} Credit Report",
            price=price
        ) + "\n\n" + "\n".join(info_lines)
    
    await state.update_data(
        checkout_category="credit_reports",
        checkout_service_name=service_type,
        checkout_base_price=str(price),
        checkout_confirm_text=confirmation_text,
        checkout_keyboard_type="confirm",
        checkout_keyboard_suffix="_cr",
        checkout_parse_mode="Markdown",
        selected_coupon_code=None,
        selected_user_coupon_id=None,
    )
    await message.answer(confirmation_text, reply_markup=confirm_keyboard(buttons, suffix="_cr"), parse_mode="Markdown")


async def handle_bulk_credit_report(message: Message, state: FSMContext, session: AsyncSession, mirror_bot_id: int, text: str, texts, buttons):
    logger.info(f"[CR BULK HANDLER] Triggered! User: {message.from_user.id}")
    
    data = await state.get_data()
    service_name = data.get("service_name")
    service_type = data.get("service_type")
    price_per_item = data.get("bulk_price")
    
    try:
        entries = BulkParser.parse_bulk_entries(text)
        
        if len(entries) < mirror_bot_config.min_bulk_items:
            await message.answer(texts.MIN_ENTRIES_REQUIRED.format(min_items=mirror_bot_config.min_bulk_items))
            return
        
        if len(entries) > mirror_bot_config.max_bulk_items:
            await message.answer(texts.MAX_ENTRIES_ALLOWED.format(max_items=mirror_bot_config.max_bulk_items))
            return
        
        validated_entries = []
        for i, entry in enumerate(entries, 1):
            # Для WalletHub принимаем ЛЮБОЙ текст без валидации и парсинга
            if service_type == "cr_wallet":
                # БЕЗ ПАРСИНГА - принимаем любой текст как есть
                validated_entries.append({"raw_input": entry.strip()})
            else:
                # Для остальных используем парсинг и валидацию
                from mirror_bot.services.validator import parse_freeform_text

                parsed_data = parse_freeform_text(entry, required_fields=["first_name", "last_name"])

                # Детальное логирование для отладки
                logger.info(f"[CR BULK DEBUG] Entry #{i}: {entry[:50]}...")
                logger.info(f"[CR BULK DEBUG] Parsed: first={parsed_data.get('first_name')}, last={parsed_data.get('last_name')}, ssn={parsed_data.get('ssn')}, dob={parsed_data.get('dob')}")
                logger.info(f"[CR BULK DEBUG] Errors: {parsed_data.get('errors')}")

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
                    'ssn': parsed_data.get('ssn'),
                    'dob': parsed_data.get('dob')
                }

                try:
                    validated = CreditReportData(**model_data)
                    validated_entries.append(validated.dict())
                except ValidationError as e:
                    await message.answer(texts.ENTRY_VALIDATION_ERROR.format(entry_num=i, error_msg=e.errors()[0]['msg']))
                    return
        
        final_price = price_per_item * len(validated_entries)
        
        summary = f"✅ {len(validated_entries)} entries validated!\n\n"
        for i, entry in enumerate(validated_entries, 1):
            summary += f"📋 **Entry #{i}:**\n"
            summary += f"👤 `{entry['first_name']} {entry['last_name']}`\n"
            summary += f"📍 `{entry['address']}`\n"
            summary += f"🏙️ `{entry['city']}, {entry['state']} {entry['zip_code']}`\n"
            summary += f"🆔 SSN: `{entry['ssn']}`\n"
            summary += f"🎂 DOB: `{entry['dob']}`\n\n"
        
        summary += texts.BULK_PRICE_PER_ITEM.format(price=price_per_item)
        summary += texts.TOTAL_WITH_CONFIRM.format(total=final_price)
        await state.update_data(
            validated_data=validated_entries,
            is_bulk=True,
            total_price=final_price,
            checkout_category="credit_reports",
            checkout_service_name=service_type,
            checkout_base_price=str(final_price),
            checkout_confirm_text=summary,
            checkout_keyboard_type="bulk",
            checkout_keyboard_suffix="_cr",
            checkout_parse_mode="Markdown",
            selected_coupon_code=None,
            selected_user_coupon_id=None,
        )
        await state.set_state(OrderStates.confirmation)
        await message.answer(summary, reply_markup=bulk_confirmation_keyboard(buttons, suffix="_cr"), parse_mode="Markdown")
    
    except Exception as e:
        logger.error(f"[CR BULK HANDLER] Error: {e}", exc_info=True)
        await message.answer(texts.ERROR_PROCESSING_BULK.format(error=str(e)))


@router.message(OrderStates.waiting_bulk_data, ServiceFilter("credit_report"), F.text)
async def credit_report_bulk_data_handler(message: Message, state: FSMContext, session: AsyncSession, mirror_bot_id: int, texts, buttons):
    """Обработчик bulk данных для Credit Reports"""
    text = message.text.strip()
    await handle_bulk_credit_report(message, state, session, mirror_bot_id, text, texts, buttons)


@router.callback_query(F.data == "confirm_yes_cr", OrderStates.confirmation)
@router.callback_query(F.data == "bulk_confirm_cr", OrderStates.confirmation)
async def confirm_cr_order(callback: CallbackQuery, state: FSMContext, session: AsyncSession, mirror_bot_id: int, texts, buttons):
    data = await state.get_data()
    service = data.get("service")
    
    if service != "credit_report":
        return
    
    validated_data = data.get("validated_data")
    is_bulk = data.get("is_bulk", False)
    service_type = data.get("service_type")
    
    if is_bulk:
        price = data.get("total_price")
        bulk_items = validated_data
        input_data = {"count": len(validated_data)}
    else:
        price = data.get("price")
        # Если price не был сохранён, получаем из single_price
        if price is None:
            price = data.get("single_price", ServicePrices.CREDIT_REPORT_TRANSUNION)
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
    
    # Automated CR services (TransUnion, Experian, Equifax, LexisNexis) skip workers;
    # WalletHub has no structured data so it still goes to workers.
    _cr_auto_services = {"cr_transunion", "cr_experian", "cr_equifax", "cr_lexisnexis"}
    notify_workers = service_type not in _cr_auto_services

    order = await OrderService.create_order(
        session,
        user_id=callback.from_user.id,
        mirror_bot_id=mirror_bot_id,
        category="credit_reports",
        service_name=service_type,
        input_data=input_data,
        price=pricing.final_amount,
        original_price=pricing.original_amount,
        coupon_code=pricing.code,
        discount_amount=pricing.discount_amount,
        coupon_application=pricing,
        bulk_items=bulk_items,
        notify_workers=notify_workers,
        notify_channel=True,
    )

    # Trigger CR automation for supported bureaus
    if service_type in _cr_auto_services:
        from mirror_bot.services.cr_automation import get_cr_runner
        cr_runner = get_cr_runner(mirror_bot_id)
        if cr_runner:
            await cr_runner.enqueue_order(order.id)
    
    user = await UserService.get_user(session, callback.from_user.id, mirror_bot_id)
    
    # Получаем информацию о категории и сервисе
    user_language = user.language if user and hasattr(user, 'language') else 'en'
    category_name = ProductTranslations.get_category_name(
        "credit_reports", 
        user_language
    )
    # service_type уже содержит "cr_experian" и т.д.
    service_name = ProductTranslations.get_service_name(
        service_type,
        user_language
    )
    
    # Формируем название продукта - используем переведённое имя
    product_name = service_name
    if data.get('state'):
        product_name += f" - {data.get('state')}"
    
    # Добавляем количество если bulk заказ
    if is_bulk and bulk_items:
        count = len(bulk_items)
        if count > 1:
            product_name += f" x{count}"
    
    # Получаем ETA на основе service_type
    eta = ServiceETA.get_eta(service_type)
    
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


@router.callback_query(F.data == "bulk_edit_cr", OrderStates.confirmation)
async def edit_bulk_cr_order(callback: CallbackQuery, state: FSMContext, texts, buttons):
    """Обработчик кнопки Edit для bulk заказов Credit Reports"""
    data = await state.get_data()
    service_name = data.get("service_name", "Credit Report")
    bulk_price = data.get("bulk_price", 0)
    
    # Возвращаем пользователя к вводу bulk данных
    await state.set_state(OrderStates.waiting_bulk_data)
    
    await safe_edit_message(callback,
        f"{texts.SERVICE_BULK_ORDER_HEADER.format(service_name=service_name)}\n"
        f"{texts.SERVICE_PRICE_PER_ENTRY.format(price=bulk_price)}\n\n"
        f"{texts.CR_BULK_EXAMPLE}"
    )
    await callback.answer()


@router.callback_query(F.data == "confirm_no_cr", OrderStates.confirmation)
@router.callback_query(F.data == "bulk_cancel_cr", OrderStates.confirmation)
async def cancel_cr_order(callback: CallbackQuery, state: FSMContext, texts, buttons):
    data = await state.get_data()
    service = data.get("service")
    
    if service != "credit_report":
        return
    
    await safe_edit_message(callback, texts.ORDER_CANCELLED)
    await state.clear()
    await callback.answer()

