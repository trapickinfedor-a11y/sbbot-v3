#!/usr/bin/env bash
# SBBot v3 Deploy Script
# Usage: ./deploy.sh [start|stop|restart|status|logs|shell]
set -euo pipefail

NAME="sbbot-v3"
BOT_DIR="$(cd "$(dirname "$0")/.." && pwd)/core"
DATA_DIR="$BOT_DIR/data"
LOG_FILE="$BOT_DIR/logs/bot.log"
COMPOSE_FILE="$BOT_DIR/docker-compose.yml"
OVERRIDE="$BOT_DIR/docker-compose.override.yml"

# Colors
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

need_env() {
    if [[ ! -f "$BOT_DIR/.env" ]]; then
        echo -e "${RED}ERROR: .env not found. Copy .env.example and fill in values.${NC}"
        exit 1
    fi
}

cmd_start() {
    need_env
    echo -e "${GREEN}Starting $NAME...${NC}"
    mkdir -p "$DATA_DIR" "$BOT_DIR/logs"
    cd "$BOT_DIR"
    if [[ -f docker-compose.yml ]] || [[ -f docker-compose.override.yml ]]; then
        docker compose up -d --build
    else
        echo -e "${YELLOW}No docker-compose found. Starting bare process...${NC}"
        source "$BOT_DIR/.env"
        exec python3 bot.py
    fi
}

cmd_stop() {
    echo -e "${YELLOW}Stopping $NAME...${NC}"
    cd "$BOT_DIR" && docker compose down 2>/dev/null || pkill -f "python.*bot.py" 2>/dev/null || true
}

cmd_restart() {
    cmd_stop
    sleep 2
    cmd_start
}

cmd_status() {
    cd "$BOT_DIR"
    if docker compose ps 2>/dev/null | grep -q "$NAME"; then
        echo -e "${GREEN}✓ Container running${NC}"
        docker compose ps
    elif pgrep -f "python.*bot.py" > /dev/null; then
        echo -e "${GREEN}✓ Process running${NC}"
        pgrep -fa "python.*bot.py"
    else
        echo -e "${RED}✗ Not running${NC}"
    fi
}

cmd_logs() {
    if [[ -f "$LOG_FILE" ]]; then
        tail -n 50 "$LOG_FILE"
    else
        echo -e "${YELLOW}No log file yet${NC}"
    fi
}

cmd_shell() {
    cd "$BOT_DIR"
    docker compose exec bot bash 2>/dev/null || bash
}

cmd_migrate() {
    need_env
    echo "Running DB migrations..."
    docker compose exec bot python3 -c "
import asyncio, database as db
asyncio.run(db.init_db())
print('DB OK')
" 2>/dev/null || python3 -c "
import asyncio, sys; sys.path.insert(0, '$BOT_DIR')
import database as db
asyncio.run(db.init_db())
print('DB OK')
"
}

cmd_test() {
    echo -e "${GREEN}Running tests...${NC}"
    cd "$BOT_DIR"
    python3 -m pytest tests/ -v --tb=short
}

cmd_admin() {
    echo -e "${GREEN}Starting admin panel on port 3111...${NC}"
    cd "$BOT_DIR"
    ADMIN_SECRET="${ADMIN_SECRET:-admin-secret}" \
    ADMIN_USER_IDS="${ADMIN_USER_IDS:-}" \
    python3 -m uvicorn admin_panel:app --host 0.0.0.0 --port 3111
}

cmd_full() {
    need_env
    cmd_migrate
    cmd_start
    sleep 3
    cmd_status
    echo ""
    echo "Admin panel: http://localhost:3111"
    echo "API: http://localhost:3111/api/v1"
}

ACTION="${1:-help}"
case "$ACTION" in
    start)   cmd_start ;;
    stop)    cmd_stop ;;
    restart) cmd_restart ;;
    status)  cmd_status ;;
    logs)    cmd_logs ;;
    shell)   cmd_shell ;;
    migrate) cmd_migrate ;;
    test)    cmd_test ;;
    admin)   cmd_admin ;;
    full)    cmd_full ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs|shell|migrate|test|admin|full}"
        echo ""
        echo "  start   — запустить бота"
        echo "  stop    — остановить"
        echo "  restart — перезапустить"
        echo "  status  — статус"
        echo "  logs    — последние логи"
        echo "  shell   — shell внутри контейнера"
        echo "  migrate — инициализировать БД"
        echo "  test    — запустить тесты"
        echo "  admin   — admin panel (port 3111)"
        echo "  full    — migrate + start + status"
        ;;
esac
