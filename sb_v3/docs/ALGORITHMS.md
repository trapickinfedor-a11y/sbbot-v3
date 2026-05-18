# SBBot v3 — Algorithms & Logic Reference

**Project:** SBBot v3 (LOOK)
**Updated:** 2026-05-17

---

## 1. Search Flow Architecture

```
User input (Telegram)
    │
    ├── /phone  → sb_engine.search("phone", {phone})
    ├── /address → sb_engine.search("address", {first_name, last_name, state})
    ├── /bg      → sb_engine.search("background", {first_name, last_name, state})
    ├── /ssn     → usfull_engine.search_ssn_dob(...)
    ├── /dl      → usfull_engine.search_driver_license(...)
    ├── /cr      → usfull_engine.search_credit_report(...)
    └── /cs      → usfull_engine.search_credit_score(...)

sb_engine = Enformion Pool (https://devapi.enformion.com)
usfull_engine = Usfull.pro Pool (https://usfull.pro)
```

---

## 2. Enformion Engine (`sb_engine.py`)

### 2.1 Account Selection — `_get_account()`

Health-aware round-robin: prefer accounts with highest `health.score()`, rotate within same tier.

```python
usable = [a for a in accounts if a.status in ("active", "low_balance")]
usable.sort(key=lambda a: a.health.score(), reverse=True)
acc = usable[rr_index % len(usable)]
```

**Fallback chain:** usable account → `__global__` synthetic account (if `api_key` set) → `None`

### 2.2 Request Headers

```
Content-Type: application/json
galaxy-ap-name: <email>
galaxy-ap-password: <password>
galaxy-search-type: <mapped_type>
User-Agent: SBBot/3.0
```

Search type → Galaxy header mapping:
| Internal key | galaxy-search-type |
|---|---|
| `phone`, `ph_lookup`, `ph_batch`, `batch_phones` | `ReversePhone` |
| `phone_identify` | `PhoneIdentify` |
| `phone_verify` | `PhoneVerify` |
| all others | `Person` |

### 2.3 Endpoint Dispatch — `_make_request()`

| search_type | endpoint | payload |
|---|---|---|
| `phone`, `ph_lookup` | `ReversePhoneSearch` | `{"Phone": "..."}` |
| `address` | `PersonSearch` | `{"FirstName": fn, "LastName": ln, "State": st}` |
| `background`, `bg_name`, `bg_batch` | `PersonSearch` | `{"FirstName": fn, "LastName": ln, "State": st}` |
| `phone_identify` | `IdentifyPhoneType` | `{"Phone": "..."}` |
| `phone_verify` | `VerifyPhone` | `{"Phone": "..."}` |
| `email`, `em_lookup`, `em_verify` | — | Returns `EMAIL_SEARCH_UNSUPPORTED` |

### 2.4 Retry Logic

- **Max retries:** 3 attempts per account
- **5xx errors:** exponential backoff (1s, 2s, 4s), then try `_get_fresh_account()` to switch
- **401 →** account.status = `"blocked"`, return `BLOCKED` error
- **402 →** account.status = `"no_balance"`, call `_alert_callback()`, return `NO_TOKENS`
- **429 →** sleep 2s, 4s, 8s before retry (rate limit backoff)
- **Timeout →** try `_get_fresh_account()`, retry up to 3x
- **All retries exhausted →** `RETRIES_EXHAUSTED`

### 2.5 Response Parsing — `_parse_response()`

**ReversePhoneSearch:** iterates `data["reversePhoneRecords"][i]["tahoePerson"]`
**PersonSearch:** iterates `data["persons"][i]`

Builds person dict:
```python
{
    "name": "FirstName LastName",
    "first_name": "...",
    "last_name": "...",
    "age": int,
    "date_of_birth": "...",
    "ssn": "...",
    "phone": primary phone str,
    "phones": [{"phone": "", "phoneType": "", "carrier": "", "location": ""}],
    "phone_type": "...",
    "carrier": "...",
    "location": "City, ST",
    "voip": True/False/None,
    "connected_to": "Name",
    "addresses": ["123 Main St, City, ST 90210", "456 Elm St, ..."],
    "address": first address,
    "emails": [...],
    "email": first email,
    "relatives": "Name (Relation), Name (Relation)",
    "akas": ["FirstName Middle LastName"],
}
```

Skips records with no `name` AND no `phone`.

**Deduplication logic** (`_extract_addresses`): uses `addressLine1` as dedupe key across:
- `locations[]`
- `currentAddress`
- `historicalAddresses[]`
- `tahoePerson.addresses[]`

### 2.6 Circuit Breaker

- **failure_threshold:** 10 failures to open
- **recovery_timeout:** 60s → transitions to `half_open`
- **half_open_max:** 3 successful attempts to close
- **failure_rate:** `total_failures / (total_failures + total_successes)` — persists across `reset()`

---

## 3. Usfull.pro Engine (`usfull_engine.py`)

### 3.1 Account Selection — `_get_account()`

Checks `cb.allow_request()` first (circuit breaker). Falls back to `_get_fresh_account()` on failure.
Health-aware round-robin same as Enformion.

### 3.2 Request Headers

```
X-API-KEY: <api_key>
Content-Type: application/json
User-Agent: SBBot/2.0
```

### 3.3 Endpoints

| Method | Endpoint | Required fields | DOB format |
|---|---|---|---|
| `search_ssn_dob` | `POST /api/search/` | firstname, lastname (UPPER), st, zip | YYYYMMDD |
| `search_driver_license` | `POST /api/dl/` | first_name, last_name, address, zipcode, dob | DD.MM.YYYY, MM/DD/YYYY, YYYY-MM-DD, YYYYMMDD |
| `search_credit_report` | `POST /api/cr/` | first_name, last_name, street_address, city, state, zip_code, dob, ssn | — |
| `search_credit_score` | `POST /api/credit-score/` | same as cr | — |
| `get_balance` | `GET /api/get_balance/` | — | — |

### 3.4 Retry

- **5xx →** retry with exponential backoff (up to 3 attempts)
- **402 →** account.status = `"no_balance"`, no retry
- **Other errors →** record failure, return error

### 3.5 Health Score

```python
error_rate = errors / window_len  # MAX_ERROR_WINDOW=20
error_score = (1 - error_rate) * 50
latency_score = max(0, 30 * (1 - min(avg_latency/30, 1)))
ok_bonus = min(10, consecutive_ok * 0.5)
error_penalty = min(10, consecutive_errors)
score = error_score + latency_score + ok_bonus - error_penalty
# Range: 0–100, empty window = 100
```

### 3.6 DOB Normalization

**`_normalize_dob()`** for SSN/DOB search → YYYYMMDD:
- `DD.MM.YYYY` → misinterpreted as MM.DD.YYYY (known bug: `15.01.1985` → `19851501`)
- `MM/DD/YYYY` → `YYYYMMDD` (correct)

**`_normalize_dob_dl()`** for DL → kept as-is (DD.MM.YYYY, MM/DD/YYYY, YYYY-MM-DD, YYYYMMDD all accepted):
- `1/5/1985` → kept as `"1/5/1985"` (matches `\d{1,2}/\d{1,2}/\d{4}` pattern, no conversion)

### 3.7 Cache

1-hour TTL in-memory cache. Key format:
- SSN/DOB: `f"usfull:ssn_dob:{md5(json.dumps(data, sort_keys=True))}"`
- CR: `f"usfull:credit_report:{md5(...)}"`

---

## 4. Matching Algorithm (`matching.py`)

### 4.1 Fullz Parsing — `parse_fullz()`

Handles comma-separated, multiline, and pipe-separated formats.

Pipeline:
1. Extract state (2-letter segment, last occurrence)
2. Extract ZIP (5 digits, last occurrence)
3. Extract city (before state/ZIP in last segment)
4. Extract name: remove states, ZIPs, cities, address words → remaining → first/last
5. Extract street: first line starting with digit + street abbreviation

### 4.2 Person Scoring — `score_person()`

Max score: **165** (ZIP 50 + street 30 + city 20 + state 15 + SSN 40 + DOB 30 + phone 25 + email 20)

| Field | Points | Condition |
|---|---|---|
| ZIP | 50 | exact 5-digit match |
| ZIP | 20 | prefix match (first 3 digits) |
| Street | 30 | identical after normalization |
| Street | 15 | same base (number differs) |
| Street | 10 | identical base, same number |
| Street | 5 | ≥2 shared words |
| Street | 3 | ≥1 shared word |
| City | 20 | exact match after normalization |
| State | 15 | exact 2-letter match |
| SSN | 40 | exact 9-digit match |
| DOB | 30 | exact YYYYMMDD match |
| Phone | 25 | any fullz phone matches any person phone (10-digit normalized) |
| Email | 20 | any fullz email matches any person email |

### 4.3 Confidence Tiers

| Score | Tier | Icon |
|---|---|---|
| ≥100 | HIGH | 🟢 |
| ≥60 | MEDIUM | 🟡 |
| <60 | LOW | 🔴 |

### 4.4 Deduplication — `deduplicate_persons()`

Two-phase deduplication:

**Phase 1** (scored list):
- SSN exact match → merge (keep more fields)
- Name similarity ≥80% + same address → merge

**Phase 2** (final):
- SSN exact match
- Jaro-Winkler name similarity >88% + same state

Keeps version with more filled fields (name, first_name, last_name, ssn, dob, phone, address, emails, akas, relatives, age).

### 4.5 Jaro-Winkler Similarity — `_jaro_winkler()`

Formula: `jaro + prefix * 0.1 * (1 - jaro)`, prefix = matching chars at start (max 4).
Range: 0.0–1.0.

---

## 5. Pricing Engine

### 5.1 Base Prices (settings table, USD)

```
phone_price:            2.00
address_price:         2.00
number_address_price:  2.00
background_price:      3.00
phone_verify_price:     0.10
address_verify_price:   0.30
email_verify_price:     0.10
emailrep_price:         0.10
ssn_dob_price:         1.00
driver_license_price:   2.00
credit_report_price:    5.00
credit_score_price:     4.00
```

### 5.2 Usfull.pro Wholesale Prices

```
ssn_dob:        success $0.40 / no_result $0.01
driver_license: success $1.00 / no_result $0.00
credit_report:   success $2.50 / no_result $0.00
credit_score:    success $2.00
```

### 5.3 User Price Calculation

```
user_price = base_price * (1 + user.markup_pct / 100)
```

Default `markup_pct` = 0. User can be set via admin command.

### 5.4 Enformion Wholesale Prices (approximate, from summary)

```
ReversePhone:   $0.50/success
PersonSearch:    $0.30/success
```

### 5.5 Billing Flow

1. Check daily limit (from plan) — if exceeded, block or warn
2. Check subscription plan features — if feature not in plan, reject
3. Deduct from wallet: `balance -= user_price`
4. Record `searches += 1`, `total_spent += user_price`

---

## 6. Input Parsing (`validators.py`)

### 6.1 Freeform Parser — `parse_freeform()`

Strategy selection:
1. **Pipe format** (`|`): 3+ pipes → `_parse_pipe()`
2. **Structured** (`: `): key:value → `_parse_structured()`
3. **Multiline** (2+ lines): → `_parse_multiline()`
4. **Single line**: → `_parse_single_line()`

Post-processing: `_enhance()` fills any missed fields via targeted extraction.

### 6.2 Field Extractors (order matters — consumes from text)

1. `extract_dob()` → MM/DD/YYYY
2. `extract_ssn()` → XXX-XX-XXXX
3. `extract_phone()` → +1XXXXXXXXXX
4. Email regex → lowercase
5. `extract_zip()` → 5 or 5+4 digits
6. `extract_address()` → number + street + type
7. `extract_state()` → 2-letter code
8. City name lookup → common US cities
9. Name → first/last from remaining

### 6.3 Validators (returns `Tuple[bool, str, str]`)

| Validator | Accepts | Returns |
|---|---|---|
| `validate_phone` | `+1XXXXXXXXXX` or `XXXXXXXXXX` | normalized with country code |
| `validate_ssn` | `XXX-XX-XXXX` or 9 digits | `XXX-XX-XXXX` |
| `validate_state` | 2-letter or full name | 2-letter code |
| `validate_zip` | `12345` or `12345-6789` | as-is |
| `validate_dob` | any extract_dob format | MM/DD/YYYY |
| `validate_email` | standard email regex | lowercase |

### 6.4 Batch Parsers

- `parse_phone_list()`: one phone per line → returns `(valid[], errors[])`
- `parse_person_list()`: split by blank lines → `parse_freeform()` per block

---

## 7. Payments (`payments.py`)

### 7.1 Supported Providers

| Provider | Token Field | Currency | Webhook Auth |
|---|---|---|---|
| CryptoBot | `Crypto-Pay-API-Token` header | USDT, TON, BTC, ETH... | HMAC-SHA256(body, sha256(token)) |
| Heleket | `merchant` + `sign` (HMAC-MD5) | USDT, BTC, ETH... | HMAC-MD5(sorted JSON body) |
| BTCPayServer | `Authorization: token <api_key>` | BTC, USDT, USDC... | Bearer token |

### 7.2 Invoice Creation

**CryptoBot:**
```python
POST https://pay.crypt.bot/api/createInvoice
{"asset": "USDT", "amount": "10.00", "description": "Balance top-up",
 "payload": "uid:123:ts:1712345678", "expires_in": 3600}
→ {invoice_id, pay_url, amount, asset, status, created_at}
```

**Heleket:**
```python
POST https://api.heleket.com/v1/payment
{"amount": "10.00", "currency": "USDT", "order_id": "uid123_...", "description": "..."}
→ {uuid, url, amount, currency, payment_status}
```

**BTCPayServer:**
```python
POST <base>/api/v1/stores/<store_id>/invoices
{"amount": "10.00", "currency": "USD", "metadata": {...},
 "checkout": {"speedPolicy": "MediumTolerance"}}
→ {id, checkoutLink, amount, currency, status}
```

### 7.3 Deposit Amounts

`DEPOSIT_AMOUNTS = [5, 10, 20, 50, 100, 200]`

### 7.4 Webhook Verification

**CryptoBot:**
```python
expected = hmac.new(sha256(token), body, sha256).hexdigest()
hmac.compare_digest(expected, signature)  # signature in header
```

**Heleket:**
```python
sorted_json = json.dumps(body, separators=(',', ':'), sort_keys=True)
expected = hmac.new(api_key.encode(), sorted_json.encode(), md5).hexdigest()
hmac.compare_digest(expected, signature)
```

### 7.5 Balance Update on Webhook

On confirmed payment → `add_balance(user_id, amount)` → wallet credited.

---

## 8. Database Schema (`database.py`)

### 8.1 Tables

| Table | Key Columns | Purpose |
|---|---|---|
| `users` | user_id PK | balance, markup, is_admin, daily_limit, total_spent, searches |
| `sb_accounts` | email UNIQUE | Enformion credentials, balance_tok, status, searches |
| `usfull_accounts` | username UNIQUE | Usfull credentials, api_key, balance, status |
| `searches` | id | history: type, query, result_json, cost_user, cost_sb, status |
| `transactions` | id | balance changes: deposits + charges |
| `payments` | invoice_id UNIQUE | provider, amount, status, payload |
| `settings` | key PK | all config: prices, tokens, limits |
| `search_cache` | cache_key PK | TTL-based cache |
| `guarantee_searches` | id | 8-day guarantee search tracking |
| `admin_logs` | id | admin action audit trail |
| `webhook_logs` | id | webhook event log |
| `rate_limits` | (user_id, action) PK | rate limiting state |
| `user_alerts` | id | notifications |
| `subscription_plans` | name UNIQUE | Basic/Pro/Enterprise tiers |
| `subscriptions` | id | user → plan mapping |
| `api_keys` | api_key UNIQUE | REST API access |

### 8.2 Indexes

```sql
idx_searches_user          ON searches(user_id)
idx_payments_invoice       ON payments(invoice_id)
idx_payments_user          ON payments(user_id)
idx_guarantee_user         ON guarantee_searches(user_id)
idx_guarantee_status       ON guarantee_searches(status)
idx_admin_logs_admin       ON admin_logs(admin_id)
idx_admin_logs_target      ON admin_logs(target_type, target_id)
idx_webhook_logs_invoice   ON webhook_logs(invoice_id)
idx_webhook_logs_created   ON webhook_logs(created_at)
idx_user_alerts_user       ON user_alerts(user_id, is_read)
```

### 8.3 Default Settings (INSERT OR IGNORE)

- Prices: phone=2.0, address=2.0, bg=3.0, ssn=1.0, dl=2.0, cr=5.0, cs=4.0
- Plans: Basic($9.99/10day), Pro($29.99/50day), Enterprise($99.99/200day)
- Min deposit: $5.00
- Daily limits: basic=10, pro=50, enterprise=200, default=5

---

## 9. Formatters

### 9.1 Enformion Formatter (`formatters.py` → `fmt_enformion_result()`)

For each person (up to 10):
```
📞 *Результат* — найдено *N* записей

*#1*
  👤 JOHN DOE
  🎂 Возраст: 38 (DOB: ...)
  📱 2125551234
    Тип: Mobile
    Оператор: AT&T
  📍 City, ST
  🏠 123 Main St, City, ST 90210
  📜 История адресов (2):
    • 456 Elm St, ...
  📧 email@example.com
  🔢 SSN: 123456789
  👤 AKA: ...
  📡 VOIP: Да
  🔗 Связан с: Jane Doe
  👨‍👩‍👧 Relatives: ...
```

### 9.2 Phone Identify Formatter

Shows phone type, carrier, location, VOIP status, associated name.

### 9.3 Phone Verify Formatter

`✅ Номер АКТИВЕН — связан с: Name1, Name2`
`❌ Номер НЕАКТИВЕН или не найден`

### 9.4 Export Functions

- `export_csv()`: all people → rows, one row per person
- `export_txt()`: query + status + all fields per result
- `export_json()`: structured JSON per result

---

## 10. Bot Command Handlers (summary)

| Command | Handler | Search Type | Engine | Cost Key |
|---|---|---|---|---|
| `/start` | `cmd_start` | — | — | — |
| `/balance` | `cmd_balance` | — | — | — |
| `/admin` | `cmd_admin` | — | — | — |
| `/health` | `cmd_health` | — | usfull | — |
| `/enfstatus` | `cmd_enfstatus` | — | sb_engine | — |
| `/addaccount` | `cmd_addaccount` | — | DB | — |
| `/loadaccounts` | `cmd_loadaccounts` | — | both | — |
| `/reloadpool` | `cmd_reloadpool` | — | both | — |
| `/setadmin` | `cmd_setadmin` | — | DB | — |
| `/ban`/`/unban` | `cmd_ban`/`cmd_unban` | — | DB | — |
| `/setufkey` | `cmd_setufkey` | — | usfull | — |
| `/setpayment` | `cmd_setpayment` | — | payments | — |
| `/shutdown` | `cmd_shutdown` | — | — | — |
| Free text | `on_message` | dynamic | both | settings |

### 10.1 Batch Processing

Two-pass retry: first pass processes all, second pass retries failed with:
- `TIMEOUT`
- `RETRIES_EXHAUSTED`
- `CIRCUIT_OPEN`
- `POOL_SUSPENDED`
- `NO_ACTIVE_ACCOUNTS`

Concurrency: semaphore with configurable limit (default 5).