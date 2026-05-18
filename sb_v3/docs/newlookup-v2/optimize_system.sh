#!/bin/bash
# System optimization script for 700 bots deployment
# Run after initial deployment to optimize system performance

set -e

echo "🔧 NewLookup System Optimization"
echo "================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (sudo)"
    exit 1
fi

# 1. Optimize PostgreSQL
echo "📊 Optimizing PostgreSQL..."

# Calculate optimal settings based on available RAM
TOTAL_RAM_GB=$(free -g | awk '/^Mem:/{print $2}')
SHARED_BUFFERS=$((TOTAL_RAM_GB / 4))
EFFECTIVE_CACHE=$((TOTAL_RAM_GB * 3 / 4))

cat > /tmp/pg_optimize.sql <<EOF
-- Connection settings
ALTER SYSTEM SET max_connections = 1000;
ALTER SYSTEM SET superuser_reserved_connections = 3;

-- Memory settings
ALTER SYSTEM SET shared_buffers = '${SHARED_BUFFERS}GB';
ALTER SYSTEM SET effective_cache_size = '${EFFECTIVE_CACHE}GB';
ALTER SYSTEM SET maintenance_work_mem = '2GB';
ALTER SYSTEM SET work_mem = '16MB';

-- Checkpoint settings
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';

-- Query planner
ALTER SYSTEM SET random_page_cost = 1.1;
ALTER SYSTEM SET effective_io_concurrency = 200;

-- Logging
ALTER SYSTEM SET log_min_duration_statement = 1000;
ALTER SYSTEM SET log_checkpoints = on;
ALTER SYSTEM SET log_connections = on;
ALTER SYSTEM SET log_disconnections = on;
ALTER SYSTEM SET log_lock_waits = on;

-- Autovacuum
ALTER SYSTEM SET autovacuum_max_workers = 4;
ALTER SYSTEM SET autovacuum_naptime = '10s';
ALTER SYSTEM SET autovacuum_vacuum_scale_factor = 0.05;
ALTER SYSTEM SET autovacuum_analyze_scale_factor = 0.02;
EOF

docker exec -i newlookup_postgres psql -U newlookup -d newlookup < /tmp/pg_optimize.sql
rm /tmp/pg_optimize.sql

echo "✓ PostgreSQL optimized"
echo ""

# 2. Create database indexes
echo "📇 Creating database indexes..."

cat > /tmp/create_indexes.sql <<'EOF'
-- Users indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_bot_id ON users(bot_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_created_at ON users(created_at);

-- Orders indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_user_id ON orders(user_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_created_at ON orders(created_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_bot_id ON orders(bot_id);

-- Transactions indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transactions_user_id ON transactions(user_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transactions_account_type ON transactions(account_type);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transactions_status ON transactions(status);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transactions_created_at ON transactions(created_at);

-- Seller orders indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_seller_orders_seller_id ON seller_orders(seller_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_seller_orders_buyer_id ON seller_orders(buyer_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_seller_orders_status ON seller_orders(status);

-- Worker orders indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_worker_orders_worker_id ON worker_orders(worker_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_worker_orders_status ON worker_orders(status);

-- Mirror bots indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_mirror_bots_owner_id ON mirror_bots(owner_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_mirror_bots_status ON mirror_bots(status);

-- Sellers indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sellers_telegram_id ON sellers(telegram_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sellers_status ON sellers(status);

-- Workers indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_workers_telegram_id ON workers(telegram_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_workers_status ON workers(status);

-- Marketers indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_marketers_telegram_id ON marketers(telegram_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_marketers_referral_code ON marketers(referral_code);

-- Support tickets indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_support_messages_user_id ON support_messages(user_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_support_messages_status ON support_messages(status);

-- Composite indexes for common queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_user_status ON orders(user_id, status);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_bot_created ON orders(bot_id, created_at DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transactions_user_type ON transactions(user_id, transaction_type);
EOF

docker exec -i newlookup_postgres psql -U newlookup -d newlookup < /tmp/create_indexes.sql
rm /tmp/create_indexes.sql

echo "✓ Database indexes created"
echo ""

# 3. Optimize system settings
echo "⚙️  Optimizing system settings..."

# Increase file descriptors
cat >> /etc/security/limits.conf <<EOF
* soft nofile 65536
* hard nofile 65536
* soft nproc 65536
* hard nproc 65536
root soft nofile 65536
root hard nofile 65536
EOF

# Sysctl optimizations
cat > /etc/sysctl.d/99-newlookup-optimized.conf <<EOF
# Network optimizations
net.core.somaxconn = 65535
net.core.netdev_max_backlog = 5000
net.ipv4.tcp_max_syn_backlog = 8192
net.ipv4.ip_local_port_range = 1024 65535
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_fin_timeout = 30
net.ipv4.tcp_keepalive_time = 300
net.ipv4.tcp_keepalive_probes = 5
net.ipv4.tcp_keepalive_intvl = 15

# Memory management
vm.swappiness = 10
vm.dirty_ratio = 15
vm.dirty_background_ratio = 5
vm.overcommit_memory = 1

# File system
fs.file-max = 2097152
fs.inotify.max_user_watches = 524288
fs.inotify.max_user_instances = 512

# Kernel
kernel.pid_max = 4194304
EOF

sysctl -p /etc/sysctl.d/99-newlookup-optimized.conf > /dev/null 2>&1

echo "✓ System settings optimized"
echo ""

# 4. Setup log rotation
echo "📝 Setting up log rotation..."

cat > /etc/logrotate.d/newlookup <<EOF
/opt/newlookup/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 root root
    sharedscripts
    postrotate
        docker-compose -f /opt/newlookup/docker-compose.yml restart > /dev/null 2>&1 || true
    endscript
}
EOF

echo "✓ Log rotation configured"
echo ""

# 5. Setup monitoring alerts
echo "📊 Setting up monitoring alerts..."

mkdir -p /opt/newlookup/monitoring/alerts

cat > /opt/newlookup/monitoring/alerts/rules.yml <<EOF
groups:
  - name: newlookup_alerts
    interval: 30s
    rules:
      # High CPU usage
      - alert: HighCPUUsage
        expr: 100 - (avg by(instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High CPU usage detected"
          description: "CPU usage is above 80% for 5 minutes"

      # High memory usage
      - alert: HighMemoryUsage
        expr: (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100 > 85
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage detected"
          description: "Memory usage is above 85%"

      # Disk space low
      - alert: DiskSpaceLow
        expr: (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"}) * 100 < 15
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Disk space is low"
          description: "Less than 15% disk space available"

      # PostgreSQL down
      - alert: PostgreSQLDown
        expr: pg_up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "PostgreSQL is down"
          description: "PostgreSQL database is not responding"

      # Redis down
      - alert: RedisDown
        expr: redis_up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Redis is down"
          description: "Redis cache is not responding"

      # Too many database connections
      - alert: TooManyDatabaseConnections
        expr: pg_stat_database_numbackends > 800
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Too many database connections"
          description: "More than 800 active connections to PostgreSQL"

      # High response time
      - alert: HighResponseTime
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High response time"
          description: "95th percentile response time is above 2 seconds"
EOF

echo "✓ Monitoring alerts configured"
echo ""

# 6. Optimize Docker
echo "🐳 Optimizing Docker..."

cat > /etc/docker/daemon.json <<EOF
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "50m",
    "max-file": "5"
  },
  "storage-driver": "overlay2",
  "default-ulimits": {
    "nofile": {
      "Name": "nofile",
      "Hard": 65536,
      "Soft": 65536
    }
  }
}
EOF

systemctl restart docker

echo "✓ Docker optimized"
echo ""

# 7. Setup health check script
echo "🏥 Setting up health checks..."

cat > /opt/newlookup/health_check.sh <<'EOF'
#!/bin/bash
# Health check script

ERRORS=0

# Check PostgreSQL
if ! docker exec newlookup_postgres pg_isready -U newlookup > /dev/null 2>&1; then
    echo "❌ PostgreSQL is down"
    ERRORS=$((ERRORS + 1))
else
    echo "✓ PostgreSQL is healthy"
fi

# Check Redis
if ! docker exec newlookup_redis redis-cli -a "${REDIS_PASSWORD:-changeme_redis}" ping > /dev/null 2>&1; then
    echo "❌ Redis is down"
    ERRORS=$((ERRORS + 1))
else
    echo "✓ Redis is healthy"
fi

# Check Main Bot
if ! docker ps | grep newlookup_main_bot | grep -q "Up"; then
    echo "❌ Main Bot is down"
    ERRORS=$((ERRORS + 1))
else
    echo "✓ Main Bot is healthy"
fi

# Check Web Panel
if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "❌ Web Panel is down"
    ERRORS=$((ERRORS + 1))
else
    echo "✓ Web Panel is healthy"
fi

# Check disk space
DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 85 ]; then
    echo "⚠️  Disk usage is high: ${DISK_USAGE}%"
    ERRORS=$((ERRORS + 1))
else
    echo "✓ Disk usage is OK: ${DISK_USAGE}%"
fi

# Check memory
MEM_USAGE=$(free | awk '/Mem:/ {printf "%.0f", $3/$2 * 100}')
if [ "$MEM_USAGE" -gt 90 ]; then
    echo "⚠️  Memory usage is high: ${MEM_USAGE}%"
    ERRORS=$((ERRORS + 1))
else
    echo "✓ Memory usage is OK: ${MEM_USAGE}%"
fi

if [ $ERRORS -gt 0 ]; then
    echo ""
    echo "❌ Health check failed with $ERRORS errors"
    exit 1
else
    echo ""
    echo "✅ All systems healthy"
    exit 0
fi
EOF

chmod +x /opt/newlookup/health_check.sh

# Add to crontab (every 5 minutes)
(crontab -l 2>/dev/null | grep -v health_check.sh; echo "*/5 * * * * /opt/newlookup/health_check.sh >> /opt/newlookup/logs/health_check.log 2>&1") | crontab -

echo "✓ Health checks configured"
echo ""

# 8. Restart services to apply changes
echo "🔄 Restarting services..."

cd /opt/newlookup
docker-compose restart postgres redis

echo "✓ Services restarted"
echo ""

# 9. Run VACUUM ANALYZE
echo "🧹 Running database maintenance..."

docker exec newlookup_postgres psql -U newlookup -d newlookup -c "VACUUM ANALYZE;"

echo "✓ Database maintenance completed"
echo ""

echo "================================="
echo "✅ Optimization completed!"
echo "================================="
echo ""
echo "📊 System Status:"
echo "- CPU cores: $(nproc)"
echo "- Total RAM: ${TOTAL_RAM_GB}GB"
echo "- PostgreSQL shared_buffers: ${SHARED_BUFFERS}GB"
echo "- PostgreSQL effective_cache_size: ${EFFECTIVE_CACHE}GB"
echo ""
echo "📝 Next steps:"
echo "1. Monitor system: /opt/newlookup/health_check.sh"
echo "2. Check logs: docker-compose logs -f"
echo "3. View metrics: http://localhost:9090 (Prometheus)"
echo "4. View dashboards: http://localhost:3000 (Grafana)"
echo ""
echo "🎯 System is optimized for 700 bots!"
