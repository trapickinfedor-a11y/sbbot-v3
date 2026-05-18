from dataclasses import dataclass
from os import getenv
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    main_bot_token: str
    media_video_path: str
    database_url: str
    
    @classmethod
    def from_env(cls):
        return cls(
            main_bot_token=getenv("MAIN_BOT_TOKEN"),
            media_video_path=getenv("MEDIA_VIDEO_PATH", "./media/conpress.mp4"),
            database_url=getenv("DATABASE_URL", "postgresql+asyncpg://newlookup:tgbotnewlookup@postgres:5432/newlookup"),
        )
    
    @property
    def video_file_exists(self) -> bool:
        return Path(self.media_video_path).exists()

config = Config.from_env()

