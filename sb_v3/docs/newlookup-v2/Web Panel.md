# Web Panel — web_panel/

[[MOC]] > Web Panel

**204 файла** | FastAPI | Jinja2 Templates | 40+ API-роутеров | Порт :8000

---

## Базовые файлы

### web_panel/__init__.py
**Строк:** 1

### web_panel/main.py
**Строк:** 701

Фабрика приложения FastAPI. Регистрирует все роутеры и запускает scheduled jobs.

**Функции (60+):**
- `def create_app() -> FastAPI`
- `async def lifespan(app: FastAPI)`
- `async def _send_daily_owner_stats()`
- `async def _check_scheduled_broadcasts()`
- `async def _auto_confirm_seller_orders()`
- `async def _auto_unpublish_seller_items()`
- `async def _warm_menu_count_cache()`
- `async def _run_ledger_reconciliation()`
- `async def _auto_resolve_disputes()`
- `async def _check_alerts_job()`

**Scheduled jobs (запускаются в lifespan):**
- `_send_daily_owner_stats` — ежедневная статистика владельцам
- `_check_scheduled_broadcasts` — проверка запланированных рассылок
- `_auto_confirm_seller_orders` — автоподтверждение заказов продавцов
- `_auto_unpublish_seller_items` — автоснятие с публикации
- `_warm_menu_count_cache` — прогрев Redis-кэша
- `_run_ledger_reconciliation` — сверка ledger
- `_auto_resolve_disputes` — автоматическое разрешение споров
- `_check_alerts_job` — мониторинг алертов

**Cross-imports:**
- Все web_panel.api.* роутеры
- `from shared.database.session import init_db, async_session_maker`
- `from web_panel.config import web_panel_config`

---

### web_panel/run.py
Запуск Uvicorn сервера на порту :8000.

### web_panel/auth.py
**Строк:** 710

JWT авторизация + RBAC.

**Функции (49):**
- `def create_access_token(data: dict, expires_delta) -> str`
- `async def get_current_user(token: str) -> dict`
- `def require_role(*roles)` — декоратор проверки роли
- `def require_finance_access()` — доступ к финансам
- `def require_seller_moderation_access()` — доступ к модерации
- `def require_crm_view()` — просмотр CRM
- `def require_crm_edit()` — редактирование CRM
- `def require_ban_access()` — права на бан
- `def require_catalog_read_access()` — чтение каталога
- `def require_catalog_write_access()` — запись каталога
- `_parse_and_verify_init_data(init_data: str) -> dict` — Telegram WebApp init data

**Роли:**
- `ROLE_OWNER` — полные права
- `ROLE_SUPER_ADMIN`
- `ROLE_ADMIN`
- `ROLE_CUSTOM` — кастомные права

### web_panel/config.py
**Строк:** 103

**Классы:**
- `class WebPanelConfig`

### web_panel/database.py
**Строк:** ~30

**Функции:**
- `async def get_db() -> AsyncSession` — FastAPI dependency

### web_panel/constants/categories.py
**Строк:** 472

Константы категорий товаров (банки, CC, типы, подтипы).

---

## API Роутеры (web_panel/api/)

### web_panel/api/__init__.py
**Строк:** 3

---

### web_panel/api/accounts.py
**Строк:** 448

**Классы:**
- `CategoryUpdate(BaseModel)`, `ReorderPayload(BaseModel)`, `ItemCreate(BaseModel)`, `ItemUpdate(BaseModel)`, `InventoryUpload(BaseModel)`, `ManualIssue(BaseModel)`

**Функции (16):**
- `async def list_categories(...)`
- `async def reorder_categories(...)`
- `async def update_category(...)`
- `async def list_items(...)`
- `async def create_item(...)`
- `async def reorder_items(...)`
- `async def update_item(...)`
- `async def delete_item(...)`
- `async def toggle_item(...)`
- `async def seed_accounts(...)`
- `async def list_inventory(...)`
- `async def inventory_stats(...)`
- `async def upload_inventory(...)`
- `async def upload_inventory_text(...)`
- `async def manual_issue(...)`
- `async def delete_inventory(...)`

**Роуты:**
- `@router.get("/categories")`
- `@router.put("/categories/reorder")`
- `@router.put("/categories/{cat_id}")`
- `@router.get("/items")`
- `@router.post("/items")`
- `@router.put("/items/reorder")`
- `@router.put("/items/{item_id}")`
- `@router.delete("/items/{item_id}")`
- `@router.post("/items/{item_id}/toggle")`
- `@router.post("/seed")`
- `@router.get("/inventory")`
- `@router.get("/inventory/stats")`
- `@router.post("/inventory/upload")`
- `@router.post("/inventory/upload-text")`
- `@router.post("/inventory/issue")`
- `@router.delete("/inventory/{inv_id}")`

**Prefix:** `/api/accounts`

**Cross-imports:**
- `from web_panel.auth import require_catalog_read_access, require_catalog_write_access`
- `from shared.database.models import AccountCategory, AccountItem, AccountInventory`

---

### web_panel/api/admin_roles.py
**Строк:** 110

**Классы:** `AdminRoleCreate(BaseModel)`, `AdminRoleUpdate(BaseModel)`

**Функции (4):**
- `async def list_roles(...)`
- `async def create_role(...)`
- `async def update_role(...)`
- `async def delete_role(...)`

**Роуты:**
- `@router.get("/")` — список ролей
- `@router.post("/")` — создать роль
- `@router.put("/{role_id}")` — обновить
- `@router.delete("/{role_id}")` — удалить

**Prefix:** `/api/admin-roles`

---

### web_panel/api/admins.py
**Строк:** 367

**Функции:**
- CRUD для администраторов
- Управление правами и ролями

**Роуты:**
- `@router.get("/")` — список
- `@router.post("/")` — создать
- `@router.get("/{admin_id}")`
- `@router.put("/{admin_id}")`
- `@router.delete("/{admin_id}")`
- `@router.put("/{admin_id}/roles")`

**Prefix:** `/api/admins`

---

### web_panel/api/alerts.py
**Строк:** 34

**Роуты:**
- `@router.get("/status")` — статус алертов

**Prefix:** `/api/alerts`

**Cross-imports:**
- `from web_panel.services.alert_service import AlertService`

---

### web_panel/api/analytics.py
**Строк:** 852

**Функции:**
- Аналитика по заказам, пользователям, доходам
- Воронки, сегментация

**Роуты:**
- `@router.get("/summary")` — сводка
- `@router.get("/funnel")` — воронка
- `@router.get("/abandoned-carts")` — брошенные корзины
- `@router.get("/daily")` — дневные данные
- `@router.get("/export")` — экспорт CSV

**Prefix:** `/api/analytics`

---

### web_panel/api/analytics_advanced.py
**Строк:** 460

Advanced аналитика v2.

**Роуты:**
- `@router.get("/v2/summary")`
- `@router.get("/v2/cohort")`
- `@router.get("/v2/ltv")`

**Prefix:** `/api/analytics`

---

### web_panel/api/another_services.py
**Строк:** 145

**Роуты:**
- `@router.get("/")` — список кнопок
- `@router.post("/")` — создать
- `@router.put("/{btn_id}")`
- `@router.delete("/{btn_id}")`

**Prefix:** `/api/another-services`

---

### web_panel/api/audit.py
**Строк:** 341

Журнал аудита действий администраторов.

**Роуты:**
- `@router.get("/")` — список логов
- `@router.get("/{log_id}")` — деталь

**Prefix:** `/api/audit`

---

### web_panel/api/auth.py
**Строк:** ~100

**Роуты:**
- `@router.post("/login")` — JWT аутентификация
- `@router.post("/logout")`
- `@router.get("/me")` — текущий пользователь

**Prefix:** `/api/auth`

---

### web_panel/api/automation.py
**Строк:** 592

**Роуты:**
- `@router.get("/config")` — конфиг
- `@router.put("/config")` — обновить конфиг
- `@router.get("/proxies")`, `@router.post("/proxies")`, `@router.delete("/proxies/{id}")`
- `@router.get("/api-keys")`, `@router.post("/api-keys")`, `@router.delete("/api-keys/{id}")`
- `@router.get("/jobs")` — список заданий
- `@router.post("/jobs/run")` — запустить задание
- `@router.get("/finance")` — финансовые записи

**Prefix:** `/api/automation`

---

### web_panel/api/bank_items.py
**Строк:** 391

**Роуты:**
- `@router.get("/")` — список банков
- `@router.post("/")` — создать
- `@router.put("/{bank_id}")`
- `@router.delete("/{bank_id}")`
- `@router.post("/reorder")`

**Prefix:** `/api/bank-items`

---

### web_panel/api/bots.py
**Строк:** 567

Управление Telegram-ботами. Рассылки.

**Функции:**
- `async def list_bots(...)`
- `async def get_bot_stats(...)`
- `async def broadcast_message(...)`
- `async def toggle_bot(...)`

**Роуты:**
- `@router.get("/")` — список ботов
- `@router.get("/{bot_id}/stats")`
- `@router.post("/{bot_id}/broadcast")`
- `@router.post("/{bot_id}/toggle")`

**Prefix:** `/api/bots`

---

### web_panel/api/bot_owners.py
**Строк:** 209

**Роуты:**
- `@router.get("/")` — список владельцев
- `@router.get("/{owner_id}")` — деталь
- `@router.put("/{owner_id}/withdrawal/{wid}/approve")`
- `@router.put("/{owner_id}/withdrawal/{wid}/reject")`

**Prefix:** `/api/bot-owners`

---

### web_panel/api/broadcasts.py
**Строк:** 768

**Роуты:**
- `@router.get("/")` — список рассылок
- `@router.post("/")` — создать
- `@router.get("/{broadcast_id}")`
- `@router.put("/{broadcast_id}")`
- `@router.delete("/{broadcast_id}")`
- `@router.post("/{broadcast_id}/send")` — отправить немедленно
- `@router.post("/{broadcast_id}/schedule")` — запланировать

**Prefix:** `/api/broadcasts`

---

### web_panel/api/brute_bank.py
**Строк:** 572

Модерация brute-банков.

**Роуты:**
- `@router.get("/groups")` — список групп
- `@router.get("/items")` — список позиций
- `@router.put("/items/{item_id}/approve")`
- `@router.put("/items/{item_id}/reject")`
- `@router.get("/items/{item_id}")`

**Prefix:** `/api/brute-bank`

---

### web_panel/api/bulk_discounts.py
**Строк:** 118

**Роуты:**
- `@router.get("/")` — уровни скидок
- `@router.post("/")` — создать
- `@router.put("/{tier_id}")`
- `@router.delete("/{tier_id}")`

**Prefix:** `/api/bulk-discounts`

---

### web_panel/api/cc_catalog.py
**Строк:** 188

**Роуты:**
- `@router.get("/categories")`
- `@router.post("/categories")`
- `@router.get("/items")`
- `@router.post("/items")`
- `@router.put("/items/{item_id}")`
- `@router.delete("/items/{item_id}")`

**Prefix:** `/api/cc-catalog`

---

### web_panel/api/checks.py
**Строк:** 394

Управление Check-позициями продавцов.

**Роуты:**
- `@router.get("/")` — список
- `@router.get("/{check_id}")`
- `@router.put("/{check_id}/approve")`
- `@router.put("/{check_id}/reject")`

**Prefix:** `/api/checks`

---

### web_panel/api/complaints.py
**Строк:** 406

**Роуты:**
- `@router.get("/")` — список жалоб
- `@router.get("/{complaint_id}")`
- `@router.put("/{complaint_id}/resolve")`
- `@router.put("/{complaint_id}/reject")`

**Prefix:** `/api/complaints`

---

### web_panel/api/dashboard.py
**Строк:** ~200

**Роуты:**
- `@router.get("/stats")` — общая статистика
- `@router.get("/recent-orders")` — последние заказы
- `@router.get("/recent-users")` — последние пользователи

**Prefix:** `/api/dashboard`

---

### web_panel/api/deposits.py
**Строк:** 234

**Роуты:**
- `@router.get("/")` — список депозитов
- `@router.get("/{deposit_id}")`
- `@router.post("/{deposit_id}/confirm")` — ручное подтверждение

**Prefix:** `/api/deposits`

---

### web_panel/api/disputes.py
**Строк:** 356

Управление спорами покупателей.

**Роуты:**
- `@router.get("/")` — список споров
- `@router.get("/{dispute_id}")`
- `@router.put("/{dispute_id}/resolve-buyer")`
- `@router.put("/{dispute_id}/resolve-seller")`
- `@router.put("/{dispute_id}/review-appeal")`

**Prefix:** `/api/disputes`

---

### web_panel/api/documents.py
**Строк:** 405

Модерация документов продавцов.

**Роуты:**
- `@router.get("/")` — список
- `@router.put("/{doc_id}/approve")`
- `@router.put("/{doc_id}/reject")`

**Prefix:** `/api/documents`

---

### web_panel/api/education.py
**Строк:** 308

**Роуты:**
- `@router.get("/categories")`
- `@router.post("/categories")`
- `@router.get("/subscriptions")`
- `@router.post("/subscriptions")`
- `@router.get("/manuals")`
- `@router.post("/manuals")`

**Prefix:** `/api/education`

---

### web_panel/api/esim.py
**Строк:** 129

**Роуты:**
- `@router.get("/services")` — сервисы eSIM
- `@router.post("/services/{service_id}/toggle")`
- `@router.post("/order")` — заказать eSIM

**Prefix:** `/api/esim`

---

### web_panel/api/export.py
**Строк:** 117

**Роуты:**
- `@router.get("/orders")` — экспорт заказов CSV
- `@router.get("/users")` — экспорт пользователей
- `@router.get("/transactions")` — экспорт транзакций

**Prefix:** `/api/export`

---

### web_panel/api/files.py
**Строк:** 215

**Роуты:**
- `@router.post("/upload")` — загрузить файл
- `@router.get("/{file_id}")` — получить файл
- `@router.delete("/{file_id}")`

**Prefix:** `/api/files`

---

### web_panel/api/global_search.py
**Строк:** 171

**Роуты:**
- `@router.get("/")` — поиск по всему: users, orders, sellers

**Prefix:** `/api/search`

---

### web_panel/api/knowledge_base.py
**Строк:** 138

**Роуты:**
- `@router.get("/articles")`
- `@router.post("/articles")`
- `@router.put("/articles/{article_id}")`
- `@router.delete("/articles/{article_id}")`

**Prefix:** `/api/knowledge-base`

---

### web_panel/api/marketers.py
**Строк:** 523

**Роуты:**
- `@router.get("/")` — список маркетологов
- `@router.get("/{marketer_id}")`
- `@router.put("/{marketer_id}/toggle")`
- `@router.get("/{marketer_id}/stats")`
- `@router.get("/withdrawals")` — выводы маркетологов
- `@router.put("/withdrawals/{wid}/approve")`
- `@router.put("/withdrawals/{wid}/reject")`

**Prefix:** `/api/marketers`

---

### web_panel/api/menu_categories.py
**Строк:** 179

**Роуты:**
- `@router.get("/")` — категории меню
- `@router.post("/")`
- `@router.put("/{cat_id}")`
- `@router.put("/reorder")`
- `@router.delete("/{cat_id}")`

**Prefix:** `/api/menu-categories`

---

### web_panel/api/ops_dashboard.py
**Строк:** 162

Operations Dashboard — метрики в реальном времени.

**Роуты:**
- `@router.get("/metrics")` — текущие метрики
- `@router.get("/alerts")` — алерты

**Prefix:** `/api/ops`

---

### web_panel/api/orders.py
**Строк:** ~400

**Роуты:**
- `@router.get("/")` — список заказов
- `@router.get("/{order_id}")`
- `@router.put("/{order_id}/force-complete")`
- `@router.put("/{order_id}/cancel")`
- `@router.put("/{order_id}/reassign")`

**Prefix:** `/api/orders`

---

### web_panel/api/pricing_config.py
**Строк:** 158

**Роуты:**
- `@router.get("/")` — все настройки ценообразования
- `@router.put("/{key}")` — обновить значение

**Prefix:** `/api/pricing-config`

---

### web_panel/api/products.py
**Строк:** 957

Каталог файловых товаров.

**Роуты:**
- `@router.get("/")` — список продуктов
- `@router.post("/")` — создать
- `@router.get("/{product_id}")`
- `@router.put("/{product_id}")`
- `@router.delete("/{product_id}")`
- `@router.post("/{product_id}/approve")`
- `@router.post("/{product_id}/reject")`
- `@router.get("/purchases")` — история покупок

**Prefix:** `/api/products`

---

### web_panel/api/referral_settings.py
**Строк:** 114

**Роуты:**
- `@router.get("/")` — настройки реферальной программы
- `@router.put("/")`

**Prefix:** `/api/referral-settings`

---

### web_panel/api/reports.py
**Строк:** 201

**Роуты:**
- `@router.get("/worker-performance")` — отчёт по воркерам
- `@router.get("/revenue")` — отчёт по доходам
- `@router.get("/seller-performance")` — отчёт по продавцам

**Prefix:** `/api/reports`

---

### web_panel/api/seller_crm.py
**Строк:** 907

CRM для продавцов: заказы, споры, выводы.

**Роуты:**
- `@router.get("/orders")` — заказы продавцов
- `@router.get("/orders/{order_id}")`
- `@router.get("/disputes")` — споры
- `@router.put("/disputes/{dispute_id}/resolve")`
- `@router.get("/withdrawals")` — выводы продавцов
- `@router.put("/withdrawals/{wid}/approve")`
- `@router.put("/withdrawals/{wid}/reject")`

**Prefix:** `/api/seller-crm`

---

### web_panel/api/seller_deposits.py
**Строк:** 149

BTCPay-депозиты продавцов.

**Роуты:**
- `@router.get("/")` — список депозитов продавцов
- `@router.post("/webhook")` — BTCPay webhook
- `@router.post("/{payment_id}/sync")` — синхронизация статуса

**Prefix:** `/api/seller-deposits`

**Cross-imports:**
- `from shared.services.btcpay_service import BTCPayService`
- `from shared.services.seller_deposit_service import SellerDepositService`

---

### web_panel/api/seller_mini_app.py
**Строк:** 1888

**Ключевой файл** — 43 endpoints для [[Mini App]].

**Функции (43+):**
- `_parse_and_verify_init_data(init_data: str) -> dict`
- `async def get_seller_me(...)` — данные продавца
- `async def get_conversations(...)` — список диалогов
- `async def get_messages(conv_id: int, ...)`
- `async def send_message(...)`
- `async def get_orders(filter, ...)`
- `async def get_order_dispute(order_id: int, ...)`
- `async def reply_to_dispute(...)`
- `async def accept_dispute(...)`
- `async def escalate_dispute(...)`
- `async def open_dispute(...)`
- `async def get_analytics_summary(date_from, date_to, ...)`
- `async def get_analytics_funnel(date_from, date_to, ...)`
- `async def get_abandoned_carts(date_from, date_to, ...)`
- `async def export_analytics_csv(...)`
- `async def get_finance_summary(...)`
- `async def request_withdrawal(...)`
- `async def export_finance(...)`
- `async def submit_upload(...)` — загрузка нового товара
- `async def request_category(...)` — запрос новой категории
- `async def get_bank_catalog(...)` — каталог банков
- `async def get_cc_catalog(...)` — каталог CC
- `async def set_vacation(...)` — режим отпуска
- `async def set_auto_payout(...)` — автовыплата
- `async def set_quiet_hours(...)` — тихие часы
- `async def get_team_helpers(...)` — список хелперов
- `async def add_helper(...)` — добавить хелпера
- `async def get_helper_audit(helper_id, ...)`
- `async def update_helper_roles(helper_id, ...)`
- `async def remove_helper(helper_id, ...)`

**Роуты:**
- `@router.get("/me")`
- `@router.get("/conversations")`
- `@router.get("/conversations/{conv_id}/messages")`
- `@router.post("/conversations/{conv_id}/messages")`
- `@router.get("/orders")`
- `@router.get("/orders/{order_id}/dispute")`
- `@router.post("/orders/{order_id}/dispute/reply")`
- `@router.post("/orders/{order_id}/dispute/accept")`
- `@router.post("/orders/{order_id}/dispute/escalate")`
- `@router.post("/orders/{order_id}/dispute/open")`
- `@router.get("/analytics/summary")`
- `@router.get("/analytics/funnel")`
- `@router.get("/analytics/abandoned-carts")`
- `@router.get("/analytics/export")`
- `@router.get("/finance/summary")`
- `@router.post("/finance/withdraw")`
- `@router.get("/finance/export")`
- `@router.post("/uploads/submit")`
- `@router.post("/uploads/request-category")`
- `@router.get("/catalog/banks")`
- `@router.get("/catalog/cc")`
- `@router.post("/settings/vacation")`
- `@router.post("/settings/auto-payout")`
- `@router.post("/settings/quiet-hours")`
- `@router.get("/team/helpers")`
- `@router.post("/team/add")`
- `@router.get("/team/helpers/{helper_id}/audit")`
- `@router.put("/team/helpers/{helper_id}/roles")`
- `@router.delete("/team/helpers/{helper_id}")`

**Prefix:** `/api/seller-mini-app`

**Cross-imports:**
- `from shared.services.seller_conversation_service import ...`
- `from shared.services.seller_dispute_service import SellerDisputeService`
- `from shared.services.seller_upload_pipeline_service import SellerUploadPipelineService`
- `from shared.services.ledger_projection_service import LedgerProjectionService`
- `from shared.services.seller_helper_service import SellerHelperService`
- `from shared.utils.telegram_auth import validate_telegram_init_data`

---

### web_panel/api/seller_moderation.py
**Строк:** 1104

Модерация товаров продавцов (банки, CC, NFC, OTP, Enroll, Selfreg, Check, Document, Fullz, Logs).

**Роуты:**
- `@router.get("/queue")` — очередь модерации
- `@router.get("/banks")` — список банков
- `@router.get("/banks/{bank_id}")`
- `@router.put("/banks/{bank_id}/approve")`
- `@router.put("/banks/{bank_id}/reject")`
- `@router.put("/banks/{bank_id}/request-changes")`
- `@router.get("/cc")` — CC-карты
- `@router.put("/cc/{item_id}/approve")`
- `@router.put("/cc/{item_id}/reject")`
- `@router.get("/nfc")`, `@router.put("/nfc/{item_id}/approve")`, `@router.put("/nfc/{item_id}/reject")`
- `@router.get("/otp")`, `@router.put("/otp/{item_id}/approve")`, `@router.put("/otp/{item_id}/reject")`
- `@router.get("/brute")` — brute items
- `@router.get("/enroll")`, approve/reject
- `@router.get("/selfreg-cc")`, approve/reject
- `@router.get("/checks")`, approve/reject
- `@router.get("/documents")`, approve/reject
- `@router.get("/fullz")`, approve/reject
- `@router.get("/logs")`, approve/reject

**Prefix:** `/api/seller-moderation`

**Cross-imports:**
- `from shared.services.moderation_pricing_service import ...`
- `from shared.database.models import SellerBank, SellerCCItem, SellerNFCItem, ...`

---

### web_panel/api/seller_team.py
**Строк:** 252

**Роуты:**
- `@router.get("/{seller_id}/helpers")` — хелперы продавца
- `@router.post("/{seller_id}/helpers")` — добавить
- `@router.put("/{seller_id}/helpers/{helper_id}/roles")`
- `@router.put("/{seller_id}/helpers/{helper_id}/status")`
- `@router.delete("/{seller_id}/helpers/{helper_id}")`

**Prefix:** `/api/sellers/{seller_id}/team`

---

### web_panel/api/sellers.py
**Строк:** 594

**Роуты:**
- `@router.get("/")` — список продавцов
- `@router.get("/{seller_id}")`
- `@router.put("/{seller_id}/approve")`
- `@router.put("/{seller_id}/ban")`
- `@router.put("/{seller_id}/unban")`
- `@router.get("/{seller_id}/stats")`
- `@router.get("/{seller_id}/banks")`
- `@router.get("/{seller_id}/orders")`

**Prefix:** `/api/sellers`

**Cross-imports:**
- `from shared.services.seller_deposit_service import SellerDepositService`
- `from shared.database.models import Seller`

---

### web_panel/api/service_prices.py
**Строк:** 319

**Роуты:**
- `@router.get("/")` — список цен
- `@router.post("/")` — создать
- `@router.put("/{price_id}")`
- `@router.delete("/{price_id}")`

**Prefix:** `/api/service-prices`

---

### web_panel/api/services.py
**Строк:** 442

Управление каталогом сервисов.

**Роуты:**
- `@router.get("/")` — список сервисов
- `@router.post("/")`
- `@router.put("/{service_id}")`
- `@router.delete("/{service_id}")`
- `@router.post("/{service_id}/toggle")`

**Prefix:** `/api/services`

---

### web_panel/api/stock.py
**Строк:** 388

**Роуты:**
- `@router.get("/")` — инвентарь
- `@router.get("/{item_id}")`
- `@router.put("/{item_id}/publish")`
- `@router.put("/{item_id}/unpublish")`

**Prefix:** `/api/stock`

---

### web_panel/api/support_tickets.py
**Строк:** 470

**Роуты:**
- `@router.get("/")` — список тикетов
- `@router.get("/{ticket_id}")`
- `@router.post("/{ticket_id}/reply")` — ответить
- `@router.put("/{ticket_id}/close")`
- `@router.put("/{ticket_id}/priority")`

**Prefix:** `/api/support-tickets`

---

### web_panel/api/telegram_sync.py
**Строк:** 136

**Роуты:**
- `@router.post("/sync/bot-usernames")` — синхронизация username ботов
- `@router.post("/sync/user-usernames")` — синхронизация username пользователей
- `@router.get("/sync/status")`

**Prefix:** `/api/telegram`

**Cross-imports:**
- `from web_panel.services.telegram_info import TelegramInfoService`
- `from shared.database.models import MirrorBot, User`

---

### web_panel/api/users.py
**Строк:** 1247

**Классы:**
- `UserResponse(BaseModel)`, `Config`, `UserDetailSummary(BaseModel)`, `UserUpdateBalance(BaseModel)`, `UserBanRequest(BaseModel)`, `SendMessageRequest(BaseModel)`, `UserUpdate(BaseModel)`, `CrossBotMessageRequest(BaseModel)`

**Функции (19):**
- `def _ensure_crm_view(current_user: dict) -> None`
- `def _ensure_crm_edit(current_user: dict) -> None`
- `def _ensure_ban_access(current_user: dict) -> None`
- `def _ensure_finance_access(current_user: dict) -> None`
- `def _decimal_to_float(value: Optional[Decimal]) -> float`
- `def _signed_transaction_amount(transaction: Transaction)`
- `def _build_balance_history(...)`
- `async def get_user_language(db, user_id, ...)`
- `async def get_users(...)`
- `async def get_user(...)`
- `async def get_user_details(...)`
- `async def update_user(...)`
- `async def update_user_balance(...)`
- `async def ban_user(...)`
- `async def send_message_to_user(...)`
- `async def send_message_via_any_bot(...)`
- `async def get_user_orders(...)`
- `async def get_user_stats(...)`
- `async def search_user_across_bots(...)`

**Роуты:**
- `@router.get("/")` — список
- `@router.get("/{user_id}", response_model=UserResponse)`
- `@router.get("/{user_id}/details")`
- `@router.put("/{user_id}")`
- `@router.post("/{user_id}/balance")` — корректировка баланса
- `@router.post("/{user_id}/ban")`
- `@router.post("/{user_id}/send-message")`
- `@router.post("/{user_id}/send-message-any-bot")`
- `@router.get("/{user_id}/orders")`
- `@router.get("/{user_id}/stats")`
- `@router.get("/search/{user_id}")`

**Prefix:** `/api/users`

---

### web_panel/api/withdrawals.py
**Строк:** 254

**Роуты:**
- `@router.get("/")` — список выводов
- `@router.get("/{withdrawal_id}")`
- `@router.put("/{withdrawal_id}/approve")`
- `@router.put("/{withdrawal_id}/reject")`

**Prefix:** `/api/withdrawals`

---

### web_panel/api/worker_crm.py
**Строк:** 438

**Роуты:**
- `@router.get("/")` — список воркеров
- `@router.get("/{worker_id}")`
- `@router.put("/{worker_id}/activate")`
- `@router.put("/{worker_id}/deactivate")`
- `@router.get("/{worker_id}/stats")`
- `@router.get("/{worker_id}/orders")`

**Prefix:** `/api/workers-crm`

---

### web_panel/api/workers.py
**Строк:** 795

**Роуты:**
- `@router.get("/")` — аналитика воркеров
- `@router.get("/{worker_id}")`
- `@router.get("/{worker_id}/score")`
- `@router.post("/{worker_id}/recalculate-score")`

**Prefix:** `/api/workers`

---

## Services (web_panel/services/)

### web_panel/services/admin_service.py
CRUD операции с администраторами.

### web_panel/services/alert_service.py
**Строк:** ~80

**Функции:**
- `async def check_alerts(session: AsyncSession) -> list[str]`
- `async def _send_alerts(alerts: list[str], now: datetime)`
- `async def get_alert_status(session: AsyncSession) -> dict`

**Cross-imports:**
- `from shared.database.models import (...)`

---

### web_panel/services/audit_service.py
**Строк:** 28

**Функции:**
- `async def log_action(...)` — запись в аудит-лог

**Cross-imports:**
- `from shared.services.admin_audit_service import log_admin_action`

---

### web_panel/services/bot_integration.py
**Строк:** 212

HTTP-клиент для общения с Main Bot API.

**Классы:**
- `class BotIntegration`

**Функции:**
- `def __init__(self)`
- `async def notify_support_order_update(order_id, ...)`
- `async def notify_user_balance_update(user_id, amount, ...)`
- `async def notify_user_ban(user_id, reason, ...)`
- `async def broadcast_message(bot_id, text, ...)`

**API вызовы:**
- `POST http://main_bot:8080/api/notify-balance-update`

**Cross-imports:**
- `from shared.security.internal_api import build_internal_api_headers`
- `from shared.database.models import MirrorBot`

---

### web_panel/services/bulk_validator.py
**Строк:** 145

**Классы:**
- `class BulkOperationValidator`

**Функции:**
- `def __init__(self)`
- `def validate_size(items) -> bool`
- `def get_batches(items, batch_size)`
- `def validate_bulk_operation(operation_type, items)`
- `def validate_user_bulk(users)`
- `def validate_order_bulk(orders)`
- `def validate_message_bulk(messages)`
- `def validate_withdrawal_bulk(withdrawals)`

---

### web_panel/services/file_upload_service.py
**Строк:** 265

**Функции:**
- Загрузка и хранение файлов (медиа, документы, чеки)

---

### web_panel/services/nocodb_sync.py
Синхронизация с NocoDB.

### web_panel/services/telegram_info.py
Получение информации о Telegram пользователях/ботах.

---

## Templates (web_panel/templates/)

40+ Jinja2 HTML-шаблонов для веб-панели:

| Шаблон | Описание |
|---|---|
| `base.html` | Базовый layout |
| `dashboard.html` | Главная страница |
| `login.html` | Авторизация |
| `users.html` / `user_detail.html` | CRM пользователей |
| `orders.html` / `order_detail.html` | Заказы |
| `workers.html` / `worker_detail.html` | Воркеры |
| `sellers.html` / `seller_detail.html` | Продавцы |
| `seller_moderation.html` | Очередь модерации |
| `broadcasts.html` | Рассылки |
| `analytics.html` | Аналитика |
| `finance.html` | Финансы |
| `settings.html` | Настройки |
| `audit.html` | Аудит-лог |
| `products.html` | Каталог товаров |
| `accounts.html` | Аккаунты |
| `education.html` | Обучение |
| ... | |

---

## Авторизация (auth.py)

- JWT Bearer tokens (заголовок `Authorization: Bearer <token>`)
- Роли: `owner`, `super_admin`, `admin`, `custom`
- Granular permissions:
  - `finance_access` — управление финансами
  - `sellers_access` — работа с продавцами
  - `support_access` — поддержка
  - `complaints_access` — жалобы
  - `orders_access` — заказы
  - `catalogs_access` — каталоги
  - `ban_access` — бан пользователей
  - `crm_view` / `crm_edit` — CRM права

---

## Scheduled Jobs

| Job | Период | Действие |
|---|---|---|
| `_send_daily_owner_stats` | Ежедневно | Статистика владельцам ботов |
| `_check_scheduled_broadcasts` | Каждую минуту | Проверка и отправка рассылок |
| `_auto_confirm_seller_orders` | Каждые N минут | Автоподтверждение заказов продавцов |
| `_auto_unpublish_seller_items` | Ежедневно | Снятие истёкших позиций |
| `_warm_menu_count_cache` | Периодически | Прогрев Redis-кэша меню |
| `_run_ledger_reconciliation` | Ежедневно | Сверка финансового ledger |
| `_auto_resolve_disputes` | Периодически | Автоматическое разрешение споров |
| `_check_alerts_job` | Каждые N минут | Мониторинг алертов |

---

## Зависимости

- [[Shared Services]] — все основные сервисы (LedgerService, SellerDepositService, модерация, NocoDB)
- [[Seller Bot]] — config (seller_bot_config), keyboards (mini app URL)
- [[Support Bot]] — balance_service
- [[Mini App]] — встроен как StaticFiles + Vite dev server proxy
- [[DB Models]] — все модели
