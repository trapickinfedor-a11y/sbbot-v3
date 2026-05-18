"""
Middleware для проверки прав доступа воркеров
"""

from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from support_bot.config import support_bot_config
from support_bot.services.access_service import SupportAccessService
from support_bot.services.worker_service import WorkerService


class WorkerAuthMiddleware(BaseMiddleware):
    """Allow workers and support/admin staff into support bot."""
    
    def __init__(self):
        super().__init__()
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Получаем user_id из события
        user_id = None
        if isinstance(event, (Message, CallbackQuery)):
            user_id = event.from_user.id
        
        if not user_id:
            return await handler(event, data)
        
        # Проверяем системного админа из env
        if user_id in support_bot_config.system_admin_ids:
            data["support_bot_actor"] = SupportAccessService.get_system_admin_actor(user_id)
            data["is_admin"] = True
            data["is_worker"] = True
            return await handler(event, data)
        
        # Получаем сессию БД
        session: AsyncSession = data.get("session")
        if not session:
            return await handler(event, data)
        
        admin_actor = await SupportAccessService.get_admin_actor(session, user_id)
        worker_actor = await SupportAccessService.get_worker_actor(session, user_id)

        if admin_actor:
            data["support_bot_actor"] = admin_actor
            data["is_admin"] = True
            data["admin_role"] = admin_actor.role

        if worker_actor:
            worker = await WorkerService.get_worker(session, user_id)
            if worker and getattr(worker, "is_suspended", False):
                suspended_reason = getattr(worker, "suspended_reason", None) or "Access suspended"
                if isinstance(event, Message):
                    await event.answer(f"❌ Доступ приостановлен.\n{str(suspended_reason)}")
                elif isinstance(event, CallbackQuery):
                    await event.answer(f"❌ Доступ приостановлен.\n{str(suspended_reason)}", show_alert=True)
                return
            data["is_worker"] = True
            data["worker"] = worker
        else:
            data["is_worker"] = False

        if admin_actor or worker_actor:
            return await handler(event, data)
        
        # Если пользователь не воркер и не админ, отправляем сообщение об ошибке
        if isinstance(event, Message):
            await event.answer(
                "❌ У вас нет доступа к этому боту.\n"
                "Обратитесь к администратору для получения прав доступа."
            )
        elif isinstance(event, CallbackQuery):
            await event.answer(
                "❌ У вас нет доступа к этому боту.",
                show_alert=True
            )
        
        return  # Не вызываем handler для неавторизованных пользователей
