"""
API endpoints для получения уведомлений от support_bot
"""

import logging
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.types import InputMediaPhoto, InputMediaDocument, BufferedInputFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from shared.database.session import get_session
from shared.database.models import MirrorBot, User
from shared.security.internal_api import verify_internal_api_request
from mirror_bot.services.user_service import UserService
from mirror_bot.constants.language_loader import LanguageLoader

logger = logging.getLogger(__name__)

app = FastAPI(dependencies=[Depends(verify_internal_api_request)])

class BulkItemNotificationData(BaseModel):
    user_id: int
    mirror_bot_id: int
    order_id: int
    item_number: int
    service_name: str
    result_status: str  # "done" или "nf"
    customer_data: Dict[str, Any]
    refund_amount: Optional[float] = None
    has_files: bool = False
    files: Optional[List[Dict[str, Any]]] = None
    result_text: Optional[str] = None
    user_language: str = "en"

class BulkOrderCompletionData(BaseModel):
    user_id: int
    mirror_bot_id: int
    order_id: int
    service_name: str
    summary: Dict[str, int]  # {"done": X, "nf": Y, "total": Z}
    price_per_item: float
    user_language: str = "en"
    files: List[Dict[str, Any]] = []  # Файлы из всех элементов

class SingleOrderNotificationData(BaseModel):
    user_id: int
    mirror_bot_id: int
    order_id: int
    service_name: str
    result_status: str  # "done" или "nf"
    customer_data: Dict[str, Any]
    refund_amount: Optional[float] = None
    has_files: bool = False
    files: Optional[List[Dict[str, Any]]] = None
    result_text: Optional[str] = None
    user_language: str = "en"

class AddInfoNotificationData(BaseModel):
    user_id: int
    mirror_bot_id: int
    order_id: int
    service_name: str
    wait_hours: int
    price: float
    user_language: str = "en"

class BalanceUpdateNotificationData(BaseModel):
    user_id: int
    mirror_bot_id: int
    amount: float
    reason: str
    user_language: str = "en"

class OrderCancellationData(BaseModel):
    user_id: int
    mirror_bot_id: int
    order_id: int
    service_name: str
    refund_amount: float
    reason: str = "cancelled"  # "cancelled", "invalid_data", "no_stock"
    user_language: str = "en"

async def get_db():
    """Получить сессию базы данных"""
    session_gen = get_session()
    session = await session_gen.__anext__()
    try:
        yield session
    finally:
        await session.close()

async def get_mirror_bot_instance(mirror_bot_id: int, session: AsyncSession) -> Bot:
    """Получить экземпляр mirror bot по ID"""
    result = await session.execute(
        select(MirrorBot).where(MirrorBot.id == mirror_bot_id)
    )
    mirror_bot = result.scalar_one_or_none()
    
    if not mirror_bot:
        raise HTTPException(status_code=404, detail="Mirror bot not found")
    
    return Bot(token=mirror_bot.bot_token)

async def get_user_language(session: AsyncSession, user_id: int, mirror_bot_id: int) -> str:
    """Получить язык пользователя"""
    try:
        user = await UserService.get_user(session, user_id, mirror_bot_id)
        return user.language if user and user.language else "en"
    except Exception:
        return "en"

def get_multilingual_texts(language: str):
    """Получить мультиязычные тексты для уведомлений"""
    try:
        if language == "ru":
            from mirror_bot.constants.texts_ru import BotTexts
            texts_class = BotTexts
        elif language == "zh":
            from mirror_bot.constants.texts_zh import BotTexts
            texts_class = BotTexts
        else:  # English default
            from mirror_bot.constants.texts_en import BotTexts
            texts_class = BotTexts
        
        # Извлекаем константы из класса
        ORDER_COMPLETED_BULK_ITEM = texts_class.ORDER_COMPLETED_BULK_ITEM
        ORDER_COMPLETED_SINGLE = texts_class.ORDER_COMPLETED_SINGLE
        ORDER_NOT_FOUND_BULK_ITEM = texts_class.ORDER_NOT_FOUND_BULK_ITEM
        ORDER_NOT_FOUND_SINGLE = texts_class.ORDER_NOT_FOUND_SINGLE
        BULK_ORDER_COMPLETED = texts_class.BULK_ORDER_COMPLETED
        ORDER_DETAILS = texts_class.ORDER_DETAILS
        SERVICE_TEXT = texts_class.SERVICE_TEXT
        STATUS_TEXT = texts_class.STATUS_TEXT
        ITEM_TEXT = texts_class.ITEM_TEXT
        FILES_TEXT = texts_class.FILES_TEXT
        BALANCE_TEXT = texts_class.BALANCE_TEXT
        REFUND_TEXT = texts_class.REFUND_TEXT
        RESULT_READY = texts_class.RESULT_READY
        ORDER_COMPLETE_THANKS = texts_class.ORDER_COMPLETE_THANKS
        NOT_FOUND_MESSAGE = texts_class.NOT_FOUND_MESSAGE
        REFUND_PROCESSED = texts_class.REFUND_PROCESSED
        FINAL_RESULTS = texts_class.FINAL_RESULTS
        ITEMS_FOUND_DELIVERED = texts_class.ITEMS_FOUND_DELIVERED
        ITEMS_NOT_FOUND_REFUNDED = texts_class.ITEMS_NOT_FOUND_REFUNDED
        SUMMARY_TEXT = texts_class.SUMMARY_TEXT
        ITEMS_FOUND = texts_class.ITEMS_FOUND
        ITEMS_REFUNDED = texts_class.ITEMS_REFUNDED
        CHECK_CHAT_HISTORY = texts_class.CHECK_CHAT_HISTORY
        CURRENT_BALANCE = texts_class.CURRENT_BALANCE
        THANK_YOU = texts_class.THANK_YOU
        ADD_INFO_PROCESSING_TITLE = texts_class.ADD_INFO_PROCESSING_TITLE
        ADD_INFO_STATUS_IN_PROGRESS = texts_class.ADD_INFO_STATUS_IN_PROGRESS
        ADD_INFO_PROCESSING_MESSAGE = texts_class.ADD_INFO_PROCESSING_MESSAGE
        ADD_INFO_NOTIFY_READY = texts_class.ADD_INFO_NOTIFY_READY
        ADD_INFO_COMPLETED_TITLE = texts_class.ADD_INFO_COMPLETED_TITLE
        ADD_INFO_COMPLETED_MESSAGE = texts_class.ADD_INFO_COMPLETED_MESSAGE
        # Новые константы для NF уведомлений
        DATA_NOT_FOUND_MESSAGE = texts_class.DATA_NOT_FOUND_MESSAGE
        REFUND_AMOUNT = texts_class.REFUND_AMOUNT
        ORDER_UPDATE = texts_class.ORDER_UPDATE
        ORDER_NUMBER = texts_class.ORDER_NUMBER
        SERVICE = texts_class.SERVICE
        CUSTOMER_DATA = texts_class.CUSTOMER_DATA
        RESULT = texts_class.RESULT
        DETAILS = texts_class.DETAILS
        THANK_YOU_FOR_ORDER = texts_class.THANK_YOU_FOR_ORDER
        ORDER_COMPLETED = texts_class.ORDER_COMPLETED_SINGLE  # Используем существующую константу
        ORDER_NOT_FOUND = getattr(texts_class, 'ORDER_NOT_FOUND', 'Order not found')
        
        return {
            'ORDER_COMPLETED_BULK_ITEM': ORDER_COMPLETED_BULK_ITEM,
            'ORDER_COMPLETED_SINGLE': ORDER_COMPLETED_SINGLE,
            'ORDER_NOT_FOUND_BULK_ITEM': ORDER_NOT_FOUND_BULK_ITEM,
            'ORDER_NOT_FOUND_SINGLE': ORDER_NOT_FOUND_SINGLE,
            'BULK_ORDER_COMPLETED': BULK_ORDER_COMPLETED,
            'ORDER_DETAILS': ORDER_DETAILS,
            'SERVICE_TEXT': SERVICE_TEXT,
            'STATUS_TEXT': STATUS_TEXT,
            'ITEM_TEXT': ITEM_TEXT,
            'FILES_TEXT': FILES_TEXT,
            'BALANCE_TEXT': BALANCE_TEXT,
            'REFUND_TEXT': REFUND_TEXT,
            'RESULT_READY': RESULT_READY,
            'ORDER_COMPLETE_THANKS': ORDER_COMPLETE_THANKS,
            'NOT_FOUND_MESSAGE': NOT_FOUND_MESSAGE,
            'REFUND_PROCESSED': REFUND_PROCESSED,
            'FINAL_RESULTS': FINAL_RESULTS,
            'ITEMS_FOUND_DELIVERED': ITEMS_FOUND_DELIVERED,
            'ITEMS_NOT_FOUND_REFUNDED': ITEMS_NOT_FOUND_REFUNDED,
            'SUMMARY_TEXT': SUMMARY_TEXT,
            'ITEMS_FOUND': ITEMS_FOUND,
            'ITEMS_REFUNDED': ITEMS_REFUNDED,
            'CHECK_CHAT_HISTORY': CHECK_CHAT_HISTORY,
            'CURRENT_BALANCE': CURRENT_BALANCE,
            'THANK_YOU': THANK_YOU,
            'ADD_INFO_PROCESSING_TITLE': ADD_INFO_PROCESSING_TITLE,
            'ADD_INFO_STATUS_IN_PROGRESS': ADD_INFO_STATUS_IN_PROGRESS,
            'ADD_INFO_PROCESSING_MESSAGE': ADD_INFO_PROCESSING_MESSAGE,
            'ADD_INFO_NOTIFY_READY': ADD_INFO_NOTIFY_READY,
            'ADD_INFO_COMPLETED_TITLE': ADD_INFO_COMPLETED_TITLE,
            'ADD_INFO_COMPLETED_MESSAGE': ADD_INFO_COMPLETED_MESSAGE,
            # Новые константы
            'DATA_NOT_FOUND_MESSAGE': DATA_NOT_FOUND_MESSAGE,
            'REFUND_AMOUNT': REFUND_AMOUNT,
            'ORDER_UPDATE': ORDER_UPDATE,
            'ORDER_NUMBER': ORDER_NUMBER,
            'SERVICE': SERVICE,
            'CUSTOMER_DATA': CUSTOMER_DATA,
            'RESULT': RESULT,
            'DETAILS': DETAILS,
            'THANK_YOU_FOR_ORDER': THANK_YOU_FOR_ORDER,
            'ORDER_COMPLETED': ORDER_COMPLETED,
            'ORDER_NOT_FOUND': ORDER_NOT_FOUND
        }
    except ImportError as e:
        # Fallback к базовым значениям
        return {
            'ORDER_COMPLETED_BULK_ITEM': '✅ Your bulk order item completed!',
            'ORDER_COMPLETED_SINGLE': '✅ Your order completed!',
            'ORDER_NOT_FOUND_BULK_ITEM': '❌ Your bulk order item - NOT FOUND',
            'ORDER_NOT_FOUND_SINGLE': '❌ Your order - NOT FOUND',
            'BULK_ORDER_COMPLETED': '🎯 Your bulk order completed!',
            'ORDER_DETAILS': '📋 Order Details:',
            'SERVICE_TEXT': 'Service:',
            'STATUS_TEXT': 'Status:',
            'ITEM_TEXT': 'Item:',
            'FILES_TEXT': 'Files:',
            'BALANCE_TEXT': 'Balance:',
            'REFUND_TEXT': 'Refund:',
            'RESULT_READY': 'Result ready!',
            'ORDER_COMPLETE_THANKS': 'Thank you for your order!',
            'NOT_FOUND_MESSAGE': 'Not found',
            'REFUND_PROCESSED': 'Refund processed',
            'FINAL_RESULTS': 'Final results',
            'ITEMS_FOUND_DELIVERED': 'Items found and delivered',
            'ITEMS_NOT_FOUND_REFUNDED': 'Items not found, refunded',
            'SUMMARY_TEXT': 'Summary',
            'ITEMS_FOUND': 'Items found',
            'ITEMS_REFUNDED': 'Items refunded',
            'CHECK_CHAT_HISTORY': 'Check chat history',
            'CURRENT_BALANCE': 'Current balance',
            'THANK_YOU': 'Thank you!',
            'ADD_INFO_PROCESSING_TITLE': 'Processing Add Info',
            'ADD_INFO_STATUS_IN_PROGRESS': 'In Progress',
            'ADD_INFO_PROCESSING_MESSAGE': 'Processing will take up to {hours} hours',
            'ADD_INFO_NOTIFY_READY': 'You will be notified when ready',
            'ADD_INFO_COMPLETED_TITLE': 'Add Info Completed',
            'ADD_INFO_COMPLETED_MESSAGE': 'Your add info order has been completed',
            'DATA_NOT_FOUND_MESSAGE': 'Unfortunately, we couldn\'t find the requested information.\nYour balance has been refunded automatically.',
            'REFUND_AMOUNT': 'Refund amount',
            'ORDER_UPDATE': 'Order Update',
            'ORDER_NUMBER': 'Order',
            'SERVICE': 'Service',
            'CUSTOMER_DATA': 'Customer Data',
            'RESULT': 'Result',
            'DETAILS': 'Details',
            'THANK_YOU_FOR_ORDER': 'Thank you for your order! 🙏',
            'ORDER_COMPLETED': '✅ Your order completed!',
            'ORDER_NOT_FOUND': '❌ Order not found'
        }

def get_service_name_multilingual(service_name: str, language: str) -> str:
    """Получить название сервиса на нужном языке используя ProductTranslations"""
    try:
        from mirror_bot.utils.product_translations import ProductTranslations

        # Используем централизованный сервис переводов
        return ProductTranslations.get_service_name(service_name, language)
    except Exception as e:
        logger.error(f"Failed to get service name translation: {e}")
        # Fallback: возвращаем оригинальное имя
        return service_name

def format_customer_data(customer_data: Dict[str, Any]) -> str:
    """Форматировать данные клиента для отображения"""
    if not customer_data:
        return ""
    
    data_lines = []
    for key, value in customer_data.items():
        if key not in ['item_number'] and value:
            formatted_key = key.replace('_', ' ').title()
            data_lines.append(f"<b>{formatted_key}:</b> {value}")
    
    if data_lines:
        return f"\n\n<b>Your data:</b>\n" + "\n".join(data_lines)
    return ""


def _compose_delivery_caption(base_caption: Optional[str], file_caption: Optional[str]) -> Optional[str]:
    base = (base_caption or "").strip()
    note = (file_caption or "").strip()
    if base and note:
        return f"{base}\n\n📝 <b>Worker note:</b>\n{note}"
    return base or note or None

async def send_files_in_groups(bot: Bot, user_id: int, files: List[Dict[str, Any]], order_id: int, item_number: int = None, caption_text: str = None) -> dict:
    """
    Отправить файлы группами через скачивание и переотправку.

    Returns:
        dict with keys: sent (int), failed (int), errors (list[str])
    """
    result = {"sent": 0, "failed": 0, "errors": []}
    if not files:
        return result

    import os
    import asyncio
    support_bot_token = os.getenv("SUPPORT_BOT_TOKEN")
    if not support_bot_token:
        logger.error("SUPPORT_BOT_TOKEN not found in environment")
        result["errors"].append("SUPPORT_BOT_TOKEN not configured")
        return result

    support_bot = Bot(token=support_bot_token)

    try:
        logger.info(f"Starting to send {len(files)} files to user {user_id} for order {order_id}")

        for i, file_info in enumerate(files, 1):
            file_label = file_info.get('file_name', f'file_{i}')
            sent_ok = False
            last_error = ""

            for attempt in range(2):
                try:
                    file_obj = await support_bot.get_file(file_info["file_id"])
                    file_bytes = await support_bot.download_file(file_obj.file_path)
                    data_bytes = file_bytes.getvalue()
                    logger.info(f"Downloaded {file_label}, size: {len(data_bytes)} bytes (attempt {attempt+1})")

                    if len(data_bytes) == 0:
                        last_error = "File is empty (0 bytes)"
                        logger.warning(f"Empty file {file_label} for order {order_id}")
                        break

                    file_item_num = file_info.get("item_number")
                    customer_data = file_info.get("customer_data", {})
                    file_caption = file_info.get("caption")

                    if file_item_num and customer_data:
                        customer_info = format_customer_data(customer_data)
                        caption = _compose_delivery_caption(
                            f"📄 <b>Your Result - Item #{file_item_num}</b>\n\n{customer_info}",
                            file_caption,
                        )
                    elif caption_text and i == 1:
                        caption = _compose_delivery_caption(caption_text, file_caption)
                    else:
                        caption = _compose_delivery_caption(
                            f"📄 <b>Your Result</b>\n\n<b>File {i}/{len(files)}</b>",
                            file_caption,
                        )

                    file_name = file_info.get('file_name', f'file_{i}')
                    file_type = file_info.get("type", "document")

                    if file_type == "photo":
                        await bot.send_photo(
                            chat_id=user_id,
                            photo=BufferedInputFile(data_bytes, filename=file_name or f"photo_{i}.jpg"),
                            caption=caption, parse_mode="HTML",
                        )
                    elif file_type == "video":
                        await bot.send_video(
                            chat_id=user_id,
                            video=BufferedInputFile(data_bytes, filename=file_name or f"video_{i}.mp4"),
                            caption=caption, parse_mode="HTML",
                        )
                    elif file_type == "audio":
                        await bot.send_audio(
                            chat_id=user_id,
                            audio=BufferedInputFile(data_bytes, filename=file_name or f"audio_{i}.mp3"),
                            caption=caption, parse_mode="HTML",
                        )
                    elif file_type == "voice":
                        await bot.send_voice(
                            chat_id=user_id,
                            voice=BufferedInputFile(data_bytes, filename=file_name or f"voice_{i}.ogg"),
                            caption=caption, parse_mode="HTML",
                        )
                    elif file_type == "video_note":
                        await bot.send_video_note(
                            chat_id=user_id,
                            video_note=BufferedInputFile(data_bytes, filename=file_name or f"video_note_{i}.mp4"),
                        )
                    else:
                        await bot.send_document(
                            chat_id=user_id,
                            document=BufferedInputFile(data_bytes, filename=file_name or f"document_{i}"),
                            caption=caption, parse_mode="HTML",
                        )

                    sent_ok = True
                    result["sent"] += 1
                    logger.info(f"Delivered file {i}/{len(files)} ({file_label}) for order {order_id}")
                    break

                except Exception as file_error:
                    last_error = str(file_error)
                    logger.warning(f"Attempt {attempt+1} failed for {file_label}: {file_error}")
                    if attempt == 0:
                        await asyncio.sleep(1)

            if not sent_ok:
                result["failed"] += 1
                result["errors"].append(f"{file_label}: {last_error}")
                logger.error(f"Failed to deliver file {file_label} for order {order_id} after retries")
                try:
                    await bot.send_message(
                        chat_id=user_id,
                        text=f"❌ <b>File Error</b>\n\nCouldn't deliver file: {file_label}\n\nPlease contact support.",
                        parse_mode="HTML",
                    )
                except Exception:
                    pass

    finally:
        await support_bot.session.close()

    logger.info(f"Delivery summary for order {order_id}: sent={result['sent']}, failed={result['failed']}")
    return result

@app.post("/notify-bulk-item-completed")
async def notify_bulk_item_completed(
    data: BulkItemNotificationData,
    session: AsyncSession = Depends(get_db)
):
    """Notify user about bulk item completion"""
    bot = None
    try:
        bot = await get_mirror_bot_instance(data.mirror_bot_id, session)
        user_language = await get_user_language(session, data.user_id, data.mirror_bot_id)
        
        # Получаем мультиязычные тексты
        texts = get_multilingual_texts(user_language)
        
        # Получаем баланс пользователя
        user = await UserService.get_user(session, data.user_id, data.mirror_bot_id)
        user_balance = user.balance if user else 0.00
        
        # Получаем название сервиса на нужном языке
        service_name_localized = get_service_name_multilingual(data.service_name, user_language)
        
        # Форматируем данные клиента
        customer_data_text = format_customer_data(data.customer_data)
        
        if data.result_status == "done":
            # Успешное завершение - отправляем детальное сообщение с информацией
            text = f"""✅ <b>{texts['ORDER_COMPLETED_BULK_ITEM']}</b>

<b>{texts['ORDER_DETAILS']}</b>
• <b>{texts['SERVICE_TEXT']}</b> {service_name_localized}
• <b>{texts['STATUS_TEXT']}</b> ✅ DONE{customer_data_text}

<b>{texts['FILES_TEXT']}</b> {len(data.files) if data.files else 0} file(s) attached below
<b>{texts['BALANCE_TEXT']}</b> ${user_balance:.2f}

━━━━━━━━━━━━━━━━━━
{texts['RESULT_READY']}"""
            
            # Если есть файлы, отправляем их с полным описанием в caption
            if data.has_files and data.files:
                delivery = await send_files_in_groups(
                    bot=bot,
                    user_id=data.user_id,
                    files=data.files,
                    order_id=data.order_id,
                    item_number=data.item_number,
                    caption_text=text,
                )
                if delivery["failed"] > 0:
                    logger.warning(
                        f"Bulk item {data.order_id}#{data.item_number}: {delivery['failed']} file(s) failed: {delivery['errors']}"
                    )
            elif hasattr(data, 'result_text') and data.result_text:
                # Если есть текстовый результат, добавляем его к сообщению
                text_with_result = f"""{text}

📝 <b>Result:</b>
{data.result_text}"""
                await bot.send_message(
                    chat_id=data.user_id,
                    text=text_with_result,
                    parse_mode=ParseMode.HTML
                )
            else:
                # Если файлов нет, отправляем обычное сообщение
                await bot.send_message(
                    chat_id=data.user_id,
                    text=text,
                    parse_mode=ParseMode.HTML
                )
        
        elif data.result_status == "nf":
            # Не найдено - отправляем детальное сообщение с информацией
            text = f"""❌ <b>{texts['ORDER_NOT_FOUND_BULK_ITEM']}</b>

<b>{texts['ORDER_DETAILS']}</b>
• <b>{texts['SERVICE_TEXT']}</b> {service_name_localized}
• <b>{texts['STATUS_TEXT']}</b> ❌ NOT FOUND{customer_data_text}

<b>{texts['REFUND_TEXT']}</b> ${data.refund_amount:.2f} returned to your balance
<b>{texts['BALANCE_TEXT']}</b> ${user_balance:.2f}

━━━━━━━━━━━━━━━━━━
{texts['NOT_FOUND_MESSAGE']}"""
            
            await bot.send_message(
                chat_id=data.user_id,
                text=text,
                parse_mode=ParseMode.HTML
            )
        
        await bot.session.close()
        logger.info(f"Bulk item notification sent for order {data.order_id} item {data.item_number}")

        return {"status": "success"}

    except Exception as e:
        logger.error(f"Failed to send bulk item notification: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if bot is not None:
            try:
                await bot.session.close()
            except Exception:
                pass

@app.post("/notify-bulk-order-completed")
async def notify_bulk_order_completed(
    data: BulkOrderCompletionData,
    session: AsyncSession = Depends(get_db)
):
    """Notify user about bulk order completion"""
    bot = None
    try:
        bot = await get_mirror_bot_instance(data.mirror_bot_id, session)
        user_language = await get_user_language(session, data.user_id, data.mirror_bot_id)
        
        # Получаем мультиязычные тексты
        texts = get_multilingual_texts(user_language)
        
        # Получаем баланс пользователя
        user = await UserService.get_user(session, data.user_id, data.mirror_bot_id)
        user_balance = user.balance if user else 0.00
        
        # Получаем название сервиса на нужном языке
        service_name_localized = get_service_name_multilingual(data.service_name, user_language)
        
        # Рассчитываем общую сумму возврата
        total_refund = data.summary['nf'] * data.price_per_item
        
        text = f"""🎯 <b>{texts['BULK_ORDER_COMPLETED']}</b>

<b>{texts['ORDER_DETAILS']}</b>
• <b>{texts['SERVICE_TEXT']}</b> {service_name_localized}
• <b>{texts['STATUS_TEXT']}</b> ✅ COMPLETED

{texts['FINAL_RESULTS']}
• <b>{texts['ITEMS_FOUND_DELIVERED']}</b> {data.summary['done']}
• <b>{texts['ITEMS_NOT_FOUND_REFUNDED']}</b> {data.summary['nf']}

{texts['SUMMARY_TEXT']}
• <b>{texts['ITEMS_FOUND']}</b> {data.summary['done']}
• <b>{texts['ITEMS_REFUNDED']}</b> {data.summary['nf']} (${total_refund:.2f})
• <b>{texts['CURRENT_BALANCE']}</b> ${user_balance:.2f}

━━━━━━━━━━━━━━━━━━
{texts['CHECK_CHAT_HISTORY']}

{texts['THANK_YOU']}"""
        
        await bot.send_message(
            chat_id=data.user_id,
            text=text,
            parse_mode=ParseMode.HTML
        )
        
        if data.files:
            logger.info(f"Sending {len(data.files)} files for bulk order {data.order_id}")
            delivery = await send_files_in_groups(bot, data.user_id, data.files, data.order_id)
            if delivery["failed"] > 0:
                logger.warning(
                    f"Bulk order {data.order_id} completion: {delivery['failed']} file(s) failed: {delivery['errors']}"
                )
        
        # Отправляем кнопку "Заказать ещё"
        try:
            from mirror_bot.keyboards.inline import reorder_keyboard
            await bot.send_message(
                chat_id=data.user_id,
                text="⬇️",
                reply_markup=reorder_keyboard(data.service_name, user_language),
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logger.warning(f"Failed to send reorder button: {e}")
        
        await bot.session.close()
        logger.info(f"Bulk order completion notification sent for order {data.order_id}")

        return {"status": "success"}

    except Exception as e:
        logger.error(f"Failed to send bulk order completion notification: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if bot is not None:
            try:
                await bot.session.close()
            except Exception:
                pass

@app.post("/notify-single-order-completed")
async def notify_single_order_completed(
    data: SingleOrderNotificationData,
    session: AsyncSession = Depends(get_db)
):
    """Notify user about single order completion"""
    bot = None
    try:
        bot = await get_mirror_bot_instance(data.mirror_bot_id, session)
        user_language = await get_user_language(session, data.user_id, data.mirror_bot_id)
        
        # Получаем мультиязычные тексты
        texts = get_multilingual_texts(user_language)
        
        # Получаем баланс пользователя
        user = await UserService.get_user(session, data.user_id, data.mirror_bot_id)
        user_balance = user.balance if user else 0.00
        
        # Получаем название сервиса на нужном языке
        service_name_localized = get_service_name_multilingual(data.service_name, user_language)
        
        # Форматируем данные клиента
        customer_data_text = format_customer_data(data.customer_data)
        
        if data.result_status == "done":
            # Успешное завершение
            text = f"""<b>{texts['ORDER_COMPLETED_SINGLE']}</b>

<b>{texts['ORDER_DETAILS']}</b>
• <b>{texts['SERVICE_TEXT']}</b> {service_name_localized}
• <b>{texts['STATUS_TEXT']}</b> ✅ DONE{customer_data_text}

<b>{texts['FILES_TEXT']}</b> {len(data.files) if data.files else 0} file(s) attached below
<b>{texts['BALANCE_TEXT']}</b> ${user_balance:.2f}

━━━━━━━━━━━━━━━━━━
{texts['ORDER_COMPLETE_THANKS']}
"""
            
            if data.has_files and data.files:
                delivery = await send_files_in_groups(
                    bot=bot,
                    user_id=data.user_id,
                    files=data.files,
                    order_id=data.order_id,
                    caption_text=text,
                )
                if delivery["failed"] > 0:
                    logger.warning(
                        f"Order {data.order_id}: {delivery['failed']} file(s) failed to deliver: {delivery['errors']}"
                    )
            elif hasattr(data, 'result_text') and data.result_text:
                # Если есть текстовый результат, добавляем его к сообщению
                text_with_result = f"""{text}

📝 <b>Result:</b>
{data.result_text}"""
                await bot.send_message(
                    chat_id=data.user_id,
                    text=text_with_result,
                    parse_mode=ParseMode.HTML
                )
            else:
                # Если файлов нет, отправляем обычное сообщение
                await bot.send_message(
                    chat_id=data.user_id,
                    text=text,
                    parse_mode=ParseMode.HTML
                )
        
        elif data.result_status == "nf":
            # Не найдено
            text = f"""❌ <b>{texts['ORDER_NOT_FOUND_SINGLE']}</b>

<b>{texts['ORDER_DETAILS']}</b>
• <b>{texts['SERVICE_TEXT']}</b> {service_name_localized}
• <b>{texts['STATUS_TEXT']}</b> ❌ NOT FOUND{customer_data_text}

<b>{texts['REFUND_TEXT']}</b> ${data.refund_amount:.2f} returned to your balance
<b>{texts['BALANCE_TEXT']}</b> ${user_balance:.2f}

━━━━━━━━━━━━━━━━━━
{texts['REFUND_PROCESSED']}
"""
            
            await bot.send_message(
                chat_id=data.user_id,
                text=text,
                parse_mode=ParseMode.HTML
            )
        
        # Отправляем кнопку "Заказать ещё"
        try:
            from mirror_bot.keyboards.inline import reorder_keyboard
            await bot.send_message(
                chat_id=data.user_id,
                text="⬇️",
                reply_markup=reorder_keyboard(data.service_name, user_language),
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logger.warning(f"Failed to send reorder button: {e}")
        
        await bot.session.close()
        logger.info(f"Single order notification sent for order {data.order_id}")

        return {"status": "success"}

    except Exception as e:
        logger.error(f"Failed to send single order notification: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if bot is not None:
            try:
                await bot.session.close()
            except Exception:
                pass

@app.post("/notify-addinfo-completed")
async def notify_addinfo_completed(
    data: AddInfoNotificationData,
    session: AsyncSession = Depends(get_db)
):
    """Notify user about Add Info order completion"""
    bot = None
    try:
        bot = await get_mirror_bot_instance(data.mirror_bot_id, session)
        user_language = await get_user_language(session, data.user_id, data.mirror_bot_id)
        
        # Получаем мультиязычные тексты
        texts = get_multilingual_texts(user_language)
        
        # Получаем баланс пользователя
        user = await UserService.get_user(session, data.user_id, data.mirror_bot_id)
        user_balance = user.balance if user else 0.00
        
        # Получаем название сервиса на нужном языке
        service_name_localized = get_service_name_multilingual(data.service_name, user_language)
        
        text = f"""⏰ <b>{texts['ADD_INFO_PROCESSING_TITLE']}</b>

<b>{texts['SERVICE_TEXT']}</b> {service_name_localized}
<b>{texts['STATUS_TEXT']}</b> {texts['ADD_INFO_STATUS_IN_PROGRESS']}

{texts['ADD_INFO_PROCESSING_MESSAGE'].format(hours=data.wait_hours)}

{texts['ADD_INFO_NOTIFY_READY']}

{texts['CURRENT_BALANCE']} <b>${user_balance:.2f}</b>"""
        
        await bot.send_message(
            chat_id=data.user_id,
            text=text,
            parse_mode=ParseMode.HTML
        )
        
        await bot.session.close()
        logger.info(f"Add Info notification sent for order {data.order_id}")

        return {"status": "success"}

    except Exception as e:
        logger.error(f"Failed to send Add Info notification: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if bot is not None:
            try:
                await bot.session.close()
            except Exception:
                pass

@app.post("/notify-balance-update")
async def notify_balance_update(
    data: BalanceUpdateNotificationData,
    session: AsyncSession = Depends(get_db)
):
    """Notify user about balance update"""
    bot = None
    try:
        bot = await get_mirror_bot_instance(data.mirror_bot_id, session)
        
        # Получаем мультиязычные тексты
        texts = LanguageLoader.get_texts(data.user_language)
        
        # Получаем текущий баланс пользователя
        user = await UserService.get_user(session, data.user_id, data.mirror_bot_id)
        current_balance = user.balance if user else 0.00
        
        # Формируем сообщение на языке пользователя
        if data.amount > 0:
            text = f"💰 <b>{texts.BALANCE_UPDATED}</b>\n\n"
            text += f"✅ {texts.BALANCE_ADDED}: ${data.amount:.2f}\n"
        else:
            text = f"💰 <b>{texts.BALANCE_UPDATED}</b>\n\n"
            text += f"❌ {texts.BALANCE_DEDUCTED}: ${abs(data.amount):.2f}\n"
        
        text += f"{texts.REASON}: {data.reason}\n"
        text += f"{texts.CURRENT_BALANCE}: <b>${current_balance:.2f}</b>\n\n"
        text += texts.CONTACT_SUPPORT_IF_QUESTIONS
        
        await bot.send_message(
            chat_id=data.user_id,
            text=text,
            parse_mode=ParseMode.HTML
        )
        
        await bot.session.close()
        logger.info(f"Balance update notification sent to user {data.user_id}")

        return {"status": "success"}

    except Exception as e:
        logger.error(f"Failed to send balance update notification: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if bot is not None:
            try:
                await bot.session.close()
            except Exception:
                pass


@app.post("/notify-order-cancelled")
async def notify_order_cancelled(
    data: OrderCancellationData,
    session: AsyncSession = Depends(get_db)
):
    """Notify user about order cancellation"""
    bot = None
    try:
        bot = await get_mirror_bot_instance(data.mirror_bot_id, session)
        
        # Получаем мультиязычные тексты
        texts = LanguageLoader.get_texts(data.user_language)
        
        # Получаем баланс пользователя
        user = await UserService.get_user(session, data.user_id, data.mirror_bot_id)
        user_balance = user.balance if user else 0.00
        
        # Получаем название сервиса на нужном языке
        from mirror_bot.utils.product_translations import ProductTranslations
        service_name_localized = ProductTranslations.get_service_name(data.service_name, data.user_language)
        
        # Формируем сообщение
        message = f"<b>{texts.ORDER_CANCELLED_TITLE}</b>\n\n"
        message += texts.ORDER_CANCELLED_MESSAGE.format(order_id=data.order_id) + "\n"
        message += texts.ORDER_CANCELLED_SERVICE.format(service=service_name_localized) + "\n\n"
        
        # Добавляем причину отмены
        if data.reason == "invalid_data":
            message += f"📝 {texts.ORDER_CANCELLED_INVALID_DATA}\n\n"
        elif data.reason == "no_stock":
            message += f"📝 {texts.ORDER_CANCELLED_NO_STOCK}\n\n"
        
        # Информация о возврате
        message += texts.ORDER_CANCELLED_REFUND.format(amount=data.refund_amount) + "\n"
        message += texts.ORDER_CANCELLED_BALANCE.format(balance=user_balance) + "\n\n"
        message += f"ℹ️ {texts.ORDER_CANCELLED_SUPPORT}"
        
        # Отправляем сообщение
        await bot.send_message(
            chat_id=data.user_id,
            text=message,
            parse_mode=ParseMode.HTML
        )
        
        await bot.session.close()
        logger.info(f"Order cancellation notification sent to user {data.user_id}")

        return {"status": "success"}

    except Exception as e:
        logger.error(f"Failed to send order cancellation notification: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if bot is not None:
            try:
                await bot.session.close()
            except Exception:
                pass