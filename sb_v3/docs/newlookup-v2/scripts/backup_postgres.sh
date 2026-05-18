#!/bin/bash
# PostgreSQL Backup Script for NewLookup
# Создаёт ежедневные бэкапы базы данных

set -e

# Configuration
BACKUP_DIR="/opt/backups/postgres"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30
CONTAINER_NAME="newlookup_postgres"
DB_NAME="${POSTGRES_DB:-newlookup}"
DB_USER="${POSTGRES_USER:-newlookup}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} Starting PostgreSQL backup..."

# Check if container is running
if ! docker ps | grep -q "$CONTAINER_NAME"; then
    echo -e "${RED}Error: Container $CONTAINER_NAME is not running${NC}"
    exit 1
fi

# Create backup
BACKUP_FILE="$BACKUP_DIR/${DB_NAME}_${DATE}.dump"
echo -e "${YELLOW}Creating backup: $BACKUP_FILE${NC}"

docker exec "$CONTAINER_NAME" pg_dump -U "$DB_USER" -Fc "$DB_NAME" > "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Backup created successfully${NC}"
    
    # Compress backup
    echo -e "${YELLOW}Compressing backup...${NC}"
    gzip "$BACKUP_FILE"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Backup compressed: ${BACKUP_FILE}.gz${NC}"
        
        # Get file size
        SIZE=$(du -h "${BACKUP_FILE}.gz" | cut -f1)
        echo -e "${GREEN}Backup size: $SIZE${NC}"
    else
        echo -e "${RED}✗ Compression failed${NC}"
        exit 1
    fi
else
    echo -e "${RED}✗ Backup failed${NC}"
    exit 1
fi

# Delete old backups
echo -e "${YELLOW}Cleaning up old backups (older than $RETENTION_DAYS days)...${NC}"
DELETED=$(find "$BACKUP_DIR" -name "*.dump.gz" -mtime +$RETENTION_DAYS -delete -print | wc -l)
echo -e "${GREEN}✓ Deleted $DELETED old backup(s)${NC}"

# Optional: Upload to S3 or remote storage
# Uncomment and configure if needed
# if [ -n "$AWS_S3_BUCKET" ]; then
#     echo -e "${YELLOW}Uploading to S3...${NC}"
#     aws s3 cp "${BACKUP_FILE}.gz" "s3://$AWS_S3_BUCKET/backups/postgres/"
#     if [ $? -eq 0 ]; then
#         echo -e "${GREEN}✓ Uploaded to S3${NC}"
#     else
#         echo -e "${RED}✗ S3 upload failed${NC}"
#     fi
# fi

# List recent backups
echo -e "\n${GREEN}Recent backups:${NC}"
ls -lh "$BACKUP_DIR" | tail -n 5

echo -e "\n${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] Backup completed successfully!${NC}"
