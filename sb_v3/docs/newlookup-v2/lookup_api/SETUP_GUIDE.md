# Lookup API — Полное руководство по настройке

## Обзор

Lookup API — это self-hosted сервис для поиска SSN, Driver License и Credit Reports, полностью совместимый с интерфейсом usfull.info. Позволяет использовать собственную базу данных вместо внешнего платного API.

## Архитектура

```
┌─────────────┐
│ Mirror Bot  │──┐
└─────────────┘  │
                 │  HTTP (X-API-KEY)
┌─────────────┐  │
│ Worker Bot  │──┼──► ┌──────────────┐      ┌──────────────┐
└─────────────┘  │    │ Lookup API   │─────►│  SQLite DB   │
                 │    │ (port 8082)  │      │ (lookup.db)  │
┌─────────────┐  │    └──────────────┘      └──────────────┘
│ Support Bot │──┘
└─────────────┘
```

## Быстрый старт (Production)

### 1. Настройка переменных окружения

В `.env` файле проекта:

```bash
# Lookup API Configuration
LOOKUP_API_BASE_URL=http://lookup_api:8082
LOOKUP_API_PORT=8082
LOOKUP_ADMIN_TOKEN=your_secure_random_token_here_min_32_chars

# Pricing
PRICE_SSN_FOUND=0.40
PRICE_SSN_NOFOUND=0.01
PRICE_DL_FOUND=1.00
PRICE_DL_NOFOUND=0.00
PRICE_CR_FOUND=0.40
PRICE_CR_NOFOUND=0.01
```

**Важно:** Сгенерируйте надёжный `LOOKUP_ADMIN_TOKEN`:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 2. Запуск через Docker Compose

```bash
# Запустить только Lookup API (для тестирования)
docker compose up lookup_api -d

# Или запустить весь стек
docker compose up -d
```

API будет доступен внутри Docker сети на `http://lookup_api:8082`.

### 3. Создание API ключа для ботов

```bash
# Войти в контейнер
docker exec -it newlookup_lookup_api bash

# Создать ключ
python3 manage_keys.py create bot_user secure_password_123 --balance 1000.0

# Скопировать API Key из вывода
```

Или через API:

```bash
curl -X POST 'http://localhost:8082/api/create_token/' \
  -H 'Content-Type: application/json' \
  -d '{"username":"bot_user","password":"secure_password_123"}'
```

### 4. Сохранение API ключа в базе ботов

API ключ нужно сохранить в таблице `api_keys` основной базы данных ботов:

```sql
INSERT INTO api_keys (key_name, key_value, key_type, is_active)
VALUES ('lookup_api', 'your_api_key_here', 'lookup', 1);
```

Или через Support Bot (если есть соответствующий handler).

### 5. Импорт данных

#### Подготовка CSV файлов

**Формат для SSN (persons):**
```csv
firstname,lastname,middlename,ssn,dob,address,city,st,zip,phone,name_suff
JOHN,DOE,M,123456789,19900115,123 MAIN ST,NEW YORK,NY,10001,2125551234,
```

**Формат для DL (licenses):**
```csv
first_name,last_name,dob,address,city,state,zipcode,license_number,license_state
JOHN,DOE,19900115,123 MAIN ST,NEW YORK,NY,10001,D12345678,NY
```

**Формат для Credit Reports:**
```csv
ssn,first_name,last_name,dob,address,city,state,zip_code,bureau,credit_score,report_json,raw_text
123456789,JOHN,DOE,19900115,123 MAIN ST,NEW YORK,NY,10001,transunion,720,{},
```

#### Импорт через Docker

```bash
# Скопировать CSV в контейнер
docker cp /path/to/ssn_data.csv newlookup_lookup_api:/tmp/

# Войти в контейнер
docker exec -it newlookup_lookup_api bash

# Импортировать
python3 importer.py persons /tmp/ssn_data.csv --db /app/data/lookup.db
python3 importer.py licenses /tmp/dl_data.csv --db /app/data/lookup.db
python3 importer.py credit-reports /tmp/cr_data.csv --db /app/data/lookup.db

# Перестроить FTS индекс
python3 importer.py rebuild-fts --db /app/data/lookup.db
```

### 6. Проверка работы

```bash
# Проверить баланс
curl -X GET 'http://localhost:8082/api/get_balance/' \
  -H 'X-API-KEY: your_api_key'

# Тестовый поиск SSN
curl -X POST 'http://localhost:8082/api/search/' \
  -H 'Content-Type: application/json' \
  -H 'X-API-KEY: your_api_key' \
  -d '{"firstname":"JOHN","lastname":"DOE","st":"NY"}'
```

## Локальная разработка

### 1. Установка зависимостей

```bash
cd lookup_api
pip install -r requirements.txt
```

### 2. Инициализация БД

```bash
export LOOKUP_DB_PATH=/Users/user/Desktop/прокты/newlookup/data/lookup.db
python3 -c "import sys; sys.path.insert(0, '.'); from app import init_db; init_db()"
```

### 3. Создание тестового ключа

```bash
python3 manage_keys.py create test_user test_password --balance 100.0
```

### 4. Запуск сервера

```bash
./start_lookup_api.sh
```

Или вручную:

```bash
export LOOKUP_DB_PATH=/path/to/lookup.db
python3 -m uvicorn app:app --host 0.0.0.0 --port 8001 --reload
```

## Управление API ключами

### Создание ключа

```bash
python3 manage_keys.py create username password --balance 1000.0
```

### Список всех ключей

```bash
python3 manage_keys.py list
```

Вывод:
```
Username             API Key                                                          Balance      Active   Created
----------------------------------------------------------------------------------------------------------------------------------
bot_user             4ae7e27294ee5905d99dd0a26bc0fe5b5353bffd273f31dddad80a526d015c31 $1000.00     ✅       2026-03-22 16:10:28
test_user            abc123...                                                        $98.80       ✅       2026-03-22 15:30:15
```

### Проверка баланса

```bash
python3 manage_keys.py balance username
```

### Пополнение баланса

```bash
python3 manage_keys.py add-balance username 500.0
```

### Деактивация/активация

```bash
python3 manage_keys.py deactivate username
python3 manage_keys.py activate username
```

## Интеграция с ботами

Боты автоматически используют Lookup API, если в `.env` указан `LOOKUP_API_BASE_URL`.

### Как это работает

1. `UsfullClient` в `mirror_bot/services/usfull_service.py` читает `LOOKUP_API_BASE_URL`
2. Если указан `http://lookup_api:8082` — использует self-hosted API
3. Если не указан или `https://usfull.pro` — использует внешний API
4. Интерфейс полностью совместим, код ботов не меняется

### Получение API ключа в боте

Боты загружают ключ из таблицы `api_keys`:

```python
from mirror_bot.services.ssn_dl_automation import _load_usfull_client

async with get_session() as session:
    client = await _load_usfull_client(session)
    if client:
        result = await client.search_ssn(
            firstname="JOHN",
            lastname="DOE",
            st="NY"
        )
```

## Мониторинг и обслуживание

### Проверка здоровья API

```bash
curl http://localhost:8082/health
```

### Просмотр логов

```bash
docker logs -f newlookup_lookup_api
```

### Статистика использования

```bash
curl -X GET 'http://localhost:8082/api/admin/stats' \
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

### Список пользователей

```bash
curl -X GET 'http://localhost:8082/api/admin/users' \
  -H 'X-Admin-Token: your_admin_token'
```

### Пополнение баланса через API

```bash
curl -X POST 'http://localhost:8082/api/admin/add_balance' \
  -H 'Content-Type: application/json' \
  -H 'X-Admin-Token: your_admin_token' \
  -d '{"username":"bot_user","amount":500.0,"note":"Monthly top-up"}'
```

## Резервное копирование

### Backup базы данных

```bash
# Из контейнера
docker exec newlookup_lookup_api sqlite3 /app/data/lookup.db ".backup /app/data/lookup_backup_$(date +%Y%m%d).db"

# Скопировать на хост
docker cp newlookup_lookup_api:/app/data/lookup_backup_20260322.db ./backups/
```

### Восстановление

```bash
# Скопировать backup в контейнер
docker cp ./backups/lookup_backup_20260322.db newlookup_lookup_api:/app/data/

# Восстановить
docker exec newlookup_lookup_api cp /app/data/lookup_backup_20260322.db /app/data/lookup.db

# Перезапустить API
docker restart newlookup_lookup_api
```

## Производительность

### Оптимизация для больших баз

Если база данных содержит миллионы записей:

1. **Увеличить размер кэша SQLite:**
   ```python
   conn.execute("PRAGMA cache_size = -64000")  # 64MB
   ```

2. **Использовать индексы:**
   ```sql
   CREATE INDEX IF NOT EXISTS idx_persons_name_dob ON persons(lastname, firstname, dob);
   CREATE INDEX IF NOT EXISTS idx_persons_zip_st ON persons(zip, st);
   ```

3. **Периодически перестраивать FTS:**
   ```bash
   python3 importer.py rebuild-fts --db /app/data/lookup.db
   ```

4. **Мониторить размер базы:**
   ```bash
   docker exec newlookup_lookup_api du -h /app/data/lookup.db
   ```

### Масштабирование

Для высоких нагрузок:

1. Запустить несколько реплик API:
   ```yaml
   lookup_api:
     deploy:
       replicas: 3
   ```

2. Добавить load balancer (nginx):
   ```nginx
   upstream lookup_api {
       server lookup_api_1:8082;
       server lookup_api_2:8082;
       server lookup_api_3:8082;
   }
   ```

3. Использовать read-only реплики БД для поисковых запросов.

## Troubleshooting

### API не отвечает

```bash
# Проверить статус контейнера
docker ps | grep lookup_api

# Проверить логи
docker logs newlookup_lookup_api --tail 100

# Проверить healthcheck
docker inspect newlookup_lookup_api | grep -A 10 Health
```

### База данных заблокирована

```bash
# Проверить WAL файлы
docker exec newlookup_lookup_api ls -lh /app/data/lookup.db*

# Сделать checkpoint
docker exec newlookup_lookup_api sqlite3 /app/data/lookup.db "PRAGMA wal_checkpoint(TRUNCATE);"
```

### FTS поиск не работает

```bash
# Перестроить индекс
docker exec newlookup_lookup_api python3 importer.py rebuild-fts --db /app/data/lookup.db
```

### Недостаточно баланса

```bash
# Пополнить через manage_keys.py
docker exec newlookup_lookup_api python3 manage_keys.py add-balance bot_user 1000.0

# Или через admin API
curl -X POST 'http://localhost:8082/api/admin/add_balance' \
  -H 'X-Admin-Token: your_admin_token' \
  -d '{"username":"bot_user","amount":1000.0}'
```

## Безопасность

### Рекомендации

1. **Используйте сильные токены:**
   ```bash
   LOOKUP_ADMIN_TOKEN=$(python3 -c "import secrets; print(secrets.token_hex(32))")
   ```

2. **Не экспонируйте API наружу:**
   - В production убрать `ports:` из docker-compose.yml
   - Использовать только внутреннюю сеть `bot_network`

3. **Регулярно меняйте пароли:**
   ```bash
   # Деактивировать старый ключ
   python3 manage_keys.py deactivate old_user
   
   # Создать новый
   python3 manage_keys.py create new_user new_password --balance 1000.0
   ```

4. **Мониторьте использование:**
   ```bash
   # Проверить billing log
   docker exec newlookup_lookup_api sqlite3 /app/data/lookup.db \
     "SELECT * FROM billing_log ORDER BY created_at DESC LIMIT 20;"
   ```

5. **Backup регулярно:**
   ```bash
   # Добавить в crontab
   0 2 * * * docker exec newlookup_lookup_api sqlite3 /app/data/lookup.db ".backup /app/data/lookup_backup_$(date +\%Y\%m\%d).db"
   ```

## Миграция с usfull.info

### Шаг 1: Подготовка данных

Если у вас есть экспорт из usfull.info, конвертируйте в CSV:

```python
import json
import csv

with open('usfull_export.json') as f:
    data = json.load(f)

with open('persons.csv', 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['firstname', 'lastname', 'middlename', 'ssn', 'dob', 'address', 'city', 'st', 'zip', 'phone', 'name_suff'])
    writer.writeheader()
    for record in data['results']:
        writer.writerow({
            'firstname': record.get('firstname', ''),
            'lastname': record.get('lastname', ''),
            'middlename': record.get('middlename', ''),
            'ssn': record.get('ssn', ''),
            'dob': record.get('dob', ''),
            'address': record.get('address', ''),
            'city': record.get('city', ''),
            'st': record.get('st', ''),
            'zip': record.get('zip', ''),
            'phone': record.get('phone', ''),
            'name_suff': record.get('name_suff', ''),
        })
```

### Шаг 2: Импорт

```bash
python3 importer.py persons persons.csv --db /app/data/lookup.db
python3 importer.py rebuild-fts --db /app/data/lookup.db
```

### Шаг 3: Переключение

В `.env`:
```bash
# Было
LOOKUP_API_BASE_URL=https://usfull.pro

# Стало
LOOKUP_API_BASE_URL=http://lookup_api:8082
```

### Шаг 4: Тестирование

Запустить несколько тестовых запросов и сравнить результаты.

## Поддержка

При возникновении проблем:

1. Проверьте логи: `docker logs newlookup_lookup_api`
2. Проверьте healthcheck: `curl http://localhost:8082/health`
3. Проверьте базу данных: `docker exec newlookup_lookup_api sqlite3 /app/data/lookup.db ".tables"`
4. Проверьте документацию: `lookup_api/README.md`
