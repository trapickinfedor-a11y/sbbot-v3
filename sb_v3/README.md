# SearchBug Bot v2

Многопоточный Telegram-бот для поиска через searchbug.com с управлением пулом аккаунтов, прокси-ротацией и алертами администратору.

---

## Быстрый старт

```bash
# 1. Установить зависимости
pip install -r requirements.txt

# 2. Задать токен бота
export BOT_TOKEN="ваш_токен_от_BotFather"

# 3. Запустить
python3 bot.py
```

---

## Настройка

### Переменные окружения

| Переменная | Описание | Обязательно |
|---|---|---|
| `BOT_TOKEN` | Токен от @BotFather | ✅ Да |
| `EMAILREP_KEY` | API ключ emailrep.io (100 req/day бесплатно без ключа) | Нет |
| `BATCH_SIZE` | Кол-во параллельных запросов в batch (по умолчанию: 5) | Нет |

---

## Загрузка аккаунтов

### Способ 1 — Файл (рекомендуется)

Отправьте боту `.txt` файл после команды `/loadaccounts`:

```
email:password:proxy
email:password
```

Пример (`accounts.txt`):
```
user1@gmail.com:pass123:http://login:pass@proxy1.host:8080
user2@gmail.com:pass456:http://login:pass@proxy2.host:8080
user3@gmail.com:pass789:socks5://login:pass@proxy3.host:1080
user4@gmail.com:pass000
```

### Способ 2 — Команда

```
/addaccount user@mail.com password http://proxy:8080
```

### Способ 3 — Через Admin Panel

Кнопка **➕ Добавить аккаунт** → введите `email password proxy`

---

## Распределение нагрузки

- **Round-Robin**: каждый новый запрос идёт на следующий аккаунт по кругу
- **1 аккаунт = 1 прокси**: каждая сессия привязана к своему прокси навсегда
- **Batch**: параллельная обработка через `asyncio.Semaphore(BATCH_SIZE)`
- **Автоматический пропуск**: аккаунты со статусом `no_balance` / `blocked` / `failed` пропускаются

---

## Мониторинг баланса

Каждые **5 минут** бот проверяет баланс всех активных аккаунтов.

### Статусы аккаунтов

| Статус | Иконка | Описание |
|---|---|---|
| `active` | ✅ | Работает нормально |
| `low_balance` | ⚠️ | Баланс ≤ 30% от начального |
| `no_balance` | ❌ | Баланс = 0, аккаунт пропускается |
| `blocked` | ⛔ | Аккаунт заблокирован SearchBug |
| `failed` | 🔴 | Ошибка входа |

### Алерты администратору

Бот присылает уведомление в чат администратора когда:
- Баланс упал до ≤ 30% → `⚠️ Низкий баланс: 28%`
- Баланс стал 0 → `❌ Аккаунт без баланса`
- Аккаунт заблокирован → `⛔ Аккаунт заблокирован`

**Настройка чата для алертов:**
```
/setadminchat
```
(выполнить в нужном чате/группе)

---

## Услуги и цены

| Раздел | Услуга | Цена по умолчанию |
|---|---|---|
| 📞 Phone | Reverse Lookup | $2.00 |
| 📞 Phone | Identify Type | $0.10 |
| 📞 Phone | Verify Active | $0.10 |
| 📞 Phone | Batch Lookup | $2.00 × N |
| 🏠 Address | Reverse Lookup | $2.00 |
| 🏠 Address | Number+Address Lookup | $2.00 |
| 🏠 Address | Verify (USPS) | $0.30 |
| 🏠 Address | Batch Lookup | $2.00 × N |
| 🔍 Background | By Name | $3.00 |
| 🔍 Background | Batch | $3.00 × N |
| 📧 Email | Lookup | $2.00 |
| 📧 Email | Verify | $0.10 |
| 📧 Email | EmailRep Check | $0.10 |

Цены настраиваются через Admin Panel → ⚙️ Цены.

---

## Команды бота

### Пользовательские
| Команда | Описание |
|---|---|
| `/start` | Главное меню |
| `/balance` | Ваш баланс |

### Административные
| Команда | Описание |
|---|---|
| `/admin` | Панель администратора |
| `/sbstatus` | Статус пула SB аккаунтов |
| `/loadaccounts` | Загрузить файл аккаунтов |
| `/addaccount email pass [proxy]` | Добавить один аккаунт |
| `/reloadpool` | Перезагрузить пул без рестарта |
| `/setadmin [user_id]` | Назначить администратора |
| `/setadminchat` | Установить чат для алертов |
| `/ban USER_ID` | Заблокировать пользователя |
| `/unban USER_ID` | Разблокировать пользователя |

---

## Первый запуск

1. Запустите бота
2. Напишите `/setadmin` — станете администратором
3. Напишите `/setadminchat` — этот чат получит алерты
4. Напишите `/loadaccounts` — загрузите файл аккаунтов
5. Проверьте `/sbstatus` — убедитесь что аккаунты активны

---

## Структура файлов

```
sbbot_v2/
├── bot.py              — Telegram бот (handlers, UI)
├── sb_engine.py        — Движок SearchBug (login, search, pool)
├── database.py         — SQLite база данных
├── formatter.py        — Форматирование результатов + экспорт
├── requirements.txt    — Зависимости Python
├── run.sh              — Скрипт запуска
├── accounts_example.txt — Пример файла аккаунтов
├── data/               — База данных (создаётся автоматически)
├── logs/               — Логи (создаётся автоматически)
└── exports/            — Экспортированные файлы
```

---

## SOCKS5 прокси

Для SOCKS5 нужна дополнительная библиотека:

```bash
pip install aiohttp-socks
```

Затем раскомментируйте строку в `requirements.txt`.

---

## Поддержка

SSN Lookup — будет добавлен в следующей версии.
