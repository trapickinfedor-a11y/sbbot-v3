"""
Сервис для доставки товаров (Products) пользователям
Работает с файлами, загруженными на сервер через админ панель
"""

from aiogram import Bot
from aiogram.types import FSInputFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import os
import logging

from shared.database.models import Product, MirrorBot

logger = logging.getLogger(__name__)


class ProductDeliveryService:
    """Сервис для отправки товаров пользователям"""
    
    @staticmethod
    async def send_product_to_user(
        session: AsyncSession,
        user_id: int,
        product_id: int,
        mirror_bot_id: int
    ) -> bool:
        """
        Отправить товар пользователю через его Mirror Bot
        
        Args:
            session: Сессия БД
            user_id: ID пользователя
            product_id: ID товара
            mirror_bot_id: ID Mirror Bot пользователя
            
        Returns:
            bool: Успешно ли отправлен товар
        """
        
        # 1. Получить товар
        product_result = await session.execute(
            select(Product).where(Product.id == product_id)
        )
        product = product_result.scalar_one_or_none()
        
        if not product:
            logger.warning(f"Product {product_id} not found")
            return False
        
        if not product.file_path or not os.path.exists(product.file_path):
            logger.error(f"File not found for product {product_id}: {product.file_path}")
            return False
        
        # 2. Получить Mirror Bot
        mirror_bot_result = await session.execute(
            select(MirrorBot).where(MirrorBot.id == mirror_bot_id)
        )
        mirror_bot = mirror_bot_result.scalar_one_or_none()
        
        if not mirror_bot:
            logger.error(f"Mirror bot {mirror_bot_id} not found")
            return False
        
        # 3. Создать бота
        bot = Bot(token=mirror_bot.bot_token)
        
        try:
            # 4. Отправить файл
            file_type = product.file_type or "document"
            caption = f"📦 {product.name}\n\n{product.description or ''}"
            
            if file_type == "photo":
                await bot.send_photo(
                    chat_id=user_id,
                    photo=FSInputFile(product.file_path),
                    caption=caption
                )
            elif file_type == "video":
                await bot.send_video(
                    chat_id=user_id,
                    video=FSInputFile(product.file_path),
                    caption=caption
                )
            else:
                # document и всё остальное
                await bot.send_document(
                    chat_id=user_id,
                    document=FSInputFile(product.file_path),
                    caption=caption
                )
            
            logger.info(f"Product {product_id} sent to user {user_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to send product {product_id} to user {user_id}: {e}")
            return False
        
        finally:
            await bot.session.close()
    
    @staticmethod
    async def send_product_with_service_info(
        session: AsyncSession,
        user_id: int,
        product_id: int,
        mirror_bot_id: int,
        order_id: int = None
    ) -> bool:
        """
        Отправить товар с информацией о заказе/сервисе
        
        Args:
            session: Сессия БД
            user_id: ID пользователя
            product_id: ID товара
            mirror_bot_id: ID Mirror Bot пользователя
            order_id: ID заказа (опционально)
            
        Returns:
            bool: Успешно ли отправлен товар
        """
        
        # 1. Получить товар с сервисом
        product_result = await session.execute(
            select(Product).where(Product.id == product_id)
        )
        product = product_result.scalar_one_or_none()
        
        if not product:
            logger.warning(f"Product {product_id} not found")
            return False
        
        if not product.file_path or not os.path.exists(product.file_path):
            logger.error(f"File not found for product {product_id}: {product.file_path}")
            return False
        
        # 2. Получить Mirror Bot
        mirror_bot_result = await session.execute(
            select(MirrorBot).where(MirrorBot.id == mirror_bot_id)
        )
        mirror_bot = mirror_bot_result.scalar_one_or_none()
        
        if not mirror_bot:
            logger.error(f"Mirror bot {mirror_bot_id} not found")
            return False
        
        # 3. Создать бота
        bot = Bot(token=mirror_bot.bot_token)
        
        try:
            # 4. Отправить информационное сообщение
            from mirror_bot.constants.language_loader import get_texts
            temp_texts = get_texts('en')  # Fallback
            
            order_text = f" #{order_id}" if order_id else ""
            message_text = temp_texts.YOUR_ORDER_READY.format(order_text=order_text) + "\n\n"
            message_text += f"{temp_texts.PRODUCT_LABEL} {product.name}\n"
            message_text += f"{temp_texts.CATEGORY_LABEL} {product.category} / {product.subcategory}\n"
            
            if product.service:
                message_text += f"**Service:** {product.service.name}\n"
            
            message_text += f"\n{temp_texts.YOUR_FILE_ATTACHED_BELOW}"
            
            await bot.send_message(
                chat_id=user_id,
                text=message_text,
                parse_mode="Markdown"
            )
            
            # 5. Отправить файл
            file_type = product.file_type or "document"
            caption = f"📦 {product.name}"
            
            if product.file_name:
                caption += f" - {product.file_name}"
            
            if file_type == "photo":
                await bot.send_photo(
                    chat_id=user_id,
                    photo=FSInputFile(product.file_path),
                    caption=caption
                )
            elif file_type == "video":
                await bot.send_video(
                    chat_id=user_id,
                    video=FSInputFile(product.file_path),
                    caption=caption
                )
            else:
                # document и всё остальное
                await bot.send_document(
                    chat_id=user_id,
                    document=FSInputFile(product.file_path),
                    caption=caption
                )
            
            logger.info(f"Product {product_id} with service info sent to user {user_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to send product {product_id} with service info to user {user_id}: {e}")
            return False
        
        finally:
            await bot.session.close()
