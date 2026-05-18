#!/bin/bash
# Application Update Script
# Безопасное обновление приложения с минимальным downtime

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}"
echo "╔════════════════════════════════════════════════════════╗"
echo "║     NewLookup Application Update                      ║"
echo "╚════════════════════════════════════════════════════════╝"
echo -e "${NC}\n"

# Check if running in correct directory
if [ ! -f "docker-compose.production.yml" ]; then
    echo -e "${RED}Error: docker-compose.production.yml not found${NC}"
    echo "Run this script from /opt/newlookup directory"
    exit 1
fi

# Backup before update
echo -e "${YELLOW}Creating backup before update...${NC}"
if [ -f "scripts/backup_postgres.sh" ]; then
    bash scripts/backup_postgres.sh
    echo -e "${GREEN}✓ Backup created${NC}"
else
    echo -e "${YELLOW}⚠ Backup script not found, skipping backup${NC}"
fi

# Pull latest code
echo -e "\n${YELLOW}Pulling latest code from repository...${NC}"
git fetch origin
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo "Current branch: $CURRENT_BRANCH"

# Show changes
echo -e "\n${YELLOW}Changes to be applied:${NC}"
git log HEAD..origin/$CURRENT_BRANCH --oneline --no-decorate | head -10

# Confirm update
echo -e "\n${YELLOW}Do you want to proceed with the update? (yes/no)${NC}"
read -r CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo -e "${YELLOW}Update cancelled${NC}"
    exit 0
fi

# Pull changes
git pull origin $CURRENT_BRANCH

# Check for migration files
echo -e "\n${YELLOW}Checking for database migrations...${NC}"
if [ -d "alembic/versions" ]; then
    NEW_MIGRATIONS=$(git diff HEAD@{1} HEAD --name-only | grep "alembic/versions" || true)
    if [ -n "$NEW_MIGRATIONS" ]; then
        echo -e "${YELLOW}⚠ New migrations detected:${NC}"
        echo "$NEW_MIGRATIONS"
        NEEDS_MIGRATION=true
    else
        echo -e "${GREEN}✓ No new migrations${NC}"
        NEEDS_MIGRATION=false
    fi
else
    NEEDS_MIGRATION=false
fi

# Rebuild images
echo -e "\n${YELLOW}Rebuilding Docker images...${NC}"
docker-compose -f docker-compose.production.yml build --parallel
echo -e "${GREEN}✓ Images rebuilt${NC}"

# Run migrations if needed
if [ "$NEEDS_MIGRATION" = true ]; then
    echo -e "\n${YELLOW}Running database migrations...${NC}"
    docker-compose -f docker-compose.production.yml run --rm main_bot alembic upgrade head
    echo -e "${GREEN}✓ Migrations completed${NC}"
fi

# Rolling restart (one service at a time to minimize downtime)
echo -e "\n${YELLOW}Restarting services...${NC}"

SERVICES=(
    "celery_worker"
    "celery_beat"
    "marketer_bot"
    "seller_bot"
    "worker_bot"
    "support_bot"
    "main_bot"
    "web_panel"
)

for service in "${SERVICES[@]}"; do
    echo -e "${YELLOW}Restarting $service...${NC}"
    docker-compose -f docker-compose.production.yml up -d --no-deps --force-recreate $service
    sleep 3
    
    # Check if service is running
    if docker ps | grep -q "newlookup_$service"; then
        echo -e "${GREEN}✓ $service restarted${NC}"
    else
        echo -e "${RED}✗ $service failed to start${NC}"
        echo -e "${RED}Rolling back...${NC}"
        git reset --hard HEAD@{1}
        docker-compose -f docker-compose.production.yml up -d
        exit 1
    fi
done

# Verify deployment
echo -e "\n${YELLOW}Verifying deployment...${NC}"
sleep 5

# Check container health
UNHEALTHY=$(docker ps --filter "health=unhealthy" --format "{{.Names}}" | grep "newlookup" || true)
if [ -n "$UNHEALTHY" ]; then
    echo -e "${RED}✗ Unhealthy containers detected:${NC}"
    echo "$UNHEALTHY"
    echo -e "${RED}Consider rolling back${NC}"
    exit 1
fi

# Run health check if available
if [ -f "scripts/health_check.sh" ]; then
    bash scripts/health_check.sh
fi

# Show running containers
echo -e "\n${YELLOW}Current container status:${NC}"
docker-compose -f docker-compose.production.yml ps

# Success
echo -e "\n${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✓ UPDATE COMPLETED SUCCESSFULLY!                      ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"

echo -e "\n${BLUE}Post-update checklist:${NC}"
echo "1. Test bots on Telegram"
echo "2. Check Web Panel functionality"
echo "3. Monitor logs for errors: docker-compose logs -f"
echo "4. Check monitoring dashboards"
echo "5. Verify database integrity"

echo -e "\n${YELLOW}If issues occur, rollback with:${NC}"
echo "git reset --hard HEAD@{1}"
echo "docker-compose -f docker-compose.production.yml up -d --build"

echo -e "\n${GREEN}Update complete! 🚀${NC}\n"
