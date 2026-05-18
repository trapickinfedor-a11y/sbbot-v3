from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import Seller, SellerHelper
from shared.services.seller_deposit_service import SellerDepositService


@dataclass
class SellerActorContext:
    seller: Seller
    helper: Optional[SellerHelper] = None
    pending_approval: bool = False

    @property
    def is_owner(self) -> bool:
        return self.helper is None

    @property
    def is_helper(self) -> bool:
        return self.helper is not None

    @property
    def actor_telegram_id(self) -> int:
        return int(self.helper.telegram_id if self.helper else self.seller.telegram_id)

    @property
    def actor_label(self) -> str:
        if self.helper:
            return self.helper.display_name or self.helper.username or f"Helper {self.helper.id}"
        return self.seller.display_name or self.seller.username or f"Seller {self.seller.id}"

    @property
    def role(self) -> str:
        return self.helper.role if self.helper else "owner"

    def can_upload(self) -> bool:
        return self.is_owner or self.role in {"upload_helper", "manager_helper"}

    def can_support(self) -> bool:
        return self.is_owner or self.role in {"support_helper", "manager_helper"}

    def can_manage_helpers(self) -> bool:
        return self.is_owner

    def can_manage_finance(self) -> bool:
        return self.is_owner

    def can_view_profile(self) -> bool:
        return True


async def resolve_seller_actor(session: AsyncSession, telegram_id: int) -> Optional[SellerActorContext]:
    seller = await session.scalar(select(Seller).where(Seller.telegram_id == telegram_id))
    if seller:
        return SellerActorContext(
            seller=seller,
            helper=None,
            pending_approval=not SellerDepositService.seller_is_active(seller),
        )

    helper = await session.scalar(
        select(SellerHelper).where(
            and_(
                SellerHelper.telegram_id == telegram_id,
                SellerHelper.status.in_(("pending", "active")),
            )
        )
    )
    if not helper:
        return None

    seller = await session.scalar(select(Seller).where(Seller.id == helper.seller_id))
    if not seller:
        return None

    pending = helper.status != "active" or not SellerDepositService.seller_is_active(seller)
    return SellerActorContext(seller=seller, helper=helper, pending_approval=pending)
