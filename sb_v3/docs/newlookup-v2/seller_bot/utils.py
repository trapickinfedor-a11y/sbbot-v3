"""Seller bot utilities"""

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import SellerChat, SellerConversation, SellerOrder


async def get_seller_unread_count(session: AsyncSession, seller_id: int) -> int:
    """Get total count of unread buyer messages for seller"""
    conv_result = await session.execute(
        select(func.count(SellerChat.id))
        .join(SellerConversation, SellerChat.seller_conversation_id == SellerConversation.id)
        .where(
            and_(
                SellerConversation.seller_id == seller_id,
                SellerChat.sender_type == "buyer",
                SellerChat.is_read == False,
            )
        )
    )
    legacy_result = await session.execute(
        select(func.count(SellerChat.id))
        .join(SellerOrder, SellerChat.seller_order_id == SellerOrder.id)
        .where(
            and_(
                SellerOrder.seller_id == seller_id,
                SellerChat.sender_type == "buyer",
                SellerChat.is_read == False,
                SellerChat.seller_conversation_id.is_(None),
            )
        )
    )
    return (conv_result.scalar_one() or 0) + (legacy_result.scalar_one() or 0)
