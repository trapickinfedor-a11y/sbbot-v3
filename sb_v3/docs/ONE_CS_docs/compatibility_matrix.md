# CSBot Admin System Compatibility Matrix

**Author:** Manus AI  
**Date:** 2026-04-03

## Scope

Этот документ фиксирует **фактически подтверждённое покрытие** по проекту на текущем шаге. Матрица специально отделяет три уровня состояния: реально подтверждённые safe/imported-data и admin UI сценарии; кодово существующие, но ещё не доведённые до production-workflow модули; а также пробелы, которые нельзя считать закрытыми только потому, что есть маршрут, read-only экран или mock-данные.

## Compatibility Matrix

| Модуль / область | Что именно проверено | Подтверждение | Текущий статус | Граница уверенности |
| --- | --- | --- | --- | --- |
| Imported-format normalizer | Разбор нескольких паттернов из полного пользовательского набора через обезличенную fixture-выборку | `shared/importedLeadFormat.ts`, `server/importedLeadFormat.test.ts`, `server/fixtures/importedLeadDataset.fixture.txt` | Pass | Высокая уверенность в пределах уже выделенных паттернов |
| Safe redaction / PII reduction | Маскирование имён, телефонов, email-derived значений и исключение чувствительных данных из safe-flow | parser/service tests | Pass | Высокая |
| Safe preview backend | Формирование preview summary и safe sample records по imported dataset | `server/platformService.test.ts` | Pass | Высокая |
| Safe batch backend | Создание safe batch для downstream-safe flow | `server/platformService.test.ts` | Pass | Высокая |
| REST safe preview/import | Безопасные REST endpoint-ы preview/import для того же адаптированного формата | `server/restApi.test.ts` | Pass | Высокая |
| Imported Data UI | Loading/empty/error состояния, post-login preview → safe batch flow | `manual_imported_data_browser_regression.md` | Pass | Высокая |
| Overview route | Read-only overview screen, sidebar, KPI cards и health blocks | `manual_admin_sections_regression.md` | Pass | Средне-высокая |
| Jobs route | Отдельный маршрут `/jobs`, empty-state path и read-only boundary | `manual_admin_sections_regression.md` | Pass | Средне-высокая |
| Proxy route | Отдельный маршрут `/proxy`, empty-state path и read-only boundary | `manual_admin_sections_regression.md` | Pass | Средне-высокая |
| Workers route | Отдельный маршрут `/workers`, data-present read-only surface, table и recommendations | `manual_admin_sections_regression.md` | Pass | Средне-высокая |
| Billing route | Отдельный маршрут `/billing`, read-only billing surface и usage economics | `manual_admin_sections_regression.md` | Pass | Средне-высокая |
| Metrics route | Маршрут `/metrics`, telemetry KPI/health counters, audit empty-state; исправлены 404 и wrong-module selection | `manual_admin_sections_regression.md`, `client/src/pages/operations.routes.test.ts`, `client/src/App.tsx`, `client/src/pages/Operations.tsx` | Pass | Средне-высокая |
| System route | Отдельный маршрут `/system`, status cards, safe scenarios и stabilization checklist | `manual_admin_sections_regression.md` | Pass | Средне-высокая |
| Admin route map | Раздельные маршруты `/`, `/imported-data`, `/jobs`, `/proxy`, `/workers`, `/billing`, `/metrics`, `/telemetry`, `/system` | `client/src/App.tsx`, `client/src/pages/operations.routes.test.ts` | Pass | Высокая |
| Operations section selection | Соответствие маршрутов нужным доменным секциям, включая `resolvePageKey('/metrics') === 'telemetry'` | `client/src/pages/operations.routes.test.ts`, `client/src/pages/Operations.tsx` | Pass | Высокая |
| Operations section UI states | Loading, error, empty и data-present состояния для Jobs, Proxy, Workers, Billing, Metrics и System закреплены отдельными Vitest-проверками; отдельный live manual rerun именно loading/error paths пока не выполнен | `client/src/pages/operations.sections.test.ts`, `client/src/pages/Operations.tsx` | Pass | Высокая для automated coverage, средняя для live confirmation |
| DB schema sync for auth/user path | Закрытие drift по `users.telegramChatId` и повторная auth/user regression на актуальной схеме | schema sync + повторная проверка состояния проекта + `todo.md` | Pass | Средняя |
| Full test suite | Полный прогон Vitest после фиксов imported-format, admin-routing и section-state coverage | `pnpm test` | Pass | Высокая |
| Proxy provider workflow | Реальные provider adapters, sticky/rotating routing, fallback и traffic accounting | backlog + текущее состояние кода | Partial | Есть admin/read-only surface, но нет подтверждённого production workflow |
| Worker execution workflow | Полноценный worker pool, retries, dispatch и failure recovery | backlog + текущее состояние кода | Partial | Есть UI/backend basis, но не подтверждён end-to-end production контур |
| Billing / subscriptions workflow | Полный платёжный и metering lifecycle, а не только read-only admin surface | backlog + текущее состояние кода | Partial | Read-only surface подтверждён, production billing lifecycle нет |
| Telemetry / audit production workflow | Полный operational telemetry pipeline, а не только metrics screen | backlog + текущее состояние кода | Partial | Metrics UI подтверждён, production-grade monitoring coverage ограничен |
| Telegram integration | Реальные уведомления и пользовательские сценарии Telegram | backlog | Not covered | Не подтверждено в этом цикле |
| Full platform production readiness | Полная готовность всей платформы как production system | сводный статус | Not covered | Текущий цикл этого не доказывает |

## Manual Coverage Per Admin Section

| Раздел | Маршрут | Что подтверждено вручную | Статус |
| --- | --- | --- | --- |
| Overview | `/` | Стабильный read-only overview surface: sidebar, KPI и health blocks | Pass |
| Imported Data | `/imported-data` | Preview, summary и safe batch flow | Pass |
| Jobs | `/jobs` | Empty-state path и read-only boundary | Pass |
| Proxy | `/proxy` | Empty-state path и read-only boundary | Pass |
| Workers | `/workers` | Data-present table, state cards и recommendations | Pass |
| Billing | `/billing` | Data-present billing surface и usage economics | Pass |
| Metrics | `/metrics` | Telemetry screen после фикса routing и module selection | Pass |
| System | `/system` | Read-only system surface и stabilization checklist | Pass |

## Automated Coverage Snapshot

| Набор тестов | Результат |
| --- | --- |
| `pnpm test` | **32/32 tests passed** |
| `server/importedLeadFormat.test.ts` | 6/6 passed |
| `server/platformService.test.ts` | 8/8 passed |
| `server/restApi.test.ts` | 6/6 passed |
| `server/auth.logout.test.ts` | 1/1 passed |
| `client/src/pages/operations.routes.test.ts` | 3/3 passed |
| `client/src/pages/operations.sections.test.ts` | 8/8 passed |

## Confirmed Fixes In This Cycle

| Исправление | Что было подтверждено | Статус |
| --- | --- | --- |
| Imported-format adaptation | Система адаптирована под расширенный обезличенный dataset, а не только под synthetic-пример | Fixed and covered |
| Safe preview / safe batch operator flow | Полный post-login flow подтверждён вручную | Fixed and covered |
| DB schema drift | Drift по `users.telegramChatId` закрыт, auth/user regression повторно прогнана | Fixed and revalidated |
| Metrics routing | Убран 404 на `/metrics` | Fixed and covered |
| Metrics module selection | `/metrics` больше не рендерит Jobs-контент, а выбирает telemetry section | Fixed and covered |

## Remaining Boundaries

| Область | Почему нельзя завышать готовность |
| --- | --- |
| Proxy layer | Подтверждён admin/read-only surface, но не production-grade provider execution |
| Workers | Подтверждён UI и часть backend basis, но не полный live operational workflow |
| Billing / subscriptions | Подтверждён read-only admin surface, но не end-to-end billing lifecycle |
| Telemetry / audit | Подтверждён metrics UI, но не весь production monitoring pipeline |
| Telegram | Не подтверждён в этом цикле |
| Manual loading/error admin paths | Empty/data-present состояния подтверждены live/manual evidence, но loading/error состояния по Jobs, Proxy, Workers, Billing, Metrics и System отдельно в браузере не форсировались в этом цикле | 
| Whole platform | Нельзя трактовать текущий результат как полный production rollout всей системы |

## Current Honest Status

На текущем шаге **надёжно подтверждены** следующие зоны: expanded imported-format dataset, safe preview/safe-batch, REST safe preview/import, imported-data UI flow, отдельные маршруты overview/jobs/proxy/workers/billing/metrics/system, ручная live-проверка empty/data-present surface этих admin-разделов по browser evidence и пользовательским скриншотам, автоматическое покрытие loading/error/empty/data-present состояний для operations-секций, исправление Metrics regression и успешный прогон **32/32 тестов**.

При этом **вся платформа целиком не считается production-ready**. Для proxy/workers/billing/telemetry/telegram по-прежнему нужны отдельные operational и end-to-end сценарии beyond read-only admin surface. Кроме того, manual coverage по admin-разделам сейчас честно ограничивается live-подтверждением empty/data-present paths: loading/error состояния закреплены автотестами, но не были отдельно форсированы и вручную перепроверены в браузере в рамках этого цикла.
