# Launch Runbook

Актуальный runbook для `newlookup` после стабилизации Docker, startup validation и seller flows.

## Runtime Modes

### Docker full stack

Поднимает:
- `postgres`
- `redis`
- `main_bot` (включая mirror bots)
- `support_bot`
- `worker_bot`
- `web_panel`
- `seller_bot`
- `marketer_bot`
- `celery_worker` + `celery_beat`
- `lookup_api`

Команда:

```bash
cp .env.example .env
mkdir -p data uploads media
docker compose up -d --build
```

### Docker core stack

Если нужен только buyer/support core без seller-модуля:

```bash
docker compose up -d postgres redis main_bot support_bot web_panel
```

### Local dev stack

Локальный launcher всегда переключает проект на SQLite через `LOCAL_DATABASE_URL` и `LOCAL_TASKS_DATABASE_URL`.

```bash
cp .env.example .env
mkdir -p data uploads media
python3 run_local.py
```

## Required Env Vars

### Shared

- `DATABASE_URL`
- `REDIS_URL`
- `REDIS_PASSWORD` (used by docker-compose redis `--requirepass`)
- `POSTGRES_PASSWORD` (required, no default)
- `ADMIN_IDS`
- `INTERNAL_API_TOKEN`

### Main bot

- `MAIN_BOT_TOKEN`
- `MAIN_BOT_USERNAME`

### Support bot

- `SUPPORT_BOT_TOKEN`
- `ORDERS_CHANNEL_ID`
- `SUPPORT_LOG_CHAT_ID`

### Seller bot

- `SELLER_BOT_TOKEN`
- `SELLER_MINI_APP_URL`

### Marketer bot

- `MARKETER_BOT_TOKEN`

### Web panel

- `WEB_PANEL_SECRET_KEY`
- `WEB_PANEL_PORT`
- `ADMIN_USERNAME`
- `ADMIN_PASSWORD`

### Tasks DB

- `TASKS_DATABASE_URL`

Для local launcher:

- `LOCAL_DATABASE_URL`
- `LOCAL_TASKS_DATABASE_URL`

## Fresh DB Bootstrap

### Docker

```bash
cp .env.example .env
mkdir -p data uploads media
docker compose up -d postgres redis
docker compose up -d --build
```

Что происходит автоматически:
- `Base.metadata.create_all()` создаёт таблицы для fresh DB.
- `init_db()` догоняет runtime-migrations для existing/fresh schema.
- `init_tasks_db()` создаёт общую `tasks.db` только для нефинансовых background tasks.

### Local

```bash
cp .env.example .env
python3 run_local.py
```

## Existing DB Upgrade

Перед апгрейдом:

```bash
pg_dump "$DATABASE_URL" > backup-before-launch.sql
```

Прогон миграций без полного старта сервиса:

```bash
python3 -c "import asyncio; from shared.database.session import init_db; asyncio.run(init_db())"
python3 -c "import asyncio; from shared.database.tasks_session import init_tasks_db; asyncio.run(init_tasks_db())"
```

В Docker можно выполнить то же через любой сервис, у которого есть кодовая база:

```bash
docker compose run --rm web_panel python -c "import asyncio; from shared.database.session import init_db; asyncio.run(init_db())"
docker compose run --rm web_panel python -c "import asyncio; from shared.database.tasks_session import init_tasks_db; asyncio.run(init_tasks_db())"
```

## Operator Checks

### Health / readiness

- `docker compose ps` показывает все контейнеры в `Up`.
- `docker compose logs main_bot support_bot web_panel seller_bot --tail=100` не содержит startup validation errors.
- `http://localhost:8000/` отвечает web panel.
- `http://localhost:8181/docs` отвечает support API.
- В `data/tasks.db` используется один общий volume/path для `support_bot`, `seller_bot` и `web_panel` только для reminder/background задач.

### Internal auth

Все сервисы должны использовать один и тот же `INTERNAL_API_TOKEN`. Не полагаться на случайный fallback secret.

## Smoke Checklist

### Infra

- `docker compose config` проходит без ошибок.
- `postgres` healthy.
- `redis` healthy.
- `web_panel` стартует без `reload=True` в production entrypoint.

### Bots and APIs

- `main_bot` поднимается и восстанавливает mirror bots из БД.
- `support_bot` стартует вместе с HTTP API на `8181`.
- `seller_bot` стартует и открывает seller menu.
- `marketer_bot` стартует, если токен задан.

### Seller flows

- Seller может открыть mini app.
- Bank preview/submit принимает `product_type`, `product_subtype`, `instruction`, number-access и auto-unpublish поля.
- Brute upload проходит preview и submit без category-step.
- Новый brute batch виден в web panel moderation.

### Admin flows

- В `/brute-bank` можно создать group по `bank_code`.
- Pending brute item при approve автоматически матчится к group по `bank_code`.
- Approved brute item виден buyer-side в `Brute BANK`.

### Buyer/support flows

- Buyer создаёт обычный order, support получает notification через HTTP API.
- HTTP notification path делает retry при временной ошибке.
- Seller bank order уходит админам; если DM не доставился, используется fallback в orders channel.
- Поиск по `Brute BANK` не ломает Markdown и не зависает в search FSM.

## Common Failure Modes

- `startup validation failed`: не хватает обязательных env vars или один из них пустой.
- `Invalid internal API token`: токены разных сервисов не совпадают.
- `sqlite tasks.db split-brain`: у контейнеров нет общего `./data:/app/data`.
- `No banks matched your search` при очевидном наличии товаров: brute items не approve'd или не привязаны к group.
- `Seller access not found` в mini app: Telegram WebApp auth невалиден или seller/helper не связан с seller account.

## Production Hardening

Before going live, verify:

1. **Secrets**: all `*_TOKEN`, `*_PASSWORD`, `*_SECRET_KEY` are strong random values (not defaults from `.env.example`).
2. **Ports**: `postgres` and `redis` ports are bound to `127.0.0.1` (done in compose) or removed entirely behind a reverse proxy.
3. **Lookup API**: `LOOKUP_ADMIN_TOKEN` is set to a strong value; port is `expose`-only (internal network).
4. **Worker Bot API**: port 8181 is `expose`-only (internal network).
5. **Redis**: `REDIS_PASSWORD` is set and `REDIS_URL` includes the password.
6. **CORS**: `CORS_ORIGINS` in `.env` lists only your actual panel domain(s).
7. **ENVIRONMENT=production**: enables strict checks in `web_panel/config.py` (fails on missing secrets).
8. **Backups**: schedule `pg_dump` cron + offsite copy of `./data/` (lookup SQLite, uploads).
9. **TLS**: web panel and any public-facing endpoints behind HTTPS reverse proxy (nginx/caddy).
10. **Monitoring**: check `/health` endpoints on web_panel, lookup_api, worker_bot, support_bot.

## Source Of Truth

Для запуска и smoke-проверок использовать этот файл вместе с:
- `docker-compose.yml`
- `.env.example`
- `run_local.py`
