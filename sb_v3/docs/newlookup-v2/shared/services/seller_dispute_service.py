from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import Seller, SellerBank, SellerOrder, SellerOrderDispute, SystemSetting
from shared.services.ledger_service import LedgerService
from shared.services.seller_order_delivery_service import get_seller_order_v24_windows, release_seller_order_reservation
from support_bot.services.balance_service import BalanceService


async def _get_setting_int(session: AsyncSession, key: str, default: int) -> int:
    row = await session.scalar(select(SystemSetting).where(SystemSetting.key == key))
    if not row or row.value in (None, ""):
        return default
    try:
        return int(str(row.value).strip())
    except (TypeError, ValueError):
        return default


class SellerDisputeService:
    @staticmethod
    async def get_seller_response_hours(session: AsyncSession) -> int:
        return await _get_setting_int(session, "SELLER_DISPUTE_RESPONSE_HOURS", 24)

    @staticmethod
    async def open_dispute(
        session: AsyncSession,
        *,
        order: SellerOrder,
        opened_by: int,
        reason: str,
        description: Optional[str] = None,
        buyer_evidence: Optional[dict] = None,
    ) -> SellerOrderDispute:
        now = datetime.now(timezone.utc)
        dispute_hours, _ = await get_seller_order_v24_windows(session)
        response_hours = await SellerDisputeService.get_seller_response_hours(session)
        dispute = await session.scalar(
            select(SellerOrderDispute).where(SellerOrderDispute.order_id == order.id)
        )
        if dispute is None:
            dispute = SellerOrderDispute(
                order_id=order.id,
                opened_by=opened_by,
                reason=reason,
                description=description,
            )
            session.add(dispute)
        dispute.status = "open"
        dispute.description = description or dispute.description
        dispute.seller_response_due_at = now + timedelta(hours=response_hours)
        dispute.seller_responded_at = None
        dispute.buyer_evidence = buyer_evidence or dispute.buyer_evidence
        dispute.resolution_note = None
        dispute.resolved_by = None
        dispute.resolved_at = None
        order.status = "disputed"
        order.disputed_at = now
        order.dispute_deadline_at = now + timedelta(hours=dispute_hours)
        await LedgerService.dispute_seller_hold(session, order_id=order.id)
        return dispute

    @staticmethod
    async def mark_seller_responded(
        session: AsyncSession,
        *,
        order_id: int,
        message_text: Optional[str] = None,
        files: Optional[list] = None,
    ) -> None:
        dispute = await session.scalar(
            select(SellerOrderDispute).where(
                SellerOrderDispute.order_id == order_id,
                SellerOrderDispute.status == "open",
            )
        )
        if not dispute:
            return
        dispute.seller_responded_at = datetime.now(timezone.utc)
        evidence = dict(dispute.seller_evidence or {})
        if message_text:
            evidence["last_message_text"] = message_text[:1000]
        if files:
            evidence["files"] = files
        if evidence:
            evidence["updated_at"] = datetime.now(timezone.utc).isoformat()
            dispute.seller_evidence = evidence

    @staticmethod
    async def request_appeal(
        session: AsyncSession,
        *,
        dispute_id: int,
        reason: str,
    ) -> Optional[SellerOrderDispute]:
        dispute = await session.scalar(select(SellerOrderDispute).where(SellerOrderDispute.id == dispute_id))
        if not dispute:
            return None
        if dispute.status not in {"resolved_buyer", "resolved_seller", "cancelled"}:
            raise RuntimeError("Appeal is only available for resolved disputes")
        dispute.appeal_status = "requested"
        dispute.appeal_reason = reason
        dispute.appeal_requested_at = datetime.now(timezone.utc)
        return dispute

    @staticmethod
    async def review_appeal(
        session: AsyncSession,
        *,
        dispute_id: int,
        status: str,
        actor_admin_id: Optional[int] = None,
        note: Optional[str] = None,
    ) -> Optional[SellerOrderDispute]:
        dispute = await session.scalar(select(SellerOrderDispute).where(SellerOrderDispute.id == dispute_id))
        if not dispute:
            return None
        if dispute.appeal_status != "requested":
            raise RuntimeError("Appeal review is only available for requested appeals")
        dispute.appeal_status = status
        dispute.assigned_admin_id = actor_admin_id or dispute.assigned_admin_id
        if note:
            merged = (dispute.resolution_note or "").strip()
            dispute.resolution_note = f"{merged}\nAppeal review: {note}".strip()
        return dispute

    @staticmethod
    async def resolve_for_buyer(
        session: AsyncSession,
        *,
        dispute: SellerOrderDispute,
        order: SellerOrder,
        actor_admin_id: Optional[int] = None,
        resolution_note: Optional[str] = None,
    ) -> None:
        # Re-fetch dispute with row lock to prevent double-resolution race condition.
        locked_dispute = await session.scalar(
            select(SellerOrderDispute)
            .where(SellerOrderDispute.id == dispute.id)
            .with_for_update()
        )
        if not locked_dispute or locked_dispute.status != "open":
            raise RuntimeError(f"Dispute {dispute.id} is already resolved or not found")
        now = datetime.now(timezone.utc)
        seller = await session.scalar(select(Seller).where(Seller.id == order.seller_id))
        order.status = "cancelled"
        order.returned_at = now
        order.admin_notes = resolution_note or f"Dispute resolved in buyer favor: {dispute.reason}"
        order.check_expires_at = None
        order.auto_complete_at = None
        order.dispute_deadline_at = None
        if seller and order.pending_credited_at and not order.settled_at:
            await LedgerService.fail_seller_hold(session, seller_id=seller.id, order_id=order.id)
        await release_seller_order_reservation(session, order)
        refund_success = await BalanceService.refund_order(
            session,
            order.buyer_user_id,
            Decimal(str(order.price_for_buyer)),
            order.id,
            commit=False,
        )
        if not refund_success:
            raise RuntimeError("Refund failed")
        locked_dispute.status = "resolved_buyer"
        locked_dispute.resolution_note = resolution_note or None
        locked_dispute.resolved_by = actor_admin_id
        locked_dispute.resolved_at = now

    @staticmethod
    async def resolve_for_seller(
        session: AsyncSession,
        *,
        dispute: SellerOrderDispute,
        order: SellerOrder,
        actor_admin_id: Optional[int] = None,
        resolution_note: Optional[str] = None,
    ) -> None:
        # Re-fetch dispute with row lock to prevent double-resolution race condition.
        locked_dispute = await session.scalar(
            select(SellerOrderDispute)
            .where(SellerOrderDispute.id == dispute.id)
            .with_for_update()
        )
        if not locked_dispute or locked_dispute.status != "open":
            raise RuntimeError(f"Dispute {dispute.id} already resolved")
        now = datetime.now(timezone.utc)
        dispute_window_hours, _ = await get_seller_order_v24_windows(session)
        order.status = "completed"
        order.admin_notes = resolution_note or f"Dispute resolved in seller favor: {locked_dispute.reason}"
        order.check_window_minutes = dispute_window_hours * 60
        order.check_expires_at = now + timedelta(hours=dispute_window_hours)
        order.auto_complete_at = now + timedelta(hours=dispute_window_hours)
        order.dispute_deadline_at = now + timedelta(hours=dispute_window_hours)
        locked_dispute.status = "resolved_seller"
        locked_dispute.resolution_note = resolution_note or None
        locked_dispute.resolved_by = actor_admin_id
        locked_dispute.resolved_at = now

    @staticmethod
    async def auto_resolve_expired_disputes(session: AsyncSession, limit: int = 100) -> int:
        rows = list(
            (
                await session.execute(
                    select(SellerOrderDispute)
                    .where(
                        SellerOrderDispute.status == "open",
                        SellerOrderDispute.seller_response_due_at.is_not(None),
                        SellerOrderDispute.seller_response_due_at <= datetime.now(timezone.utc),
                        SellerOrderDispute.seller_responded_at.is_(None),
                    )
                    .limit(limit)
                )
            ).scalars().all()
        )
        processed = 0
        for dispute in rows:
            order = await session.scalar(select(SellerOrder).where(SellerOrder.id == dispute.order_id))
            if not order:
                continue
            await SellerDisputeService.resolve_for_buyer(
                session,
                dispute=dispute,
                order=order,
                actor_admin_id=None,
                resolution_note="Auto-resolved in buyer favor: seller response timeout.",
            )
            processed += 1
        return processed

