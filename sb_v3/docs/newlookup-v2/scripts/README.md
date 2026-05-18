# Scripts Directory

Utility scripts for managing NewLookup production deployment.

## 📁 Available Scripts

### 🔄 Deployment & Updates

#### `quick_start.sh`
**Purpose**: Automated initial deployment  
**Usage**: `./scripts/quick_start.sh`  
**Description**: Performs complete initial deployment including environment validation, Docker setup, database initialization, and service startup.

**What it does**:
- Validates environment variables
- Creates required directories
- Checks Docker installation
- Builds and starts all services
- Runs database migrations
- Verifies deployment

**When to use**: First-time deployment or complete redeployment

---

#### `update_application.sh`
**Purpose**: Safe application updates with rollback capability  
**Usage**: `./scripts/update_application.sh`  
**Description**: Pulls latest code, rebuilds images, runs migrations, and performs rolling restart with minimal downtime.

**What it does**:
- Creates backup before update
- Pulls latest code from git
- Detects new migrations
- Rebuilds Docker images
- Performs rolling restart
- Verifies deployment health
- Automatic rollback on failure

**When to use**: Regular application updates

---

#### `rollback.sh`
**Purpose**: Rollback to previous version  
**Usage**: `./scripts/rollback.sh`  
**Description**: Reverts application to a previous git commit with database backup.

**What it does**:
- Shows recent commits
- Creates backup before rollback
- Resets code to specified commit
- Rebuilds and restarts services
- Verifies health

**When to use**: When update fails or causes issues

---

#### `verify_deployment.sh`
**Purpose**: Comprehensive deployment verification  
**Usage**: `./scripts/verify_deployment.sh`  
**Description**: Runs 10 categories of checks to verify deployment health.

**Checks**:
1. System requirements (CPU, RAM, disk)
2. Docker installation
3. Application files
4. Container status
5. Database health
6. Redis health
7. Web Panel accessibility
8. Backup configuration
9. Monitoring (optional)
10. Security (firewall, fail2ban)

**When to use**: After deployment, updates, or troubleshooting

---

### 💾 Backup & Recovery

#### `backup_postgres.sh`
**Purpose**: PostgreSQL database backup  
**Usage**: `./scripts/backup_postgres.sh`  
**Description**: Creates compressed database dump with 30-day retention.

**Features**:
- Compressed pg_dump format
- Automatic old backup cleanup
- Optional S3 upload
- Colored output with timestamps

**Scheduled**: Daily at 3 AM (via cron)

---

#### `backup_uploads.sh`
**Purpose**: Files and uploads backup  
**Usage**: `./scripts/backup_uploads.sh`  
**Description**: Incremental backup using rsync with hard-linked snapshots.

**Features**:
- Space-efficient hard links
- 14-day retention
- Incremental updates
- Snapshot history

**Scheduled**: Daily at 4 AM (via cron)

---

#### `restore_postgres.sh`
**Purpose**: Database restore from backup  
**Usage**: `./scripts/restore_postgres.sh <backup_file.dump.gz>`  
**Description**: Safely restores database from backup with confirmation.

**What it does**:
- Interactive confirmation
- Stops bots during restore
- Terminates active connections
- Drops and recreates database
- Restores from backup
- Restarts services

**When to use**: Disaster recovery or data restoration

---

### 🔍 Monitoring & Health

#### `health_check.sh`
**Purpose**: System health monitoring  
**Usage**: `./scripts/health_check.sh`  
**Description**: Comprehensive health check with alert notifications.

**Checks**:
- All container status
- PostgreSQL health and connections
- Redis health and memory
- Disk space usage
- Memory usage
- Web Panel accessibility

**Features**:
- Email alerts (if configured)
- Webhook alerts (if configured)
- Colored output
- Error/warning counters

**Scheduled**: Every 5 minutes (via cron)

---

#### `view_logs.sh`
**Purpose**: Convenient log viewer  
**Usage**: `./scripts/view_logs.sh [service] [options]`  
**Description**: Easy access to service logs with filtering.

**Examples**:
```bash
./scripts/view_logs.sh main -f          # Follow main bot logs
./scripts/view_logs.sh postgres -n 50   # Last 50 lines
./scripts/view_logs.sh all --errors     # All errors
```

**Options**:
- `-f, --follow`: Follow log output
- `-n, --lines N`: Show last N lines
- `-e, --errors`: Show only errors

---

### 🗄️ Database Management

#### `optimize_database.sh`
**Purpose**: Database optimization and indexing  
**Usage**: `./scripts/optimize_database.sh`  
**Description**: Creates performance indexes and runs maintenance.

**What it does**:
- Creates indexes on frequently queried columns
- Runs ANALYZE on all tables
- Performs VACUUM
- Shows table sizes

**When to use**: After initial deployment, monthly maintenance

---

#### `manage_migrations.sh`
**Purpose**: Database migration management  
**Usage**: `./scripts/manage_migrations.sh [command]`  
**Description**: Alembic migration wrapper with safety features.

**Commands**:
- `status`: Show current migration status
- `upgrade`: Apply all pending migrations
- `downgrade`: Rollback last migration
- `history`: Show migration history
- `create`: Create new migration

**Features**:
- Automatic backup before migrations
- Interactive confirmation for downgrades
- Clear status reporting

---

### 📊 Monitoring Setup

#### `setup_monitoring.sh`
**Purpose**: Monitoring stack setup  
**Usage**: `./scripts/setup_monitoring.sh`  
**Description**: Starts and configures Prometheus + Grafana.

**What it does**:
- Starts monitoring containers
- Verifies service health
- Shows access information
- Lists recommended dashboards

**When to use**: After initial deployment

---

## 🔧 Script Permissions

All scripts should be executable. If not, run:
```bash
chmod +x scripts/*.sh
```

## 📋 Cron Schedule

Add to crontab (`crontab -e`):
```cron
# PostgreSQL backup - Daily at 3 AM
0 3 * * * /opt/newlookup/scripts/backup_postgres.sh >> /var/log/newlookup/backup_postgres.log 2>&1

# Uploads backup - Daily at 4 AM
0 4 * * * /opt/newlookup/scripts/backup_uploads.sh >> /var/log/newlookup/backup_uploads.log 2>&1

# Health check - Every 5 minutes
*/5 * * * * /opt/newlookup/scripts/health_check.sh >> /var/log/newlookup/health_check.log 2>&1

# Log cleanup - Daily at 1 AM
0 1 * * * find /var/log/newlookup -name "*.log" -mtime +30 -delete

# Docker cleanup - Weekly on Monday at 1 AM
0 1 * * 1 docker system prune -af --volumes --filter "until=168h" >> /var/log/newlookup/docker_cleanup.log 2>&1

# Database vacuum - Weekly on Sunday at 5 AM
0 5 * * 0 docker exec newlookup_postgres vacuumdb -U newlookup -d newlookup --analyze --verbose >> /var/log/newlookup/vacuum.log 2>&1
```

## 🚨 Emergency Procedures

### Service Down
```bash
# Check status
docker-compose -f docker-compose.production.yml ps

# View logs
./scripts/view_logs.sh [service] --errors

# Restart service
docker-compose -f docker-compose.production.yml restart [service]

# Full restart
docker-compose -f docker-compose.production.yml restart
```

### Database Issues
```bash
# Check connections
docker exec newlookup_postgres psql -U newlookup -d newlookup -c "SELECT count(*) FROM pg_stat_activity;"

# Kill idle connections
docker exec newlookup_postgres psql -U newlookup -d newlookup -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle' AND state_change < current_timestamp - INTERVAL '10 minutes';"

# Restore from backup
./scripts/restore_postgres.sh /opt/backups/postgres/latest.dump.gz
```

### Disk Space Full
```bash
# Check usage
df -h

# Clean Docker
docker system prune -af --volumes

# Clean old logs
find /var/log/newlookup -name "*.log" -mtime +7 -delete

# Clean old backups
find /opt/backups -name "*.dump.gz" -mtime +30 -delete
```

### Failed Update
```bash
# Rollback to previous version
./scripts/rollback.sh

# Or manual rollback
git reset --hard HEAD~1
docker-compose -f docker-compose.production.yml up -d --build
```

## 📞 Support

For issues:
1. Check logs: `./scripts/view_logs.sh all --errors`
2. Run health check: `./scripts/health_check.sh`
3. Verify deployment: `./scripts/verify_deployment.sh`
4. Review documentation in `/opt/newlookup/docs/`

## 🔗 Related Documentation

- [Production Deployment Guide](../docs/PRODUCTION_DEPLOYMENT.md)
- [Deployment Checklist](../docs/DEPLOYMENT_CHECKLIST.md)
- [Infrastructure Files](../docs/INFRASTRUCTURE_FILES.md)
- [System Requirements](../SYSTEM_REQUIREMENTS_700_BOTS.md)
