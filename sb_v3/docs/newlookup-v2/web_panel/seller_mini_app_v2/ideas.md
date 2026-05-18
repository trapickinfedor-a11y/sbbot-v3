# Seller Hub Mini App v2 — Design Ideas

## Context
Telegram Mini App для продавцов (sellers) в экосистеме NewLookup. Работает внутри Telegram WebApp, тёмная тема обязательна, мобильный формат (375–430px ширина). Основные задачи: управление чатами с покупателями, заказами, загрузка товаров, аналитика, финансы.

---

<response>
<text>

## Идея 1: Terminal Noir

**Design Movement:** Cyberpunk Terminal / Dark Hacker Aesthetic

**Core Principles:**
1. Monochromatic dark base с единственным неоновым акцентом (cyan #00E5FF)
2. Моноширинный шрифт для данных, sans-serif для навигации
3. Острые углы, тонкие линии, минимум декора
4. Данные — главный визуальный элемент

**Color Philosophy:** Почти чёрный фон (#0A0E13), тёмно-серые карточки (#111820), единственный акцент — электрический cyan. Ощущение профессионального инструмента, не потребительского приложения.

**Layout Paradigm:** Левая колонка — навигация-иконки (icon rail), правая — контент. На мобильном — bottom tab bar с иконками без подписей.

**Signature Elements:**
- Scan-line эффект на header (subtle CSS animation)
- Пульсирующие точки статуса (online/offline)
- Числа с моноширинным шрифтом (JetBrains Mono)

**Interaction Philosophy:** Мгновенный отклик, нет анимаций перехода — только fade 80ms. Данные появляются без задержки.

**Animation:** Только opacity transitions (80ms). Никаких slide/bounce.

**Typography System:** JetBrains Mono для цифр и кодов, Inter для UI текста.

</text>
<probability>0.07</probability>
</response>

---

<response>
<text>

## Идея 2: Obsidian Glass — ВЫБРАННАЯ

**Design Movement:** Glassmorphism + Material You Dark

**Core Principles:**
1. Многослойная глубина через backdrop-blur и полупрозрачные поверхности
2. Telegram-native цвета с расширенной палитрой акцентов
3. Плавные микроанимации (spring physics)
4. Информационная иерархия через цвет и размер, не через линии

**Color Philosophy:** Базовый фон — глубокий navy-black (#0D1117). Карточки — rgba(255,255,255,0.04) с blur(20px). Акцент — electric blue (#3B82F6) с cyan-teal (#06B6D4) для вторичных элементов. Статусы: emerald для успеха, amber для предупреждений, rose для ошибок. Палитра создаёт ощущение профессионального финансового инструмента.

**Layout Paradigm:** Полноэкранный мобильный layout. Фиксированный header (56px) + bottom tab bar (64px + safe area). Контент между ними — scrollable. Карточки с rounded-2xl, subtle border rgba(255,255,255,0.08).

**Signature Elements:**
- Gradient avatar с инициалами (синий → cyan)
- Status indicator с анимированным glow
- Числа с tabular-nums для выравнивания

**Interaction Philosophy:** Spring animations на tab switch (framer-motion). Haptic feedback через Telegram.HapticFeedback. Swipe gestures на мобильном.

**Animation:** Tab transitions — slide + fade (200ms spring). Cards — stagger появление (50ms delay). Числа — count-up animation при первой загрузке.

**Typography System:** Geist Sans (или system-ui) для UI, Geist Mono для цифр и кодов. Размеры: 11px labels, 14px body, 17px titles, 24px big numbers.

</text>
<probability>0.09</probability>
</response>

---

<response>
<text>

## Идея 3: Midnight Dashboard

**Design Movement:** Premium SaaS Dark Dashboard

**Core Principles:**
1. Строгая сетка, чёткие секции
2. Высокий контраст текста (WCAG AA)
3. Цветовое кодирование статусов
4. Компактность — максимум данных на экране

**Color Philosophy:** Slate-900 фон, slate-800 карточки, violet-500 акцент. Классическая enterprise палитра.

**Layout Paradigm:** Стандартный bottom navigation, section headers с dividers.

**Signature Elements:** Status badges, progress bars, data tables.

**Interaction Philosophy:** Стандартные transitions, без излишеств.

**Animation:** Minimal — только opacity.

**Typography System:** Inter everywhere, разные веса.

</text>
<probability>0.04</probability>
</response>

---

## Выбор: **Идея 2 — Obsidian Glass**

Glassmorphism + Material You Dark лучше всего подходит для Telegram Mini App:
- Органично вписывается в тёмную тему Telegram
- Создаёт ощущение premium инструмента
- Spring animations дают нативное мобильное ощущение
- Backdrop-blur карточки добавляют глубину без перегруза
