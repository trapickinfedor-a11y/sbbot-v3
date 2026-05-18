# NewLookup — Map of Content

Obsidian-документация проекта NewLookup. Wiki-ссылки для Graph View.

## Статистика проекта

| Модуль | Файлов | Строк кода (прим.) |
|--------|--------|---------------------|
| [[Seller Bot]] | 45 | ~8 500 |
| [[Support Bot]] | 51 | ~12 000 |
| Main Bot ([[Architecture]]) | 34 | ~2 500 |
| [[Web Panel]] | 204 | ~35 000+ |
| [[Mini App]] | 83 | ~8 500 |
| [[Shared Services]] | 78 | ~18 000 |
| [[Lookup API]] | 3 | ~1 500 |
| [[DB Models]] | 1 (+миграции) | ~5 100 |
| **Итого** | **~499** | **~91 000+** |

## Модули

- [[Architecture]] — стек, Main Bot, конфигурация, точки входа
- [[Seller Bot]] — Telegram-бот для селлеров (45 файлов, 13+ FSM, 4 языка)
- [[Support Bot]] — Telegram-бот для воркеров/поддержки (51 файл, seller moderation 1582 строки)
- [[Web Panel]] — FastAPI admin-панель (204 файла, 40+ API, Jinja2 templates)
- [[Mini App]] — React 19 + TypeScript Seller Mini App V2 (83 файла, 7 табов)
- [[Shared Services]] — общий слой: 78 файлов, LedgerService (1072 строки), UploadPipeline (1363 строки)
- [[Lookup API]] — FastAPI + SQLite, SSN/DL/CreditReport (3 файла, порт :8001)
- [[DB Models]] — SQLAlchemy 2804 строки + 50+ таблиц из миграций

## Связи между компонентами

```
Seller Bot ←→ Web Panel    (moderation API, seller_mini_app.py)
Support Bot ←→ Main Bot    (HTTP :8080, 5 notify endpoints)
Seller Bot ←→ Support Bot  (dispute_service, conversation service)
Web Panel ←→ Shared        (ledger, deposits, moderation pricing)
Mini App ←→ Web Panel      (/api/seller-mini-app/*, 43 endpoints)
Lookup API                  (автономный, SQLite, порт :8001)
```

## Порты

| Компонент | Порт |
|-----------|------|
| Web Panel | :8000 |
| Lookup API | :8001 |
| Main Bot API | :8080 |
