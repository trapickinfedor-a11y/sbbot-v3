"""
Сервис фонового мониторинга платежей
Автоматически проверяет статус платежей и зачисляет баланс
"""

import asyncio
import logging
from typing import Dict, Optional
from datetime import datetime, timedelta
from decimal import Decimal
from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.session import async_session_maker
from shared.database.models import User
from mirror_bot.constants.language_loader import get_texts

logger = logging.getLogger(__name__)


class ActivePayment:
    """Информация об активном платеже"""
    
    def __init__(
        self,
        user_id: int,
        invoice_id: str,
        order_id: Optional[str],
        amount: Decimal,
        payment_method: str,
        expires_at: datetime,
        mirror_bot_id: int
    ):
        self.user_id = user_id
        self.invoice_id = invoice_id
        self.order_id = order_id
        self.amount = amount
        self.payment_method = payment_method
        self.expires_at = expires_at
        self.mirror_bot_id = mirror_bot_id
        self.task: Optional[asyncio.Task] = None
        self.is_cancelled = False


class PaymentMonitor:
    """
    Монитор платежей с фоновой проверкой
    
    Автоматически проверяет статус платежей каждые 10 секунд
    и зачисляет баланс при успешной оплате
    """
    
    def __init__(self):
        self.active_payments: Dict[str, ActivePayment] = {}  # invoice_id -> ActivePayment
        
    def start_monitoring(
        self,
        user_id: int,
        invoice_id: str,
        order_id: Optional[str],
        amount: Decimal,
        payment_method: str,
        expires_in_seconds: int,
        mirror_bot_id: int,
        bot: Bot
    ):
        """
        Начать мониторинг платежа
        
        Args:
            user_id: ID пользователя Telegram
            invoice_id: ID инвойса (для CryptoPay int, для Cryptomus UUID)
            order_id: ID заказа (только для Cryptomus)
            amount: Сумма к зачислению на баланс
            payment_method: "cryptopay" или "cryptomus"
            expires_in_seconds: Время жизни платежа в секундах (по умолчанию 3600)
            mirror_bot_id: ID бота в системе
            bot: Экземпляр бота для отправки уведомлений
        """
        # Преобразуем invoice_id в строку для использования как ключ словаря
        invoice_id_str = str(invoice_id)
        
        # Останавливаем старый мониторинг если есть
        if invoice_id_str in self.active_payments:
            self.stop_monitoring(invoice_id_str)
        
        expires_at = datetime.now() + timedelta(seconds=expires_in_seconds)
        
        payment = ActivePayment(
            user_id=user_id,
            invoice_id=invoice_id_str,
            order_id=order_id,
            amount=amount,
            payment_method=payment_method,
            expires_at=expires_at,
            mirror_bot_id=mirror_bot_id
        )
        
        # Проверяем, что есть активный event loop
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            logger.error("No running event loop found! Cannot start payment monitoring.")
            return
        
        # Создаём фоновую задачу
        payment.task = asyncio.create_task(
            self._monitor_payment(payment, bot)
        )
        
        self.active_payments[invoice_id_str] = payment
        
        logger.info(
            f"✅ Started monitoring payment {invoice_id_str} for user {user_id}, "
            f"method: {payment_method}, amount: ${amount}, expires in: {expires_in_seconds}s"
        )
    
    def stop_monitoring(self, invoice_id: str):
        """Остановить мониторинг платежа"""
        # Преобразуем invoice_id в строку для единообразия
        invoice_id_str = str(invoice_id)
        
        if invoice_id_str in self.active_payments:
            payment = self.active_payments[invoice_id_str]
            payment.is_cancelled = True
            
            if payment.task and not payment.task.done():
                payment.task.cancel()
            
            del self.active_payments[invoice_id_str]
            logger.info(f"🛑 Stopped monitoring payment {invoice_id_str}")
    
    async def _monitor_payment(self, payment: ActivePayment, bot: Bot):
        """
        Фоновая задача мониторинга платежа
        Проверяет статус каждые 10 секунд
        """
        check_interval = 10  # секунд между проверками
        checks_count = 0
        
        logger.info(f"🔄 Payment monitoring task started for invoice {payment.invoice_id}")
        
        try:
            while not payment.is_cancelled:
                # Проверяем не истёк ли срок
                if datetime.now() >= payment.expires_at:
                    logger.info(f"⏰ Payment {payment.invoice_id} expired")
                    await self._notify_payment_expired(payment, bot)
                    break
                
                checks_count += 1
                # Логируем каждую 6-ю проверку (раз в минуту) для информативности
                if checks_count % 6 == 0 or checks_count == 1:
                    logger.info(
                        f"🔍 Checking payment {payment.invoice_id} (check #{checks_count}), "
                        f"method: {payment.payment_method}"
                    )
                else:
                    logger.debug(
                        f"Checking payment {payment.invoice_id} (check #{checks_count}), "
                        f"method: {payment.payment_method}"
                    )
                
                # Проверяем статус
                status = await self._check_payment_status(payment)

                # Cryptomus возвращает "paid" или "paid_over" для успешных платежей
                if status in ["paid", "paid_over"]:
                    logger.info(f"✅ Payment {payment.invoice_id} is PAID (status: {status})! Processing...")
                    await self._process_successful_payment(payment, bot)
                    break
                # Cryptomus возвращает "cancel", "fail", "system_fail" для неуспешных
                elif status in ["cancel", "cancelled", "fail", "system_fail"]:
                    logger.info(f"❌ Payment {payment.invoice_id} status: {status}")
                    # Отправляем уведомление об истечении/отмене
                    await self._notify_payment_expired(payment, bot)
                    break
                elif status is None:
                    logger.warning(f"⚠️ Failed to get status for payment {payment.invoice_id}, retrying...")
                
                # Ждём перед следующей проверкой
                await asyncio.sleep(check_interval)
                
        except asyncio.CancelledError:
            logger.info(f"🛑 Monitoring cancelled for payment {payment.invoice_id}")
        except Exception as e:
            logger.error(f"❌ Error monitoring payment {payment.invoice_id}: {e}", exc_info=True)
        finally:
            # Убираем из активных
            if payment.invoice_id in self.active_payments:
                del self.active_payments[payment.invoice_id]
                logger.info(f"🗑️ Removed payment {payment.invoice_id} from active payments")
    
    async def _check_payment_status(self, payment: ActivePayment) -> Optional[str]:
        """Проверить статус платежа"""
        try:
            from mirror_bot.services.payment_service import PaymentService

            if payment.payment_method == "cryptomus":
                status = await PaymentService.check_payment_status(
                    payment.invoice_id,
                    method="cryptomus",
                    order_id=payment.order_id
                )

                # Детальное логирование для отладки
                logger.info(
                    f"💬 Cryptomus payment {payment.invoice_id} status check: "
                    f"status='{status}', order_id={payment.order_id}"
                )
            else:
                status = await PaymentService.check_payment_status(
                    payment.invoice_id,
                    method="cryptopay"
                )

            return status

        except Exception as e:
            logger.error(f"Failed to check payment status {payment.invoice_id}: {e}")
            return None
    
    async def _process_successful_payment(self, payment: ActivePayment, bot: Bot):
        """Обработать успешный платёж - зачислить баланс и уведомить"""
        try:
            from shared.database.session import async_session_maker
            from mirror_bot.services.user_service import UserService
            
            # Зачисляем баланс (с учётом маркетолога)
            async with async_session_maker() as session:
                new_balance = await UserService.add_balance_with_marketer(
                    session=session,
                    user_id=payment.user_id,
                    amount=payment.amount,
                    mirror_bot_id=payment.mirror_bot_id,
                    description=f"Auto top-up via {payment.payment_method} (Invoice: {payment.invoice_id})"
                )
                
                if new_balance is not None:
                    logger.info(
                        f"✅ Balance credited! User {payment.user_id}: "
                        f"+${payment.amount}, new balance: ${new_balance}"
                    )

                    # Получаем язык пользователя и отправляем уведомление
                    user_language = await self._get_user_language(session, payment.user_id, payment.mirror_bot_id)
                    await self._notify_payment_success(payment, new_balance, bot, user_language)
                    
                    # Уведомляем админов
                    try:
                        from shared.services.admin_notification_service import AdminNotificationService
                        await AdminNotificationService.notify_payment_success(
                            user_id=payment.user_id,
                            amount=float(payment.amount),
                            new_balance=float(new_balance),
                            payment_method=payment.payment_method,
                            invoice_id=payment.invoice_id
                        )
                    except Exception as e:
                        logger.warning(f"Failed to send admin payment notification: {e}")
                else:
                    logger.error(
                        f"❌ Failed to credit balance for user {payment.user_id}! "
                        f"User not found in database. Payment: {payment.invoice_id}, "
                        f"Amount: ${payment.amount}, Method: {payment.payment_method}"
                    )
                    
        except Exception as e:
            logger.error(f"Error processing successful payment {payment.invoice_id}: {e}", exc_info=True)
    
    async def _get_user_language(self, session: AsyncSession, user_id: int, mirror_bot_id: int) -> str:
        """Получить язык пользователя из базы данных"""
        try:
            stmt = select(User).where(
                User.user_id == user_id,
                User.mirror_bot_id == mirror_bot_id
            )
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            
            if user and user.language:
                return user.language
            return "en"  # По умолчанию английский
        except Exception as e:
            logger.error(f"Error getting user language: {e}")
            return "en"
    
    async def _notify_payment_success(self, payment: ActivePayment, new_balance: Decimal, bot: Bot, language: str = "en"):
        """Отправить уведомление об успешной оплате"""
        try:
            texts = get_texts(language)
            
            message = (
                texts.PAYMENT_AUTO_SUCCESS_TITLE +
                texts.PAYMENT_AUTO_SUCCESS_AMOUNT.replace("{amount}", str(payment.amount)) +
                texts.PAYMENT_AUTO_SUCCESS_BALANCE.replace("{balance}", str(new_balance)) +
                texts.PAYMENT_AUTO_SUCCESS_THANKS
            )
            
            await bot.send_message(
                chat_id=payment.user_id,
                text=message,
                parse_mode="HTML"
            )
            
            logger.info(f"Sent payment success notification to user {payment.user_id} (lang: {language})")
            
        except Exception as e:
            logger.error(f"Failed to send notification to user {payment.user_id}: {e}")
    
    async def _notify_payment_expired(self, payment: ActivePayment, bot: Bot):
        """Отправить уведомление об истечении времени оплаты"""
        try:
            # Получаем язык пользователя
            async with async_session_maker() as session:
                user_language = await self._get_user_language(session, payment.user_id, payment.mirror_bot_id)
            
            texts = get_texts(user_language)
            
            message = (
                texts.PAYMENT_AUTO_EXPIRED_TITLE +
                texts.PAYMENT_AUTO_EXPIRED_AMOUNT.replace("{amount}", str(payment.amount)) +
                texts.PAYMENT_AUTO_EXPIRED_CREATE_NEW
            )
            
            await bot.send_message(
                chat_id=payment.user_id,
                text=message,
                parse_mode="HTML"
            )
            
            logger.info(f"Sent payment expired notification to user {payment.user_id} (lang: {user_language})")
            
            # Уведомляем админов
            try:
                from shared.services.admin_notification_service import AdminNotificationService
                await AdminNotificationService.notify_payment_expired(
                    user_id=payment.user_id,
                    amount=float(payment.amount),
                    payment_method=payment.payment_method,
                    invoice_id=payment.invoice_id
                )
            except Exception as e:
                logger.warning(f"Failed to send admin payment expired notification: {e}")
            
        except Exception as e:
            logger.error(f"Failed to send expiration notification to user {payment.user_id}: {e}")
    
    def get_active_payments_count(self) -> int:
        """Получить количество активных платежей"""
        return len(self.active_payments)
    
    def get_user_active_payment(self, user_id: int) -> Optional[ActivePayment]:
        """Получить активный платёж пользователя"""
        for payment in self.active_payments.values():
            if payment.user_id == user_id:
                return payment
        return None


# Глобальный экземпляр монитора
payment_monitor = PaymentMonitor()

