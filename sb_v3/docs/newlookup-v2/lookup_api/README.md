# Lookup API — Self-Hosted SSN/DL/Credit Report Search

Локальный API-сервер для поиска SSN, Driver License и Credit Reports, полностью совместимый с интерфейсом usfull.info.

## Быстрый старт

### 1. Установка зависимостей

```bash
cd lookup_api
pip install -r requirements.txt
```

### 2. Инициализация базы данных

```bash
# Создать пустую БД
export LOOKUP_DB_PATH=/Users/user/Desktop/прокты/newlookup/data/lookup.db
python3 -c "import sys; sys.path.insert(0, '.'); from app import init_db; init_db()"
```

### 3. Импорт данных

```bash
# Импорт SSN records
python3 importer.py persons ../data/ssn_import_data.csv --db ../data/lookup.db

# Импорт Driver Licenses (если есть)
python3 importer.py licenses /path/to/dl_data.csv --db ../data/lookup.db

# Импорт Credit Reports (если есть)
python3 importer.py credit-reports /path/to/cr_data.csv --db ../data/lookup.db

# Перестроить FTS индекс после импорта
python3 importer.py rebuild-fts --db ../data/lookup.db
```

### 4. Создание API ключа

```bash
curl -X POST 'http://localhost:8001/api/create_token/' \
  -H 'Content-Type: application/json' \
  -d '{"username":"your_username","password":"your_password"}'
```

Ответ:
```json
{
  "status": "ok",
  "api_key": "4ae7e27294ee5905d99dd0a26bc0fe5b5353bffd273f31dddad80a526d015c31",
  "balance": 0.0,
  "message": "Account created"
}
```

### 5. Запуск сервера

```bash
export LOOKUP_DB_PATH=/Users/user/Desktop/прокты/newlookup/data/lookup.db
python3 -m uvicorn app:app --host 0.0.0.0 --port 8001
```

Или используйте скрипт:
```bash
./start_lookup_api.sh
```

## API Endpoints

### POST /api/search/ — SSN Lookup

Поиск по имени/фамилии или прямой поиск по SSN.

**Запрос:**
```json
{
  "firstname": "THOMAS",
  "lastname": "DICKSON",
  "middlename": "B",
  "dob": "19701101",
  "city": "PITTSBURGH",
  "st": "PA",
  "zip": "15211",
  "ssn": "173640373"
}
```

**Поля:**
- `firstname`, `lastname` — обязательные для поиска по имени
- `ssn` — если указан, выполняется прямой поиск по SSN (игнорируя имя)
- `middlename`, `dob`, `city`, `st`, `zip` — опциональные фильтры

**Ответ:**
```json
{
  "status": "ok",
  "count": 5,
  "results": [
    {
      "id": 1,
      "firstname": "THOMAS",
      "lastname": "DICKSON",
      "middlename": "B",
      "ssn": "173640373",
      "dob": "19701101",
      "address": "415 GRIFFIN ST",
      "city": "PITTSBURGH",
      "st": "PA",
      "zip": "15211",
      "phone": "4124311840",
      "name_suff": "JR"
    }
  ]
}
```

**Пример curl:**
```bash
curl -X POST 'http://localhost:8001/api/search/' \
  -H 'Content-Type: application/json' \
  -H 'X-API-KEY: your_api_key' \
  -d '{"firstname":"THOMAS","lastname":"DICKSON","st":"PA","zip":"15211"}'
```

### POST /api/dl/ — Driver License Lookup

Поиск водительских прав по имени, ZIP и DOB.

**Запрос:**
```json
{
  "first_name": "JOHN",
  "last_name": "DOE",
  "address": "123 MAIN ST",
  "zipcode": "12345",
  "dob": "19900115"
}
```

### POST /api/cr/ — Credit Report Lookup

Поиск кредитных отчётов по SSN или имени+DOB.

**Запрос:**
```json
{
  "ssn": "123456789",
  "first_name": "JOHN",
  "last_name": "DOE",
  "dob": "19900115",
  "bureau": "transunion"
}
```

**bureau:** `transunion`, `experian`, `equifax`, `lexisnexis`, `wallet`, `any`

### GET /api/get_balance/

Проверка баланса аккаунта.

```bash
curl -X GET 'http://localhost:8001/api/get_balance/' \
  -H 'X-API-KEY: your_api_key'
```

## Конфигурация

Переменные окружения:

```bash
# Путь к базе данных
LOOKUP_DB_PATH=/path/to/lookup.db

# Токен администратора
LOOKUP_ADMIN_TOKEN=your_secure_admin_token

# Цены (совместимо с usfull.info)
PRICE_SSN_FOUND=0.40
PRICE_SSN_NOFOUND=0.01
PRICE_DL_FOUND=1.00
PRICE_DL_NOFOUND=0.00
PRICE_CR_FOUND=0.40
PRICE_CR_NOFOUND=0.01

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:8000
```

## Интеграция с ботом

В `.env` файле бота укажите:

```bash
# Вместо внешнего API используем локальный
LOOKUP_API_BASE_URL=http://localhost:8001
LOOKUP_API_KEY=your_api_key_here
```

Код бота (`mirror_bot/services/usfull_service.py`) автоматически будет использовать локальный API без изменений.

## Импорт данных

### Формат CSV для SSN (persons)

Колонки: `firstname`, `lastname`, `middlename`, `ssn`, `dob`, `address`, `city`, `st`, `zip`, `phone`, `name_suff`

```csv
firstname,lastname,middlename,ssn,dob,address,city,st,zip,phone,name_suff
THOMAS,DICKSON,B,173640373,19701101,415 GRIFFIN ST,PITTSBURGH,PA,15211,4124311840,JR
```

### Формат CSV для DL (licenses)

Колонки: `first_name`, `last_name`, `dob`, `address`, `city`, `state`, `zipcode`, `license_number`, `license_state`

### Формат CSV для Credit Reports

Колонки: `ssn`, `first_name`, `last_name`, `dob`, `address`, `city`, `state`, `zip_code`, `bureau`, `credit_score`, `report_json`, `raw_text`

## Admin API

### POST /api/admin/add_balance

Добавить баланс пользователю (требуется `X-Admin-Token`).

```bash
curl -X POST 'http://localhost:8001/api/admin/add_balance' \
  -H 'Content-Type: application/json' \
  -H 'X-Admin-Token: your_admin_token' \
  -d '{"username":"test_user","amount":100.0,"note":"Initial balance"}'
```

### GET /api/admin/users

Список всех пользователей.

### GET /api/admin/stats

Статистика БД (количество записей, биллинг).

## Тестовый аккаунт

Для тестирования создан аккаунт:

- **Username:** `test_user`
- **Password:** `test_password_123`
- **API Key:** `4ae7e27294ee5905d99dd0a26bc0fe5b5353bffd273f31dddad80a526d015c31`
- **Balance:** $100.00

## Структура БД

```sql
-- API ключи
api_keys (id, username, password_hash, api_key, balance, is_active, created_at)

-- Биллинг
billing_log (id, api_key_id, entry_type, amount, service, description, created_at)

-- SSN записи
persons (id, firstname, lastname, middlename, ssn, dob, address, city, st, zip, phone, name_suff)

-- FTS индекс для быстрого поиска
persons_fts (firstname, lastname, city, address)

-- Водительские права
licenses (id, first_name, last_name, dob, address, city, state, zipcode, license_number, license_state)

-- Кредитные отчёты
cr_records (id, ssn, first_name, last_name, dob, address, city, state, zip_code, bureau, credit_score, report_json, raw_text, report_file, created_at)
```

## Производительность

- FTS5 индекс для быстрого полнотекстового поиска
- WAL режим для параллельных чтений
- Batch импорт (5000 записей за раз)

## Troubleshooting

### База данных не найдена

```bash
export LOOKUP_DB_PATH=/full/path/to/lookup.db
python3 -c "import sys; sys.path.insert(0, '.'); from app import init_db; init_db()"
```

### FTS поиск не работает

```bash
python3 importer.py rebuild-fts --db /path/to/lookup.db
```

### Недостаточно баланса

```bash
curl -X POST 'http://localhost:8001/api/admin/add_balance' \
  -H 'X-Admin-Token: changeme-set-LOOKUP_ADMIN_TOKEN' \
  -d '{"username":"test_user","amount":100.0}'
```
