#!/bin/bash
# Uploads Backup Script for NewLookup
# Создаёт бэкапы загруженных файлов (товары, медиа)

set -e

# Configuration
SOURCE_DIR="/opt/newlookup/uploads"
BACKUP_DIR="/opt/backups/uploads"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=14

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Create backup directory
mkdir -p "$BACKUP_DIR"

echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} Starting uploads backup..."

# Check if source directory exists
if [ ! -d "$SOURCE_DIR" ]; then
    echo -e "${RED}Error: Source directory $SOURCE_DIR does not exist${NC}"
    exit 1
fi

# Create incremental backup using rsync
echo -e "${YELLOW}Syncing files...${NC}"
rsync -avz --delete \
    --exclude='*.tmp' \
    --exclude='.DS_Store' \
    "$SOURCE_DIR/" "$BACKUP_DIR/latest/"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Files synced successfully${NC}"
    
    # Get directory size
    SIZE=$(du -sh "$BACKUP_DIR/latest" | cut -f1)
    echo -e "${GREEN}Backup size: $SIZE${NC}"
    
    # Count files
    FILES=$(find "$BACKUP_DIR/latest" -type f | wc -l)
    echo -e "${GREEN}Total files: $FILES${NC}"
else
    echo -e "${RED}✗ Sync failed${NC}"
    exit 1
fi

# Create dated snapshot (hard links to save space)
SNAPSHOT_DIR="$BACKUP_DIR/snapshot_$DATE"
echo -e "${YELLOW}Creating snapshot: $SNAPSHOT_DIR${NC}"
cp -al "$BACKUP_DIR/latest" "$SNAPSHOT_DIR"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Snapshot created${NC}"
else
    echo -e "${RED}✗ Snapshot creation failed${NC}"
fi

# Delete old snapshots
echo -e "${YELLOW}Cleaning up old snapshots (older than $RETENTION_DAYS days)...${NC}"
find "$BACKUP_DIR" -maxdepth 1 -name "snapshot_*" -mtime +$RETENTION_DAYS -exec rm -rf {} \;
echo -e "${GREEN}✓ Cleanup completed${NC}"

# List recent snapshots
echo -e "\n${GREEN}Recent snapshots:${NC}"
ls -lh "$BACKUP_DIR" | grep "snapshot_" | tail -n 5

echo -e "\n${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] Uploads backup completed!${NC}"
