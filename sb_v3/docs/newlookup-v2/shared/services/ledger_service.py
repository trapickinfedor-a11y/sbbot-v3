from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import (
    BotOwner,
    LEDGER_ACCOUNT_MARKETER,
    LEDGER_ACCOUNT_OWNER,
    LEDGER_ACCOUNT_SELLER,
    LEDGER_ACCOUNT_USER,
    LEDGER_ACCOUNT_WORKER,
    LEDGER_CURRENCY_USD,
    Marketer,
    Seller,
    Transaction,
    TRANSACTION_STATUS_COMPLETED,
    TRANSACTION_STATUS_DISPUTED,
    TRANSACTION_STATUS_FAILED,
    TRANSACTION_STATUS_ON_HOLD,
    TRANSACTION_STATUS_PENDING,
    User,
    Worker,
)
from shared.services.ledger_projection_service import LedgerProjectionService


def money(value: Decimal | str | float | int | None) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value.quantize(Decimal("0.01"))
    return Decimal(str(value)).quantize(Decimal("0.01"))


class LedgerService:
    @staticmethod
    async def _has_account_transactions(session: AsyncSession, *, account_type: str, account_id: int) -> bool:
        return bool(
            await session.scalar(
                select(Transaction.id)
                .where(Transaction.account_type == account_type, Transaction.account_id == account_id)
                .limit(1)
            )
        )

    @staticmethod
    async def _bootstrap_user_if_needed(session: AsyncSession, user: User) -> None:
        if await LedgerService._has_account_transactions(session, account_type=LEDGER_ACCOUNT_USER, account_id=user.user_id):
            return
        opening_balance = money(user.balance)
        if opening_balance == 0:
            return
        await LedgerService.create_entry(
            session,
            account_type=LEDGER_ACCOUNT_USER,
            account_id=user.user_id,
            user_id=user.user_id,
            tx_type="projection_bootstrap",
            amount=opening_balance,
            description=f"Bootstrap user balance for #{user.user_id}",
            idempotency_key=LedgerService.build_idempotency_key("bootstrap", LEDGER_ACCOUNT_USER, user.user_id),
        )

    @staticmethod
    async def _bootstrap_seller_if_needed(session: AsyncSession, seller: Seller) -> None:
        if await LedgerService._has_account_transactions(session, account_type=LEDGER_ACCOUNT_SELLER, account_id=seller.id):
            return
        withdrawable = money(getattr(seller, "withdrawable_balance", 0))
        pending = money(getattr(seller, "pending_balance", 0))
        if withdrawable != 0:
            await LedgerService.create_entry(
                session,
                account_type=LEDGER_ACCOUNT_SELLER,
                account_id=seller.id,
                tx_type="projection_bootstrap",
                amount=withdrawable,
                description=f"Bootstrap seller withdrawable for #{seller.id}",
                idempotency_key=LedgerService.build_idempotency_key("bootstrap", LEDGER_ACCOUNT_SELLER, seller.id, "withdrawable"),
            )
        if pending != 0:
            await LedgerService.create_entry(
                session,
                account_type=LEDGER_ACCOUNT_SELLER,
                account_id=seller.id,
                tx_type="projection_bootstrap",
                amount=pending,
                description=f"Bootstrap seller pending for #{seller.id}",
                status=TRANSACTION_STATUS_ON_HOLD,
                idempotency_key=LedgerService.build_idempotency_key("bootstrap", LEDGER_ACCOUNT_SELLER, seller.id, "pending"),
            )

    @staticmethod
    async def _bootstrap_worker_if_needed(session: AsyncSession, worker: Worker) -> None:
        if await LedgerService._has_account_transactions(session, account_type=LEDGER_ACCOUNT_WORKER, account_id=worker.id):
            return
        opening_balance = money(worker.balance)
        if opening_balance == 0:
            return
        await LedgerService.create_entry(
            session,
            account_type=LEDGER_ACCOUNT_WORKER,
            account_id=worker.id,
            tx_type="projection_bootstrap",
            amount=opening_balance,
            description=f"Bootstrap worker balance for #{worker.id}",
            idempotency_key=LedgerService.build_idempotency_key("bootstrap", LEDGER_ACCOUNT_WORKER, worker.id),
        )

    @staticmethod
    async def _bootstrap_marketer_if_needed(session: AsyncSession, marketer: Marketer) -> None:
        if await LedgerService._has_account_transactions(session, account_type=LEDGER_ACCOUNT_MARKETER, account_id=marketer.id):
            return
        opening_balance = money(marketer.balance)
        if opening_balance == 0:
            return
        await LedgerService.create_entry(
            session,
            account_type=LEDGER_ACCOUNT_MARKETER,
            account_id=marketer.id,
            tx_type="projection_bootstrap",
            amount=opening_balance,
            description=f"Bootstrap marketer balance for #{marketer.id}",
            idempotency_key=LedgerService.build_idempotency_key("bootstrap", LEDGER_ACCOUNT_MARKETER, marketer.id),
        )

    @staticmethod
    async def _bootstrap_owner_if_needed(session: AsyncSession, owner: BotOwner) -> None:
        if await LedgerService._has_account_transactions(session, account_type=LEDGER_ACCOUNT_OWNER, account_id=owner.owner_user_id):
            return
        opening_balance = money(owner.balance)
        if opening_balance == 0:
            return
        await LedgerService.create_entry(
            session,
            account_type=LEDGER_ACCOUNT_OWNER,
            account_id=owner.owner_user_id,
            tx_type="projection_bootstrap",
            amount=opening_balance,
            description=f"Bootstrap owner balance for #{owner.owner_user_id}",
            idempotency_key=LedgerService.build_idempotency_key("bootstrap", LEDGER_ACCOUNT_OWNER, owner.owner_user_id),
        )

    @staticmethod
    async def _sync_projection(session: AsyncSession, *, account_type: str, account_id: int) -> None:
        if account_type == LEDGER_ACCOUNT_USER:
            await LedgerProjectionService.sync_user_projection(session, account_id)
        elif account_type == LEDGER_ACCOUNT_SELLER:
            await LedgerProjectionService.sync_seller_projection(session, account_id)
        elif account_type == LEDGER_ACCOUNT_WORKER:
            await LedgerProjectionService.sync_worker_projection(session, account_id)
        elif account_type == LEDGER_ACCOUNT_MARKETER:
            await LedgerProjectionService.sync_marketer_projection(session, account_id)
        elif account_type == LEDGER_ACCOUNT_OWNER:
            await LedgerProjectionService.sync_owner_projection(session, account_id)

    @staticmethod
    def build_idempotency_key(*parts: object) -> str:
        return ":".join(str(part) for part in parts if part not in (None, ""))

    @staticmethod
    async def get_transaction(
        session: AsyncSession,
        *,
        idempotency_key: Optional[str] = None,
        account_type: Optional[str] = None,
        account_id: Optional[int] = None,
        tx_type: Optional[str] = None,
        related_entity_type: Optional[str] = None,
        related_entity_id: Optional[int] = None,
    ) -> Optional[Transaction]:
        query = select(Transaction)
        if idempotency_key:
            query = query.where(Transaction.idempotency_key == idempotency_key)
        else:
            if account_type is not None:
                query = query.where(Transaction.account_type == account_type)
            if account_id is not None:
                query = query.where(Transaction.account_id == account_id)
            if tx_type is not None:
                query = query.where(Transaction.type == tx_type)
            if related_entity_type is not None:
                query = query.where(Transaction.related_entity_type == related_entity_type)
            if related_entity_id is not None:
                query = query.where(Transaction.related_entity_id == related_entity_id)
        return await session.scalar(query.order_by(Transaction.id.desc()).limit(1))

    @staticmethod
    async def create_entry(
        session: AsyncSession,
        *,
        account_type: str,
        account_id: int,
        tx_type: str,
        amount: Decimal,
        description: str,
        user_id: Optional[int] = None,
        currency: str = LEDGER_CURRENCY_USD,
        status: str = TRANSACTION_STATUS_COMPLETED,
        related_entity_type: Optional[str] = None,
        related_entity_id: Optional[int] = None,
        effective_at: Optional[datetime] = None,
        idempotency_key: Optional[str] = None,
    ) -> Transaction:
        if idempotency_key:
            existing = await session.scalar(
                select(Transaction).where(Transaction.idempotency_key == idempotency_key)
            )
            if existing:
                return existing

        entry = Transaction(
            user_id=user_id,
            account_type=account_type,
            account_id=account_id,
            type=tx_type,
            amount=money(amount),
            currency=currency,
            status=status,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
            effective_at=effective_at,
            idempotency_key=idempotency_key,
            description=description,
        )
        session.add(entry)
        await session.flush()
        return entry

    @staticmethod
    async def _lock_user(session: AsyncSession, user_id: int) -> Optional[User]:
        return await session.scalar(select(User).where(User.user_id == user_id).with_for_update())

    @staticmethod
    async def _lock_seller(session: AsyncSession, seller_id: int) -> Optional[Seller]:
        return await session.scalar(select(Seller).where(Seller.id == seller_id).with_for_update())

    @staticmethod
    async def _lock_worker(session: AsyncSession, worker_id: int) -> Optional[Worker]:
        return await session.scalar(select(Worker).where(Worker.id == worker_id).with_for_update())

    @staticmethod
    async def _lock_marketer(session: AsyncSession, marketer_id: int) -> Optional[Marketer]:
        return await session.scalar(select(Marketer).where(Marketer.id == marketer_id).with_for_update())

    @staticmethod
    async def _lock_owner(session: AsyncSession, owner_user_id: int) -> Optional[BotOwner]:
        return await session.scalar(
            select(BotOwner).where(BotOwner.owner_user_id == owner_user_id).with_for_update()
        )

    @staticmethod
    async def credit_user_balance(
        session: AsyncSession,
        *,
        user_id: int,
        amount: Decimal,
        tx_type: str,
        description: str,
        related_entity_type: Optional[str] = None,
        related_entity_id: Optional[int] = None,
        idempotency_key: Optional[str] = None,
        status: str = TRANSACTION_STATUS_COMPLETED,
        effective_at: Optional[datetime] = None,
    ) -> Optional[Transaction]:
        amount = money(amount)
        existing = await LedgerService.get_transaction(session, idempotency_key=idempotency_key) if idempotency_key else None
        if existing:
            return existing
        user = await LedgerService._lock_user(session, user_id)
        if not user:
            return None
        await LedgerService._bootstrap_user_if_needed(session, user)
        entry = await LedgerService.create_entry(
            session,
            account_type=LEDGER_ACCOUNT_USER,
            account_id=user_id,
            user_id=user_id,
            tx_type=tx_type,
            amount=amount,
            description=description,
            status=status,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
            effective_at=effective_at,
            idempotency_key=idempotency_key,
        )
        await LedgerService._sync_projection(
            session,
            account_type=LEDGER_ACCOUNT_USER,
            account_id=user_id,
        )
        return entry

    @staticmethod
    async def debit_user_balance(
        session: AsyncSession,
        *,
        user_id: int,
        amount: Decimal,
        tx_type: str,
        description: str,
        related_entity_type: Optional[str] = None,
        related_entity_id: Optional[int] = None,
        idempotency_key: Optional[str] = None,
        status: str = TRANSACTION_STATUS_COMPLETED,
        effective_at: Optional[datetime] = None,
    ) -> Optional[Transaction]:
        amount = money(amount)
        existing = await LedgerService.get_transaction(session, idempotency_key=idempotency_key) if idempotency_key else None
        if existing:
            return existing
        user = await LedgerService._lock_user(session, user_id)
        if not user:
            return None
        await LedgerService._bootstrap_user_if_needed(session, user)
        current_balance = await LedgerProjectionService.get_user_balance(session, user_id)
        if current_balance < amount:
            return None
        entry = await LedgerService.create_entry(
            session,
            account_type=LEDGER_ACCOUNT_USER,
            account_id=user_id,
            user_id=user_id,
            tx_type=tx_type,
            amount=-amount,
            description=description,
            status=status,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
            effective_at=effective_at,
            idempotency_key=idempotency_key,
        )
        await LedgerService._sync_projection(
            session,
            account_type=LEDGER_ACCOUNT_USER,
            account_id=user_id,
        )
        return entry

    @staticmethod
    async def refund_user_transaction(
        session: AsyncSession,
        *,
        user_id: int,
        amount: Decimal,
        description: str,
        related_entity_type: Optional[str] = None,
        related_entity_id: Optional[int] = None,
        idempotency_key: Optional[str] = None,
        tx_type: str = "refund",
    ) -> Optional[Transaction]:
        return await LedgerService.credit_user_balance(
            session,
            user_id=user_id,
            amount=amount,
            tx_type=tx_type,
            description=description,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
            idempotency_key=idempotency_key,
        )

    @staticmethod
    async def mark_transaction_completed(
        session: AsyncSession,
        *,
        idempotency_key: Optional[str] = None,
        transaction_id: Optional[int] = None,
    ) -> Optional[Transaction]:
        query = select(Transaction).with_for_update()
        if transaction_id is not None:
            query = query.where(Transaction.id == transaction_id)
        else:
            query = query.where(Transaction.idempotency_key == idempotency_key)
        tx = await session.scalar(query)
        if not tx:
            return None
        tx.status = TRANSACTION_STATUS_COMPLETED
        tx.effective_at = datetime.now(timezone.utc)
        await session.flush()
        await LedgerService._sync_projection(
            session,
            account_type=tx.account_type,
            account_id=tx.account_id,
        )
        return tx

    @staticmethod
    async def mark_transaction_disputed(
        session: AsyncSession,
        *,
        idempotency_key: Optional[str] = None,
        transaction_id: Optional[int] = None,
    ) -> Optional[Transaction]:
        query = select(Transaction).with_for_update()
        if transaction_id is not None:
            query = query.where(Transaction.id == transaction_id)
        else:
            query = query.where(Transaction.idempotency_key == idempotency_key)
        tx = await session.scalar(query)
        if not tx:
            return None
        tx.status = TRANSACTION_STATUS_DISPUTED
        await session.flush()
        await LedgerService._sync_projection(
            session,
            account_type=tx.account_type,
            account_id=tx.account_id,
        )
        return tx

    @staticmethod
    async def mark_transaction_failed(
        session: AsyncSession,
        *,
        idempotency_key: Optional[str] = None,
        transaction_id: Optional[int] = None,
    ) -> Optional[Transaction]:
        query = select(Transaction).with_for_update()
        if transaction_id is not None:
            query = query.where(Transaction.id == transaction_id)
        else:
            query = query.where(Transaction.idempotency_key == idempotency_key)
        tx = await session.scalar(query)
        if not tx:
            return None
        tx.status = TRANSACTION_STATUS_FAILED
        await session.flush()
        await LedgerService._sync_projection(
            session,
            account_type=tx.account_type,
            account_id=tx.account_id,
        )
        return tx

    @staticmethod
    async def create_seller_hold(
        session: AsyncSession,
        *,
        seller_id: int,
        amount: Decimal,
        order_id: int,
        effective_at: Optional[datetime],
        description: str,
    ) -> Optional[Transaction]:
        idempotency_key = LedgerService.build_idempotency_key("seller-hold", order_id)
        existing = await LedgerService.get_transaction(session, idempotency_key=idempotency_key)
        if existing:
            return existing
        seller = await LedgerService._lock_seller(session, seller_id)
        if not seller:
            return None
        await LedgerService._bootstrap_seller_if_needed(session, seller)
        available = (await LedgerProjectionService.get_seller_projection(session, seller_id))["withdrawable_balance"]
        if available < money(amount):
            return None
        entry = await LedgerService.create_entry(
            session,
            account_type=LEDGER_ACCOUNT_SELLER,
            account_id=seller_id,
            tx_type="purchase",
            amount=amount,
            description=description,
            status=TRANSACTION_STATUS_ON_HOLD,
            related_entity_type="seller_order",
            related_entity_id=order_id,
            effective_at=effective_at,
            idempotency_key=idempotency_key,
        )
        await LedgerService._sync_projection(
            session,
            account_type=LEDGER_ACCOUNT_SELLER,
            account_id=seller_id,
        )
        return entry

    @staticmethod
    async def settle_seller_hold(
        session: AsyncSession,
        *,
        seller_id: int,
        order_id: int,
        fallback_amount: Optional[Decimal] = None,
    ) -> Optional[Transaction]:
        tx = await session.scalar(
            select(Transaction)
            .where(Transaction.idempotency_key == LedgerService.build_idempotency_key("seller-hold", order_id))
            .with_for_update()
        )
        if not tx:
            if fallback_amount is None:
                return None
            tx = await LedgerService.create_entry(
                session,
                account_type=LEDGER_ACCOUNT_SELLER,
                account_id=seller_id,
                tx_type="purchase",
                amount=money(fallback_amount),
                description=f"Seller hold settlement for order #{order_id}",
                status=TRANSACTION_STATUS_COMPLETED,
                related_entity_type="seller_order",
                related_entity_id=order_id,
                effective_at=datetime.now(timezone.utc),
                idempotency_key=LedgerService.build_idempotency_key("seller-hold", order_id),
            )
            await LedgerService._sync_projection(
                session,
                account_type=LEDGER_ACCOUNT_SELLER,
                account_id=seller_id,
            )
            return tx
        if tx.status == TRANSACTION_STATUS_COMPLETED:
            return tx
        tx.status = TRANSACTION_STATUS_COMPLETED
        tx.effective_at = datetime.now(timezone.utc)
        await session.flush()
        await LedgerService._sync_projection(
            session,
            account_type=LEDGER_ACCOUNT_SELLER,
            account_id=seller_id,
        )
        return tx

    @staticmethod
    async def dispute_seller_hold(session: AsyncSession, *, order_id: int) -> Optional[Transaction]:
        tx = await session.scalar(
            select(Transaction)
            .where(Transaction.idempotency_key == LedgerService.build_idempotency_key("seller-hold", order_id))
            .with_for_update()
        )
        if not tx:
            return None
        tx.status = TRANSACTION_STATUS_DISPUTED
        await session.flush()
        await LedgerService._sync_projection(
            session,
            account_type=tx.account_type,
            account_id=tx.account_id,
        )
        return tx

    @staticmethod
    async def fail_seller_hold(session: AsyncSession, *, seller_id: int, order_id: int) -> Optional[Transaction]:
        tx = await session.scalar(
            select(Transaction)
            .where(Transaction.idempotency_key == LedgerService.build_idempotency_key("seller-hold", order_id))
            .with_for_update()
        )
        if not tx:
            return None
        if tx.status == TRANSACTION_STATUS_FAILED:
            return tx
        tx.status = TRANSACTION_STATUS_FAILED
        tx.effective_at = datetime.now(timezone.utc)
        await session.flush()
        await LedgerService._sync_projection(
            session,
            account_type=LEDGER_ACCOUNT_SELLER,
            account_id=seller_id,
        )
        return tx

    @staticmethod
    async def credit_worker_balance(
        session: AsyncSession,
        *,
        worker_id: int,
        amount: Decimal,
        description: str,
        related_entity_type: Optional[str] = None,
        related_entity_id: Optional[int] = None,
        idempotency_key: Optional[str] = None,
    ) -> Optional[Transaction]:
        existing = await LedgerService.get_transaction(session, idempotency_key=idempotency_key) if idempotency_key else None
        if existing:
            return existing
        worker = await LedgerService._lock_worker(session, worker_id)
        if not worker:
            return None
        await LedgerService._bootstrap_worker_if_needed(session, worker)
        amount = money(amount)
        entry = await LedgerService.create_entry(
            session,
            account_type=LEDGER_ACCOUNT_WORKER,
            account_id=worker_id,
            tx_type="payout_worker",
            amount=amount,
            description=description,
            status=TRANSACTION_STATUS_COMPLETED,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
            idempotency_key=idempotency_key,
        )
        await LedgerService._sync_projection(
            session,
            account_type=LEDGER_ACCOUNT_WORKER,
            account_id=worker_id,
        )
        return entry

    @staticmethod
    async def credit_marketer_balance(
        session: AsyncSession,
        *,
        marketer_id: int,
        amount: Decimal,
        description: str,
        related_entity_type: Optional[str] = None,
        related_entity_id: Optional[int] = None,
        idempotency_key: Optional[str] = None,
    ) -> Optional[Transaction]:
        existing = await LedgerService.get_transaction(session, idempotency_key=idempotency_key) if idempotency_key else None
        if existing:
            return existing
        marketer = await LedgerService._lock_marketer(session, marketer_id)
        if not marketer:
            return None
        await LedgerService._bootstrap_marketer_if_needed(session, marketer)
        amount = money(amount)
        entry = await LedgerService.create_entry(
            session,
            account_type=LEDGER_ACCOUNT_MARKETER,
            account_id=marketer_id,
            tx_type="commission",
            amount=amount,
            description=description,
            status=TRANSACTION_STATUS_COMPLETED,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
            idempotency_key=idempotency_key,
        )
        await LedgerService._sync_projection(
            session,
            account_type=LEDGER_ACCOUNT_MARKETER,
            account_id=marketer_id,
        )
        return entry

    @staticmethod
    async def credit_owner_balance(
        session: AsyncSession,
        *,
        owner_user_id: int,
        amount: Decimal,
        description: str,
        related_entity_type: Optional[str] = None,
        related_entity_id: Optional[int] = None,
        idempotency_key: Optional[str] = None,
    ) -> Optional[Transaction]:
        existing = await LedgerService.get_transaction(session, idempotency_key=idempotency_key) if idempotency_key else None
        if existing:
            return existing
        owner = await LedgerService._lock_owner(session, owner_user_id)
        if not owner:
            return None
        await LedgerService._bootstrap_owner_if_needed(session, owner)
        amount = money(amount)
        entry = await LedgerService.create_entry(
            session,
            account_type=LEDGER_ACCOUNT_OWNER,
            account_id=owner_user_id,
            tx_type="commission",
            amount=amount,
            description=description,
            status=TRANSACTION_STATUS_COMPLETED,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
            idempotency_key=idempotency_key,
        )
        await LedgerService._sync_projection(
            session,
            account_type=LEDGER_ACCOUNT_OWNER,
            account_id=owner_user_id,
        )
        return entry

    @staticmethod
    async def credit_seller_balance(
        session: AsyncSession,
        *,
        seller_id: int,
        amount: Decimal,
        description: str,
        related_entity_type: Optional[str] = None,
        related_entity_id: Optional[int] = None,
        idempotency_key: Optional[str] = None,
        status: str = TRANSACTION_STATUS_COMPLETED,
        effective_at: Optional[datetime] = None,
        tx_type: str = "sale",
    ) -> Optional[Transaction]:
        existing = await LedgerService.get_transaction(session, idempotency_key=idempotency_key) if idempotency_key else None
        if existing:
            return existing
        seller = await LedgerService._lock_seller(session, seller_id)
        if not seller:
            return None
        await LedgerService._bootstrap_seller_if_needed(session, seller)
        entry = await LedgerService.create_entry(
            session,
            account_type=LEDGER_ACCOUNT_SELLER,
            account_id=seller_id,
            tx_type=tx_type,
            amount=money(amount),
            description=description,
            status=status,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
            effective_at=effective_at,
            idempotency_key=idempotency_key,
        )
        await LedgerService._sync_projection(
            session,
            account_type=LEDGER_ACCOUNT_SELLER,
            account_id=seller_id,
        )
        return entry

    @staticmethod
    async def reserve_seller_withdrawal(
        session: AsyncSession,
        *,
        seller: Seller,
        amount: Decimal,
        withdrawal_id: int,
        related_entity_type: str = "seller_withdrawal",
        key_prefix: str = "seller-withdrawal",
        description: Optional[str] = None,
    ) -> bool:
        reservation_key = LedgerService.build_idempotency_key(key_prefix, withdrawal_id)
        existing = await LedgerService.get_transaction(session, idempotency_key=reservation_key)
        if existing:
            return True
        locked_seller = await LedgerService._lock_seller(session, seller.id)
        if not locked_seller:
            return False
        await LedgerService._bootstrap_seller_if_needed(session, locked_seller)
        available = (await LedgerProjectionService.get_seller_projection(session, seller.id))["withdrawable_balance"]
        if available < money(amount):
            return False
        await LedgerService.create_entry(
            session,
            account_type=LEDGER_ACCOUNT_SELLER,
            account_id=seller.id,
            tx_type="withdrawal",
            amount=-money(amount),
            description=description or f"Seller withdrawal #{withdrawal_id}",
            status=TRANSACTION_STATUS_PENDING,
            related_entity_type=related_entity_type,
            related_entity_id=withdrawal_id,
            idempotency_key=reservation_key,
        )
        await LedgerService._sync_projection(
            session,
            account_type=LEDGER_ACCOUNT_SELLER,
            account_id=seller.id,
        )
        return True

    @staticmethod
    async def release_seller_withdrawal_reservation(
        session: AsyncSession,
        *,
        seller: Seller,
        amount: Decimal,
        withdrawal_id: int,
        key_prefix: str = "seller-withdrawal",
    ) -> None:
        reservation_key = LedgerService.build_idempotency_key(key_prefix, withdrawal_id)
        tx = await session.scalar(select(Transaction).where(Transaction.idempotency_key == reservation_key).with_for_update())
        if not tx or tx.status == TRANSACTION_STATUS_FAILED:
            return
        tx.status = TRANSACTION_STATUS_FAILED
        tx.effective_at = datetime.now(timezone.utc)
        await session.flush()
        await LedgerService._sync_projection(
            session,
            account_type=LEDGER_ACCOUNT_SELLER,
            account_id=seller.id,
        )

    @staticmethod
    async def finalize_seller_withdrawal(
        session: AsyncSession,
        *,
        seller: Seller,
        amount: Decimal,
        withdrawal_id: int,
        key_prefix: str = "seller-withdrawal",
    ) -> None:
        tx = await session.scalar(
            select(Transaction)
            .where(Transaction.idempotency_key == LedgerService.build_idempotency_key(key_prefix, withdrawal_id))
            .with_for_update()
        )
        if not tx:
            return
        if tx.status != TRANSACTION_STATUS_COMPLETED:
            tx.status = TRANSACTION_STATUS_COMPLETED
            tx.effective_at = datetime.now(timezone.utc)
        await session.flush()
        await LedgerService._sync_projection(
            session,
            account_type=LEDGER_ACCOUNT_SELLER,
            account_id=seller.id,
        )

    @staticmethod
    async def reserve_worker_withdrawal(
        session: AsyncSession,
        *,
        worker: Worker,
        amount: Decimal,
        withdrawal_id: int,
        related_entity_type: str = "worker_withdrawal",
        key_prefix: str = "worker-withdrawal",
        description: Optional[str] = None,
    ) -> bool:
        reservation_key = LedgerService.build_idempotency_key(key_prefix, withdrawal_id)
        existing = await LedgerService.get_transaction(session, idempotency_key=reservation_key)
        if existing:
            return True
        amount = money(amount)
        locked_worker = await LedgerService._lock_worker(session, worker.id)
        if not locked_worker:
            return False
        await LedgerService._bootstrap_worker_if_needed(session, locked_worker)
        available = (await LedgerProjectionService.get_worker_projection(session, worker.id))["balance"]
        if available < amount:
            return False
        await LedgerService.create_entry(
            session,
            account_type=LEDGER_ACCOUNT_WORKER,
            account_id=worker.id,
            tx_type="withdrawal",
            amount=-amount,
            description=description or f"Worker withdrawal #{withdrawal_id}",
            status=TRANSACTION_STATUS_PENDING,
            related_entity_type=related_entity_type,
            related_entity_id=withdrawal_id,
            idempotency_key=reservation_key,
        )
        await LedgerService._sync_projection(
            session,
            account_type=LEDGER_ACCOUNT_WORKER,
            account_id=worker.id,
        )
        return True

    @staticmethod
    async def release_worker_withdrawal_reservation(
        session: AsyncSession,
        *,
        worker: Worker,
        amount: Decimal,
        withdrawal_id: int,
        key_prefix: str = "worker-withdrawal",
    ) -> None:
        tx = await session.scalar(
            select(Transaction)
            .where(Transaction.idempotency_key == LedgerService.build_idempotency_key(key_prefix, withdrawal_id))
            .with_for_update()
        )
        if not tx or tx.status == TRANSACTION_STATUS_FAILED:
            return
        tx.status = TRANSACTION_STATUS_FAILED
        tx.effective_at = datetime.now(timezone.utc)
        await session.flush()
        await LedgerService._sync_projection(
            session,
            account_type=LEDGER_ACCOUNT_WORKER,
            account_id=worker.id,
        )

    @staticmethod
    async def finalize_worker_withdrawal(
        session: AsyncSession,
        *,
        worker: Worker,
        amount: Decimal,
        withdrawal_id: int,
        key_prefix: str = "worker-withdrawal",
    ) -> None:
        tx = await session.scalar(
            select(Transaction)
            .where(Transaction.idempotency_key == LedgerService.build_idempotency_key(key_prefix, withdrawal_id))
            .with_for_update()
        )
        if not tx:
            return
        if tx.status != TRANSACTION_STATUS_COMPLETED:
            tx.status = TRANSACTION_STATUS_COMPLETED
            tx.effective_at = datetime.now(timezone.utc)
        await session.flush()
        await LedgerService._sync_projection(
            session,
            account_type=LEDGER_ACCOUNT_WORKER,
            account_id=worker.id,
        )

    @staticmethod
    async def reserve_marketer_withdrawal(
        session: AsyncSession,
        *,
        marketer: Marketer,
        amount: Decimal,
        withdrawal_id: int,
    ) -> bool:
        reservation_key = LedgerService.build_idempotency_key("marketer-withdrawal", withdrawal_id)
        existing = await LedgerService.get_transaction(session, idempotency_key=reservation_key)
        if existing:
            return True
        amount = money(amount)
        locked_marketer = await LedgerService._lock_marketer(session, marketer.id)
        if not locked_marketer:
            return False
        await LedgerService._bootstrap_marketer_if_needed(session, locked_marketer)
        available = (await LedgerProjectionService.get_marketer_projection(session, marketer.id))["balance"]
        if available < amount:
            return False
        await LedgerService.create_entry(
            session,
            account_type=LEDGER_ACCOUNT_MARKETER,
            account_id=marketer.id,
            tx_type="withdrawal",
            amount=-amount,
            description=f"Marketer withdrawal #{withdrawal_id}",
            status=TRANSACTION_STATUS_PENDING,
            related_entity_type="marketer_withdrawal",
            related_entity_id=withdrawal_id,
            idempotency_key=reservation_key,
        )
        await LedgerService._sync_projection(
            session,
            account_type=LEDGER_ACCOUNT_MARKETER,
            account_id=marketer.id,
        )
        return True

    @staticmethod
    async def release_marketer_withdrawal_reservation(
        session: AsyncSession,
        *,
        marketer: Marketer,
        amount: Decimal,
        withdrawal_id: int,
    ) -> None:
        tx = await session.scalar(
            select(Transaction)
            .where(Transaction.idempotency_key == LedgerService.build_idempotency_key("marketer-withdrawal", withdrawal_id))
            .with_for_update()
        )
        if not tx or tx.status == TRANSACTION_STATUS_FAILED:
            return
        tx.status = TRANSACTION_STATUS_FAILED
        tx.effective_at = datetime.now(timezone.utc)
        await session.flush()
        await LedgerService._sync_projection(
            session,
            account_type=LEDGER_ACCOUNT_MARKETER,
            account_id=marketer.id,
        )

    @staticmethod
    async def finalize_marketer_withdrawal(
        session: AsyncSession,
        *,
        marketer: Marketer,
        amount: Decimal,
        withdrawal_id: int,
    ) -> None:
        tx = await session.scalar(
            select(Transaction)
            .where(Transaction.idempotency_key == LedgerService.build_idempotency_key("marketer-withdrawal", withdrawal_id))
            .with_for_update()
        )
        if not tx:
            return
        if tx.status != TRANSACTION_STATUS_COMPLETED:
            tx.status = TRANSACTION_STATUS_COMPLETED
            tx.effective_at = datetime.now(timezone.utc)
        await session.flush()
        await LedgerService._sync_projection(
            session,
            account_type=LEDGER_ACCOUNT_MARKETER,
            account_id=marketer.id,
        )

    @staticmethod
    async def reserve_owner_withdrawal(
        session: AsyncSession,
        *,
        owner: BotOwner,
        amount: Decimal,
        withdrawal_id: int,
    ) -> bool:
        reservation_key = LedgerService.build_idempotency_key("owner-withdrawal", withdrawal_id)
        existing = await LedgerService.get_transaction(session, idempotency_key=reservation_key)
        if existing:
            return True
        amount = money(amount)
        locked_owner = await LedgerService._lock_owner(session, owner.owner_user_id)
        if not locked_owner:
            return False
        await LedgerService._bootstrap_owner_if_needed(session, locked_owner)
        available = (await LedgerProjectionService.get_owner_projection(session, owner.owner_user_id))["balance"]
        if available < amount:
            return False
        await LedgerService.create_entry(
            session,
            account_type=LEDGER_ACCOUNT_OWNER,
            account_id=owner.owner_user_id,
            tx_type="withdrawal",
            amount=-amount,
            description=f"Owner withdrawal #{withdrawal_id}",
            status=TRANSACTION_STATUS_PENDING,
            related_entity_type="owner_withdrawal",
            related_entity_id=withdrawal_id,
            idempotency_key=reservation_key,
        )
        await LedgerService._sync_projection(
            session,
            account_type=LEDGER_ACCOUNT_OWNER,
            account_id=owner.owner_user_id,
        )
        return True

    @staticmethod
    async def release_owner_withdrawal_reservation(
        session: AsyncSession,
        *,
        owner: BotOwner,
        amount: Decimal,
        withdrawal_id: int,
    ) -> None:
        tx = await session.scalar(
            select(Transaction)
            .where(Transaction.idempotency_key == LedgerService.build_idempotency_key("owner-withdrawal", withdrawal_id))
            .with_for_update()
        )
        if not tx or tx.status == TRANSACTION_STATUS_FAILED:
            return
        tx.status = TRANSACTION_STATUS_FAILED
        tx.effective_at = datetime.now(timezone.utc)
        await session.flush()
        await LedgerService._sync_projection(
            session,
            account_type=LEDGER_ACCOUNT_OWNER,
            account_id=owner.owner_user_id,
        )

    @staticmethod
    async def finalize_owner_withdrawal(
        session: AsyncSession,
        *,
        owner: BotOwner,
        amount: Decimal,
        withdrawal_id: int,
    ) -> None:
        tx = await session.scalar(
            select(Transaction)
            .where(Transaction.idempotency_key == LedgerService.build_idempotency_key("owner-withdrawal", withdrawal_id))
            .with_for_update()
        )
        if not tx:
            return
        if tx.status != TRANSACTION_STATUS_COMPLETED:
            tx.status = TRANSACTION_STATUS_COMPLETED
            tx.effective_at = datetime.now(timezone.utc)
        await session.flush()
        await LedgerService._sync_projection(
            session,
            account_type=LEDGER_ACCOUNT_OWNER,
            account_id=owner.owner_user_id,
        )

    @staticmethod
    def compute_hold_effective_at(*, now: Optional[datetime] = None, hours: int = 0) -> datetime:
        return (now or datetime.now(timezone.utc)) + timedelta(hours=max(0, int(hours or 0)))
