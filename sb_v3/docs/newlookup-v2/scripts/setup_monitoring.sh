#!/bin/bash
# Monitoring Setup Script
# Автоматическая настройка Prometheus + Grafana

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}"
echo "╔════════════════════════════════════════════════════════╗"
echo "║     NewLookup Monitoring Setup                        ║"
echo "╚════════════════════════════════════════════════════════╝"
echo -e "${NC}\n"

# Check if monitoring compose file exists
if [ ! -f "docker-compose.monitoring.yml" ]; then
    echo -e "${RED}Error: docker-compose.monitoring.yml not found${NC}"
    exit 1
fi

# Load environment
if [ -f ".env" ]; then
    source .env
fi

# Set default Grafana credentials if not set
GRAFANA_ADMIN_USER=${GRAFANA_ADMIN_USER:-admin}
GRAFANA_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD:-admin}

echo -e "${YELLOW}Starting monitoring stack...${NC}"
docker-compose -f docker-compose.monitoring.yml up -d

echo -e "${GREEN}✓ Monitoring services started${NC}\n"

# Wait for services to be ready
echo -e "${YELLOW}Waiting for services to be ready...${NC}"
sleep 10

# Check Prometheus
echo -e "${YELLOW}Checking Prometheus...${NC}"
if curl -f -s http://localhost:9090/-/healthy &>/dev/null; then
    echo -e "${GREEN}✓ Prometheus is healthy${NC}"
else
    echo -e "${RED}✗ Prometheus is not responding${NC}"
fi

# Check Grafana
echo -e "${YELLOW}Checking Grafana...${NC}"
if curl -f -s http://localhost:3000/api/health &>/dev/null; then
    echo -e "${GREEN}✓ Grafana is healthy${NC}"
else
    echo -e "${RED}✗ Grafana is not responding${NC}"
fi

# Display access information
echo -e "\n${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✓ MONITORING SETUP COMPLETE!                          ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"

echo -e "\n${BLUE}Access Information:${NC}"
echo -e "Prometheus: ${GREEN}http://localhost:9090${NC}"
echo -e "Grafana:    ${GREEN}http://localhost:3000${NC}"
echo -e "Username:   ${GREEN}${GRAFANA_ADMIN_USER}${NC}"
echo -e "Password:   ${GREEN}${GRAFANA_ADMIN_PASSWORD}${NC}"

echo -e "\n${BLUE}Available Metrics:${NC}"
echo "- Node Exporter:     http://localhost:9100/metrics"
echo "- PostgreSQL:        http://localhost:9187/metrics"
echo "- Redis:             http://localhost:9121/metrics"
echo "- cAdvisor:          http://localhost:8080/metrics"

echo -e "\n${BLUE}Recommended Grafana Dashboards:${NC}"
echo "1. Node Exporter Full (ID: 1860)"
echo "   - Import: Configuration → Dashboards → Import → 1860"
echo ""
echo "2. PostgreSQL Database (ID: 9628)"
echo "   - Import: Configuration → Dashboards → Import → 9628"
echo ""
echo "3. Redis Dashboard (ID: 11835)"
echo "   - Import: Configuration → Dashboards → Import → 11835"
echo ""
echo "4. Docker Container Metrics (ID: 893)"
echo "   - Import: Configuration → Dashboards → Import → 893"

echo -e "\n${BLUE}Next Steps:${NC}"
echo "1. Access Grafana at http://localhost:3000"
echo "2. Login with credentials above"
echo "3. Change default password (recommended)"
echo "4. Import recommended dashboards"
echo "5. Configure alert notifications (optional)"

echo -e "\n${YELLOW}To stop monitoring:${NC}"
echo "docker-compose -f docker-compose.monitoring.yml down"

echo -e "\n${GREEN}Monitoring is ready! 📊${NC}\n"
