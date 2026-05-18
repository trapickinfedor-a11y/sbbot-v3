# Deploy

Актуальная инструкция запуска перенесена в `docs/LAUNCH_RUNBOOK.md`.

## Quick Start

### Docker full stack

```bash
cp .env.example .env
mkdir -p data uploads media
docker compose up -d --build
```

### Local dev

```bash
cp .env.example .env
mkdir -p data uploads media
python3 run_local.py
```

## Notes

- `docker-compose.yml` является источником правды для production-like запуска.
- `run_local.py` является источником правды для local SQLite режима.
- Миграции выполняются через `shared.database.session.init_db()`.
- Общая `tasks.db` инициализируется через `shared.database.tasks_session.init_tasks_db()` только для reminder/background задач, не для payout finance records.

## Before Launch

- Заполнить все обязательные env vars из `.env.example`.
- Проверить единый `INTERNAL_API_TOKEN` для всех сервисов.
- Убедиться, что `./data` смонтирован в `support_bot`, `seller_bot` и `web_panel`.
- Пройти smoke checklist из `docs/LAUNCH_RUNBOOK.md`.
