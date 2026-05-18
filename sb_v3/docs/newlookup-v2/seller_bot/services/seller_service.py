from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, List
from datetime import datetime, timezone

from shared.database.models import Seller, SellerBank, SellerOrder
from shared.services.seller_deposit_service import SellerDepositService


class SellerService:
    
    @staticmethod
    async def get_seller(session: AsyncSession, telegram_id: int) -> Optional[Seller]:
        result = await session.execute(
            select(Seller).where(Seller.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_or_create_admin_seller(
        session: AsyncSession,
        telegram_id: int,
        username: Optional[str] = None,
        display_name: Optional[str] = None,
    ) -> Seller:
        """Create approved seller for admin if not exists (for full panel access)"""
        seller = await SellerService.get_seller(session, telegram_id)
        if seller:
            return seller
        seller = Seller(
            telegram_id=telegram_id,
            username=username,
            display_name=display_name or username or str(telegram_id),
            language="en",
            rules_accepted=True,
            seller_type="internal",
            is_approved=True,
            is_active=True,
            access_status="active",
            security_deposit_status="held",
            security_deposit_categories=["bank", "enrol", "brute", "cc"],
            approved_at=datetime.now(timezone.utc)
        )
        session.add(seller)
        await session.commit()
        await session.refresh(seller)
        return seller
    
    @staticmethod
    async def get_seller_by_id(session: AsyncSession, seller_id: int) -> Optional[Seller]:
        result = await session.execute(
            select(Seller).where(Seller.id == seller_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def register_seller(
        session: AsyncSession,
        telegram_id: int,
        username: Optional[str] = None,
        display_name: Optional[str] = None,
        seller_type: str = "external",
        language: Optional[str] = None,
        rules_accepted: bool = False,
    ) -> Seller:
        seller = await SellerService.get_seller(session, telegram_id)
        if seller:
            seller.username = username
            seller.display_name = display_name or username or seller.display_name or str(telegram_id)
            seller.seller_type = seller_type or seller.seller_type
            seller.is_active = True
            if language:
                seller.language = language
            if rules_accepted:
                seller.rules_accepted = True
        else:
            seller = Seller(
                telegram_id=telegram_id,
                username=username,
                display_name=display_name or username or str(telegram_id),
                language=language or "en",
                rules_accepted=rules_accepted,
                seller_type=seller_type,
                is_approved=False,
                is_active=True,
                access_status="pending_deposit",
            )
            session.add(seller)
        await session.commit()
        await session.refresh(seller)
        return seller

    @staticmethod
    async def create_or_update_seller_draft(
        session: AsyncSession,
        telegram_id: int,
        username: Optional[str] = None,
        display_name: Optional[str] = None,
        language: Optional[str] = None,
    ) -> Seller:
        seller = await SellerService.get_seller(session, telegram_id)
        if seller:
            seller.username = username
            seller.display_name = display_name or username or seller.display_name or str(telegram_id)
            seller.is_active = True
            if language:
                seller.language = language
        else:
            seller = Seller(
                telegram_id=telegram_id,
                username=username,
                display_name=display_name or username or str(telegram_id),
                language=language or "en",
                rules_accepted=False,
                seller_type="external",
                is_approved=False,
                is_active=True,
                access_status="pending_deposit",
            )
            session.add(seller)
        await session.commit()
        await session.refresh(seller)
        return seller
    
    @staticmethod
    async def approve_seller(session: AsyncSession, seller_id: int) -> Optional[Seller]:
        seller = await SellerService.get_seller_by_id(session, seller_id)
        if not seller:
            return None
        SellerDepositService.activate_seller_access(seller, approved_at=datetime.now(timezone.utc))
        await session.commit()
        await session.refresh(seller)
        return seller
    
    @staticmethod
    async def reject_seller(session: AsyncSession, seller_id: int) -> Optional[Seller]:
        seller = await SellerService.get_seller_by_id(session, seller_id)
        if not seller:
            return None
        seller.is_approved = False
        seller.is_active = False
        seller.access_status = "frozen"
        await session.commit()
        return seller
    
    @staticmethod
    async def get_all_sellers(session: AsyncSession, approved_only: bool = False) -> List[Seller]:
        query = select(Seller).order_by(Seller.created_at.desc())
        if approved_only:
            query = query.where(Seller.is_approved == True, Seller.is_active == True)
        result = await session.execute(query)
        return list(result.scalars().all())
    
    @staticmethod
    async def get_pending_sellers(session: AsyncSession) -> List[Seller]:
        result = await session.execute(
            select(Seller).where(
                Seller.is_approved == False,
                Seller.is_active == True
            ).order_by(Seller.created_at.desc())
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def toggle_seller(session: AsyncSession, seller_id: int) -> Optional[Seller]:
        seller = await SellerService.get_seller_by_id(session, seller_id)
        if not seller:
            return None
        seller.is_active = not seller.is_active
        await session.commit()
        await session.refresh(seller)
        return seller
