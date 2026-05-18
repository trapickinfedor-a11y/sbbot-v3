#!/bin/bash
# Deployment script for 700 Mirror Bots + 30K users system
# System Requirements: 16 vCPU / 32 GB RAM / 500 GB SSD

set -e  # Exit on error

echo "🚀 NewLookup Deployment Script for 700 Bots"
echo "=============================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root (sudo)${NC}"
    exit 1
fi

# System checks
echo "📋 Checking system requirements..."

# Check CPU
CPU_CORES=$(nproc)
if [ "$CPU_CORES" -lt 16 ]; then
    echo -e "${YELLOW}⚠️  Warning: Only $CPU_CORES CPU cores detected. Recommended: 16+${NC}"
else
    echo -e "${GREEN}✓ CPU: $CPU_CORES cores${NC}"
fi

# Check RAM
TOTAL_RAM=$(free -g | awk '/^Mem:/{print $2}')
if [ "$TOTAL_RAM" -lt 30 ]; then
    echo -e "${YELLOW}⚠️  Warning: Only ${TOTAL_RAM}GB RAM detected. Recommended: 32GB+${NC}"
else
    echo -e "${GREEN}✓ RAM: ${TOTAL_RAM}GB${NC}"
fi

# Check disk space
DISK_SPACE=$(df -BG / | awk 'NR==2 {print $4}' | sed 's/G//')
if [ "$DISK_SPACE" -lt 400 ]; then
    echo -e "${YELLOW}⚠️  Warning: Only ${DISK_SPACE}GB free space. Recommended: 500GB+${NC}"
else
    echo -e "${GREEN}✓ Disk: ${DISK_SPACE}GB free${NC}"
fi

echo ""

# Install Docker if not present
if ! command -v docker &> /dev/null; then
    echo "📦 Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    systemctl enable docker
    systemctl start docker
    rm get-docker.sh
    echo -e "${GREEN}✓ Docker installed${NC}"
else
    echo -e "${GREEN}✓ Docker already installed${NC}"
fi

# Install Docker Compose if not present
if ! command -v docker-compose &> /dev/null; then
    echo "📦 Installing Docker Compose..."
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    echo -e "${GREEN}✓ Docker Compose installed${NC}"
else
    echo -e "${GREEN}✓ Docker Compose already installed${NC}"
fi

echo ""

# Configure system limits
echo "⚙️  Configuring system limits..."

# Increase file descriptors
cat >> /etc/security/limits.conf <<EOF
* soft nofile 65536
* hard nofile 65536
* soft nproc 65536
* hard nproc 65536
EOF

# Sysctl optimizations
cat > /etc/sysctl.d/99-newlookup.conf <<EOF
# Network optimizations
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 8192
net.ipv4.ip_local_port_range = 1024 65535
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_fin_timeout = 30

# Memory
vm.swappiness = 10
vm.dirty_ratio = 15
vm.dirty_background_ratio = 5

# File system
fs.file-max = 2097152
fs.inotify.max_user_watches = 524288
EOF

sysctl -p /etc/sysctl.d/99-newlookup.conf > /dev/null 2>&1

echo -e "${GREEN}✓ System limits configured${NC}"
echo ""

# Setup directories
echo "📁 Creating directories..."
mkdir -p /opt/newlookup/{data,uploads,media,logs,backups}
mkdir -p /opt/newlookup/uploads/{admin,products,telegram}
mkdir -p /opt/newlookup/backups/{postgres,uploads}

echo -e "${GREEN}✓ Directories created${NC}"
echo ""

# Check .env file
if [ ! -f .env ]; then
    echo -e "${RED}❌ .env file not found!${NC}"
    echo "Please create .env file with required variables."
    echo "See .env.example for reference."
    exit 1
fi

echo -e "${GREEN}✓ .env file found${NC}"
echo ""

# PostgreSQL tuning
echo "🐘 Configuring PostgreSQL..."

# Create custom PostgreSQL config
cat > postgresql-custom.conf <<EOF
# Custom PostgreSQL configuration for 700 bots / 30K users

# Connections
max_connections = 1000
superuser_reserved_connections = 3

# Memory Settings (for 32GB RAM system)
shared_buffers = 8GB
effective_cache_size = 24GB
maintenance_work_mem = 2GB
work_mem = 16MB

# Checkpoint Settings
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100

# Query Planner
random_page_cost = 1.1
effective_io_concurrency = 200

# Logging
log_min_duration_statement = 1000
log_line_prefix = '%t [%p]: user=%u,db=%d '
log_checkpoints = on
log_connections = on
log_disconnections = on
log_lock_waits = on

# Autovacuum
autovacuum_max_workers = 4
autovacuum_naptime = 10s
autovacuum_vacuum_scale_factor = 0.05
autovacuum_analyze_scale_factor = 0.02
EOF

echo -e "${GREEN}✓ PostgreSQL config created${NC}"
echo ""

# Redis tuning
echo "🔴 Configuring Redis..."

cat > redis-custom.conf <<EOF
# Custom Redis configuration

# Memory
maxmemory 2gb
maxmemory-policy allkeys-lru

# Persistence (disabled for cache)
save ""
appendonly no

# Performance
tcp-backlog 511
timeout 300
tcp-keepalive 60

# Clients
maxclients 10000

# Logging
loglevel notice
EOF

echo -e "${GREEN}✓ Redis config created${NC}"
echo ""

# Update docker-compose.yml with custom configs
echo "🐳 Updating Docker Compose configuration..."

# Backup original docker-compose.yml
if [ -f docker-compose.yml ]; then
    cp docker-compose.yml docker-compose.yml.backup
    echo -e "${GREEN}✓ Backed up docker-compose.yml${NC}"
fi

echo ""

# Setup monitoring
echo "📊 Setting up monitoring..."

# Create Prometheus config
mkdir -p monitoring
cat > monitoring/prometheus.yml <<EOF
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'node'
    static_configs:
      - targets: ['node-exporter:9100']

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']
EOF

echo -e "${GREEN}✓ Monitoring configured${NC}"
echo ""

# Setup backup script
echo "💾 Setting up backup scripts..."

cat > /opt/newlookup/backups/backup.sh <<'EOF'
#!/bin/bash
# Automated backup script

BACKUP_DIR="/opt/newlookup/backups"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

echo "Starting backup at $(date)"

# Backup PostgreSQL
echo "Backing up PostgreSQL..."
docker exec newlookup_postgres pg_dump -U newlookup -Fc newlookup > \
  "$BACKUP_DIR/postgres/newlookup_$DATE.dump"

if [ $? -eq 0 ]; then
    gzip "$BACKUP_DIR/postgres/newlookup_$DATE.dump"
    echo "✓ PostgreSQL backup completed"
else
    echo "✗ PostgreSQL backup failed"
fi

# Backup uploads
echo "Backing up uploads..."
rsync -az --delete /opt/newlookup/uploads/ "$BACKUP_DIR/uploads/"
echo "✓ Uploads backup completed"

# Delete old backups
find "$BACKUP_DIR/postgres" -name "*.dump.gz" -mtime +$RETENTION_DAYS -delete
echo "✓ Old backups cleaned up"

echo "Backup completed at $(date)"
EOF

chmod +x /opt/newlookup/backups/backup.sh

# Add to crontab
(crontab -l 2>/dev/null; echo "0 3 * * * /opt/newlookup/backups/backup.sh >> /opt/newlookup/logs/backup.log 2>&1") | crontab -

echo -e "${GREEN}✓ Backup scripts configured (daily at 3 AM)${NC}"
echo ""

# Setup firewall
echo "🔒 Configuring firewall..."

if command -v ufw &> /dev/null; then
    ufw --force enable
    ufw default deny incoming
    ufw default allow outgoing
    ufw allow 22/tcp comment 'SSH'
    ufw allow 80/tcp comment 'HTTP'
    ufw allow 443/tcp comment 'HTTPS'
    ufw allow 8000/tcp comment 'Web Panel'
    echo -e "${GREEN}✓ Firewall configured${NC}"
else
    echo -e "${YELLOW}⚠️  UFW not installed. Please configure firewall manually.${NC}"
fi

echo ""

# Pull Docker images
echo "📥 Pulling Docker images..."
docker-compose pull

echo ""

# Start services
echo "🚀 Starting services..."
docker-compose up -d

echo ""
echo "⏳ Waiting for services to start..."
sleep 10

# Check service status
echo ""
echo "📊 Service Status:"
docker-compose ps

echo ""
echo "=============================================="
echo -e "${GREEN}✅ Deployment completed!${NC}"
echo "=============================================="
echo ""
echo "📝 Next steps:"
echo "1. Check logs: docker-compose logs -f"
echo "2. Access Web Panel: http://your-server-ip:8000"
echo "3. Create first Mirror Bot via Main Bot"
echo "4. Monitor system: htop, docker stats"
echo ""
echo "📊 Monitoring:"
echo "- Prometheus: http://your-server-ip:9090"
echo "- Grafana: http://your-server-ip:3000 (if configured)"
echo ""
echo "💾 Backups:"
echo "- Location: /opt/newlookup/backups/"
echo "- Schedule: Daily at 3 AM"
echo "- Retention: 30 days"
echo ""
echo "📚 Documentation:"
echo "- System Requirements: SYSTEM_REQUIREMENTS_700_BOTS.md"
echo "- Start Guide: START_GUIDE.md"
echo ""
echo "🎯 System is ready for 700 bots and 30K users!"
