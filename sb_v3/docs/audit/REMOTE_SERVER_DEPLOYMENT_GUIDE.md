# Remote Server Deployment Guide for ONE CS

## Назначение документа

Этот документ описывает, как развернуть текущий проект **CSBot Admin System / ONE CS** на внешнем Linux-сервере пользователя. Он нужен для того, чтобы перенос на хост **193.221.200.87** выполнялся последовательно, без потери базы данных, без рассинхрона схемы и с понятным способом перезапуска сервиса.

Документ ориентирован на сценарий, где приложение запускается как **Node.js service** за **Nginx reverse proxy**, а база данных либо уже доступна по внешнему `DATABASE_URL`, либо подключается как отдельный managed/MySQL instance.

## Что должно быть готово до деплоя

Перед выкладкой нужно подтвердить несколько условий.

| Требование | Зачем это нужно |
|---|---|
| На сервере установлен Node.js 22+ | Проект использует современный runtime и `pnpm` |
| На сервере установлен `pnpm` | Для установки зависимостей и запуска build/start |
| Доступен `DATABASE_URL` | Backend и авторизация используют базу данных |
| Настроены OAuth/env переменные | Без них логин и системные интеграции работать не будут |
| Открыт порт приложения или настроен reverse proxy | Чтобы сайт был доступен извне |
| Есть каталог для приложения, например `/opt/csbot_admin_system` | Для чистого и повторяемого размещения файлов |

## Рекомендуемая структура на сервере

На удалённом сервере рекомендуется использовать следующую структуру каталогов.

| Путь | Назначение |
|---|---|
| `/opt/csbot_admin_system/app` | Код проекта |
| `/opt/csbot_admin_system/shared` | Общие артефакты деплоя, если понадобятся |
| `/opt/csbot_admin_system/logs` | Логи приложения |
| `/opt/csbot_admin_system/.env` | Переменные окружения для production |

## Production environment variables

Ниже перечислены ключевые переменные окружения, которые должны быть доступны приложению на сервере.

| Переменная | Обязательность | Назначение |
|---|---|---|
| `DATABASE_URL` | Да | Подключение к MySQL/TiDB |
| `JWT_SECRET` | Да | Подпись cookie и auth session |
| `VITE_APP_ID` | Да | OAuth application id |
| `OAUTH_SERVER_URL` | Да | Backend OAuth server |
| `VITE_OAUTH_PORTAL_URL` | Да | OAuth portal URL для frontend |
| `OWNER_OPEN_ID` | Да | Идентификатор владельца |
| `OWNER_NAME` | Да | Имя владельца |
| `BUILT_IN_FORGE_API_URL` | Да, если используются built-in integrations | Серверные интеграции платформы |
| `BUILT_IN_FORGE_API_KEY` | Да, если используются built-in integrations | Ключ built-in integrations |
| `VITE_FRONTEND_FORGE_API_URL` | По текущему шаблону | Клиентский доступ к platform APIs |
| `VITE_FRONTEND_FORGE_API_KEY` | По текущему шаблону | Клиентский доступ к platform APIs |
| `PORT` | Да | Порт backend-сервиса |
| `NODE_ENV` | Да | Production mode |

## Рекомендуемый `.env` шаблон

Ниже приведён безопасный шаблон, который нужно заполнить фактическими значениями.

```env
NODE_ENV=production
PORT=3000
DATABASE_URL=mysql://USER:PASSWORD@HOST:3306/DBNAME
JWT_SECRET=replace_with_strong_secret
VITE_APP_ID=replace_with_app_id
OAUTH_SERVER_URL=https://api.manus.im
VITE_OAUTH_PORTAL_URL=https://manus.im
OWNER_OPEN_ID=replace_with_owner_open_id
OWNER_NAME=replace_with_owner_name
BUILT_IN_FORGE_API_URL=replace_with_api_url
BUILT_IN_FORGE_API_KEY=replace_with_api_key
VITE_FRONTEND_FORGE_API_URL=replace_with_frontend_api_url
VITE_FRONTEND_FORGE_API_KEY=replace_with_frontend_api_key
```

## Порядок первого деплоя

Первый деплой лучше выполнять как отдельную, воспроизводимую последовательность действий. Это снижает риск смешения старых файлов и новой сборки.

### 1. Подготовка сервера

Нужно создать рабочие каталоги и убедиться, что у сервиса есть права на чтение и запись логов.

```bash
mkdir -p /opt/csbot_admin_system/app
mkdir -p /opt/csbot_admin_system/logs
```

### 2. Копирование проекта

Код проекта нужно передать на сервер в каталог `/opt/csbot_admin_system/app`. Это можно сделать через `scp`, `rsync` или архивом.

Пример с архивом:

```bash
cd /opt/csbot_admin_system
unzip csbot_admin_system.zip -d app
```

### 3. Установка зависимостей

После копирования проекта нужно установить зависимости.

```bash
cd /opt/csbot_admin_system/app
pnpm install --frozen-lockfile
```

### 4. Синхронизация схемы базы

Перед запуском сервиса обязательно нужно синхронизировать схему, особенно если на сервере уже есть старая таблица `users` без `telegramChatId` и `status`.

```bash
cd /opt/csbot_admin_system/app
node apply_schema_sync.mjs
```

Этот шаг обязателен, потому что в проект уже встроен non-destructive fix для устранения рассинхрона схемы по `users.telegramChatId` и `users.status`.

### 5. Сборка проекта

После синхронизации схемы нужно собрать production-версию.

```bash
cd /opt/csbot_admin_system/app
pnpm build
```

### 6. Smoke test

Перед systemd-запуском полезно вручную проверить, что приложение стартует.

```bash
cd /opt/csbot_admin_system/app
NODE_ENV=production PORT=3000 pnpm start
```

Если сервер запускается и отвечает, процесс можно остановить и перевести сервис под systemd.

## systemd service

Ниже приведён рекомендуемый unit-файл для systemd.

```ini
[Unit]
Description=CSBot Admin System
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/csbot_admin_system/app
EnvironmentFile=/opt/csbot_admin_system/.env
ExecStart=/usr/bin/env pnpm start
Restart=always
RestartSec=5
StandardOutput=append:/opt/csbot_admin_system/logs/app.log
StandardError=append:/opt/csbot_admin_system/logs/app-error.log
User=root

[Install]
WantedBy=multi-user.target
```

Файл нужно сохранить как:

```bash
/etc/systemd/system/csbot-admin.service
```

После этого применяются стандартные команды:

```bash
systemctl daemon-reload
systemctl enable csbot-admin
systemctl start csbot-admin
systemctl status csbot-admin
```

## Nginx reverse proxy

Если внешний доступ идёт через Nginx, можно использовать следующую базовую конфигурацию.

```nginx
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

Если домен уже настроен, вместо `_` нужно указать production domain. После этого конфигурацию нужно проверить и перезагрузить Nginx.

```bash
nginx -t
systemctl reload nginx
```

## Обновление существующей версии

При обновлении уже установленного проекта рекомендуется использовать один и тот же порядок действий.

| Шаг | Команда |
|---|---|
| Остановить сервис | `systemctl stop csbot-admin` |
| Обновить код | `rsync` / `scp` / распаковка архива |
| Установить зависимости | `pnpm install --frozen-lockfile` |
| Синхронизировать схему | `node apply_schema_sync.mjs` |
| Собрать проект | `pnpm build` |
| Запустить сервис | `systemctl start csbot-admin` |
| Проверить статус | `systemctl status csbot-admin` |

## Команды диагностики

Ниже приведены основные команды для production-поддержки.

| Задача | Команда |
|---|---|
| Проверить статус сервиса | `systemctl status csbot-admin` |
| Смотреть live-логи | `journalctl -u csbot-admin -f` |
| Смотреть файловые логи | `tail -f /opt/csbot_admin_system/logs/app.log` |
| Проверить порт | `ss -tulpn | grep 3000` |
| Проверить HTTP-ответ | `curl -I http://127.0.0.1:3000` |

## Что проверить после запуска

После production-запуска нужно вручную пройти минимальный smoke-check. Сначала следует открыть главную админ-панель и убедиться, что сайт отвечает. Затем нужно проверить логин, Overview, Imported Data и Jobs. После этого стоит убедиться, что новые поля **credit score**, **product score 1–20** и **data quality 1–10** видны в интерфейсе и не приводят к runtime-ошибкам.

## Production checklist для ONE CS

| Проверка | Ожидаемый результат |
|---|---|
| Приложение стартует без crash loop | systemd показывает `active (running)` |
| База подключается без `ER_BAD_FIELD_ERROR` | Ошибки по `telegramChatId` отсутствуют |
| Overview открывается | Панель загружается без белого экрана |
| Imported Data preview работает | Видны вычисленные поля ONE CS |
| Jobs / Operations открываются | Видны `creditScore`, `productScore`, `dataQualityScore`, `status`, `adverseReasons` |
| Тесты проекта проходили до деплоя | Локальный quality gate закрыт |

## Особое замечание по текущему состоянию проекта

В рамках текущей подготовки уже подтверждено, что локальный test-suite проходит, а схема базы может быть синхронизирована встроенным скриптом. Поэтому production-деплой должен выполняться именно через этот сценарий, а не через ручные ad-hoc изменения таблиц. Это снизит риск повторного появления ошибки `Unknown column 'telegramChatId'`.

## Короткий вывод

Для безопасного поднятия ONE CS на внешнем сервере нужно сделать четыре обязательных шага: передать код, установить зависимости, выполнить `apply_schema_sync.mjs`, затем собрать и запустить сервис под systemd. После этого нужно отдельно проверить интерфейсы Overview, Imported Data и Jobs, потому что именно в них отображается новый итоговый контракт ONE CS с `productScore 1–20` и `dataQualityScore 1–10`.
