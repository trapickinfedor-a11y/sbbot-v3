"""
Обработчик платежей через Crypto Pay и Cryptomus
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timezone
import logging

from mirror_bot.services.crypto_pay import CryptoPayAPI, CryptoPayError
from mirror_bot.services.crypto_pay_models import (
    Invoice, CryptoAsset, FiatCurrency, PaidButtonName
)
from mirror_bot.services.cryptomus import CryptomusAPI, CryptomusError
from mirror_bot.utils.message_utils import safe_edit_message
from mirror_bot.services.cryptomus_models import PaymentInfo
from mirror_bot.keyboards.inline import get_payment_keyboard
from mirror_bot.config import mirror_bot_config
from mirror_bot.constants.prices import SystemFees

logger = logging.getLogger(__name__)

router = Router(name="payment")


class PaymentManager:
    """Менеджер платежей"""
    
    def __init__(self, crypto_pay_api: CryptoPayAPI):
        self.api = crypto_pay_api
        self._active_invoices: Dict[int, Invoice] = {}  # user_id -> Invoice
    
    async def create_payment(
        self,
        user_id: int,
        amount_usd: float,
        description: str,
        payload: Optional[str] = None
    ) -> Tuple[Invoice, float, float]:
        """
        Создание платежа для пользователя с учетом комиссии платформы 3%
        
        Args:
            user_id: Telegram user ID
            amount_usd: Сумма пополнения (которая должна прийти на баланс)
            description: Описание платежа
            payload: Дополнительные данные (например, ID заказа)
        
        Returns:
            Tuple: (Invoice объект, сумма на баланс, сумма к оплате)
        """
        try:
            # Рассчитываем сумму с учетом комиссии
            # Формула: amount_to_pay = desired_amount / (1 - fee_percent / 100)
            # Пример: 100$ / 0.97 = 103.09$
            # Проверка: 103.09$ - 3% = 100$
            fee_percent = mirror_bot_config.payment_fee_percent
            amount_to_pay = round(amount_usd / (1 - fee_percent / 100), 2)
            
            invoice = await self.api.create_invoice(
                amount=str(amount_to_pay),
                currency_type="fiat",
                fiat=FiatCurrency.USD,
                description=description,
                payload=payload or f"user_{user_id}_topup_{amount_usd}",
                allow_comments=True,
                allow_anonymous=False,
                expires_in=86400,  # 24 часа на оплату
                accepted_assets=[
                    CryptoAsset.USDT,
                    CryptoAsset.TON,
                    CryptoAsset.BTC,
                    CryptoAsset.ETH,
                    CryptoAsset.USDC
                ]
            )
            
            self._active_invoices[user_id] = invoice
            logger.info(
                f"Created invoice {invoice.invoice_id} for user {user_id}: "
                f"balance +${amount_usd}, total payment ${amount_to_pay} (fee {fee_percent}%)"
            )
            
            return invoice, amount_usd, amount_to_pay
        
        except CryptoPayError as e:
            logger.error(f"Failed to create invoice for user {user_id}: {e}")
            raise
    
    async def check_payment_status(self, invoice_id: int) -> Optional[Invoice]:
        """
        Проверка статуса платежа
        
        Args:
            invoice_id: ID инвойса
        
        Returns:
            Invoice объект или None
        """
        try:
            invoice = await self.api.get_invoice_by_id(invoice_id)
            return invoice
        except CryptoPayError as e:
            logger.error(f"Failed to check invoice {invoice_id}: {e}")
            return None
    
    async def cancel_payment(self, invoice_id: int) -> bool:
        """
        Отмена платежа
        
        Args:
            invoice_id: ID инвойса
        
        Returns:
            True если успешно отменен
        """
        try:
            result = await self.api.delete_invoice(invoice_id)
            logger.info(f"Cancelled invoice {invoice_id}")
            return result
        except CryptoPayError as e:
            logger.error(f"Failed to cancel invoice {invoice_id}: {e}")
            return False
    
    def get_active_invoice(self, user_id: int) -> Optional[Invoice]:
        """Получение активного инвойса пользователя"""
        return self._active_invoices.get(user_id)
    
    def remove_active_invoice(self, user_id: int):
        """Удаление активного инвойса пользователя"""
        if user_id in self._active_invoices:
            del self._active_invoices[user_id]


class CryptomusManager:
    """Менеджер платежей через Cryptomus"""
    
    def __init__(self, cryptomus_api: CryptomusAPI):
        self.api = cryptomus_api
        self._active_payments: Dict[int, PaymentInfo] = {}  # user_id -> PaymentInfo
    
    async def create_payment(
        self,
        user_id: int,
        amount_usd: float,
        description: str,
        order_id: str,
        url_callback: Optional[str] = None
    ) -> Tuple[PaymentInfo, float, float]:
        """
        Создание платежа для пользователя с учетом комиссии платформы 2%
        
        Args:
            user_id: Telegram user ID
            amount_usd: Сумма пополнения (которая должна прийти на баланс)
            description: Описание платежа
            order_id: Уникальный ID заказа
            url_callback: URL для webhook
        
        Returns:
            Tuple: (PaymentInfo объект, сумма на баланс, сумма к оплате)
        """
        try:
            # Рассчитываем сумму с учетом комиссии Cryptomus (2%)
            fee_percent = mirror_bot_config.cryptomus_fee_percent
            amount_to_pay = round(amount_usd / (1 - fee_percent / 100), 2)
            
            payment = await self.api.create_payment(
                amount=str(amount_to_pay),
                currency="USD",
                order_id=order_id,
                url_callback=url_callback,
                lifetime=86400,  # 24 часа на оплату
                # currencies - не передаём, Cryptomus покажет все доступные валюты
                additional_data=f"user_{user_id}_balance_{amount_usd}"
            )
            
            self._active_payments[user_id] = payment
            logger.info(
                f"Created Cryptomus payment {payment.uuid} for user {user_id}: "
                f"balance +${amount_usd}, total payment ${amount_to_pay} (fee {fee_percent}%)"
            )
            
            return payment, amount_usd, amount_to_pay
        
        except CryptomusError as e:
            logger.error(f"Failed to create Cryptomus payment for user {user_id}: {e}")
            raise
    
    async def check_payment_status(self, order_id: str) -> Optional[PaymentInfo]:
        """
        Проверка статуса платежа
        
        Args:
            order_id: ID заказа
        
        Returns:
            PaymentInfo объект или None
        """
        try:
            payment = await self.api.get_payment_info(order_id=order_id)
            return payment
        except CryptomusError as e:
            logger.error(f"Failed to check Cryptomus payment {order_id}: {e}")
            return None
    
    def get_active_payment(self, user_id: int) -> Optional[PaymentInfo]:
        """Получение активного платежа пользователя"""
        return self._active_payments.get(user_id)
    
    def remove_active_payment(self, user_id: int):
        """Удаление активного платежа пользователя"""
        if user_id in self._active_payments:
            del self._active_payments[user_id]


# Глобальные экземпляры (будут инициализированы в main.py)
payment_manager: Optional[PaymentManager] = None
cryptomus_manager: Optional[CryptomusManager] = None


def init_payment_manager(api_token: str, testnet: bool = False):
    """
    Инициализация менеджера платежей CryptoPay
    
    Args:
        api_token: API токен Crypto Pay
        testnet: Использовать тестовую сеть
    """
    global payment_manager
    api = CryptoPayAPI(token=api_token, testnet=testnet)
    payment_manager = PaymentManager(api)
    logger.info(f"CryptoPay manager initialized (testnet={testnet})")


def init_cryptomus_manager(merchant_id: str, payment_key: str, payout_key: Optional[str] = None):
    """
    Инициализация менеджера платежей Cryptomus
    
    Args:
        merchant_id: UUID мерчанта
        payment_key: API ключ для платежей
        payout_key: API ключ для выплат (опционально)
    """
    global cryptomus_manager
    api = CryptomusAPI(merchant_id=merchant_id, payment_key=payment_key, payout_key=payout_key)
    cryptomus_manager = CryptomusManager(api)
    logger.info("Cryptomus manager initialized")


# ============================================
# HELPER FUNCTIONS
# ============================================

def format_payment_message(
    description: str,
    balance_amount: float,
    total_amount: float,
    invoice_id: int,
    fee_percent: float = SystemFees.PAYMENT_FEE_PERCENT,
    texts = None
) -> str:
    """
    Форматирование сообщения о платеже с информацией о комиссии (CryptoPay)
    
    Args:
        description: Описание платежа
        balance_amount: Сумма, которая придет на баланс
        total_amount: Общая сумма к оплате
        invoice_id: ID инвойса
        fee_percent: Процент комиссии
        texts: Объект с текстами для мультиязычности
    
    Returns:
        Отформатированное сообщение
    """
    fee_amount = total_amount - balance_amount
    
    if texts:
        return texts.CRYPTOPAY_PAYMENT_FORMAT.format(
            description=description,
            balance_amount=balance_amount,
            fee_amount=fee_amount,
            fee_percent=fee_percent,
            total_amount=total_amount,
            invoice_id=invoice_id
        )
    
    # Fallback to English if texts not provided
    text = f"""🪙 **{description}**
**Payment via CryptoBot**

**Amount to balance:** ${balance_amount:.2f} USD
**Platform fee ({fee_percent}%):** +${fee_amount:.2f} USD
━━━━━━━━━━━━━━━━━━━━━━
**Total to pay:** ${total_amount:.2f} USD

ℹ️ *Payment processing fee: {fee_percent}%*

📌 **Accepted cryptocurrencies:**
   • USDT (TRC20/ERC20)
   • TON
   • BTC
   • ETH
   • USDC

⏱ Invoice expires in 24 hours
🆔 Invoice ID: `{invoice_id}`
"""
    
    return text


def format_cryptomus_payment_message(
    description: str,
    balance_amount: float,
    total_amount: float,
    order_id: str,
    uuid: str,
    fee_percent: float = SystemFees.CRYPTOMUS_FEE_PERCENT,
    texts = None
) -> str:
    """
    Форматирование сообщения о платеже через Cryptomus
    
    Args:
        description: Описание платежа
        balance_amount: Сумма, которая придет на баланс
        total_amount: Общая сумма к оплате
        order_id: ID заказа
        uuid: UUID платежа
        fee_percent: Процент комиссии
        texts: Объект с текстами для мультиязычности
    
    Returns:
        Отформатированное сообщение
    """
    fee_amount = total_amount - balance_amount
    
    if texts:
        return texts.CRYPTOMUS_PAYMENT_FORMAT.format(
            description=description,
            balance_amount=balance_amount,
            fee_amount=fee_amount,
            fee_percent=fee_percent,
            total_amount=total_amount,
            order_id=order_id,
            uuid=uuid
        )
    
    # Fallback to English if texts not provided
    text = f"""💎 **{description}**
**Payment via Cryptomus**

**Amount to balance:** ${balance_amount:.2f} USD
**Platform fee ({fee_percent}%):** +${fee_amount:.2f} USD
━━━━━━━━━━━━━━━━━━━━━━
**Total to pay:** ${total_amount:.2f} USD

ℹ️ *Payment processing fee: {fee_percent}%*

📌 **Accepted cryptocurrencies:**
   • USDT (TRC20/ERC20/BEP20)
   • BTC, ETH, TON
   • LTC, TRX, USDC
   • And more...

⏱ Invoice expires in 24 hours
🆔 Order ID: `{order_id}`
🔖 Payment UUID: `{uuid}`
"""
    
    return text


async def create_payment_with_info(
    user_id: int,
    amount_usd: float,
    description: str,
    payload: Optional[str] = None,
    texts = None
) -> Tuple[str, str, int]:
    """
    Создание платежа через CryptoPay с форматированной информацией
    
    Args:
        user_id: Telegram user ID
        amount_usd: Сумма пополнения на баланс
        description: Описание
        payload: Дополнительные данные
        texts: Объект с текстами для мультиязычности
    
    Returns:
        Tuple: (formatted_text, payment_url, invoice_id)
    """
    if not payment_manager:
        raise Exception("Payment manager not initialized")
    
    invoice, balance_amount, total_amount = await payment_manager.create_payment(
        user_id=user_id,
        amount_usd=amount_usd,
        description=description,
        payload=payload
    )
    
    text = format_payment_message(
        description=description,
        balance_amount=balance_amount,
        total_amount=total_amount,
        invoice_id=invoice.invoice_id,
        fee_percent=mirror_bot_config.payment_fee_percent,
        texts=texts
    )
    
    return text, invoice.bot_invoice_url, invoice.invoice_id


async def create_cryptomus_payment_with_info(
    user_id: int,
    amount_usd: float,
    description: str,
    order_id: Optional[str] = None,
    url_callback: Optional[str] = None,
    texts = None
) -> Tuple[str, str, str, str]:
    """
    Создание платежа через Cryptomus с форматированной информацией
    
    Args:
        user_id: Telegram user ID
        amount_usd: Сумма пополнения на баланс
        description: Описание
        order_id: Уникальный ID заказа (если не указан, генерируется автоматически)
        url_callback: URL для webhook
        texts: Объект с текстами для мультиязычности
    
    Returns:
        Tuple: (formatted_text, payment_url, order_id, uuid)
    """
    if not cryptomus_manager:
        raise Exception("Cryptomus manager not initialized")
    
    import uuid as uuid_lib
    if not order_id:
        order_id = f"topup_{user_id}_{uuid_lib.uuid4().hex[:8]}"
    
    payment, balance_amount, total_amount = await cryptomus_manager.create_payment(
        user_id=user_id,
        amount_usd=amount_usd,
        description=description,
        order_id=order_id,
        url_callback=url_callback
    )
    
    text = format_cryptomus_payment_message(
        description=description,
        balance_amount=balance_amount,
        total_amount=total_amount,
        order_id=order_id,
        uuid=payment.uuid,
        fee_percent=mirror_bot_config.cryptomus_fee_percent,
        texts=texts
    )
    
    return text, payment.url, order_id, payment.uuid


# ============================================
# HANDLERS
# ============================================

@router.message(Command("pay"))
async def cmd_pay_test(message: Message, texts, buttons):
    """Тестовый платеж"""
    if not payment_manager:
        await message.answer(texts.PAYMENT_SYSTEM_NOT_CONFIGURED)
        return
    
    try:
        # Создаем тестовый платеж на $100 (на баланс придет ровно $100)
        text, payment_url, invoice_id = await create_payment_with_info(
            user_id=message.from_user.id,
            amount_usd=100.0,
            description="Test Payment",
            texts=texts
        )
        
        keyboard = get_payment_keyboard(payment_url, invoice_id)
        await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")
    
    except Exception as e:
        logger.error(f"Payment error: {e}")
        await message.answer(texts.PAYMENT_ERROR_CREATING.format(error=str(e)))


@router.callback_query(F.data.startswith("check_payment:"))
async def check_payment_callback(callback: CallbackQuery, texts, buttons):
    """Проверка статуса платежа"""
    if not payment_manager:
        await callback.answer(texts.PAYMENT_SYSTEM_NOT_CONFIGURED_ALERT, show_alert=True)
        return
    
    try:
        invoice_id = int(callback.data.split(":")[1])
        
        invoice = await payment_manager.check_payment_status(invoice_id)
        
        if not invoice:
            await callback.answer(texts.PAYMENT_INVOICE_NOT_FOUND, show_alert=True)
            return
        
        if invoice.status.value == "paid":
            await callback.answer(texts.PAYMENT_CONFIRMED, show_alert=True)
            
            # Обновляем сообщение
            text = texts.PAYMENT_CONFIRMED_TEXT.format(
                amount=invoice.paid_amount,
                asset=invoice.paid_asset.value,
                invoice_id=invoice.invoice_id,
                paid_at=invoice.paid_at
            )
            
            await safe_edit_message(callback, text, parse_mode="Markdown")
            
            # Убираем из активных
            payment_manager.remove_active_invoice(callback.from_user.id)
        
        elif invoice.status.value == "expired":
            await callback.answer(texts.PAYMENT_EXPIRED, show_alert=True)
            payment_manager.remove_active_invoice(callback.from_user.id)
        
        else:
            await callback.answer(texts.PAYMENT_WAITING, show_alert=False)
    
    except Exception as e:
        logger.error(f"Check payment error: {e}")
        await callback.answer(texts.PAYMENT_CHECK_ERROR, show_alert=True)


@router.message(Command("payment_stats"))
async def cmd_payment_stats(message: Message):
    """Статистика мониторинга платежей (админ команда)"""
    from mirror_bot.services.payment_monitor import payment_monitor
    
    active_count = payment_monitor.get_active_payments_count()
    
    if active_count == 0:
        await message.answer(
            "📊 <b>Payment Monitor Status</b>\n\n"
            "✅ Monitor is running\n"
            "📭 No active payments being monitored\n"
            "⏱️ Check interval: 10 seconds",
            parse_mode="HTML"
        )
    else:
        text = (
            "📊 <b>Payment Monitor Status</b>\n\n"
            f"✅ Monitor is running\n"
            f"💳 Active payments: <b>{active_count}</b>\n"
            f"⏱️ Check interval: 10 seconds\n\n"
            "<b>Active payments:</b>\n"
        )
        
        for payment in payment_monitor.active_payments.values():
            time_left = (payment.expires_at - datetime.now(timezone.utc)).total_seconds() / 60
            text += (
                f"• User {payment.user_id}: ${payment.amount} "
                f"({payment.payment_method}) - {time_left:.1f}m left\n"
            )
        
        await message.answer(text, parse_mode="HTML")


@router.callback_query(F.data.startswith("cancel_payment:"))
async def cancel_payment_callback(callback: CallbackQuery, texts, buttons):
    """Отмена платежа"""
    if not payment_manager:
        await callback.answer(texts.PAYMENT_SYSTEM_NOT_CONFIGURED_ALERT, show_alert=True)
        return
    
    try:
        invoice_id = int(callback.data.split(":")[1])
        
        success = await payment_manager.cancel_payment(invoice_id)
        
        if success:
            await callback.answer(texts.PAYMENT_CANCELLED_SUCCESS, show_alert=True)
            await safe_edit_message(callback, texts.PAYMENT_CANCELLED_TEXT, parse_mode="Markdown")
            payment_manager.remove_active_invoice(callback.from_user.id)
        else:
            await callback.answer(texts.PAYMENT_CANCEL_FAILED, show_alert=True)
    
    except Exception as e:
        logger.error(f"Cancel payment error: {e}")
        await callback.answer(texts.PAYMENT_CANCEL_ERROR, show_alert=True)


# ============================================
# WEBHOOK HANDLER
# ============================================

async def handle_webhook_update(
    body: str,
    signature: str,
    api_token: str
) -> Dict[str, Any]:
    """
    Обработка webhook обновления от Crypto Pay
    
    Args:
        body: JSON строка тела запроса
        signature: Значение заголовка crypto-pay-api-signature
        api_token: API токен для проверки подписи
    
    Returns:
        Dict с результатом обработки
    """
    import json
    from mirror_bot.services.crypto_pay_models import WebhookUpdate
    
    # Проверяем подпись
    if not CryptoPayAPI.verify_webhook_signature(api_token, body, signature):
        logger.warning("Invalid webhook signature!")
        return {"ok": False, "error": "Invalid signature"}

    try:
        # Парсим данные
        data = json.loads(body)
        update = WebhookUpdate(**data)
        invoice_id = update.payload.invoice_id if update.payload else None

        logger.info(f"Webhook update: {update.update_type}, invoice_id={invoice_id}")

        # Idempotency check — защита от дублирующих webhook-ов CryptoPay
        if invoice_id:
            try:
                from shared.config.settings import global_settings
                from redis.asyncio import from_url as redis_from_url

                redis_client = await redis_from_url(
                    global_settings.redis_url,
                    encoding="utf-8",
                    decode_responses=True
                )
                lock_key = f"webhook:cryptopay:{invoice_id}"

                # SETNX: если ключ уже существует — это дубликат
                is_new = await redis_client.set(lock_key, "1", nx=True, ex=3600)
                if not is_new:
                    logger.warning(f"Duplicate webhook detected for invoice {invoice_id}, skipping processing")
                    return {"ok": True, "status": "duplicate_skipped", "invoice_id": invoice_id}

                # Ключ установлен, продолжаем обработку
                # Redis клиент остаётся открытым для возможной очистки при ошибке
            except Exception as redis_err:
                logger.warning(f"Redis idempotency check failed: {redis_err}, proceeding without lock")
                redis_client = None

        if update.update_type == "invoice_paid":
            invoice = update.payload
            
            # Здесь можно добавить логику обработки успешного платежа
            # Например, сохранение в базу данных, отправка уведомления и т.д.
            
            logger.info(
                f"Invoice {invoice.invoice_id} paid: "
                f"{invoice.paid_amount} {invoice.paid_asset.value} "
                f"(payload: {invoice.payload})"
            )
            
            # Обрабатываем платеж
            # Payload содержит user_id и amount в формате "user_id:amount"
            try:
                from shared.database.session import async_session_maker
                from mirror_bot.services.user_service import UserService
                from decimal import Decimal
                
                if invoice.payload:
                    parts = invoice.payload.split(":")
                    if len(parts) == 2:
                        user_id = int(parts[0])
                        amount = Decimal(str(invoice.paid_amount))
                        
                        # Пополняем баланс (с учётом маркетолога)
                        async with async_session_maker() as session:
                            from sqlalchemy import select
                            from shared.database.models import User
                            u = await session.execute(select(User).where(User.user_id == user_id))
                            user = u.scalar_one_or_none()
                            mid = user.mirror_bot_id if user else 0
                            new_balance = await UserService.add_balance_with_marketer(
                                session=session,
                                user_id=user_id,
                                amount=amount,
                                mirror_bot_id=mid,
                                description=f"CryptoPay top-up (Invoice {invoice.invoice_id})"
                            )

                            if new_balance is not None:
                                logger.info(f"Balance updated for user {user_id}: +${amount}, new balance: ${new_balance}")
                            else:
                                logger.error(f"Failed to update balance for user {user_id}: User not found in database")
                
            except Exception as e:
                logger.error(f"Error processing payment: {e}")
            
            return {
                "ok": True,
                "invoice_id": invoice.invoice_id,
                "status": "processed"
            }
        
        return {"ok": True, "status": "ignored"}
    
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        return {"ok": False, "error": str(e)}

