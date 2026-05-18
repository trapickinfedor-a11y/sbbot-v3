# API Reference — Complete Request/Response Examples

**Project:** SBBot v3 (LOOK)
**APIs:** usfull.pro, Enformion, self-hosted Lookup API
**Updated:** 2026-05-17

---

## 1. USFULL.PRO API

**Base URL:** `https://usfull.pro`
**Auth:** `X-API-KEY` header
**User-Agent:** `SBBot/2.0`
**Content-Type:** `application/json`

---

### POST /api/search/ — SSN/DOB Search

**Cost:** $0.40 success / $0.01 no result

**Headers:**
```
X-API-KEY: <api_key>
Content-Type: application/json
User-Agent: SBBot/2.0
```

**Request (name search):**
```json
{
  "firstname": "JOHN",
  "lastname": "SMITH",
  "dob": "19850115",
  "city": "LOS ANGELES",
  "st": "CA",
  "zip": "90210",
  "phone": 2125551234
}
```

**Request (direct SSN search):**
```json
{
  "firstname": "",
  "lastname": "",
  "ssn": 123456789
}
```

**DOB format:** YYYYMMDD, YYYY, MM/DD/YYYY, or YYYY-MM-DD (normalized automatically)
**Fields:** firstname/lastname = UPPERCASE required. Optional: dob, city, st, zip, phone, ssn.

**Success Response (200):**
```json
{
  "ok": true,
  "results": [
    {
      "firstname": "JOHN",
      "middlename": "M",
      "lastname": "SMITH",
      "name_suff": "JR",
      "ssn": "123456789",
      "dob": "19850115",
      "address": "123 MAIN ST",
      "city": "LOS ANGELES",
      "st": "CA",
      "zip": "90210",
      "phone": "2125551234"
    }
  ],
  "count": 1,
  "account": "username"
}
```

**Error Responses:**
- 403: `{"ok": false, "error": "Account blocked or invalid API key", "results": []}`
- 402: `{"ok": false, "error": "Insufficient balance", "results": []}`
- other: `{"ok": false, "error": "<message>", "results": []}`

**Curl:**
```bash
curl -X POST 'https://usfull.pro/api/search/' \
  -H 'X-API-KEY: your_api_key' \
  -H 'Content-Type: application/json' \
  -H 'User-Agent: SBBot/2.0' \
  -d '{"firstname":"JOHN","lastname":"SMITH","st":"CA","zip":"90210"}'
```

---

### POST /api/dl/ — Driver License Search

**Cost:** $1.00 success

**Headers:**
```
X-API-KEY: <api_key>
Content-Type: application/json
User-Agent: SBBot/2.0
```

**Request:**
```json
{
  "first_name": "JOHN",
  "last_name": "DOE",
  "address": "123 MAIN ST",
  "zipcode": "12345",
  "dob": "01/15/1985"
}
```

**Success Response (200):**
```json
{
  "ok": true,
  "license_number": "D12345678",
  "license_state": "NY",
  "balance_deducted": 1.0,
  "remaining_balance": 99.0,
  "account": "username"
}
```

**Error Responses:**
- 401: `{"ok": false, "error": "Invalid API key"}`
- 402: `{"ok": false, "error": "Insufficient balance"}`
- other: `{"ok": false, "error": "<message>"}`

**Curl:**
```bash
curl -X POST 'https://usfull.pro/api/dl/' \
  -H 'X-API-KEY: your_api_key' \
  -H 'Content-Type: application/json' \
  -d '{"first_name":"JOHN","last_name":"DOE","zipcode":"12345","dob":"01/15/1985"}'
```

---

### POST /api/cr/ — Credit Report Search

**Cost:** $2.50 success

**Headers:**
```
X-API-KEY: <api_key>
Content-Type: application/json
User-Agent: SBBot/2.0
```

**Request:**
```json
{
  "first_name": "JOHN",
  "last_name": "DOE",
  "street_address": "123 MAIN ST",
  "city": "LOS ANGELES",
  "state": "CA",
  "zip_code": "90210",
  "dob": "01/15/1985",
  "ssn": "123456789"
}
```

**Success Response (200):**
```json
{
  "ok": true,
  "data": {
    "credit_score": 720,
    "open_accounts": 6,
    "closed_accounts": 4,
    "total_debt": "$15420",
    "inquiries": 2,
    "derogatory_marks": 0,
    "oldest_account": "2018-03",
    "payment_history": "Good",
    "account_types": ["credit_card", "mortgage", "auto_loan"]
  },
  "account": "username"
}
```

**Error Responses:**
- 402: `{"ok": false, "error": "Insufficient balance"}`
- other: `{"ok": false, "error": "<message>"}`

**Curl:**
```bash
curl -X POST 'https://usfull.pro/api/cr/' \
  -H 'X-API-KEY: your_api_key' \
  -H 'Content-Type: application/json' \
  -d '{"ssn":"123456789","bureau":"transunion"}'
```

---

### POST /api/credit-score/ — Credit Score Search

**Cost:** $2.00 success

**Request:**
```json
{
  "first_name": "JOHN",
  "last_name": "DOE",
  "street_address": "123 MAIN ST",
  "city": "LOS ANGELES",
  "state": "CA",
  "zip_code": "90210",
  "dob": "01/15/1985",
  "ssn": "123456789"
}
```

**Success Response (200):**
```json
{
  "ok": true,
  "data": {
    "credit_score": 720,
    "score_range": "Good",
    "factors": ["Payment history", "Credit utilization"],
    "percentile": 68
  },
  "account": "username"
}
```

---

### GET /api/get_balance/ — Balance Check

**Headers:**
```
X-API-KEY: <api_key>
User-Agent: SBBot/2.0
```

**Success Response (200):**
```json
{
  "_http_status": 200,
  "balance": 150.50
}
```

**Timeout Response:**
```json
{
  "_http_status": 0,
  "status": "error",
  "message": "Timeout"
}
```

**Curl:**
```bash
curl -X GET 'https://usfull.pro/api/get_balance/' \
  -H 'X-API-KEY: your_api_key'
```

---

### POST /api/create_token/ — Create Account

**Request:**
```json
{
  "username": "user@example.com",
  "password": "password123"
}
```

**Success Response (200):**
```json
{
  "token": "your_api_key_here"
}
```
Also returns `api_key` or `key` field.

---

## 2. ENFORMION API

**Base URL:** `https://devapi.enformion.com`
**Auth:** Galaxy headers (NOT Basic auth)
**User-Agent:** `SBBot/3.0`

### Headers (all requests):
```
Content-Type: application/json
galaxy-ap-name: <email>
galaxy-ap-password: <password>
galaxy-search-type: <mapped_type>
User-Agent: SBBot/3.0
```

### Search type → galaxy-search-type mapping:
| bot key | galaxy-search-type |
|---------|------------------|
| `phone`, `ph_lookup`, `ph_batch`, `batch_phones` | `ReversePhone` |
| `phone_identify` | `PhoneIdentify` |
| `phone_verify` | `PhoneVerify` |
| all others | `Person` |

---

### POST /ReversePhoneSearch — Reverse Phone

**Request:**
```json
{
  "Phone": "2125551234"
}
```

**Success Response (200):**
```json
{
  "reversePhoneRecords": [
    {
      "Id": "123456",
      "FirstName": "JOHN",
      "LastName": "DOE",
      "Address": "123 MAIN ST, NEW YORK, NY 10001",
      "PhoneNumber": "2125551234",
      "Carrier": "AT&T",
      "LineType": "Landline"
    }
  ]
}
```

**Curl:**
```bash
curl -X POST 'https://devapi.enformion.com/ReversePhoneSearch' \
  -H 'Content-Type: application/json' \
  -H 'galaxy-ap-name: your_email' \
  -H 'galaxy-ap-password: your_password' \
  -H 'galaxy-search-type: ReversePhone' \
  -d '{"Phone":"2125551234"}'
```

---

### POST /PersonSearch — Person Search

**Request:**
```json
{
  "FirstName": "JOHN",
  "LastName": "DOE",
  "State": "CA"
}
```

**Success Response (200):**
```json
{
  "persons": [
    {
      "Id": "789456",
      "FirstName": "JOHN",
      "MiddleName": "M",
      "LastName": "DOE",
      "Age": 38,
      "Address": "123 MAIN ST",
      "City": "LOS ANGELES",
      "State": "CA",
      "Zip": "90210",
      "Phones": ["2125551234"],
      "Emails": ["john@example.com"]
    }
  ]
}
```

---

### POST /EmailSearch — Email Lookup

**Request:**
```json
{
  "Email": "john@example.com"
}
```

**Success Response (200):**
```json
{
  "emailRecords": [
    {
      "email": "john@example.com",
      "firstName": "JOHN",
      "lastName": "DOE",
      "registrar": "gmail.com",
      "dateCreated": "2020-01-15"
    }
  ]
}
```

---

### POST /AddressSearch — Address Lookup

**Request:**
```json
{
  "StreetAddress": "123 MAIN ST",
  "City": "LOS ANGELES",
  "State": "CA",
  "ZipCode": "90210"
}
```

**Success Response (200):**
```json
{
  "addressRecords": [
    {
      "streetAddress": "123 MAIN ST",
      "city": "LOS ANGELES",
      "state": "CA",
      "zipCode": "90210",
      "currentResidents": [
        {
          "name": "JOHN DOE",
          "age": 38,
          "phones": ["2125551234"],
          "relocationRisk": "Low"
        }
      ]
    }
  ]
}
```

---

## 3. Self-Hosted Lookup API

**Base URL:** `http://localhost:8001/api/` (or `http://lookup_api:8082` in Docker)
**Auth:** `X-API-KEY` header or `X-Admin-Token` for admin endpoints

---

### POST /api/create_token/

**Request:**
```json
{
  "username": "developer_app",
  "password": "secure_password_123"
}
```

**Response:**
```json
{
  "status": "ok",
  "api_key": "4ae7e27294ee5905d99dd0a26bc0fe5b5353bffd273f31dddad80a526d015c31",
  "balance": 100.0,
  "message": "Account created"
}
```

**Curl:**
```bash
curl -X POST 'http://localhost:8001/api/create_token/' \
  -H 'Content-Type: application/json' \
  -d '{"username":"your_username","password":"your_password"}'
```

---

### GET /api/get_balance/

**Request:**
```
GET /api/get_balance/
X-API-KEY: your_api_key
```

**Response:**
```json
{
  "status": "ok",
  "balance": 98.80
}
```

---

### POST /api/search/ — SSN Lookup

**Request:**
```json
{
  "firstname": "THOMAS",
  "lastname": "DICKSON",
  "middlename": "B",
  "city": "PITTSBURGH",
  "st": "PA",
  "zip": "15211"
}
```

**Response:**
```json
{
  "status": "ok",
  "count": 1,
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

**Curl:**
```bash
curl -X POST 'http://localhost:8001/api/search/' \
  -H 'Content-Type: application/json' \
  -H 'X-API-KEY: your_api_key' \
  -d '{"firstname":"THOMAS","lastname":"DICKSON","st":"PA","zip":"15211"}'
```

---

### POST /api/dl/ — Driver License Lookup

**Request:**
```json
{
  "first_name": "JOHN",
  "last_name": "DOE",
  "address": "123 MAIN ST",
  "zipcode": "12345",
  "dob": "19900115"
}
```

**Response:**
```json
{
  "status": "ok",
  "count": 1,
  "results": [
    {
      "license_number": "D12345678",
      "license_state": "NY"
    }
  ]
}
```

---

### POST /api/cr/ — Credit Report Lookup

**Request:**
```json
{
  "ssn": "123456789",
  "first_name": "JOHN",
  "last_name": "DOE",
  "dob": "19900115",
  "bureau": "transunion"
}
```

**bureau values:** `transunion`, `experian`, `equifax`, `lexisnexis`, `wallet`, `any`

**Response:**
```json
{
  "status": "ok",
  "count": 1,
  "results": [
    {
      "id": 1,
      "ssn": "123456789",
      "first_name": "JOHN",
      "last_name": "DOE",
      "dob": "19900115",
      "address": "123 MAIN ST, NEW YORK, NY",
      "city": "NEW YORK",
      "state": "NY",
      "zip_code": "10001",
      "bureau": "transunion",
      "credit_score": 720,
      "report_json": {
        "open_accounts": 6,
        "closed_accounts": 4,
        "total_debt": "$15420",
        "inquiries": 2
      },
      "report_file": "/app/data/cr_pdfs/cr_1.pdf",
      "has_pdf": true
    }
  ]
}
```

---

### GET /health

**Response:**
```json
{
  "status": "ok",
  "version": "1.0.0"
}
```

---

### Admin Endpoints

**POST /api/admin/add_balance**
```bash
curl -X POST 'http://localhost:8001/api/admin/add_balance' \
  -H 'X-Admin-Token: your_admin_token' \
  -H 'Content-Type: application/json' \
  -d '{"username":"bot_user","amount":500.0,"note":"Monthly top-up"}'
```

**GET /api/admin/users**
```bash
curl -X GET 'http://localhost:8001/api/admin/users' \
  -H 'X-Admin-Token: your_admin_token'
```

**GET /api/admin/stats**
```bash
curl -X GET 'http://localhost:8001/api/admin/stats' \
  -H 'X-Admin-Token: your_admin_token'
```

**Response:**
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

---

## 4. CRYPTOBOT API (Payments)

**Base URL:** `https://pay.crypt.bot/` (or configurable)
**Auth:** `X-API-KEY` header

### Create Invoice
**POST /api/createInvoice**

```json
{
  "amount": 10.0,
  "currency": "USD",
  "order_id": "order_12345",
  "description": "Balance top-up"
}
```

**Response:**
```json
{
  "ok": true,
  "result": {
    "invoice_id": "INV_ABC123",
    "pay_url": "https://pay.crypt.bot/i/INV_ABC123",
    "amount": 10.0,
    "currency": "USD"
  }
}
```

---

## 5. HELEKET API (Payments)

**Base URL:** `https://pay.helekit.com/api/`
**Auth:** Bearer token

### Create Payment
**POST /invoice/create**

```json
{
  "amount": 10.00,
  "currency": "USDT",
  "order_id": "order_12345"
}
```

---

## 6. BTCPAYSERVER API (Payments)

**Base URL:** configured via `BTCPAY_HOST` + `BTCPAY_API_KEY`
**Auth:** Authorization header with Bearer token

### Create Invoice
**POST /api/v1/invoices**

```json
{
  "amount": 10.00,
  "currency": "USD",
  "metadata": {
    "order_id": "order_12345"
  }
}
```

---

## 7. EMAILREP.IO API

**Base_url:** `https://emailrep.io/`
**Auth:** `X-API-KEY` header (optional, 100/day free without key)

### Email Reputation
**GET /john@example.com**

**Response:**
```json
{
  "email": "john@example.com",
  "reputation": "medium",
  "suspicious": false,
  "details": {
    "domain_exists": true,
    "domain_age": "2010-05-01",
    "accept_all": false,
    "free_provider": false,
    "disposable": false,
    "deliverable": true
  }
}
```

---

## 8. SBBot v3 Internal REST API (api.py)

**Base URL:** `http://localhost:3111/api/v1`
**Auth:** Bearer token (API key)

### POST /api/v1/requests/single
```json
{
  "requestMode": "single",
  "payload": {
    "firstName": "John",
    "lastName": "Doe",
    "ssn": "123456789",
    "creditScore": 720
  },
  "proxy": {
    "policy": "rotating-us"
  }
}
```

### GET /api/v1/jobs/:publicId
### GET /api/v1/usage/summary

---

## Pricing Reference

| Service | Success | No Result |
|---------|---------|-----------|
| SSN/DOB Search | $0.40 | $0.01 |
| Driver License | $1.00 | $0.00 |
| Credit Report | $2.50 | $0.01 |
| Credit Score | $2.00 | — |
| Reverse Phone (Enformion) | $0.50 | — |
| Person Search (Enformion) | $0.30 | — |
| Email Lookup (Enformion) | $0.20 | — |
| Address Lookup (Enformion) | $0.30 | — |
