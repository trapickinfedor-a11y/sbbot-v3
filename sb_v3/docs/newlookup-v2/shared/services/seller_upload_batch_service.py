from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select

from shared.database.models import (
    BruteBankItem,
    SellerBank,
    SellerCCItem,
    SellerCheckItem,
    SellerNFCItem,
    SellerOTPItem,
    SellerSelfregCCItem,
    SellerUploadBatch,
)


class SellerUploadBatchService:
    @staticmethod
    async def create_batch(
        session: AsyncSession,
        *,
        seller_id: int,
        item_type: str,
        upload_mode: str,
        title: str | None,
        total_items: int,
        draft_payload: dict | None = None,
        validation_summary: dict | None = None,
        error_report: dict | None = None,
        submitted: bool = False,
        resubmitted_from_batch_id: int | None = None,
    ) -> SellerUploadBatch:
        batch = SellerUploadBatch(
            seller_id=seller_id,
            item_type=item_type,
            upload_mode=upload_mode,
            title=title,
            total_items=total_items,
            moderation_status="pending",
            draft_payload=draft_payload,
            validation_summary=validation_summary,
            error_report=error_report,
            submitted_at=datetime.now(timezone.utc) if submitted else None,
            resubmitted_from_batch_id=resubmitted_from_batch_id,
            pending_items=total_items,
        )
        session.add(batch)
        await session.flush()
        return batch

    @staticmethod
    async def recalc_batch_status(session: AsyncSession, batch_id: int | None, item_type: str) -> None:
        if not batch_id:
            return
        batch = await session.get(SellerUploadBatch, batch_id)
        if not batch:
            return

        if item_type == "bank":
            rows = list((await session.execute(select(SellerBank.moderation_status).where(SellerBank.upload_batch_id == batch_id))).scalars().all())
            approved_value = "approved"
            rejected_values = {"rejected"}
            changes_values = {"changes_requested"}
            pending_values = {"pending_moderation"}
        elif item_type == "cc":
            rows = list((await session.execute(select(SellerCCItem.moderation_status).where(SellerCCItem.upload_batch_id == batch_id))).scalars().all())
            approved_value = "approved"
            rejected_values = {"rejected"}
            changes_values = {"changes_requested"}
            pending_values = {"pending_moderation"}
        elif item_type == "nfc":
            rows = list((await session.execute(select(SellerNFCItem.moderation_status).where(SellerNFCItem.upload_batch_id == batch_id))).scalars().all())
            approved_value = "approved"
            rejected_values = {"rejected"}
            changes_values = {"changes_requested"}
            pending_values = {"pending_moderation"}
        elif item_type == "otp":
            rows = list((await session.execute(select(SellerOTPItem.moderation_status).where(SellerOTPItem.upload_batch_id == batch_id))).scalars().all())
            approved_value = "approved"
            rejected_values = {"rejected"}
            changes_values = {"changes_requested"}
            pending_values = {"pending_moderation"}
        elif item_type == "selfreg_cc":
            rows = list((await session.execute(select(SellerSelfregCCItem.moderation_status).where(SellerSelfregCCItem.upload_batch_id == batch_id))).scalars().all())
            approved_value = "approved"
            rejected_values = {"rejected"}
            changes_values = {"changes_requested"}
            pending_values = {"pending_moderation"}
        elif item_type == "check":
            rows = list((await session.execute(select(SellerCheckItem.moderation_status).where(SellerCheckItem.upload_batch_id == batch_id))).scalars().all())
            approved_value = "approved"
            rejected_values = {"rejected"}
            changes_values = {"changes_requested"}
            pending_values = {"pending_moderation"}
        else:
            rows = list((await session.execute(select(BruteBankItem.moderation_status).where(BruteBankItem.upload_batch_id == batch_id))).scalars().all())
            approved_value = "approved"
            rejected_values = {"rejected"}
            changes_values = set()
            pending_values = {"pending"}

        if not rows:
            return
        batch.total_items = len(rows)
        batch.approved_items = sum(1 for row in rows if row == approved_value)
        batch.rejected_items = sum(1 for row in rows if row in rejected_values)
        batch.changes_requested_items = sum(1 for row in rows if row in changes_values)
        batch.pending_items = sum(1 for row in rows if row in pending_values)

        unique = set(rows)
        if unique == {approved_value}:
            batch.moderation_status = "approved"
        elif unique.issubset(rejected_values):
            batch.moderation_status = "rejected"
        elif unique & changes_values:
            batch.moderation_status = "changes_requested"
        elif unique & pending_values:
            batch.moderation_status = "pending"
        else:
            batch.moderation_status = "partial"
        if batch.moderation_status in {"approved", "rejected", "partial", "changes_requested"}:
            batch.reviewed_at = datetime.now(timezone.utc)
        await session.commit()

    @staticmethod
    async def list_batches(session: AsyncSession, seller_id: int, limit: int = 100) -> list[SellerUploadBatch]:
        result = await session.execute(
            select(SellerUploadBatch)
            .where(SellerUploadBatch.seller_id == seller_id)
            .order_by(SellerUploadBatch.created_at.desc(), SellerUploadBatch.id.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
