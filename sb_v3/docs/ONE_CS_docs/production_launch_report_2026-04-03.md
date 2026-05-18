# Production Launch Report — ONE CS

## Executive Summary

По состоянию на **2026-04-03 / 2026-04-04 CEST** новый контур **ONE CS** переведён в рабочий production-режим на сервере **193.221.200.87**. Публичные домены, ранее обслуживавшие legacy-контур, теперь проксируются через **nginx** на устойчивый экземпляр **ONE CS**, работающий под **systemd** на порту **3112**. Дополнительно сохранён ранее подтверждённый canary-контур на порту **3111**, что даёт быстрый локальный rollback-путь без немедленного пересборочного цикла.

Запуск выполнен в стабильностно-ориентированном режиме. Сначала был подтверждён здоровый canary на 3111, затем был создан устойчивый сервисный runtime через `onecs.service`, после чего реальные активные nginx vhost-файлы были переключены на 3112. После переключения были повторно проверены локальные upstream-ответы, публичный HTTP-контур и доменные virtual host-маршруты. Дополнительно локальный регрессионный набор проекта прошёл успешно: **51/51 тестов**.

## Final Production Topology

| Component | Final state | Notes |
|---|---:|---|
| Public reverse proxy | Active | nginx обслуживает внешний HTTP-контур |
| Active public upstream | `127.0.0.1:3112` | это текущий production runtime |
| Warm rollback upstream | `127.0.0.1:3111` | ранее подтверждённый healthy canary всё ещё доступен локально |
| Runtime manager | `systemd` | `onecs.service` закрепляет запуск нового контура |
| Legacy port | `3000` | исключён из активного nginx routing |
| Telegram bot service | Active separately | `csbot.service` продолжает работать отдельно |

## What Was Verified

| Check | Result | Evidence summary |
|---|---:|---|
| `onecs.service` запущен | Pass | активный systemd unit поднял Node runtime на 3112 |
| Порт 3112 слушает | Pass | локальный HTTP-ответ 200 от `127.0.0.1:3112` |
| Порт 3111 сохранён как резервный контур | Pass | canary продолжает отвечать 200 локально |
| nginx синтаксически корректен | Pass | `nginx -t` успешен перед reload |
| Активные доменные vhost-файлы переведены на 3112 | Pass | `sites-enabled/*` и `sites-available/*` синхронизированы на `proxy_pass http://127.0.0.1:3112;` |
| Публичный root через nginx отвечает | Pass | `HTTP/1.1 200 OK` от `http://127.0.0.1/` |
| Все production-домены отдают 200 | Pass | проверены `daisysms.click`, `codes`, `icu`, `rest`, `shop`, `space`, `store`, `top`, `us`, `vip` |
| Admin UI открывается | Pass | получен подтверждающий скриншот Overview после запуска |
| Controlled bootstrap доказан отдельным воспроизводимым контуром | Pass | из отдельного каталога `/opt/csbot_admin_system/bootstrap-proof-20260404-015245` собран и поднят независимый runtime на `3113`, получен `health_code=200` и лог `Server running on http://localhost:3113/` |
| Rollback drill реально выполнен | Pass | активные nginx vhost были временно переведены на `3111`, все 10 доменов отдали `200`, после чего upstream возвращён на `3112` и снова подтверждён код `200` по всем доменам |
| Critical flows и job queue на активном 3112 подтверждены | Pass | через REST API на `3112` созданы queued job и retry job; зафиксированы `worker.started`, `worker.completed`, `job.waiting_retry`, `worker.retried`, `job.completed`, финальные статусы `succeeded` |
| Локальный регрессионный набор проекта | Pass | `8` test files, `51` tests passed |

## Deployment Actions Actually Performed

| Step | Result |
|---|---|
| Подтверждён healthy canary ONE CS на `3111` | Выполнено |
| Выявлено, что активные домены обслуживаются отдельными nginx vhost-файлами в `sites-enabled`, а не только `default` | Выполнено |
| Создан `start-onecs.sh` с извлечённым рабочим окружением из healthy runtime | Выполнено |
| Создан и включён `onecs.service` для устойчивого запуска на `3112` | Выполнено |
| Сделан backup активных nginx vhost-файлов перед изменением | Выполнено |
| Активные домены переключены с `3111`/legacy-контура на `3112` | Выполнено |
| Выполнен `nginx -t` и `systemctl reload nginx` | Выполнено |
| Проведена постдеплой-проверка upstream, публичного root и всех доменов | Выполнено |
| Выполнен отдельный bootstrap-proof в новом каталоге с install/build/start на `3113` без влияния на production | Выполнено |
| Выполнен реальный rollback drill `3112 -> 3111 -> 3112` по всем активным доменам | Выполнено |
| Выполнена REST-проверка queued runtime и retry lifecycle именно на активном `3112` | Выполнено |
| Запущен локальный vitest-регресс проекта | Выполнено |

## Active Runtime and Rollback Artifacts

| Artifact | Location | Purpose |
|---|---|---|
| systemd unit | `/etc/systemd/system/onecs.service` | устойчивый запуск ONE CS |
| start script | `/opt/csbot_admin_system/app/start-onecs.sh` | экспорт рабочего env и запуск `node dist/index.js` |
| nginx backup | `/root/nginx-onecs-cutover-20260404-014824/` | быстрый возврат nginx-конфигов до финального cutover |
| previous default backup | `/etc/nginx/sites-available/default.onecs-backup-20260404-014639` | дополнительный backup служебного default-файла |
| warm rollback app | `127.0.0.1:3111` | локальный fallback-контур |
| active production app | `127.0.0.1:3112` | основной живой runtime |
| bootstrap proof app | `127.0.0.1:3113` | независимый доказательный runtime из отдельного deploy-каталога |
| active config audit | `/home/ubuntu/csbot_admin_system/audit/active_production_config_20260403_195209.log` | снимок systemd, портов, nginx upstream и start script |
| rollback drill audit | `/home/ubuntu/csbot_admin_system/audit/rollback_drill_20260403_195815.log` | журнал реального переключения `3112 -> 3111 -> 3112` |
| critical flows audit | `/home/ubuntu/csbot_admin_system/audit/critical_flows_3112_retry_20260403_200036.log` | журнал queued job и retry lifecycle на активном `3112` |

## Test Result Summary

| Scope | Result |
|---|---:|
| Test files | 8 passed |
| Individual tests | 51 passed |
| Duration | 4.37s |
| Key validated areas | platform service, REST API, imported-format flows, admin sections, routes, secrets validation, auth logout |

## Known Caveats and Honest Residual Risks

Текущий запуск можно считать **рабочим и доказательно подтверждённым для production HTTP-контура**, однако несколько честных замечаний всё ещё остаются. Во-первых, сохранённый canary на **3111** по-прежнему остаётся отдельным живым процессом, пригодным для быстрого rollback upstream, но не оформленным как второй такой же устойчивый service-managed контур. Во-вторых, bootstrap-proof на **3113** был выполнен как отдельный доказательный запуск и не предназначен для постоянной эксплуатации; его ценность в том, что он подтвердил воспроизводимость каталога деплоя, сборки и старта вне уже работающего production-процесса. В-третьих, rollback readiness теперь подтверждён не только документированным планом, но и реальным drill-переключением `3112 -> 3111 -> 3112` с сохранением ответов `200` по всем активным доменам. В-четвёртых, critical flows и job queue на активном `3112` подтверждены через реальные REST-вызовы queued runtime и retry lifecycle, однако это всё ещё адресная operational verification, а не широкий отдельный набор полноценных внешних end-to-end сценариев.

## Fast Rollback Procedure

Если после переключения будет замечена деградация, откат может быть выполнен быстро и без сложной пересборки. Рекомендуемый путь — сначала вернуть nginx upstream с `3112` на `3111`, потому что 3111 остаётся локально живым и уже ранее подтверждён как healthy контур. Если понадобится полный конфигурационный возврат, можно восстановить сохранённые vhost-файлы из каталога backup.

| Rollback level | Action | Expected effect |
|---|---|---|
| Level 1 | вернуть `proxy_pass` в активных nginx vhost с `3112` на `3111`, затем `nginx -t && systemctl reload nginx` | быстрый возврат на warm canary |
| Level 2 | восстановить файлы из `/root/nginx-onecs-cutover-20260404-014824/` | полный возврат nginx-конфигурации до финального cutover |
| Level 3 | при необходимости остановить `onecs.service` и держать трафик только на 3111 | изоляция нового устойчивого runtime |

## Current Status Statement

На текущем этапе можно честно зафиксировать следующее: **production HTTP-контур ONE CS успешно переключён и отвечает корректно**, **устойчивый runtime создан и активен через systemd на 3112**, **controlled bootstrap подтверждён независимым proof-контуром на 3113**, **rollback readiness подтверждён реальным drill-переключением `3112 -> 3111 -> 3112`**, **critical flows queued/retry подтверждены именно на активном runtime 3112**, **админ-интерфейс подтверждён визуально**, а **локальный регрессионный набор проекта проходит 51/51**. Практический следующий шаг уже вне обязательного cutover — либо перевести резервный 3111 в такой же service-managed контур, либо формально закрыть его и держать rollback только на уровне backup-конфигов и повторного запуска.
