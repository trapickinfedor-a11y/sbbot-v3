# Integration README

Этот репозиторий больше не запускается через legacy `system_launcher.py` как основной production-path.

## Current Integration Topology

- `main_bot` поднимает основной polling и HTTP API управления mirror bots.
- `mirror_bot` обслуживает buyers и создаёт orders.
- `support_bot` принимает HTTP notifications и работает как support/worker bot.
- `seller_bot` управляет seller inventory, chat и upload flows.
- `web_panel` даёт admin UI, seller mini app API и scheduler jobs.
- `marketer_bot` обслуживает promo/referral контур.
- `shared` содержит общие модели, БД, internal auth и cross-service services.

## Integration Rules

- Все сервисы используют одну основную БД через `DATABASE_URL`.
- Внутренние HTTP вызовы используют общий `INTERNAL_API_TOKEN`.
- `support_bot`, `seller_bot` и `web_panel` делят один `TASKS_DATABASE_URL`.
- `Brute` группируется по `bank_code`; seller-side category selection для brute отсутствует.
- Seller mini app должен отправлять те же payload-поля, что и seller upload pipeline.

## Launch References

- Запуск и recovery: `docs/LAUNCH_RUNBOOK.md`
- Docker topology: `docker-compose.yml`
- Local topology: `run_local.py`
- Env template: `.env.example`
