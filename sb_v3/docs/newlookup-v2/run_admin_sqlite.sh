#!/bin/bash
# Запуск Web Panel Admin на SQLite (мини-база)

set -e

echo "╔════════════════════════════════════════════════════════╗"
echo "║     🖥️  Web Panel Admin - SQLite Version              ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

cd /Users/user/Desktop/прокты/newlookup

# Создаем тестовый .env для SQLite
cat > .env.sqlite << 'EOF'
# SQLite Version (мини-база)
DATABASE_URL=sqlite+aiosqlite:///./data/newlookup.db
WEB_PANEL_PORT=8000
WEB_PANEL_SECRET_KEY=test-secret-key-12345
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
ADMIN_IDS=5611930487
EOF

echo "✅ Создали .env.sqlite"
echo ""

# Проверяем наличие data директории
mkdir -p ./data
echo "✅ Создали директорию ./data"
echo ""

# Запускаем Web Panel напрямую (без Docker)
echo "🚀 Запуск Web Panel на SQLite..."
echo ""

# Экспортируем переменные
export DATABASE_URL="sqlite+aiosqlite:///./data/newlookup.db"
export WEB_PANEL_PORT=8000
export WEB_PANEL_SECRET_KEY="test-secret-key-12345"
export ADMIN_USERNAME=admin
export ADMIN_PASSWORD=admin123
export ADMIN_IDS=5611930487

# Запускаем Python
cd web_panel
python3 run.py &

echo ""
echo "⏳ Ожидание запуска (5 секунд)..."
sleep 5

echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║  ✅ Web Panel запущена на SQLite!                     ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""
echo "🌐 Откройте в браузере:"
echo "   👉 http://localhost:8000 👈"
echo ""
echo "🔐 Логин:"
echo "   Username: admin"
echo "   Password: admin123"
echo ""
echo "📚 API Docs: http://localhost:8000/docs"
echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║  Для остановки: Ctrl+C                                 ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

# Открываем браузер
if [[ "$OSTYPE" == "darwin"* ]]; then
    open http://localhost:8000
fi

# Держим процесс
wait
