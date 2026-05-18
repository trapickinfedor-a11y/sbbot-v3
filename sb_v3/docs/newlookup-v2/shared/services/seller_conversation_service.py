from __future__ import annotations

"""
Сервис для работы с чатами селлер-покупатель (один чат на покупателя)
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import SellerConversation, SellerOrder, SellerChat


async def get_or_create_conversation(
    session: AsyncSession,
    seller_id: int,
    buyer_user_id: int,
    mirror_bot_id: int | None,
    *,
    source_order_type: str | None = None,
    source_order_id: int | None = None,
) -> SellerConversation:
    """Получить или создать чат между селлером и покупателем"""
    mirror_cond = (
        (SellerConversation.mirror_bot_id == mirror_bot_id)
        if mirror_bot_id is not None
        else SellerConversation.mirror_bot_id.is_(None)
    )
    if source_order_id is not None:
        result = await session.execute(
            select(SellerConversation).where(
                SellerConversation.seller_id == seller_id,
                SellerConversation.buyer_user_id == buyer_user_id,
                mirror_cond,
                SellerConversation.source_order_id == source_order_id,
                SellerConversation.source_order_type == source_order_type,
            )
        )
        conv = result.scalar_one_or_none()
        if conv:
            return conv

    result = await session.execute(
        select(SellerConversation).where(
            SellerConversation.seller_id == seller_id,
            SellerConversation.buyer_user_id == buyer_user_id,
            mirror_cond,
            SellerConversation.source_order_id.is_(None),
        )
    )
    conv = result.scalar_one_or_none()
    if conv:
        if source_order_id is not None and conv.source_order_id is None:
            conv.source_order_id = source_order_id
            conv.source_order_type = source_order_type
            await session.commit()
            await session.refresh(conv)
        return conv
    conv = SellerConversation(
        seller_id=seller_id,
        buyer_user_id=buyer_user_id,
        mirror_bot_id=mirror_bot_id,
        source_order_type=source_order_type,
        source_order_id=source_order_id,
    )
    session.add(conv)
    await session.commit()
    await session.refresh(conv)
    return conv


async def get_conversation_from_order(
    session: AsyncSession,
    order: SellerOrder
) -> SellerConversation:
    """Получить/создать чат из заказа"""
    return await get_or_create_conversation(
        session,
        seller_id=order.seller_id,
        buyer_user_id=order.buyer_user_id,
        mirror_bot_id=order.mirror_bot_id,
        source_order_type=(getattr(order, "product_type", None) or "bank"),
        source_order_id=getattr(order, "id", None),
    )
