#!/bin/bash
# Скрипт запуска Web Panel Admin

set -e

echo "╔════════════════════════════════════════════════════════╗"
echo "║        🖥️  Web Panel Admin - Запуск                   ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

cd /Users/user/Desktop/прокты/newlookup

# Проверка Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не найден! Установите Docker Desktop"
    exit 1
fi

echo "✅ Docker найден"

# Проверка docker-compose
if command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
elif docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
else
    echo "❌ docker-compose не найден!"
    exit 1
fi

echo "✅ $COMPOSE_CMD найден"
echo ""

# Остановка старых контейнеров
echo "⏹️  Остановка старых контейнеров..."
$COMPOSE_CMD down web_panel 2>/dev/null || true

# Запуск сервисов
echo "🚀 Запуск сервисов (postgres, redis, web_panel)..."
$COMPOSE_CMD up -d postgres redis web_panel

echo ""
echo "⏳ Ожидание запуска (30 секунд)..."
sleep 30

# Проверка статуса
echo ""
echo "📊 Статус сервисов:"
$COMPOSE_CMD ps

echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║  ✅ Web Panel Admin запущена!                         ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""
echo "🌐 Откройте в браузере:"
echo "   👉 http://localhost:8000 👈"
echo ""
echo "🔐 Логин:"
echo "   Username: admin"
echo "   Password: (из вашего .env файла)"
echo ""
echo "📚 API Docs: http://localhost:8000/docs"
echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║  Для остановки: $COMPOSE_CMD down web_panel             ║"
echo "║  Для логов: $COMPOSE_CMD logs -f web_panel              ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

# Предложение открыть браузер
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "🌐 Открытие браузера..."
    open http://localhost:8000
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "🌐 Открытие браузера..."
    xdg-open http://localhost:8000 2>/dev/null || echo "Откройте вручную: http://localhost:8000"
else
    echo "🌐 Откройте браузер и перейдите на: http://localhost:8000"
fi

echo ""
echo "✅ Готово!"
