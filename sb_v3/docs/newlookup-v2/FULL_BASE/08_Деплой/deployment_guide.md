## Deployment Guide — Развертывание и Обслуживание

**Задача:** Описать полный, воспроизводимый и автоматизированный процесс развертывания, обновления и обслуживания всей системы Newlookup. Это критически важный документ для DevOps-инженера и для обеспечения стабильности платформы.

**Философия:** "Инфраструктура как код (IaC)". Все аспекты инфраструктуры должны быть описаны в коде, версионированы и автоматизированы, чтобы исключить ручные ошибки.

---

### 1. Архитектура и Технологический Стек

Система состоит из нескольких независимых, но взаимосвязанных сервисов, упакованных в Docker-контейнеры.

*   **База данных:** PostgreSQL (основная), Redis (для кеширования и очередей).
*   **Бэкенд:** Python (FastAPI).
    *   `core-api`: Основной API для всей бизнес-логики.
    *   `telegram-bots`: Сервис, запускающий всех Telegram-ботов (использует aiogram).
*   **Фронтенд:**
    *   `admin-panel`: React (Vite).
    *   `seller-mini-app`: React (Vite), интегрируется в Telegram.
    *   `public-site`: Next.js.
*   **Очередь задач:** Celery с RabbitMQ или Redis в качестве брокера.
*   **Платежный шлюз:** BTCPay Server (разворачивается как отдельный сервис).

### 2. Docker Compose для Локальной Разработки

Для упрощения локальной разработки создается файл `docker-compose.dev.yml`.

```yaml
version: '3.8'

services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: newlookup
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data/

  redis:
    image: redis:7
    ports:
      - "6379:6379"

  api:
    build: ./backend/core-api
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - ./backend/core-api:/app
    ports:
      - "8000:8000"
    depends_on:
      - db
      - redis

  bots:
    build: ./backend/telegram-bots
    command: python main.py
    volumes:
      - ./backend/telegram-bots:/app
    depends_on:
      - api

  # ... и так далее для фронтенд-сервисов

volumes:
  postgres_data:
```

**Запуск:** `docker-compose -f docker-compose.dev.yml up`

### 3. Production-Развертывание (CI/CD)

**Цель:** Автоматизировать процесс сборки, тестирования и развертывания при каждом коммите в `main` ветку.

**Инструменты:**
*   **Хостинг:** Выделенный сервер (Hetzner, OVH) или облако (AWS, GCP).
*   **CI/CD:** GitHub Actions.
*   **Оркестрация:** Docker Swarm или Kubernetes (k3s для простоты).

**Процесс (GitHub Actions Workflow):**

1.  **Push в `main` ветку.**
2.  **Run Tests:** Запускаются юнит-тесты и интеграционные тесты.
3.  **Build & Push Docker Images:**
    *   Собираются Docker-образы для каждого сервиса.
    *   Образам присваивается тег с хешем коммита (`my-api:a1b2c3d`).
    *   Образы загружаются в Docker Hub или другой приватный репозиторий.
4.  **Deploy to Production:**
    *   GitHub Actions по SSH подключается к продакшен-серверу.
    *   Выполняет команду `docker stack deploy` (для Swarm) или `kubectl apply` (для Kubernetes), обновляя образы сервисов до новой версии.
    *   Docker Swarm/Kubernetes плавно, без даунтайма, заменяет старые контейнеры на новые.

### 4. Мониторинг и Логирование

**Задача:** Иметь полное представление о состоянии системы в реальном времени и возможность быстро диагностировать проблемы.

**Стек ELK/PLG:**
*   **Prometheus:** Сбор метрик со всех сервисов (CPU, RAM, количество запросов, время ответа).
*   **Grafana:** Визуализация метрик из Prometheus в виде дашбордов.
*   **Loki:** Сбор логов из всех Docker-контейнеров.
*   **Promtail:** Агент для отправки логов в Loki.

**Что мониторить:**
*   **Системные метрики:** Нагрузка на CPU, использование памяти, место на диске.
*   **Бизнес-метрики:** Количество регистраций, продаж, активных пользователей (отправляются из `core-api` в Prometheus).
*   **Ошибки:** Дашборд в Grafana, показывающий количество 5xx ошибок и других исключений из логов.

**Алертинг:**
*   Настраивается в Grafana или Alertmanager.
*   **Правила:**
    *   Если CPU > 90% в течение 5 минут → отправить алерт в Telegram-чат администраторов.
    *   Если сервис `core-api` не отвечает > 1 минуты → отправить алерт.
    *   Если количество 5xx ошибок превышает 10 в минуту → отправить алерт.

### 5. Резервное Копирование (Backup)

**Задача:** Обеспечить возможность восстановления системы в случае сбоя.

*   **База данных (PostgreSQL):**
    *   Настраивается ежедневный `pg_dump`.
    *   Бэкап шифруется и загружается во внешнее S3-совместимое хранилище (например, Backblaze B2).
    *   Хранятся бэкапы за последние 30 дней.
*   **Docker-тома:**
    *   Данные, которые хранятся в Docker-томах (например, загруженные пользователями файлы), также ежедневно бэкапятся в S3.
*   **Проверка восстановления:** Раз в месяц проводится тестовое восстановление из бэкапа на отдельном сервере, чтобы убедиться в их работоспособности.

## 6. Инструмент Управления Проектом: Plane

**Задача:** Настроить единое пространство для управления разработкой, задачами, документацией и баг-трекингом.

**Решение:** Используем **Plane** ([plane.so](https://plane.so)) — open-source all-in-one платформу, которая заменяет Jira, Confluence и Airtable.

### 6.1. Docker Compose для Plane

Создайте файл `docker-compose-plane.yml`:

```yaml
version: '3.8'

services:
  plane-app:
    image: makeplane/plane:latest
    container_name: plane-app
    ports:
      - "8080:80"
    environment:
      - REDIS_URL=redis://plane-redis:6379/0
      - POSTGRES_URL=postgres://user:password@plane-db:5432/plane-db
      - NEXT_PUBLIC_API_BASE_URL=http://localhost:8080
      - NEXT_PUBLIC_SENTRY_DSN=
    depends_on:
      - plane-db
      - plane-redis

  plane-db:
    image: postgres:15-alpine
    container_name: plane-db
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=plane-db
    volumes:
      - plane-data:/var/lib/postgresql/data

  plane-redis:
    image: redis:7-alpine
    container_name: plane-redis

volumes:
  plane-data:
```

**Запуск:** `docker-compose -f docker-compose-plane.yml up -d`

### 6.2. Что куда из баз?

**Важно:** Plane **не подключается** к основной базе данных Newlookup (PostgreSQL). Это **полностью изолированная система** со своей собственной базой данных (`plane-db` в Docker-контейнере). Это сделано для безопасности и стабильности.

| Что делаем | Где делаем | Какая БД используется |
| :--- | :--- | :--- |
| **Разработка** (задачи, баги, спринты) | **Plane** | `plane-db` (внутренняя БД Plane) |
| **Просмотр данных Newlookup** (пользователи, заказы) | **Admin Panel** (наша, на React) | `newlookup_db` (основная БД проекта) |
| **Документация для разработчиков** | **Plane** (раздел Pages) | `plane-db` |
| **Техническое Задание (v21 и т.д.)** | **Plane** (раздел Pages) | `plane-db` |

**Итог:**
*   **Plane** — для управления командой и проектом.
*   **Admin Panel** — для управления данными и операциями в самом Newlookup.

Это стандартная и правильная практика разделения сред: среда для управления разработкой и среда для управления продуктом не должны пересекаться на уровне баз данных.
