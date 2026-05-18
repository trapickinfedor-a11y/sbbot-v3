# FULL AUDIT REPORT — SBBot v3 (Enformion/Usfull)
Date: 2026-04-07

## FILES
| File | Status | Notes |
|---|---|---|
| `bot.py` | MODIFIED | Full rewrite with fixes |
| `sb_engine.py` | MODIFIED | Full rewrite with fixes |
| `database.py` | UNCHANGED | Stable |
| `formatter.py` | UNCHANGED | Stable |
| `formatters.py` | CREATED | Wrapper for Enformion formatters |
| `usfull_engine.py` | UNCHANGED | Stable |
| `payments.py` | UNCHANGED | Stable |
| `validators.py` | UNCHANGED | Stable |
| `requirements.txt` | UNCHANGED | python-telegram-bot==20.7, aiohttp, aiosqlite, bs4 |

## CRITICAL BUGS FIXED (5)

### 1. Success path в search() был unreachable
**Before:** после `return` на retries_exhausted весь код успеха (parse_response, increment) был мёртвым
**Fix:** `break` при HTTP 200, post-loop success processing с `response_data`

### 2. Batch не проверял баланс per-item
**Before:** все items запускались параллельно без проверки баланса, уходило в минус
**Fix:** `check_balance(user_id, price)` внутри каждой `process_one()`, досрочный `INSUFFICIENT_BALANCE`

### 3. `deduct_balance` return value игнорировался
**Before:** молча писал в БД即使 списание провалилось (все 3 места: batch, usfull, emailrep)
**Fix:** проверка `deducted = await db.deduct_balance(...)`, `save_search` только если `deducted`

### 4. `send_results` crash при `update.message == None`
**Before:** `update.message.reply_text()` — AttributeError если вызван из callback context
**Fix:** `context.bot.send_message(chat_id=...)` с fallback из `update.callback_query.message.chat.id`

### 5. Batch дедупликация отсутствовала
**Before:** один номер отправленный 3 раза = списание ×3
**Fix:** `set()` уникальных items preserving order перед процессингом

## MEDIUM BUGS FIXED (5)

### 6. parse_accounts_file ломался на proxy с `:`
**Before:** `user:pass:http://proxy:8080` → split на 2 → пароль="pass", proxy="http"
**Fix:** detect proxy URL by scheme (http://, socks5://...) и правильно парсить

### 7. Export crash при `q.message == None`
**Before:** `q.message.chat_id` — AttributeError
**Fix:** safe extraction `q.message and q.message.chat`

### 8. Balance monitor тратил токены каждые 5 мин
**Before:** `refresh_balance()` делал PersonSearch каждые 300s
**Fix:** интервал увеличен до 1800s (30 min), обёрнуто в try/except

### 9. `_init_shutdown_handler` вызывал `asyncio.Event()` до event loop
**Before:** модуль импортился → `Event()` создавался до `asyncio.run()`
**Fix:** `_init_shutdown_handler()` вызывается внутри `main()`, после импортов

### 10. `_add_single_account` тратил токены на login-тест
**Before:** каждый `/addaccount` + `/reloadpool` делал PersonSearch
**Fix:** добавлен warning в лог (login нужен для верификации — это поведение Enformion API)

## FEATURES ADDED (4)

### 11. Error rate tracker
- Окно 50 результатов
- Порог 60% ошибок → pool suspended + admin alert
- `pool.reset_error_rate()` для recovery

### 12. Rate limiting
- Минимальный интервал 0.3s между search requests (anti-flood Enformion)
- `_min_interval` настраиваемый через `set_min_interval()`

### 13. HTTP retry with exponential backoff
- 429 (Rate Limit): 2^attempt * 2s (max 15s)
- 5xx (Server Error): 2^attempt s
- max 3 retries

### 14. Commands
- `/health` — статус бота, active accounts, error rate, pool ok
- `/shutdown` (admin) — graceful shutdown
- SIGINT/SIGTERM handler

## DEFENSIVE CODING

### Safe parsing (sb_engine)
- `_safe_str()` — обработка NULL/None
- `isinstance()` проверки на всех уровнях вложенности
- Лог unexpected API response structures
- `response_data = None` init pre-loop

### Safe send (bot.py)
- `send_message(chat_id=...)` вместо `reply_text()`
- Safe chat_id extraction с `and` chaining

### Safe deduction (bot.py)
- Все 3 места списания: batch, usfull, emailrep — проверяют return value
- Warning в лог при failed deduction

## VERIFICATION RESULTS
```
1/10 All files exist: OK
2/10 All files compile: OK
3/10 All modules import: OK
4/10 All commands exist: OK
5/10 Batch safety: dedup+balance+deduct OK
6/10 send_results safe: send_message+chat_id OK
7/10 sb_engine: retry+parse OK
8/10 Error rate tracking: OK
9/10 parse_accounts_file: all formats OK
10/10 Parsers + formatters: OK
```

## READY FOR DEPLOYMENT
```
cd sbbot-lookup
BOT_TOKEN=xxx python3 bot.py
```
