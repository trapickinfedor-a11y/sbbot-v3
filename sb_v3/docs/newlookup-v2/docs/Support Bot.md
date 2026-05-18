# Support Bot — support_bot/

[[MOC]] > Support Bot

**51 файл** | aiogram 3.x | Ключевой модуль: seller_moderation (1582 строки) | Ролевая система

---

## support_bot/__init__.py
**Строк:** 6

---

## support_bot/bot.py
**Строк:** 152

**Функции:**
- `def _validate_support_bot_startup() -> None`
- `async def main()`
- `async def _global_error_handler(event, **kwargs)`
- `async def _start_worker_reminders(*args, **kwargs)`
- `async def _stop_worker_reminders(*args, **kwargs)`

**Cross-imports:**
- `from support_bot.config import support_bot_config`
- `from support_bot.handlers import (...)`
- `from support_bot.middlewares.database import DatabaseMiddleware`
- `from support_bot.middlewares.worker_auth import WorkerAuthMiddleware`
- `from shared.config.env_utils import StartupValidationError, validate_startup_env`
- `from shared.database.session import async_session_maker`
- `from shared.database.tasks_session import init_tasks_db`
- `from shared.middlewares.error_logging import GlobalErrorLoggingMiddleware`
- `from shared.services.admin_notification_service import AdminNotificationService`
- `from support_bot.services.worker_reminder_service import run_worker_order_reminder_watcher`

**TODO/заглушки:** 1

---

## support_bot/config.py
**Строк:** 81

**Классы:**
- `class SupportBotConfig`

**Cross-imports:**
- `from shared.config.env_utils import parse_int_env, parse_int_list_env`

---

## support_bot/api/__init__.py
**Строк:** 1

---

## Константы (support_bot/constants/)

### support_bot/constants/buttons_accounts.py
**Строк:** 10

**Классы:**
- `class AccountsAdminBtns`

---

### support_bot/constants/buttons_esim.py
**Строк:** 14

**Классы:**
- `class ESIMAdminBtns`

---

### support_bot/constants/service_names.py
**Строк:** 217

**Функции:**
- `def get_esim_service_name(service_name: str, quantity: int) -> str`
- `def get_full_service_name(service_name: str, input_data: dict) -> str`

---

## Handlers (support_bot/handlers/)

### support_bot/handlers/__init__.py
**Строк:** 1

### support_bot/handlers/start.py
**Строк:** 112

Точка входа воркера / начало работы.

**Роуты:**
- `@router.message(CommandStart())`
- `@router.callback_query(F.data == "main_menu")`

**Cross-imports:**
- `from support_bot.services.access_service import SupportBotActor`
- `from shared.database.models import Worker`

---

### support_bot/handlers/orders.py
**Строк:** 1188

Основной handler для воркеров: взятие заказов, отправка результатов.

**Классы:**
- `class OrderStates(StatesGroup)`

**FSM:**
- `waiting_result = State()`
- `waiting_addinfo = State()`
- `waiting_bulk_item = State()`

**Роуты:**
- `@router.callback_query(F.data == "available_orders")`
- `@router.callback_query(F.data.startswith("take_order:"))`
- `@router.callback_query(F.data.startswith("order_detail:"))`
- `@router.callback_query(F.data.startswith("complete_order:"))`
- `@router.message(OrderStates.waiting_result)`
- `@router.callback_query(F.data.startswith("cancel_order:"))`
- `@router.callback_query(F.data.startswith("not_found:"))`
- `@router.callback_query(F.data.startswith("addinfo_request:"))`

**Cross-imports:**
- `from support_bot.services.order_service import OrderService`
- `from support_bot.services.order_delivery_service import OrderDeliveryService`
- `from shared.database.models import Order, Worker`

**API вызовы:**
- `http://main_bot:8080/api/notify-single-order-completed`
- `http://main_bot:8080/api/notify-addinfo-completed`

---

### support_bot/handlers/work_orders.py
**Строк:** 954

Заказы в рабочем режиме (расширенные функции).

**Классы:**
- `class WorkStates(StatesGroup)`

**FSM:**
- `working = State()`
- `awaiting_file = State()`
- `awaiting_bulk = State()`

**Роуты:**
- `@router.callback_query(F.data == "my_active_orders")`
- `@router.callback_query(F.data.startswith("work_order:"))`
- `@router.message(WorkStates.awaiting_file, F.document)`

**Cross-imports:**
- `from support_bot.services.order_service import OrderService`
- `from support_bot.services.worker_notification_service import WorkerNotificationService`

---

### support_bot/handlers/seller_moderation.py
**Строк:** 1582

**Ключевой handler** — модерация загруженных товаров продавцов (банки, CC, NFC, OTP).

**Классы:**
- `class RequestChangesStates(StatesGroup)`
- `class ModCCSearchStates(StatesGroup)`

**FSM:**
- `RequestChangesStates.waiting_message = State()`
- `ModCCSearchStates.waiting_query = State()`

**Роуты:**
- `@router.callback_query(F.data == "moderation_queue")`
- `@router.callback_query(F.data.startswith("mod_bank:"))`
- `@router.callback_query(F.data.startswith("approve_bank:"))`
- `@router.callback_query(F.data.startswith("reject_bank:"))`
- `@router.callback_query(F.data.startswith("request_changes:"))`
- `@router.callback_query(F.data.startswith("mod_cc:"))`
- `@router.callback_query(F.data.startswith("approve_cc:"))`
- `@router.callback_query(F.data.startswith("reject_cc:"))`
- `@router.callback_query(F.data.startswith("mod_nfc:"))`
- `@router.callback_query(F.data.startswith("mod_otp:"))`
- `@router.message(RequestChangesStates.waiting_message)`

**Cross-imports:**
- `from shared.database.models import SellerBank, SellerCCItem, SellerNFCItem, SellerOTPItem, Seller`
- `from shared.services.moderation_pricing_service import ...`
- `from shared.services.nocodb_service import NocoDBService`
- `from shared.services.admin_notification_service import AdminNotificationService`

---

### support_bot/handlers/seller_orders.py
**Строк:** 808

Управление заказами со стороны поддержки/модераторов.

**Классы:**
- `class RejectOrderStates(StatesGroup)`

**FSM:**
- `waiting_reason = State()`

**Роуты:**
- `@router.callback_query(F.data == "seller_orders_queue")`
- `@router.callback_query(F.data.startswith("seller_order_detail:"))`
- `@router.callback_query(F.data.startswith("admin_resolve_dispute:"))`
- `@router.callback_query(F.data.startswith("admin_reject_order:"))`

**Cross-imports:**
- `from shared.services.seller_dispute_service import SellerDisputeService`
- `from shared.services.seller_order_delivery_service import ...`
- `from shared.database.models import SellerOrder, SellerOrderDispute`

**API вызовы:**
- `http://main_bot:8080/api/notify-order-cancelled`

---

### support_bot/handlers/accountant_panel.py
**Строк:** 935

Финансовая панель: транзакции, выводы, балансы.

**Роуты:**
- `@router.callback_query(F.data == "accountant_panel")`
- `@router.callback_query(F.data == "pending_withdrawals")`
- `@router.callback_query(F.data.startswith("approve_withdrawal:"))`
- `@router.callback_query(F.data.startswith("reject_withdrawal:"))`
- `@router.callback_query(F.data == "worker_withdrawals")`
- `@router.callback_query(F.data == "seller_withdrawals")`

**Cross-imports:**
- `from shared.services.ledger_service import LedgerService`
- `from shared.database.models import WorkerWithdrawal, SellerWithdrawal, Transaction`

---

### support_bot/handlers/tickets.py
**Строк:** 509

Тикет-система поддержки.

**Классы:**
- `class CreateTicketFSM(StatesGroup)`
- `class ReplyTicketFSM(StatesGroup)`

**FSM:**
- `CreateTicketFSM: waiting_category = State()`, `waiting_subject = State()`, `waiting_message = State()`
- `ReplyTicketFSM: waiting_reply = State()`

**Роуты:**
- `@router.callback_query(F.data == "support_tickets")`
- `@router.callback_query(F.data.startswith("ticket_detail:"))`
- `@router.callback_query(F.data.startswith("reply_ticket:"))`
- `@router.callback_query(F.data.startswith("close_ticket:"))`
- `@router.message(ReplyTicketFSM.waiting_reply)`

**Cross-imports:**
- `from shared.database.models import SupportTicket, SupportTicketMessage`

---

### support_bot/handlers/esim.py
**Строк:** 599

Управление eSIM сервисами.

**Классы:**
- `class ESIMAdminStates(StatesGroup)`

**FSM:**
- `waiting_config = State()`
- `waiting_assign = State()`

**Роуты:**
- `@router.callback_query(F.data == "esim_admin")`
- `@router.callback_query(F.data.startswith("esim_category:"))`
- `@router.callback_query(F.data.startswith("esim_manage:"))`

**Cross-imports:**
- `from support_bot.constants.buttons_esim import ESIMAdminBtns`

---

### support_bot/handlers/files.py
**Строк:** 502

Загрузка и управление файлами поддержки.

**Классы:**
- `class FileStates(StatesGroup)`

**FSM:**
- `waiting_file = State()`
- `waiting_description = State()`

**Роуты:**
- `@router.callback_query(F.data == "file_manager")`
- `@router.message(FileStates.waiting_file, F.document)`

---

### support_bot/handlers/upload_product.py
**Строк:** 1025

Загрузка товаров (продуктов) администратором.

**Классы:**
- `class UploadProductStates(StatesGroup)`
- `class UploadAccountStates(StatesGroup)`

**FSM:**
- `UploadProductStates: waiting_category = State()`, `waiting_file = State()`, `waiting_price = State()`, `waiting_name = State()`, `confirm = State()`
- `UploadAccountStates: waiting_category = State()`, `waiting_data = State()`, `confirm = State()`

**Роуты:**
- `@router.callback_query(F.data == "upload_product")`
- `@router.callback_query(F.data == "upload_account")`
- `@router.message(UploadProductStates.waiting_file, F.document)`

**Cross-imports:**
- `from shared.database.models import Product, AccountItem, AccountInventory`
- `from shared.services.product_audit_service import log_product_action`

---

### support_bot/handlers/bulk_orders.py
**Строк:** 581

Обработка массовых заказов.

**Роуты:**
- `@router.callback_query(F.data == "bulk_orders")`
- `@router.callback_query(F.data.startswith("bulk_detail:"))`
- `@router.callback_query(F.data.startswith("bulk_item:"))`

**Cross-imports:**
- `from shared.database.models import Order, BulkOrderItem`

**API вызовы:**
- `http://main_bot:8080/api/notify-bulk-item-completed`
- `http://main_bot:8080/api/notify-bulk-order-completed`

---

### support_bot/handlers/complaints.py
**Строк:** 256

Рассмотрение жалоб покупателей.

**Классы:**
- `class ComplaintStates(StatesGroup)`

**FSM:**
- `waiting_response = State()`

**Роуты:**
- `@router.callback_query(F.data == "complaints")`
- `@router.callback_query(F.data.startswith("complaint_detail:"))`
- `@router.callback_query(F.data.startswith("resolve_complaint:"))`

**Cross-imports:**
- `from support_bot.services.complaint_service import ComplaintService`
- `from shared.database.models import Complaint`

---

### support_bot/handlers/history.py
**Строк:** 269

История заказов и транзакций.

**Роуты:**
- `@router.callback_query(F.data == "order_history")`
- `@router.callback_query(F.data.startswith("history_order:"))`

**Cross-imports:**
- `from shared.database.models import Order`

---

### support_bot/handlers/manual_balance.py
**Строк:** 157

Ручная корректировка баланса.

**Классы:**
- `class ManualBalanceStates(StatesGroup)`

**FSM:**
- `waiting_user_id = State()`
- `waiting_amount = State()`
- `waiting_reason = State()`
- `confirm = State()`

**Роуты:**
- `@router.callback_query(F.data == "manual_balance")`
- `@router.message(ManualBalanceStates.waiting_user_id)`
- `@router.message(ManualBalanceStates.waiting_amount)`

**Cross-imports:**
- `from shared.services.ledger_service import LedgerService`
- `from support_bot.services.balance_service import BalanceService`

---

### support_bot/handlers/mass_broadcast.py
**Строк:** 161

Массовые рассылки администратора.

**Классы:**
- `class BroadcastFSM(StatesGroup)`

**FSM:**
- `waiting_message = State()`
- `waiting_audience = State()`
- `confirm = State()`

**Роуты:**
- `@router.callback_query(F.data == "mass_broadcast")`
- `@router.message(BroadcastFSM.waiting_message)`

**Cross-imports:**
- `from shared.database.models import Broadcast`

---

### support_bot/handlers/profile.py
**Строк:** 94

Профиль воркера.

**Роуты:**
- `@router.callback_query(F.data == "worker_profile")`

**Cross-imports:**
- `from support_bot.services.worker_service import WorkerService`

---

### support_bot/handlers/statistics.py
**Строк:** 301

Статистика для администратора.

**Роуты:**
- `@router.callback_query(F.data == "admin_stats")`
- `@router.callback_query(F.data == "worker_stats")`
- `@router.callback_query(F.data == "financial_stats")`

**Cross-imports:**
- `from shared.database.models import Order, Worker, Transaction`

---

### support_bot/handlers/user_info.py
**Строк:** 354

Поиск и просмотр информации о пользователях.

**Классы:**
- `class UserInfoStates(StatesGroup)`

**FSM:**
- `waiting_user_id = State()`
- `waiting_search = State()`

**Роуты:**
- `@router.callback_query(F.data == "user_lookup")`
- `@router.message(UserInfoStates.waiting_user_id)`

**Cross-imports:**
- `from shared.database.models import User, Order`

---

### support_bot/handlers/worker_withdrawal.py
**Строк:** 326

Управление выводами воркеров и отчётами о расходах.

**Классы:**
- `class WorkerWithdrawalStates(StatesGroup)`
- `class WorkerExpenseStates(StatesGroup)`

**FSM WorkerWithdrawalStates:**
- `waiting_amount = State()`
- `waiting_requisites = State()`
- `confirm = State()`

**FSM WorkerExpenseStates:**
- `waiting_category = State()`
- `waiting_amount = State()`
- `waiting_description = State()`
- `waiting_receipt = State()`

**Роуты:**
- `@router.callback_query(F.data == "request_worker_withdrawal")`
- `@router.callback_query(F.data == "expense_report")`
- `@router.message(WorkerWithdrawalStates.waiting_amount)`

**Cross-imports:**
- `from support_bot.services.balance_service import BalanceService`
- `from shared.database.models import WorkerWithdrawal, WorkerExpenseReport`

---

### support_bot/handlers/accounts.py
**Строк:** 288

Управление аккаунтами (AccountInventory).

**Роуты:**
- `@router.callback_query(F.data == "accounts_panel")`
- `@router.callback_query(F.data.startswith("account_category:"))`

**Cross-imports:**
- `from shared.database.models import AccountCategory, AccountItem, AccountInventory`
- `from support_bot.constants.buttons_accounts import AccountsAdminBtns`

---

### support_bot/handlers/uploader_panel.py
**Строк:** 61

Панель загрузчика (ограниченные права).

**Роуты:**
- `@router.callback_query(F.data == "uploader_panel")`

**Cross-imports:**
- `from support_bot.services.access_service import SupportBotActor`

---

## Keyboards (support_bot/keyboards/)

### support_bot/keyboards/inline.py
**Строк:** 518

**Функции (18 клавиатур):**
- `get_main_menu_keyboard(actor)`
- `get_orders_keyboard(orders)`
- `get_order_detail_keyboard(order, actor)`
- `get_moderation_queue_keyboard(items)`
- `get_bank_moderation_keyboard(bank)`
- `get_cc_moderation_keyboard(item)`
- `get_withdrawal_keyboard(withdrawals)`
- `get_complaint_keyboard(complaint)`
- `get_ticket_keyboard(ticket)`
- `get_user_info_keyboard(user)`
- `get_worker_stats_keyboard(worker)`
- `get_accountant_keyboard()`
- ... и другие

---

## Middlewares (support_bot/middlewares/)

### support_bot/middlewares/database.py
**Строк:** ~30

**Классы:**
- `class DatabaseMiddleware(BaseMiddleware)`

Инжектирует AsyncSession в handler data.

---

### support_bot/middlewares/worker_auth.py
**Строк:** ~100

**Классы:**
- `class WorkerAuthMiddleware(BaseMiddleware)`

**Cross-imports:**
- `from support_bot.services.access_service import SupportBotActor, SupportAccessService`
- `from shared.database.models import Worker, Admin`

---

## Services (support_bot/services/)

### support_bot/services/access_service.py
**Строк:** 150

**Классы:**
- `class SupportBotActor` — контекст прав текущего пользователя
- `class SupportAccessService`

**Поля SupportBotActor:**
- `is_worker`, `is_admin_like`
- `can_add_balance`, `can_moderate_sellers`, `can_manage_finance`
- `can_upload_catalogs`, `can_moderate`

**Cross-imports:**
- `from web_panel.auth import (ROLE_ADMIN, ROLE_SUPER_ADMIN, ...)`
- `from shared.database.models import Worker, Admin`

---

### support_bot/services/order_service.py
**Строк:** 492

**Классы:**
- `class OrderService`

**Функции:**
- `async def get_available_orders(session, worker_id, categories)`
- `async def take_order(session, order_id, worker_id) -> bool`
- `async def complete_order(session, order_id, result_text, files)`
- `async def mark_not_found(session, order_id, worker_id)`
- `async def cancel_order(session, order_id, worker_id)`
- `async def get_active_orders(session, worker_id)`
- `async def request_addinfo(session, order_id, message)`

**Cross-imports:**
- `from shared.database.models import Order, WorkerOrder, Worker`
- `from shared.services.worker_order_service import WorkerOrderService`

---

### support_bot/services/notification_service.py
**Строк:** 523

**Функции:**
- Уведомления администраторам/воркерам о событиях
- `async def notify_new_order(order, bot)`
- `async def notify_order_taken(order, worker, bot)`
- `async def notify_order_completed(order, worker, bot)`

**Cross-imports:**
- `from shared.services.admin_notification_service import AdminNotificationService`

---

### support_bot/services/order_delivery_service.py
**Строк:** 496

**Функции:**
- Доставка результатов заказа через Main Bot API
- `async def deliver_order_result(order_id, result_text, files)`

**API вызовы:**
- `POST http://main_bot:8080/api/notify-single-order-completed`
- `POST http://main_bot:8080/api/notify-bulk-item-completed`

---

### support_bot/services/order_notification_service.py
**Строк:** 231

**Функции:**
- `async def notify_new_order_to_workers(order, bot)`
- `async def notify_order_channel(order_data, bot)`

**API вызовы:**
- `POST http://main_bot:8080/api/notify-order-cancelled`

---

### support_bot/services/worker_service.py
**Строк:** 164

**Функции:**
- `async def get_or_create_worker(session, telegram_id, username)`
- `async def update_worker_stats(session, worker_id)`
- `async def get_worker_by_id(session, worker_id)`

**Cross-imports:**
- `from shared.database.models import Worker, WorkerStats`
- `from shared.services.worker_score_service import recalculate_worker_score`

---

### support_bot/services/balance_service.py
**Строк:** 74

**Классы:**
- `class BalanceService`

**Функции:**
- `async def add_balance(session, user_id, amount, reason)`
- `async def deduct_balance(session, user_id, amount, reason)`
- `async def get_balance(session, user_id) -> Decimal`

**Cross-imports:**
- `from shared.services.ledger_service import LedgerService`
- `from shared.database.models import User`

---

### support_bot/services/complaint_service.py
**Строк:** 55

**Функции:**
- `async def create_complaint(session, user_id, worker_id, order_id, reason)`
- `async def resolve_complaint(session, complaint_id, resolution)`

**Cross-imports:**
- `from shared.database.models import Complaint`

---

### support_bot/services/support_logger.py
**Строк:** 316

**Функции:**
- Логирование действий поддержки в NocoDB и в Telegram log-channel

**Cross-imports:**
- `from shared.services.nocodb_service import NocoDBService`
- `from shared.services.log_channel_service import LogChannelService`

---

### support_bot/services/worker_notification_service.py
**Строк:** 297

**Функции:**
- `async def notify_worker_reminder(order, worker, bot)`
- `async def send_order_reminder(task, bot)`

**Cross-imports:**
- `from shared.services.notification_service import NotificationService`

---

### support_bot/services/worker_reminder_service.py
**Строк:** 113

**Функции:**
- `async def run_worker_order_reminder_watcher(session_maker, bot)` — периодически проверяет и отправляет напоминания

**Cross-imports:**
- `from shared.services.worker_reminder_task_service import WorkerReminderTaskService`
- `from shared.database.tasks_session import get_tasks_session`

---

### support_bot/services/order_channel_service.py
**Строк:** 72

**Функции:**
- `async def send_order_to_channel(order_data, bot)` — отправка заказа в канал воркеров

---

## Utilities (support_bot/utils/)

### support_bot/utils/message_utils.py

**Функции:**
- `async def safe_edit(message, text, **kwargs)` — безопасное редактирование без исключений
- `async def safe_answer(message, text, **kwargs)` — безопасный ответ

---

### support_bot/utils/order_notifier.py
**Строк:** 70

**Функции:**
- Форматирование и отправка уведомлений о заказах

---

## Ролевая система (SupportBotActor)

| Флаг | Описание |
|---|---|
| `is_worker` | Обычный воркер |
| `is_admin_like` | Администратор или супер-администратор |
| `can_add_balance` | Права на ручную корректировку баланса |
| `can_moderate_sellers` | Модерация товаров продавцов |
| `can_manage_finance` | Управление финансами (выводы, транзакции) |
| `can_upload_catalogs` | Загрузка товаров в каталог |
| `can_moderate` | Базовые права модератора |

**Роли из [[Web Panel]]:** `ROLE_OWNER`, `ROLE_SUPER_ADMIN`, `ROLE_ADMIN`, `ROLE_CUSTOM`

---

## FSM-машины сводная таблица

| FSM | Файл | Состояния |
|---|---|---|
| `OrderStates` | orders.py | waiting_result → waiting_addinfo → waiting_bulk_item |
| `WorkStates` | work_orders.py | working → awaiting_file → awaiting_bulk |
| `FileStates` | files.py | waiting_file → waiting_description |
| `ComplaintStates` | complaints.py | waiting_response |
| `RequestChangesStates` | seller_moderation.py | waiting_message |
| `ModCCSearchStates` | seller_moderation.py | waiting_query |
| `RejectOrderStates` | seller_orders.py | waiting_reason |
| `ManualBalanceStates` | manual_balance.py | waiting_user_id → waiting_amount → waiting_reason → confirm |
| `BroadcastFSM` | mass_broadcast.py | waiting_message → waiting_audience → confirm |
| `UserInfoStates` | user_info.py | waiting_user_id → waiting_search |
| `WorkerWithdrawalStates` | worker_withdrawal.py | waiting_amount → waiting_requisites → confirm |
| `WorkerExpenseStates` | worker_withdrawal.py | waiting_category → waiting_amount → waiting_description → waiting_receipt |
| `UploadProductStates` | upload_product.py | waiting_category → waiting_file → waiting_price → waiting_name → confirm |
| `UploadAccountStates` | upload_product.py | waiting_category → waiting_data → confirm |
| `CreateTicketFSM` | tickets.py | waiting_category → waiting_subject → waiting_message |
| `ReplyTicketFSM` | tickets.py | waiting_reply |
| `ESIMAdminStates` | esim.py | waiting_config → waiting_assign |

---

## API-вызовы к Main Bot

| Метод | URL | Когда |
|---|---|---|
| POST | `http://main_bot:8080/api/notify-order-cancelled` | Отмена заказа |
| POST | `http://main_bot:8080/api/notify-addinfo-completed` | Дополнительная информация отправлена |
| POST | `http://main_bot:8080/api/notify-bulk-item-completed` | Завершён элемент bulk-заказа |
| POST | `http://main_bot:8080/api/notify-bulk-order-completed` | Завершён bulk-заказ |
| POST | `http://main_bot:8080/api/notify-single-order-completed` | Завершён обычный заказ |

---

## Зависимости

- [[Shared Services]] — LedgerService, AdminNotificationService, WorkerOrderService, NocoDBService, LogChannelService
- [[Seller Bot]] — seller_bot.config (для mini app URL), seller_bot.keyboards
- [[Web Panel]] — web_panel.auth (роли ROLE_ADMIN, ROLE_SUPER_ADMIN), web_panel.constants.categories
- [[DB Models]] — все модели через `shared.database.models`
