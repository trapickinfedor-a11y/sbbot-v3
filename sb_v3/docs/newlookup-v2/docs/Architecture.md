# Architecture — Общая архитектура NewLookup

[[MOC]] > Architecture

## Стек технологий

| Слой | Технологии |
|---|---|
| Backend (Telegram боты) | Python 3.9+, aiogram 3.x |
| Backend (Web API) | FastAPI, Uvicorn, Pydantic |
| ORM / БД | SQLAlchemy 2.x async, SQLite (основная + tasks) |
| Frontend | React 19 + TypeScript, Vite 6 |
| UI компоненты | shadcn/ui, Tailwind CSS |
| Шаблоны (веб-панель) | Jinja2 |
| Асинхронность | asyncio, async/await everywhere |
| Платежи | BTCPay Server |
| Внешние интеграции | NocoDB, Telegram WebApp SDK |
| Контейнеризация | Docker Compose (381 строка) |
| Аутентификация | JWT Bearer (веб-панель), Telegram initData (mini app) |

---

## Компоненты системы

| Компонент | Порт | Файлов | Описание |
|---|---|---|---|
| [[Seller Bot]] | — | 45 | Telegram-бот для продавцов |
| [[Support Bot]] | — | 51 | Telegram-бот для воркеров/поддержки |
| Main Bot | :8080 | 34 | Mirror bot management + HTTP API |
| [[Web Panel]] | :8000 | 204 | Admin-панель FastAPI + Jinja2 |
| [[Lookup API]] | :8001 | 3 | SSN/DL/CreditReport API (автономный) |
| [[Shared Services]] | — | 78 | Общие сервисы, модели, middleware |
| [[Mini App]] | (под :8000) | 83 | React 19 Seller Mini App V2 |

---

## Конфигурация

### .env
**Строк:** 57

Содержит:
- `SELLER_BOT_TOKEN`, `SUPPORT_BOT_TOKEN`
- `DATABASE_URL` — SQLite или PostgreSQL
- `ADMIN_IDS` — Telegram ID администраторов
- `BTCPAY_*` — настройки BTCPay
- `NOCODB_*` — настройки NocoDB
- `JWT_SECRET`
- `INTERNAL_API_TOKEN` — для inter-service аутентификации
- `REDIS_URL` — для MenuCountCacheService (опционально)
- `MAPS_*` — Google Maps API

### docker-compose.yml
**Строк:** 381

Сервисы:
- `seller_bot`
- `support_bot`
- `main_bot`
- `web_panel`
- `lookup_api`
- Volumes для SQLite файлов и медиа

---

## Main Bot (34 файла)

Управляет зеркальными Telegram-ботами и предоставляет HTTP API для уведомлений.

### main_bot/__init__.py
**Строк:** 1

### main_bot/app/__init__.py
**Строк:** 1

### main_bot/app/api/__init__.py
**Строк:** 1

### main_bot/app/api/bot_management.py
**Строк:** 67

**Классы:**
- `BotStatusUpdate(BaseModel)`

**Функции:**
- `async def toggle_bot_status(data: BotStatusUpdate)`
- `async def get_bot_status(bot_id: int)`
- `def set_mirror_bot_service(service)`

**Роуты:**
- `@app.post("/bot/toggle")`
- `@app.get("/bot/status/{bot_id}")`

**Cross-imports:**
- `from shared.security.internal_api import verify_internal_api_request`

---

### main_bot/app/api/notifications.py
**Строк:** 860

**Классы:**
- `BulkItemNotificationData(BaseModel)`
- `BulkOrderCompletionData(BaseModel)`
- `SingleOrderNotificationData(BaseModel)`
- `AddInfoNotificationData(BaseModel)`
- `BalanceUpdateNotificationData(BaseModel)`
- `OrderCancellationData(BaseModel)`

**Функции (14):**
- `async def get_db()`
- `async def get_mirror_bot_instance(mirror_bot_id: int, session)`
- `async def get_user_language(session: AsyncSession, user_id)`
- `def get_multilingual_texts(language: str)`
- `def get_service_name_multilingual(service_name: str, language)`
- `def format_customer_data(customer_data: Dict[str, Any])`
- `def _compose_delivery_caption(base_caption, files)`
- `async def send_files_in_groups(bot, user_id, files)`
- `async def notify_bulk_item_completed(...)`
- `async def notify_bulk_order_completed(...)`
- `async def notify_single_order_completed(...)`
- `async def notify_addinfo_completed(...)`
- `async def notify_balance_update(...)`
- `async def notify_order_cancelled(...)`

**Роуты:**
- `@app.post("/notify-bulk-item-completed")`
- `@app.post("/notify-bulk-order-completed")`
- `@app.post("/notify-single-order-completed")`
- `@app.post("/notify-addinfo-completed")`
- `@app.post("/notify-balance-update")`
- `@app.post("/notify-order-cancelled")`

**Cross-imports:**
- `from shared.database.session import get_session`
- `from shared.database.models import MirrorBot, User`
- `from shared.security.internal_api import verify_internal_api_request`

**TODO/заглушки:** 1

---

### main_bot/app/api/server.py
**Строк:** 53

**Функции:**
- `async def lifespan(app: FastAPI)`
- `async def start_http_server()`

**Cross-imports:**
- `from main_bot.app.api.notifications import app as notifications_app`
- `from main_bot.app.api.bot_management import app as bot_management_app`
- `from main_bot.app.api.user_orders import app as user_orders_app`

**API вызовы:**
- `app.mount("/api/v1", user_orders_app)` — монтирует user_orders_app

---

### main_bot/app/api/user_orders.py
**Строк:** 196

**Классы:**
- `SellerInfo(BaseModel)`
- `ProductInfo(BaseModel)`
- `OrderHistoryItem(BaseModel)`
- `PaginatedOrderHistory(BaseModel)`
- `SetArchiveChannelRequest(BaseModel)`
- `CouponActivateRequest(BaseModel)`

**Функции:**
- `async def get_db()`
- `async def get_current_user(...)`
- `async def get_my_orders(...)`
- `async def set_archive_channel(...)`
- `async def activate_coupon(...)`

**Роуты:**
- `@app.get("/orders/my", response_model=PaginatedOrderHistory)`
- `@app.post("/users/me/set-archive-channel")`
- `@app.post("/coupons/activate")`

**Cross-imports:**
- `from shared.database.models import MirrorBot, User`
- `from shared.services.coupon_service import CouponService`
- `from shared.utils.telegram_auth import validate_telegram_init_data`

---

### main_bot/app/config.py
**Строк:** 26

**Классы:**
- `class Config`

**Функции:**
- `def from_env(cls)`
- `def video_file_exists(self) -> bool`

---

### main_bot/app/constants/__init__.py
**Строк:** 1

### main_bot/app/constants/config.py
**Строк:** 9

**Классы:**
- `class AppConstants`

### main_bot/app/constants/texts.py
**Строк:** 43

**Классы:**
- `class BotTexts`

**Функции:**
- `def bot_confirmed(bot_username: str) -> str`

---

### main_bot/app/domain/__init__.py
**Строк:** 1

### main_bot/app/domain/entities.py
**Строк:** 20

**Классы:**
- `class MirrorBot` (domain entity, не ORM)

**Функции:**
- `def create(cls, user_id: int, bot_token: str, bot_username: ...)`

---

### main_bot/app/handlers/__init__.py
**Строк:** 1

### main_bot/app/handlers/owner_cabinet.py
**Строк:** 352

**Классы:**
- `class WithdrawStates(StatesGroup)`

**Функции (12):**
- `async def _get_owner_keyboard(has_bots: bool)`
- `def _build_month_chart_text(chart: dict) -> str`
- `async def owner_cabinet_callback(callback, mirror_service, state)`
- `async def owner_stats_callback(callback, mirror_service)`
- `async def owner_month_chart_callback(callback, mirror_service)`
- `async def owner_withdraw_history_callback(callback, mirror_service)`
- `async def owner_withdraw_start(callback, mirror_service, state)`
- `async def owner_withdraw_amount(message, state)`
- `async def owner_withdraw_method(callback, state)`
- `async def owner_withdraw_network(callback, state)`
- `async def owner_withdraw_requisites(message, state)`
- `async def owner_create_bot_callback(callback, mirror_service)`

**Роуты:**
- `@router.callback_query(F.data == "owner_cabinet")`
- `@router.callback_query(F.data == "owner_stats")`
- `@router.callback_query(F.data == "owner_month_chart")`
- `@router.callback_query(F.data == "owner_withdraw_history")`
- `@router.callback_query(F.data == "owner_withdraw")`
- `@router.message(WithdrawStates.waiting_amount, F.text)`
- `@router.callback_query(F.data.startswith("owner_method:"))`
- `@router.callback_query(F.data.startswith("owner_network:"))`
- `@router.message(WithdrawStates.waiting_requisites, F.text)`
- `@router.callback_query(F.data == "owner_create_bot")`

**FSM:**
- `waiting_amount = State()`
- `waiting_method = State()`
- `waiting_network = State()`
- `waiting_requisites = State()`

**Cross-imports:**
- `from shared.services.bot_owner_service import (...)`
- `from shared.services.ledger_projection_service import LedgerProjectionService`
- `from shared.services.ledger_service import LedgerService`

---

### main_bot/app/handlers/start.py
**Строк:** 53

**Функции:**
- `async def start_handler(message: Message, mirror_service: MirrorBotService)`

**Роуты:**
- `@router.message(CommandStart())`

**Cross-imports:**
- `from main_bot.app.services.mirror_bot import MirrorBotService`
- `from main_bot.app.keyboards.main_menu import get_main_menu_keyboard, get_bot_active_keyboard`

---

### main_bot/app/handlers/token.py
**Строк:** 33

**Функции:**
- `async def token_handler(message: Message, mirror_service: MirrorBotService)`

**Роуты:**
- `@router.message(lambda message: message.text and TOKEN_PATTERN.match(message.text))`

**Cross-imports:**
- `from main_bot.app.services.mirror_bot import MirrorBotService`

---

### main_bot/app/keyboards/__init__.py
**Строк:** 1

### main_bot/app/keyboards/main_menu.py
**Строк:** 18

**Функции:**
- `def get_main_menu_keyboard() -> InlineKeyboardMarkup`
- `def get_bot_active_keyboard(bot_username: str) -> InlineKeyboardMarkup`

**Cross-imports:**
- `from main_bot.app.constants.config import AppConstants`

---

### main_bot/app/main.py
**Строк:** 104

**Функции:**
- `def _validate_main_bot_startup() -> None`
- `def create_repository() -> BotRepository`
- `async def start_bot_polling(mirror_service: MirrorBotService)`
- `async def main()`

**Cross-imports:**
- `from main_bot.app.services.mirror_bot import MirrorBotService`
- `from main_bot.app.middleware.logging import LoggingMiddleware`
- `from main_bot.app.middleware.ban_check import MainBotBanCheckMiddleware`
- `from main_bot.app.middleware.mirror_service import MirrorServiceMiddleware`
- `from main_bot.app.api.server import start_http_server`
- `from shared.middlewares.error_logging import GlobalErrorLoggingMiddleware`

**TODO/заглушки:** 1

---

### main_bot/app/middleware/__init__.py
**Строк:** 1

### main_bot/app/middleware/ban_check.py
**Строк:** 81

**Классы:**
- `class MainBotBanCheckMiddleware(BaseMiddleware)`

**Функции:**
- `async def __call__(...)`

**Cross-imports:**
- `from shared.database.models import User`

---

### main_bot/app/middleware/error_handler.py
**Строк:** 27

**Классы:**
- `class ErrorHandlerMiddleware(BaseMiddleware)`

**Функции:**
- `async def __call__(...)`

---

### main_bot/app/middleware/logging.py
**Строк:** 26

**Классы:**
- `class LoggingMiddleware(BaseMiddleware)`

**Функции:**
- `async def __call__(...)`

---

### main_bot/app/middleware/mirror_service.py
**Строк:** 18

**Классы:**
- `class MirrorServiceMiddleware(BaseMiddleware)`

**Функции:**
- `def __init__(self, mirror_service)`
- `async def __call__(...)`

---

### main_bot/app/repository/__init__.py
**Строк:** 1

### main_bot/app/repository/base.py
**Строк:** 39

**Классы:**
- `class BotRepository(ABC)` — абстрактный репозиторий

**Функции (8 абстрактных методов):**
- `async def create(self, bot: MirrorBot) -> MirrorBot`
- `async def get_by_token(self, bot_token: str) -> Optional[MirrorBot]`
- `async def get_by_user_id(self, user_id: int) -> Optional[MirrorBot]`
- `async def get_by_id(self, bot_id: int) -> Optional[MirrorBot]`
- `async def get_all(self) -> List[MirrorBot]`
- `async def reactivate(self, bot_id: int, bot_username: Optional[str])`
- `async def delete_by_user_id(self, user_id: int) -> bool`
- `async def init_db(self)`

**TODO/заглушки:** 8 (`pass` в абстрактных методах)

---

### main_bot/app/repository/postgres.py
**Строк:** 138

**Классы:**
- `class PostgresBotRepository(BotRepository)`

**Функции (9):**
- `async def init_db(self)`
- `async def create(self, bot: MirrorBotEntity) -> MirrorBotEntity`
- `async def get_by_token(self, bot_token: str)`
- `async def get_by_user_id(self, user_id: int)`
- `async def get_all_by_user_id(self, user_id: int) -> List`
- `async def get_by_id(self, bot_id: int)`
- `async def get_all(self) -> List`
- `async def reactivate(self, bot_id: int, bot_username: Optional[str])`
- `async def delete_by_user_id(self, user_id: int) -> bool`

**Cross-imports:**
- `from shared.database.models import MirrorBot as MirrorBotModel`
- `from shared.database.session import async_session_maker, init_db`

---

### main_bot/app/repository/sqlite.py
**Строк:** 122

**Классы:**
- `class SQLiteBotRepository(BotRepository)`

**Функции (8):**
- `def __init__(self, db_path: str)`
- `async def init_db(self)`
- `async def create(self, bot: MirrorBot) -> MirrorBot`
- `async def get_by_user_id(self, user_id: int)`
- `async def get_all(self) -> List`
- `async def get_by_token(self, bot_token: str)`
- `async def reactivate(self, bot_id: int, bot_username: Optional[str])`
- `async def delete_by_user_id(self, user_id: int) -> bool`

---

### main_bot/app/services/__init__.py
**Строк:** 1

### main_bot/app/services/mirror_bot.py
**Строк:** 255

**Классы:**
- `class MirrorBotService`

**Функции (14):**
- `def __init__(self, repository: BotRepository)`
- `async def validate_token(self, token: str) -> Optional[dict]`
- `async def start_mirror_bot(self, user_id: int, bot_token: str)`
- `async def _launch_bot(self, mirror_bot: MirrorBot)`
- `async def _run_polling(self, dp, bot, bot_id)`
- `async def stop_mirror_bot(self, user_id: int) -> bool`
- `async def restore_all_bots(self)`
- `async def get_user_bot(self, user_id: int) -> Optional[MirrorBot]`
- `async def get_user_bots(self, user_id: int) -> list[MirrorBot]`
- `async def shutdown_all(self)`
- `async def update_bot_username(self, user_id: int, bot_username: str)`
- `async def start_bot_by_id(self, bot_id: int) -> bool`
- `async def stop_bot_by_id(self, bot_id: int) -> bool`
- `async def is_bot_running(self, bot_id: int) -> bool`

**TODO/заглушки:** 4

---

### main_bot/app/utils/__init__.py
**Строк:** 1

### main_bot/app/utils/helpers.py
**Строк:** 25

**Функции:**
- `async def send_message_with_media(...)`

---

### main_bot/run.py
**Строк:** 10

**Cross-imports:**
- `from main_bot.app.main import main`

---

## Точки входа

| Сервис | Файл запуска | Точка входа |
|---|---|---|
| Seller Bot | `seller_bot/run.py` | `seller_bot/bot.py → async def main()` |
| Support Bot | `support_bot/run.py` | `support_bot/bot.py → async def main()` |
| Main Bot | `main_bot/run.py` | `main_bot/app/main.py → async def main()` |
| Web Panel | `web_panel/run.py` | `web_panel/main.py → FastAPI app` |
| Lookup API | `lookup_api/app.py` | standalone FastAPI |

### test_seller_system.py
**Строк:** 284

**Функции (10):**
- `def print_status(message, status='info')`
- `def check_env_file()`
- `def check_seller_bot_structure()`
- `def check_web_panel_structure()`
- `def check_shared_services()`
- `def check_imports()`
- `def check_documentation()`
- `def count_code_lines()`
- `def print_summary(results)`
- `def main()`

---

## Межсервисное взаимодействие

```
Support Bot → Main Bot HTTP :8080
  POST /notify-order-cancelled
  POST /notify-addinfo-completed
  POST /notify-bulk-item-completed
  POST /notify-bulk-order-completed
  POST /notify-single-order-completed

Web Panel → Main Bot HTTP :8080
  POST /api/notify-balance-update
  POST /api/notify-user-ban

Mini App → Web Panel HTTP :8000
  GET/POST /api/seller-mini-app/* (43 endpoints)

Shared Services → NocoDB HTTP
  POST /api/v2/... (fire-and-forget logging)

Shared Services → BTCPay HTTP
  POST /api/v1/stores/.../invoices
```

---

## См. также

- [[DB Models]] — структура данных
- [[Shared Services]] — общий код
- [[Web Panel]] — admin-панель
- [[Mini App]] — React Seller Mini App
