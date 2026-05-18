# CSBot Admin System Manual Admin Sections Regression

**Author:** Manus AI  
**Date:** 2026-04-03

## Scope

Этот документ фиксирует **ручную браузерную проверку** расширенной админ-панели после синхронизации schema drift по `users.telegramChatId`, исправления маршрутизации Metrics и адаптации overview/jobs/proxy/workers/billing/system-поверхности под уже реализованные backend-модули. Документ намеренно отделяет **ручные подтверждения на live UI** от автоматических Vitest-проверок: loading/error состояния для operations-секций теперь дополнительно закреплены автотестами, но в этой матрице отражается именно то, что было подтверждено вручную на интерфейсе.

## Manual Scenario Matrix

| Section | Route | Manually confirmed path | UI evidence | Status |
| --- | --- | --- | --- | --- |
| Overview | `/` | Data-present read-only surface: sidebar, boundary card, KPI cards, queue health, provider health, system snapshot | Пользовательский overview screenshot после schema sync + повторное визуальное подтверждение, включая актуальный live-скриншот с KPI и health-блоками | Pass |
| Jobs | `/jobs` | Empty-state path: отображаются boundary-блок, module status cards и таблица без записей с `No jobs available` | User-provided live screenshot of `/jobs` with indexed sidebar navigation + browser/manual navigation snapshot | Pass |
| Proxy | `/proxy` | Empty-state path: отображаются read-only boundary и пустое состояние `Proxy module is empty` без layout breakdown | User-provided live screenshot of `/proxy` with indexed sidebar navigation + browser/manual navigation snapshot | Pass |
| Workers | `/workers` | Data-present path: отображаются worker nodes, queue posture и recommendations | User-provided live screenshot of `/workers` with indexed sidebar navigation + browser/manual navigation snapshot | Pass |
| Billing | `/billing` | Data-present path: отображаются plans/subscriptions, payments/API keys и usage economics | User-provided live screenshot of `/billing` with indexed sidebar navigation + browser/manual navigation snapshot | Pass |
| Metrics | `/metrics` | Mixed path: telemetry counters и health cards присутствуют, audit trail подтверждён через empty-state `No telemetry audit yet`; ранее воспроизводившиеся 404 и wrong-module selection больше не наблюдаются | User-provided live screenshot of `/metrics` with indexed sidebar navigation + browser/manual navigation snapshot after routing fix | Pass |
| System | `/system` | Data-present path: отображаются safe test scenarios и stabilization checklist | User-provided live screenshot of `/system` with indexed sidebar navigation + browser/manual navigation snapshot | Pass |

## Manual Findings

| Observation | Interpretation |
| --- | --- |
| Overview стабильно рендерится и повторно подтверждён пользовательскими скриншотами | Визуальная регрессия overview после schema sync на текущем шаге не воспроизводится; дополнительный live-скриншот показывает boundary card, KPI `Success Rate 98.4%`, `Queue Depth 12`, `Proxy COGS $184.42`, `Transport Errors 7`, queue health по default/bulk/vip и provider health |
| Jobs empty-state дополнительно подтверждён live-скриншотом пользователя с маршрута `/jobs` | На текущем шаге явно видны `Jobs loaded 0`, `Running 0`, `Waiting retry 0` и текст `No jobs available`, значит раздел корректно остаётся в safe read-only empty path |
| Jobs и Proxy подтверждены по empty-state paths | Эти разделы сейчас корректно показывают безопасные пустые состояния вместо 404 или layout failure; для Proxy дополнительно видны `Providers 0`, `Policies 0`, `Health status healthy` и текст `Proxy module is empty` на live-скриншоте |
| Workers дополнительно подтверждён live-скриншотом пользователя с маршрута `/workers` | На текущем шаге явно видны `Workers 0`, `Healthy 2`, `Busy 0`, queue posture по default/bulk/vip и операторские recommendations, значит data-present read-only surface рендерится стабильно |
| Billing дополнительно подтверждён live-скриншотом пользователя с маршрута `/billing` | На текущем шаге явно видны `Plans 0`, `Subscriptions 0`, `Payments 0`, а также usage economics с `Requests 6240`, `Browser runs 980`, `Revenue $622.15` и `Margin $437.73`, значит data-present/read-only billing surface рендерится стабильно |
| System дополнительно подтверждён live-скриншотом пользователя с маршрута `/system` | На текущем шаге явно видны `Platform status healthy`, `Safe scenarios 3`, `Checklist items 4`, три safe test scenarios и stabilization checklist из четырёх пунктов, значит system read-only surface рендерится стабильно |
| Workers, Billing и System подтверждены по data-present read-only surface | Витрина реализованных модулей отображается стабильно и визуально консистентно |
| Metrics вручную подтверждён после исправления route mapping и `resolvePageKey` | Регрессия `/metrics` локализована и закрыта: ни 404, ни рендер Jobs-контента больше не наблюдаются; live-скриншот дополнительно показывает `Success rate 0.0%`, `Retry rate 0.0%`, `Audit events 0`, `Platform status healthy`, `Workers healthy 2` и empty-state `No telemetry audit yet` |

## Relationship To Automated Coverage

Ручная проверка выше подтверждает, что основные admin sections **визуально доступны и рендерятся корректно** на live UI. Отдельно от этого, автоматические проверки в `client/src/pages/operations.sections.test.ts` покрывают **loading, error, empty и data-present состояния** для Jobs, Proxy, Workers, Billing, Metrics и System. Поэтому совокупное основание теперь выглядит так: ручная матрица подтверждает реальную интерфейсную доступность разделов, а Vitest закрепляет предсказуемое поведение их ключевых состояний.

## Remaining Manual Gap

| Area | Current state | What is still needed |
| --- | --- | --- |
| Jobs / Proxy / Workers / Billing / Metrics / System loading paths | Подтверждены автоматическими тестами, но не отдельным ручным прогоном | Нужен ручной сценарий с явным ожиданием loading-banner и фиксацией текста состояния |
| Jobs / Proxy / Workers / Billing / Metrics / System error paths | Подтверждены автоматическими тестами, но не отдельным ручным прогоном | Нужен ручной сценарий с воспроизведением query-error и фиксацией error-alert текста |

## Boundary

Эта матрица **не означает**, что proxy provider execution, worker orchestration, billing lifecycle, telemetry pipeline или Telegram-интеграция завершены end-to-end. Она подтверждает только то, что текущая расширенная read-only/admin-поверхность работает стабильно и соответствует задокументированному объёму реализованных модулей.
