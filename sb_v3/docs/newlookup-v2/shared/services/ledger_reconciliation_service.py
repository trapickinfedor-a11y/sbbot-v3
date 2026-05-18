from __future__ import annotations

import logging
from dataclasses import dataclass
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
    TRANSACTION_STATUS_FAILED,
    TRANSACTION_STATUS_ON_HOLD,
    TRANSACTION_STATUS_PENDING,
    Transaction,
    User,
    Worker,
)
from shared.services.ledger_service import money
from shared.services.nocodb_service import NocoDBService
from shared.services.seller_finance_service import SellerFinanceService

logger = logging.getLogger(__name__)

BALANCE_AFFECTING_STATUSES = {
    TRANSACTION_STATUS_COMPLETED,
    TRANSACTION_STATUS_PENDING,
    TRANSACTION_STATUS_ON_HOLD,
    TRANSACTION_STATUS_DISPUTED,
}
SELLER_PENDING_STATUSES = {TRANSACTION_STATUS_ON_HOLD, TRANSACTION_STATUS_DISPUTED}
SELLER_WITHDRAWABLE_STATUSES = {TRANSACTION_STATUS_COMPLETED, TRANSACTION_STATUS_PENDING}


@dataclass
class ReconciliationIssue:
    account_type: str
    account_id: int
    field: str
    expected: Decimal
    actual: Decimal

    def as_payload(self) -> dict:
        return {
            "account_type": self.account_type,
            "account_id": self.account_id,
            "field": self.field,
            "expected": float(self.expected),
            "actual": float(self.actual),
        }


class LedgerReconciliationService:
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
        query = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.account_type == account_type,
            Transaction.account_id == account_id,
            Transaction.status.in_(tuple(statuses)),
        )
        if positive_only:
            query = query.where(Transaction.amount > 0)
        if negative_only:
            query = query.where(Transaction.amount < 0)
        result = await session.scalar(query)
        return money(result)

    @staticmethod
    def _add_issue(
        issues: list[ReconciliationIssue],
        *,
        account_type: str,
        account_id: int,
        field: str,
        expected: Decimal,
        actual: Decimal,
    ) -> None:
        expected = money(expected)
        actual = money(actual)
        if expected == actual:
            return
        issues.append(
            ReconciliationIssue(
                account_type=account_type,
                account_id=account_id,
                field=field,
                expected=expected,
                actual=actual,
            )
        )

    @staticmethod
    async def reconcile_users(session: AsyncSession) -> list[ReconciliationIssue]:
        issues: list[ReconciliationIssue] = []
        users = list((await session.execute(select(User))).scalars().all())
        for user in users:
            expected_balance = await LedgerReconciliationService._sum_transactions(
                session,
                account_type=LEDGER_ACCOUNT_USER,
                account_id=user.user_id,
                statuses=BALANCE_AFFECTING_STATUSES,
            )
            LedgerReconciliationService._add_issue(
                issues,
                account_type=LEDGER_ACCOUNT_USER,
                account_id=user.user_id,
                field="balance",
                expected=expected_balance,
                actual=money(user.balance),
            )
        return issues

    @staticmethod
    async def reconcile_sellers(session: AsyncSession) -> list[ReconciliationIssue]:
        issues: list[ReconciliationIssue] = []
        sellers = list((await session.execute(select(Seller))).scalars().all())
        for seller in sellers:
            expected_pending = await LedgerReconciliationService._sum_transactions(
                session,
                account_type=LEDGER_ACCOUNT_SELLER,
                account_id=seller.id,
                statuses=SELLER_PENDING_STATUSES,
            )
            expected_withdrawable = await LedgerReconciliationService._sum_transactions(
                session,
                account_type=LEDGER_ACCOUNT_SELLER,
                account_id=seller.id,
                statuses=SELLER_WITHDRAWABLE_STATUSES,
            )
            expected_total_earned = await LedgerReconciliationService._sum_transactions(
                session,
                account_type=LEDGER_ACCOUNT_SELLER,
                account_id=seller.id,
                statuses={TRANSACTION_STATUS_COMPLETED},
                positive_only=True,
            )
            LedgerReconciliationService._add_issue(
                issues,
                account_type=LEDGER_ACCOUNT_SELLER,
                account_id=seller.id,
                field="pending_balance",
                expected=expected_pending,
                actual=SellerFinanceService.pending_balance(seller),
            )
            LedgerReconciliationService._add_issue(
                issues,
                account_type=LEDGER_ACCOUNT_SELLER,
                account_id=seller.id,
                field="withdrawable_balance",
                expected=expected_withdrawable,
                actual=SellerFinanceService.withdrawable_balance(seller),
            )
            LedgerReconciliationService._add_issue(
                issues,
                account_type=LEDGER_ACCOUNT_SELLER,
                account_id=seller.id,
                field="total_earned",
                expected=expected_total_earned,
                actual=money(seller.total_earned),
            )
        return issues

    @staticmethod
    async def reconcile_workers(session: AsyncSession) -> list[ReconciliationIssue]:
        issues: list[ReconciliationIssue] = []
        workers = list((await session.execute(select(Worker))).scalars().all())
        for worker in workers:
            expected_balance = await LedgerReconciliationService._sum_transactions(
                session,
                account_type=LEDGER_ACCOUNT_WORKER,
                account_id=worker.id,
                statuses=BALANCE_AFFECTING_STATUSES,
            )
            expected_total_earned = await LedgerReconciliationService._sum_transactions(
                session,
                account_type=LEDGER_ACCOUNT_WORKER,
                account_id=worker.id,
                statuses={TRANSACTION_STATUS_COMPLETED},
                positive_only=True,
            )
            expected_total_withdrawn = abs(
                await LedgerReconciliationService._sum_transactions(
                    session,
                    account_type=LEDGER_ACCOUNT_WORKER,
                    account_id=worker.id,
                    statuses={TRANSACTION_STATUS_COMPLETED},
                    negative_only=True,
                )
            )
            LedgerReconciliationService._add_issue(
                issues,
                account_type=LEDGER_ACCOUNT_WORKER,
                account_id=worker.id,
                field="balance",
                expected=expected_balance,
                actual=money(worker.balance),
            )
            LedgerReconciliationService._add_issue(
                issues,
                account_type=LEDGER_ACCOUNT_WORKER,
                account_id=worker.id,
                field="total_earned",
                expected=expected_total_earned,
                actual=money(worker.total_earned),
            )
            LedgerReconciliationService._add_issue(
                issues,
                account_type=LEDGER_ACCOUNT_WORKER,
                account_id=worker.id,
                field="total_withdrawn",
                expected=expected_total_withdrawn,
                actual=money(worker.total_withdrawn),
            )
        return issues

    @staticmethod
    async def reconcile_marketers(session: AsyncSession) -> list[ReconciliationIssue]:
        issues: list[ReconciliationIssue] = []
        marketers = list((await session.execute(select(Marketer))).scalars().all())
        for marketer in marketers:
            expected_balance = await LedgerReconciliationService._sum_transactions(
                session,
                account_type=LEDGER_ACCOUNT_MARKETER,
                account_id=marketer.id,
                statuses=BALANCE_AFFECTING_STATUSES,
            )
            expected_total_earned = await LedgerReconciliationService._sum_transactions(
                session,
                account_type=LEDGER_ACCOUNT_MARKETER,
                account_id=marketer.id,
                statuses={TRANSACTION_STATUS_COMPLETED},
                positive_only=True,
            )
            expected_total_withdrawn = abs(
                await LedgerReconciliationService._sum_transactions(
                    session,
                    account_type=LEDGER_ACCOUNT_MARKETER,
                    account_id=marketer.id,
                    statuses={TRANSACTION_STATUS_COMPLETED},
                    negative_only=True,
                )
            )
            LedgerReconciliationService._add_issue(
                issues,
                account_type=LEDGER_ACCOUNT_MARKETER,
                account_id=marketer.id,
                field="balance",
                expected=expected_balance,
                actual=money(marketer.balance),
            )
            LedgerReconciliationService._add_issue(
                issues,
                account_type=LEDGER_ACCOUNT_MARKETER,
                account_id=marketer.id,
                field="total_earned",
                expected=expected_total_earned,
                actual=money(marketer.total_earned),
            )
            LedgerReconciliationService._add_issue(
                issues,
                account_type=LEDGER_ACCOUNT_MARKETER,
                account_id=marketer.id,
                field="total_withdrawn",
                expected=expected_total_withdrawn,
                actual=money(marketer.total_withdrawn),
            )
        return issues

    @staticmethod
    async def reconcile_owners(session: AsyncSession) -> list[ReconciliationIssue]:
        issues: list[ReconciliationIssue] = []
        owners = list((await session.execute(select(BotOwner))).scalars().all())
        for owner in owners:
            expected_balance = await LedgerReconciliationService._sum_transactions(
                session,
                account_type=LEDGER_ACCOUNT_OWNER,
                account_id=owner.owner_user_id,
                statuses=BALANCE_AFFECTING_STATUSES,
            )
            expected_total_earned = await LedgerReconciliationService._sum_transactions(
                session,
                account_type=LEDGER_ACCOUNT_OWNER,
                account_id=owner.owner_user_id,
                statuses={TRANSACTION_STATUS_COMPLETED},
                positive_only=True,
            )
            expected_total_withdrawn = abs(
                await LedgerReconciliationService._sum_transactions(
                    session,
                    account_type=LEDGER_ACCOUNT_OWNER,
                    account_id=owner.owner_user_id,
                    statuses={TRANSACTION_STATUS_COMPLETED},
                    negative_only=True,
                )
            )
            LedgerReconciliationService._add_issue(
                issues,
                account_type=LEDGER_ACCOUNT_OWNER,
                account_id=owner.owner_user_id,
                field="balance",
                expected=expected_balance,
                actual=money(owner.balance),
            )
            LedgerReconciliationService._add_issue(
                issues,
                account_type=LEDGER_ACCOUNT_OWNER,
                account_id=owner.owner_user_id,
                field="total_earned",
                expected=expected_total_earned,
                actual=money(owner.total_earned),
            )
            LedgerReconciliationService._add_issue(
                issues,
                account_type=LEDGER_ACCOUNT_OWNER,
                account_id=owner.owner_user_id,
                field="total_withdrawn",
                expected=expected_total_withdrawn,
                actual=money(owner.total_withdrawn),
            )
        return issues

    @staticmethod
    async def run_full_reconciliation(
        session: AsyncSession,
        *,
        emit_alerts: bool = True,
    ) -> dict:
        issues: list[ReconciliationIssue] = []
        for part in (
            await LedgerReconciliationService.reconcile_users(session),
            await LedgerReconciliationService.reconcile_sellers(session),
            await LedgerReconciliationService.reconcile_workers(session),
            await LedgerReconciliationService.reconcile_marketers(session),
            await LedgerReconciliationService.reconcile_owners(session),
        ):
            issues.extend(part)

        payload = [issue.as_payload() for issue in issues]
        if issues:
            logger.warning("Ledger reconciliation found %s issues", len(issues))
            if emit_alerts:
                for issue in issues:
                    NocoDBService.log_event(
                        event_type="ledger_reconciliation_mismatch",
                        actor_type="system",
                        actor_id=None,
                        target_type=issue.account_type,
                        target_id=issue.account_id,
                        status="mismatch",
                        payload=issue.as_payload(),
                    )
        else:
            logger.info("Ledger reconciliation passed with no issues")

        return {
            "ok": not issues,
            "issue_count": len(issues),
            "issues": payload,
        }
