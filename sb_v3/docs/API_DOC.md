# SBBot v3 — API Documentation

**Base URL:** `https://your-domain.com` (или `http://localhost:8081` для локальной разработки)

---

## Quick Start

```bash
# 1. Создайте API ключ в Telegram бот
/apikey create

# 2. Используйте ключ
curl -X GET "https://your-domain/v1/limits" \
  -H "X-API-Key: sk_your_key_here"
```

---

## Authentication

Все endpoints (кроме `/health`) требуют заголовок `X-API-Key`:

```
X-API-Key: sk_your_api_key_here
```

Ключ создаётся командой `/apikey create` в Telegram бот.

---

## Endpoints

### `GET /health`

Liveness check. Не требует авторизации.

```json
{ "status": "ok", "version": "3.0" }
```

---

### `GET /v1/prices`

Прайс-лист всех поисковых типов.

```json
{
  "prices": {
    "phone": 3.00,
    "address": 1.20,
    "background": 3.50,
    "phone_identify": 1.00,
    "phone_verify": 1.00,
    "address_verify": 0.80,
    "email_verify": 0.60,
    "emailrep": 0.40,
    "ssn_dob": 1.50,
    "driver_license": 3.00,
    "credit_report": 6.00,
    "credit_score": 4.00
  },
  "note": "Prices are per search. Batch available at /v1/search/batch (up to 20/query)."
}
```

---

### `GET /v1/limits`

Текущие лимиты и использование вашего ключа.

```bash
curl -X GET "https://your-domain/v1/limits" \
  -H "X-API-Key: sk_your_key"
```

```json
{
  "tier": "starter",
  "daily_limit": 100,
  "remaining_today": 87,
  "rate_limit_per_min": 10,
  "total_requests": 1340,
  "searches_today": 13
}
```

---

### `GET /v1/tiers`

Информация о всех тарифных планах.

```bash
curl -X GET "https://your-domain/v1/tiers" \
  -H "X-API-Key: sk_your_key"
```

```json
{
  "starter": {"cost_monthly": 29.99, "daily_limit": 100, "rate_limit_per_min": 10},
  "pro": {"cost_monthly": 99.99, "daily_limit": 500, "rate_limit_per_min": 30},
  "enterprise": {"cost_monthly": 299.99, "daily_limit": 2000, "rate_limit_per_min": 60},
  "unlimited": {"cost_monthly": 999.99, "daily_limit": 999999, "rate_limit_per_min": 300}
}
```

---

### `POST /v1/search`

Выполнить один поиск.

**Запрос:**

```bash
curl -X POST "https://your-domain/v1/search" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk_your_key" \
  -d '{
    "type": "phone",
    "query": "+12025551234",
    "options": {}
  }'
```

**Body schema:**

```json
{
  "type": "phone|address|background|phone_identify|phone_verify|address_verify|email_verify|emailrep|ssn_dob|driver_license|credit_report|credit_score",
  "query": "...",       // используется для phone, emailrep
  "options": {          // дополнительные параметры
    "first_name": "John",
    "last_name": "Doe",
    "state": "CA",
    "address": "123 Main St",
    "city": "Los Angeles",
    "zip": "90001",
    "dob": "01.15.1985",
    "ssn": "123-45-6789",
    "phone": "+12025551234",
    "email": "john@example.com"
  }
}
```

**Ответ:**

```json
{
  "ok": true,
  "type": "phone",
  "price": 3.00,
  "data": {
    "ok": true,
    "type": "phone",
    "query": {"phone": "+12025551234"},
    "people": [...],
    "parsed": {...},
    "error": "",
    "tokens_cost": 0,
    "account": "enformion-1@email.com"
  }
}
```

---

## Search Types & Validation

### `phone` — Phone Reverse Lookup
**Цена:** $3.00 | **API:** Enformion

```json
{
  "type": "phone",
  "query": "+12025551234"
}
```

**Валидация:**
- Телефон: E.164 формат или любой формат с цифрами (7-15 цифр)
- `"+1XXXXXXXXXX"` — международный
- `"1-800-xxx-xxxx"` — US формат
- `"8XXXXXXXXXX"` — российский
- Если менее 7 или более 15 цифр → `400 Bad Request`

**Пример ответа:**
```json
{
  "ok": true,
  "type": "phone",
  "price": 3.00,
  "data": {
    "ok": true,
    "people": [
      {
        "name": "John Doe",
        "phone": "+12025551234",
        "address": "123 Main St, Los Angeles, CA 90001",
        "carrier": "AT&T",
        "line_type": "Mobile"
      }
    ]
  }
}
```

---

### `address` — Person Search by Name
**Цена:** $1.20 | **API:** Enformion

```json
{
  "type": "address",
  "query": "",
  "options": {
    "first_name": "John",
    "last_name": "Doe",
    "state": "CA"
  }
}
```

**Валидация:**
- `first_name`: 2-50 символов, только буквы и пробелы
- `last_name`: 2-50 символов, только буквы, дефис, апостроф
- `state`: 2 буквы (US state code) или пусто

---

### `background` — Full Background Check
**Цена:** $3.50 | **API:** Enformion

```json
{
  "type": "background",
  "query": "John Doe",
  "options": {
    "first_name": "John",
    "last_name": "Doe",
    "state": "CA"
  }
}
```

**Валидация:** Аналогично `address`

---

### `phone_identify` — Phone Type/Carrier Identification
**Цена:** $1.00 | **API:** Enformion

```json
{
  "type": "phone_identify",
  "query": "+12025551234"
}
```

**Валидация:** Телефон 7-15 цифр

---

### `phone_verify` — Phone Active/Inactive Verification
**Цена:** $1.00 | **API:** Enformion

```json
{
  "type": "phone_verify",
  "query": "+12025551234"
}
```

**Валидация:** Телефон 7-15 цифр

---

### `address_verify` — Address Validation
**Цена:** $0.80 | **API:** Enformion

```json
{
  "type": "address_verify",
  "query": "",
  "options": {
    "first_name": "John",
    "last_name": "Doe",
    "state": "CA",
    "address": "123 Main St"
  }
}
```

**Валидация:**
- Адрес: 5-200 символов
- Имя/фамилия: обязательно

---

### `email_verify` — Email Verification
**Цена:** $0.60 | **API:** Enformion

```json
{
  "type": "email_verify",
  "query": "",
  "options": {
    "email": "user@example.com"
  }
}
```

**Валидация:**
- Email: RFC 5321 формат
- Домен должен существовать

---

### `emailrep` — Email Reputation
**Цена:** $0.40 | **API:** EmailRep.io

```json
{
  "type": "emailrep",
  "query": "user@example.com"
}
```

**Валидация:**
- Email: RFC 5321 формат

**Пример ответа:**
```json
{
  "ok": true,
  "type": "emailrep",
  "price": 0.40,
  "data": {
    "email": "user@example.com",
    "reputation": "high",
    "suspicious": false,
    "recent_abuse": false,
    "domain_age": "10 years",
    "tags": ["valid_format", "disposable"]
  }
}
```

---

### `ssn_dob` — SSN/DOB Lookup
**Цена:** $1.50 | **API:** Usfull.pro

```json
{
  "type": "ssn_dob",
  "query": "",
  "options": {
    "first_name": "John",
    "last_name": "Doe",
    "dob": "01.15.1985",
    "city": "Los Angeles",
    "state": "CA",
    "zip": "90001",
    "ssn": "123-45-6789"
  }
}
```

**Валидация:**
- `first_name`: 2-50 букв, латиница
- `last_name`: 2-50 букв, латиница
- `dob`: форматы `MM.DD.YYYY`, `DD.MM.YYYY`, `YYYY-MM-DD`, `MM/DD/YYYY`, `YYYY/MM/DD`
- `ssn`: формат `XXX-XX-XXXX` (9 цифр) или последние 4 цифры
- `state`: 2 буквы или пусто

**Пример ответа:**
```json
{
  "ok": true,
  "type": "ssn_dob",
  "price": 1.50,
  "data": {
    "ok": true,
    "results": [
      {
        "name": "John Doe",
        "ssn": "***-**-6789",
        "dob": "01/15/1985",
        "address": "123 Main St",
        "phone": "+12025551234"
      }
    ]
  }
}
```

---

### `driver_license` — Driver License Lookup
**Цена:** $3.00 | **API:** Usfull.pro

```json
{
  "type": "driver_license",
  "query": "",
  "options": {
    "first_name": "John",
    "last_name": "Doe",
    "state": "CA",
    "address": "123 Main St",
    "city": "Los Angeles",
    "zip": "90001",
    "dob": "01.15.1985"
  }
}
```

**Валидация:**
- `first_name`, `last_name`: 2-50 букв
- `state`: 2 буквы (US state code)
- `dob`: любой из форматов даты
- Требуется либо `address` + `city` + `zip`, либо только `state`

---

### `credit_report` — Credit Report
**Цена:** $6.00 | **API:** Usfull.pro

```json
{
  "type": "credit_report",
  "query": "",
  "options": {
    "first_name": "John",
    "last_name": "Doe",
    "state": "CA",
    "address": "123 Main St",
    "city": "Los Angeles",
    "zip": "90001",
    "dob": "01.15.1985",
    "ssn": "123-45-6789"
  }
}
```

**Валидация:**
- Требуется: `first_name`, `last_name`, `state`, `dob`, `ssn`
- `ssn`: формат `XXX-XX-XXXX`

---

### `credit_score` — Credit Score
**Цена:** $4.00 | **API:** Usfull.pro

```json
{
  "type": "credit_score",
  "query": "",
  "options": {
    "first_name": "John",
    "last_name": "Doe",
    "state": "CA",
    "address": "123 Main St",
    "city": "Los Angeles",
    "zip": "90001",
    "dob": "01.15.1985",
    "ssn": "123-45-6789"
  }
}
```

**Валидация:** Аналогично `credit_report`

---

## Batch Search

### `POST /v1/search/batch`

Батч-поиск до 20 запросов за один вызов.

```bash
curl -X POST "https://your-domain/v1/search/batch" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk_your_key" \
  -d '{
    "type": "phone",
    "queries": ["+12025551234", "+12025551111", "+12025552222"]
  }'
```

**Body:**
```json
{
  "type": "phone|ssn_dob|address|background|emailrep",
  "queries": ["...", "...", ...]  // 1-20 элементов
}
```

**Ответ:**
```json
{
  "type": "phone",
  "price_per_query": 3.00,
  "total_price": 9.00,
  "count": 3,
  "results": [
    { "ok": true, "data": {...} },
    { "ok": true, "data": {...} },
    { "ok": true, "data": {...} }
  ]
}
```

---

## Rate Limits & Errors

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | OK |
| 400 | Bad Request — невалидные параметры |
| 401 | Unauthorized — неверный или отсутствующий API ключ |
| 403 | Forbidden — ключ не авторизован для этого действия |
| 429 | Rate limit exceeded — превышен лимит |
| 503 | Service Unavailable — API провайдер не настроен |

### Rate Limit Response (429)

```json
{
  "detail": "Rate limit exceeded — try again in 60 seconds"
}
```

### Daily Limit Response (429)

```json
{
  "detail": "Daily limit exceeded. Remaining: 0"
}
```

### Validation Error (400)

```json
{
  "detail": "Invalid phone number: must contain 7-15 digits. Got: '123'"
}
```

---

## Python SDK Example

```python
import requests

API_KEY = "sk_your_key_here"
BASE = "https://your-domain.com"

headers = {"X-API-Key": API_KEY}

# Получить лимиты
limits = requests.get(f"{BASE}/v1/limits", headers=headers).json()
print(f"Осталось: {limits['remaining_today']}/{limits['daily_limit']}")

# Поиск телефона
result = requests.post(
    f"{BASE}/v1/search",
    headers=headers,
    json={"type": "phone", "query": "+12025551234"}
).json()

print(f"Найдено {len(result['data'].get('people', []))} записей")
```

---

## Node.js SDK Example

```javascript
const API_KEY = "sk_your_key_here";
const BASE = "https://your-domain.com";

const headers = { "X-API-Key": API_KEY };

// Поиск
const result = await fetch(`${BASE}/v1/search`, {
  method: "POST",
  headers: { ...headers, "Content-Type": "application/json" },
  body: JSON.stringify({ type: "phone", query: "+12025551234" })
}).then(r => r.json());

console.log(result);
```

---

## Pricing Summary

| Type | Price | API Cost | Margin |
|------|------:|--------:|-------:|
| phone | $3.00 | $2.00 | 33% |
| address | $1.20 | $0.50 | 58% |
| background | $3.50 | $2.00 | 43% |
| phone_identify | $1.00 | $0.50 | 50% |
| phone_verify | $1.00 | $0.50 | 50% |
| address_verify | $0.80 | $0.50 | 37% |
| email_verify | $0.60 | $0.30 | 50% |
| emailrep | $0.40 | $0.00 | 100% |
| ssn_dob | $1.50 | $0.40 | 73% |
| driver_license | $3.00 | $1.00 | 67% |
| credit_report | $6.00 | $2.50 | 58% |
| credit_score | $4.00 | $0.00 | 100% |

---

## Changelog

- **v3.0** — Initial release with 12 search types, API key auth, rate limiting, 4 subscription tiers