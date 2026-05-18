from decimal import Decimal
from typing import Optional, Literal
import logging

logger = logging.getLogger(__name__)

PaymentMethod = Literal["cryptopay", "cryptomus"]


class PaymentService:
    """
    Сервис для работы с платежами через payment_manager и cryptomus_manager.
    Этот класс является оберткой для использования в хэндлерах.
    Поддерживает два метода оплаты: CryptoPay (CryptoBot) и Cryptomus.
    """
    
    @staticmethod
    async def create_invoice(
        amount: Decimal,
        user_id: int,
        method: PaymentMethod = "cryptopay"
    ) -> dict:
        """
        Создание инвойса через выбранный метод оплаты
        
        Args:
            amount: Сумма пополнения (придет на баланс)
            user_id: ID пользователя Telegram
            method: Метод оплаты ("cryptopay" или "cryptomus")
        
        Returns:
            dict с invoice_id, payment_url, status и другими данными
        """
        if method == "cryptopay":
            return await PaymentService.create_cryptobot_invoice(amount, user_id)
        elif method == "cryptomus":
            return await PaymentService.create_cryptomus_invoice(amount, user_id)
        else:
            raise ValueError(f"Unknown payment method: {method}")
    
    @staticmethod
    async def create_cryptobot_invoice(amount: Decimal, user_id: int) -> dict:
        """
        Создание инвойса через CryptoPay API
        
        Args:
            amount: Сумма пополнения (придет на баланс)
            user_id: ID пользователя Telegram
        
        Returns:
            dict с invoice_id, payment_url и status
        """
        from mirror_bot.handlers.payment import payment_manager
        
        if not payment_manager:
            logger.error("Payment manager not initialized!")
            raise Exception("Payment system is not configured. Please contact administrator.")
        
        try:
            # Используем payment_manager для создания инвойса
            invoice, balance_amount, total_amount = await payment_manager.create_payment(
                user_id=user_id,
                amount_usd=float(amount),
                description=f"Balance Top-Up ${amount}",
                payload=f"topup_{user_id}_{amount}"
            )
            
            logger.info(
                f"Invoice created for user {user_id}: "
                f"invoice_id={invoice.invoice_id}, "
                f"balance=${balance_amount}, total=${total_amount}"
            )
            
            return {
                "invoice_id": invoice.invoice_id,
                "payment_url": invoice.bot_invoice_url,
                "status": "pending",
                "mini_app_invoice_url": invoice.mini_app_invoice_url,
                "web_app_invoice_url": invoice.web_app_invoice_url
            }
        
        except Exception as e:
            logger.error(f"Failed to create invoice: {e}")
            raise
    
    @staticmethod
    async def create_cryptomus_invoice(amount: Decimal, user_id: int) -> dict:
        """
        Создание инвойса через Cryptomus API
        
        Args:
            amount: Сумма пополнения (придет на баланс)
            user_id: ID пользователя Telegram
        
        Returns:
            dict с invoice_id, payment_url и status
        """
        from mirror_bot.handlers.payment import cryptomus_manager
        
        if not cryptomus_manager:
            logger.error("Cryptomus manager not initialized!")
            raise Exception("Cryptomus payment system is not configured. Please contact administrator.")
        
        try:
            # Генерируем уникальный order_id
            import uuid
            order_id = f"topup_{user_id}_{uuid.uuid4().hex[:8]}"
            
            # Используем cryptomus_manager для создания платежа
            payment, balance_amount, total_amount = await cryptomus_manager.create_payment(
                user_id=user_id,
                amount_usd=float(amount),
                description=f"Balance Top-Up ${amount}",
                order_id=order_id,
                url_callback=None  # TODO: Добавить webhook URL если нужно
            )
            
            logger.info(
                f"Cryptomus payment created for user {user_id}: "
                f"uuid={payment.uuid}, order_id={order_id}, "
                f"balance=${balance_amount}, total=${total_amount}"
            )
            
            return {
                "invoice_id": payment.uuid,
                "order_id": order_id,
                "payment_url": payment.url,
                "status": "pending",
                "method": "cryptomus"
            }
        
        except Exception as e:
            logger.error(f"Failed to create Cryptomus invoice: {e}")
            raise
    
    @staticmethod
    async def check_payment_status(
        invoice_id: str,
        method: PaymentMethod = "cryptopay",
        order_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Проверка статуса платежа
        
        Args:
            invoice_id: ID инвойса (строка или число)
            method: Метод оплаты ("cryptopay" или "cryptomus")
            order_id: ID заказа (для Cryptomus)
        
        Returns:
            Статус платежа: "paid", "active", "expired" или None
        """
        if method == "cryptopay":
            from mirror_bot.handlers.payment import payment_manager
            
            if not payment_manager:
                logger.error("Payment manager not initialized!")
                return None
            
            try:
                # Преобразуем invoice_id в int если это нужно
                if isinstance(invoice_id, str):
                    invoice_id = int(invoice_id)
                
                invoice = await payment_manager.check_payment_status(invoice_id)
                
                if not invoice:
                    return None
                
                return invoice.status.value
            
            except Exception as e:
                logger.error(f"Failed to check CryptoPay payment status: {e}")
                return None
        
        elif method == "cryptomus":
            from mirror_bot.handlers.payment import cryptomus_manager

            if not cryptomus_manager:
                logger.error("Cryptomus manager not initialized!")
                return None

            try:
                # Для Cryptomus используем order_id
                if not order_id:
                    logger.error("order_id is required for Cryptomus payment check")
                    return None

                payment = await cryptomus_manager.check_payment_status(order_id)

                if not payment:
                    logger.warning(f"Cryptomus payment not found: order_id={order_id}")
                    return None

                # Логируем ВСЕ поля для отладки
                logger.info(
                    f"🔍 Cryptomus payment info for order {order_id}:\n"
                    f"  - uuid: {payment.uuid}\n"
                    f"  - status: '{payment.status}'\n"
                    f"  - payment_status: '{payment.payment_status}'\n"
                    f"  - is_final: {payment.is_final}\n"
                    f"  - amount: {payment.amount}\n"
                    f"  - payer_amount: {payment.payer_amount}\n"
                    f"  - txid: {payment.txid}"
                )

                # Проверяем оба поля статуса
                # payment_status - это основной статус платежа
                # status - это дополнительный статус
                if payment.payment_status:
                    return payment.payment_status.lower()
                elif payment.status:
                    return payment.status.lower()
                else:
                    return None

            except Exception as e:
                logger.error(f"Failed to check Cryptomus payment status: {e}", exc_info=True)
                return None
        
        else:
            logger.error(f"Unknown payment method: {method}")
            return None

