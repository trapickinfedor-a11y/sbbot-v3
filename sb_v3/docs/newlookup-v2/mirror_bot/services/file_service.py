"""
Сервис для работы с файлами в боте
"""

import os
import uuid
import aiofiles
import aiohttp
import logging
from typing import Optional, Dict, Any
from aiogram import Bot
from aiogram.types import Message, FSInputFile

from shared.database.models import SupportMessage

logger = logging.getLogger(__name__)


class FileService:
    """Сервис для работы с файлами"""
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self.upload_dir = "uploads/telegram"
        os.makedirs(self.upload_dir, exist_ok=True)
    
    async def download_and_save_file(self, message: Message) -> Optional[Dict[str, Any]]:
        """
        Скачать файл из сообщения и сохранить на сервере
        """
        
        try:
            logger.info(f"Starting file download for message from user {message.from_user.id}")
            file_info = None
            file_type = None
            file_name = None
            
            # Определяем тип файла
            if message.photo:
                # Берем фото наибольшего размера
                photo = message.photo[-1]
                file_info = await self.bot.get_file(photo.file_id)
                file_type = "photo"
                file_name = f"photo_{uuid.uuid4()}.jpg"
                
            elif message.document:
                file_info = await self.bot.get_file(message.document.file_id)
                file_type = "document"
                file_name = message.document.file_name or f"document_{uuid.uuid4()}"
                
            elif message.video:
                file_info = await self.bot.get_file(message.video.file_id)
                file_type = "video"
                file_name = f"video_{uuid.uuid4()}.mp4"
                
            elif message.audio:
                file_info = await self.bot.get_file(message.audio.file_id)
                file_type = "audio"
                file_name = message.audio.file_name or f"audio_{uuid.uuid4()}.mp3"
                
            elif message.voice:
                file_info = await self.bot.get_file(message.voice.file_id)
                file_type = "voice"
                file_name = f"voice_{uuid.uuid4()}.ogg"
                
            elif message.video_note:
                file_info = await self.bot.get_file(message.video_note.file_id)
                file_type = "video_note"
                file_name = f"video_note_{uuid.uuid4()}.mp4"
            
            if not file_info:
                return None
            
            # Генерируем уникальное имя файла для хранения
            file_extension = os.path.splitext(file_name)[1] if file_name else ""
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            local_file_path = os.path.join(self.upload_dir, unique_filename)
            
            # Скачиваем файл
            await self.bot.download_file(file_info.file_path, local_file_path)
            
            return {
                "file_id": unique_filename,  # Используем локальное имя файла
                "original_telegram_file_id": file_info.file_id,
                "file_name": file_name,
                "file_type": file_type,
                "file_size": file_info.file_size,
                "local_path": local_file_path
            }
            
        except Exception as e:
            logger.error(f"Ошибка при скачивании файла: {e}")
            return None
    
    async def send_file_to_user(self, chat_id: int, file_data: Dict[str, Any], caption: str = None) -> bool:
        """
        Отправить файл пользователю
        """
        
        try:
            # Если есть local_path, используем его (файлы от админа)
            if "local_path" in file_data and file_data["local_path"]:
                file_path = file_data["local_path"]
            else:
                # Иначе ищем в uploads/telegram (файлы от пользователей)
                file_path = os.path.join(self.upload_dir, file_data["file_id"])
            
            logger.info(f"Trying to send file: {file_path}")
            
            # Проверяем существование файла
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return False
            
            # Определяем метод отправки по типу файла
            file_type = file_data.get("file_type") or file_data.get("type", "document")
            
            if file_type == "photo":
                await self.bot.send_photo(
                    chat_id=chat_id,
                    photo=FSInputFile(file_path),
                    caption=caption
                )
            elif file_type == "video":
                await self.bot.send_video(
                    chat_id=chat_id,
                    video=FSInputFile(file_path),
                    caption=caption
                )
            elif file_type == "audio":
                await self.bot.send_audio(
                    chat_id=chat_id,
                    audio=FSInputFile(file_path),
                    caption=caption
                )
            elif file_type == "voice":
                await self.bot.send_voice(
                    chat_id=chat_id,
                    voice=FSInputFile(file_path),
                    caption=caption
                )
            else:  # document и остальные
                await self.bot.send_document(
                    chat_id=chat_id,
                    document=FSInputFile(file_path),
                    caption=caption
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при отправке файла пользователю: {e}")
            return False
    
    async def get_file_info(self, file_id: str) -> Optional[Dict[str, Any]]:
        """
        Получить информацию о файле по ID
        """
        
        file_path = os.path.join(self.upload_dir, file_id)
        
        if not os.path.exists(file_path):
            return None
        
        file_size = os.path.getsize(file_path)
        file_extension = os.path.splitext(file_path)[1]
        
        return {
            "file_id": file_id,
            "file_path": file_path,
            "file_size": file_size,
            "file_extension": file_extension
        }