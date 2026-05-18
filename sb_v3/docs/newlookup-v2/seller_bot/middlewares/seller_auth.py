from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from seller_bot.config import seller_bot_config
from shared.services.seller_actor_service import resolve_seller_actor


class SellerAuthMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user_id = None
        if isinstance(event, (Message, CallbackQuery)):
            user_id = event.from_user.id
        
        if not user_id:
            return await handler(event, data)
        
        # Админы всегда имеют доступ
        if user_id in seller_bot_config.admin_ids:
            data["is_admin"] = True
            data["is_seller"] = True
            data["seller"] = None
            data["seller_actor"] = None
            data["is_helper"] = False
            return await handler(event, data)
        
        session: AsyncSession = data.get("session")
        if not session:
            return await handler(event, data)
        
        actor = await resolve_seller_actor(session, user_id)
        
        data["is_admin"] = False

        if actor and not actor.pending_approval:
            data["is_seller"] = True
            data["seller"] = actor.seller
            data["seller_actor"] = actor
            data["is_helper"] = actor.is_helper
            return await handler(event, data)

        if actor:
            data["is_seller"] = False
            data["seller"] = actor.seller
            data["seller_actor"] = actor
            data["is_helper"] = actor.is_helper
            data["pending_approval"] = True
            return await handler(event, data)

        # New user - not registered yet, let /start handle it
        data["is_seller"] = False
        data["seller"] = None
        data["seller_actor"] = None
        data["is_helper"] = False
        data["pending_approval"] = False
        return await handler(event, data)
