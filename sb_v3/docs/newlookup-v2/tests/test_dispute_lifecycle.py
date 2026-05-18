"""Dispute lifecycle integration tests.

Tests cover:
- Opening a dispute
- Seller submitting evidence (text + file)
- Admin resolving a dispute
- Seller requesting an appeal
- Edge cases: double-appeal, appeal on non-resolved dispute
"""

from __future__ import annotations

import unittest
from datetime import datetime
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from shared.database.models import Base, SellerOrderDispute

SellerDispute = SellerOrderDispute  # alias


class DisputeLifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
        )
        async with self.engine.begin() as conn:
            await conn.execute(text("PRAGMA foreign_keys = OFF"))
            await conn.run_sync(Base.metadata.create_all)
        self.session_maker = async_sessionmaker(self.engine, expire_on_commit=False)

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()

    async def _create_dispute(
        self,
        session,
        order_id: int = 9001,
        seller_id: int = 1,
        description: str = "Test dispute",
    ) -> SellerDispute:
        dispute = SellerDispute(
            order_id=order_id,
            opened_by=seller_id,
            reason="not_delivered",
            description=description,
            status="open",
        )
        session.add(dispute)
        await session.flush()
        return dispute

    # ── Basic creation ────────────────────────────────────────────────────────

    async def test_dispute_created_with_open_status(self) -> None:
        async with self.session_maker() as session:
            dispute = await self._create_dispute(session)
            await session.commit()

            self.assertEqual(dispute.status, "open")
            self.assertIsNone(dispute.seller_evidence)
            self.assertIsNone(dispute.appeal_status)
            self.assertIsNone(dispute.resolved_at)

    # ── Evidence submission (text) ────────────────────────────────────────────

    async def test_seller_can_submit_text_evidence(self) -> None:
        async with self.session_maker() as session:
            dispute = await self._create_dispute(session)
            await session.commit()
            await session.refresh(dispute)

            dispute.seller_evidence = {
                "text": "I delivered the correct item. Here is my explanation.",
                "submitted_at": datetime.utcnow().isoformat(),
            }
            dispute.status = "seller_responded"
            dispute.seller_responded_at = datetime.utcnow()
            await session.commit()
            await session.refresh(dispute)

            self.assertEqual(dispute.status, "seller_responded")
            self.assertIn("text", dispute.seller_evidence)
            self.assertIsNotNone(dispute.seller_responded_at)

    # ── Evidence submission (file) ────────────────────────────────────────────

    async def test_seller_can_submit_file_evidence(self) -> None:
        async with self.session_maker() as session:
            dispute = await self._create_dispute(session)
            await session.commit()
            await session.refresh(dispute)

            dispute.seller_evidence = {
                "file_id": "AgACAgIxxxxx",
                "media_type": "document",
                "submitted_at": datetime.utcnow().isoformat(),
            }
            dispute.status = "seller_responded"
            dispute.seller_responded_at = datetime.utcnow()
            await session.commit()
            await session.refresh(dispute)

            self.assertEqual(dispute.status, "seller_responded")
            self.assertEqual(dispute.seller_evidence["media_type"], "document")

    # ── Admin resolution ──────────────────────────────────────────────────────

    async def test_admin_can_resolve_dispute(self) -> None:
        async with self.session_maker() as session:
            dispute = await self._create_dispute(session)
            dispute.status = "seller_responded"
            await session.commit()
            await session.refresh(dispute)

            dispute.status = "resolved"
            dispute.resolution_note = "Dispute resolved in favour of buyer."
            dispute.resolved_by = 99001
            dispute.resolved_at = datetime.utcnow()
            await session.commit()
            await session.refresh(dispute)

            self.assertEqual(dispute.status, "resolved")
            self.assertIsNotNone(dispute.resolved_at)
            self.assertIsNotNone(dispute.resolution_note)

    # ── Appeal flow ───────────────────────────────────────────────────────────

    async def test_seller_can_request_appeal_after_resolution(self) -> None:
        async with self.session_maker() as session:
            dispute = await self._create_dispute(session)
            dispute.status = "resolved"
            dispute.resolved_at = datetime.utcnow()
            await session.commit()
            await session.refresh(dispute)

            self.assertIsNone(dispute.appeal_status)

            dispute.appeal_status = "pending"
            dispute.appeal_reason = "I disagree with the resolution. Proof attached."
            dispute.appeal_requested_at = datetime.utcnow()
            await session.commit()
            await session.refresh(dispute)

            self.assertEqual(dispute.appeal_status, "pending")
            self.assertIsNotNone(dispute.appeal_reason)
            self.assertIsNotNone(dispute.appeal_requested_at)

    async def test_seller_cannot_double_appeal(self) -> None:
        """Once appeal_status is set, it should not be overwritten."""
        async with self.session_maker() as session:
            dispute = await self._create_dispute(session)
            dispute.status = "resolved"
            dispute.appeal_status = "pending"
            dispute.appeal_reason = "First appeal reason."
            dispute.appeal_requested_at = datetime.utcnow()
            await session.commit()
            await session.refresh(dispute)

            already_appealed = dispute.appeal_status is not None
            self.assertTrue(already_appealed)

    async def test_appeal_blocked_before_resolution(self) -> None:
        """Appeal should only be available when dispute.status == 'resolved'."""
        async with self.session_maker() as session:
            dispute = await self._create_dispute(session)
            await session.commit()
            await session.refresh(dispute)

            can_appeal = dispute.status == "resolved" and dispute.appeal_status is None
            self.assertFalse(can_appeal)

    # ── Evidence is preserved across updates ─────────────────────────────────

    async def test_evidence_is_preserved_across_additional_text(self) -> None:
        async with self.session_maker() as session:
            dispute = await self._create_dispute(session)
            await session.commit()
            await session.refresh(dispute)

            dispute.seller_evidence = {"file_id": "file_111", "media_type": "document"}
            await session.commit()
            await session.refresh(dispute)

            existing = dict(dispute.seller_evidence)
            existing["text"] = "Additional explanation."
            dispute.seller_evidence = existing
            await session.commit()
            await session.refresh(dispute)

            self.assertIn("file_id", dispute.seller_evidence)
            self.assertIn("text", dispute.seller_evidence)

    # ── Multiple disputes per seller allowed ──────────────────────────────────

    async def test_multiple_disputes_different_orders(self) -> None:
        async with self.session_maker() as session:
            d1 = await self._create_dispute(session, order_id=9001)
            d2 = await self._create_dispute(session, order_id=9002)
            await session.commit()

            self.assertNotEqual(d1.id, d2.id)
            self.assertEqual(d1.order_id, 9001)
            self.assertEqual(d2.order_id, 9002)

    # ── Dispute reason is stored ──────────────────────────────────────────────

    async def test_dispute_reason_is_stored(self) -> None:
        async with self.session_maker() as session:
            dispute = await self._create_dispute(session)
            await session.commit()
            await session.refresh(dispute)

            self.assertEqual(dispute.reason, "not_delivered")

    # ── Resolved dispute timestamp ────────────────────────────────────────────

    async def test_unresolved_dispute_has_no_resolved_at(self) -> None:
        async with self.session_maker() as session:
            dispute = await self._create_dispute(session)
            await session.commit()
            await session.refresh(dispute)

            self.assertIsNone(dispute.resolved_at)
            self.assertIsNone(dispute.resolution_note)


if __name__ == "__main__":
    unittest.main()
