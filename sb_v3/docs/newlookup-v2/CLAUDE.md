# CLAUDE.md — newlookup-docs

## Цель проекта
Obsidian wiki-документация системы NewLookup. Каждый .md файл — отдельный модуль системы, связанный wiki-ссылками `[[...]]`.

## Правила
- Все файлы — Markdown для Obsidian
- Wiki-ссылки между документами: `[[Architecture]]`, `[[Seller Bot]]` и т.д.
- Русский язык
- Максимальная детализация: каждый файл, функция, класс, роут, FSM-состояние
- Структура из analysis: tree → описание → таблицы

## Источник данных
Весь контент берётся из `Folders/newlookup-analysis.md` (2586 строк) — полный аудит проекта.

## Файлы документации
- MOC.md — центральный хаб
- Architecture.md — стек, Main Bot, конфигурация
- Seller Bot.md — 45 файлов seller_bot/
- Support Bot.md — 51 файл support_bot/
- Web Panel.md — 204 файла web_panel/
- Mini App.md — 83 файла seller_mini_app_v2/
- Shared Services.md — 78 файлов shared/
- Lookup API.md — 3 файла lookup_api/
- DB Models.md — models.py + миграции
