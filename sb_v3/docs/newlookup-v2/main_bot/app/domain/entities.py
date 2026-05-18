from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class MirrorBot:
    user_id: int
    bot_token: str
    bot_username: str
    created_at: datetime
    id: Optional[int] = None
    
    @classmethod
    def create(cls, user_id: int, bot_token: str, bot_username: str):
        return cls(
            user_id=user_id,
            bot_token=bot_token,
            bot_username=bot_username,
            created_at=datetime.now()
        )

