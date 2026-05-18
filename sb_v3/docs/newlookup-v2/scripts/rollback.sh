#!/bin/bash
# Rollback Script for Failed Deployments
# Откатывает приложение к предыдущей версии

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${RED}"
echo "╔════════════════════════════════════════════════════════╗"
echo "║     ⚠️  ROLLBACK TO PREVIOUS VERSION                  ║"
echo "╚════════════════════════════════════════════════════════╝"
echo -e "${NC}\n"

# Check if running in correct directory
if [ ! -f "docker-compose.production.yml" ]; then
    echo -e "${RED}Error: docker-compose.production.yml not found${NC}"
    exit 1
fi

# Show current commit
echo -e "${YELLOW}Current version:${NC}"
git log -1 --oneline

# Show previous commits
echo -e "\n${YELLOW}Recent commits:${NC}"
git log --oneline -5

# Ask which commit to rollback to
echo -e "\n${YELLOW}Enter commit hash to rollback to (or 'HEAD~1' for previous):${NC}"
read -r ROLLBACK_TO

if [ -z "$ROLLBACK_TO" ]; then
    ROLLBACK_TO="HEAD~1"
fi

# Confirm rollback
echo -e "\n${RED}⚠️  WARNING: This will rollback to: $ROLLBACK_TO${NC}"
echo -e "${YELLOW}Target commit:${NC}"
git log -1 --oneline "$ROLLBACK_TO"

echo -e "\n${RED}Are you sure you want to rollback? (yes/no)${NC}"
read -r CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo -e "${YELLOW}Rollback cancelled${NC}"
    exit 0
fi

# Create backup before rollback
echo -e "\n${YELLOW}Creating backup before rollback...${NC}"
if [ -f "scripts/backup_postgres.sh" ]; then
    bash scripts/backup_postgres.sh
    echo -e "${GREEN}✓ Backup created${NC}"
fi

# Stop all services
echo -e "\n${YELLOW}Stopping all services...${NC}"
docker-compose -f docker-compose.production.yml down
echo -e "${GREEN}✓ Services stopped${NC}"

# Rollback code
echo -e "\n${YELLOW}Rolling back code...${NC}"
git reset --hard "$ROLLBACK_TO"
echo -e "${GREEN}✓ Code rolled back${NC}"

# Check for migration rollback
echo -e "\n${YELLOW}Checking database migrations...${NC}"
echo -e "${RED}⚠️  Manual migration rollback may be required${NC}"
echo -e "${YELLOW}Review alembic history and downgrade if needed:${NC}"
echo "docker-compose -f docker-compose.production.yml run --rm main_bot alembic downgrade -1"

# Rebuild images
echo -e "\n${YELLOW}Rebuilding Docker images...${NC}"
docker-compose -f docker-compose.production.yml build --parallel
echo -e "${GREEN}✓ Images rebuilt${NC}"

# Start services
echo -e "\n${YELLOW}Starting services...${NC}"
docker-compose -f docker-compose.production.yml up -d
echo -e "${GREEN}✓ Services started${NC}"

# Wait and verify
echo -e "\n${YELLOW}Waiting for services to be ready...${NC}"
sleep 10

# Check container status
echo -e "\n${YELLOW}Container status:${NC}"
docker-compose -f docker-compose.production.yml ps

# Run health check
if [ -f "scripts/health_check.sh" ]; then
    echo -e "\n${YELLOW}Running health check...${NC}"
    bash scripts/health_check.sh
fi

# Success
echo -e "\n${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✓ ROLLBACK COMPLETED                                  ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"

echo -e "\n${BLUE}Post-rollback checklist:${NC}"
echo "1. Test bots on Telegram"
echo "2. Check Web Panel functionality"
echo "3. Monitor logs: docker-compose logs -f"
echo "4. Verify database integrity"
echo "5. Check for any migration issues"

echo -e "\n${YELLOW}Current version:${NC}"
git log -1 --oneline

echo -e "\n${GREEN}Rollback complete! 🔄${NC}\n"
