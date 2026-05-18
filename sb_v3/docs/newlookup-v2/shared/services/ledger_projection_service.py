from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import (
    BotOwner,
    LEDGER_ACCOUNT_MARKETER,
    LEDGER_ACCOUNT_OWNER,
    LEDGER_ACCOUNT_SELLER,
    LEDGER_ACCOUNT_USER,
    LEDGER_ACCOUNT_WORKER,
    Marketer,
    Seller,
    TRANSACTION_STATUS_COMPLETED,
    TRANSACTION_STATUS_DISPUTED,
    TRANSACTION_STATUS_ON_HOLD,
    TRANSACTION_STATUS_PENDING,
    Transaction,
    User,
    Worker,
)


def _money(value) -> Decimal:
    if value is None:
        return Decimal("0.00")
    if isinstance(value, Decimal):
        return value.quantize(Decimal("0.01"))
    return Decimal(str(value)).quantize(Decimal("0.01"))


BALANCE_AFFECTING_STATUSES = {
    TRANSACTION_STATUS_COMPLETED,
    TRANSACTION_STATUS_PENDING,
    TRANSACTION_STATUS_ON_HOLD,
    TRANSACTION_STATUS_DISPUTED,
}
SELLER_PENDING_STATUSES = {TRANSACTION_STATUS_ON_HOLD, TRANSACTION_STATUS_DISPUTED}
# Only COMPLETED transactions contribute to the withdrawable balance.
# PENDING transactions must NOT be included — they may still fail, and including
# them causes double-spend: a seller can withdraw funds before they are settled.
SELLER_WITHDRAWABLE_STATUSES = {TRANSACTION_STATUS_COMPLETED}


class LedgerProjectionService:
    @staticmethod
    async def _sum_transactions(
        session: AsyncSession,
        *,
        account_type: str,
        account_id: int,
        statuses: set[str],
        positive_only: bool = False,
        negative_only: bool = False,
    ) -> Decimal:
        stmt = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.account_type == account_type,
            Transaction.account_id == account_id,
            Transaction.status.in_(tuple(statuses)),
        )
        if positive_only:
            stmt = stmt.where(Transaction.amount > 0)
        if negative_only:
            stmt = stmt.where(Transaction.amount < 0)
        return _money(await session.scalar(stmt))

    @staticmethod
    async def get_user_balance(session: AsyncSession, user_id: int) -> Decimal:
        return await LedgerProjectionService._sum_transactions(
            session,
            account_type=LEDGER_ACCOUNT_USER,
            account_id=user_id,
            statuses=BALANCE_AFFECTING_STATUSES,
        )

    @staticmethod
    async def sync_user_projection(session: AsyncSession, user_id: int) -> User | None:
        user = await session.scalar(select(User).where(User.user_id == user_id).with_for_update())
        if not user:
            return None
        user.balance = await LedgerProjectionService.get_user_balance(session, user_id)
        await session.flush()
        return user

    @staticmethod
    async def get_seller_projection(session: AsyncSession, seller_id: int) -> dict[str, Decimal]:
        pending_balance = await LedgerProjectionService._sum_transactions(
            session,
            account_type=LEDGER_ACCOUNT_SELLER,
            account_id=seller_id,
            statuses=SELLER_PENDING_STATUSES,
        )
        withdrawable_balance = await LedgerProjectionService._sum_transactions(
            session,
            account_type=LEDGER_ACCOUNT_SELLER,
            account_id=seller_id,
            statuses=SELLER_WITHDRAWABLE_STATUSES,
        )
        total_earned = await LedgerProjectionService._sum_transactions(
            session,
            account_type=LEDGER_ACCOUNT_SELLER,
            account_id=seller_id,
            statuses={TRANSACTION_STATUS_COMPLETED},
            positive_only=True,
        )
        return {
            "pending_balance": pending_balance,
            "withdrawable_balance": withdrawable_balance,
            "total_earned": total_earned,
        }

    @staticmethod
    async def sync_seller_projection(session: AsyncSession, seller_id: int) -> Seller | None:
        seller = await session.scalar(select(Seller).where(Seller.id == seller_id).with_for_update())
        if not seller:
            return None
        projection = await LedgerProjectionService.get_seller_projection(session, seller_id)
        seller.pending_balance = projection["pending_balance"]
        seller.withdrawable_balance = projection["withdrawable_balance"]
        seller.total_earned = projection["total_earned"]
        await session.flush()
        return seller

    @staticmethod
    async def get_worker_projection(session: AsyncSession, worker_id: int) -> dict[str, Decimal]:
        balance = await LedgerProjectionService._sum_transactions(
            session,
            account_type=LEDGER_ACCOUNT_WORKER,
            account_id=worker_id,
            statuses=BALANCE_AFFECTING_STATUSES,
        )
        total_earned = await LedgerProjectionService._sum_transactions(
            session,
            account_type=LEDGER_ACCOUNT_WORKER,
            account_id=worker_id,
            statuses={TRANSACTION_STATUS_COMPLETED},
            positive_only=True,
        )
        total_withdrawn = abs(
            await LedgerProjectionService._sum_transactions(
                session,
                account_type=LEDGER_ACCOUNT_WORKER,
                account_id=worker_id,
                statuses={TRANSACTION_STATUS_COMPLETED},
                negative_only=True,
            )
        )
        return {
            "balance": balance,
            "total_earned": total_earned,
            "total_withdrawn": total_withdrawn,
        }

    @staticmethod
    async def sync_worker_projection(session: AsyncSession, worker_id: int) -> Worker | None:
        worker = await session.scalar(select(Worker).where(Worker.id == worker_id).with_for_update())
        if not worker:
            return None
        projection = await LedgerProjectionService.get_worker_projection(session, worker_id)
        worker.balance = projection["balance"]
        worker.total_earned = projection["total_earned"]
        worker.total_withdrawn = projection["total_withdrawn"]
        await session.flush()
        return worker

    @staticmethod
    async def get_marketer_projection(session: AsyncSession, marketer_id: int) -> dict[str, Decimal]:
        balance = await LedgerProjectionService._sum_transactions(
            session,
            account_type=LEDGER_ACCOUNT_MARKETER,
            account_id=marketer_id,
            statuses=BALANCE_AFFECTING_STATUSES,
        )
        total_earned = await LedgerProjectionService._sum_transactions(
            session,
            account_type=LEDGER_ACCOUNT_MARKETER,
            account_id=marketer_id,
            statuses={TRANSACTION_STATUS_COMPLETED},
            positive_only=True,
        )
        total_withdrawn = abs(
            await LedgerProjectionService._sum_transactions(
                session,
                account_type=LEDGER_ACCOUNT_MARKETER,
                account_id=marketer_id,
                statuses={TRANSACTION_STATUS_COMPLETED},
                negative_only=True,
            )
        )
        return {
            "balance": balance,
            "total_earned": total_earned,
            "total_withdrawn": total_withdrawn,
        }

    @staticmethod
    async def sync_marketer_projection(session: AsyncSession, marketer_id: int) -> Marketer | None:
        marketer = await session.scalar(select(Marketer).where(Marketer.id == marketer_id).with_for_update())
        if not marketer:
            return None
        projection = await LedgerProjectionService.get_marketer_projection(session, marketer_id)
        marketer.balance = projection["balance"]
        marketer.total_earned = projection["total_earned"]
        marketer.total_withdrawn = projection["total_withdrawn"]
        await session.flush()
        return marketer

    @staticmethod
    async def get_owner_projection(session: AsyncSession, owner_user_id: int) -> dict[str, Decimal]:
        balance = await LedgerProjectionService._sum_transactions(
            session,
            account_type=LEDGER_ACCOUNT_OWNER,
            account_id=owner_user_id,
            statuses=BALANCE_AFFECTING_STATUSES,
        )
        total_earned = await LedgerProjectionService._sum_transactions(
            session,
            account_type=LEDGER_ACCOUNT_OWNER,
            account_id=owner_user_id,
            statuses={TRANSACTION_STATUS_COMPLETED},
            positive_only=True,
        )
        total_withdrawn = abs(
            await LedgerProjectionService._sum_transactions(
                session,
                account_type=LEDGER_ACCOUNT_OWNER,
                account_id=owner_user_id,
                statuses={TRANSACTION_STATUS_COMPLETED},
                negative_only=True,
            )
        )
        return {
            "balance": balance,
            "total_earned": total_earned,
            "total_withdrawn": total_withdrawn,
        }

    @staticmethod
    async def sync_owner_projection(session: AsyncSession, owner_user_id: int) -> BotOwner | None:
        owner = await session.scalar(select(BotOwner).where(BotOwner.owner_user_id == owner_user_id).with_for_update())
        if not owner:
            return None
        projection = await LedgerProjectionService.get_owner_projection(session, owner_user_id)
        owner.balance = projection["balance"]
        owner.total_earned = projection["total_earned"]
        owner.total_withdrawn = projection["total_withdrawn"]
        await session.flush()
        return owner
