# Запросы «full info»: SSN + DL + CR

Официальная документация провайдера: **[USFULL API — service/docs](https://usfull.info/service/docs/)**.  
В примерах там же обычно указан хост **`https://usfull.pro`** (не путать с сайтом `.info`).

Отдельного метода **`/fullinfo` нет**: цепочка из трёх вызовов:

| Шаг | Метод | Назначение |
|-----|--------|------------|
| 1 | `POST /api/search/` | SSN / DOB |
| 2 | `POST /api/dl/` | Driver License |
| 3 | `POST /api/cr/` | Credit Report |

Тарифы и лимиты — в [документации](https://usfull.info/service/docs/) (в т.ч. отдельно **Credit Score**: `POST /api/credit-score/`).

### Имя и middle name

- В **`firstname`** передавайте **только имя** (например `Thomas`, `Kyle`, `Sean`, `Stephen`).
- **Middle** — в отдельное поле **`middlename`** (инициал `C` или полное `Darwin` и т.д.).
- Так делает **self-hosted `lookup_api`** (поле добавлено в API). У **USFULL** в публичной доке поле может не быть перечислено — его можно всё равно отправить (часто лишние поля игнорируются) или оставить только `firstname`/`lastname`, если провайдер отвечает ошибкой.

---

## USFULL (production): логин, пароль и API key

**Логин и пароль от аккаунта USFULL** в API используются так, как в документации:

- Для **`/api/search/`** и **`/api/get_balance/`**: помимо заголовка **`X-API-KEY`** с токеном нужна **HTTP Basic Authentication** (`-u "логин:пароль"` в curl).
- Для **`/api/dl/`** и **`/api/cr/`** в доках указан заголовок **`X-API-Key`** (другой регистр) + тот же API key. Basic Auth в примерах для DL/CR не фигурирует — ориентируйтесь на актуальный текст [service/docs](https://usfull.info/service/docs/).

**Важно:** не передавайте чужой аккаунт — в правилах USFULL это может привести к блокировке.

Общий шаблон для **production**:

```bash
export BASE="https://usfull.pro"
export KEY="ВАШ_API_KEY_ИЗ_ЛК"
export USFULL_USER="ваш_логин"
export USFULL_PASS="ваш_пароль"
```

---

## Отличия: USFULL vs self-hosted `lookup_api`

| | **USFULL** ([docs](https://usfull.info/service/docs/)) | **Self-hosted** (`lookup_api` в репо) |
|---|----------------|--------------------------------------|
| Search | `X-API-KEY` + **Basic Auth** | только `X-API-KEY` |
| Search middle | по доке — `firstname` / `lastname`; опционально **`middlename`** в JSON (если поддерживают) | **`middlename`** отдельно; без него middle во **`firstname`** всё ещё работает (legacy) |
| DL | **`dob` обязателен**; `first_name` до 15 символов (буквы/апостроф) | `dob` можно опустить (своя логика поиска) |
| CR | Поля: `first_name`, `last_name`, **`street_address`**, **`city`**, **`state`**, **`zip_code`**, **`dob`**, **`ssn`** | SQLite: часто достаточно `ssn` + `bureau`; адрес — опционально |
| Ответ CR | `status`, `report_data`, … | `status: ok`, `results[]`, опционально PDF |

Ниже — **два набора примеров** для одних и тех же людей.

---

## Примеры под **USFULL** (`https://usfull.pro`)

Подставьте **`DOB`** в допустимом формате (например `MM/DD/YYYY` или `DD.MM.YYYY` — см. docs).  
**`SSN_DIGITS`** — 9 цифр из ответа `POST /api/search/` → `results[0].ssn`.

### 1) Kyle K Linseman — 1070 Ocean Blvd, Hampton, NH 03842

**Search** (Basic + key; middle отдельно):

```bash
curl -sS -X POST "$BASE/api/search/" \
  -H "X-API-KEY: $KEY" \
  -H "Content-Type: application/json" \
  -H "User-Agent: MyApp/1.0" \
  -u "$USFULL_USER:$USFULL_PASS" \
  -d '{
    "firstname": "Kyle",
    "middlename": "K",
    "lastname": "Linseman",
    "city": "Hampton",
    "st": "NH",
    "zip": "03842"
  }'
```

**DL** (`dob` обязателен по документации):

```bash
curl -sS -X POST "$BASE/api/dl/" \
  -H "X-API-Key: $KEY" \
  -H "Content-Type: application/json" \
  -H "User-Agent: MyApp/1.0" \
  -d '{
    "first_name": "Kyle",
    "last_name": "Linseman",
    "address": "1070 Ocean Blvd",
    "zipcode": "03842",
    "dob": "REPLACE_DOB"
  }'
```

**CR** (полный адрес + `dob` + `ssn`, как в [доке Credit Report](https://usfull.info/service/docs/)):

```bash
curl -sS -X POST "$BASE/api/cr/" \
  -H "X-API-Key: $KEY" \
  -H "Content-Type: application/json" \
  -H "User-Agent: MyApp/1.0" \
  -d '{
    "first_name": "Kyle",
    "last_name": "Linseman",
    "street_address": "1070 Ocean Blvd",
    "city": "Hampton",
    "state": "NH",
    "zip_code": "03842",
    "dob": "REPLACE_DOB",
    "ssn": "SSN_DIGITS"
  }'
```

### 2) Sean R Piwowar — Fairfax, VA

```bash
# search
curl -sS -X POST "$BASE/api/search/" \
  -H "X-API-KEY: $KEY" -H "Content-Type: application/json" -H "User-Agent: MyApp/1.0" \
  -u "$USFULL_USER:$USFULL_PASS" \
  -d '{"firstname":"Sean","middlename":"R","lastname":"Piwowar","city":"Fairfax","st":"VA","zip":"22032"}'

# dl
curl -sS -X POST "$BASE/api/dl/" \
  -H "X-API-Key: $KEY" -H "Content-Type: application/json" -H "User-Agent: MyApp/1.0" \
  -d '{"first_name":"Sean","last_name":"Piwowar","address":"5552 Ann Peake Dr","zipcode":"22032","dob":"REPLACE_DOB"}'

# cr
curl -sS -X POST "$BASE/api/cr/" \
  -H "X-API-Key: $KEY" -H "Content-Type: application/json" -H "User-Agent: MyApp/1.0" \
  -d '{"first_name":"Sean","last_name":"Piwowar","street_address":"5552 Ann Peake Dr","city":"Fairfax","state":"VA","zip_code":"22032","dob":"REPLACE_DOB","ssn":"SSN_DIGITS"}'
```

### 3) Thomas C Dickson — Philadelphia, PA 19147

Search: `"firstname":"Thomas"`, `"middlename":"C"`, `"lastname":"Dickson"`, `Philadelphia`, `PA`, `19147`; DL/CR с улицей `334 Earp St`.

### 4) Stephen Darwin Rudolph — Philadelphia, PA 19147

Search: `"firstname":"Stephen"`, `"middlename":"Darwin"`, `"lastname":"Rudolph"`; DL/CR: `1224 S American St`, `Philadelphia`, `PA`, `19147`.

---

## Примеры под **self-hosted** `lookup_api`

Только **`X-API-KEY`**, без Basic Auth.

```bash
export BASE="http://127.0.0.1:8082"
export KEY="YOUR_API_KEY"
```

**Search** с middle отдельно:

```bash
curl -sS -X POST "$BASE/api/search/" \
  -H "X-API-KEY: $KEY" -H "Content-Type: application/json" \
  -d '{
    "firstname": "Thomas",
    "middlename": "C",
    "lastname": "Dickson",
    "city": "Philadelphia",
    "st": "PA",
    "zip": "19147"
  }'
```

**CR (self-hosted)** после search:

```bash
curl -sS -X POST "$BASE/api/cr/" \
  -H "X-API-KEY: $KEY" -H "Content-Type: application/json" \
  -d '{"ssn": "SSN_DIGITS", "bureau": "any"}'
```

---

## Автоматизация (скрипт в репо)

```bash
export LOOKUP_API_KEY="YOUR_API_KEY"
export LOOKUP_API_BASE_URL="https://usfull.pro"   # или http://127.0.0.1:8082
export LOOKUP_API_BASIC_AUTH="логин:пароль"
chmod +x scripts/fullinfo_chain.sh
./scripts/fullinfo_chain.sh
```

Формат строк людей в скрипте: `firstname` и **`middlename` раздельно** (см. комментарий в `fullinfo_chain.sh`).

---

## PDF CR (только self-hosted)

```bash
curl -sS -o report.pdf -H "X-API-KEY: $KEY" \
  "$BASE/api/cr/download/RECORD_ID"
```

У USFULL в публичной доке другой формат ответа CR (`report_data` в JSON), отдельного `download` в этом репозитории под их API нет.
