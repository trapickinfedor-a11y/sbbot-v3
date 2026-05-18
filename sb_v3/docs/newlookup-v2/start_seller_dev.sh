#!/bin/bash
# Скрипт для быстрого запуска Seller системы в dev режиме

set -e

echo "🚀 Starting Seller System (Development Mode)"
echo "=============================================="
echo ""

# Цвета
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Проверка .env
if [ ! -f .env ]; then
    echo -e "${RED}❌ .env файл не найден${NC}"
    echo "Скопируйте .env.example в .env и настройте переменные"
    exit 1
fi

echo -e "${GREEN}✅ .env файл найден${NC}"

# Проверка Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker не установлен${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker установлен${NC}"

# Проверка docker-compose
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ docker-compose не установлен${NC}"
    exit 1
fi

echo -e "${GREEN}✅ docker-compose установлен${NC}"
echo ""

# Остановка существующих контейнеров
echo -e "${BLUE}🛑 Остановка существующих контейнеров...${NC}"
docker-compose down 2>/dev/null || true
echo ""

# Запуск PostgreSQL
echo -e "${BLUE}🐘 Запуск PostgreSQL...${NC}"
docker-compose up -d postgres
echo -e "${GREEN}✅ PostgreSQL запущен${NC}"
echo ""

# Ожидание готовности PostgreSQL
echo -e "${BLUE}⏳ Ожидание готовности PostgreSQL (10 сек)...${NC}"
sleep 10
echo ""

# Запуск Redis
echo -e "${BLUE}🔴 Запуск Redis...${NC}"
docker-compose up -d redis
echo -e "${GREEN}✅ Redis запущен${NC}"
echo ""

# Запуск Web Panel
echo -e "${BLUE}🌐 Запуск Web Panel...${NC}"
docker-compose up -d web_panel
echo -e "${GREEN}✅ Web Panel запущен на http://localhost:8000${NC}"
echo ""

# Запуск Seller Bot
echo -e "${BLUE}🤖 Запуск Seller Bot...${NC}"
docker-compose up -d seller_bot
echo -e "${GREEN}✅ Seller Bot запущен${NC}"
echo ""

# Проверка статуса
echo -e "${BLUE}📊 Статус сервисов:${NC}"
docker-compose ps
echo ""

# Вывод логов
echo -e "${YELLOW}📝 Логи Seller Bot (последние 20 строк):${NC}"
docker-compose logs --tail=20 seller_bot
echo ""

echo -e "${YELLOW}📝 Логи Web Panel (последние 20 строк):${NC}"
docker-compose logs --tail=20 web_panel
echo ""

# Итоговая информация
echo "=============================================="
echo -e "${GREEN}✅ Seller система запущена!${NC}"
echo "=============================================="
echo ""
echo "📍 Доступные URL:"
echo "  • Web Panel:    http://localhost:8000"
echo "  • Mini App:     http://localhost:8000/seller-mini-app"
echo "  • API Docs:     http://localhost:8000/docs"
echo ""
echo "📝 Полезные команды:"
echo "  • Логи Seller Bot:  docker-compose logs -f seller_bot"
echo "  • Логи Web Panel:   docker-compose logs -f web_panel"
echo "  • Остановить всё:   docker-compose down"
echo "  • Перезапустить:    docker-compose restart seller_bot"
echo ""
echo "🧪 Тестирование:"
echo "  1. Откройте Telegram бота"
echo "  2. Отправьте /start"
echo "  3. Нажмите кнопку '🖥 Mini App'"
echo ""
echo -e "${BLUE}Для просмотра логов в реальном времени:${NC}"
echo "  docker-compose logs -f seller_bot web_panel"
echo ""
