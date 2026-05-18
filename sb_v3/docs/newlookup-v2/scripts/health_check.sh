#!/bin/bash
# Health Check Script for NewLookup
# Проверяет состояние всех сервисов и отправляет алерты при проблемах

set -e

# Configuration
ALERT_EMAIL="${ALERT_EMAIL:-admin@example.com}"
ALERT_WEBHOOK="${ALERT_WEBHOOK:-}"
LOG_FILE="/var/log/newlookup/health_check.log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Counters
ERRORS=0
WARNINGS=0

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Alert function
send_alert() {
    local severity=$1
    local message=$2
    
    log "${RED}ALERT [$severity]: $message${NC}"
    
    # Send email alert (if configured)
    if [ -n "$ALERT_EMAIL" ] && command -v mail &> /dev/null; then
        echo "$message" | mail -s "[NewLookup] $severity Alert" "$ALERT_EMAIL"
    fi
    
    # Send webhook alert (if configured)
    if [ -n "$ALERT_WEBHOOK" ]; then
        curl -X POST "$ALERT_WEBHOOK" \
            -H "Content-Type: application/json" \
            -d "{\"severity\":\"$severity\",\"message\":\"$message\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}" \
            2>/dev/null || true
    fi
}

# Check Docker containers
check_containers() {
    log "Checking Docker containers..."
    
    local containers=(
        "newlookup_postgres"
        "newlookup_redis"
        "newlookup_main_bot"
        "newlookup_support_bot"
        "newlookup_worker_bot"
        "newlookup_seller_bot"
        "newlookup_marketer_bot"
        "newlookup_web_panel"
    )
    
    for container in "${containers[@]}"; do
        if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
            # Check if container is healthy
            health=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "none")
            
            if [ "$health" = "healthy" ] || [ "$health" = "none" ]; then
                log "${GREEN}✓ $container is running${NC}"
            else
                log "${RED}✗ $container is unhealthy (status: $health)${NC}"
                send_alert "CRITICAL" "Container $container is unhealthy"
                ((ERRORS++))
            fi
        else
            log "${RED}✗ $container is not running${NC}"
            send_alert "CRITICAL" "Container $container is not running"
            ((ERRORS++))
        fi
    done
}

# Check PostgreSQL
check_postgres() {
    log "Checking PostgreSQL..."
    
    if docker exec newlookup_postgres pg_isready -U newlookup &>/dev/null; then
        log "${GREEN}✓ PostgreSQL is responding${NC}"
        
        # Check connections
        connections=$(docker exec newlookup_postgres psql -U newlookup -d newlookup -t -c \
            "SELECT count(*) FROM pg_stat_activity WHERE datname='newlookup';" 2>/dev/null | tr -d ' ')
        
        log "Active connections: $connections"
        
        if [ "$connections" -gt 900 ]; then
            log "${RED}⚠ High connection count: $connections/1000${NC}"
            send_alert "WARNING" "PostgreSQL connection count is high: $connections/1000"
            ((WARNINGS++))
        fi
    else
        log "${RED}✗ PostgreSQL is not responding${NC}"
        send_alert "CRITICAL" "PostgreSQL is not responding"
        ((ERRORS++))
    fi
}

# Check Redis
check_redis() {
    log "Checking Redis..."
    
    if docker exec newlookup_redis redis-cli -a "${REDIS_PASSWORD:-changeme_redis}" ping &>/dev/null; then
        log "${GREEN}✓ Redis is responding${NC}"
        
        # Check memory usage
        memory=$(docker exec newlookup_redis redis-cli -a "${REDIS_PASSWORD:-changeme_redis}" \
            INFO memory | grep "used_memory_human" | cut -d: -f2 | tr -d '\r')
        
        log "Redis memory usage: $memory"
    else
        log "${RED}✗ Redis is not responding${NC}"
        send_alert "CRITICAL" "Redis is not responding"
        ((ERRORS++))
    fi
}

# Check disk space
check_disk() {
    log "Checking disk space..."
    
    usage=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
    
    if [ "$usage" -gt 90 ]; then
        log "${RED}✗ Disk usage critical: ${usage}%${NC}"
        send_alert "CRITICAL" "Disk usage is critical: ${usage}%"
        ((ERRORS++))
    elif [ "$usage" -gt 80 ]; then
        log "${YELLOW}⚠ Disk usage high: ${usage}%${NC}"
        send_alert "WARNING" "Disk usage is high: ${usage}%"
        ((WARNINGS++))
    else
        log "${GREEN}✓ Disk usage OK: ${usage}%${NC}"
    fi
}

# Check memory
check_memory() {
    log "Checking memory..."
    
    if command -v free &> /dev/null; then
        mem_usage=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100}')
        
        if [ "$mem_usage" -gt 95 ]; then
            log "${RED}✗ Memory usage critical: ${mem_usage}%${NC}"
            send_alert "CRITICAL" "Memory usage is critical: ${mem_usage}%"
            ((ERRORS++))
        elif [ "$mem_usage" -gt 85 ]; then
            log "${YELLOW}⚠ Memory usage high: ${mem_usage}%${NC}"
            send_alert "WARNING" "Memory usage is high: ${mem_usage}%"
            ((WARNINGS++))
        else
            log "${GREEN}✓ Memory usage OK: ${mem_usage}%${NC}"
        fi
    fi
}

# Check Web Panel
check_web_panel() {
    log "Checking Web Panel..."
    
    if curl -f -s -o /dev/null -w "%{http_code}" http://localhost:8000/health 2>/dev/null | grep -q "200"; then
        log "${GREEN}✓ Web Panel is responding${NC}"
    else
        log "${RED}✗ Web Panel is not responding${NC}"
        send_alert "CRITICAL" "Web Panel is not responding"
        ((ERRORS++))
    fi
}

# Main execution
log "========== Starting Health Check =========="

check_containers
check_postgres
check_redis
check_disk
check_memory
check_web_panel

log "========== Health Check Complete =========="
log "Errors: $ERRORS, Warnings: $WARNINGS"

if [ $ERRORS -gt 0 ]; then
    log "${RED}Health check FAILED with $ERRORS error(s)${NC}"
    exit 1
elif [ $WARNINGS -gt 0 ]; then
    log "${YELLOW}Health check completed with $WARNINGS warning(s)${NC}"
    exit 0
else
    log "${GREEN}Health check PASSED${NC}"
    exit 0
fi
