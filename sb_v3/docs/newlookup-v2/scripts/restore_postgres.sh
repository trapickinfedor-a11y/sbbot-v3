#!/bin/bash
# PostgreSQL Restore Script for NewLookup
# Восстанавливает базу данных из бэкапа

set -e

# Configuration
BACKUP_DIR="/opt/backups/postgres"
CONTAINER_NAME="newlookup_postgres"
DB_NAME="${POSTGRES_DB:-newlookup}"
DB_USER="${POSTGRES_USER:-newlookup}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check if backup file is provided
if [ -z "$1" ]; then
    echo -e "${RED}Error: No backup file specified${NC}"
    echo -e "Usage: $0 <backup_file.dump.gz>"
    echo -e "\nAvailable backups:"
    ls -lh "$BACKUP_DIR"/*.dump.gz 2>/dev/null || echo "No backups found"
    exit 1
fi

BACKUP_FILE="$1"

# Check if file exists
if [ ! -f "$BACKUP_FILE" ]; then
    # Try with backup directory prefix
    BACKUP_FILE="$BACKUP_DIR/$1"
    if [ ! -f "$BACKUP_FILE" ]; then
        echo -e "${RED}Error: Backup file not found: $1${NC}"
        exit 1
    fi
fi

echo -e "${YELLOW}⚠️  WARNING: This will REPLACE the current database!${NC}"
echo -e "${YELLOW}Database: $DB_NAME${NC}"
echo -e "${YELLOW}Backup file: $BACKUP_FILE${NC}"
echo -e "\n${RED}Are you sure you want to continue? (yes/no)${NC}"
read -r CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo -e "${YELLOW}Restore cancelled${NC}"
    exit 0
fi

# Check if container is running
if ! docker ps | grep -q "$CONTAINER_NAME"; then
    echo -e "${RED}Error: Container $CONTAINER_NAME is not running${NC}"
    exit 1
fi

echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} Starting database restore..."

# Decompress if needed
TEMP_FILE="/tmp/restore_$(date +%s).dump"
if [[ "$BACKUP_FILE" == *.gz ]]; then
    echo -e "${YELLOW}Decompressing backup...${NC}"
    gunzip -c "$BACKUP_FILE" > "$TEMP_FILE"
    RESTORE_FILE="$TEMP_FILE"
else
    RESTORE_FILE="$BACKUP_FILE"
fi

# Stop all bots to prevent database access
echo -e "${YELLOW}Stopping bot services...${NC}"
docker compose stop main_bot support_bot worker_bot seller_bot marketer_bot web_panel 2>/dev/null || true

# Drop existing connections
echo -e "${YELLOW}Terminating active connections...${NC}"
docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d postgres -c \
    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$DB_NAME' AND pid <> pg_backend_pid();" \
    2>/dev/null || true

# Drop and recreate database
echo -e "${YELLOW}Dropping database...${NC}"
docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS $DB_NAME;"

echo -e "${YELLOW}Creating database...${NC}"
docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d postgres -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"

# Restore backup
echo -e "${YELLOW}Restoring backup...${NC}"
cat "$RESTORE_FILE" | docker exec -i "$CONTAINER_NAME" pg_restore -U "$DB_USER" -d "$DB_NAME" -v

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Database restored successfully${NC}"
else
    echo -e "${RED}✗ Restore failed${NC}"
    rm -f "$TEMP_FILE"
    exit 1
fi

# Cleanup
rm -f "$TEMP_FILE"

# Restart services
echo -e "${YELLOW}Restarting bot services...${NC}"
docker compose up -d main_bot support_bot worker_bot seller_bot marketer_bot web_panel

echo -e "\n${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] Restore completed successfully!${NC}"
echo -e "${YELLOW}Please verify that all services are working correctly.${NC}"
