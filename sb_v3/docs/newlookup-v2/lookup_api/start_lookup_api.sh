#!/bin/bash
# Start Lookup API server

set -e

# Configuration
DB_PATH="${LOOKUP_DB_PATH:-/Users/user/Desktop/прокты/newlookup/data/lookup.db}"
HOST="${LOOKUP_API_HOST:-0.0.0.0}"
PORT="${LOOKUP_API_PORT:-8001}"
ADMIN_TOKEN="${LOOKUP_ADMIN_TOKEN:-changeme-set-LOOKUP_ADMIN_TOKEN}"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Lookup API...${NC}"
echo "Database: $DB_PATH"
echo "Host: $HOST"
echo "Port: $PORT"
echo ""

# Check if database exists
if [ ! -f "$DB_PATH" ]; then
    echo -e "${YELLOW}Database not found. Initializing...${NC}"
    export LOOKUP_DB_PATH="$DB_PATH"
    python3 -c "import sys; sys.path.insert(0, '.'); from app import init_db; init_db()"
    echo -e "${GREEN}Database initialized.${NC}"
fi

# Export environment variables
export LOOKUP_DB_PATH="$DB_PATH"
export LOOKUP_ADMIN_TOKEN="$ADMIN_TOKEN"

# Start server
echo -e "${GREEN}Starting server on http://${HOST}:${PORT}${NC}"
echo ""
python3 -m uvicorn app:app --host "$HOST" --port "$PORT" --log-level info
