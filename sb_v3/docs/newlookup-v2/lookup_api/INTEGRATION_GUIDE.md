# Lookup API — Интеграция с ботами

## Быстрая интеграция

Lookup API уже полностью совместим с существующим кодом ботов через `UsfullClient`. Никаких изменений в коде не требуется.

## Шаг 1: Настройка переменных окружения

В файле `.env` проекта измените:

```bash
# Было (внешний API)
LOOKUP_API_BASE_URL=https://usfull.pro
LOOKUP_API_KEY=your_external_key

# Стало (self-hosted)
LOOKUP_API_BASE_URL=http://lookup_api:8082  # для Docker
# или
LOOKUP_API_BASE_URL=http://localhost:8001   # для локальной разработки
```

## Шаг 2: Создание API ключа для ботов

### Вариант A: Через manage_keys.py

```bash
cd lookup_api
LOOKUP_DB_PATH=../data/lookup.db python3 manage_keys.py create bot_production strong_password_here --balance 10000.0
```

Вывод:
```
✅ Created API key for 'bot_production'
   API Key: abc123def456...
   Balance: $10000.00
```

### Вариант B: Через API

```bash
curl -X POST 'http://localhost:8001/api/create_token/' \
  -H 'Content-Type: application/json' \
  -d '{"username":"bot_production","password":"strong_password_here"}'
```

## Шаг 3: Сохранение ключа в базе данных ботов

API ключ должен быть сохранён в таблице `api_keys` основной базы данных:

```sql
-- Подключиться к PostgreSQL
psql -U newlookup -d newlookup

-- Вставить ключ
INSERT INTO api_keys (key_name, key_value, key_type, is_active, created_at)
VALUES (
    'lookup_api',
    'abc123def456...',  -- ваш API ключ из шага 2
    'lookup',
    true,
    NOW()
);
```

Или через Python:

```python
from shared.database.session import get_session
from shared.database.models import APIKey

async with get_session() as session:
    api_key = APIKey(
        key_name="lookup_api",
        key_value="abc123def456...",  # ваш API ключ
        key_type="lookup",
        is_active=True
    )
    session.add(api_key)
    await session.commit()
```

## Шаг 4: Проверка интеграции

### Автоматическое использование в ботах

Боты автоматически загружают ключ из БД и используют Lookup API:

```python
# В mirror_bot/services/ssn_dl_automation.py
from mirror_bot.services.ssn_dl_automation import _load_usfull_client

async with get_session() as session:
    client = await _load_usfull_client(session)
    if client:
        # Автоматически использует LOOKUP_API_BASE_URL из .env
        result = await client.search_ssn(
            firstname="JOHN",
            lastname="DOE",
            st="NY"
        )
        print(f"Found {result['count']} records")
```

### Ручное тестирование

```python
from mirror_bot.services.usfull_service import UsfullClient

client = UsfullClient(api_key="abc123def456...")

# SSN поиск
result = await client.search_ssn(
    firstname="THOMAS",
    lastname="DICKSON",
    st="PA",
    zip_code="15211"
)
print(f"Found {result['count']} records")

# DL поиск
result = await client.search_dl(
    first_name="JOHN",
    last_name="DOE",
    address="123 MAIN ST, NEW YORK, NY",
    zipcode="10001",
    dob="19900115"
)
print(f"License: {result.get('license_number')}")

# Credit Report поиск
result = await client.search_cr(
    ssn="123456789",
    bureau="transunion"
)
print(f"Credit Score: {result['results'][0]['credit_score']}")

# Проверка баланса
balance = await client.get_balance()
print(f"Balance: ${balance}")
```

## Как это работает

### Архитектура

```
┌──────────────┐
│  Mirror Bot  │
│              │
│ OrderStates  │
│ waiting_data │
└──────┬───────┘
       │
       │ 1. Парсит данные заказа
       │    (SSNLookupData, DLLookupData, etc.)
       │
       ▼
┌──────────────────────────────┐
│ ssn_dl_automation.py         │
│                              │
│ async def process_ssn_order()│
└──────┬───────────────────────┘
       │
       │ 2. Загружает UsfullClient
       │    из api_keys таблицы
       │
       ▼
┌──────────────────────────────┐
│ UsfullClient                 │
│ (usfull_service.py)          │
│                              │
│ BASE_URL = os.getenv(        │
│   "LOOKUP_API_BASE_URL",     │
│   "https://usfull.pro"       │
│ )                            │
└──────┬───────────────────────┘
       │
       │ 3. HTTP запрос
       │    POST /api/search/
       │    X-API-KEY: abc123...
       │
       ▼
┌──────────────────────────────┐
│ Lookup API                   │
│ (app.py)                     │
│                              │
│ @app.post("/api/search/")    │
│ def search_ssn(...)          │
└──────┬───────────────────────┘
       │
       │ 4. Поиск в SQLite
       │    FTS5 + индексы
       │
       ▼
┌──────────────────────────────┐
│ lookup.db                    │
│                              │
│ - persons (SSN records)      │
│ - persons_fts (FTS index)    │
│ - licenses (DL records)      │
│ - cr_records (Credit Reports)│
│ - billing_log (биллинг)      │
└──────────────────────────────┘
```

### Поток данных для SSN заказа

1. **Пользователь отправляет данные в бот:**
   ```
   John Doe
   123 Main St, New York, NY 10001
   01/15/1990
   ```

2. **Бот парсит в SSNLookupData:**
   ```python
   {
       "first_name": "JOHN",
       "last_name": "DOE",
       "address": "123 MAIN ST",
       "city": "NEW YORK",
       "state": "NY",
       "zip_code": "10001",
       "dob": "01/15/1990"
   }
   ```

3. **ssn_dl_automation.py вызывает API:**
   ```python
   client = await _load_usfull_client(session)
   result = await client.search_ssn_from_order_data(order.input_data)
   ```

4. **UsfullClient отправляет HTTP запрос:**
   ```http
   POST http://lookup_api:8082/api/search/
   X-API-KEY: abc123...
   Content-Type: application/json

   {
       "firstname": "JOHN",
       "lastname": "DOE",
       "city": "NEW YORK",
       "st": "NY",
       "zip": "10001",
       "dob": "19900115"
   }
   ```

5. **Lookup API ищет в базе:**
   ```sql
   -- FTS поиск по имени
   SELECT rowid FROM persons_fts 
   WHERE persons_fts MATCH '"JOHN" "DOE"'
   
   -- Фильтрация по дополнительным полям
   SELECT * FROM persons 
   WHERE id IN (...)
     AND dob = '19900115'
     AND st = 'NY'
     AND zip = '10001'
   ```

6. **API возвращает результаты:**
   ```json
   {
       "status": "ok",
       "count": 2,
       "results": [
           {
               "id": 123,
               "firstname": "JOHN",
               "lastname": "DOE",
               "ssn": "123456789",
               "dob": "19900115",
               "address": "123 MAIN ST",
               "city": "NEW YORK",
               "st": "NY",
               "zip": "10001",
               "phone": "2125551234"
           }
       ]
   }
   ```

7. **Бот форматирует и отправляет пользователю:**
   ```
   ✅ Found 2 records:

   1️⃣ JOHN DOE
   📋 SSN: 123-45-6789
   🎂 DOB: 01/15/1990
   📍 123 MAIN ST, NEW YORK, NY 10001
   📞 (212) 555-1234
   ```

## Мониторинг использования

### Проверка баланса

```bash
# Через manage_keys.py
LOOKUP_DB_PATH=../data/lookup.db python3 manage_keys.py balance bot_production

# Через API
curl -X GET 'http://localhost:8001/api/get_balance/' \
  -H 'X-API-KEY: abc123...'
```

### История биллинга

```sql
-- Подключиться к lookup.db
sqlite3 /path/to/lookup.db

-- Последние 20 операций
SELECT 
    datetime(created_at) as time,
    service,
    amount,
    description
FROM billing_log
WHERE api_key_id = (SELECT id FROM api_keys WHERE username = 'bot_production')
ORDER BY created_at DESC
LIMIT 20;
```

### Статистика использования

```bash
curl -X GET 'http://localhost:8001/api/admin/stats' \
  -H 'X-Admin-Token: your_admin_token'
```

Ответ:
```json
{
    "persons_count": 15000,
    "licenses_count": 8500,
    "cr_records_count": 3200,
    "api_keys_count": 5,
    "total_billed": 1250.50,
    "db_size_mb": 245.3
}
```

## Автоматическое пополнение баланса

### Через cron (рекомендуется)

```bash
# Добавить в crontab
0 0 1 * * cd /path/to/lookup_api && LOOKUP_DB_PATH=../data/lookup.db python3 manage_keys.py add-balance bot_production 1000.0
```

### Через скрипт мониторинга

```python
import asyncio
from mirror_bot.services.usfull_service import UsfullClient

async def check_and_refill():
    client = UsfullClient(api_key="abc123...")
    balance = await client.get_balance()
    
    if balance < 100:
        # Отправить уведомление админу
        print(f"⚠️ Low balance: ${balance}")
        
        # Автоматически пополнить
        # (через admin API или manage_keys.py)

asyncio.run(check_and_refill())
```

## Переключение между self-hosted и внешним API

### Для тестирования

```bash
# .env.local (локальная разработка)
LOOKUP_API_BASE_URL=http://localhost:8001

# .env.production (production с self-hosted)
LOOKUP_API_BASE_URL=http://lookup_api:8082

# .env.external (fallback на внешний API)
LOOKUP_API_BASE_URL=https://usfull.pro
```

### Динамическое переключение

```python
import os

# Проверить доступность self-hosted API
try:
    response = await client.get(f"{os.getenv('LOOKUP_API_BASE_URL')}/health")
    if response.status_code == 200:
        # Использовать self-hosted
        pass
except:
    # Fallback на внешний API
    os.environ["LOOKUP_API_BASE_URL"] = "https://usfull.pro"
```

## Troubleshooting

### Бот не находит API ключ

```python
# Проверить наличие ключа в БД
async with get_session() as session:
    key = await session.execute(
        select(APIKey).where(
            APIKey.key_name == "lookup_api",
            APIKey.is_active == True
        )
    )
    key = key.scalar_one_or_none()
    if not key:
        print("❌ API key not found in database")
```

### API возвращает 401 Unauthorized

```bash
# Проверить ключ в lookup.db
sqlite3 /path/to/lookup.db "SELECT username, api_key, is_active FROM api_keys WHERE api_key = 'abc123...';"
```

### API возвращает 402 Insufficient Balance

```bash
# Пополнить баланс
LOOKUP_DB_PATH=../data/lookup.db python3 manage_keys.py add-balance bot_production 1000.0
```

### Медленные запросы

```bash
# Перестроить FTS индекс
python3 importer.py rebuild-fts --db /path/to/lookup.db

# Проверить размер базы
du -h /path/to/lookup.db

# Оптимизировать
sqlite3 /path/to/lookup.db "VACUUM; ANALYZE;"
```

## Резюме

✅ **Никаких изменений в коде ботов не требуется**  
✅ **Просто измените LOOKUP_API_BASE_URL в .env**  
✅ **Создайте API ключ и сохраните в api_keys таблицу**  
✅ **Импортируйте данные в lookup.db**  
✅ **Запустите lookup_api сервис через Docker Compose**

Всё остальное работает автоматически через существующий `UsfullClient`.
