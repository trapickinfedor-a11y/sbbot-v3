# Production Deployment Runbook for NewLookup
# Complete guide for deploying to production server

## 📋 Prerequisites

### Server Requirements
- **OS**: Ubuntu 22.04 LTS
- **CPU**: 16 vCPU (minimum)
- **RAM**: 32 GB (minimum)
- **Storage**: 500 GB NVMe SSD
- **Network**: 1 Gbps
- **Provider**: Hetzner AX102 (recommended) or Vultr High Frequency

### Required Access
- Root SSH access to server
- Domain name (optional, for SSL)
- Email for alerts (optional)

---

## 🚀 Step 1: Initial Server Setup

### 1.1 Connect to Server
```bash
ssh root@your-server-ip
```

### 1.2 Update System
```bash
apt update && apt upgrade -y
apt install -y curl wget git vim htop
```

### 1.3 Create Application User
```bash
useradd -m -s /bin/bash newlookup
usermod -aG sudo newlookup
mkdir -p /opt/newlookup
chown -R newlookup:newlookup /opt/newlookup
```

### 1.4 Install Docker
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
usermod -aG docker newlookup
systemctl enable docker
systemctl start docker
```

### 1.5 Install Docker Compose
```bash
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
docker-compose --version
```

---

## 🔒 Step 2: Security Setup

### 2.1 Configure Firewall (UFW)
```bash
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw allow 8000/tcp  # Web Panel (restrict to your IP in production)
ufw enable
ufw status
```

### 2.2 Install Fail2ban
```bash
apt install -y fail2ban
systemctl enable fail2ban
systemctl start fail2ban

# Create jail configuration
cat > /etc/fail2ban/jail.local << 'EOF'
[sshd]
enabled = true
port = 22
maxretry = 3
bantime = 3600
findtime = 600

[nginx-limit-req]
enabled = true
filter = nginx-limit-req
logpath = /var/log/nginx/error.log
maxretry = 5
bantime = 3600
EOF

systemctl restart fail2ban
```

### 2.3 Secure SSH
```bash
# Edit SSH config
sed -i 's/#PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
systemctl restart sshd
```

---

## 📦 Step 3: Deploy Application

### 3.1 Clone Repository
```bash
su - newlookup
cd /opt/newlookup
git clone https://github.com/your-org/newlookup.git .
```

### 3.2 Create Environment File
```bash
cp .env.example .env
vim .env
```

**Required environment variables:**
```bash
# Database
POSTGRES_USER=newlookup
POSTGRES_PASSWORD=<generate-strong-password>
POSTGRES_DB=newlookup
DATABASE_URL=postgresql+asyncpg://newlookup:<password>@postgres:5432/newlookup

# Redis
REDIS_PASSWORD=<generate-strong-password>
REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0

# Bot Tokens (get from @BotFather)
MAIN_BOT_TOKEN=<your-main-bot-token>
SUPPORT_BOT_TOKEN=<your-support-bot-token>
WORKER_BOT_TOKEN=<your-worker-bot-token>
SELLER_BOT_TOKEN=<your-seller-bot-token>
MARKETER_BOT_TOKEN=<your-marketer-bot-token>

# Admin
ADMIN_IDS=<your-telegram-id>
ADMIN_USERNAME=admin
ADMIN_PASSWORD=<generate-strong-password>

# Security
WEB_PANEL_SECRET_KEY=<generate-random-64-char-string>
INTERNAL_API_TOKEN=<generate-random-32-char-string>
LOOKUP_ADMIN_TOKEN=<generate-random-32-char-string>

# Channels
ORDERS_CHANNEL_ID=<your-orders-channel-id>

# Web Panel
WEB_PANEL_PORT=8000
SELLER_MINI_APP_URL=https://your-domain.com/seller-app
```

**Generate secure passwords:**
```bash
# Generate random passwords
openssl rand -base64 32
openssl rand -hex 32
```

### 3.3 Create Required Directories
```bash
mkdir -p /opt/newlookup/{data,uploads,media,logs}
mkdir -p /opt/backups/{postgres,uploads}
mkdir -p /var/log/newlookup
chown -R newlookup:newlookup /opt/newlookup
chown -R newlookup:newlookup /opt/backups
chown -R newlookup:newlookup /var/log/newlookup
```

### 3.4 Build and Start Services
```bash
cd /opt/newlookup

# Build images
docker-compose -f docker-compose.production.yml build

# Start database first
docker-compose -f docker-compose.production.yml up -d postgres redis

# Wait for database to be ready
sleep 10

# Run database migrations
docker-compose -f docker-compose.production.yml run --rm main_bot alembic upgrade head

# Start all services
docker-compose -f docker-compose.production.yml up -d

# Check status
docker-compose -f docker-compose.production.yml ps
```

---

## 🔍 Step 4: Verify Deployment

### 4.1 Check Container Status
```bash
docker ps
docker-compose -f docker-compose.production.yml logs --tail=50
```

### 4.2 Check Database
```bash
docker exec newlookup_postgres psql -U newlookup -d newlookup -c "SELECT version();"
docker exec newlookup_postgres psql -U newlookup -d newlookup -c "SELECT count(*) FROM users;"
```

### 4.3 Check Redis
```bash
docker exec newlookup_redis redis-cli -a ${REDIS_PASSWORD} ping
docker exec newlookup_redis redis-cli -a ${REDIS_PASSWORD} INFO memory
```

### 4.4 Check Web Panel
```bash
curl http://localhost:8000/health
```

### 4.5 Test Bot
- Send `/start` to your main bot on Telegram
- Verify bot responds correctly

---

## 📊 Step 5: Setup Monitoring

### 5.1 Start Monitoring Stack
```bash
cd /opt/newlookup
docker-compose -f docker-compose.monitoring.yml up -d
```

### 5.2 Access Grafana
- URL: `http://your-server-ip:3000`
- Default credentials: `admin / admin`
- Change password on first login

### 5.3 Configure Prometheus Data Source
1. Go to Configuration → Data Sources
2. Add Prometheus
3. URL: `http://prometheus:9090`
4. Save & Test

### 5.4 Import Dashboards
- Node Exporter Dashboard: ID 1860
- PostgreSQL Dashboard: ID 9628
- Redis Dashboard: ID 11835
- Docker Dashboard: ID 893

---

## 🔄 Step 6: Setup Backups

### 6.1 Make Scripts Executable
```bash
chmod +x /opt/newlookup/scripts/*.sh
```

### 6.2 Test Backup Scripts
```bash
# Test PostgreSQL backup
/opt/newlookup/scripts/backup_postgres.sh

# Test uploads backup
/opt/newlookup/scripts/backup_uploads.sh

# Verify backups created
ls -lh /opt/backups/postgres/
ls -lh /opt/backups/uploads/
```

### 6.3 Setup Cron Jobs
```bash
crontab -e
```

Add the following lines:
```cron
# PostgreSQL daily backup at 3 AM
0 3 * * * /opt/newlookup/scripts/backup_postgres.sh >> /var/log/newlookup/backup_postgres.log 2>&1

# Uploads daily backup at 4 AM
0 4 * * * /opt/newlookup/scripts/backup_uploads.sh >> /var/log/newlookup/backup_uploads.log 2>&1

# Health check every 5 minutes
*/5 * * * * /opt/newlookup/scripts/health_check.sh >> /var/log/newlookup/health_check.log 2>&1

# Cleanup old logs daily at 1 AM
0 1 * * * find /var/log/newlookup -name "*.log" -mtime +30 -delete

# Docker cleanup weekly on Monday at 1 AM
0 1 * * 1 docker system prune -af --volumes --filter "until=168h" >> /var/log/newlookup/docker_cleanup.log 2>&1
```

### 6.4 Test Restore
```bash
# Test database restore (CAUTION: This will replace current database)
/opt/newlookup/scripts/restore_postgres.sh /opt/backups/postgres/latest_backup.dump.gz
```

---

## 🌐 Step 7: SSL/TLS Setup (Optional but Recommended)

### 7.1 Install Certbot
```bash
apt install -y certbot python3-certbot-nginx
```

### 7.2 Install Nginx
```bash
apt install -y nginx
systemctl enable nginx
systemctl start nginx
```

### 7.3 Configure Nginx
```bash
cat > /etc/nginx/sites-available/newlookup << 'EOF'
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

ln -s /etc/nginx/sites-available/newlookup /etc/nginx/sites-enabled/
nginx -t
systemctl reload nginx
```

### 7.4 Obtain SSL Certificate
```bash
certbot --nginx -d your-domain.com
```

---

## 📈 Step 8: Performance Tuning

### 8.1 Optimize PostgreSQL
```bash
# Already configured in config/postgresql.conf
# Verify settings
docker exec newlookup_postgres psql -U newlookup -c "SHOW shared_buffers;"
docker exec newlookup_postgres psql -U newlookup -c "SHOW max_connections;"
```

### 8.2 Create Database Indexes
```bash
docker exec newlookup_postgres psql -U newlookup -d newlookup << 'EOF'
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_mirror_bot_id ON users(mirror_bot_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_user_id ON orders(user_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_created_at ON orders(created_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_seller_orders_seller_id ON seller_orders(seller_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_seller_orders_status ON seller_orders(status);
EOF
```

### 8.3 Optimize System
```bash
# Increase file descriptors
echo "* soft nofile 65536" >> /etc/security/limits.conf
echo "* hard nofile 65536" >> /etc/security/limits.conf

# Optimize network
cat >> /etc/sysctl.conf << 'EOF'
net.core.somaxconn = 1024
net.ipv4.tcp_max_syn_backlog = 2048
net.ipv4.ip_local_port_range = 10000 65535
EOF

sysctl -p
```

---

## 🔧 Step 9: Maintenance Commands

### View Logs
```bash
# All services
docker-compose -f docker-compose.production.yml logs -f

# Specific service
docker-compose -f docker-compose.production.yml logs -f main_bot

# Last 100 lines
docker-compose -f docker-compose.production.yml logs --tail=100 main_bot
```

### Restart Services
```bash
# Restart all
docker-compose -f docker-compose.production.yml restart

# Restart specific service
docker-compose -f docker-compose.production.yml restart main_bot
```

### Update Application
```bash
cd /opt/newlookup
git pull
docker-compose -f docker-compose.production.yml build
docker-compose -f docker-compose.production.yml up -d
```

### Database Maintenance
```bash
# Vacuum analyze
docker exec newlookup_postgres vacuumdb -U newlookup -d newlookup --analyze --verbose

# Check database size
docker exec newlookup_postgres psql -U newlookup -d newlookup -c "SELECT pg_size_pretty(pg_database_size('newlookup'));"

# Check table sizes
docker exec newlookup_postgres psql -U newlookup -d newlookup -c "SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size FROM pg_tables WHERE schemaname = 'public' ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC LIMIT 10;"
```

---

## 🚨 Step 10: Troubleshooting

### Container Won't Start
```bash
# Check logs
docker logs newlookup_main_bot

# Check resource usage
docker stats

# Restart container
docker restart newlookup_main_bot
```

### Database Connection Issues
```bash
# Check PostgreSQL is running
docker ps | grep postgres

# Check connections
docker exec newlookup_postgres psql -U newlookup -d newlookup -c "SELECT count(*) FROM pg_stat_activity;"

# Kill idle connections
docker exec newlookup_postgres psql -U newlookup -d newlookup -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle' AND state_change < current_timestamp - INTERVAL '10 minutes';"
```

### High Memory Usage
```bash
# Check memory usage
free -h
docker stats --no-stream

# Restart services if needed
docker-compose -f docker-compose.production.yml restart
```

### Disk Space Issues
```bash
# Check disk usage
df -h

# Clean Docker
docker system prune -af --volumes

# Clean old logs
find /var/log/newlookup -name "*.log" -mtime +7 -delete

# Clean old backups
find /opt/backups -name "*.dump.gz" -mtime +30 -delete
```

---

## ✅ Deployment Checklist

- [ ] Server meets minimum requirements (16 vCPU / 32 GB RAM)
- [ ] Ubuntu 22.04 LTS installed
- [ ] Docker and Docker Compose installed
- [ ] Firewall configured (UFW)
- [ ] Fail2ban installed and configured
- [ ] Application cloned to /opt/newlookup
- [ ] .env file created with all required variables
- [ ] Required directories created
- [ ] Database initialized and migrated
- [ ] All containers running
- [ ] Bots responding on Telegram
- [ ] Web Panel accessible
- [ ] Monitoring stack running
- [ ] Grafana dashboards configured
- [ ] Backup scripts tested
- [ ] Cron jobs configured
- [ ] SSL certificate obtained (if using domain)
- [ ] Health checks passing
- [ ] Performance indexes created

---

## 📞 Support

For issues or questions:
1. Check logs: `docker-compose logs`
2. Run health check: `/opt/newlookup/scripts/health_check.sh`
3. Check monitoring: Grafana dashboards
4. Review documentation in `/opt/newlookup/docs/`

---

**Deployment completed! System is ready for production use. 🚀**
