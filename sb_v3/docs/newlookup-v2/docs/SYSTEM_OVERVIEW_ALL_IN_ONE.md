# NewLookup System Overview

Единый документ по всей системе: текущий marketplace-контур, вспомогательные сервисы, общие модули, инфраструктура, запуск, потоки данных и legacy-слой.

## Launch Snapshot

Актуальный operational snapshot:
- основной production-like запуск описан в `docs/LAUNCH_RUNBOOK.md`
- Docker source of truth: `docker-compose.yml`
- local source of truth: `run_local.py`
- env template: `.env.example`

Что важно для текущего контура:
- все сервисы используют раннюю startup validation по обязательным env vars
- `support_bot`, `seller_bot` и `web_panel` делят одну `tasks.db`
- `Brute` каталог у buyer-side работает через search/pagination/grouping по `bank_code`
- seller mini app покрывает bank upload fields и brute upload без category step

Ниже остаётся расширенный архитектурный обзор; для запуска и recovery использовать runbook.

## 1. Что это за репозиторий

`newlookup` это мультисервисный Python-репозиторий, где в одном кодовом дереве собраны:

- основной продукт на Telegram-ботах;
- административная веб-панель;
- общий слой моделей, БД и сервисов;
- seller и marketer контуры;
- legacy-компоненты, оставшиеся от более старой системы.

Это не один монолитный сервис и не frontend/backend в классическом SPA-формате. Основной пользовательский интерфейс системы находится в Telegram-ботах.

## 2. Главная архитектурная идея

Система построена вокруг одной общей доменной модели и общей базы данных.

Основные роли:

- покупатель работает через `mirror_bot`;
- воркер и саппорт работают через `support_bot`;
- селлер работает через `seller_bot`;
- владелец бота и администратор управляют системой через `main_bot` и `web_panel`;
- маркетолог работает через `marketer_bot`.

Все эти роли используют общие сущности из `shared`.

## 3. Верхнеуровневая структура репозитория

```text
newlookup/
├── main_bot/        # Главный бот и API управления mirror-ботами
├── mirror_bot/      # Пользовательские Telegram-боты покупателей
├── support_bot/     # Бот саппорта/воркеров + внутренний API уведомлений
├── seller_bot/      # Бот селлеров
├── marketer_bot/    # Бот маркетологов и реферального контура
├── web_panel/       # FastAPI admin panel + templates + static
├── shared/          # Общие модели, БД, сервисы, безопасность, утилиты
├── scripts/         # Миграции, вспомогательные и обслуживающие скрипты
├── docs/            # Документация, спеки, roadmap
├── data/            # Локальные SQLite БД и runtime данные
├── uploads/         # Загруженные файлы
├── media/           # Медиа-ассеты
├── docker-compose.yml
├── run_local.py
├── STRUCTURE.md
└── ARCHITECTURE.md  # Legacy / auxiliary overview
```

## 4. Стек технологий

Основной стек:

- Python
- `aiogram` для Telegram-ботов
- `FastAPI` + `uvicorn` для HTTP API и веб-панели
- `SQLAlchemy asyncio`
- `PostgreSQL` для основного production-контура
- `SQLite` для local/dev и отдельных внутренних задач
- `Redis`
- `Jinja2` templates + статические JS/CSS файлы
- `APScheduler` для фоновых задач в веб-панели

В репозитории не найдено:

- `package.json`
- `pyproject.toml`
- `Makefile`
- корневой `README.md`

Поэтому фактическими обзорными входами в проект являются `STRUCTURE.md`, `docs/*` и исходный код точек входа.

## 5. Карта сервисов

### 5.1 `main_bot`

Назначение:

- главный управляющий бот;
- поднимает polling;
- восстанавливает все `mirror_bot` экземпляры из БД;
- поднимает внутренний HTTP API;
- выступает центром управления mirror-ботами.

Точки входа:

- `main_bot/app/main.py`
- `main_bot/run.py`

Основная логика:

- инициализация БД через репозиторий;
- создание `MirrorBotService`;
- вызов восстановления ранее зарегистрированных ботов;
- запуск HTTP-сервера и Telegram polling параллельно.

### 5.2 `mirror_bot`

Назначение:

- основной клиентский интерфейс для покупателей;
- принимает заказы;
- показывает услуги и категории;
- ведет оплату, buyer orders, buyer chat, поддержку;
- отправляет пользователю результаты.

Точка входа:

- `mirror_bot/bot.py`

Особенность:

- это не один единственный бот;
- экземпляры создаются динамически через `create_mirror_bot(token, mirror_bot_id)`;
- один `main_bot` управляет множеством mirror-ботов, хранящихся в БД.

### 5.3 `support_bot`

Назначение:

- внутренний бот для воркеров, саппорта и админов;
- получает уведомления о новых заказах;
- маршрутизирует заказы воркерам;
- ведет seller moderation, complaints, history, uploads;
- поднимает внутренний API уведомлений.

Точки входа:

- `support_bot/bot.py`
- `support_bot/run.py`
- `support_bot/api_server.py`

Внутренний API:

- работает на `8181`;
- принимает события наподобие `new-order`, `order-to-channel`, `complaint-resolved`.

### 5.4 `seller_bot`

Назначение:

- Telegram-интерфейс селлеров;
- управление складом и товарами;
- seller orders;
- чат с покупателем;
- вывод средств;
- загрузка контента и результатов.

Точки входа:

- `seller_bot/bot.py`
- `seller_bot/run.py`

Особенность:

- использует общую БД;
- использует seller-specific middleware;
- связан с seller CRM в `web_panel`.

### 5.5 `marketer_bot`

Назначение:

- реферальный и маркетинговый контур;
- работа с промокодами, маркетологами и привязкой трафика.

Точка входа:

- `marketer_bot/bot.py`

### 5.6 `web_panel`

Назначение:

- админ-панель;
- API и UI для управления данными системы;
- CRM, аналитика, отчеты, селлеры, воркеры, маркетологи, боты, цены, товары, категории, жалобы, broadcast.

Точки входа:

- `web_panel/main.py`
- `web_panel/run.py`

Особенности:

- `FastAPI` приложение;
- шаблоны в `web_panel/templates`;
- статика в `web_panel/static`;
- фоновые задачи через `APScheduler`;
- отдельный seller mini app.

### 5.7 `shared`

Назначение:

- единое ядро системы;
- модели данных;
- сессии БД;
- общие сервисы;
- утилиты;
- internal API security;
- бизнес-логика, используемая несколькими сервисами.

Основные подпапки:

- `shared/database`
- `shared/services`
- `shared/security`
- `shared/utils`
- `shared/nocodb`

## 6. Главные сущности системы

Ключевые доменные сущности хранятся в `shared/database/models.py`.

Базовые сущности:

- `MirrorBot` — отдельный пользовательский бот/магазин;
- `User` — пользователь внутри конкретного mirror-бота;
- `Order` — заказ пользователя;
- `BulkOrderItem` — элементы bulk-заказа;
- `Transaction` — движение по балансу;
- `Worker` — исполнитель заказов;
- `BotOwner` и `BotOwnerStats` — владелец mirror-бота и его метрики;
- seller-сущности — контур продавцов, заказов продавцов и seller chat;
- marketer/referral сущности — реферальный контур.

Из этого следует, что система обслуживает сразу несколько типов акторов:

- buyer
- worker
- seller
- bot owner
- admin
- marketer

## 7. Как сервисы взаимодействуют

### 7.1 Основной buyer flow

```text
Покупатель
  -> mirror_bot
  -> создание User / Order в общей БД
  -> support_bot получает внутреннее уведомление
  -> воркер обрабатывает заказ
  -> результат отправляется обратно пользователю
  -> уведомление приходит в нужный mirror_bot через API main_bot
```

### 7.2 Seller flow

```text
Покупатель оформляет seller-related заказ
  -> заказ фиксируется в общей БД
  -> support/admin контур модерирует или подтверждает заказ
  -> seller_bot уведомляет селлера
  -> селлер работает с заказом, файлами, чатом
  -> buyer и seller общаются через seller chat сущности
```

### 7.3 Admin flow

```text
Администратор
  -> web_panel
  -> управление ботами, пользователями, воркерами, заказами, селлерами, ролями
  -> фоновые задачи и сервисные процессы
  -> контроль статусов, рассылок, CRM и аналитики
```

### 7.4 Notification flow

```text
Order created
  -> support_bot API уведомлений
  -> воркеры / канал заказов

Order completed or cancelled
  -> main_bot API уведомлений
  -> уведомление пользователю в конкретный mirror_bot

Balance or add-info updates
  -> main_bot API
  -> message to buyer
```

## 8. Что именно делает каждый слой

### Telegram слой

- `mirror_bot` — customer-facing сценарии
- `support_bot` — operations и worker workflows
- `seller_bot` — seller workflows
- `marketer_bot` — marketing workflows
- `main_bot` — owner-facing control and orchestration

### HTTP/API слой

- `main_bot` — API для отправки результатов и апдейтов в mirror-боты
- `support_bot` — API для уведомлений о новых заказах и статусах
- `web_panel` — основной administrative API и HTML UI

### Data слой

- `shared/database/models.py` — доменная модель
- `shared/database/session.py` — инициализация и сессии основной БД
- `shared/database/tasks_session.py` — отдельная tasks DB

### Business logic слой

- `shared/services/*`
- сервисы внутри каждого бота
- notification services
- moderation, delivery, owner stats, broadcasts

## 9. Инфраструктура и запуск

### 9.1 Docker режим

Основной файл:

- `docker-compose.yml`

Сервисы:

- `postgres`
- `redis`
- `main_bot`
- `support_bot`
- `web_panel`
- `marketer_bot`
- `seller_bot`

Смысл зависимостей:

- почти все прикладные сервисы зависят от `postgres` и `redis`;
- `support_bot` открывает порт `8181`;
- `web_panel` открывает `8000` по умолчанию;
- инфраструктура общая для всего current продукта.

### 9.2 Local режим

Основной файл:

- `run_local.py`

Что делает:

- принудительно переключает систему на `SQLite`;
- вызывает инициализацию БД;
- запускает локально:
  - `main_bot`
  - `support_bot`
  - `web_panel`
  - `seller_bot`

Это основной удобный dev launcher для локальной среды.

## 10. База данных и миграции

В проекте не обнаружен стандартный migration framework уровня `Alembic`.

Фактический подход такой:

- создание таблиц через `Base.metadata.create_all()`;
- дополнительная инициализация в `init_db()`;
- ad-hoc изменения схемы через отдельные Python-скрипты;
- утилиты и миграционные сценарии лежат в `scripts/` и частично в корне.

Это значит, что схема управляется кодом приложения и точечными миграциями, а не единой цепочкой версионируемых migration-файлов.

## 11. Frontend и UI

В проекте нет отдельного frontend-приложения на Node/Vite/React как основного UI.

Фактический UI распределен так:

- для покупателей интерфейс находится в Telegram через `mirror_bot`;
- для селлеров интерфейс находится в `seller_bot` и частично в seller mini app;
- для админов интерфейс находится в `web_panel/templates` и `web_panel/static`.

Иными словами:

- Telegram является главным продуктовым интерфейсом;
- `web_panel` является внутренним административным интерфейсом.

## 12. Основные каталоги по назначению

### Backend / API

- `web_panel`
- `main_bot/app/api`
- `support_bot/api`

### Bot logic

- `main_bot`
- `mirror_bot`
- `support_bot`
- `seller_bot`
- `marketer_bot`

### Shared code

- `shared`

### Notifications

- `main_bot/app/api/notifications.py`
- `support_bot/api/notifications.py`
- `shared/services/order_notification_service.py`
- `shared/services/admin_notification_service.py`
- `shared/services/log_channel_service.py`

### Database

- `shared/database/models.py`
- `shared/database/session.py`
- `shared/database/tasks_session.py`
- `data/*.db`

### Uploads / media

- `uploads`
- `media`

### Docs / specs

- `docs`
- `STRUCTURE.md`
- `ARCHITECTURE.md`

### Scripts / maintenance

- `scripts`
- корневые `migrate_*`, `fix_*`, `check_*`, `update_*`

## 13. Legacy слой

В репозитории присутствует отдельный исторический контур, который не является центральной частью текущего marketplace-продукта.

К нему относятся:

- `system_launcher.py`
- `pptp_auto_bruteforcer.py`
- `admin_panel_bot.py`
- `admin_panel_integration.py`
- `crypto_order_bot.py`
- `crypto_order_checker.py`
- `crypto_gateway_config.py`
- `crypto_bot_demo.py`

Этот слой:

- использует собственную логику;
- местами опирается на `SQLite`;
- относится к auxiliary/legacy направлению;
- архитектурно отделен от основного buyer/support/seller/web-panel контура.

Для него уже есть отдельный обзор в `ARCHITECTURE.md`.

## 14. Практическая схема системы

```text
                    +----------------------+
                    |      Web Panel       |
                    |  Admin UI + API +    |
                    |  Scheduler + CRM     |
                    +----------+-----------+
                               |
                               v
 +-------------+    +----------------------+    +-------------+
 |  Main Bot   |<-->|   Shared Services    |<-->| Support Bot |
 | control/API |    | models, db, logic,   |    | worker ops  |
 +------+------+    | security, utilities  |    +------+------+ 
        |           +----------+-----------+           |
        |                      |                       |
        v                      v                       v
 +-------------+       +---------------+       +--------------+
 | Mirror Bots |       | PostgreSQL /  |       | Seller Bot   |
 | buyers UI   |       | SQLite + Redis|       | sellers UI   |
 +------+------+       +-------+-------+       +------+-------+
        |                      |                      |
        +----------------------+----------------------+
                               |
                               v
                        +-------------+
                        | Marketer Bot|
                        +-------------+
```

## 15. Что читать первым для входа в проект

Рекомендуемый порядок:

1. `docs/SYSTEM_OVERVIEW_ALL_IN_ONE.md`
2. `STRUCTURE.md`
3. `docs/DEVELOPMENT_ROADMAP.md`
4. `docker-compose.yml`
5. `run_local.py`
6. `shared/database/models.py`
7. `shared/database/session.py`
8. `main_bot/app/main.py`
9. `mirror_bot/bot.py`
10. `support_bot/bot.py`
11. `support_bot/api/notifications.py`
12. `main_bot/app/api/notifications.py`
13. `seller_bot/bot.py`
14. `web_panel/main.py`
15. `ARCHITECTURE.md`

## 16. Краткий итог

`newlookup` это единая многоролевая Telegram-first платформа с общей БД, где:

- `mirror_bot` обслуживает покупателей;
- `support_bot` обслуживает воркеров и внутренние процессы;
- `seller_bot` обслуживает селлеров;
- `marketer_bot` обслуживает маркетинговый контур;
- `main_bot` управляет mirror-ботами и API;
- `web_panel` является административным центром;
- `shared` связывает все это в единую систему.

Legacy-компоненты находятся рядом, но архитектурно являются отдельным слоем.
