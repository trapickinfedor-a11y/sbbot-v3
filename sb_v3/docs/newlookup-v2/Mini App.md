# Mini App

[[MOC]] > Mini App

**83 файла** | React 19 + TypeScript | Vite | `web_panel/seller_mini_app_v2/`

---

## Основные файлы

### client/src/App.tsx — 49 строк
### client/src/main.tsx — 5 строк

### client/src/pages/Home.tsx — 4 строки
### client/src/pages/NotFound.tsx — 49 строк
### client/src/pages/SellerApp.tsx — 219 строк

---

## Компоненты

### client/src/components/AppHeader.tsx — 215 строк
**State:** `useState` — showNotifs

### client/src/components/BottomNav.tsx — 100 строк

### client/src/components/ErrorBoundary.tsx — 62 строки
**Классы:** `ErrorBoundary extends Component<Props, State>`

### client/src/components/ManusDialog.tsx — 85 строк
**State:** `useState` — internalOpen

### client/src/components/Map.tsx — 155 строк
**API:** `${MAPS_PROXY_URL}/maps/api/js?key=${API_KEY}&v=weekly&libraries=marker,places,geocoding,geometry`

---

## Табы (основная логика)

### client/src/components/tabs/UploadsTab.tsx — 2100 строк
**State (useState):** q, cat, bankId, customBank, useCustom, productType, customProductType, regMm, regDd, regYyyy, ...
**API-вызовы:**
- `POST /api/seller-mini-app/uploads/submit` (5 вариантов)
- `POST /api/seller-mini-app/uploads/request-category` (3 вариантов)

### client/src/components/tabs/TeamTab.tsx — 594 строки
**State:** identifier, selectedRoles, loading, expanded, audit, auditLoading, editRoles, savingRoles, confirmRemove
**API:**
- `POST /api/seller-mini-app/team/add`
- `GET /api/seller-mini-app/team/helpers/{id}/audit`
- `PATCH /api/seller-mini-app/team/helpers/{id}/roles`
- `DELETE /api/seller-mini-app/team/helpers/{id}`
- `GET /api/seller-mini-app/team/helpers`

### client/src/components/tabs/OrdersTab.tsx — 574 строки
**State:** dispute, loading, replyText, sending, accepting, escalating, openingNew, newReason, showOpenForm
**API:**
- `GET /api/seller-mini-app/orders/${id}/dispute`
- `POST /api/seller-mini-app/orders/${id}/dispute/reply`
- `POST /api/seller-mini-app/orders/${id}/dispute/accept`
- `POST /api/seller-mini-app/orders/${id}/dispute/escalate`
- `POST /api/seller-mini-app/orders/${id}/dispute/open`
- `GET /api/seller-mini-app/orders?filter=${f}`

### client/src/components/tabs/AnalyticsTab.tsx — 546 строк
**State:** selectedYear, selectedMonth, preset, summary, funnel, abandoned, dailyData, loading, exporting
**API:**
- `api.analyticsSummary(date_from, date_to)`
- `api.analyticsFunnel(date_from, date_to)`
- `api.abandonedCarts(date_from, date_to)`
- `api.exportAnalyticsCSV(date_from, date_to)`

### client/src/components/tabs/SettingsTab.tsx — 336 строк
**State:** vacationLoading, autoPayoutLoading, quietFrom, quietTo, quietLoading
**API:**
- `api.setVacation(!seller.is_on_vacation, null)`
- `api.setAutoPayout(!seller.auto_payout_enabled)`
- `api.setQuietHours(quietFrom, quietTo)`

### client/src/components/tabs/ChatsTab.tsx — 318 строк
**State:** search, activeConvId, payload, loadingChat, mobileView, messageText, file, sending
**API:**
- `api.messages(id)`
- `api.send(fd)`

### client/src/components/tabs/FinanceTab.tsx — 267 строк
**State:** summary, loading, withdrawAmount, requisites, withdrawing, exporting
**API:**
- `api.financeSummary()`
- `api.withdraw(amount, requisites)`
- `api.financeExport()`

---

## Contexts

### client/src/contexts/AppContext.tsx — 262 строки
**State:** seller, conversations, activeTab, isLoading, error, isDemoMode
**API:** `api.me()`, `api.conversations()`, `api.orders("active")`

### client/src/contexts/ThemeContext.tsx — 64 строки
**State:** theme

---

## Hooks

| Файл | Строк |
|------|-------|
| client/src/hooks/useComposition.ts | 81 |
| client/src/hooks/useMobile.tsx | 21 |
| client/src/hooks/usePersistFn.ts | 20 |

---

## Lib

### client/src/lib/api.ts — 237 строк
**Base:** `/api/seller-mini-app`
**Методы:** me, conversations, messages, send, orders, financeSummary, withdraw, financeExport, analyticsSummary, analyticsFunnel, setVacation, setAutoPayout, setQuietHours, ...

### client/src/lib/mockData.ts — 265 строк
### client/src/lib/telegram.ts — 105 строк
### client/src/lib/utils.ts — 61 строка

---

## UI-компоненты (shadcn/ui)

| Компонент | Строк | Компонент | Строк |
|-----------|-------|-----------|-------|
| accordion.tsx | 64 | alert-dialog.tsx | 155 |
| alert.tsx | 66 | aspect-ratio.tsx | 9 |
| avatar.tsx | 51 | badge.tsx | 46 |
| breadcrumb.tsx | 109 | button-group.tsx | 83 |
| button.tsx | 60 | calendar.tsx | 211 |
| card.tsx | 92 | carousel.tsx | 239 |
| chart.tsx | 355 | checkbox.tsx | 30 |
| collapsible.tsx | 31 | command.tsx | 184 |
| context-menu.tsx | 250 | dialog.tsx | 208 |
| drawer.tsx | 133 | dropdown-menu.tsx | 255 |
| empty.tsx | 104 | field.tsx | 242 |
| form.tsx | 168 | hover-card.tsx | 42 |
| input-group.tsx | 168 | input-otp.tsx | 75 |
| input.tsx | 70 | item.tsx | 193 |
| kbd.tsx | 28 | label.tsx | 22 |
| menubar.tsx | 274 | navigation-menu.tsx | 168 |
| pagination.tsx | 127 | popover.tsx | 46 |
| progress.tsx | 29 | radio-group.tsx | 43 |
| resizable.tsx | 54 | scroll-area.tsx | 56 |
| select.tsx | 185 | separator.tsx | 26 |
| sheet.tsx | 139 | sidebar.tsx | 733 |
| skeleton.tsx | 13 | slider.tsx | 61 |
| sonner.tsx | 23 | spinner.tsx | 16 |
| switch.tsx | 29 | table.tsx | 114 |
| tabs.tsx | 64 | textarea.tsx | 67 |
| toggle-group.tsx | 73 | toggle.tsx | 45 |
| tooltip.tsx | 59 | | |

---

## Прочее

### client/src/const.ts — 17 строк
**API:** `${window.location.origin}/api/oauth/callback`

### server/index.ts — 33 строки
### shared/const.ts — 2 строки
### vite.config.ts — 189 строк

## Конфигурация

- Vite `base: "/seller-mini-app/"`
- wouter `<Router base="/seller-mini-app">`
- StaticFiles mount `/seller-mini-app/assets`
- Авторизация через Telegram `initData` → `_parse_and_verify_init_data` ([[Web Panel]])
