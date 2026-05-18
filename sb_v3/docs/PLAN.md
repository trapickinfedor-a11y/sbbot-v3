# MASTER PLAN — SBBot v3 (look)

**Дата:** 2026-05-17
**Продукт:** Multi-search Telegram bot v3
**APIs:** usfull.pro (SSN/DL/CR) + Enformion (phone/address/batch)

---

## Что есть

### SBBot v3 Core (`core/`)
- **bot.py** — 3,672 строк, python-telegram-bot, handlers, keyboards, FSM, batch processing
- **usfull_engine.py** — usfull.pro API client (SSN/DL/CR, balance, circuit breaker, health scoring)
- **sb_engine.py** — Enformion API client (phone/address/background/email/batch)
- **database.py** — SQLite schema, users, accounts, logs
- **formatters.py** — результаты → text/TXT/CSV/JSON экспорт
- **payments.py** — CryptoPay/Cryptomus/Helekit/BTCPay integration
- **matching.py** — Match fullz, deduplication
- **api.py** — REST API endpoints (single/bulk/job status/usage)
- **schema.ts** — Drizzle schema (users, apiKeys, searchRequests, auditLogs, notifications, systemSettings)

### Lookup API (`docs/NEWLOOKUP_docs/lookup_api/`)
- Self-hosted SSN/DL/CR API (usfull.info совместимый)
- API endpoints: `/api/search/`, `/api/dl/`, `/api/cr/`, `/api/create_token/`
- Импорт CSV, управление ключами, баланс, биллинг

---

## План

### Сейчас
1. Починить usfull_engine health scoring и circuit breaker
2. Запустить бота с реальным токеном
3. Проверить баланс usfull.pro

### Короткий срок
1. Подключить реальные API ключи usfull.pro
2. Построить цепочку SSN → DL → CR
3. Добавить batch processing для всех search types
4. Протестировать payment flow (CryptoPay/Cryptomus/BTCPay)

### Средний срок
1. Self-hosted Lookup API на своём сервере
2. Админка для управления ключами и балансом
3. Мониторинг: Grafana/Metabase dashboards
4. Celery worker для фоновых задач
