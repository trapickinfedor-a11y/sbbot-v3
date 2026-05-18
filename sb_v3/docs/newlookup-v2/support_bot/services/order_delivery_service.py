"""
Сервис доставки результатов заказов пользователям через их mirror bot
"""

import logging
import os
import tempfile
from typing import Optional, Dict, Any
from pathlib import Path

import aiohttp
from aiogram import Bot
from aiogram.types import FSInputFile, BufferedInputFile
from aiogram.enums import ParseMode
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from shared.database.models import Order, MirrorBot, User
from shared.security.internal_api import build_internal_api_headers
from support_bot.config import support_bot_config

logger = logging.getLogger(__name__)


class OrderDeliveryService:
    """Сервис доставки результатов заказов"""
    
    @staticmethod
    async def get_user_language(
        session: AsyncSession,
        user_id: int,
        mirror_bot_id: int
    ) -> str:
        """Получить язык пользователя из базы данных"""
        try:
            result = await session.execute(
                select(User).where(
                    User.user_id == user_id,
                    User.mirror_bot_id == mirror_bot_id
                )
            )
            user = result.scalar_one_or_none()
            return user.language if user and user.language else "en"
        except Exception as e:
            logger.error(f"Error getting user language: {e}")
            return "en"
    
    @staticmethod
    async def deliver_order_result(
        session: AsyncSession,
        order: Order,
        result_text: Optional[str] = None,
        result_file_url: Optional[str] = None,
        result_file_name: Optional[str] = None,
        result_status: str = "done"
    ) -> bool:
        """
        Доставить результат заказа пользователю через его mirror bot
        
        Args:
            session: Сессия БД
            order: Заказ
            result_text: Текст результата
            result_file_url: URL файла для скачивания
            result_file_name: Имя файла
            result_status: Статус результата (done/nf)
        
        Returns:
            bool: Успешность доставки
        """
        try:
            # Получаем mirror bot пользователя
            mirror_bot = await OrderDeliveryService._get_user_mirror_bot(
                session, order.user_id, order.mirror_bot_id
            )
            
            if not mirror_bot:
                logger.error(f"Mirror bot not found for order {order.id}")
                return False
            
            # Создаем bot instance
            bot = Bot(token=mirror_bot.bot_token)
            
            try:
                # Формируем сообщение
                if result_status == "done":
                    message_text = f"✅ **Order Completed!**\n\n"
                    message_text += f"**Service:** {order.service_name}\n"
                    message_text += f"**Category:** {order.category}\n\n"
                    
                    if result_text:
                        message_text += f"**Result:**\n{result_text}\n\n"
                    
                    message_text += "Thank you for using our service! 🎉"
                    
                elif result_status == "nf":
                    message_text = f"❌ **Order - Not Found**\n\n"
                    message_text += f"**Service:** {order.service_name}\n"
                    message_text += f"**Category:** {order.category}\n\n"
                    message_text += "Unfortunately, we couldn't find the requested information.\n"
                    message_text += "Your balance has been refunded. 💰"
                
                else:
                    message_text = f"📦 **Order #{order.id} Update**\n\n"
                    message_text += f"**Service:** {order.service_name}\n"
                    message_text += f"**Status:** {result_status}\n\n"
                    if result_text:
                        message_text += f"**Details:**\n{result_text}"
                
                # Отправляем результат
                if result_file_url and result_status == "done":
                    # Скачиваем и отправляем файл
                    success = await OrderDeliveryService._send_file_result(
                        bot, order.user_id, message_text, result_file_url, result_file_name
                    )
                else:
                    # Отправляем только текст
                    success = await OrderDeliveryService._send_text_result(
                        bot, order.user_id, message_text
                    )
                
                return success
                
            finally:
                await bot.session.close()
                
        except Exception as e:
            logger.error(f"Failed to deliver order {order.id}: {e}")
            return False
    
    @staticmethod
    async def _get_user_mirror_bot(
        session: AsyncSession, 
        user_id: int, 
        mirror_bot_id: int
    ) -> Optional[MirrorBot]:
        """Получить mirror bot пользователя (НЕ main bot)"""
        try:
            # Получаем mirror bot по ID
            result = await session.execute(
                select(MirrorBot)
                .where(
                    MirrorBot.id == mirror_bot_id,
                    MirrorBot.is_active == True
                )
            )
            mirror_bot = result.scalar_one_or_none()
            
            if not mirror_bot:
                logger.warning(f"Mirror bot {mirror_bot_id} not found or inactive")
                return None
            
            return mirror_bot
            
        except Exception as e:
            logger.error(f"Error getting mirror bot: {e}")
            return None
    
    @staticmethod
    async def _send_file_result(
        bot: Bot,
        user_id: int,
        message_text: str,
        file_url: str,
        file_name: Optional[str] = None
    ) -> bool:
        """Скачать файл и отправить пользователю"""
        temp_file_path = None
        
        try:
            # Скачиваем файл
            temp_file_path = await OrderDeliveryService._download_file(file_url, file_name)
            
            if not temp_file_path:
                # Если не удалось скачать, отправляем только текст
                return await OrderDeliveryService._send_text_result(bot, user_id, message_text)
            
            # Отправляем файл
            file_input = FSInputFile(temp_file_path, filename=file_name or "result.txt")
            
            await bot.send_document(
                chat_id=user_id,
                document=file_input,
                caption=message_text,
                parse_mode=ParseMode.MARKDOWN
            )
            
            logger.info(f"File result sent to user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send file result to user {user_id}: {e}")
            # Fallback: отправляем только текст
            return await OrderDeliveryService._send_text_result(bot, user_id, message_text)
            
        finally:
            # Удаляем временный файл
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                    logger.debug(f"Temporary file {temp_file_path} deleted")
                except Exception as e:
                    logger.warning(f"Failed to delete temp file {temp_file_path}: {e}")
    
    @staticmethod
    async def _send_text_result(bot: Bot, user_id: int, message_text: str) -> bool:
        """Отправить текстовый результат"""
        try:
            await bot.send_message(
                chat_id=user_id,
                text=message_text,
                parse_mode=ParseMode.MARKDOWN
            )
            
            logger.info(f"Text result sent to user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send text result to user {user_id}: {e}")
            return False
    
    @staticmethod
    async def _download_file(file_url: str, file_name: Optional[str] = None) -> Optional[str]:
        """Скачать файл во временную папку"""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
                async with session.get(file_url) as response:
                    if response.status != 200:
                        logger.error(f"Failed to download file: HTTP {response.status}")
                        return None
                    
                    # Создаем временный файл
                    suffix = ""
                    if file_name:
                        suffix = Path(file_name).suffix
                    
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                        async for chunk in response.content.iter_chunked(8192):
                            temp_file.write(chunk)
                        
                        temp_file_path = temp_file.name
                    
                    logger.info(f"File downloaded to {temp_file_path}")
                    return temp_file_path
                    
        except Exception as e:
            logger.error(f"Failed to download file from {file_url}: {e}")
            return None
    
    @staticmethod
    async def notify_addinfo_completed(order: Order, wait_hours: int, session: Optional[AsyncSession] = None) -> bool:
        """Уведомить о завершении Add Info заказа через mirror bot пользователя"""
        try:
            # Получаем язык пользователя, если есть сессия
            user_language = "en"
            if session:
                user_language = await OrderDeliveryService.get_user_language(
                    session, order.user_id, order.mirror_bot_id
                )
            
            # Отправляем уведомление через HTTP API к mirror bot
            api_url = f"{os.getenv('MAIN_BOT_API_URL', 'http://main_bot:8080')}/api/notify-addinfo-completed"
            
            payload = {
                "user_id": order.user_id,
                "mirror_bot_id": order.mirror_bot_id,
                "order_id": order.id,
                "service_name": order.service_name,
                "wait_hours": wait_hours,
                "price": float(order.price),
                "user_language": user_language
            }
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
                async with session.post(
                    api_url,
                    json=payload,
                    headers=build_internal_api_headers(),
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        logger.info(f"Add Info notification sent successfully for order {order.id}")
                        return True
                    else:
                        logger.warning(f"Failed to send Add Info notification: HTTP {response.status}")
                        return False
            
        except Exception as e:
            logger.error(f"Failed to notify add info completion for order {order.id}: {e}")
            return False
    
    @staticmethod
    async def notify_bulk_item_completed(
        user_id: int,
        mirror_bot_id: int,
        order_id: int,
        item_number: int,
        service_name: str,
        result_status: str = "done",
        customer_data: Optional[Dict[str, Any]] = None,
        refund_amount: Optional[float] = None,
        files: Optional[list] = None,
        result_text: Optional[str] = None,
        user_language: Optional[str] = None
    ) -> bool:
        """
        Уведомить о завершении элемента bulk заказа через mirror bot пользователя
        
        Args:
            user_id: ID пользователя
            mirror_bot_id: ID mirror bot
            order_id: ID заказа
            item_number: Номер элемента
            service_name: Название сервиса
            result_status: "done" или "nf"
            customer_data: Данные клиента
            refund_amount: Сумма возврата (для NF)
            files: Список файлов
            result_text: Текстовый результат
        
        Returns:
            bool: Успешность отправки
        """
        try:
            # Отправляем уведомление через HTTP API к mirror bot
            api_url = f"{os.getenv('MAIN_BOT_API_URL', 'http://main_bot:8080')}/api/notify-bulk-item-completed"
            
            payload = {
                "user_id": user_id,
                "mirror_bot_id": mirror_bot_id,
                "order_id": order_id,
                "item_number": item_number,
                "service_name": service_name,
                "result_status": result_status,
                "customer_data": customer_data or {},
                "refund_amount": float(refund_amount) if refund_amount else None,
                "has_files": bool(files),
                "files": files or [],
                "result_text": result_text,
                "user_language": user_language or "en"
            }
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as client_session:
                async with client_session.post(
                    api_url,
                    json=payload,
                    headers=build_internal_api_headers(),
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        logger.info(f"Bulk item notification sent successfully for order {order_id} item {item_number}")
                        return True
                    else:
                        logger.warning(f"Failed to send bulk item notification: HTTP {response.status}")
                        return False
            
        except Exception as e:
            logger.error(f"Failed to notify bulk item completion for order {order_id} item {item_number}: {e}")
            return False
    
    @staticmethod
    async def notify_bulk_order_completed(
        session: AsyncSession,
        order: Order,
        summary: dict
    ) -> bool:
        """
        Уведомить о завершении всего bulk заказа через mirror bot пользователя
        
        Args:
            session: Сессия БД
            order: Заказ
            summary: Сводка {"done": X, "nf": Y, "total": Z}
        
        Returns:
            bool: Успешность отправки
        """
        try:
            # Отправляем уведомление через HTTP API к mirror bot
            api_url = f"{os.getenv('MAIN_BOT_API_URL', 'http://main_bot:8080')}/api/notify-bulk-order-completed"
            
            # Получаем язык пользователя
            user_language = await OrderDeliveryService.get_user_language(
                session, order.user_id, order.mirror_bot_id
            )
            
            # Собираем все файлы из bulk элементов
            all_files = []
            for item in order.bulk_items:
                if item.result_data and item.result_data.get("files"):
                    for file_info in item.result_data["files"]:
                        # Добавляем номер элемента и данные клиента к файлу
                        file_with_item = file_info.copy()
                        file_with_item["item_number"] = item.item_number
                        file_with_item["customer_data"] = item.input_data  # Данные клиента для caption
                        all_files.append(file_with_item)
            
            payload = {
                "user_id": order.user_id,
                "mirror_bot_id": order.mirror_bot_id,
                "order_id": order.id,
                "service_name": order.service_name,
                "summary": summary,
                "price_per_item": float(order.price / order.bulk_count),
                "user_language": user_language,
                "files": all_files  # Добавляем файлы
            }
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as client_session:
                async with client_session.post(
                    api_url,
                    json=payload,
                    headers=build_internal_api_headers(),
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        logger.info(f"Bulk order completion notification sent successfully for order {order.id}")
                        return True
                    else:
                        logger.warning(f"Failed to send bulk order completion notification: HTTP {response.status}")
                        return False
            
        except Exception as e:
            logger.error(f"Failed to notify bulk order completion for order {order.id}: {e}")
            return False
    
    @staticmethod
    async def deliver_single_order_result(
        user_id: int,
        mirror_bot_id: int,
        order_id: int,
        service_name: str,
        result_status: str = "done",
        customer_data: Optional[Dict[str, Any]] = None,
        refund_amount: Optional[float] = None,
        files: Optional[list] = None,
        result_text: Optional[str] = None,
        user_language: Optional[str] = None
    ) -> bool:
        """
        Доставить результат single заказа пользователю через HTTP API
        
        Args:
            user_id: ID пользователя
            mirror_bot_id: ID mirror bot
            order_id: ID заказа
            service_name: Название сервиса
            result_status: Статус результата (done/nf)
            customer_data: Данные клиента
            refund_amount: Сумма возврата (для NF)
            files: Список файлов
            result_text: Текстовый результат
        
        Returns:
            bool: Успешность доставки
        """
        try:
            # Отправляем уведомление через HTTP API к mirror bot
            api_url = f"{os.getenv('MAIN_BOT_API_URL', 'http://main_bot:8080')}/api/notify-single-order-completed"
            
            logger.info(f"Sending single order notification to {api_url} for order {order_id}")
            
            payload = {
                "user_id": user_id,
                "mirror_bot_id": mirror_bot_id,
                "order_id": order_id,
                "service_name": service_name,
                "result_status": result_status,
                "customer_data": customer_data or {},
                "refund_amount": float(refund_amount) if refund_amount else None,
                "has_files": bool(files),
                "files": files or [],
                "result_text": result_text,
                "user_language": user_language or "en"
            }
            
            logger.info(f"Payload: {payload}")
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as client_session:
                async with client_session.post(
                    api_url,
                    json=payload,
                    headers=build_internal_api_headers(),
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        logger.info(f"Single order notification sent successfully for order {order_id}")
                        return True
                    else:
                        response_text = await response.text()
                        logger.warning(f"Failed to send single order notification: HTTP {response.status}, Response: {response_text}")
                        return False
            
        except Exception as e:
            logger.error(f"Failed to deliver single order result for order {order_id}: {e}")
            return False
