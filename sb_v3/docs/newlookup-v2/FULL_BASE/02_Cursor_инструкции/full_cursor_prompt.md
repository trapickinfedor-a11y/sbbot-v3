# ONE Bot — Full Cursor Prompt (Split by Agents)

> Разбей работу на 9 независимых агентов. Каждый агент работает параллельно над своим модулем.
> Все агенты используют общую БД (PostgreSQL), общий config.py, общий encryption service.
> НЕ трогай существующий код — только добавляй новые файлы и расширяй схему БД.

---

## AGENT 1 — Mirror Bot (Main Bot Fixes & Updates)

### 1.1 Language selection fix
On /start show 4 language buttons before anything else:
```
[🇺🇸 English] [🇷🇺 Русский] [🇪🇸 Español] [🇩🇪 Deutsch]
```
Save chosen language to users.language column. All subsequent messages use that language.
All text strings must be stored in a `translations` dict/table keyed by language code.

### 1.2 Coupon system
Table `coupons`: code, type (percent|fixed|free_service), value, applicable_to (all|category_name|service_id), max_activations, used_count, expires_at, is_active.

Flow: user enters coupon code → bot validates → shows discount preview → applies at checkout.
Admin can create/edit/disable coupons via admin panel.

### 1.3 Buyer ↔ Seller chat
After purchase, buyer gets button [💬 Write to seller].
Opens a proxied chat thread (stored in table `chats`: order_id, buyer_id, seller_id, messages[]).
Seller receives notification in Seller App.
Both sides can send text + files.

### 1.4 Order rating
After purchase, buyer sees [👍 Like] [👎 Dislike] buttons.
If not rated → reminder appears in purchase history with [⭐ Rate this order].
Rating stored in `ratings` table, affects seller's success_rate %.

### 1.5 Education section
#### Manuals
- Admin uploads PDF → bot stores original in /manuals/originals/
- On purchase: generate unique watermarked PDF per user (visible watermark "@username | ID:XXXXX | ONE" diagonal on every page + invisible zero-width Unicode tracker)
- Delivered as images (each page = image) with watermark
- Admin panel: manage order, pagination, create new, edit price
- New manuals added to worker bot queue same as all other services

#### Base & Subscriptions
- Positions added as manual orders (worker bot), no auto-delivery
- Admin manages via worker panel same as existing services

### 1.6 Documents — add counters
All subcategory levels show count in []:
```
📄 Documents
├── Checks [47]
│   ├── Chase [12]
│   ├── Wells Fargo [8]
```

### 1.7 Fullz configurator extension
After existing configurator steps, add before quantity selection:

**Step: Select Report Group**
```
📑 Select Report Group:
[With CR +$2.00] [CR & DL +$10.00] [CR, DL & MVR +$22.00] [WE CR, DL & FULL MVR +$32.00]
```

**Step: Carrier filter (only if CR selected)**
```
🔌 Carrier in CR/BG:
[Without AT&T +$7] [Without T-Mobile +$7] [Without Verizon +$7] [Any — $0]
```

**Step: Bank filter (only if CR selected)**
```
🏦 Bank filter:
[Without Citi +$7] [Without Chase +$7] [Without Wells +$7] [Without BoA +$7] [Without US +$7] [Any — $0]
```

Then → quantity selection → checkout.

### 1.8 Subscriptions / Accounts — new categories
Add PROXY and AI subcategories under Subscriptions.
Same discount logic as eSIM (bulk discount tiers).
Admin adds positions with description manually.

### 1.9 eSIM — CUSTOM configurator (3rd category)
```
hidden base_price = $30
Step 1: State → [Select state +$10] [Any $0]
Step 2: Carrier → [AT&T +$20] [Verizon +$20] [T-Mobile +$20] [Any $0]
Step 3: Credit Score → [700+ +$10] [800+ +$20] [Any $0]
Step 4: Gender → [Male +$5] [Female +$5] [Any $0]
Step 5: Bulk discount tiers (same as other eSIM)
Step 6: ✍️ Add info in CR (text field)
```
Admin can change all descriptions on all 4 languages.

### 1.10 Referrals rename
Section now called "🤝 Referrals +10%". Admin can edit description on all 4 languages.

### 1.11 Admin price management
Admin can change ALL prices for ALL services from admin panel.
Can add new subcategories, reorder them — changes reflect immediately in bot and worker bot creation flow.

---

## AGENT 2 — Marketing Bot

### Full flow:
1. /start → choose language [🇺🇸 EN] [🇷🇺 RU] [🇪🇸 ES] [🇩🇪 DE]
2. User receives instruction text: how to use the bot, how to create bots, how to withdraw
3. User sees their interactive dashboard (sent as formatted message):

```
📊 Your Dashboard

📈 Total earned today: $0.00
📈 Total earned: $0.00
💸 Total withdrawn: $0.00

👥 Total referrals: 0 (all bots)

Today:
  Bot 1 — Reg: 0 | First top-ups: 0 | Amount: $0.00 | Earned: $0.00
  Bot 2 — ...
  Bot 3 — ...

Last 30 days:
  Bot 1 — Reg: 0 | First top-ups: 0 | Amount: $0.00 | Earned: $0.00
  ...
```

### Buttons:
```
[📱 My Bots] [💸 Withdraw] [📋 All Top-ups] [➕ Create Bot] [🔄 Refresh]
```

### Create Bot logic:
- Same logic as main bot mirror creation
- Limit: 5 bots per marketer
- Each bot tracks its own stats separately

### All Top-ups:
- Shows list of all top-ups across all bots
- Does NOT reveal user personal data

### Withdraw:
- USDT / BTC / XMR / LTC
- Enter amount + wallet → confirmation → request sent to admin/accountant

### Auto-messages:
- Every 50 new users in a bot → send message to bot owner with notification
- Every 50 users → bot sends message to users asking to create their own bots

---

## AGENT 3 — Seller Bot + App

### /start flow:
1. Show instruction: why seller pays insurance deposit + terms of service
2. Payment via BTCPay Server API (BTC / LTC / XMR) — auto-confirm on blockchain
3. Package selection:
```
[CC + Enroll + NFC + OTP — $200]
[Selfregs BA + Selfregs CC — $100]
[Logs + Brute — $150]
[Checks — $200]
```
4. After payment confirmed → seller gets access to their purchased categories

### After /start (active seller):
```
👤 Seller Dashboard

💼 Hold balance: $X.XX (value of listed inventory)
💸 Withdrawal balance: $X.XX
📊 Rate: X%
✅ Success sales: X%

[👤 Profile] [➕ Add Support] [💸 Withdraw] [📦 App]
```

### Withdraw:
USDT / BTC / XMR / LTC → amount + wallet → confirmation → request to admin.
Admin can approve or cancel. On approval → seller withdrawal_balance resets to 0.

### Add Supports:
Seller enters Telegram ID + assigns role (category access).
Support sees only their assigned categories and notifications.

### App (web panel):
- Full analytics by date: sales %, rating, disputes
- Upload inventory per category
- Chat with buyers
- Profile management
- Supports / audit log
- Withdrawal requests

### Seller notifications:
```
✅ Item uploaded successfully
🛒 Your item was purchased
💬 Buyer wrote to you
⚠️ Buyer submitted a report
💰 Balance credited: +$X
📊 Daily report: X sold, $X earned, X disputes
```

### Daily report (auto, once per day):
```
📊 Daily Report
Items sold: X | Revenue: $X | Disputes: X open
```

---

## AGENT 4 — Worker Bot

### /start:
```
👋 Welcome, [Name]!

🆔 Support ID: XX
📊 Total Orders: XX
💰 Earned today: $X.XX
💸 Withdrawal balance: $X.XX

📋 Your Categories: [list assigned categories]

[📥 Available Orders] [⚙️ My Orders (Processing)] [📋 Order History]
[📊 My Statistics] [👤 Profile]
```

### Order assignment logic:
Admin assigns worker to specific category + specific service.
Worker receives ONLY orders from their assigned category/service.
Admin sets fixed price OR % per worker — deducted automatically from revenue.

### Order notification:
```
📦 New Order #XXXX

Service: [service name]
Category: [category]

👤 Customer Data:
[raw input data]

[✅ Take Order] [⬅️ Back]
```

### Order processing:
```
📦 ORDER #XXXX
Service: ...
Status: PROCESSING
Customer Data: ...
Created: [datetime]
Taken by you at: [datetime]

[✅ DONE + Text] [✅ DONE + Files] [📝 Write Message]
[❌ NF (Not Found)] [✖️ Cancel Order] [🚨 Report Client]
```

### Write message:
Worker types message → confirms → message sent to customer → order reappears for next action.

### Auto-notifications:
Every 2 hours → reminder of orders currently in processing status.

### Statistics & withdrawal:
Worker can view full stats and submit withdrawal request from bot.
Balance resets on admin approval. Daily report sent automatically.

---

## AGENT 5 — Support Bot

### Roles (assigned by admin):
- **Moderator**: receives sales, reports, disputes, upload approval requests. Interactive menu with confirm/cancel/modify. Sees full order as buyer sees it (all files, text).
- **Support**: receives support ticket texts. Can reply directly from bot. Full reply only from admin panel.
- **Uploader**: receives upload logs, can view successful/failed uploads per category.
- **Accountant**: receives seller + marketer withdrawal requests. Gets reminders. Can mark as paid.
- **Main Admin**: receives ALL successful actions across all bots.

### Moderator flow:
```
📋 New Report #XXXX
Order: #XXXX | Category: CC | Buyer: @user
Reason: Login not working
[📎 Screenshot attached]

[✅ Approve Refund] [❌ Reject] [💬 Ask for more info]
```

### Broadcast from admin:
Admin can send mass notifications to:
- All workers
- All sellers
- All marketers
- All users (in batches of 50)

---

## AGENT 6 — Admin Panel (Web)

### Analytics:
- Orders by category (all service types)
- Purchased items + orders combined view
- Transactions with full payment description
- Add mirror bots quickly (button)
- Mark marketing bots

### Worker management:
- Assign worker → select category → select service(s)
- Set fixed price or % per worker
- Worker stats, balance, withdrawal requests
- Mass notification to all workers

### Payment integrations:
- Current: show active payment methods
- Prepared slots for: Helicat API, BTCPay Server API (add keys, show status, toggle on/off)

### Automation section:
- Separate tab for automations (no logic yet, just structure)
- Stats panel for each automation
- API key management per automation worker
- Browser fix applied in automation code:
```python
browser_args = [
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox",
    "--disable-gpu",
    "--disable-software-rasterizer",
]
camoufox_kwargs.update({
    "headless": self.headless,
    "proxy": {"server": proxy_url},
    "args": browser_args,
})
```

### Price management:
Admin changes ALL prices for ALL services from one panel.
Changes reflect immediately in bot menus and worker assignment flow.

### Support chat:
Convenient support chat interface in admin panel.
Complaints managed via cron tasks.

---

## AGENT 7 — CC Shop Module (Full Upload & Browse)

### Categories:
```
CC
├── With ZIP []
├── With Fullz []
├── NON-VBV []
├── Enroll []
│   ├── FDECS [] ├── DIGITALCARDSERVICE [] ├── MYCARDINFO [] ├── CARDNAV []
├── OTP CARD []
├── CC (standard) []
├── Debit []
└── NFC []
    ├── Apple Pay (AP) []
    └── Google Pay (GP) []

BANK
├── Personal VCC []
├── Personal Banks []
├── Business Banks []
├── Crypto Banks []
│   ├── Available [N] ← from seller panel
│   └── Per Name+Address (soon)

Brute Bank ← from seller panel
Logs ← from seller panel
```

### CC Upload (bulk .txt):
```
NUMBER|EXP_MM|EXP_YYYY|CVV|FNAME|LNAME|ADDRESS|CITY|STATE|ZIP|COUNTRY
```
Required: NUMBER, EXP_MM, EXP_YYYY, CVV, ZIP
Optional: FNAME, LNAME, ADDRESS, CITY, STATE, COUNTRY

Auto-detection per line:
1. Luhn check → invalid: skip
2. BIN lookup (local SQLite first → binlist.net API → cache):
   - card scheme (Visa/MC/Amex/Discover)
   - card level (Classic/Gold/Platinum/Business/Infinite)
   - bank name
   - country
   - type (credit/debit/prepaid)
3. Auto-detect subcategory:
   - has ZIP → With ZIP
   - has FNAME+LNAME+ADDRESS → With Fullz
   - seller pre-selected NON-VBV → NON-VBV
   - else → Standard

Auto-pricing table (seller can override):
| Level     | Standard | NON-VBV | With Fullz | With ZIP |
|-----------|----------|---------|------------|----------|
| Classic   | $8       | $14     | $12        | $10      |
| Gold      | $15      | $24     | $20        | $18      |
| Platinum  | $22      | $35     | $30        | $26      |
| Business  | $30      | $48     | $42        | $36      |
| Infinite  | $45      | $72     | $62        | $54      |

After upload → show summary: "Found 247 cards. Valid: 231. Duplicates: 16. Add?"

### NFC Upload (bulk .txt, no mass upload — per bank):
```
NUMBER|EXP_MM|EXP_YYYY|CVV|FNAME|LNAME|STATE|ZIP|COUNTRY|NFC_TYPE|DEVICE_TOKEN
```
Seller selects: [Apple Pay (AP)] [Google Pay (GP)] → selects/adds bank → uploads file.

### Enroll Upload (ZIP per item):
```
/enroll_data.json:
{
  card_credit_debit, portal (FDECS/DIGITALCARDSERVICE/MYCARDINFO/CARDNAV),
  card_type, balance, state, zip,
  has_ssn, has_dob, has_name, has_address,
  phone_area_code, has_email, has_security_qa,
  has_docs, doc_type (Driver License/Passport/SSN Card)
}
```

### OTP CARD Upload (ZIP per item):
```
/otp_data.json:
{
  bank, balance (optional), has_fullz,
  sms_access_type (via_seller | via_account),
  seller_description
}
```

### Brute Banks Upload (bulk .txt):
```
BANK|LOGIN|PASS|ACCOUNT_NUMBER|ROUTING|BALANCE|STATE|NAME|ADDRESS
OR
BANK|no|no|ACCOUNT_NUMBER|ROUTING|BALANCE|STATE|NAME|ADDRESS
```
Required: BANK, LOGIN or ACCOUNT_NUMBER, BALANCE
Auto-creates subcategory by BANK name.

### Logs Upload (ZIP per item):
```
/metadata.json:
{
  banks: [{ name, accounts: [{type, balance, bt, has_cvv}], email, email_valid }],
  flags: { has_cvv, bt_available, promo_available, zelle_enroll, wire_available,
           billpay_available, external_available, safepass_unlocked, need_phone_enroll },
  is_business, seller_notes
}
/cookies/ (required)
/passwords/ (optional)
/screenshot.png (optional — auto-watermarked)
```
Account types: Checking / Savings / CC / Invest / Line of credit / BUS Checking / BUS Savings / BUS CC

### Selfregs BA Upload (ZIP per item):
```
/ba_data.json:
{
  bank, state, zip, balance,
  has_phone, phone_days_remaining, phone_renewable, phone_change_method,
  email_access, email_change_method (call | lk+hold | custom),
  has_ssn, has_docs, doc_type
}
```

### Selfregs CC Upload (ZIP per item):
```
/cc_data.json:
{
  bank, card_name, state, zip, credit_limit,
  is_vcc, vcc_limit,
  has_email, has_phone, phone_days, phone_renewable, phone_changeable,
  online_access
}
```

### Checks Upload (ZIP per item):
```
/check_data.json:
{
  check_type (Personal/Business/Payroll/Cashier's),
  bank, amount, state, zip,
  has_holder_name, has_address, check_date,
  has_micr, has_serial, has_memo,
  seller_description
}
/scan.jpg (required)
/template.pdf (optional)
```

---

## AGENT 8 — Purchase Flow & Guarantee System

### Universal purchase flow (all categories):

**Step 1 — Product card:**
User browses with filter buttons + pagination [◀ N/Total ▶]

**Step 2 — Confirm:**
```
⚠️ Confirm purchase?
[product name | key params]
💵 $XX will be deducted from your balance
[✅ Confirm] [❌ Cancel]
```

**Step 3 — Warning + conditions (shown after confirm, before data):**

| Category | Warning text | Timer |
|----------|-------------|-------|
| CC / Debit / Brute | "Ready to buy? No refund after purchase." | ❌ |
| NFC | "24 hours to check account access. Video proof accepted." | ⏱ 24h |
| OTP Card | "If something doesn't work — let us know within 1 hour." | ⏱ 1h |
| Enroll | "Got an issue? You have 2 hours to reach out." | ⏱ 2h |
| Selfregs BA | "Questions within 3 hours — just write to us." | ⏱ 3h |
| Selfregs CC | "Any issues — reach out within 1 hour." | ⏱ 1h |
| Logs | "If it's dead — let us know within 6 hours." | ⏱ 6h |
| Checks | "Any issues — reach out within 1 hour." | ⏱ 1h |

**Step 4 — Data delivery:**

- CC/Brute: data shown immediately in message
- NFC/Enroll/OTP/Selfregs: [🔓 Open Data] button + timer + [💬 Something wrong?]
- Logs: [📦 Download ZIP] + timer + [💬 Something wrong?]
- Checks: [📄 Download] + timer + [💬 Something wrong?]

**Step 5 — Rating:**
After timer expires OR after user opens data:
[👍 Like] [👎 Dislike] → if not rated → reminder in purchase history

**Step 6 — Report:**
[💬 Something wrong?] → opens chat with support. No mandatory screenshot. Human decision.
Timer expires → button disappears silently.

**CC specific — after data shown:**
```
✅ Purchase successful!
━━━━━━━━━━━━━━━━━━━
You have 15 minutes to verify data.
Appeal possible with video proof from any verified checker.
━━━━━━━━━━━━━━━━━━━
[Your card data here]
━━━━━━━━━━━━━━━━━━━
[✅ Confirm — Like] [❌ Report — Dislike] [🏠 Main Menu]
```

---

## AGENT 9 — CRM & NocoDB Integration

Log ALL of the following to NocoDB via API:

| Event | Fields logged |
|-------|--------------|
| Worker messages in orders | order_id, worker_id, message, files, timestamp |
| Moderator actions | order_id, moderator_id, action, message, files, timestamp |
| Seller ↔ buyer chat | order_id, seller_id, buyer_id, message, files, timestamp |
| Support tickets | ticket_id, user_id, message, support_reply, files, timestamp |
| Manual top-ups | user_id, amount, admin_id, note, timestamp |
| Bot top-ups | user_id, amount, payment_method, tx_id, timestamp |
| File operations | user_id, action (view/add/delete/sell), file_id, category, timestamp |
| Failed uploads | seller_id, category, error_reason, timestamp |
| User bugs | user_id, error_type, context, timestamp |

All logs are read-only in NocoDB (append only, never delete).

---

## SHARED REQUIREMENTS (all agents)

### Database additions:
```sql
-- New tables needed:
coupons, chats, chat_messages, ratings, translations,
seller_packages, seller_supports, worker_assignments,
marketing_bots, marketing_stats, crm_logs,
automation_workers, automation_keys,
bin_cache, category_requests, pricing_config
```

### File structure additions:
```
/handlers/
  coupon.py, chat.py, rating.py, language.py
  cc_browse.py, cc_purchase.py, cc_upload.py
  nfc_upload.py, enroll_upload.py, otp_upload.py
  ba_upload.py, selfreg_cc_upload.py
  logs_upload.py, brute_upload.py, checks_upload.py
  guarantee.py, report.py

/services/
  bin_lookup.py, cc_parser.py, brute_parser.py
  zip_validator.py, watermark_pdf.py
  btcpay.py, helicat.py
  crm_logger.py, nocobd_client.py
  notification_scheduler.py

/bots/
  marketing_bot.py
  seller_bot.py
  worker_bot.py
  support_bot.py

/app/ (seller web app)
  main.py (FastAPI)
  routers/analytics.py, upload.py, chat.py, profile.py, supports.py
  templates/

/admin/ (web admin panel)
  routers/prices.py, workers.py, automations.py, broadcast.py
```

### Config:
All base prices, discount tiers, timer durations, commission rates stored in DB table `pricing_config`.
Admin changes them from panel → immediate effect everywhere.

### Translations:
All user-facing strings in `translations` table: key, en, ru, es, de.
Admin edits all strings from admin panel.
