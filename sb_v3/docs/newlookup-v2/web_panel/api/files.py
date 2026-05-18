"""
API для работы с файлами
"""

import os
import uuid
import aiofiles
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from web_panel.auth import get_current_user
from web_panel.database import get_db
from shared.database.models import SupportMessage
from web_panel.config import web_panel_config

router = APIRouter()
logger = logging.getLogger(__name__)

# Директория для хранения файлов
UPLOAD_DIR = os.path.abspath(web_panel_config.upload_dir)
TELEGRAM_FILES_DIR = os.path.join(UPLOAD_DIR, "telegram")

# Создаем директории если их нет
os.makedirs(TELEGRAM_FILES_DIR, exist_ok=True)


def _safe_resolve(base_dir: str, file_id: str) -> str:
    """
    Безопасно разрешает путь к файлу, защищая от path traversal.
    Поднимает HTTPException 400 если file_id выходит за пределы base_dir.
    """
    # os.path.basename убирает любые ../ и абсолютные компоненты
    safe_name = os.path.basename(file_id)
    if not safe_name or safe_name != file_id:
        raise HTTPException(status_code=400, detail="Invalid file identifier")
    resolved = os.path.realpath(os.path.join(base_dir, safe_name))
    base_real = os.path.realpath(base_dir)
    if not resolved.startswith(base_real + os.sep) and resolved != base_real:
        raise HTTPException(status_code=400, detail="Invalid file identifier")
    return resolved


@router.get("/telegram/{file_id}")
@router.get("/telegram/{bot_id}/{file_id}")
async def get_telegram_file(
    file_id: str,
    bot_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    """
    Получить файл по file_id из Telegram (требует аутентификации).
    """
    try:
        logger.info(f"Requesting file: {file_id}, bot_id: {bot_id}")

        telegram_file_path = _safe_resolve(TELEGRAM_FILES_DIR, file_id)
        logger.info(f"Looking for file at: {telegram_file_path}")

        if os.path.exists(telegram_file_path):
            logger.info(f"File found in telegram directory: {telegram_file_path}")
            file_extension = os.path.splitext(telegram_file_path)[1].lower()
            return FileResponse(
                path=telegram_file_path,
                media_type=get_media_type(file_extension),
                filename=f"file_{file_id}{file_extension}",
            )

        admin_file_path = _safe_resolve(os.path.join(UPLOAD_DIR, "admin"), file_id)
        logger.info(f"Looking for file in admin directory: {admin_file_path}")

        if os.path.exists(admin_file_path):
            logger.info(f"File found in admin directory: {admin_file_path}")
            file_extension = os.path.splitext(admin_file_path)[1].lower()
            return FileResponse(
                path=admin_file_path,
                media_type=get_media_type(file_extension),
                filename=file_id,
            )

        logger.warning(f"File not found in any directory: {file_id}")
        raise HTTPException(status_code=404, detail="Файл не найден")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_telegram_file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка при загрузке файла: {str(e)}")


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Загрузить файл от админа
    """
    
    try:
        # Генерируем уникальное имя файла
        file_extension = os.path.splitext(file.filename)[1] if file.filename else ""
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, "admin", unique_filename)
        
        # Создаем директорию если её нет
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Сохраняем файл
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        return {
            "file_id": unique_filename,
            "filename": file.filename,
            "size": len(content),
            "content_type": file.content_type
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при загрузке файла: {str(e)}"
        )


@router.get("/admin/{file_id}")
async def get_admin_file(
    file_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Получить файл загруженный админом (требует аутентификации).
    """
    file_path = _safe_resolve(os.path.join(UPLOAD_DIR, "admin"), file_id)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Файл не найден")

    file_extension = os.path.splitext(file_path)[1].lower()
    return FileResponse(
        path=file_path,
        media_type=get_media_type(file_extension),
        filename=file_id,
    )


def get_media_type(file_extension: str) -> str:
    """
    Определить MIME тип по расширению файла
    """
    
    mime_types = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.webp': 'image/webp',
        '.pdf': 'application/pdf',
        '.doc': 'application/msword',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.txt': 'text/plain',
        '.mp4': 'video/mp4',
        '.avi': 'video/x-msvideo',
        '.mov': 'video/quicktime',
        '.mp3': 'audio/mpeg',
        '.wav': 'audio/wav',
        '.zip': 'application/zip',
        '.rar': 'application/x-rar-compressed'
    }
    
    return mime_types.get(file_extension, 'application/octet-stream')


async def download_telegram_file(bot_token: str, file_id: str, file_path: str) -> bool:
    """
    Скачать файл из Telegram и сохранить локально
    """
    
    try:
        import aiohttp
        
        # Получаем информацию о файле
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
            # Получаем file_path из Telegram
            get_file_url = f"https://api.telegram.org/bot{bot_token}/getFile"
            async with session.get(get_file_url, params={"file_id": file_id}) as response:
                if response.status != 200:
                    return False
                
                file_info = await response.json()
                if not file_info.get("ok"):
                    return False
                
                telegram_file_path = file_info["result"]["file_path"]
            
            # Скачиваем файл
            download_url = f"https://api.telegram.org/file/bot{bot_token}/{telegram_file_path}"
            async with session.get(download_url) as response:
                if response.status != 200:
                    return False
                
                # Сохраняем файл
                async with aiofiles.open(file_path, 'wb') as f:
                    async for chunk in response.content.iter_chunked(8192):
                        await f.write(chunk)
                
                return True
                
    except Exception as e:
        logger.error(f"Ошибка при скачивании файла из Telegram: {e}")
        return False