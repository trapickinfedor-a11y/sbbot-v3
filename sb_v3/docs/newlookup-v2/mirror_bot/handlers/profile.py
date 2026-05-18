from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal, InvalidOperation
import os
import httpx
from mirror_bot.keyboards.inline import profile_keyboard, topup_keyboard, payment_link_keyboard, language_keyboard
from mirror_bot.middlewares.language import LanguageHelper
from mirror_bot.constants.language_loader import get_texts
from mirror_bot.constants.buttons_en import ButtonTexts
from mirror_bot.services.user_service import UserService
from mirror_bot.services.payment_service import PaymentService
from mirror_bot.services.payment_monitor import payment_monitor
from mirror_bot.states.order import TopupStates, SendMoneyStates, CouponStates
from mirror_bot.config import mirror_bot_config
from mirror_bot.utils.message_utils import safe_edit_message
from mirror_bot.utils.media_library import resolve_bot_photo
from shared.services.coupon_service import CouponService
from shared.services.ledger_service import LedgerService
from shared.security.internal_api import build_internal_api_headers
import logging

logger = logging.getLogger(__name__)

router = Router()

PROFILE_PHOTO = resolve_bot_photo("profile", "профиль", fallback_path="media/профиль.png")
REFERRAL_PHOTO = resolve_bot_photo("referral", "реф", fallback_path="media/реф.jpg")
TOPUP_PHOTO = resolve_bot_photo("topup", "top up", fallback_path="media/top up.jpg")
MAIN_BOT_API_URL = os.getenv("MAIN_BOT_API_URL", "http://localhost:8080/api/v1")


def _render_profile_text(texts, user, referrals_count: int) -> str:
    profile_text = texts.PROFILE_TEXT.format(
        user_id=user.user_id,
        balance=user.balance,
        created_at=user.created_at.strftime("%Y-%m-%d"),
        referral_link=f"https://t.me/{mirror_bot_config.main_bot_username}?start={user.referral_link}",
        referrals_count=referrals_count,
    )
    active_coupon_code = getattr(user, "active_coupon_code", None)
    if active_coupon_code:
        profile_text += f"\n\n🎟 Active coupon: <code>{active_coupon_code}</code>"
    return profile_text


@router.message(F.text.in_(ButtonTexts.get_all_variants("MY_PROFILE")))
async def profile_handler(message: Message, session: AsyncSession, mirror_bot_id: int, texts, buttons):
    user = await UserService.get_user(session, message.from_user.id, mirror_bot_id)
    
    if not user:
        await message.answer(texts.USER_NOT_FOUND)
        return
    
    ref_stats = await UserService.get_referral_stats(session, message.from_user.id)
    profile_text = _render_profile_text(texts, user, ref_stats["referrals_count"])
    
    try:
        await message.answer_photo(
            photo=PROFILE_PHOTO,
            caption=profile_text,
            reply_markup=profile_keyboard(buttons),
            parse_mode=None
        )
    except Exception:
        await message.answer(
            profile_text,
            reply_markup=profile_keyboard(buttons),
            parse_mode=None
        )


@router.callback_query(F.data == "apply_coupon")
async def apply_coupon_prompt(callback: CallbackQuery, state: FSMContext, session: AsyncSession, mirror_bot_id: int, texts, buttons):
    user = await UserService.get_user(session, callback.from_user.id, mirror_bot_id)
    if not user:
        await callback.answer(texts.USER_NOT_FOUND_ALERT, show_alert=True)
        return
    await state.set_state(CouponStates.waiting_code)
    current_coupon = f"\n\nCurrent coupon: <code>{user.active_coupon_code}</code>" if getattr(user, "active_coupon_code", None) else ""
    await safe_edit_message(
        callback,
        "Enter coupon code to apply a special discount.\nSend /clear to remove the active coupon."
        f"{current_coupon}",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(CouponStates.waiting_code, F.text)
async def coupon_code_handler(message: Message, state: FSMContext, session: AsyncSession, mirror_bot_id: int, texts, buttons):
    user = await UserService.get_user(session, message.from_user.id, mirror_bot_id)
    if not user:
        await state.clear()
        await message.answer(texts.USER_NOT_FOUND)
        return

    raw_code = (message.text or "").strip()
    if raw_code.lower() in {"/clear", "clear", "remove"}:
        await CouponService.clear_user_coupon(session, user)
        await state.clear()
        await message.answer("Coupon cleared. Future purchases will use regular pricing.")
        return

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{MAIN_BOT_API_URL}/coupons/activate",
                json={"code": raw_code},
                headers={
                    **build_internal_api_headers(),
                    "X-Mirror-Bot-Id": str(mirror_bot_id),
                    "X-User-Id": str(user.user_id),
                },
            )
    except Exception as exc:
        logger.error("Coupon activation API failed: %s", exc)
        await message.answer("Coupon activation is temporarily unavailable. Please try again later.")
        return

    if response.status_code == 404:
        await message.answer("Coupon not found. Try another code or send /clear.")
        return
    if response.status_code in {400, 409}:
        detail = response.json().get("detail") if response.headers.get("content-type", "").startswith("application/json") else None
        await message.answer(f"Coupon cannot be applied: {detail or 'Unknown error'}")
        return
    if response.status_code >= 500:
        await message.answer("Coupon activation is temporarily unavailable. Please try again later.")
        return

    await state.clear()
    await message.answer(
        f"Coupon <code>{CouponService.normalize_code(raw_code)}</code> activated. It will be applied automatically on eligible purchases.",
        parse_mode="HTML",
    )


@router.callback_query(F.data == "ref_system")
async def referral_system_handler(callback: CallbackQuery, session: AsyncSession, mirror_bot_id: int, texts, buttons):
    import json
    from sqlalchemy import select as _sel
    from shared.database.models import SystemSetting

    user = await UserService.get_user(session, callback.from_user.id, mirror_bot_id)
    if not user:
        await callback.answer(texts.USER_NOT_FOUND_ALERT, show_alert=True)
        return

    ref_stats = await UserService.get_referral_stats(session, callback.from_user.id)

    rates_row = await session.scalar(_sel(SystemSetting).where(SystemSetting.key == "referral_rates"))
    try:
        rates = {**{"1": 10.0, "2": 7.0, "3": 5.0, "4": 3.0}, **(json.loads(rates_row.value) if rates_row else {})}
    except Exception:
        rates = {"1": 10.0, "2": 7.0, "3": 5.0, "4": 3.0}

    total_pct = sum(float(rates.get(str(i), 0)) for i in range(1, 5))
    ref_link = f"https://t.me/{mirror_bot_config.main_bot_username}?start={user.referral_link}"
    caption = (
        f"🤝 <b>Referral Program — up to +{total_pct:.0f}%</b>\n\n"
        f"Your referral link:\n{ref_link}\n\n"
        f"💰 Total earned: <b>${ref_stats['earned']:.2f}</b>\n"
        f"👥 Direct referrals: <b>{ref_stats['count']}</b>\n\n"
        f"📊 <b>4-level system:</b> every purchase in your chain earns "
        f"you a bonus on your balance — automatically.\n\n"
        f"1️⃣ Level 1 — <b>{rates.get('1', 10)}%</b>\n"
        f"2️⃣ Level 2 — <b>{rates.get('2', 7)}%</b>\n"
        f"3️⃣ Level 3 — <b>{rates.get('3', 5)}%</b>\n"
        f"4️⃣ Level 4 — <b>{rates.get('4', 3)}%</b>\n\n"
        f"Share your link and earn from every order your referrals make!"
    )

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Copy Link", url=ref_link)],
        [InlineKeyboardButton(text=buttons.BACK, callback_data="back_to_profile")],
    ])

    try:
        await callback.message.delete()
        await callback.bot.send_photo(
            chat_id=callback.message.chat.id,
            photo=REFERRAL_PHOTO,
            caption=caption,
            reply_markup=kb,
            parse_mode="HTML",
        )
    except Exception:
        await safe_edit_message(callback, caption, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data == "view_rules")
async def view_rules_handler(callback: CallbackQuery, texts, buttons):
    """Просмотр правил из профиля"""
    try:
        await callback.message.delete()
    except Exception:
        pass

    RULES_PHOTO = resolve_bot_photo("rules", "правила", fallback_path="media/правила.jpg")
    try:
        await callback.bot.send_photo(
            chat_id=callback.message.chat.id,
            photo=RULES_PHOTO
        )
    except Exception:
        pass

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=buttons.BACK, callback_data="back_to_profile")]
    ])
    await callback.bot.send_message(
        chat_id=callback.message.chat.id,
        text=texts.RULES_TEXT,
        reply_markup=back_kb,
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_profile")
async def back_to_profile_handler(callback: CallbackQuery, session: AsyncSession, mirror_bot_id: int, texts, buttons):
    """Возврат в профиль"""
    try:
        await callback.message.delete()
    except Exception:
        pass

    user = await UserService.get_user(session, callback.from_user.id, mirror_bot_id)
    if not user:
        await callback.answer(texts.USER_NOT_FOUND_ALERT, show_alert=True)
        return

    ref_stats = await UserService.get_referral_stats(session, callback.from_user.id)

    try:
        await callback.bot.send_photo(
            chat_id=callback.message.chat.id,
            photo=PROFILE_PHOTO,
            caption=texts.PROFILE_TEXT.format(
                user_id=user.user_id,
                balance=user.balance,
                created_at=user.created_at.strftime("%Y-%m-%d"),
                referral_link=f"https://t.me/{mirror_bot_config.main_bot_username}?start={user.referral_link}",
                referrals_count=ref_stats["referrals_count"]
            ),
            reply_markup=profile_keyboard(buttons),
            parse_mode=None
        )
    except Exception:
        await callback.bot.send_message(
            chat_id=callback.message.chat.id,
            text=texts.PROFILE_TEXT.format(
                user_id=user.user_id,
                balance=user.balance,
                created_at=user.created_at.strftime("%Y-%m-%d"),
                referral_link=f"https://t.me/{mirror_bot_config.main_bot_username}?start={user.referral_link}",
                referrals_count=ref_stats["referrals_count"]
            ),
            reply_markup=profile_keyboard(buttons),
            parse_mode=None
        )
    await callback.answer()


@router.message(F.text.in_(ButtonTexts.get_all_variants("TOP_UP_BALANCE")))
async def topup_balance_handler(message: Message, texts, buttons):
    try:
        await message.answer_photo(
            photo=TOPUP_PHOTO,
            caption=texts.TOPUP_STEP1,
            reply_markup=topup_keyboard(buttons),
            parse_mode=None
        )
    except Exception:
        await message.answer(
            texts.TOPUP_STEP1,
            reply_markup=topup_keyboard(buttons),
            parse_mode=None
        )


@router.callback_query(F.data.in_(["pay_cryptopay", "pay_cryptomus"]))
async def payment_method_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, mirror_bot_id: int, texts, buttons):
    await state.update_data(payment_method=callback.data)
    await state.set_state(TopupStates.waiting_amount)
    if callback.data == "pay_cryptopay":
        message_text = texts.TOPUP_STEP2_CRYPTOPAY
    else:
        message_text = texts.TOPUP_STEP2
    await safe_edit_message(callback, message_text, parse_mode=None)
    await callback.answer()


@router.message(TopupStates.waiting_amount)
async def topup_amount_handler(message: Message, state: FSMContext, mirror_bot_id: int, texts, buttons, bot):
    try:
        amount = Decimal(message.text)
        
        if amount < mirror_bot_config.min_topup or amount > mirror_bot_config.max_topup:
            await message.answer(texts.TOPUP_INVALID_AMOUNT, parse_mode=None)
            return
        
        data = await state.get_data()
        payment_method = data.get("payment_method")
        
        if payment_method == "pay_cryptopay":
            invoice = await PaymentService.create_cryptobot_invoice(amount, message.from_user.id)
            payment_text = texts.TOPUP_STEP3_CRYPTOPAY.format(amount=amount)
            await state.update_data(
                invoice_id=invoice["invoice_id"], 
                amount=amount,
                payment_method="cryptopay"
            )
        elif payment_method == "pay_cryptomus":
            invoice = await PaymentService.create_cryptomus_invoice(amount, message.from_user.id)
            payment_text = texts.TOPUP_STEP3
            await state.update_data(
                invoice_id=invoice["invoice_id"],
                order_id=invoice.get("order_id"),
                amount=amount,
                payment_method="cryptomus"
            )
        else:
            await message.answer(texts.INVALID_PAYMENT_METHOD)
            await state.clear()
            return
        
        await state.set_state(TopupStates.waiting_payment)
        
        # Запускаем фоновый мониторинг платежа
        # Важно: invoice_id должен быть строкой для единообразия
        invoice_id_str = str(invoice["invoice_id"])
        payment_method_clean = payment_method.replace("pay_", "")  # "pay_cryptopay" -> "cryptopay"
        
        payment_monitor.start_monitoring(
            user_id=message.from_user.id,
            invoice_id=invoice_id_str,
            order_id=invoice.get("order_id"),
            amount=amount,
            payment_method=payment_method_clean,
            expires_in_seconds=3600,  # 1 час
            mirror_bot_id=mirror_bot_id,
            bot=bot
        )
        
        await message.answer(
            payment_text,
            reply_markup=payment_link_keyboard(invoice["payment_url"], buttons),
            parse_mode=None
        )
    
    except (ValueError, TypeError, InvalidOperation):
        await message.answer(texts.TOPUP_INVALID_AMOUNT, parse_mode=None)
    except Exception as e:
        await message.answer(texts.ERROR_CREATING_PAYMENT.format(error=str(e)), parse_mode=None)


@router.callback_query(F.data == "check_payment", TopupStates.waiting_payment)
async def check_payment_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, mirror_bot_id: int, texts):
    data = await state.get_data()
    invoice_id = data.get("invoice_id")
    amount = data.get("amount")
    payment_method = data.get("payment_method", "cryptopay")
    order_id = data.get("order_id")
    
    # Проверяем статус в зависимости от метода оплаты
    if payment_method == "cryptomus":
        status = await PaymentService.check_payment_status(invoice_id, method="cryptomus", order_id=order_id)
    else:
        status = await PaymentService.check_payment_status(invoice_id, method="cryptopay")
    
    if status == "paid":
        new_balance = await UserService.add_balance_with_marketer(session, callback.from_user.id, Decimal(amount), mirror_bot_id)

        # Останавливаем фоновый мониторинг (invoice_id должен быть строкой)
        payment_monitor.stop_monitoring(str(invoice_id))

        if new_balance is not None:
            await safe_edit_message(
                callback,
                texts.TOPUP_SUCCESS_SHORT.format(amount=amount)
            )
            await state.clear()
            await callback.answer(texts.PAYMENT_SUCCESSFUL)
        else:
            logger.error(f"Failed to credit balance for user {callback.from_user.id}")
            await callback.answer("Payment received but failed to credit balance. Please contact support.", show_alert=True)
    elif status == "expired" or status == "cancelled":
        # Платёж истёк или отменён
        payment_monitor.stop_monitoring(str(invoice_id))
        await state.clear()
        await safe_edit_message(
            callback,
            texts.TOPUP_EXPIRED
        )
        await callback.answer(texts.PAYMENT_EXPIRED, show_alert=True)
    else:
        await callback.answer(texts.PAYMENT_NOT_RECEIVED)


@router.callback_query(F.data == "send_money")
async def send_money_handler(callback: CallbackQuery, state: FSMContext, texts):
    await state.set_state(SendMoneyStates.waiting_user_id)
    await safe_edit_message(callback, texts.SEND_MONEY_TEXT, parse_mode=None)
    await callback.answer()


@router.message(SendMoneyStates.waiting_user_id)
async def send_money_user_id_handler(message: Message, state: FSMContext, session: AsyncSession, mirror_bot_id: int, texts):
    try:
        recipient_id = int(message.text)
        await state.update_data(recipient_id=recipient_id)
        await state.set_state(SendMoneyStates.waiting_amount)
        
        sender = await UserService.get_user(session, message.from_user.id, mirror_bot_id)
        balance = sender.balance if sender else Decimal("0.00")
        
        await message.answer(texts.SEND_MONEY_AMOUNT_SHORT.format(balance=balance))
    
    except ValueError:
        await message.answer(texts.INVALID_USER_ID)


@router.message(SendMoneyStates.waiting_amount)
async def send_money_amount_handler(message: Message, state: FSMContext, session: AsyncSession, mirror_bot_id: int, texts, buttons):
    try:
        amount = Decimal(message.text)
        
        if amount <= 0:
            await message.answer(texts.INVALID_AMOUNT_NUMBER)
            return
        
        data = await state.get_data()
        recipient_id = data.get("recipient_id")
        
        # Проверяем существование отправителя
        sender = await UserService.get_user(session, message.from_user.id, mirror_bot_id)
        
        if not sender:
            await message.answer(texts.USER_NOT_FOUND_CONTACT_SUPPORT)
            await state.clear()
            return
        
        # Проверяем существование получателя
        recipient = await UserService.get_user(session, recipient_id, mirror_bot_id)
        
        if not recipient:
            await message.answer(texts.RECIPIENT_NOT_FOUND.format(recipient_id=recipient_id))
            await state.clear()
            return
        
        if sender.balance < amount:
            await message.answer(
                texts.SEND_MONEY_INSUFFICIENT_SHORT.format(balance=sender.balance, amount=amount)
            )
            return
        
        # Сохраняем сумму в state и переходим к подтверждению
        await state.update_data(amount=amount)
        await state.set_state(SendMoneyStates.confirmation)
        
        balance_after = sender.balance - amount
        
        # Импортируем клавиатуру подтверждения
        from mirror_bot.keyboards.inline import confirm_keyboard
        
        await message.answer(
            texts.SEND_MONEY_CONFIRM.format(
                amount=amount, 
                recipient_id=recipient_id, 
                balance_after=balance_after
            ),
            reply_markup=confirm_keyboard(buttons, suffix="_sendmoney"),
            parse_mode="Markdown"
        )
    
    except (ValueError, TypeError, InvalidOperation):
        await message.answer(texts.INVALID_AMOUNT_NUMBER)


@router.callback_query(F.data == "confirm_yes_sendmoney", SendMoneyStates.confirmation)
async def send_money_confirm_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, mirror_bot_id: int, texts):
    """Подтверждение перевода"""
    data = await state.get_data()
    recipient_id = data.get("recipient_id")
    amount = Decimal(str(data.get("amount")))
    
    sender = await UserService.get_user(session, callback.from_user.id, mirror_bot_id)
    
    if not sender:
        await callback.message.answer(texts.USER_NOT_FOUND_CONTACT_SUPPORT)
        await state.clear()
        await callback.answer()
        return
    
    # Повторно проверяем существование получателя перед переводом
    recipient = await UserService.get_user(session, recipient_id, mirror_bot_id)
    
    if not recipient:
        await callback.message.answer(texts.RECIPIENT_NOT_FOUND.format(recipient_id=recipient_id))
        await state.clear()
        await callback.answer()
        return
    
    if sender.balance < amount:
        await callback.message.answer(
            texts.SEND_MONEY_INSUFFICIENT_SHORT.format(balance=sender.balance, amount=amount)
        )
        await state.clear()
        await callback.answer()
        return
    
    debit_tx = await LedgerService.debit_user_balance(
        session,
        user_id=sender.user_id,
        amount=amount,
        tx_type="transfer_out",
        description=f"Transfer to {recipient_id}",
        related_entity_type="user_transfer",
        related_entity_id=recipient_id,
    )
    credit_tx = await LedgerService.credit_user_balance(
        session,
        user_id=recipient_id,
        amount=amount,
        tx_type="transfer_in",
        description=f"Transfer from {callback.from_user.id}",
        related_entity_type="user_transfer",
        related_entity_id=sender.user_id,
    )

    if debit_tx is None or credit_tx is None:
        await callback.message.answer(
            f"❌ Transfer failed: Recipient user {recipient_id} not found in database."
        )
        await state.clear()
        await callback.answer()
        return

    await session.commit()

    await safe_edit_message(
        callback,
        texts.SEND_MONEY_SUCCESS_SHORT.format(amount=amount, recipient_id=recipient_id, balance=sender.balance),
        parse_mode=None
    )
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "confirm_no_sendmoney", SendMoneyStates.confirmation)
async def send_money_cancel_handler(callback: CallbackQuery, state: FSMContext, texts):
    """Отмена перевода"""
    await safe_edit_message(callback, texts.CANCELLED, parse_mode=None)
    await state.clear()
    await callback.answer()


# ========== CC ORDERS ==========

@router.callback_query(F.data == "buyer_my_cc_orders")
async def buyer_my_cc_orders_handler(callback: CallbackQuery, session: AsyncSession, mirror_bot_id: int, texts, buttons):
    """Список CC заказов пользователя (SellerCCOrder)."""
    from sqlalchemy import select, desc
    from shared.database.models import SellerCCOrder, SellerCCItem

    page_data = callback.data  # for future pagination

    result = await session.execute(
        select(SellerCCOrder)
        .where(SellerCCOrder.buyer_user_id == callback.from_user.id)
        .order_by(desc(SellerCCOrder.created_at))
        .limit(10)
    )
    orders = result.scalars().all()

    if not orders:
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        await safe_edit_message(
            callback,
            "💳 *My CC Orders*\n\nYou have no CC orders yet.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=buttons.BACK, callback_data="back_to_profile")]
            ]),
            parse_mode="Markdown",
        )
        await callback.answer()
        return

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    status_map = {
        "pending_admin": "⏳ Pending",
        "approved": "✅ Approved",
        "completed": "📦 Completed",
        "rejected": "❌ Rejected",
        "cancelled": "🚫 Cancelled",
    }

    lines = ["💳 *My CC Orders*\n"]
    for o in orders:
        status = status_map.get(o.status, o.status)
        created = o.created_at.strftime("%d.%m.%y") if o.created_at else "—"
        lines.append(f"• #{o.id} — ${o.price_for_buyer:.2f} — {status} — {created}")

    await safe_edit_message(
        callback,
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=buttons.BACK, callback_data="back_to_profile")]
        ]),
        parse_mode="Markdown",
    )
    await callback.answer()


# ========== LANGUAGE SELECTION HANDLERS ==========

@router.callback_query(F.data == "choose_lang")
async def choose_language_handler(callback: CallbackQuery, texts, buttons):
    """Показать меню выбора языка"""
    await safe_edit_message(
        callback,
        texts.CHOOSE_YOUR_LANGUAGE,
        reply_markup=language_keyboard(buttons),
        parse_mode=None
    )


    # Language handler removed — handled by start.py router which is registered first

