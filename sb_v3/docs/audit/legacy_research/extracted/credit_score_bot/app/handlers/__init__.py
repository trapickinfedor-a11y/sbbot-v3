"""
Модуль для регистрации всех хэндлеров в главном диспетчере.
"""

from aiogram import Dispatcher
from .form_handlers import router as form_router
from .ssn_handler import router as ssn_router
from .bulk_handler import router as bulk_router
from .retry_handler import router as retry_router

def register_handlers(dp: Dispatcher):
    # Регистрируем хэндлеры в определенном порядке
    # Сначала команды, потом специфичные состояния, потом общий текст
    dp.include_router(form_router)
    dp.include_router(retry_router)
    dp.include_router(bulk_router) # Должен идти до ssn_handler и общего текстового хэндлера
    dp.include_router(ssn_router)
