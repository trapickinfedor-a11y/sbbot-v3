from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from mirror_bot.keyboards.inline import (
    support_categories_keyboard,
    my_tickets_keyboard,
    ticket_detail_keyboard,
    back_to_support_keyboard
)
from mirror_bot.services.support_service import SupportService
from mirror_bot.utils.message_utils import safe_edit_message
from shared.database.models import SupportTicket, SupportMessage
from mirror_bot.constants.buttons_en import ButtonTexts
from mirror_bot.utils.media_library import resolve_bot_photo

router = Router()

SUPPORT_PHOTO = resolve_bot_photo("support", fallback_path="media/support.png")


# Обработка текстовой кнопки "📞 Support"
@router.message(F.text.in_(ButtonTexts.get_all_variants("SUPPORT")))
async def support_button_handler(message: Message, state: FSMContext, texts, buttons):
    """Обработка кнопки Support из главного меню"""
    await state.clear()
    
    try:
        await message.answer_photo(
            photo=SUPPORT_PHOTO,
            caption=texts.SUPPORT_MAIN,
            reply_markup=support_categories_keyboard(buttons)
        )
    except Exception:
        await message.answer(
            texts.SUPPORT_MAIN,
            reply_markup=support_categories_keyboard(buttons)
        )


class SupportStates(StatesGroup):
    choosing_category = State()
    writing_message = State()
    attaching_files = State()
    replying_to_ticket = State()


@router.callback_query(F.data == "support")
async def support_menu(callback: CallbackQuery, state: FSMContext, texts, buttons):
    """Главное меню поддержки"""
    await state.clear()
    
    try:
        await callback.message.delete()
        await callback.bot.send_photo(
            chat_id=callback.message.chat.id,
            photo=SUPPORT_PHOTO,
            caption=texts.SUPPORT_MAIN,
            reply_markup=support_categories_keyboard(buttons)
        )
    except Exception:
        await callback.message.edit_text(
            texts.SUPPORT_MAIN,
            reply_markup=support_categories_keyboard(buttons)
        )
    await callback.answer()


@router.callback_query(F.data == "my_tickets")
async def my_tickets_menu(callback: CallbackQuery, session: AsyncSession, mirror_bot_id: int, texts, buttons):
    """Мои запросы - список тикетов пользователя"""
    user_id = callback.from_user.id
    
    # Получаем открытые тикеты
    open_tickets = await SupportService.get_user_tickets(
        session, user_id, mirror_bot_id, status="open"
    )
    
    # Получаем закрытые тикеты (последние 10)
    closed_tickets = await SupportService.get_user_tickets(
        session, user_id, mirror_bot_id, status="closed", limit=10
    )
    
    text = texts.MY_TICKETS_HEADER
    
    if open_tickets:
        text += texts.OPEN_TICKETS_HEADER
        for ticket in open_tickets:
            unread_count = await SupportService.get_unread_messages_count(session, ticket.id, user_id)
            unread_badge = f" 🔴 {unread_count}" if unread_count > 0 else ""
            text += f"#{ticket.id} - {ticket.subject[:30]}...{unread_badge}\n"
        text += "\n"
    else:
        text += f"{texts.NO_OPEN_TICKETS}\n\n"
    
    if closed_tickets:
        text += f"{texts.CLOSED_TICKETS_HEADER}\n"
        for ticket in closed_tickets:
            text += f"#{ticket.id} - {ticket.subject[:30]}...\n"
    
    await safe_edit_message(
        callback,
        text,
        reply_markup=my_tickets_keyboard(open_tickets, closed_tickets),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("support_category_"))
async def choose_category(callback: CallbackQuery, state: FSMContext, texts):
    """Выбор категории обращения"""
    category = callback.data.replace("support_category_", "")
    
    category_names = {
        "payment": texts.CATEGORY_PAYMENT,
        "product": texts.CATEGORY_PRODUCT,
        "general": texts.CATEGORY_GENERAL,
        "partnership": texts.CATEGORY_PARTNERSHIP
    }
    
    await state.update_data(category=category)
    await state.set_state(SupportStates.writing_message)
    
    text = f"**{category_names.get(category, texts.CATEGORY_GENERAL)}**\n\n{texts.DESCRIBE_YOUR_PROBLEM}"
    
    await safe_edit_message(callback, text, parse_mode="Markdown")
    await callback.answer()


@router.message(SupportStates.writing_message)
async def receive_support_message(message: Message, state: FSMContext, session: AsyncSession, mirror_bot_id: int, texts):
    """Получение сообщения от пользователя"""
    if not message.text or len(message.text) < 10:
        await message.answer(texts.SUPPORT_MESSAGE_TOO_SHORT)
        return
    
    data = await state.get_data()
    category = data.get("category", "general")
    
    # Создаем тикет
    ticket = await SupportService.create_ticket(
        session=session,
        user_id=message.from_user.id,
        mirror_bot_id=mirror_bot_id,
        category=category,
        subject=message.text[:200],  # Первые 200 символов как subject
        initial_message=message.text
    )
    
    await state.clear()
    
    from mirror_bot.constants.language_loader import get_texts
    temp_texts = get_texts('en')  # Fallback, ideally should use user language
    
    text = (
        f"{temp_texts.YOUR_TICKET_CREATED.format(ticket_id=ticket.id)}\n\n"
        f"{temp_texts.CATEGORY_PREFIX} {category}\n"
        f"{temp_texts.STATUS_PREFIX} {temp_texts.STATUS_OPEN}\n\n"
        f"{temp_texts.OUR_SPECIALISTS_WILL_REPLY}\n"
        f"{temp_texts.YOU_WILL_BE_NOTIFIED}\n\n"
        f"{temp_texts.WANT_TO_ATTACH_FILES}"
    )
    
    await message.answer(
        text,
        reply_markup=ticket_detail_keyboard(ticket.id, has_files_option=True),
        parse_mode="Markdown"
    )


@router.callback_query(F.data.startswith("ticket_"))
async def view_ticket(callback: CallbackQuery, session: AsyncSession, texts):
    """Просмотр тикета"""
    ticket_id = int(callback.data.split("_")[1])
    
    # Получаем тикет с сообщениями
    ticket = await SupportService.get_ticket_with_messages(session, ticket_id)
    
    if not ticket:
        await callback.answer(texts.SUPPORT_TICKET_NOT_FOUND, show_alert=True)
        return
    
    # Проверяем что тикет принадлежит пользователю
    if ticket.user_id != callback.from_user.id:
        await callback.answer(texts.SUPPORT_ACCESS_DENIED, show_alert=True)
        return
    
    # Отмечаем сообщения как прочитанные
    await SupportService.mark_messages_as_read(session, ticket_id, callback.from_user.id)
    
    # Формируем текст с историей переписки
    category_names = {
        "payment": texts.CATEGORY_PAYMENT,
        "product": texts.CATEGORY_PRODUCT,
        "general": texts.CATEGORY_GENERAL,
        "partnership": texts.CATEGORY_PARTNERSHIP
    }
    
    status_emoji = {
        "open": "🟢",
        "in_progress": "🟡",
        "waiting_user": "🔵",
        "closed": "⚪️"
    }
    
    status_names = {
        "open": texts.STATUS_OPEN,
        "in_progress": texts.STATUS_IN_PROGRESS,
        "waiting_user": texts.STATUS_WAITING_USER,
        "closed": texts.STATUS_CLOSED
    }
    
    text = (
        f"{texts.TICKET_HEADER.format(ticket_id=ticket.id)}\n\n"
        f"{texts.CATEGORY_PREFIX} {category_names.get(ticket.category, ticket.category)}\n"
        f"{texts.STATUS_PREFIX} {status_emoji.get(ticket.status, '⚪️')} {status_names.get(ticket.status, ticket.status)}\n"
        f"{texts.CREATED_PREFIX} {ticket.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
        "━━━━━━━━━━━━━━━━━\n\n"
    )
    
    # Добавляем историю сообщений
    for msg in ticket.messages:
        sender = texts.SENDER_YOU if msg.sender_type == "user" else texts.SENDER_SUPPORT
        time_str = msg.created_at.strftime('%d.%m %H:%M')
        
        text += f"**{sender}** ({time_str}):\n"
        text += f"{msg.message_text}\n"
        
        if msg.files:
            text += f"{texts.FILES_COUNT.format(count=len(msg.files))}\n"
        
        text += "\n"
    
    can_reply = ticket.status != "closed"
    
    await safe_edit_message(
        callback,
        text,
        reply_markup=ticket_detail_keyboard(ticket.id, can_reply=can_reply, is_viewing=True),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("reply_ticket_"))
async def start_reply_to_ticket(callback: CallbackQuery, state: FSMContext, texts):
    """Начать ответ на тикет"""
    ticket_id = int(callback.data.replace("reply_ticket_", ""))
    
    await state.update_data(ticket_id=ticket_id)
    await state.set_state(SupportStates.replying_to_ticket)
    
    await callback.message.answer(texts.WRITE_YOUR_MESSAGE)
    await callback.answer()


@router.message(SupportStates.replying_to_ticket)
async def receive_reply_message(message: Message, state: FSMContext, session: AsyncSession, texts):
    """Получение ответа от пользователя"""
    data = await state.get_data()
    ticket_id = data.get("ticket_id")
    
    if not ticket_id:
        await state.clear()
        await message.answer(texts.SUPPORT_TICKET_NOT_FOUND)
        return
    
    # Проверяем что тикет существует и открыт
    ticket = await SupportService.get_ticket_by_id(session, ticket_id)
    
    if not ticket:
        await state.clear()
        await message.answer(texts.SUPPORT_TICKET_NOT_FOUND)
        return
    
    if ticket.status == "closed":
        await state.clear()
        await message.answer(texts.SUPPORT_TICKET_CLOSED)
        return
    
    # Проверяем что тикет принадлежит пользователю
    if ticket.user_id != message.from_user.id:
        await state.clear()
        await message.answer(texts.SUPPORT_ACCESS_DENIED)
        return
    
    # Извлекаем текст и файлы
    message_text = message.text or message.caption or ""
    files = []
    
    # Обрабатываем файлы если есть
    if message.photo or message.document or message.video or message.audio or message.voice or message.video_note:
        from mirror_bot.services.file_service import FileService
        
        file_service = FileService(message.bot)
        file_info = await file_service.download_and_save_file(message)
        
        if file_info:
            files.append({
                "file_id": file_info["file_id"],  # Локальный ID файла
                "file_name": file_info["file_name"],
                "type": file_info["file_type"],
                "size": file_info["file_size"],
                "original_telegram_file_id": file_info["original_telegram_file_id"]
            })
    
    if not message_text and not files:
        await message.answer(texts.SUPPORT_MESSAGE_EMPTY)
        return
    
    # Добавляем сообщение к тикету
    await SupportService.add_message_to_ticket(
        session=session,
        ticket_id=ticket_id,
        sender_type="user",
        sender_id=message.from_user.id,
        message_text=message_text,
        files=files if files else None
    )
    
    # Обновляем статус тикета на waiting_user если был in_progress
    if ticket.status == "in_progress":
        await SupportService.update_ticket_status(session, ticket_id, "waiting_user")
    
    await state.clear()
    
    await message.answer(
        f"{texts.YOUR_MESSAGE_SENT}\n\n"
        f"{texts.TICKET_NUMBER_PREFIX}{ticket_id}\n"
        f"{texts.YOU_WILL_BE_NOTIFIED}",
        parse_mode="Markdown"
    )


@router.callback_query(F.data.startswith("attach_files_"))
async def attach_files_to_ticket(callback: CallbackQuery, state: FSMContext, texts):
    """Прикрепить файлы к тикету"""
    ticket_id = int(callback.data.replace("attach_files_", ""))
    
    await state.update_data(ticket_id=ticket_id, attaching=True)
    await state.set_state(SupportStates.attaching_files)
    
    await callback.message.answer(texts.SEND_FILES_INSTRUCTION)
    await callback.answer()


@router.message(SupportStates.attaching_files)
async def receive_attachment(message: Message, state: FSMContext, session: AsyncSession, texts):
    """Получение прикрепленных файлов"""
    if message.text and message.text == "/done":
        await state.clear()
        await message.answer(texts.SUPPORT_FILES_ATTACHED)
        return
    
    data = await state.get_data()
    ticket_id = data.get("ticket_id")
    
    if not ticket_id:
        await state.clear()
        return
    
    # Извлекаем файл
    files = []
    caption = message.caption or ""
    
    # Обрабатываем файлы если есть
    if message.photo or message.document or message.video or message.audio or message.voice or message.video_note:
        from mirror_bot.services.file_service import FileService
        
        file_service = FileService(message.bot)
        file_info = await file_service.download_and_save_file(message)
        
        if file_info:
            files.append({
                "file_id": file_info["file_id"],  # Локальный ID файла
                "file_name": file_info["file_name"],
                "type": file_info["file_type"],
                "size": file_info["file_size"],
                "original_telegram_file_id": file_info["original_telegram_file_id"]
            })
    
    if files:
        # Добавляем сообщение с файлом
        await SupportService.add_message_to_ticket(
            session=session,
            ticket_id=ticket_id,
            sender_type="user",
            sender_id=message.from_user.id,
            message_text=caption if caption else "📎 Файл",
            files=files
        )
        
        await message.answer(texts.SUPPORT_FILE_ATTACHED)


@router.callback_query(F.data == "back_to_support")
async def back_to_support_menu(callback: CallbackQuery, state: FSMContext):
    """Вернуться в меню поддержки"""
    await state.clear()
    await support_menu(callback, state)

