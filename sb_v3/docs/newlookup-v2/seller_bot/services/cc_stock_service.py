from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

from shared.database.models import SellerCCItem, Seller
from shared.services.nocodb_service import NocoDBService
from shared.services.bin_lookup_service import BinLookupService


class CCStockService:
    
    @staticmethod
    async def get_seller_cc_items(session: AsyncSession, seller_id: int) -> List[SellerCCItem]:
        result = await session.execute(
            select(SellerCCItem).where(
                SellerCCItem.seller_id == seller_id,
                SellerCCItem.is_active == True
            ).order_by(SellerCCItem.category_code, SellerCCItem.item_name)
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def get_cc_item_by_id(session: AsyncSession, item_id: int) -> Optional[SellerCCItem]:
        result = await session.execute(
            select(SellerCCItem).where(SellerCCItem.id == item_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def add_cc_item(
        session: AsyncSession,
        seller_id: int,
        item_name: str,
        category_code: str,
        cc_code: str,
        seller_price: Decimal,
        markup_percent: float = 20.0,
        description: str = None,
        instruction: str = None,
        product_subtype: str = "cc",
        extra_data: dict = None,
        parsed_data: dict | None = None,
        upload_batch_id: int | None = None,
    ) -> SellerCCItem:
        parsed_data = parsed_data or {}
        num = (parsed_data.get("number") or "").replace(" ", "")
        card_bin = num[:6] if len(num) >= 6 else None
        card_type = (extra_data or {}).get("card_type") or (parsed_data.get("extra_data") or {}).get("card_type")
        item = SellerCCItem(
            seller_id=seller_id,
            upload_batch_id=upload_batch_id,
            card_bin=card_bin,
            item_name=item_name,
            cc_code=cc_code,
            category_code=category_code,
            product_type="cc",
            product_subtype=product_subtype,
            seller_price=seller_price,
            base_price=seller_price,
            buyer_price=seller_price,
            is_in_stock=True,
            stock_count=1,
            description=description,
            instruction=instruction,
            number=parsed_data.get("number"),
            exp_mm=parsed_data.get("exp_mm"),
            exp_yyyy=parsed_data.get("exp_yyyy"),
            cvv=parsed_data.get("cvv"),
            fname=parsed_data.get("fname"),
            lname=parsed_data.get("lname"),
            address=parsed_data.get("address"),
            city=parsed_data.get("city"),
            state=parsed_data.get("state"),
            zip=parsed_data.get("zip"),
            country=parsed_data.get("country"),
            bank_name=parsed_data.get("bank_name"),
            card_brand=parsed_data.get("card_brand"),
            card_level=parsed_data.get("card_level"),
            card_type=card_type,
            is_non_vbv=bool(parsed_data.get("is_non_vbv")),
            has_fullz=bool(parsed_data.get("has_fullz")),
            extra_data=extra_data,
            is_active=True,
            moderation_status="pending_moderation"
        )
        session.add(item)
        await session.commit()
        await session.refresh(item)
        NocoDBService.log_seller_upload(
            seller_id=seller_id,
            category=category_code,
            status="success",
            extra={
                "item_type": "cc",
                "upload_batch_id": upload_batch_id,
                "cc_item_id": item.id,
                "item_name": item_name,
                "product_subtype": product_subtype,
            },
        )
        return item
