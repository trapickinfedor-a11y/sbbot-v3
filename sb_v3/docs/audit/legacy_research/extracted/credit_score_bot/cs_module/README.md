# cs_module — Credit Score Parser Module

Асинхронный модуль для получения кредитного рейтинга через `universal-credit.com` с интеграцией в Telegram-бот.

---

## Архитектура

```
cs_module/
├── __init__.py                    # Публичный API
├── core/
│   └── queue.py                   # WorkerPool + WorkerPoolConfig
├── workers/
│   └── cs_worker.py               # CreditScoreWorker (основная логика)
├── proxy/
│   └── manager.py                 # ProxyManager + ProxyPool (9proxy)
├── fingerprint/
│   └── rotator.py                 # FingerprintRotator (UA, screen, TZ, WebGL)
├── antidetect/
│   └── human.py                   # Human-like behavior (typing, mouse, scroll)
├── bot_interface/
│   ├── models.py                  # JobRequest, JobResult, JobStatus
│   └── ssn_flow.py                # SSN request/resume flow
└── example_bot_integration.py     # Пример интеграции с ботом
```

---

## Ключевые компоненты

### 1. WorkerPool — пул из 5 воркеров

Каждый воркер работает независимо:
- Своя очередь задач (общая `asyncio.Queue`)
- Свой `ProxyManager` (ротация IP каждые 3 попытки)
- Свой `FingerprintRotator` (новый fingerprint на каждый запрос)

```python
from cs_module import WorkerPool, WorkerPoolConfig

config = WorkerPoolConfig(
    proxy_host="gate.9proxy.com",
    proxy_port=7777,
    proxy_username="user",
    proxy_password="pass",
    rotate_every=3,       # Смена IP каждые 3 попытки
    num_workers=5,
    on_result=my_callback,
)
pool = WorkerPool(config)
await pool.start()
```

### 2. ProxyManager — ротация IP через 9proxy

Использует **sticky sessions** 9proxy: каждые `rotate_every` попыток генерируется новый `session_id` в username, что заставляет 9proxy выдать новый IP.

Формат username: `{user}-country-us-session-{random_id}`

```
Попытка 1: session-abc12345 → IP 104.x.x.x
Попытка 2: session-abc12345 → IP 104.x.x.x (тот же)
Попытка 3: session-abc12345 → IP 104.x.x.x (тот же)
Попытка 4: session-xyz98765 → IP 198.x.x.x (НОВЫЙ IP)
```

### 3. FingerprintRotator — новый fingerprint на каждый запрос

Рандомизирует:
- User-Agent (Firefox, разные версии и ОС)
- Screen resolution (1366×768, 1920×1080, etc.)
- Timezone (10 US timezones)
- Language / Accept-Language
- WebGL vendor/renderer
- Canvas noise seed
- Audio context noise seed
- Hardware concurrency (CPU cores)
- Device memory

### 4. Anti-detection (antidetect/human.py)

- **Typing**: случайные задержки между символами (50–250ms), "паузы раздумья" (7% символов)
- **Mouse**: движение по кривой Безье (не прямая линия)
- **Scroll**: случайные инкременты, переменная скорость
- **Page warm-up**: случайные движения мыши + скролл после загрузки
- **JS noise injection**: canvas, audio, WebGL, battery API — рандомизация для ThreatMetrix

### 5. SSN Flow — запрос SSN у пользователя

Когда парсер не может получить score без SSN (fallback на petalcard.com):

```python
# В боте — обработчик ответа пользователя с SSN
from cs_module import ssn_flow

# Когда пользователь прислал SSN:
success = ssn_flow.provide_ssn(job_id, "591-47-1800")
# Воркер автоматически возобновляется с новым SSN
```

---

## Флоу обработки запроса

```
Bot → submit(JobRequest)
         ↓
    asyncio.Queue
         ↓
    Worker (один из 5)
         ↓
    [Новый fingerprint]
    [Получить proxy URL (ротация каждые 3)]
         ↓
    Запустить camoufox браузер
         ↓
    Inject ThreatMetrix noise
         ↓
    Заполнить форму universal-credit.com
    ├── Step 1: Имя, адрес, DOB
    ├── Step 2: Доход
    └── Step 3: Email, пароль, согласие
         ↓
    Ждать adverse-page / offer-page
         ↓
    Перейти в Documents portal
         ↓
    Скачать Adverse Action Notice PDF
         ↓
    Извлечь credit score из PDF
         ↓
    JobResult → on_result callback → Bot
```

---

## Интеграция в бот

```python
# bot.py
from cs_module import WorkerPool, WorkerPoolConfig, JobRequest, ssn_flow

# Инициализация при старте бота
pool = WorkerPool(WorkerPoolConfig(
    proxy_host="gate.9proxy.com",
    proxy_port=7777,
    proxy_username="YOUR_USER",
    proxy_password="YOUR_PASS",
    on_result=send_result_to_user,
))

@bot.on_startup
async def startup():
    await pool.start()

@bot.on_shutdown
async def shutdown():
    await pool.stop()

# Обработчик команды /check
@bot.message_handler(commands=['check'])
async def handle_check(message):
    job = JobRequest(
        telegram_chat_id=message.chat.id,
        telegram_message_id=message.message_id,
        telegram_user_id=message.from_user.id,
        first_name="John",
        last_name="Doe",
        street="123 Main St",
        city="Los Angeles",
        state="CA",
        zip_code="90001",
        dob="01/15/1990",
    )
    await pool.submit(job)

# Обработчик ответа с SSN
pending_ssn = {}  # chat_id → job_id

@bot.message_handler(func=lambda m: m.chat.id in pending_ssn)
async def handle_ssn_reply(message):
    job_id = pending_ssn.pop(message.chat.id)
    ok = ssn_flow.provide_ssn(job_id, message.text)
    if not ok:
        await bot.reply_to(message, "❌ Неверный формат SSN. Используйте XXX-XX-XXXX")
```

---

## Зависимости

```
camoufox
playwright
aiohttp
pdfminer.six
```

---

## Конфигурация 9proxy

9proxy поддерживает sticky sessions через параметр `session` в username:

```
http://user-country-us-session-RANDOM:pass@gate.9proxy.com:7777
```

Каждые 3 попытки генерируется новый `RANDOM` → новый IP.
