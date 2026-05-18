from __future__ import annotations

"""
Хэндлеры для работы с файлами в результатах заказов
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from support_bot.services.worker_service import WorkerService
from support_bot.services.order_service import OrderService
from support_bot.services.notification_service import NotificationService
from support_bot.services.order_delivery_service import OrderDeliveryService
from support_bot.services.support_logger import SupportLogger
from support_bot.keyboards.inline import main_menu_keyboard
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from shared.utils.chat_filter import filter_and_log, filter_message, is_message_blocked

router = Router(name="files")
logger = logging.getLogger(__name__)


class FileStates(StatesGroup):
    """Состояния для работы с файлами"""
    waiting_for_file = State()
    waiting_for_info = State()


def file_upload_keyboard(order_id: int, item_number: int = None) -> InlineKeyboardMarkup:
    """Клавиатура для загрузки файлов с кнопкой отмены"""
    if item_number:
        # Для bulk заказа - возврат к элементу
        back_callback = f"bulk_item:{order_id}:{item_number}"
    else:
        # Для single заказа - возврат к заказу
        back_callback = f"order_view:{order_id}"
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancel Upload", callback_data=f"cancel_upload:{order_id}:{item_number or 0}")]
    ])


@router.callback_query(F.data.startswith("order_send_file:"))
async def request_file(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    """Запрос на отправку файла с результатами"""
    
    order_id = int(callback.data.split(":")[1])
    
    worker = await WorkerService.get_worker(session, callback.from_user.id)
    order = await OrderService.get_order(session, order_id)
    
    if not order or order.worker_id != worker.id:
        await callback.answer("Access denied", show_alert=True)
        return
    
    # Сохраняем order_id в state
    await state.update_data(order_id=order_id)
    await state.set_state(FileStates.waiting_for_file)
    
    await callback.message.edit_text(
        f"📎 <b>Upload File - Order #{order_id}</b>\n\n"
        f"Please send the result file:\n"
        f"• Document (.txt, .pdf, .zip, etc.)\n"
        f"• Photo (screenshot)\n\n"
        f"You can send multiple files if needed.\n"
        f"When done, send /done",
        reply_markup=file_upload_keyboard(order_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("bulk_done_files:"))
async def request_bulk_file(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    """Запрос на отправку файла для bulk заказа"""
    
    parts = callback.data.split(":")
    order_id = int(parts[1])
    item_number = int(parts[2])
    
    worker = await WorkerService.get_worker(session, callback.from_user.id)
    order = await OrderService.get_order(session, order_id)
    
    if not order or order.worker_id != worker.id:
        await callback.answer("Access denied", show_alert=True)
        return
    
    # Сохраняем order_id и item_number в state
    await state.update_data(order_id=order_id, item_number=item_number, is_bulk=True)
    await state.set_state(FileStates.waiting_for_file)
    
    await callback.message.edit_text(
        f"📎 <b>Upload File - Order #{order_id} Item #{item_number}</b>\n\n"
        f"Please send the result file for item #{item_number}:\n"
        f"• Document (.txt, .pdf, .zip, etc.)\n"
        f"• Photo (screenshot)\n\n"
        f"You can send multiple files if needed.\n"
        f"When done, send /done",
        reply_markup=file_upload_keyboard(order_id, item_number)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cancel_upload:"))
async def cancel_file_upload(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    """Отмена загрузки файла"""
    
    parts = callback.data.split(":")
    order_id = int(parts[1])
    item_number = int(parts[2]) if parts[2] != "0" else None
    
    # Очищаем состояние
    await state.clear()
    
    from support_bot.handlers.orders import show_order_details
    await show_order_details(callback, session, order_id)
    await callback.answer("❌ File upload cancelled")


@router.message(FileStates.waiting_for_file, F.document | F.photo | F.video | F.audio | F.voice | F.video_note)
async def receive_file(message: Message, session: AsyncSession, state: FSMContext):
    """Получение файла от саппорта"""
    
    try:
        data = await state.get_data()
        order_id = data.get("order_id")
        item_number = data.get("item_number")
        is_bulk = data.get("is_bulk", False)
        
        logger.info(f"Receiving file for order {order_id}, item {item_number}, is_bulk: {is_bulk}")
        
        if not order_id:
            await message.answer("❌ Error: Order not found")
            await state.clear()
            return
        
        worker = await WorkerService.get_worker(session, message.from_user.id)
        order = await OrderService.get_order(session, order_id)
        
        if not order or order.worker_id != worker.id:
            await message.answer("❌ Access denied")
            await state.clear()
            return

        caption_text = (message.caption or "").strip()
        if caption_text and is_message_blocked(caption_text):
            await message.answer("❌ Caption contains only contact information and was blocked.")
            return
        if caption_text:
            caption_text, violated = await filter_and_log(
                text=caption_text,
                worker_id=worker.id,
                order_id=order.id,
                session=session,
            )
        else:
            violated = False
        
        raw_media_name = ""
        if message.document:
            raw_media_name = message.document.file_name or ""
        elif message.video:
            raw_media_name = message.video.file_name or ""
        elif message.audio:
            raw_media_name = message.audio.file_name or ""

        if raw_media_name:
            _, file_name_violated = await filter_and_log(
                text=raw_media_name,
                worker_id=worker.id,
                order_id=order.id,
                session=session,
            )
        else:
            file_name_violated = False

        if file_name_violated:
            await message.answer("❌ File name contains contact information and was blocked.")
            return

        # Подготавливаем информацию о файле
        if message.document:
            file_info = {
                "file_id": message.document.file_id,
                "file_name": message.document.file_name or "document",
                "file_size": message.document.file_size,
                "mime_type": message.document.mime_type,
                "type": "document",
                "caption": caption_text or None,
            }
            logger.info(f"Received document: {message.document.file_name}, mime_type: {message.document.mime_type}")
        elif message.photo:
            photo = message.photo[-1]  # Берем самое большое фото
            file_info = {
                "file_id": photo.file_id,
                "file_size": photo.file_size,
                "type": "photo",
                "file_name": f"photo_{photo.file_id[:8]}.jpg",
                "caption": caption_text or None,
            }
            logger.info(f"Received photo: {photo.file_id}")
        elif message.video:
            file_info = {
                "file_id": message.video.file_id,
                "file_name": message.video.file_name or f"video_{message.video.file_id[:8]}.mp4",
                "file_size": message.video.file_size,
                "mime_type": message.video.mime_type,
                "type": "video",
                "caption": caption_text or None,
            }
            logger.info(f"Received video: {message.video.file_name}")
        elif message.audio:
            file_info = {
                "file_id": message.audio.file_id,
                "file_name": message.audio.file_name or f"audio_{message.audio.file_id[:8]}.mp3",
                "file_size": message.audio.file_size,
                "mime_type": message.audio.mime_type,
                "type": "audio",
                "caption": caption_text or None,
            }
            logger.info(f"Received audio: {message.audio.file_name}")
        elif message.voice:
            file_info = {
                "file_id": message.voice.file_id,
                "file_name": f"voice_{message.voice.file_id[:8]}.ogg",
                "file_size": message.voice.file_size,
                "mime_type": message.voice.mime_type,
                "type": "voice",
                "caption": caption_text or None,
            }
            logger.info(f"Received voice message")
        elif message.video_note:
            file_info = {
                "file_id": message.video_note.file_id,
                "file_name": f"video_note_{message.video_note.file_id[:8]}.mp4",
                "file_size": message.video_note.file_size,
                "type": "video_note",
                "caption": caption_text or None,
            }
            logger.info(f"Received video note")
        else:
            await message.answer("❌ Unsupported file type")
            return
        
        if is_bulk and item_number:
            # Для bulk заказа - сохраняем файл для конкретного элемента
            logger.info(f"Looking for bulk item {item_number} in {len(order.bulk_items)} bulk items")
            bulk_item = next((item for item in order.bulk_items if item.item_number == item_number), None)
            if bulk_item:
                logger.info(f"Found bulk item {item_number}")
                if bulk_item.result_data is None:
                    bulk_item.result_data = {}
                if "files" not in bulk_item.result_data:
                    bulk_item.result_data["files"] = []
                
                bulk_item.result_data["files"].append(file_info)
                # Помечаем поле как измененное для SQLAlchemy
                from sqlalchemy.orm.attributes import flag_modified
                flag_modified(bulk_item, "result_data")
                await session.commit()
                
                files_count = len(bulk_item.result_data["files"])
                warning_text = "⚠️ Contact information was removed from the caption.\n\n" if violated else ""
                await message.answer(
                    f"✅ File received for item #{item_number}!\n\n"
                    f"Total files for this item: {files_count}\n\n"
                    f"{warning_text}"
                    f"Send more files or send /done to finish."
                )
                
                logger.info(f"File added to order {order_id} item {item_number}: {file_info.get('file_name', 'photo')}")
            else:
                await message.answer(f"❌ Error: Bulk item #{item_number} not found")
                logger.error(f"Bulk item {item_number} not found for order {order_id}. Available items: {[item.item_number for item in order.bulk_items]}")
                return
        else:
            # Для обычного заказа - сохраняем в общий список файлов заказа
            if order.files is None:
                order.files = []
            
            order.files.append(file_info)
            await session.commit()
            
            warning_text = "⚠️ Contact information was removed from the caption.\n\n" if violated else ""
            await message.answer(
                f"✅ File received!\n\n"
                f"Total files: {len(order.files)}\n\n"
                f"{warning_text}"
                f"Send more files or send /done to finish."
            )
            
            logger.info(f"File added to order {order_id}: {file_info.get('file_name', 'photo')}")
    
    except Exception as e:
        logger.error(f"Error receiving file: {e}")
        await message.answer("❌ Error saving file")


@router.message(FileStates.waiting_for_file, F.text == "/done")
async def finish_file_upload(message: Message, session: AsyncSession, state: FSMContext):
    """Завершение загрузки файлов"""
    
    try:
        data = await state.get_data()
        order_id = data.get("order_id")
        item_number = data.get("item_number")
        is_bulk = data.get("is_bulk", False)
        
        if not order_id:
            await message.answer("❌ Error: Order not found")
            await state.clear()
            return
        
        worker = await WorkerService.get_worker(session, message.from_user.id)
        order = await OrderService.get_order(session, order_id)
        
        if not order or order.worker_id != worker.id:
            await message.answer("❌ Access denied")
            await state.clear()
            return
        
        if is_bulk and item_number:
            # Для bulk заказа - проверяем файлы конкретного элемента
            bulk_item = next((item for item in order.bulk_items if item.item_number == item_number), None)
            
            logger.info(f"[FINISH] Bulk item found: {bulk_item is not None}")
            if bulk_item:
                logger.info(f"[FINISH] result_data: {bulk_item.result_data}")
                logger.info(f"[FINISH] Files in result_data: {bulk_item.result_data.get('files') if bulk_item.result_data else None}")
            
            if not bulk_item or not bulk_item.result_data or not bulk_item.result_data.get("files"):
                await message.answer(
                    "❌ No files uploaded! Please upload at least one file.",
                    reply_markup=file_upload_keyboard(order_id, item_number)
                )
                return
            
            files_count = len(bulk_item.result_data["files"])
        else:
            # Для обычного заказа - проверяем общие файлы заказа
            if not order.files or len(order.files) == 0:
                await message.answer(
                    "❌ No files uploaded! Please upload at least one file.",
                    reply_markup=file_upload_keyboard(order_id)
                )
                return
            
            files_count = len(order.files)
        
        if is_bulk and item_number:
            # Для bulk заказа - отмечаем конкретный элемент как выполненный
            bulk_item = next((item for item in order.bulk_items if item.item_number == item_number), None)
            if not bulk_item:
                await message.answer(f"❌ Error: Bulk item #{item_number} not found")
                await state.clear()
                return
                
            if bulk_item:
                bulk_item.status = "done"
                bulk_item.result_data["status"] = "done"
                bulk_item.result_data["has_files"] = True
                bulk_item.result_data["files_count"] = files_count
                await session.commit()
                user_language = await OrderDeliveryService.get_user_language(
                    session, order.user_id, order.mirror_bot_id
                )
                result_text = next(
                    (
                        (file_info.get("caption") or "").strip()
                        for file_info in (bulk_item.result_data.get("files", []) if bulk_item.result_data else [])
                        if (file_info.get("caption") or "").strip()
                    ),
                    None,
                )
                await OrderDeliveryService.notify_bulk_item_completed(
                    user_id=order.user_id,
                    mirror_bot_id=order.mirror_bot_id,
                    order_id=order.id,
                    item_number=item_number,
                    service_name=order.service_name,
                    result_status="done",
                    customer_data=bulk_item.input_data,
                    files=bulk_item.result_data.get("files", []) if bulk_item.result_data else [],
                    result_text=result_text,
                    user_language=user_language,
                )
                
                # Показываем сообщение о завершении и возвращаемся к bulk заказу
                from support_bot.keyboards.inline import bulk_order_keyboard
                
                await message.answer(
                    f"✅ <b>Item #{item_number} - Files Uploaded!</b>\n\n"
                    f"📁 Files: {files_count}\n"
                    f"📊 Status: DONE\n\n"
                    f"Continue with other items:",
                    reply_markup=bulk_order_keyboard(order.id, order.bulk_count, is_taken=True, bulk_items=order.bulk_items),
                    parse_mode="HTML"
                )
        else:
            # Для обычного заказа - завершаем весь заказ
            await OrderService.complete_order(
                session,
                order,
                result_data={"status": "done", "has_files": True, "files_count": files_count}
            )
            
            # Обновляем статистику
            await WorkerService.increment_stat(session, worker.id, order.category, "done")
            worker.orders_completed += 1
            await session.commit()
            
            # Логируем завершение заказа
            await SupportLogger.log_order_completed(
                worker_username=worker.username or str(worker.telegram_id),
                worker_id=worker.id,
                order_id=order.id,
                service_name=order.service_name,
                user_id=order.user_id,
                result_status="done"
            )
            
            # Отправляем уведомление с файлами
            # Получаем язык пользователя
            user_language = await OrderDeliveryService.get_user_language(
                session, order.user_id, order.mirror_bot_id
            )
            result_text = next(
                (
                    (file_info.get("caption") or "").strip()
                    for file_info in (order.files or [])
                    if (file_info.get("caption") or "").strip()
                ),
                None,
            )
            
            await OrderDeliveryService.deliver_single_order_result(
                user_id=order.user_id,
                mirror_bot_id=order.mirror_bot_id,
                order_id=order.id,
                service_name=order.service_name,
                result_status="done",
                customer_data=order.input_data,
                files=order.files or [],
                result_text=result_text,
                user_language=user_language
            )
            
            # Уведомляем админов
            try:
                from shared.services.admin_notification_service import AdminNotificationService
                await AdminNotificationService.notify_files_sent(
                    order_id=order.id,
                    service_name=order.service_name,
                    worker_username=worker.username or str(worker.telegram_id),
                    worker_id=worker.id,
                    user_id=order.user_id,
                    files_count=files_count
                )
            except Exception as e:
                logger.warning(f"Failed to send admin notification: {e}")
            
            await message.answer(
                f"✅ <b>Order #{order.id} Completed!</b>\n\n"
                f"Files uploaded: {files_count}\n"
                f"Customer has been notified.\n\n"
                f"Great work! 👍",
                reply_markup=main_menu_keyboard()
            )
        
        await state.clear()
    
    except Exception as e:
        logger.error(f"Error finishing file upload: {e}", exc_info=True)
        await message.answer(f"❌ Error completing order: {str(e)}")
        await state.clear()


@router.message(FileStates.waiting_for_file)
async def invalid_file_input(message: Message, state: FSMContext):
    """Обработка неправильного ввода"""
    
    # Получаем данные из состояния для кнопки "Назад"
    data = await state.get_data()
    order_id = data.get("order_id")
    item_number = data.get("item_number")
    
    if order_id:
        keyboard = file_upload_keyboard(order_id, item_number)
    else:
        keyboard = None
    
    await message.answer(
        "❌ Please send a document or photo file.\n\n"
        "Supported formats:\n"
        "• Documents: .txt, .pdf, .zip, .doc, etc.\n"
        "• Photos: screenshots or images\n\n"
        "When finished, send /done",
        reply_markup=keyboard
    )

