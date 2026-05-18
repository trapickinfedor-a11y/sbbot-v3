from abc import ABC, abstractmethod
from typing import Optional, List
from main_bot.app.domain.entities import MirrorBot

class BotRepository(ABC):
    
    @abstractmethod
    async def create(self, bot: MirrorBot) -> MirrorBot:
        pass
    
    @abstractmethod
    async def get_by_token(self, bot_token: str) -> Optional[MirrorBot]:
        """Получить бота по токену (даже неактивного)"""
        pass
    
    @abstractmethod
    async def get_by_user_id(self, user_id: int) -> Optional[MirrorBot]:
        pass
    
    @abstractmethod
    async def get_by_id(self, bot_id: int) -> Optional[MirrorBot]:
        pass
    
    @abstractmethod
    async def get_all(self) -> List[MirrorBot]:
        pass
    
    @abstractmethod
    async def reactivate(self, bot_id: int, bot_username: Optional[str] = None) -> bool:
        """Реактивировать неактивного бота"""
        pass
    
    @abstractmethod
    async def delete_by_user_id(self, user_id: int) -> bool:
        pass
    
    @abstractmethod
    async def init_db(self):
        pass

