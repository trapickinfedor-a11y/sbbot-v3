#!/bin/bash
# Metabase Setup Script
# Автоматическая настройка Metabase BI

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}"
echo "╔════════════════════════════════════════════════════════╗"
echo "║     NewLookup Metabase BI Setup                       ║"
echo "╚════════════════════════════════════════════════════════╝"
echo -e "${NC}\n"

# Check if compose file exists
if [ ! -f "docker-compose.metabase.yml" ]; then
    echo -e "${RED}Error: docker-compose.metabase.yml not found${NC}"
    exit 1
fi

# Load environment
if [ -f ".env" ]; then
    source .env
fi

# Generate secure passwords if not set
if [ -z "$METABASE_DB_PASS" ]; then
    export METABASE_DB_PASS=$(openssl rand -base64 32)
    echo -e "${YELLOW}Generated secure METABASE_DB_PASS${NC}"
fi

echo -e "${YELLOW}Starting Metabase stack...${NC}"
docker-compose -f docker-compose.metabase.yml up -d

echo -e "${GREEN}✓ Metabase services started${NC}\n"

# Wait for services to be ready
echo -e "${YELLOW}Waiting for Metabase to be ready (this may take 2-3 minutes)...${NC}"
sleep 30

# Check Metabase health
echo -e "${YELLOW}Checking Metabase health...${NC}"
max_attempts=30
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if curl -f -s http://localhost:3000/api/health &>/dev/null; then
        echo -e "${GREEN}✓ Metabase is healthy${NC}"
        break
    else
        attempt=$((attempt + 1))
        echo -e "${YELLOW}Attempt $attempt/$max_attempts: Waiting for Metabase...${NC}"
        sleep 10
    fi
done

if [ $attempt -eq $max_attempts ]; then
    echo -e "${RED}✗ Metabase is not responding after $max_attempts attempts${NC}"
    echo -e "${YELLOW}Check logs: docker logs newlookup_metabase${NC}"
    exit 1
fi

# Display access information
echo -e "\n${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✓ METABASE SETUP COMPLETE!                            ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"

echo -e "\n${BLUE}Access Information:${NC}"
echo -e "Metabase:   ${GREEN}http://localhost:3000${NC}"
echo -e ""
echo -e "${BLUE}Initial Setup:${NC}"
echo "1. Open http://localhost:3000 in your browser"
echo "2. Complete the initial setup wizard:"
echo "   - Create admin account"
echo "   - Set language and timezone (UTC)"
echo "   - Configure usage data preferences"
echo ""
echo -e "${BLUE}Database Connections:${NC}"
echo ""
echo "1. NewLookup Main Database:"
echo "   Name: NewLookup Production"
echo "   Type: PostgreSQL"
echo "   Host: postgres"
echo "   Port: 5432"
echo "   Database: newlookup"
echo "   Username: \$POSTGRES_USER (from .env)"
echo "   Password: \$POSTGRES_PASSWORD (from .env)"
echo ""
echo "2. Metabase Internal Database (auto-configured):"
echo "   Already connected via environment variables"
echo ""
echo -e "${BLUE}Import Dashboards:${NC}"
echo "1. Go to: Browse → Collections"
echo "2. Create new collection: 'NewLookup Analytics'"
echo "3. Import dashboards from config/metabase/dashboards/"
echo ""
echo -e "${BLUE}Available Dashboards:${NC}"
echo "  📊 001_overview.yml    - Platform Overview"
echo "  👥 002_users.yml       - User Analytics"
echo "  🛒 003_orders.yml      - Orders Analytics"
echo "  🏪 004_sellers.yml     - Sellers Analytics"
echo "  🎧 005_support.yml     - Support & Disputes"
echo "  💰 006_finances.yml    - Finances & Ledger"
echo "  📦 007_products.yml    - Products Catalog"
echo "  🤖 008_bots.yml        - Bots Monitoring"
echo ""
echo -e "${BLUE}System Metrics Endpoints:${NC}"
echo "- Node Exporter:     http://localhost:9100/metrics"
echo "- PostgreSQL:        http://localhost:9187/metrics"
echo "- Redis:             http://localhost:9121/metrics"
echo ""
echo -e "${BLUE}Next Steps:${NC}"
echo "1. Complete Metabase setup wizard"
echo "2. Add NewLookup PostgreSQL database"
echo "3. Import dashboard configurations"
echo "4. Create custom questions and alerts"
echo "5. Set up automated reports (optional)"
echo ""
echo -e "${YELLOW}To stop Metabase:${NC}"
echo "docker-compose -f docker-compose.metabase.yml down"
echo ""
echo -e "${YELLOW}To view logs:${NC}"
echo "docker-compose -f docker-compose.metabase.yml logs -f metabase"
echo ""
echo -e "${GREEN}Metabase BI is ready! 📊${NC}\n"
