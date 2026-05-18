from __future__ import annotations

from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import (
    SellerCheckItem,
    SellerDocumentItem,
    SellerEnrollItem,
    SellerFullzItem,
    SellerNFCItem,
    SellerOTPItem,
    SellerSelfregCCItem,
)
from shared.services.nocodb_service import NocoDBService


class SpecialStockService:
    @staticmethod
    async def add_nfc_item(session: AsyncSession, **payload) -> SellerNFCItem:
        item = SellerNFCItem(**payload)
        session.add(item)
        await session.commit()
        await session.refresh(item)
        NocoDBService.log_seller_upload(
            seller_id=getattr(item, "seller_id", None),
            category="bank",
            status="success",
            extra={"item_type": "nfc", "upload_batch_id": getattr(item, "upload_batch_id", None), "item_id": item.id},
        )
        return item

    @staticmethod
    async def add_otp_item(session: AsyncSession, **payload) -> SellerOTPItem:
        item = SellerOTPItem(**payload)
        session.add(item)
        await session.commit()
        await session.refresh(item)
        NocoDBService.log_seller_upload(
            seller_id=getattr(item, "seller_id", None),
            category="bank",
            status="success",
            extra={"item_type": "otp", "upload_batch_id": getattr(item, "upload_batch_id", None), "item_id": item.id},
        )
        return item

    @staticmethod
    async def add_enroll_item(session: AsyncSession, **payload) -> SellerEnrollItem:
        item = SellerEnrollItem(**payload)
        session.add(item)
        await session.commit()
        await session.refresh(item)
        NocoDBService.log_seller_upload(
            seller_id=getattr(item, "seller_id", None),
            category="bank",
            status="success",
            extra={"item_type": "enroll", "item_id": item.id},
        )
        return item

    @staticmethod
    async def add_selfreg_cc_item(session: AsyncSession, **payload) -> SellerSelfregCCItem:
        item = SellerSelfregCCItem(**payload)
        session.add(item)
        await session.commit()
        await session.refresh(item)
        NocoDBService.log_seller_upload(
            seller_id=getattr(item, "seller_id", None),
            category="cc",
            status="success",
            extra={"item_type": "selfreg_cc", "upload_batch_id": getattr(item, "upload_batch_id", None), "item_id": item.id},
        )
        return item

    @staticmethod
    async def add_check_item(session: AsyncSession, **payload) -> SellerCheckItem:
        item = SellerCheckItem(**payload)
        session.add(item)
        await session.commit()
        await session.refresh(item)
        NocoDBService.log_seller_upload(
            seller_id=getattr(item, "seller_id", None),
            category="bank",
            status="success",
            extra={"item_type": "check", "upload_batch_id": getattr(item, "upload_batch_id", None), "item_id": item.id},
        )
        return item

    @staticmethod
    async def add_document_item(session: AsyncSession, **payload) -> SellerDocumentItem:
        item = SellerDocumentItem(**payload)
        session.add(item)
        await session.commit()
        await session.refresh(item)
        NocoDBService.log_seller_upload(
            seller_id=getattr(item, "seller_id", None),
            category="docs",
            status="success",
            extra={"item_type": "document", "upload_batch_id": getattr(item, "upload_batch_id", None), "item_id": item.id},
        )
        return item

    @staticmethod
    async def add_fullz_item(session: AsyncSession, **payload) -> SellerFullzItem:
        item = SellerFullzItem(**payload)
        session.add(item)
        await session.commit()
        await session.refresh(item)
        NocoDBService.log_seller_upload(
            seller_id=getattr(item, "seller_id", None),
            category="fullz",
            status="success",
            extra={"item_type": "fullz", "upload_batch_id": getattr(item, "upload_batch_id", None), "item_id": item.id},
        )
        return item

    @staticmethod
    def price_to_decimal(value) -> Decimal:
        return Decimal(str(value))
