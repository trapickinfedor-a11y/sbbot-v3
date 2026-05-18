# NewLookup v2 — Handoff для следующей сессии

## Что сделано
- **8 агентов реализованы**, все ветки смержены в `feat/v2`
- **Seller Bot** (seller_bot/): онбординг, daily reports, notifications, buy_access, add_seller — 6 коммитов, +1008 строк
- **Mini App** (web_panel/seller_mini_app_v2/): ModerationStatusTab, uploadInstructions, ChatsTab dispute, OrdersTab detail, FinanceTab balance+history, AnalyticsTab comparison, BottomNav 8 табов — 3 коммита
- **Admin Panel**: Referrals, Broadcasts, RBAC, Service Config — всё работает
- **dist пересобран** (index-C1RjjS6x.js, 16:52 сегодня)
- Сервер запущен на :8000 без --reload

## Что ещё нужно проверить
- Mini App показывает 5 табов вместо 8 — возможно BottomNav фильтрует табы по роли/авторизации
  - Код содержит все 8 табов (подтверждено grep)
  - Проверить: `web_panel/seller_mini_app_v2/client/src/components/BottomNav.tsx` — есть ли условная фильтрация NAV_ITEMS
  - Проверить: `web_panel/seller_mini_app_v2/client/src/contexts/AppContext.tsx` — начальный activeTab и доступные табы

## Ключевые пути
- Проект: /Users/user/Desktop/Проекты/newlookup
- Mini App src: web_panel/seller_mini_app_v2/client/src/
- Mini App dist: web_panel/seller_mini_app_v2/dist/
- Ветка: feat/v2
- Документация: Folders/newlookup-docs/
- Описание на рабочем столе: /Users/user/Desktop/NewLookup-Full-Description.md
