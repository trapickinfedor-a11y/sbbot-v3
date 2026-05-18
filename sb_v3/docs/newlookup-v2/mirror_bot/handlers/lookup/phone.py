from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import ValidationError
from mirror_bot.states.order import OrderStates
from mirror_bot.services.validator import PhoneSearchData
from mirror_bot.services.order_service import OrderService
from mirror_bot.services.checkout_coupon_service import CheckoutCouponService
from mirror_bot.services.user_service import UserService
from mirror_bot.constants.prices import ServicePrices
from mirror_bot.constants.service_eta import ServiceETA
from mirror_bot.constants.language_loader import get_texts
from mirror_bot.keyboards.inline import confirm_keyboard
from mirror_bot.filters.service_filter import ServiceFilter
from mirror_bot.utils.message_utils import safe_edit_message
from mirror_bot.utils.product_translations import ProductTranslations

router = Router()


@router.callback_query(F.data.in_(["phone_name", "phone_ssn", "phone_full"]))
async def phone_search_type(callback: CallbackQuery, state: FSMContext, texts, buttons):
    service_map = {
        "phone_name": ("NAME LOOKUP", ServicePrices.LOOKUP_PHONE_NAME, "[Phone](https://t.me/ONE_TUTORIAL/5)"),
        "phone_ssn": ("NAME DOB SSN", ServicePrices.LOOKUP_PHONE_SSN, "[Phone + SSN](https://t.me/ONE_TUTORIAL/6)"),
        "phone_full": ("FULL LOOKUP", ServicePrices.LOOKUP_PHONE_FULL, "[Phone + SSN + CS](https://t.me/ONE_TUTORIAL/7)")
    }
    
    service_name, price, tutorial_link = service_map[callback.data]
    
    await state.set_state(OrderStates.waiting_data)
    await state.update_data(
        service="phone_search",
        service_type=callback.data,
        service_name=service_name,
        price=price
    )
    
    await safe_edit_message(callback,
        texts.PHONE_LOOKUP_FORMAT.format(service_name=service_name, price=price, tutorial_link=tutorial_link),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.message(OrderStates.waiting_data, ServiceFilter("phone_search"), F.text)
async def phone_data_handler(message: Message, state: FSMContext, session: AsyncSession, mirror_bot_id: int, texts, buttons):
    data = await state.get_data()
    service_name = data.get("service_name")
    service_type = data.get("service_type")
    price = data.get("price")

    try:
        validated_data = PhoneSearchData(phone=message.text.strip())

        confirmation_text = texts.ORDER_CONFIRMATION.format(
            service_name=f"Phone {service_name}",
            price=price
        ) + f"\n\n📞 {validated_data.phone}"

        await state.update_data(
            validated_data=validated_data.dict(),
            checkout_category="lookup",
            checkout_service_name=service_type,
            checkout_base_price=str(price),
            checkout_confirm_text=confirmation_text,
            checkout_keyboard_type="confirm",
            checkout_keyboard_suffix="_phone",
            checkout_parse_mode="Markdown",
            selected_coupon_code=None,
            selected_user_coupon_id=None,
        )
        await state.set_state(OrderStates.confirmation)
        await message.answer(confirmation_text, reply_markup=confirm_keyboard(buttons, suffix="_phone"), parse_mode="Markdown")

    except ValidationError as e:
        await message.answer(
            f"❌ {e.errors()[0]['msg']}\n\n"
            f"{texts.PHONE_EXAMPLE_FORMAT}"
        )


@router.callback_query(F.data == "confirm_yes_phone", OrderStates.confirmation)
async def confirm_phone_order(callback: CallbackQuery, state: FSMContext, session: AsyncSession, mirror_bot_id: int, texts):
    data = await state.get_data()
    service = data.get("service")
    
    if service != "phone_search":
        return
    
    validated_data = data.get("validated_data")
    service_type = data.get("service_type")
    price = data.get("price")
    
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
    
    order = await OrderService.create_order(
        session,
        user_id=callback.from_user.id,
        mirror_bot_id=mirror_bot_id,
        category="lookup",
        service_name=service_type,
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
        "lookup", 
        user_language
    )
    service_name = ProductTranslations.get_service_name(
        service_type,
        user_language
    )
    
    # Формируем название продукта используя переведённое имя сервиса
    product_name = service_name
    if data.get('state'):
        product_name += f" - {data.get('state')}"
    
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


@router.callback_query(F.data == "confirm_no_phone", OrderStates.confirmation)
async def cancel_phone_order(callback: CallbackQuery, state: FSMContext, texts):
    data = await state.get_data()
    service = data.get("service")
    
    if service != "phone_search":
        return
    
    await safe_edit_message(callback, texts.ORDER_CANCELLED)
    await state.clear()
    await callback.answer()

