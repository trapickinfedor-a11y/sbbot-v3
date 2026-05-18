from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from typing import Optional, List
from datetime import datetime, timezone
from decimal import Decimal

from shared.database.models import SellerBank, Seller


class StockService:
    @staticmethod
    def free_stock_expr():
        return SellerBank.stock_count - func.coalesce(SellerBank.reserved_count, 0)

    @staticmethod
    def get_free_stock(bank: SellerBank) -> int:
        return max(0, int(bank.stock_count or 0) - int(getattr(bank, "reserved_count", 0) or 0))
    
    @staticmethod
    async def get_seller_banks(session: AsyncSession, seller_id: int) -> List[SellerBank]:
        result = await session.execute(
            select(SellerBank).where(
                SellerBank.seller_id == seller_id,
                SellerBank.is_active == True
            ).order_by(SellerBank.category, SellerBank.bank_name)
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def get_bank_by_id(session: AsyncSession, bank_id: int) -> Optional[SellerBank]:
        result = await session.execute(
            select(SellerBank).where(SellerBank.id == bank_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def add_bank(
        session: AsyncSession,
        seller_id: int,
        bank_name: str,
        category: str,
        seller_price: Decimal,
        markup_percent: float = 20.0,
        description: str = None,
        bank_code: str = None,
        product_type: str = "bank",
        product_subtype: str = "log",
        instruction: str = None,
        has_chat: bool = True,
        stock_count: int = 1,
        upload_batch_id: int | None = None,
    ) -> SellerBank:
        """Add bank. If bank_code provided (Add to existing), use it. Else (Create new) use s{seller_id}_{slug}."""
        if not bank_code:
            bank_code = bank_name.lower().replace(" ", "_").replace("-", "_")
            bank_code = f"s{seller_id}_{bank_code}"
        if product_type == "enrol":
            bank_code = f"enrol_{product_subtype}__{bank_code}"
        elif product_subtype:
            bank_code = f"{product_type}_{product_subtype}__{bank_code}"
        
        moderation_status = "pending_moderation"  # All new items go through moderation
        bank = SellerBank(
            seller_id=seller_id,
            upload_batch_id=upload_batch_id,
            bank_name=bank_name,
            bank_code=bank_code,
            category=category,
            product_type=product_type,
            product_subtype=product_subtype,
            seller_price=seller_price,
            base_price=seller_price,
            buyer_price=seller_price,
            is_in_stock=stock_count > 0,
            stock_count=stock_count,
            reserved_count=0,
            description=description,
            instruction=instruction,
            has_chat=has_chat,
            is_active=True,
            moderation_status=moderation_status
        )
        session.add(bank)
        await session.commit()
        await session.refresh(bank)
        return bank
    
    @staticmethod
    async def toggle_stock(session: AsyncSession, bank_id: int) -> Optional[SellerBank]:
        bank = await StockService.get_bank_by_id(session, bank_id)
        if not bank:
            return None
        bank.is_in_stock = not bank.is_in_stock and StockService.get_free_stock(bank) > 0
        if bank.is_in_stock and bank.stock_count <= 0:
            bank.stock_count = max(1, int(getattr(bank, "reserved_count", 0) or 0))
            bank.is_in_stock = StockService.get_free_stock(bank) > 0
        bank.updated_at = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(bank)
        return bank
    
    @staticmethod
    async def update_price(
        session: AsyncSession,
        bank_id: int,
        seller_price: Decimal,
        markup_percent: float = 20.0,
        bot=None,
    ) -> Optional[SellerBank]:
        bank = await StockService.get_bank_by_id(session, bank_id)
        if not bank:
            return None
        old_buyer_price = float(bank.buyer_price or 0)
        bank.seller_price = seller_price
        bank.base_price = seller_price
        bank.buyer_price = seller_price
        bank.markup_code = None
        bank.markup_kind = None
        bank.markup_value = None
        bank.moderation_status = "pending_moderation"
        bank.updated_at = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(bank)
        # Trigger wishlist price-drop notifications if price decreased
        if bot and old_buyer_price > float(seller_price):
            try:
                from mirror_bot.services.wishlist_notifier import notify_wishlist_price_drop
                await notify_wishlist_price_drop(
                    bot, session,
                    product_type="bank",
                    product_id=bank_id,
                    product_name=bank.bank_name or f"Product #{bank_id}",
                    new_price=float(seller_price),
                    old_price=old_buyer_price,
                )
            except Exception as exc:
                import logging
                logging.getLogger(__name__).warning("Wishlist price drop notify failed: %s", exc)
        return bank

    @staticmethod
    async def update_stock_count(
        session: AsyncSession,
        bank_id: int,
        stock_count: int,
    ) -> Optional[SellerBank]:
        bank = await StockService.get_bank_by_id(session, bank_id)
        if not bank:
            return None
        reserved_count = int(getattr(bank, "reserved_count", 0) or 0)
        if stock_count < reserved_count:
            return None
        bank.stock_count = max(0, stock_count)
        bank.is_in_stock = StockService.get_free_stock(bank) > 0
        bank.updated_at = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(bank)
        return bank
    
    @staticmethod
    async def delete_bank(session: AsyncSession, bank_id: int) -> bool:
        bank = await StockService.get_bank_by_id(session, bank_id)
        if not bank:
            return False
        if int(getattr(bank, "reserved_count", 0) or 0) > 0:
            return False
        bank.is_active = False
        bank.is_in_stock = False
        bank.updated_at = datetime.now(timezone.utc)
        await session.commit()
        return True
    
    @staticmethod
    async def get_all_in_stock(session: AsyncSession) -> List[SellerBank]:
        """All banks in stock from all approved sellers (moderation_status=approved)"""
        result = await session.execute(
            select(SellerBank).join(Seller).where(
                and_(
                    SellerBank.is_in_stock == True,
                    SellerBank.is_active == True,
                    SellerBank.moderation_status == "approved",
                    StockService.free_stock_expr() > 0,
                    Seller.is_approved == True,
                    Seller.is_active == True,
                    Seller.is_on_vacation == False,
                )
            ).order_by(SellerBank.category, SellerBank.bank_name)
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def get_in_stock_by_category(session: AsyncSession, category: str) -> List[SellerBank]:
        result = await session.execute(
            select(SellerBank).join(Seller).where(
                and_(
                    SellerBank.category == category,
                    SellerBank.is_in_stock == True,
                    SellerBank.is_active == True,
                    SellerBank.moderation_status == "approved",
                    StockService.free_stock_expr() > 0,
                    Seller.is_approved == True,
                    Seller.is_active == True,
                    Seller.is_on_vacation == False,
                )
            ).order_by(SellerBank.bank_name)
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def find_seller_for_bank(session: AsyncSession, bank_code: str) -> Optional[SellerBank]:
        """Find an in-stock bank by code from any approved seller (moderation_status=approved)"""
        result = await session.execute(
            select(SellerBank).join(Seller).where(
                and_(
                    SellerBank.bank_code == bank_code,
                    SellerBank.is_in_stock == True,
                    SellerBank.is_active == True,
                    SellerBank.moderation_status == "approved",
                    StockService.free_stock_expr() > 0,
                    Seller.is_approved == True,
                    Seller.is_active == True,
                    Seller.is_on_vacation == False,
                )
            ).limit(1)
        )
        return result.scalar_one_or_none()
