#!/bin/bash
# ============================================
# NEWLOOKUP — Запуск всех ботов
# Запускать из папки проекта:
#   cd /Users/user/Desktop/прокты/newlookup
#   bash start_bots.sh
# ============================================

set -a
source .env
set +a

# Локальная БД (SQLite) вместо PostgreSQL
export DATABASE_URL="sqlite+aiosqlite:///./data/newlookup.db"
export TASKS_DATABASE_URL="sqlite+aiosqlite:///./data/tasks.db"
export MAIN_BOT_API_PORT=8080

LOG_DIR="./logs"
mkdir -p "$LOG_DIR"

# Убиваем старые процессы
echo "🔄 Останавливаем старые процессы..."
pkill -f "seller_bot.bot" 2>/dev/null
pkill -f "marketer_bot.bot" 2>/dev/null
pkill -f "support_bot.bot" 2>/dev/null
pkill -f "worker_bot.bot" 2>/dev/null
pkill -f "main_bot/run.py" 2>/dev/null
pkill -f "uvicorn web_panel" 2>/dev/null
lsof -ti :8080 | xargs kill -9 2>/dev/null
lsof -ti :8181 | xargs kill -9 2>/dev/null
lsof -ti :8000 | xargs kill -9 2>/dev/null
sleep 3

echo ""
echo "🚀 Запускаем всё..."

# Admin Panel (Web)
python3 -m uvicorn web_panel.main:app --host 0.0.0.0 --port 8000 > "$LOG_DIR/web_panel.log" 2>&1 &
echo "✅ Admin Panel   → http://localhost:8000  (PID: $!)"

sleep 2

# Seller Bot
python3 -m seller_bot.bot > "$LOG_DIR/seller_bot.log" 2>&1 &
echo "✅ Seller Bot     → @sdsvfsdbot           (PID: $!)"

# Marketer Bot
python3 -m marketer_bot.bot > "$LOG_DIR/marketer_bot.log" 2>&1 &
echo "✅ Marketer Bot   → @msacdskabot          (PID: $!)"

# Support Bot (Workers + Admins)
python3 -m support_bot.bot > "$LOG_DIR/support_bot.log" 2>&1 &
echo "✅ Support Bot    → Workers + Admins       (PID: $!)"

# Worker Bot (Worker-only interface + API on 8181)
python3 worker_bot/run.py > "$LOG_DIR/worker_bot.log" 2>&1 &
echo "✅ Worker Bot     → Workers API :8181      (PID: $!)"

# Main Bot + Mirror Bots (buyer bots)
python3 main_bot/run.py > "$LOG_DIR/main_bot.log" 2>&1 &
echo "✅ Main Bot       → @mainbodabot          (PID: $!)"

echo ""
echo "⏳ Ждём 10 секунд..."
sleep 10

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 СТАТУС БОТОВ:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

for bot in "seller_bot" "marketer_bot" "support_bot" "worker_bot" "main_bot"; do
    if grep -q "Run polling\|Start polling\|starting" "$LOG_DIR/${bot}.log" 2>/dev/null; then
        echo "  ✅ $bot — OK"
    else
        last=$(tail -1 "$LOG_DIR/${bot}.log" 2>/dev/null)
        echo "  ❌ $bot — $last"
    fi
done

echo ""
echo "🌐 Admin Panel: http://localhost:8000"
echo "🔑 Логин: см. ADMIN_USERNAME / ADMIN_PASSWORD в .env"
echo ""
echo "📋 Логи: $LOG_DIR/"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
