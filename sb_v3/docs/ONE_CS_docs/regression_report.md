# CSBot Admin System Regression Report

**Author:** Manus AI  
**Date:** 2026-04-03

## Scope

Этот отчёт фиксирует **фактически подтверждённый регрессионный объём** проекта после адаптации под присланные материалы, расширения imported-format dataset harness, ручной проверки admin-разделов и исправления маршрутизации Metrics. Документ специально **не завышает** итоговый статус: наличие read-only интерфейса, маршрута или mock-данных не трактуется как подтверждённая production-ready готовность соответствующего доменного модуля.

## Regression Summary

| Область | Что именно проверено | Подтверждение | Статус |
| --- | --- | --- | --- |
| Imported-format parsing | Разбор нескольких структурных паттернов из полного пользовательского набора через обезличенную fixture-выборку | `server/importedLeadFormat.test.ts` | Pass |
| Safe PII reduction | Маскирование имён, телефонов и email-derived значений в safe-flow | parser/service tests | Pass |
| Safe preview backend flow | Preview summary и safe sample generation для imported dataset | `server/platformService.test.ts` | Pass |
| Safe batch backend flow | Формирование safe batch для downstream-safe flow | `server/platformService.test.ts` | Pass |
| REST preview/import | Safe preview/import endpoint-ы для того же адаптированного формата | `server/restApi.test.ts` | Pass |
| Imported-data admin UI | Loading/empty/error state и post-login сценарий preview → safe batch | `manual_imported_data_browser_regression.md` | Pass |
| Overview screen | Стабильный рендер overview-экрана после schema sync; подтверждён пользовательским скриншотом | пользовательский screenshot + `manual_admin_sections_regression.md` | Pass |
| Jobs / Proxy / Workers / Billing / Metrics / System | Отдельные read-only admin sections подтверждены вручную на live UI; empty/data-present paths подтверждены browser evidence и пользовательскими скриншотами | `manual_admin_sections_regression.md` | Pass |
| Metrics routing and page resolution | Устранены и 404 на `/metrics`, и ошибочный рендер Jobs-контента на Metrics-route | `client/src/pages/operations.routes.test.ts`, `client/src/App.tsx`, `client/src/pages/Operations.tsx` | Pass |
| Admin route structure | Выделены и подтверждены маршруты `/`, `/imported-data`, `/jobs`, `/proxy`, `/workers`, `/billing`, `/metrics`, `/telemetry`, `/system` | `client/src/App.tsx`, `client/src/pages/operations.routes.test.ts` | Pass |
| End-to-end platform readiness | Полная готовность proxy/workers/billing/telegram/telemetry как production modules | `todo.md`, compatibility matrix | Not covered |

## Full Test Run Result

Текущий полный прогон Vitest проходит успешно и уже включает **серверные и клиентские тесты маршрутизации**.

| Прогон | Результат |
| --- | --- |
| `pnpm test` | **32/32 tests passed** |
| `server/importedLeadFormat.test.ts` | 6/6 passed |
| `server/platformService.test.ts` | 8/8 passed |
| `server/restApi.test.ts` | 6/6 passed |
| `server/auth.logout.test.ts` | 1/1 passed |
| `client/src/pages/operations.routes.test.ts` | 3/3 passed |
| `client/src/pages/operations.sections.test.ts` | 8/8 passed |

## What Was Actually Adapted

| Модуль | Фактическое изменение |
| --- | --- |
| `shared/importedLeadFormat.ts` | Normalizer адаптирован под дополнительные реальные паттерны: альтернативные source headers, нестандартные имена, вариации address/age/date markers и uncertain markers. |
| `server/fixtures/importedLeadDataset.fixture.txt` | В репозиторий добавлена обезличенная fixture-выборка, отражающая реальные структурные паттерны полного пользовательского набора без хранения исходных чувствительных данных. |
| `server/platformService.ts` | Preview/safe-batch сценарии адаптированы под более широкий imported-format dataset. |
| `server/platformService.test.ts` | Backend-регрессия расширена с synthetic-примера до fixture-выборки, собранной из фактических паттернов пользовательского материала. |
| `server/restApi.test.ts` | REST-регрессия расширена на тот же dataset для safe preview/import endpoint-ов. |
| `client/src/pages/ImportedData.tsx` | Imported-data экран вынесен в отдельную страницу с самостоятельным операторским контуром. |
| `client/src/pages/Overview.tsx` | Добавлен отдельный обзорный экран админ-панели. |
| `client/src/pages/Operations.tsx` | Добавлены отдельные секции для Jobs, Proxy, Workers, Billing, Telemetry и System поверх существующих typed-query контрактов. |
| `client/src/App.tsx` | Маршруты разделены на overview, imported-data и operations-derived sections; `/metrics` зарегистрирован как отдельный admin route. |
| `client/src/pages/operations.routes.test.ts` | Добавлена автоматическая защита фикса для маршрута `/metrics` и его сопоставления telemetry-section. |
| `client/src/pages/operations.sections.test.ts` | Добавлены автоматические проверки loading/error/empty/data-present состояний для Jobs, Proxy, Workers, Billing, Metrics и System. |
| `vitest.config.ts` | Полный тестовый прогон расширен так, чтобы подхватывать и client-side тесты. |

## Findings And Deviations

| Наблюдение | Влияние | Текущее состояние | Практический вывод |
| --- | --- | --- | --- |
| Imported-format контур подтверждён уже не только на synthetic-примере | Positive | Fixture-coverage расширена | Адаптацию формата можно считать устойчивой в пределах уже выделенных паттернов |
| Manual browser regression теперь есть не только для `/imported-data` | Positive | Overview, Jobs, Proxy, Workers, Billing, Metrics и System подтверждены вручную | Расширенная админ-панель теперь подтверждена не только кодом и vitest |
| Пользовательский overview-скриншот соответствует manual matrix | Positive | Live overview UI визуально консистентен | Визуальное подтверждение совпадает с зафиксированным отчётом по разделам |
| В исторических логах встречается старый `telegramChatId` error | Bounded | Актуальные network/runtime данные уже возвращают `telegramChatId` без SQL failure | Это нужно трактовать как исторический след, а не как автоматически воспроизводимую текущую поломку |
| Большие доменные блоки платформы ещё не доведены до full production workflow | High for platform scope | Proxy/workers/billing/telegram/telemetry не закрыты end-to-end | Общий статус проекта остаётся частично подтверждённым, а не полностью завершённым |

## Confirmed Boundary Of Confidence

| Зона | Уровень уверенности | Основание |
| --- | --- | --- |
| Imported-format parsing и safe normalization | High | Расширенные unit/service tests на fixture-выборке |
| Safe preview / safe batch backend behavior | High | Backend tests + manual imported-data regression |
| REST safe preview/import | High | Выделенные REST tests |
| Imported-data operator UI flow | High | Post-login manual regression подтверждена |
| Overview screen | High | Manual matrix + пользовательский screenshot |
| Jobs/Proxy/Workers/Billing/Metrics/System UI state behavior | High | Route mapping, ручная проверка empty/data-present surface, live UI evidence и отдельные Vitest-проверки loading/error/empty/data-present состояний подтверждены; отдельный manual browser rerun именно loading/error paths пока не выполнялся |
| Metrics route stability | High | Исправление закреплено и в коде, и в route-тесте |
| Auth/user persistence path against current schema | Medium | Актуальные ответы runtime возвращают `telegramChatId`, но historical error trace остаётся в логах |
| Full platform production readiness | Low | Крупные operational modules не завершены |

## Residual Risks

| Риск | Почему остаётся | Следующий разумный шаг |
| --- | --- | --- |
| Overclaim risk | Уже есть большой объём подтверждённой admin-поверхности, но это не равно production workflows | В документации и итоговом статусе продолжать жёстко отделять read-only/admin surface от operational readiness |
| Telemetry / billing / workers depth risk | Эти блоки визуально подтверждены, но не прошли отдельные end-to-end operational сценарии | Расширять доменные integration tests и manual сценарии beyond UI render |
| Dataset expansion risk | В следующем пользовательском наборе могут появиться новые imported-format edge cases | Дозаливать новые паттерны в обезличенную fixture-выборку и повторять harness |
| Historical log confusion | Старые runtime errors могут создавать ложное впечатление о текущем падении | При следующем цикле очистить или явно отделить historical evidence от current-state evidence в отчётах |

## Current Conclusion

На текущем шаге можно честно утверждать следующее. **Система адаптирована и протестирована под расширенный imported-format поднабор**, а не только под единичный synthetic-пример. Safe normalization, backend preview/safe-batch, REST preview/import и post-login imported-data UI flow подтверждены тестами и ручной регрессией. Расширенная админ-панель с разделами Overview, Jobs, Proxy, Workers, Billing, Metrics и System также подтверждена на живом интерфейсе; пользовательские live-скриншоты дополнительно подтвердили empty/data-present surface по ключевым admin-разделам, а Metrics routing regression устранена и закреплена тестом.

При этом **весь проект нельзя считать полностью завершённым production-состоянием**. Read-only admin coverage, routing coverage и ручной UI regression ещё не означают, что proxy-layer, worker orchestration, billing/subscriptions, telemetry pipeline и Telegram-интеграция завершены end-to-end. Отдельно важно сохранять честную границу: loading/error состояния для Jobs, Proxy, Workers, Billing, Metrics и System сейчас надёжно закреплены Vitest-проверками, но не были отдельно форсированы и вручную перепроверены в браузере в рамках этого цикла.

Итоговый честный статус на этот момент — **стабильный и хорошо покрытый imported-data / safe-import поднабор плюс существенно лучше подтверждённая расширенная админ-панель с отдельным автоматическим покрытием UI-состояний и live-подтверждением empty/data-present surface**, но не полный production-grade rollout всей платформы.
