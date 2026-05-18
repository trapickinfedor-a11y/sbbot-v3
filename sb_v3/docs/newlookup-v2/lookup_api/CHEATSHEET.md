# Lookup API — Шпаргалка

## Быстрые команды

### Запуск API (локально)
```bash
cd lookup_api
./start_lookup_api.sh
```

### Управление ключами
```bash
# Список ключей
LOOKUP_DB_PATH=../data/lookup.db python3 manage_keys.py list

# Создать ключ
LOOKUP_DB_PATH=../data/lookup.db python3 manage_keys.py create username password --balance 1000

# Баланс
LOOKUP_DB_PATH=../data/lookup.db python3 manage_keys.py balance username

# Пополнить
LOOKUP_DB_PATH=../data/lookup.db python3 manage_keys.py add-balance username 500
```

### Импорт данных
```bash
# SSN records
python3 importer.py persons data.csv --db ../data/lookup.db

# Driver Licenses
python3 importer.py licenses data.csv --db ../data/lookup.db

# Credit Reports
python3 importer.py credit-reports data.csv --db ../data/lookup.db

# Rebuild FTS
python3 importer.py rebuild-fts --db ../data/lookup.db
```

### API запросы
```bash
# Баланс
curl -X GET 'http://localhost:8001/api/get_balance/' \
  -H 'X-API-KEY: your_key'

# SSN поиск
curl -X POST 'http://localhost:8001/api/search/' \
  -H 'X-API-KEY: your_key' \
  -H 'Content-Type: application/json' \
  -d '{"firstname":"JOHN","lastname":"DOE","st":"NY"}'

# DL поиск
curl -X POST 'http://localhost:8001/api/dl/' \
  -H 'X-API-KEY: your_key' \
  -H 'Content-Type: application/json' \
  -d '{"first_name":"JOHN","last_name":"DOE","zipcode":"10001","dob":"19900115"}'

# Health check
curl http://localhost:8001/health
```

### Docker команды
```bash
# Запустить
docker compose up lookup_api -d

# Логи
docker logs -f newlookup_lookup_api

# Войти в контейнер
docker exec -it newlookup_lookup_api bash

# Импорт в контейнере
docker cp data.csv newlookup_lookup_api:/tmp/
docker exec newlookup_lookup_api python3 importer.py persons /tmp/data.csv --db /app/data/lookup.db

# Перезапустить
docker restart newlookup_lookup_api
```

## Тестовый аккаунт

```
Username: test_user
Password: test_password_123
API Key:  4ae7e27294ee5905d99dd0a26bc0fe5b5353bffd273f31dddad80a526d015c31
Balance:  $98.80
```

## Интеграция с ботом

### .env
```bash
LOOKUP_API_BASE_URL=http://lookup_api:8082  # Docker
# или
LOOKUP_API_BASE_URL=http://localhost:8001   # Локально
```

### SQL (сохранить ключ в БД ботов)
```sql
INSERT INTO api_keys (key_name, key_value, key_type, is_active)
VALUES ('lookup_api', 'your_api_key_here', 'lookup', true);
```

## Форматы CSV

### persons.csv
```csv
firstname,lastname,middlename,ssn,dob,address,city,st,zip,phone,name_suff
JOHN,DOE,M,123456789,19900115,123 MAIN ST,NEW YORK,NY,10001,2125551234,
```

### licenses.csv
```csv
first_name,last_name,dob,address,city,state,zipcode,license_number,license_state
JOHN,DOE,19900115,123 MAIN ST,NEW YORK,NY,10001,D12345678,NY
```

### credit_reports.csv
```csv
ssn,first_name,last_name,dob,address,city,state,zip_code,bureau,credit_score,report_json,raw_text
123456789,JOHN,DOE,19900115,123 MAIN ST,NEW YORK,NY,10001,transunion,720,{},
```

## Endpoints

| Метод | Endpoint | Описание |
|-------|----------|----------|
| POST | `/api/create_token/` | Создать API ключ |
| GET | `/api/get_balance/` | Проверить баланс |
| POST | `/api/search/` | SSN/DOB поиск |
| POST | `/api/dl/` | Driver License поиск |
| POST | `/api/cr/` | Credit Report поиск |
| GET | `/api/cr/download/{id}` | Скачать CR PDF |
| GET | `/health` | Health check |
| POST | `/api/admin/add_balance` | Пополнить баланс (admin) |
| GET | `/api/admin/users` | Список пользователей (admin) |
| GET | `/api/admin/stats` | Статистика (admin) |
| POST | `/api/admin/import_csv` | Импорт CSV (admin) |

## Цены (по умолчанию)

| Операция | Найдено | Не найдено |
|----------|---------|------------|
| SSN | $0.40 | $0.01 |
| DL | $1.00 | $0.00 |
| CR | $0.40 | $0.01 |

## Troubleshooting

| Проблема | Решение |
|----------|---------|
| 401 Unauthorized | Проверить API ключ |
| 402 Insufficient Balance | Пополнить баланс через `manage_keys.py add-balance` |
| 404 Not Found | Проверить endpoint URL |
| База заблокирована | `sqlite3 lookup.db "PRAGMA wal_checkpoint(TRUNCATE);"` |
| FTS не работает | `python3 importer.py rebuild-fts --db lookup.db` |
| Медленные запросы | `sqlite3 lookup.db "VACUUM; ANALYZE;"` |

## Файлы

```
lookup_api/
├── app.py                    # API сервер
├── importer.py              # Импорт данных
├── manage_keys.py           # Управление ключами
├── start_lookup_api.sh      # Скрипт запуска
├── README.md                # Краткая документация
├── SETUP_GUIDE.md           # Полное руководство
├── INTEGRATION_GUIDE.md     # Интеграция с ботами
├── STATUS.md                # Текущий статус
├── CHEATSHEET.md            # Эта шпаргалка
└── .env.example             # Пример конфигурации
```

## Полезные ссылки

- Полная документация: `SETUP_GUIDE.md`
- Интеграция с ботами: `INTEGRATION_GUIDE.md`
- Текущий статус: `STATUS.md`
- Быстрый старт: `README.md`
