# Seller Bot — seller_bot/

[[MOC]] > Seller Bot

**45 файлов** | aiogram 3.x | 4 языка (EN, RU, ZH, ES) | 13+ FSM-машин | Python 3.9+

---

## seller_bot/__init__.py
**Строк:** 1

---

## seller_bot/bot.py
**Строк:** 142

**Функции:**
- `def _validate_seller_bot_startup() -> None`
- `async def main()`
- `async def _global_error_handler(event, **kwargs)`

**Cross-imports:**
- `from seller_bot.config import seller_bot_config`
- `from seller_bot.handlers import (...)`
- `from seller_bot.middlewares.database import DatabaseMiddleware`
- `from seller_bot.middlewares.seller_auth import SellerAuthMiddleware`
- `from seller_bot.middlewares.language import SellerLanguageMiddleware`
- `from shared.config.env_utils import StartupValidationError, validate_startup_env`
- `from shared.database.session import async_session_maker`
- `from shared.database.tasks_session import init_tasks_db`
- `from shared.middlewares.error_logging import GlobalErrorLoggingMiddleware`
- `from seller_bot.services.weekly_report_service import run_weekly_report_service`
- `from seller_bot.services.auto_payout_service import run_auto_payout_watcher`

**TODO/заглушки:** 1

---

## seller_bot/config.py
**Строк:** 19

**Классы:**
- `class SellerBotConfig`

**Функции:**
- `def __post_init__(self)`

**Cross-imports:**
- `from shared.config.env_utils import parse_int_list_env`

---

## seller_bot/run.py
**Строк:** ~10

---

## seller_bot/utils.py
**Строк:** ~20

**Функции:**
- `get_seller_unread_count(...)` — количество непрочитанных сообщений

---

## Константы (seller_bot/constants/)

### seller_bot/constants/buttons_en.py
**Строк:** 53

**Классы:**
- `class ButtonTexts` — все тексты кнопок на английском

---

### seller_bot/constants/buttons_es.py
**Строк:** 32

**Классы:**
- `class ButtonTexts(EnglishButtonTexts)` — переопределение на испанский

**Cross-imports:**
- `from seller_bot.constants.buttons_en import ButtonTexts as EnglishButtonTexts`

---

### seller_bot/constants/buttons_ru.py
**Строк:** 56

**Классы:**
- `class ButtonTexts(EnglishButtonTexts)` — переопределение на русский

**Cross-imports:**
- `from seller_bot.constants.buttons_en import ButtonTexts as EnglishButtonTexts`

---

### seller_bot/constants/buttons_zh.py
**Строк:** 32

**Классы:**
- `class ButtonTexts(EnglishButtonTexts)` — переопределение на китайский

**Cross-imports:**
- `from seller_bot.constants.buttons_en import ButtonTexts as EnglishButtonTexts`

---

### seller_bot/constants/language_loader.py
**Строк:** 26

**Функции:**
- Загрузка нужного языкового пакета по коду языка

---

### seller_bot/constants/texts_en.py / texts_ru.py / texts_zh.py / texts_es.py
Тексты сообщений бота на 4 языках.

---

## Handlers (seller_bot/handlers/)

### seller_bot/handlers/start.py
**Строк:** 426

Регистрация нового продавца, онбординг, депозит (BTCPay интеграция).

**FSM:**
- Нет отдельной StatesGroup, но использует SellerDepositService

**Роуты:**
- `@router.message(CommandStart())`
- `@router.callback_query(F.data == "seller_register")`
- `@router.callback_query(F.data.startswith("deposit_package:"))`
- `@router.callback_query(F.data == "check_payment")`
- `@router.callback_query(F.data == "main_menu")`

**Cross-imports:**
- `from shared.services.seller_deposit_service import SellerDepositService`
- `from shared.services.ledger_service import LedgerService`
- `from seller_bot.services.seller_service import SellerService`

---

### seller_bot/handlers/stock.py
**Строк:** 1002

Управление банковскими аккаунтами (добавление, редактирование, публикация).

**Классы:**
- `class AddBankStates(StatesGroup)`

**FSM:**
- `product_type = State()`
- `category = State()`
- `bank_type = State()`
- `name = State()`
- `price = State()`
- `description = State()`
- `instruction = State()`
- `state_field = State()` (US State)
- `zip_code = State()`
- `confirm = State()`

**Роуты:**
- `@router.callback_query(F.data == "manage_stock")`
- `@router.callback_query(F.data == "add_bank")`
- `@router.callback_query(F.data.startswith("bank_type:"))`
- `@router.message(AddBankStates.name)`
- `@router.message(AddBankStates.price)`
- `@router.message(AddBankStates.description)`
- `@router.callback_query(F.data.startswith("edit_bank:"))`
- `@router.callback_query(F.data.startswith("toggle_bank:"))`
- `@router.callback_query(F.data.startswith("delete_bank:"))`

**Cross-imports:**
- `from seller_bot.services.stock_service import StockService`
- `from shared.services.moderation_pricing_service import ...`
- `from shared.database.models import SellerBank`

---

### seller_bot/handlers/cc_stock.py
**Строк:** 511

Управление CC-картами продавца.

**Классы:**
- `class AddCCStates(StatesGroup)`

**FSM:**
- `category = State()`
- `non_vbv = State()`
- `mode = State()`
- `type = State()`
- `name = State()`
- `price = State()`
- `description = State()`

**Роуты:**
- `@router.callback_query(F.data == "manage_cc")`
- `@router.callback_query(F.data == "add_cc")`
- `@router.message(AddCCStates.name)`
- `@router.message(AddCCStates.price)`

**Cross-imports:**
- `from seller_bot.services.cc_stock_service import CCStockService`
- `from shared.database.models import SellerCCItem`

---

### seller_bot/handlers/brute_bank.py
**Строк:** 704

Загрузка брутованных банковских аккаунтов.

**Классы:**
- `class BruteUploadStates(StatesGroup)`

**FSM:**
- `mode = State()`
- `bank_name = State()`
- `code = State()`
- `attributes = State()`
- `group_select = State()`
- `upload_data = State()`
- `confirm = State()`

**Роуты:**
- `@router.callback_query(F.data == "brute_upload")`
- `@router.message(BruteUploadStates.bank_name)`
- `@router.message(BruteUploadStates.upload_data)`

**Cross-imports:**
- `from shared.services.seller_upload_pipeline_service import SellerUploadPipelineService`
- `from shared.database.models import BruteBankGroup, BruteBankItem`

---

### seller_bot/handlers/orders.py
**Строк:** 574

Управление заказами продавца и спорами.

**Классы:**
- `class CompleteOrderStates(StatesGroup)`

**FSM:**
- `waiting_result = State()`

**Роуты:**
- `@router.callback_query(F.data == "my_orders")`
- `@router.callback_query(F.data.startswith("order_detail:"))`
- `@router.callback_query(F.data.startswith("order_respond:"))`
- `@router.callback_query(F.data.startswith("dispute_reply:"))`
- `@router.callback_query(F.data.startswith("dispute_accept:"))`
- `@router.callback_query(F.data.startswith("dispute_escalate:"))`

**Cross-imports:**
- `from shared.services.seller_dispute_service import SellerDisputeService`
- `from shared.services.seller_order_delivery_service import ...`
- `from shared.database.models import SellerOrder, SellerOrderDispute`

---

### seller_bot/handlers/chat.py
**Строк:** 444

Чат продавца с покупателем.

**Классы:**
- `class SellerChatStates(StatesGroup)`

**FSM:**
- `chatting = State()`

**Роуты:**
- `@router.callback_query(F.data == "my_chats")`
- `@router.callback_query(F.data.startswith("open_conv:"))`
- `@router.message(SellerChatStates.chatting)`

**Cross-imports:**
- `from shared.services.seller_conversation_service import ...`
- `from shared.utils.chat_render import build_chat_text, seller_chat_keyboard`
- `from shared.database.models import SellerConversation, SellerChat`

---

### seller_bot/handlers/profile.py
**Строк:** 160

Профиль продавца: статистика, рейтинг, настройки.

**Роуты:**
- `@router.callback_query(F.data == "my_profile")`
- `@router.callback_query(F.data == "reputation_info")`

**Cross-imports:**
- `from shared.services.reputation_service import get_seller_badge`
- `from shared.services.ledger_projection_service import LedgerProjectionService`

---

### seller_bot/handlers/withdrawal.py
**Строк:** 145

Вывод средств продавца.

**Классы:**
- `class WithdrawalStates(StatesGroup)`

**FSM:**
- `waiting_amount = State()`
- `waiting_requisites = State()`

**Роуты:**
- `@router.callback_query(F.data == "request_withdrawal")`
- `@router.message(WithdrawalStates.waiting_amount)`
- `@router.message(WithdrawalStates.waiting_requisites)`

**Cross-imports:**
- `from shared.services.seller_finance_service import SellerFinanceService`
- `from shared.services.ledger_service import LedgerService`
- `from shared.database.models import SellerWithdrawal`

---

### seller_bot/handlers/upload_fsm.py
**Строк:** 703

Универсальный FSM-загрузчик для новых типов товаров.

**Классы:**
- `class UploadFSM(StatesGroup)`

**FSM:**
- `template_select = State()`
- `category = State()`
- `type_select = State()`
- `data_input = State()`
- `price = State()`
- `preview = State()`
- `confirm = State()`

**Роуты:**
- `@router.callback_query(F.data == "upload_new")`
- `@router.callback_query(F.data.startswith("upload_template:"))`
- `@router.message(UploadFSM.data_input)`

**Cross-imports:**
- `from shared.services.seller_upload_pipeline_service import SellerUploadPipelineService`
- `from shared.services.seller_upload_batch_service import SellerUploadBatchService`

---

### seller_bot/handlers/uploads.py
**Строк:** 158

Список загруженных батчей продавца.

**Роуты:**
- `@router.callback_query(F.data == "my_uploads")`
- `@router.callback_query(F.data.startswith("upload_batch:"))`

**Cross-imports:**
- `from shared.services.seller_upload_batch_service import SellerUploadBatchService`

---

### seller_bot/handlers/listings.py
**Строк:** 297

Мои листинги: просмотр опубликованных позиций.

**Роуты:**
- `@router.callback_query(F.data == "my_listings")`
- `@router.callback_query(F.data.startswith("listing_detail:"))`
- `@router.callback_query(F.data.startswith("toggle_listing:"))`

**Cross-imports:**
- `from shared.database.models import SellerBank, SellerCCItem`

---

### seller_bot/handlers/helpers.py
**Строк:** 243

Управление командой (хелперами) продавца.

**Роуты:**
- `@router.callback_query(F.data == "manage_team")`
- `@router.callback_query(F.data.startswith("helper_detail:"))`
- `@router.callback_query(F.data.startswith("helper_action:"))`

**Cross-imports:**
- `from shared.services.seller_helper_service import SellerHelperService`
- `from shared.database.models import SellerHelper`

---

### seller_bot/handlers/special_products.py
**Строк:** 842

Специальные типы товаров: NFC, OTP, Enroll, Check.

**Классы:**
- `class AddNFCStates(StatesGroup)`
- `class AddOTPStates(StatesGroup)`
- `class AddEnrollStates(StatesGroup)`
- `class AddCheckStates(StatesGroup)`

**FSM для NFC:**
- `nfc_type = State()`, `bank_name = State()`, `country = State()`, `state_field = State()`, `zip_code = State()`, `price = State()`, `file_input = State()`

**FSM для OTP:**
- `bank_name = State()`, `balance = State()`, `has_fullz = State()`, `sms_access = State()`, `price = State()`

**Роуты:**
- `@router.callback_query(F.data == "add_nfc")`
- `@router.callback_query(F.data == "add_otp")`
- `@router.callback_query(F.data == "add_enroll")`
- `@router.callback_query(F.data == "add_check")`

**Cross-imports:**
- `from shared.services.seller_upload_pipeline_service import SellerUploadPipelineService`
- `from shared.database.models import SellerNFCItem, SellerOTPItem, SellerEnrollItem, SellerCheckItem`

---

### seller_bot/handlers/documents.py
**Строк:** 461

Документы (паспорта, водительские удостоверения).

**Классы:**
- `class AddDocumentStates(StatesGroup)`

**FSM:**
- `doc_type = State()`
- `state_field = State()`
- `quality = State()`
- `has_hologram = State()`
- `has_selfie = State()`
- `description = State()`
- `price = State()`
- `sample_file = State()`

**Роуты:**
- `@router.callback_query(F.data == "add_document")`
- `@router.message(AddDocumentStates.doc_type)`

**Cross-imports:**
- `from shared.database.models import SellerDocumentItem`

---

### seller_bot/handlers/fullz.py
**Строк:** 637

Fullz (полные данные физических лиц).

**Классы:**
- `class AddFullzStates(StatesGroup)`

**FSM:**
- `fullz_type = State()`
- `state_field = State()`
- `credit_score = State()`
- `age_range = State()`
- `gender = State()`
- `company_type = State()`
- `loan_size = State()`
- `report_group = State()`
- `quantity = State()`
- `price = State()`
- `data_file = State()`

**Cross-imports:**
- `from shared.database.models import SellerFullzItem`

---

### seller_bot/handlers/bulk_import.py
**Строк:** 246

Массовый CSV-импорт товаров.

**Классы:**
- `class BulkImportFSM(StatesGroup)`

**FSM:**
- `waiting_file = State()`
- `confirming = State()`

**Роуты:**
- `@router.callback_query(F.data == "bulk_import")`
- `@router.message(BulkImportFSM.waiting_file, F.document)`

**Cross-imports:**
- `from shared.services.seller_upload_pipeline_service import SellerUploadPipelineService`

---

### seller_bot/handlers/broadcast.py
**Строк:** 98

Рассылка покупателям продавца.

**Классы:**
- `class BroadcastStates(StatesGroup)`

**FSM:**
- `waiting_message = State()`

**Роуты:**
- `@router.callback_query(F.data == "send_broadcast")`
- `@router.message(BroadcastStates.waiting_message)`

---

## Keyboards (seller_bot/keyboards/)

### seller_bot/keyboards/inline.py
**Строк:** 376

**Функции (30 клавиатур):**
- `get_main_menu_keyboard(seller, btns)`
- `get_stock_keyboard(seller, btns)`
- `get_orders_keyboard(orders, btns)`
- `get_order_detail_keyboard(order, btns)`
- `get_dispute_keyboard(dispute, btns)`
- `get_bank_list_keyboard(banks, btns)`
- `get_bank_detail_keyboard(bank, btns)`
- `get_cc_list_keyboard(items, btns)`
- `get_brute_groups_keyboard(groups, btns)`
- `get_upload_types_keyboard(btns)`
- `get_batch_list_keyboard(batches, btns)`
- `get_team_keyboard(helpers, btns)`
- `get_withdrawal_methods_keyboard(btns)`
- `get_deposit_packages_keyboard(packages, btns)`
- ... и другие

---

## Middlewares (seller_bot/middlewares/)

### seller_bot/middlewares/database.py
**Строк:** ~30

**Классы:**
- `class DatabaseMiddleware(BaseMiddleware)`

Инжектирует AsyncSession в handler data.

---

### seller_bot/middlewares/seller_auth.py
**Строк:** ~100

**Классы:**
- `class SellerAuthMiddleware(BaseMiddleware)`
- `class SellerActorContext`

Аутентификация продавца и его хелперов. Использует `SellerActorContext` из [[Shared Services]].

**Cross-imports:**
- `from shared.services.seller_actor_service import resolve_seller_actor, SellerActorContext`
- `from shared.database.models import Seller`

---

### seller_bot/middlewares/language.py
**Строк:** ~40

**Классы:**
- `class SellerLanguageMiddleware(BaseMiddleware)`

Загружает языковой пакет и инжектирует `btns`/`texts` в handler data.

---

## Services (seller_bot/services/)

### seller_bot/services/seller_service.py
**Строк:** 172

**Функции:**
- `async def get_or_create_seller(session, telegram_id, username)`
- `async def get_seller_by_id(session, seller_id)`
- `async def update_seller(session, seller, **kwargs)`
- `async def get_seller_stats(session, seller_id)`

**Cross-imports:**
- `from shared.database.models import Seller`

---

### seller_bot/services/stock_service.py
**Строк:** 228

**Функции:**
- `async def create_bank(session, seller_id, data)`
- `async def get_bank_list(session, seller_id, page)`
- `async def update_bank(session, bank_id, **kwargs)`
- `async def toggle_bank_publish(session, bank_id)`
- `async def delete_bank(session, bank_id)`
- `async def get_pending_moderation_count(session, seller_id)`

**Cross-imports:**
- `from shared.database.models import SellerBank`
- `from shared.services.seller_upload_batch_service import SellerUploadBatchService`

---

### seller_bot/services/cc_stock_service.py
**Строк:** 104

**Функции:**
- `async def create_cc_item(session, seller_id, data)`
- `async def get_cc_list(session, seller_id)`
- `async def update_cc_item(session, item_id, **kwargs)`

**Cross-imports:**
- `from shared.database.models import SellerCCItem`

---

### seller_bot/services/special_stock_service.py
**Строк:** 120

**Функции:**
- Создание/получение NFC, OTP, Enroll, Check позиций

**Cross-imports:**
- `from shared.database.models import SellerNFCItem, SellerOTPItem, SellerEnrollItem`

---

### seller_bot/services/auto_payout_service.py
**Строк:** 101

**Функции:**
- `async def run_auto_payout_watcher(session_maker)` — периодически проверяет и выплачивает auto_payout

**Cross-imports:**
- `from shared.services.seller_deposit_service import SellerDepositService`
- `from shared.services.ledger_service import LedgerService`

---

### seller_bot/services/weekly_report_service.py
**Строк:** 172

**Функции:**
- `async def run_weekly_report_service(session_maker, bot)` — еженедельный отчёт продавцам

**Cross-imports:**
- `from shared.database.models import Seller`
- `from shared.services.ledger_projection_service import LedgerProjectionService`

---

## FSM-машины сводная таблица

| FSM | Файл | Состояния |
|---|---|---|
| `AddBankStates` | stock.py | product_type → category → bank_type → name → price → description → instruction → state → zip → confirm |
| `AddCCStates` | cc_stock.py | category → non_vbv → mode → type → name → price → description |
| `BruteUploadStates` | brute_bank.py | mode → bank_name → code → attributes → group_select → upload_data → confirm |
| `CompleteOrderStates` | orders.py | waiting_result |
| `SellerChatStates` | chat.py | chatting |
| `WithdrawalStates` | withdrawal.py | waiting_amount → waiting_requisites |
| `UploadFSM` | upload_fsm.py | template_select → category → type_select → data_input → price → preview → confirm |
| `AddNFCStates` | special_products.py | nfc_type → bank_name → country → state → zip → price → file_input |
| `AddOTPStates` | special_products.py | bank_name → balance → has_fullz → sms_access → price |
| `AddDocumentStates` | documents.py | doc_type → state → quality → hologram → selfie → description → price → sample_file |
| `AddFullzStates` | fullz.py | fullz_type → state → credit_score → age_range → gender → company_type → loan_size → report_group → quantity → price → data_file |
| `BulkImportFSM` | bulk_import.py | waiting_file → confirming |
| `BroadcastStates` | broadcast.py | waiting_message |

---

## Зависимости

- [[Shared Services]] — LedgerService, SellerDepositService, SellerUploadPipelineService, NocoDB, AdminNotificationService, SellerDisputeService, SellerConversationService
- [[Web Panel]] — seller moderation через API (approve/reject via admin)
- [[Support Bot]] — dispute_service, conversation_service
- [[DB Models]] — все модели через `shared.database.models`
