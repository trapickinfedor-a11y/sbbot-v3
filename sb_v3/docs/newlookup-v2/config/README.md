# Configuration Files

Production-optimized configuration files for NewLookup deployment.

## 📁 Directory Structure

```
config/
├── alerts/
│   └── newlookup_alerts.yml          # Prometheus alert rules
├── grafana/
│   ├── dashboards/
│   │   └── dashboards.yml            # Dashboard provisioning
│   └── datasources/
│       └── datasources.yml           # Data source configuration
├── nginx/
│   └── newlookup.conf                # Nginx reverse proxy
├── crontab.txt                       # Cron job schedule
├── newlookup.service                 # Systemd service file
├── pgbouncer.ini                     # PostgreSQL connection pooling
├── postgresql.conf                   # PostgreSQL optimization
├── prometheus.yml                    # Prometheus configuration
└── redis.conf                        # Redis configuration
```

---

## 🗄️ Database Configuration

### postgresql.conf
**Purpose**: PostgreSQL optimization for 32GB RAM server

**Key Settings**:
- `shared_buffers = 8GB` - 25% of RAM
- `effective_cache_size = 24GB` - 75% of RAM
- `max_connections = 1000` - High concurrency
- `work_mem = 16MB` - Per-operation memory
- `random_page_cost = 1.1` - SSD optimization

**Usage**:
```bash
# Mount in docker-compose.yml
volumes:
  - ./config/postgresql.conf:/etc/postgresql/postgresql.conf:ro
command: postgres -c config_file=/etc/postgresql/postgresql.conf
```

**Tuning**:
- Increase `shared_buffers` for more RAM
- Adjust `max_connections` based on load
- Monitor with: `SHOW shared_buffers;`

---

### pgbouncer.ini
**Purpose**: Connection pooling to reduce database load

**Key Settings**:
- `pool_mode = transaction` - Best for web apps
- `max_client_conn = 2000` - Maximum clients
- `default_pool_size = 100` - Connections per database
- `reserve_pool_size = 25` - Emergency pool

**Usage**:
```bash
# Run PgBouncer container
docker run -d \
  -v ./config/pgbouncer.ini:/etc/pgbouncer/pgbouncer.ini \
  -p 6432:6432 \
  pgbouncer/pgbouncer
```

**When to use**: When connection count exceeds 500

---

## 🔴 Cache Configuration

### redis.conf
**Purpose**: Redis cache optimization

**Key Settings**:
- `maxmemory 2gb` - Maximum memory usage
- `maxmemory-policy allkeys-lru` - Eviction policy
- `save ""` - Disable persistence (cache-only)
- Dangerous commands renamed for security

**Usage**:
```bash
# Mount in docker-compose.yml
command: redis-server /usr/local/etc/redis/redis.conf
volumes:
  - ./config/redis.conf:/usr/local/etc/redis/redis.conf:ro
```

**Tuning**:
- Increase `maxmemory` for more cache
- Enable persistence if needed: `appendonly yes`
- Monitor with: `INFO memory`

---

## 🌐 Web Server Configuration

### nginx/newlookup.conf
**Purpose**: Reverse proxy with SSL/TLS

**Features**:
- HTTP to HTTPS redirect
- SSL/TLS configuration
- Security headers
- Rate limiting
- Static file serving
- WebSocket support

**Usage**:
```bash
# Copy to Nginx sites
cp config/nginx/newlookup.conf /etc/nginx/sites-available/newlookup
ln -s /etc/nginx/sites-available/newlookup /etc/nginx/sites-enabled/
nginx -t
systemctl reload nginx
```

**Configuration**:
1. Replace `your-domain.com` with actual domain
2. Update SSL certificate paths
3. Adjust rate limits if needed

---

## 📊 Monitoring Configuration

### prometheus.yml
**Purpose**: Metrics collection configuration

**Scrape Targets**:
- Node Exporter (system metrics)
- PostgreSQL Exporter
- Redis Exporter
- cAdvisor (Docker metrics)

**Usage**:
```bash
# Mount in docker-compose.monitoring.yml
volumes:
  - ./config/prometheus.yml:/etc/prometheus/prometheus.yml:ro
```

**Customization**:
- Add application metrics endpoints
- Adjust scrape intervals
- Configure remote storage

---

### alerts/newlookup_alerts.yml
**Purpose**: Prometheus alert rules

**Alert Categories**:
- System (CPU, RAM, Disk)
- PostgreSQL (connections, queries, deadlocks)
- Redis (memory, hit rate)
- Docker (container health)

**Thresholds**:
- **Critical**: CPU >95%, RAM >95%, Disk >90%
- **Warning**: CPU >80%, RAM >85%, Disk >80%

**Usage**: Automatically loaded by Prometheus

---

### grafana/datasources/datasources.yml
**Purpose**: Grafana data source provisioning

**Data Sources**:
- Prometheus (metrics)
- PostgreSQL (direct queries)

**Usage**: Automatically loaded by Grafana on startup

---

### grafana/dashboards/dashboards.yml
**Purpose**: Dashboard provisioning configuration

**Usage**: Place dashboard JSON files in configured path

**Recommended Dashboards**:
1. Node Exporter Full (ID: 1860)
2. PostgreSQL Database (ID: 9628)
3. Redis Dashboard (ID: 11835)
4. Docker Containers (ID: 893)

---

## ⏰ Automation Configuration

### crontab.txt
**Purpose**: Scheduled task configuration

**Scheduled Tasks**:
- PostgreSQL backup (daily 3 AM)
- Uploads backup (daily 4 AM)
- Health check (every 5 minutes)
- Log cleanup (daily 1 AM)
- Docker cleanup (weekly Monday 1 AM)
- Database vacuum (weekly Sunday 5 AM)

**Usage**:
```bash
crontab -e
# Paste contents from config/crontab.txt
```

**Customization**:
- Adjust backup times
- Change retention periods
- Add custom tasks

---

### newlookup.service
**Purpose**: Systemd service for auto-start

**Features**:
- Auto-start on boot
- Restart on failure
- Proper dependencies

**Usage**:
```bash
# Install service
cp config/newlookup.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable newlookup
systemctl start newlookup

# Check status
systemctl status newlookup
```

---

## 🔧 Configuration Management

### Updating Configurations

**Database configs**:
```bash
# Edit config
vim config/postgresql.conf

# Restart PostgreSQL
docker-compose -f docker-compose.production.yml restart postgres
```

**Redis configs**:
```bash
# Edit config
vim config/redis.conf

# Restart Redis
docker-compose -f docker-compose.production.yml restart redis
```

**Monitoring configs**:
```bash
# Edit Prometheus config
vim config/prometheus.yml

# Reload Prometheus
docker exec newlookup_prometheus kill -HUP 1
```

---

## 🔍 Validation

### Test Configurations

**PostgreSQL**:
```bash
# Check syntax
docker exec newlookup_postgres postgres --check

# View current settings
docker exec newlookup_postgres psql -U newlookup -c "SHOW ALL;"
```

**Redis**:
```bash
# Check config
docker exec newlookup_redis redis-cli CONFIG GET '*'
```

**Nginx**:
```bash
# Test configuration
nginx -t

# Reload if valid
systemctl reload nginx
```

**Prometheus**:
```bash
# Check config
docker exec newlookup_prometheus promtool check config /etc/prometheus/prometheus.yml
```

---

## 📈 Performance Tuning

### Database Tuning
```sql
-- Check current settings
SHOW shared_buffers;
SHOW max_connections;
SHOW work_mem;

-- Monitor performance
SELECT * FROM pg_stat_database;
SELECT * FROM pg_stat_activity;
```

### Redis Tuning
```bash
# Check memory usage
redis-cli INFO memory

# Check hit rate
redis-cli INFO stats | grep keyspace

# Monitor commands
redis-cli MONITOR
```

---

## 🔒 Security Considerations

### Sensitive Data
- Never commit `.env` files
- Use strong passwords (32+ characters)
- Rotate credentials regularly
- Restrict file permissions: `chmod 600 config/*.conf`

### Network Security
- Use firewall (UFW)
- Enable SSL/TLS
- Restrict database access to localhost
- Use VPN for admin access

---

## 📞 Troubleshooting

### Configuration Issues

**PostgreSQL won't start**:
```bash
# Check logs
docker logs newlookup_postgres

# Validate config
docker exec newlookup_postgres postgres --check
```

**Redis connection refused**:
```bash
# Check if running
docker ps | grep redis

# Test connection
docker exec newlookup_redis redis-cli ping
```

**Prometheus not scraping**:
```bash
# Check targets
curl http://localhost:9090/api/v1/targets

# Check config
docker exec newlookup_prometheus promtool check config /etc/prometheus/prometheus.yml
```

---

## 🔗 Related Documentation

- [Production Deployment Guide](../docs/PRODUCTION_DEPLOYMENT.md)
- [System Requirements](../SYSTEM_REQUIREMENTS_700_BOTS.md)
- [Troubleshooting Guide](../docs/TROUBLESHOOTING.md)
- [Scripts Documentation](../scripts/README.md)

---

**Configuration files are production-ready and optimized for 700 bots / 30K users.**
