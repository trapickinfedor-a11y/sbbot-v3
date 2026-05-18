"""
Сервис для работы с балансом пользователей
"""

from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from shared.database.models import User
from shared.services.ledger_service import LedgerService

logger = logging.getLogger(__name__)


class BalanceService:
    """Сервис для управления балансом пользователей"""
    
    @staticmethod
    async def refund_order(
        session: AsyncSession,
        user_id: int,
        amount: Decimal,
        order_id: int,
        *,
        commit: bool = True,
    ) -> bool:
        """
        Возврат средств пользователю при NF или отмене заказа
        
        Args:
            session: Сессия БД
            user_id: Telegram ID пользователя
            amount: Сумма возврата
            order_id: ID заказа
        
        Returns:
            True если успешно, False если ошибка
        """
        try:
            from sqlalchemy import select

            async def _apply_refund() -> bool:
                tx = await LedgerService.refund_user_transaction(
                    session,
                    user_id=user_id,
                    amount=amount,
                    description=f"Refund for order #{order_id}",
                    related_entity_type="order",
                    related_entity_id=order_id,
                    idempotency_key=LedgerService.build_idempotency_key("refund-order", order_id, user_id),
                )
                if not tx:
                    logger.error(f"User {user_id} not found for refund")
                    return False
                if not commit:
                    await session.flush()
                return True

            if commit:
                async with session.begin():
                    success = await _apply_refund()
            else:
                success = await _apply_refund()

            if not success:
                return False

            logger.info(f"Refunded ${amount} to user {user_id} for order {order_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to refund order {order_id}: {e}")
            await session.rollback()
            return False

