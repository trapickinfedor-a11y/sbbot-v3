# 🗺️ Структура развития и направления деплоя

## 📊 Обзор проекта

Проект **NewLookup** — мультисервисная система, объединяющая:
- **Основной продукт:** Telegram-боты (mirror, support, seller) + веб-панель
- **Legacy-система:** PPTP bruteforcer, crypto order bot, admin panel integration

## ✅ Launch Baseline

Текущий рабочий baseline для запуска:
- production-like запуск: `docker-compose.yml`
- local запуск: `run_local.py`
- env-шаблон: `.env.example`
- операторский runbook и smoke checklist: `docs/LAUNCH_RUNBOOK.md`

Статус launch baseline:
- `compose` больше не зависит от отсутствующего `init_db.sql`
- `tasks.db` нормализована в общий runtime path
- startup validation добавлена для `main_bot`, `support_bot`, `seller_bot`, `marketer_bot`, `web_panel`
- `Brute` seller/admin/buyer flow выровнен без seller-side category step
- seller mini app отправляет актуальные bank/brute payloads

Ниже по файлу сохранён архитектурный roadmap; для фактического запуска использовать именно runbook выше.

---

## 🏗️ Карта компонентов и зависимостей

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ИНФРАСТРУКТУРА                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│  PostgreSQL  ◄──────►  Redis                                                 │
│  (БД)                 (кэш, очереди)                                         │
└─────────────────────────────────────────────────────────────────────────────┘
         │                        │
         │    ┌───────────────────┼───────────────────┐
         │    │                   │                   │
         ▼    ▼                   ▼                   ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  main_bot   │  │ support_bot │  │  seller_bot  │  │  web_panel  │
│ (mirror)    │  │             │  │             │  │  (admin)    │
└──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘
       │                │                │                │
       └────────────────┴────────────────┴────────────────┘
                                │
                         shared (модули)
```

---

## 🚀 Направления деплоя (Deployment Tiers)

### Tier 1: Минимальный стек (MVP)
**Цель:** Запуск основного бота для пользователей.

| Компонент | Обязателен | Зависимости |
|-----------|------------|-------------|
| PostgreSQL | ✅ | — |
| Redis | ✅ | — |
| main_bot | ✅ | postgres, redis |
| shared | ✅ | встроен в main_bot |

**Использование:** Тестирование, dev-окружение, минимальный production.

```bash
# MVP: только postgres, redis, main_bot
docker-compose up postgres redis main_bot -d
```

---

### Tier 2: Полный пользовательский стек
**Цель:** Полнофункциональный продукт для клиентов.

| Компонент | Обязателен | Зависимости |
|-----------|------------|-------------|
| PostgreSQL | ✅ | — |
| Redis | ✅ | — |
| main_bot | ✅ | postgres, redis |
| support_bot | ✅ | postgres, redis |
| web_panel | ✅ | postgres, redis |
| shared | ✅ | встроен |

**Использование:** Production для клиентов (lookup, banks, orders, support).

```bash
docker-compose up postgres redis main_bot support_bot web_panel -d
```

---

### Tier 3: Полный стек с продавцами
**Цель:** Включение seller-бота и всех админ-функций.

| Компонент | Обязателен | Зависимости |
|-----------|------------|-------------|
| Всё из Tier 2 | ✅ | — |
| seller_bot | ✅ | postgres, redis, support_bot (уведомления) |

**Использование:** Полный production с продавцами и модерацией.

```bash
docker-compose up -d
```

---

### Tier 4: Legacy-система (отдельно)
**Цель:** PPTP bruteforcer + crypto order bot (не связана с основным продуктом).

| Компонент | Обязателен | Зависимости |
|-----------|------------|-------------|
| pptp_auto_bruteforcer | опционально | SQLite (локально) |
| admin_panel_bot | опционально | — |
| crypto_order_bot | опционально | — |
| admin_panel_integration | опционально | Admin Panel API |

**Использование:** Отдельный деплой на другом сервере/контейнере.

```bash
# Запуск legacy-системы
python3 system_launcher.py
```

---

## 📋 Матрица независимого деплоя

| Компонент | Можно деплоить отдельно? | Требует |
|-----------|--------------------------|---------|
| **main_bot** | ✅ Да | postgres, redis |
| **support_bot** | ✅ Да | postgres, redis |
| **seller_bot** | ✅ Да | postgres, redis, support_bot (для уведомлений) |
| **web_panel** | ✅ Да | postgres, redis |
| **postgres** | ✅ Да | — |
| **redis** | ✅ Да | — |
| **Legacy (PPTP/Crypto)** | ✅ Да | Отдельная БД (SQLite), Admin Panel API |

---

## 🗂️ Рекомендуемые конфигурации деплоя

### Конфигурация A: Один сервер (монолит)
```
Сервер 1:
├── postgres
├── redis
├── main_bot
├── support_bot
├── seller_bot
└── web_panel
```
**Плюсы:** Простота, низкая стоимость.  
**Минусы:** Один point of failure, ограниченное масштабирование.

---

### Конфигурация B: Разделение по ролям
```
Сервер 1 (БД + кэш):
├── postgres
└── redis

Сервер 2 (Боты):
├── main_bot
├── support_bot
└── seller_bot

Сервер 3 (Веб):
└── web_panel
```
**Плюсы:** Изоляция, можно масштабировать ботов.  
**Минусы:** Сложнее настройка сети.

---

### Конфигурация C: Горизонтальное масштабирование
```
Load Balancer
    │
    ├── main_bot (replica 1)
    ├── main_bot (replica 2)
    └── main_bot (replica N)

postgres (primary + replicas)
redis (cluster)
web_panel (N replicas)
support_bot (1)
seller_bot (1)
```
**Плюсы:** Высокая доступность, нагрузка.  
**Минусы:** Сложность, стоимость.

---

### Конфигурация D: Legacy отдельно
```
Сервер 1 (основной продукт):
├── postgres, redis
├── main_bot, support_bot, seller_bot
└── web_panel

Сервер 2 (legacy):
├── system_launcher.py
├── pptp_auto_bruteforcer
├── admin_panel_bot
└── crypto_order_bot
```
**Плюсы:** Изоляция legacy, разные жизненные циклы.  
**Минусы:** Два окружения для поддержки.

---

## 📈 Roadmap развития

### Фаза 1: Стабилизация (текущая)
- [ ] Вынести конфигурации деплоя в отдельные docker-compose файлы
- [ ] Добавить health checks для всех сервисов
- [ ] Документировать переменные окружения по компонентам

### Фаза 2: Модуляризация
- [ ] Создать `deploy/` со скриптами для каждого tier:
  - `deploy/mvp.sh` — postgres + redis + main_bot
  - `deploy/full.sh` — полный стек без seller
  - `deploy/full-sellers.sh` — полный стек
- [ ] Добавить мониторинг (Prometheus/Grafana или аналог)

### Фаза 3: CI/CD
- [ ] GitHub Actions / GitLab CI для каждого компонента
- [ ] Отдельные пайплайны: main_bot, support_bot, seller_bot, web_panel
- [ ] Автодеплой по веткам (staging, production)

### Фаза 4: Масштабирование
- [ ] Поддержка Kubernetes (Helm charts)
- [ ] Отдельные деплойменты для каждого сервиса
- [ ] Service mesh (опционально)

---

## 🔧 Команды запуска

| Tier | Команда |
|------|---------|
| MVP | `docker-compose up postgres redis main_bot -d` |
| Full | `docker-compose up postgres redis main_bot support_bot web_panel -d` |
| Full + Sellers | `docker-compose up -d` |

---

## 📌 Резюме

| Направление | Компоненты | Когда использовать |
|-------------|------------|---------------------|
| **MVP** | postgres, redis, main_bot | Dev, тесты, минимальный запуск |
| **Full** | + support_bot, web_panel | Production для клиентов |
| **Full + Sellers** | + seller_bot | Production с продавцами |
| **Legacy** | PPTP, crypto, admin bot | Отдельный продукт/интеграция |

**Рекомендация:** Держать основной продукт (Tier 1–3) и legacy (Tier 4) в отдельных деплой-конфигурациях — у них разные жизненные циклы и зависимости.

---

## ⚡ Быстрая справка

| Цель | Команда |
|-----|---------|
| MVP (только бот) | `docker-compose up postgres redis main_bot -d` |
| Full (бот + support + панель) | `docker-compose up postgres redis main_bot support_bot web_panel -d` |
| Полный стек | `docker-compose up -d` |
| Legacy (PPTP/Crypto) | `python3 system_launcher.py` |
