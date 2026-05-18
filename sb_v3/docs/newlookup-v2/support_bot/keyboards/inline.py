"""
Inline клавиатуры для Support Bot
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Optional


def notification_keyboard(order_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для уведомления о новом заказе"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Take Order", callback_data=f"order_take:{order_id}")],
        [InlineKeyboardButton(text="👀 View Details", callback_data=f"order_view:{order_id}")],
        [InlineKeyboardButton(text="🏠 Open Worker Bot", callback_data="main_menu")]
    ])


def main_menu_keyboard(worker=None) -> InlineKeyboardMarkup:
    """Deprecated: worker menu removed. Use admin_menu_keyboard instead."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚠️ Worker menu removed", callback_data="main_menu")]
    ])


def admin_menu_keyboard(
    *,
    can_add_balance: bool = False,
    can_moderate: bool = False,
    can_manage_finance: bool = False,
    can_upload_catalogs: bool = False,
) -> InlineKeyboardMarkup:
    """Compact menu for non-worker operational roles."""
    buttons = []
    if can_upload_catalogs:
        buttons.append([InlineKeyboardButton(text="📤 Uploader Panel", callback_data="uploader_menu")])
    if can_manage_finance:
        buttons.append([InlineKeyboardButton(text="💼 Accountant Panel", callback_data="accountant_menu")])
    if can_moderate:
        buttons.append([InlineKeyboardButton(text="📋 Seller Moderation", callback_data="mod_back")])
    if can_add_balance:
        buttons.append([InlineKeyboardButton(text="🔍 Check User Balance", callback_data="check_user_balance")])
    buttons.append([InlineKeyboardButton(text="📋 Описание", callback_data="bot_description")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def order_list_keyboard(orders: List[dict], page: int = 0) -> InlineKeyboardMarkup:
    """
    Клавиатура со списком заказов
    
    Args:
        orders: Список заказов [{"id": 1, "category": "SSN", "is_bulk": False, "bulk_count": 1}, ...]
        page: Текущая страница
    """
    buttons = []
    
    for order in orders:
        order_type = f"BULK x{order['bulk_count']}" if order['is_bulk'] else "Single"
        text = f"#{order['id']} - {order['category']} ({order_type})"
        buttons.append([
            InlineKeyboardButton(
                text=text,
                callback_data=f"order_view:{order['id']}"
            )
        ])
    
    # Навигация (пока без пагинации)
    buttons.append([InlineKeyboardButton(text="🔄 Refresh", callback_data="orders_refresh")])
    buttons.append([InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def single_order_keyboard(order_id: int, is_taken: bool = False, order_result_data: dict = None, order_status: str = None) -> InlineKeyboardMarkup:
    """
    Клавиатура для single заказа
    
    Args:
        order_id: ID заказа
        is_taken: Взят ли заказ в работу
        order_result_data: Данные результата заказа (для проверки Add Info состояния)
        order_status: Статус заказа (pending, working, done, nf и т.д.)
    """
    buttons = []
    
    # Проверяем, выполнен ли заказ
    is_completed = order_status in ["done", "nf"]
    
    if not is_taken:
        # Если заказ еще не взят
        buttons.append([
            InlineKeyboardButton(text="✅ Take Order", callback_data=f"order_take:{order_id}")
        ])
    elif is_completed:
        # Если заказ выполнен - показываем кнопки управления
        if order_status == "done":
            buttons.append([
                InlineKeyboardButton(text="❌ Change to NF", callback_data=f"order_nf:{order_id}"),
                InlineKeyboardButton(text="⏳ Reset to Pending", callback_data=f"order_reset:{order_id}")
            ])
        else:  # order_status == "nf"
            buttons.append([
                InlineKeyboardButton(text="✅ Change to DONE", callback_data=f"order_done:{order_id}"),
                InlineKeyboardButton(text="⏳ Reset to Pending", callback_data=f"order_reset:{order_id}")
            ])
        
        buttons.append([
            InlineKeyboardButton(text="📎 Add Files", callback_data=f"order_add_files:{order_id}")
        ])
        
        # Навигация для выполненных заказов
        buttons.append([
            InlineKeyboardButton(text="⬅️ Previous", callback_data=f"order_nav:{order_id}:prev"),
            InlineKeyboardButton(text="➡️ Next", callback_data=f"order_nav:{order_id}:next")
        ])
        
        buttons.append([
            InlineKeyboardButton(text="📦 Back to Order", callback_data=f"order_view:{order_id}")
        ])
    else:
        # Если заказ взят (обычное состояние)
        buttons.append([
            InlineKeyboardButton(text="✅ DONE", callback_data=f"order_done:{order_id}"),
            InlineKeyboardButton(text="❌ NF", callback_data=f"order_nf:{order_id}")
        ])
        buttons.append([
            InlineKeyboardButton(text="📎 DONE + Files", callback_data=f"order_send_file:{order_id}"),
            InlineKeyboardButton(text="💬 DONE + TXT", callback_data=f"order_reply_text:{order_id}")
        ])
        buttons.append([
            InlineKeyboardButton(text="❌ Cancel Order", callback_data=f"order_cancel:{order_id}")
        ])
        buttons.append([
            InlineKeyboardButton(text="⚠️ Report Client", callback_data=f"order_complaint:{order_id}")
        ])
    
    buttons.append([InlineKeyboardButton(text="⬅️ Back", callback_data="orders_available")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def bulk_order_keyboard(order_id: int, bulk_count: int, is_taken: bool = False, bulk_items: list = None) -> InlineKeyboardMarkup:
    """
    Клавиатура для bulk заказа с кнопками от 1 до N с отображением статуса
    
    Args:
        order_id: ID заказа
        bulk_count: Количество элементов
        is_taken: Взят ли заказ в работу
        bulk_items: Список BulkOrderItem для отображения статусов
    """
    buttons = []
    
    if not is_taken:
        # Если заказ еще не взят
        buttons.append([
            InlineKeyboardButton(text="✅ Take Order", callback_data=f"order_take:{order_id}")
        ])
    else:
        # Кнопки с номерами элементов и статусами (максимум 5 в ряду)
        row = []
        for i in range(1, bulk_count + 1):
            # Определяем статус для этого элемента
            status_emoji = "⏳"  # По умолчанию pending
            if bulk_items:
                item = next((item for item in bulk_items if item.item_number == i), None)
                if item:
                    status_map = {
                        "pending": "⏳",
                        "done": "✅", 
                        "nf": "❌"
                    }
                    status_emoji = status_map.get(item.status, "⏳")
            
            button_text = f"{status_emoji}{i}"
            row.append(
                InlineKeyboardButton(
                    text=button_text,
                    callback_data=f"bulk_item:{order_id}:{i}"
                )
            )
            
            if len(row) == 5:
                buttons.append(row)
                row = []
        
        if row:  # Добавляем оставшиеся кнопки
            buttons.append(row)
        
        # Дополнительные кнопки
        buttons.append([
            InlineKeyboardButton(text="✅ Complete Order", callback_data=f"order_complete:{order_id}")
        ])
        buttons.append([
            InlineKeyboardButton(text="📊 Summary", callback_data=f"bulk_summary:{order_id}")
        ])
        buttons.append([
            InlineKeyboardButton(text="❌ Cancel All", callback_data=f"order_cancel:{order_id}")
        ])
        buttons.append([
            InlineKeyboardButton(text="⚠️ Report Client", callback_data=f"order_complaint:{order_id}")
        ])
    
    buttons.append([InlineKeyboardButton(text="⬅️ Back", callback_data="orders_available")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def bulk_item_keyboard(order_id: int, item_number: int, current_status: str) -> InlineKeyboardMarkup:
    """
    Клавиатура для отдельного элемента bulk заказа
    
    Args:
        order_id: ID заказа
        item_number: Номер элемента (1, 2, 3...)
        current_status: Текущий статус элемента
    """
    buttons = []
    
    if current_status == "pending":
        # Если элемент еще не обработан
        buttons.append([
            InlineKeyboardButton(text="✅ Mark as DONE", callback_data=f"bulk_done:{order_id}:{item_number}"),
            InlineKeyboardButton(text="❌ Mark as NF", callback_data=f"bulk_nf:{order_id}:{item_number}")
        ])
        buttons.append([
            InlineKeyboardButton(text="📎 DONE + Files", callback_data=f"bulk_done_files:{order_id}:{item_number}"),
            InlineKeyboardButton(text="💬 DONE + TXT", callback_data=f"bulk_reply_text:{order_id}:{item_number}")
        ])
    elif current_status in ["done", "nf"]:
        # Если элемент уже обработан - можно изменить статус
        if current_status == "done":
            buttons.append([
                InlineKeyboardButton(text="❌ Change to NF", callback_data=f"bulk_nf:{order_id}:{item_number}"),
                InlineKeyboardButton(text="⏳ Reset to Pending", callback_data=f"bulk_reset:{order_id}:{item_number}")
            ])
        else:  # current_status == "nf"
            buttons.append([
                InlineKeyboardButton(text="✅ Change to DONE", callback_data=f"bulk_done:{order_id}:{item_number}"),
                InlineKeyboardButton(text="⏳ Reset to Pending", callback_data=f"bulk_reset:{order_id}:{item_number}")
            ])
        
        buttons.append([
            InlineKeyboardButton(text="📎 Add Files", callback_data=f"bulk_done_files:{order_id}:{item_number}")
        ])
    
    # Навигационные кнопки
    buttons.append([
        InlineKeyboardButton(text="⬅️ Previous", callback_data=f"bulk_nav:{order_id}:{item_number}:prev"),
        InlineKeyboardButton(text="➡️ Next", callback_data=f"bulk_nav:{order_id}:{item_number}:next")
    ])
    
    buttons.append([
        InlineKeyboardButton(text="📦 Back to Order", callback_data=f"order_view:{order_id}")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def bulk_summary_keyboard(order_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для сводки bulk заказа"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Complete Order", callback_data=f"order_complete:{order_id}")],
        [InlineKeyboardButton(text="⬅️ Back to Order", callback_data=f"order_view:{order_id}")]
    ])




def statistics_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Today", callback_data="stats_today")],
        [InlineKeyboardButton(text="📆 This Week", callback_data="stats_week")],
        [InlineKeyboardButton(text="📊 This Month", callback_data="stats_month")],
        [InlineKeyboardButton(text="⬅️ Back to Profile", callback_data="profile")],
        [InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu")]
    ])


def profile_keyboard(worker=None) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="📊 My Statistics", callback_data="statistics")],
        [InlineKeyboardButton(text="📋 My Categories", callback_data="my_categories")],
    ]
    if worker and getattr(worker, 'can_check_balance', False):
        buttons.append([InlineKeyboardButton(text="🔍 Check User Balance", callback_data="check_user_balance")])
    buttons.append([InlineKeyboardButton(text="📋 Submit Expense Report", callback_data="worker_expense_report")])
    buttons.append([InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    """Простая кнопка возврата в меню"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu")]
    ])


def order_notification_keyboard(order_id: int) -> InlineKeyboardMarkup:
    """
    Клавиатура для уведомления о новом single заказе
    Показывается в уведомлении, которое приходит саппорту
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Take Order", callback_data=f"notify_take:{order_id}")]
    ])


def bulk_order_notification_keyboard(order_id: int, items: List) -> InlineKeyboardMarkup:
    """
    Клавиатура для уведомления о новом bulk заказе
    Показывает кнопки "взять" для каждого элемента
    
    Args:
        order_id: ID заказа
        items: Список BulkOrderItem
    """
    buttons = []
    
    # Создаем кнопки для каждого элемента (максимум 5 в ряду)
    row = []
    for item in items:
        status_emoji = ""
        if item.status == "done":
            status_emoji = "✅"
        elif item.status == "nf":
            status_emoji = "❌"
        
        button_text = f"{status_emoji}#{item.item_number}" if status_emoji else f"#{item.item_number}"
        
        row.append(
            InlineKeyboardButton(
                text=button_text,
                callback_data=f"notify_bulk_take:{order_id}:{item.item_number}"
            )
        )
        
        if len(row) == 5:
            buttons.append(row)
            row = []
    
    if row:  # Добавляем оставшиеся кнопки
        buttons.append(row)
    
    # Кнопка "Взять все"
    buttons.append([
        InlineKeyboardButton(text="📦 Take All Items", callback_data=f"notify_take_all:{order_id}")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def working_order_keyboard(order_id: int, is_bulk: bool = False, category: str = "") -> InlineKeyboardMarkup:
    """
    Клавиатура для заказа, который взят в работу
    Появляется после нажатия "взять в работу"
    
    Args:
        order_id: ID заказа
        is_bulk: Bulk заказ или нет
        category: Категория заказа (для определения, нужна ли кнопка NF)
    """
    buttons = []
    
    # Reply на сообщение для отправки результата
    buttons.append([
        InlineKeyboardButton(text="💬 Reply with result", callback_data=f"reply_hint:{order_id}")
    ])
    
    # Дополнительное сообщение клиенту
    buttons.append([
        InlineKeyboardButton(text="📧 Send Additional Message", callback_data=f"send_additional_message:{order_id}")
    ])

    # Промежуточные статусы (видны покупателю)
    buttons.append([
        InlineKeyboardButton(text="⏳ In Progress", callback_data=f"wstatus:{order_id}:in_progress"),
        InlineKeyboardButton(text="🔍 Searching", callback_data=f"wstatus:{order_id}:searching"),
        InlineKeyboardButton(text="❗ Problem", callback_data=f"wstatus:{order_id}:problem"),
    ])

    # Основные действия
    if not is_bulk:
        # Для lookup и CR показываем NF
        if any(cat in category.lower() for cat in ["lookup", "cr_", "phone"]):
            buttons.append([
                InlineKeyboardButton(text="✅ DONE", callback_data=f"work_done:{order_id}"),
                InlineKeyboardButton(text="❌ NF", callback_data=f"work_nf:{order_id}")
            ])
        else:
            buttons.append([
                InlineKeyboardButton(text="✅ DONE", callback_data=f"work_done:{order_id}")
            ])
    
    # Дополнительные действия
    buttons.append([
        InlineKeyboardButton(text="⏰ Remind Later", callback_data=f"work_remind:{order_id}")
    ])
    
    buttons.append([
        InlineKeyboardButton(text="⚠️ Report Wrong Data", callback_data=f"work_report:{order_id}")
    ])
    
    buttons.append([
        InlineKeyboardButton(text="📝 Send Complaint", callback_data=f"complaint:{order_id}")
    ])
    
    buttons.append([
        InlineKeyboardButton(text="❌ Cancel + Refund", callback_data=f"work_cancel:{order_id}")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def bulk_item_working_keyboard(order_id: int, item_number: int, item_status: str, category: str = "") -> InlineKeyboardMarkup:
    """
    Клавиатура для элемента bulk заказа, взятого в работу
    
    Args:
        order_id: ID заказа
        item_number: Номер элемента
        item_status: Текущий статус элемента
        category: Категория заказа
    """
    buttons = []
    
    if item_status == "pending":
        # Для lookup и CR показываем NF
        if any(cat in category.lower() for cat in ["lookup", "cr_", "phone"]):
            buttons.append([
                InlineKeyboardButton(text="✅ DONE", callback_data=f"work_bulk_done:{order_id}:{item_number}"),
                InlineKeyboardButton(text="❌ NF", callback_data=f"work_bulk_nf:{order_id}:{item_number}")
            ])
        else:
            buttons.append([
                InlineKeyboardButton(text="✅ DONE", callback_data=f"work_bulk_done:{order_id}:{item_number}")
            ])
    else:
        # Уже выполнен
        status_text = "✅ DONE" if item_status == "done" else "❌ NF"
        buttons.append([
            InlineKeyboardButton(text=f"Status: {status_text}", callback_data="noop")
        ])
    
    buttons.append([
        InlineKeyboardButton(text="⬅️ Back to Order", callback_data=f"order_view:{order_id}")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def remind_later_keyboard(order_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для выбора времени напоминания"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="1h", callback_data=f"remind_time:{order_id}:1"),
            InlineKeyboardButton(text="3h", callback_data=f"remind_time:{order_id}:3"),
            InlineKeyboardButton(text="6h", callback_data=f"remind_time:{order_id}:6")
        ],
        [
            InlineKeyboardButton(text="12h", callback_data=f"remind_time:{order_id}:12"),
            InlineKeyboardButton(text="24h", callback_data=f"remind_time:{order_id}:24")
        ],
        [InlineKeyboardButton(text="❌ Cancel", callback_data=f"order_view:{order_id}")]
    ])


def history_bulk_order_keyboard(order_id: int, items: List, show_items: bool = False) -> InlineKeyboardMarkup:
    """
    Клавиатура для bulk заказа в истории с раскрывающимся списком
    
    Args:
        order_id: ID заказа
        items: Список BulkOrderItem
        show_items: Показать ли список элементов
    """
    buttons = []
    
    if not show_items:
        # Кнопка для раскрытия списка
        buttons.append([
            InlineKeyboardButton(text="📋 Show Items", callback_data=f"history_expand:{order_id}")
        ])
    else:
        # Показываем элементы (по 5 в ряду)
        row = []
        for item in items:
            # Эмодзи статуса
            status_emoji = "✅" if item.status == "done" else "❌" if item.status == "nf" else "⏳"
            
            row.append(
                InlineKeyboardButton(
                    text=f"{status_emoji}{item.item_number}",
                    callback_data=f"history_item:{order_id}:{item.item_number}"
                )
            )
            
            if len(row) == 5:
                buttons.append(row)
                row = []
        
        if row:
            buttons.append(row)
        
        # Кнопка для сворачивания
        buttons.append([
            InlineKeyboardButton(text="🔼 Hide Items", callback_data=f"history_collapse:{order_id}")
        ])
    
    buttons.append([InlineKeyboardButton(text="⬅️ Back", callback_data="orders_history")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def history_item_keyboard(order_id: int, item_number: int) -> InlineKeyboardMarkup:
    """Клавиатура для просмотра элемента в истории"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Back to Order", callback_data=f"history_view:{order_id}:1")]
    ])

