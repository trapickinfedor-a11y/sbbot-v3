#!/bin/bash
# Deployment Verification Script for NewLookup
# Проверяет корректность развёртывания системы

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Counters
PASSED=0
FAILED=0
WARNINGS=0

# Functions
print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

check_pass() {
    echo -e "${GREEN}✓ $1${NC}"
    ((PASSED++))
}

check_fail() {
    echo -e "${RED}✗ $1${NC}"
    ((FAILED++))
}

check_warn() {
    echo -e "${YELLOW}⚠ $1${NC}"
    ((WARNINGS++))
}

# Start verification
echo -e "${BLUE}"
echo "╔════════════════════════════════════════════════════════╗"
echo "║     NewLookup Deployment Verification Script          ║"
echo "║     Version 1.0                                        ║"
echo "╚════════════════════════════════════════════════════════╝"
echo -e "${NC}\n"

# ========== System Requirements ==========
print_header "1. System Requirements"

# Check CPU
CPU_CORES=$(nproc)
if [ "$CPU_CORES" -ge 16 ]; then
    check_pass "CPU cores: $CPU_CORES (minimum: 16)"
elif [ "$CPU_CORES" -ge 8 ]; then
    check_warn "CPU cores: $CPU_CORES (recommended: 16+)"
else
    check_fail "CPU cores: $CPU_CORES (minimum: 16 required)"
fi

# Check RAM
TOTAL_RAM=$(free -g | awk '/^Mem:/{print $2}')
if [ "$TOTAL_RAM" -ge 32 ]; then
    check_pass "RAM: ${TOTAL_RAM}GB (minimum: 32GB)"
elif [ "$TOTAL_RAM" -ge 16 ]; then
    check_warn "RAM: ${TOTAL_RAM}GB (recommended: 32GB+)"
else
    check_fail "RAM: ${TOTAL_RAM}GB (minimum: 32GB required)"
fi

# Check disk space
DISK_AVAIL=$(df -BG / | awk 'NR==2 {print $4}' | sed 's/G//')
if [ "$DISK_AVAIL" -ge 400 ]; then
    check_pass "Disk space: ${DISK_AVAIL}GB available"
elif [ "$DISK_AVAIL" -ge 200 ]; then
    check_warn "Disk space: ${DISK_AVAIL}GB available (recommended: 400GB+)"
else
    check_fail "Disk space: ${DISK_AVAIL}GB available (minimum: 200GB required)"
fi

# ========== Docker ==========
print_header "2. Docker Installation"

if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version | awk '{print $3}' | sed 's/,//')
    check_pass "Docker installed: $DOCKER_VERSION"
else
    check_fail "Docker not installed"
fi

if command -v docker-compose &> /dev/null; then
    COMPOSE_VERSION=$(docker-compose --version | awk '{print $4}')
    check_pass "Docker Compose installed: $COMPOSE_VERSION"
else
    check_fail "Docker Compose not installed"
fi

# Check Docker service
if systemctl is-active --quiet docker; then
    check_pass "Docker service is running"
else
    check_fail "Docker service is not running"
fi

# ========== Application Files ==========
print_header "3. Application Files"

if [ -d "/opt/newlookup" ]; then
    check_pass "Application directory exists: /opt/newlookup"
else
    check_fail "Application directory not found: /opt/newlookup"
fi

if [ -f "/opt/newlookup/.env" ]; then
    check_pass ".env file exists"
    
    # Check critical env variables
    source /opt/newlookup/.env 2>/dev/null || true
    
    if [ -n "$POSTGRES_PASSWORD" ]; then
        check_pass "POSTGRES_PASSWORD is set"
    else
        check_fail "POSTGRES_PASSWORD not set in .env"
    fi
    
    if [ -n "$MAIN_BOT_TOKEN" ]; then
        check_pass "MAIN_BOT_TOKEN is set"
    else
        check_fail "MAIN_BOT_TOKEN not set in .env"
    fi
else
    check_fail ".env file not found"
fi

if [ -f "/opt/newlookup/docker-compose.production.yml" ]; then
    check_pass "Production docker-compose file exists"
else
    check_fail "Production docker-compose file not found"
fi

# ========== Docker Containers ==========
print_header "4. Docker Containers"

CONTAINERS=(
    "newlookup_postgres"
    "newlookup_redis"
    "newlookup_main_bot"
    "newlookup_support_bot"
    "newlookup_worker_bot"
    "newlookup_seller_bot"
    "newlookup_marketer_bot"
    "newlookup_web_panel"
)

for container in "${CONTAINERS[@]}"; do
    if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
        # Check if healthy
        health=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "none")
        if [ "$health" = "healthy" ] || [ "$health" = "none" ]; then
            check_pass "Container running: $container"
        else
            check_warn "Container unhealthy: $container (status: $health)"
        fi
    else
        check_fail "Container not running: $container"
    fi
done

# ========== Database ==========
print_header "5. Database"

if docker exec newlookup_postgres pg_isready -U newlookup &>/dev/null; then
    check_pass "PostgreSQL is responding"
    
    # Check database exists
    if docker exec newlookup_postgres psql -U newlookup -lqt | cut -d \| -f 1 | grep -qw newlookup; then
        check_pass "Database 'newlookup' exists"
        
        # Check tables
        TABLE_COUNT=$(docker exec newlookup_postgres psql -U newlookup -d newlookup -t -c "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | tr -d ' ')
        if [ "$TABLE_COUNT" -gt 10 ]; then
            check_pass "Database tables: $TABLE_COUNT tables found"
        else
            check_warn "Database tables: only $TABLE_COUNT tables found (expected 20+)"
        fi
    else
        check_fail "Database 'newlookup' not found"
    fi
else
    check_fail "PostgreSQL is not responding"
fi

# ========== Redis ==========
print_header "6. Redis"

if docker exec newlookup_redis redis-cli ping &>/dev/null; then
    check_pass "Redis is responding"
else
    check_fail "Redis is not responding"
fi

# ========== Web Panel ==========
print_header "7. Web Panel"

if curl -f -s -o /dev/null http://localhost:8000 2>/dev/null; then
    check_pass "Web Panel is accessible on port 8000"
else
    check_warn "Web Panel not accessible on port 8000"
fi

# ========== Backup Configuration ==========
print_header "8. Backup Configuration"

if [ -d "/opt/backups/postgres" ]; then
    check_pass "PostgreSQL backup directory exists"
else
    check_warn "PostgreSQL backup directory not found: /opt/backups/postgres"
fi

if [ -d "/opt/backups/uploads" ]; then
    check_pass "Uploads backup directory exists"
else
    check_warn "Uploads backup directory not found: /opt/backups/uploads"
fi

if [ -f "/opt/newlookup/scripts/backup_postgres.sh" ]; then
    if [ -x "/opt/newlookup/scripts/backup_postgres.sh" ]; then
        check_pass "PostgreSQL backup script is executable"
    else
        check_warn "PostgreSQL backup script exists but not executable"
    fi
else
    check_warn "PostgreSQL backup script not found"
fi

# Check crontab
if crontab -l 2>/dev/null | grep -q "backup_postgres.sh"; then
    check_pass "Backup cron job configured"
else
    check_warn "Backup cron job not configured"
fi

# ========== Monitoring ==========
print_header "9. Monitoring (Optional)"

if docker ps --format '{{.Names}}' | grep -q "newlookup_prometheus"; then
    check_pass "Prometheus is running"
else
    check_warn "Prometheus not running (optional)"
fi

if docker ps --format '{{.Names}}' | grep -q "newlookup_grafana"; then
    check_pass "Grafana is running"
else
    check_warn "Grafana not running (optional)"
fi

# ========== Security ==========
print_header "10. Security"

# Check firewall
if command -v ufw &> /dev/null; then
    if ufw status | grep -q "Status: active"; then
        check_pass "UFW firewall is active"
    else
        check_warn "UFW firewall is not active"
    fi
else
    check_warn "UFW not installed"
fi

# Check fail2ban
if systemctl is-active --quiet fail2ban 2>/dev/null; then
    check_pass "Fail2ban is running"
else
    check_warn "Fail2ban not running (recommended)"
fi

# ========== Summary ==========
print_header "Verification Summary"

TOTAL=$((PASSED + FAILED + WARNINGS))
echo -e "Total checks: $TOTAL"
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${YELLOW}Warnings: $WARNINGS${NC}"
echo -e "${RED}Failed: $FAILED${NC}"

echo ""

if [ $FAILED -eq 0 ]; then
    if [ $WARNINGS -eq 0 ]; then
        echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
        echo -e "${GREEN}║  ✓ ALL CHECKS PASSED - DEPLOYMENT SUCCESSFUL!         ║${NC}"
        echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
        exit 0
    else
        echo -e "${YELLOW}╔════════════════════════════════════════════════════════╗${NC}"
        echo -e "${YELLOW}║  ⚠ DEPLOYMENT OK WITH WARNINGS                        ║${NC}"
        echo -e "${YELLOW}║  Review warnings above and fix if needed              ║${NC}"
        echo -e "${YELLOW}╚════════════════════════════════════════════════════════╝${NC}"
        exit 0
    fi
else
    echo -e "${RED}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║  ✗ DEPLOYMENT VERIFICATION FAILED                      ║${NC}"
    echo -e "${RED}║  Fix failed checks above before proceeding             ║${NC}"
    echo -e "${RED}╚════════════════════════════════════════════════════════╝${NC}"
    exit 1
fi
