from typing import Union, List
from aiogram.filters import Filter
from aiogram.types import Message
from aiogram.fsm.context import FSMContext


class ServiceFilter(Filter):
    """Фильтр для проверки service в FSM state"""
    
    def __init__(self, service: Union[str, List[str]]):
        self.services = [service] if isinstance(service, str) else service
    
    async def __call__(self, message: Message, state: FSMContext) -> bool:
        data = await state.get_data()
        current_service = data.get("service")
        return current_service in self.services

