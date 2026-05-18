#!/bin/bash
# Database Optimization Script
# Создаёт индексы и оптимизирует производительность

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}Starting database optimization...${NC}\n"

# Check if container is running
if ! docker ps | grep -q "newlookup_postgres"; then
    echo -e "${RED}Error: PostgreSQL container is not running${NC}"
    exit 1
fi

# Create indexes
echo -e "${YELLOW}Creating performance indexes...${NC}"

docker exec newlookup_postgres psql -U newlookup -d newlookup << 'EOF'
-- Users table indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_mirror_bot_id ON users(mirror_bot_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_created_at ON users(created_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_balance ON users(balance) WHERE balance > 0;

-- Orders table indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_user_id ON orders(user_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_created_at ON orders(created_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_seller_id ON orders(seller_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_category ON orders(category);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_status_created ON orders(status, created_at);

-- Seller orders indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_seller_orders_seller_id ON seller_orders(seller_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_seller_orders_status ON seller_orders(status);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_seller_orders_created_at ON seller_orders(created_at);

-- Transactions indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transactions_user_id ON transactions(user_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transactions_type ON transactions(transaction_type);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transactions_created_at ON transactions(created_at);

-- Disputes indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_disputes_order_id ON disputes(order_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_disputes_status ON disputes(status);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_disputes_seller_id ON disputes(seller_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_disputes_created_at ON disputes(created_at);

-- Sellers indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sellers_telegram_id ON sellers(telegram_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sellers_status ON sellers(status);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sellers_seller_type ON sellers(seller_type);

-- Workers indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_workers_telegram_id ON workers(telegram_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_workers_status ON workers(status);

-- Withdrawals indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_seller_withdrawals_seller_id ON seller_withdrawals(seller_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_seller_withdrawals_status ON seller_withdrawals(status);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_worker_withdrawals_worker_id ON worker_withdrawals(worker_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_worker_withdrawals_status ON worker_withdrawals(status);

-- Mirror bots indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_mirror_bots_bot_token ON mirror_bots(bot_token);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_mirror_bots_is_active ON mirror_bots(is_active);

-- Broadcasts indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_broadcasts_status ON broadcasts(status);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_broadcasts_scheduled_at ON broadcasts(scheduled_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_broadcasts_created_at ON broadcasts(created_at);

-- Moderation items indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bank_items_seller_id ON bank_items(seller_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bank_items_status ON bank_items(moderation_status);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_cc_items_seller_id ON cc_items(seller_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_cc_items_status ON cc_items(moderation_status);

EOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Indexes created successfully${NC}\n"
else
    echo -e "${RED}✗ Failed to create indexes${NC}"
    exit 1
fi

# Analyze tables
echo -e "${YELLOW}Analyzing tables...${NC}"
docker exec newlookup_postgres psql -U newlookup -d newlookup -c "ANALYZE;"
echo -e "${GREEN}✓ Analysis complete${NC}\n"

# Vacuum
echo -e "${YELLOW}Running vacuum...${NC}"
docker exec newlookup_postgres vacuumdb -U newlookup -d newlookup --analyze --verbose
echo -e "${GREEN}✓ Vacuum complete${NC}\n"

# Show table sizes
echo -e "${YELLOW}Table sizes:${NC}"
docker exec newlookup_postgres psql -U newlookup -d newlookup << 'EOF'
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS table_size,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) AS indexes_size
FROM pg_tables 
WHERE schemaname = 'public' 
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC 
LIMIT 15;
EOF

echo -e "\n${GREEN}Database optimization complete!${NC}"
