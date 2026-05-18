#!/bin/bash
# Quick Start Script for NewLookup Production Deployment
# Автоматизирует начальное развёртывание

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}"
echo "╔════════════════════════════════════════════════════════╗"
echo "║     NewLookup Production Quick Start                  ║"
echo "║     Automated Deployment Script                       ║"
echo "╚════════════════════════════════════════════════════════╝"
echo -e "${NC}\n"

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}Error: Do not run this script as root${NC}"
    echo "Run as: ./scripts/quick_start.sh"
    exit 1
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${RED}Error: .env file not found${NC}"
    echo "Please create .env file from .env.example first"
    exit 1
fi

# Load environment
source .env

# Check critical variables
REQUIRED_VARS=(
    "POSTGRES_PASSWORD"
    "REDIS_PASSWORD"
    "MAIN_BOT_TOKEN"
    "WEB_PANEL_SECRET_KEY"
)

echo -e "${YELLOW}Checking environment variables...${NC}"
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        echo -e "${RED}✗ $var is not set in .env${NC}"
        exit 1
    else
        echo -e "${GREEN}✓ $var is set${NC}"
    fi
done

# Create required directories
echo -e "\n${YELLOW}Creating directories...${NC}"
mkdir -p data uploads media logs
mkdir -p /tmp/newlookup_backups/{postgres,uploads}
echo -e "${GREEN}✓ Directories created${NC}"

# Check Docker
echo -e "\n${YELLOW}Checking Docker...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker not installed${NC}"
    echo "Install Docker: curl -fsSL https://get.docker.com | sh"
    exit 1
fi
echo -e "${GREEN}✓ Docker installed: $(docker --version)${NC}"

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}✗ Docker Compose not installed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker Compose installed: $(docker-compose --version)${NC}"

# Stop existing containers
echo -e "\n${YELLOW}Stopping existing containers...${NC}"
docker-compose -f docker-compose.production.yml down 2>/dev/null || true
echo -e "${GREEN}✓ Stopped${NC}"

# Build images
echo -e "\n${YELLOW}Building Docker images...${NC}"
docker-compose -f docker-compose.production.yml build --parallel
echo -e "${GREEN}✓ Images built${NC}"

# Start database services first
echo -e "\n${YELLOW}Starting database services...${NC}"
docker-compose -f docker-compose.production.yml up -d postgres redis
echo -e "${GREEN}✓ Database services started${NC}"

# Wait for database
echo -e "\n${YELLOW}Waiting for database to be ready...${NC}"
for i in {1..30}; do
    if docker exec newlookup_postgres pg_isready -U newlookup &>/dev/null; then
        echo -e "${GREEN}✓ Database is ready${NC}"
        break
    fi
    echo -n "."
    sleep 2
done

# Run migrations
echo -e "\n${YELLOW}Running database migrations...${NC}"
docker-compose -f docker-compose.production.yml run --rm main_bot alembic upgrade head
echo -e "${GREEN}✓ Migrations completed${NC}"

# Start all services
echo -e "\n${YELLOW}Starting all services...${NC}"
docker-compose -f docker-compose.production.yml up -d
echo -e "${GREEN}✓ All services started${NC}"

# Wait for services to be healthy
echo -e "\n${YELLOW}Waiting for services to be healthy...${NC}"
sleep 10

# Check container status
echo -e "\n${YELLOW}Container Status:${NC}"
docker-compose -f docker-compose.production.yml ps

# Run verification
echo -e "\n${YELLOW}Running deployment verification...${NC}"
if [ -f "scripts/verify_deployment.sh" ]; then
    bash scripts/verify_deployment.sh
else
    echo -e "${YELLOW}⚠ Verification script not found, skipping${NC}"
fi

# Display access information
echo -e "\n${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✓ DEPLOYMENT COMPLETE!                                ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"

echo -e "\n${BLUE}Access Information:${NC}"
echo -e "Web Panel: ${GREEN}http://localhost:8000${NC}"
echo -e "Username: ${GREEN}${ADMIN_USERNAME:-admin}${NC}"
echo -e "Password: ${GREEN}[check .env file]${NC}"

echo -e "\n${BLUE}Useful Commands:${NC}"
echo -e "View logs:    ${YELLOW}docker-compose -f docker-compose.production.yml logs -f${NC}"
echo -e "Stop all:     ${YELLOW}docker-compose -f docker-compose.production.yml down${NC}"
echo -e "Restart:      ${YELLOW}docker-compose -f docker-compose.production.yml restart${NC}"
echo -e "Health check: ${YELLOW}./scripts/health_check.sh${NC}"

echo -e "\n${BLUE}Next Steps:${NC}"
echo "1. Test bots on Telegram"
echo "2. Access Web Panel and verify functionality"
echo "3. Setup monitoring: docker-compose -f docker-compose.monitoring.yml up -d"
echo "4. Configure backups: crontab -e"
echo "5. Setup SSL/TLS if using domain"

echo -e "\n${GREEN}Happy bot running! 🚀${NC}\n"
