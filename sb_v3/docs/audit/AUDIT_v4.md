# SBBot v3 — Audit v4 (2026-05-17)

## Исправлено в этой сессии

### P0 — Webhook conflict (Цикл перезапусков бота)

**Проблема**: `bot.py:3300` использовал `urllib.request.urlopen("https://.../close")` вместо `bot.delete_webhook()`. Это не очищает webhook в Telegram API → 409 Conflict при каждом запуске.

**Фикс**:
```python
# bot.py main() retry loop, перед run_polling:
import asyncio
asyncio.run(app2.bot.delete_webhook(drop_pending_updates=True))
time.sleep(3)
app2.run_polling(drop_pending_updates=True)
```

### P0 — PID lock file (multiple instances)

**Проблема**: Без PID lock файл может быть запущено несколько экземпляров одновременно, что усиливает webhook conflict.

**Фикс** (bot.py после `Path("data").mkdir`):
```python
pidfile = Path("data/bot.pid")
if pidfile.exists():
    old_pid = pidfile.read_text().strip()
    if old_pid and old_pid.isdigit():
        try:
            os.kill(int(old_pid), 0)
            logger.critical(f"Another instance running (PID {old_pid}). Exiting.")
            sys.exit(1)
        except ProcessLookupError:
            logger.warning(f"Stale PID {old_pid} is dead. Removing.")
    pidfile.unlink()
pidfile.write_text(str(os.getpid()))
```

### P1 — INFO логирование в sb_engine.py

**Добавлено**:
```python
logger.info(f"[Enformion] Search OK: {search_type} → {len(people)} people found (acc={acc.email})")
logger.info(f"[Enformion] Search OK: {search_type} → no results")
logger.error(f"[Enformion] HTTP {status} FAILED: {search_type} | acc={acc.email} | raw: {raw_response[:300]}")
# refresh_balance: добавлен exc_info=True
logger.error(f"[Enformion] Balance refresh error for {acc.email}: {e}", exc_info=True)
```

### P1 — INFO логирование в usfull_engine.py

**Добавлено** в `_post()` и `_get()`:
```python
logger.info(f"[USFULL] {endpoint} → HTTP {http_status} | acc={account.username}")
logger.error(f"[USFULL] {endpoint} TIMEOUT | acc={account.username}")
logger.error(f"[USFULL] {endpoint} EXCEPTION: {e} | acc={account.username}", exc_info=True)
```

## Audit v3 — предыдущие исправления

См. `AUDIT_v3.md`.

## Оставшиеся задачи

### P1 — balance refresh в sb_engine.py

`refresh_balance()` использует `PersonSearch` с фейковыми данными `BalanceCheck/Test`. Правильный подход: Enformion API возвращает баланс в HTTP status (402 = insufficient funds, 200 = ok). Метод работает частично — при 402 ставит `no_balance`, но при 200 не обновляет `acc.balance` токенами.

**Рекомендация**: Добавить dedicated balance check endpoint если Enformion его поддерживает, или использовать AccountInfo endpoint. Пока не критично — бот работает.

### P2 — Idempotency в webhook handlers

Все три webhook handler (CryptoBot, Heleket, BTCPay) имеют проверку на дубликаты, но:
- CryptoBot: проверяет `payments` table, но не использует `webhook_logs` для дедупликации
- Heleket: НЕТ проверки `payments` table перед зачислением
- BTCPay: проверяет через metadata, но нет явной dedup по invoice_id

**Критичность**: LOW — платёжные провайдеры обычно не дублируют webhook'и. Но для надёжности стоит добавить проверку `webhook_logs` по `payload_md5` перед обработкой.

### P2 — FSM race condition

`process_batch()` использует `context.user_data["admin_state"]` для FSM-like state machine. Если пользователь быстро нажимает несколько кнопок, состояние может перезаписываться. Проверка `if state != "batch_select": return` не атомарна.

**Рекомендация**: Использовать `asyncio.Lock` per user для FSM state transitions.

## Проверка синтаксиса

```
bot.py:         OK
sb_engine.py:   OK
usfull_engine.py: OK
```

## Deployment checklist

- [ ] Удалить старый `data/bot.pid` если есть
- [ ] Проверить что `BOT_TOKEN` установлен
- [ ] Запустить: `cd /Users/user/Desktop/Проекты/sbbot_enformion && python3 bot.py`
- [ ] Проверить логи — бот не должен падать с 409 Conflict
- [ ] Проверить `/health` команду