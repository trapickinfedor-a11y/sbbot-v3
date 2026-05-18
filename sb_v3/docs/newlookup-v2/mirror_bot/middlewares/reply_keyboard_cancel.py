from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

REPLY_KEYBOARD_BUTTONS = {
    "👤 My profile",
    "💳 Top-up balance", 
    "🔎 Search",
    "📈 CREDIT REPORTS",
    "📄 DOCUMENTS",
    "🧰 PROS & FULLZ",
    "🏦 BANKS",
    "📶 eSIM",
    "🧾 Subscriptions / Accounts",
    "✍️ Add info in CR",
    "📜 Service rules",
    "🤝 Referrals +4%"
}


class ReplyKeyboardCancelMiddleware(BaseMiddleware):
    """
    Middleware для обработки нажатий кнопок Reply Keyboard во время FSM состояний.
    Если пользователь находится в FSM состоянии и нажимает кнопку из главного меню,
    то FSM state очищается и сообщение обрабатывается нормально.
    """
    
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        # Проверяем только текстовые сообщения
        if not event.text:
            return await handler(event, data)
        
        # Проверяем, является ли текст кнопкой из Reply Keyboard
        if event.text in REPLY_KEYBOARD_BUTTONS:
            state: FSMContext = data.get("state")
            if state:
                current_state = await state.get_state()
                # Если пользователь в FSM состоянии, очищаем его
                if current_state:
                    await state.clear()
        
        # Продолжаем обработку
        return await handler(event, data)

