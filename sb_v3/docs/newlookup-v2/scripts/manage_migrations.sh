#!/bin/bash
# Database Migration Script
# Управление миграциями базы данных

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

# Functions
show_help() {
    echo -e "${BLUE}Database Migration Management${NC}\n"
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  status      - Show current migration status"
    echo "  upgrade     - Apply all pending migrations"
    echo "  downgrade   - Rollback last migration"
    echo "  history     - Show migration history"
    echo "  create      - Create new migration"
    echo "  help        - Show this help message"
    echo ""
}

check_container() {
    if ! docker ps | grep -q "newlookup_main_bot"; then
        echo -e "${RED}Error: main_bot container is not running${NC}"
        exit 1
    fi
}

migration_status() {
    echo -e "${YELLOW}Current migration status:${NC}\n"
    docker-compose -f docker-compose.production.yml exec main_bot alembic current
    echo ""
    echo -e "${YELLOW}Pending migrations:${NC}"
    docker-compose -f docker-compose.production.yml exec main_bot alembic heads
}

migration_upgrade() {
    echo -e "${YELLOW}Applying migrations...${NC}"
    
    # Backup before migration
    if [ -f "scripts/backup_postgres.sh" ]; then
        echo -e "${YELLOW}Creating backup before migration...${NC}"
        bash scripts/backup_postgres.sh
    fi
    
    # Apply migrations
    docker-compose -f docker-compose.production.yml run --rm main_bot alembic upgrade head
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Migrations applied successfully${NC}"
    else
        echo -e "${RED}✗ Migration failed${NC}"
        exit 1
    fi
}

migration_downgrade() {
    echo -e "${RED}⚠️  WARNING: This will rollback the last migration${NC}"
    echo -e "${YELLOW}Are you sure? (yes/no)${NC}"
    read -r CONFIRM
    
    if [ "$CONFIRM" != "yes" ]; then
        echo -e "${YELLOW}Downgrade cancelled${NC}"
        exit 0
    fi
    
    # Backup before downgrade
    if [ -f "scripts/backup_postgres.sh" ]; then
        echo -e "${YELLOW}Creating backup before downgrade...${NC}"
        bash scripts/backup_postgres.sh
    fi
    
    echo -e "${YELLOW}Rolling back last migration...${NC}"
    docker-compose -f docker-compose.production.yml run --rm main_bot alembic downgrade -1
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Migration rolled back successfully${NC}"
    else
        echo -e "${RED}✗ Downgrade failed${NC}"
        exit 1
    fi
}

migration_history() {
    echo -e "${YELLOW}Migration history:${NC}\n"
    docker-compose -f docker-compose.production.yml exec main_bot alembic history --verbose
}

migration_create() {
    echo -e "${YELLOW}Enter migration message:${NC}"
    read -r MESSAGE
    
    if [ -z "$MESSAGE" ]; then
        echo -e "${RED}Error: Migration message is required${NC}"
        exit 1
    fi
    
    echo -e "${YELLOW}Creating migration: $MESSAGE${NC}"
    docker-compose -f docker-compose.production.yml run --rm main_bot alembic revision --autogenerate -m "$MESSAGE"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Migration created successfully${NC}"
        echo -e "${YELLOW}Review the migration file before applying${NC}"
    else
        echo -e "${RED}✗ Migration creation failed${NC}"
        exit 1
    fi
}

# Main
case "${1:-help}" in
    status)
        check_container
        migration_status
        ;;
    upgrade)
        check_container
        migration_upgrade
        ;;
    downgrade)
        check_container
        migration_downgrade
        ;;
    history)
        check_container
        migration_history
        ;;
    create)
        check_container
        migration_create
        ;;
    help|*)
        show_help
        ;;
esac
