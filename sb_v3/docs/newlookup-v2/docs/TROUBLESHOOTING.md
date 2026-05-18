# Troubleshooting Guide

Common issues and solutions for NewLookup production deployment.

## 🔍 Quick Diagnostics

### Run These First
```bash
# 1. Check all container status
docker-compose -f docker-compose.production.yml ps

# 2. Run health check
./scripts/health_check.sh

# 3. Check recent errors
./scripts/view_logs.sh all --errors -n 50

# 4. Verify deployment
./scripts/verify_deployment.sh
```

---

## 🐳 Container Issues

### Container Won't Start

**Symptoms**: Container status shows "Exited" or "Restarting"

**Diagnosis**:
```bash
# Check container logs
docker logs newlookup_[service_name]

# Check last 100 lines
docker logs --tail=100 newlookup_[service_name]

# Follow logs in real-time
docker logs -f newlookup_[service_name]
```

**Common Causes & Solutions**:

1. **Missing environment variables**
   ```bash
   # Check .env file
   cat .env | grep [VARIABLE_NAME]
   
   # Restart after fixing
   docker-compose -f docker-compose.production.yml restart [service]
   ```

2. **Port already in use**
   ```bash
   # Find process using port
   lsof -i :8000
   
   # Kill process
   kill -9 [PID]
   
   # Or change port in .env
   WEB_PANEL_PORT=8001
   ```

3. **Database not ready**
   ```bash
   # Wait for database
   docker exec newlookup_postgres pg_isready -U newlookup
   
   # Restart dependent services
   docker-compose -f docker-compose.production.yml restart main_bot
   ```

---

### Container Unhealthy

**Symptoms**: Health check status shows "unhealthy"

**Diagnosis**:
```bash
# Check health status
docker inspect --format='{{.State.Health.Status}}' newlookup_[service]

# Check health log
docker inspect --format='{{json .State.Health}}' newlookup_[service] | jq
```

**Solutions**:
```bash
# Restart unhealthy container
docker restart newlookup_[service]

# If persists, check logs
docker logs newlookup_[service] --tail=200

# Rebuild and restart
docker-compose -f docker-compose.production.yml up -d --build [service]
```

---

### High Memory Usage

**Symptoms**: Container using excessive memory, system slow

**Diagnosis**:
```bash
# Check memory usage
docker stats --no-stream

# Check system memory
free -h

# Check specific container
docker stats newlookup_[service] --no-stream
```

**Solutions**:

1. **Restart high-memory containers**
   ```bash
   docker restart newlookup_[service]
   ```

2. **Adjust resource limits** (edit docker-compose.production.yml)
   ```yaml
   deploy:
     resources:
       limits:
         memory: 2G  # Increase if needed
   ```

3. **Check for memory leaks**
   ```bash
   # Monitor over time
   watch -n 5 'docker stats --no-stream'
   ```

---

## 🗄️ Database Issues

### Cannot Connect to Database

**Symptoms**: "Connection refused" or "Could not connect to server"

**Diagnosis**:
```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# Check PostgreSQL logs
docker logs newlookup_postgres --tail=100

# Test connection
docker exec newlookup_postgres pg_isready -U newlookup
```

**Solutions**:

1. **PostgreSQL not running**
   ```bash
   docker-compose -f docker-compose.production.yml up -d postgres
   ```

2. **Wrong credentials**
   ```bash
   # Check .env file
   grep POSTGRES_ .env
   
   # Test connection with credentials
   docker exec newlookup_postgres psql -U newlookup -d newlookup -c "SELECT 1;"
   ```

3. **Database doesn't exist**
   ```bash
   # List databases
   docker exec newlookup_postgres psql -U newlookup -l
   
   # Create database if missing
   docker exec newlookup_postgres psql -U newlookup -c "CREATE DATABASE newlookup;"
   ```

---

### Too Many Connections

**Symptoms**: "FATAL: sorry, too many clients already"

**Diagnosis**:
```bash
# Check current connections
docker exec newlookup_postgres psql -U newlookup -d newlookup -c \
  "SELECT count(*) FROM pg_stat_activity;"

# Check max connections
docker exec newlookup_postgres psql -U newlookup -c "SHOW max_connections;"

# List connections by state
docker exec newlookup_postgres psql -U newlookup -d newlookup -c \
  "SELECT state, count(*) FROM pg_stat_activity GROUP BY state;"
```

**Solutions**:

1. **Kill idle connections**
   ```bash
   docker exec newlookup_postgres psql -U newlookup -d newlookup -c \
     "SELECT pg_terminate_backend(pid) FROM pg_stat_activity 
      WHERE state = 'idle' 
      AND state_change < current_timestamp - INTERVAL '10 minutes';"
   ```

2. **Increase max_connections** (edit config/postgresql.conf)
   ```ini
   max_connections = 1500  # Increase from 1000
   ```
   
   Then restart:
   ```bash
   docker-compose -f docker-compose.production.yml restart postgres
   ```

3. **Implement connection pooling** (use PgBouncer)
   ```bash
   # See config/pgbouncer.ini for configuration
   ```

---

### Slow Queries

**Symptoms**: Application slow, high database CPU

**Diagnosis**:
```bash
# Check slow queries
docker exec newlookup_postgres psql -U newlookup -d newlookup -c \
  "SELECT pid, now() - pg_stat_activity.query_start AS duration, query 
   FROM pg_stat_activity 
   WHERE state = 'active' 
   ORDER BY duration DESC;"

# Check table sizes
docker exec newlookup_postgres psql -U newlookup -d newlookup -c \
  "SELECT schemaname, tablename, 
   pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size 
   FROM pg_tables 
   WHERE schemaname = 'public' 
   ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC 
   LIMIT 10;"
```

**Solutions**:

1. **Create missing indexes**
   ```bash
   ./scripts/optimize_database.sh
   ```

2. **Run VACUUM ANALYZE**
   ```bash
   docker exec newlookup_postgres vacuumdb -U newlookup -d newlookup --analyze --verbose
   ```

3. **Kill long-running queries**
   ```bash
   # Find query PID from diagnosis above
   docker exec newlookup_postgres psql -U newlookup -d newlookup -c \
     "SELECT pg_terminate_backend([PID]);"
   ```

---

## 🔴 Redis Issues

### Redis Not Responding

**Symptoms**: "Connection refused" or timeout errors

**Diagnosis**:
```bash
# Check if Redis is running
docker ps | grep redis

# Test connection
docker exec newlookup_redis redis-cli ping

# With password
docker exec newlookup_redis redis-cli -a "${REDIS_PASSWORD}" ping

# Check Redis logs
docker logs newlookup_redis --tail=100
```

**Solutions**:

1. **Redis not running**
   ```bash
   docker-compose -f docker-compose.production.yml up -d redis
   ```

2. **Wrong password**
   ```bash
   # Check .env file
   grep REDIS_PASSWORD .env
   
   # Test with correct password
   docker exec newlookup_redis redis-cli -a "your_password" ping
   ```

3. **Redis out of memory**
   ```bash
   # Check memory usage
   docker exec newlookup_redis redis-cli -a "${REDIS_PASSWORD}" INFO memory
   
   # Flush if needed (CAUTION: clears all data)
   docker exec newlookup_redis redis-cli -a "${REDIS_PASSWORD}" FLUSHALL
   ```

---

### High Redis Memory

**Symptoms**: Redis using too much memory

**Diagnosis**:
```bash
# Check memory usage
docker exec newlookup_redis redis-cli -a "${REDIS_PASSWORD}" INFO memory | grep used_memory_human

# Check key count
docker exec newlookup_redis redis-cli -a "${REDIS_PASSWORD}" DBSIZE

# Check largest keys
docker exec newlookup_redis redis-cli -a "${REDIS_PASSWORD}" --bigkeys
```

**Solutions**:

1. **Clear expired keys**
   ```bash
   # Redis should do this automatically, but you can force it
   docker exec newlookup_redis redis-cli -a "${REDIS_PASSWORD}" BGSAVE
   ```

2. **Adjust maxmemory** (edit config/redis.conf)
   ```ini
   maxmemory 4gb  # Increase from 2gb
   ```

3. **Change eviction policy** (if needed)
   ```ini
   maxmemory-policy allkeys-lru
   ```

---

## 🌐 Web Panel Issues

### Cannot Access Web Panel

**Symptoms**: Connection refused, timeout, or 502 error

**Diagnosis**:
```bash
# Check if web_panel is running
docker ps | grep web_panel

# Check web panel logs
docker logs newlookup_web_panel --tail=100

# Test locally
curl http://localhost:8000/health

# Check port binding
netstat -tlnp | grep 8000
```

**Solutions**:

1. **Web panel not running**
   ```bash
   docker-compose -f docker-compose.production.yml up -d web_panel
   ```

2. **Port not accessible**
   ```bash
   # Check firewall
   sudo ufw status
   
   # Allow port if needed
   sudo ufw allow 8000/tcp
   ```

3. **Nginx misconfiguration** (if using reverse proxy)
   ```bash
   # Test Nginx config
   nginx -t
   
   # Reload Nginx
   systemctl reload nginx
   ```

---

### Login Issues

**Symptoms**: Cannot login, "Invalid credentials" error

**Diagnosis**:
```bash
# Check admin user in database
docker exec newlookup_postgres psql -U newlookup -d newlookup -c \
  "SELECT id, username, role FROM admin_users;"

# Check .env credentials
grep ADMIN_ .env

# Check web panel logs for auth errors
docker logs newlookup_web_panel | grep -i "auth\|login"
```

**Solutions**:

1. **Reset admin password**
   ```bash
   # Connect to database
   docker exec -it newlookup_postgres psql -U newlookup -d newlookup
   
   # Update password (use bcrypt hash)
   UPDATE admin_users SET password_hash = '[new_hash]' WHERE username = 'admin';
   ```

2. **Check role permissions**
   ```bash
   # Verify role is 'super_admin' not 'superadmin'
   docker exec newlookup_postgres psql -U newlookup -d newlookup -c \
     "UPDATE admin_users SET role = 'super_admin' WHERE username = 'admin';"
   ```

---

## 🤖 Bot Issues

### Bot Not Responding

**Symptoms**: Bot doesn't reply to messages

**Diagnosis**:
```bash
# Check if bot container is running
docker ps | grep _bot

# Check bot logs
docker logs newlookup_main_bot --tail=100

# Test bot token
curl https://api.telegram.org/bot[YOUR_BOT_TOKEN]/getMe
```

**Solutions**:

1. **Bot container not running**
   ```bash
   docker-compose -f docker-compose.production.yml up -d main_bot
   ```

2. **Invalid bot token**
   ```bash
   # Check .env file
   grep BOT_TOKEN .env
   
   # Verify token with Telegram
   curl https://api.telegram.org/bot[TOKEN]/getMe
   
   # Update .env and restart
   docker-compose -f docker-compose.production.yml restart main_bot
   ```

3. **Database connection issues**
   ```bash
   # Check if bot can connect to database
   docker logs newlookup_main_bot | grep -i "database\|connection"
   ```

---

### Webhook Issues

**Symptoms**: Bot receives no updates

**Diagnosis**:
```bash
# Check webhook status
curl https://api.telegram.org/bot[TOKEN]/getWebhookInfo

# Check if using polling instead
docker logs newlookup_main_bot | grep -i "polling\|webhook"
```

**Solutions**:

1. **Delete webhook** (if using polling)
   ```bash
   curl https://api.telegram.org/bot[TOKEN]/deleteWebhook
   ```

2. **Restart bot**
   ```bash
   docker-compose -f docker-compose.production.yml restart main_bot
   ```

---

## 💾 Disk Space Issues

### Disk Full

**Symptoms**: "No space left on device" errors

**Diagnosis**:
```bash
# Check disk usage
df -h

# Find largest directories
du -sh /* | sort -h | tail -10

# Check Docker disk usage
docker system df
```

**Solutions**:

1. **Clean Docker**
   ```bash
   # Remove unused containers, images, volumes
   docker system prune -af --volumes
   
   # Remove old images
   docker image prune -af
   ```

2. **Clean old logs**
   ```bash
   # Application logs
   find /var/log/newlookup -name "*.log" -mtime +7 -delete
   
   # Docker logs
   truncate -s 0 /var/lib/docker/containers/*/*-json.log
   ```

3. **Clean old backups**
   ```bash
   # Keep only last 7 days
   find /opt/backups -name "*.dump.gz" -mtime +7 -delete
   find /opt/backups -name "snapshot_*" -mtime +7 -exec rm -rf {} \;
   ```

4. **Increase disk space** (if possible)
   - Resize volume on cloud provider
   - Add additional volume
   - Move data to external storage

---

## 🔥 Performance Issues

### High CPU Usage

**Diagnosis**:
```bash
# Check overall CPU
top

# Check per-container CPU
docker stats --no-stream

# Check processes
ps aux --sort=-%cpu | head -10
```

**Solutions**:

1. **Identify problematic container**
   ```bash
   docker stats --no-stream | sort -k3 -h
   ```

2. **Check for infinite loops in code**
   ```bash
   docker logs [container] | grep -i "error\|exception"
   ```

3. **Restart high-CPU container**
   ```bash
   docker restart [container]
   ```

4. **Scale horizontally** (if needed)
   - Add more servers
   - Use load balancer

---

### Slow Response Times

**Diagnosis**:
```bash
# Check response time
time curl http://localhost:8000/health

# Check database query times
docker exec newlookup_postgres psql -U newlookup -d newlookup -c \
  "SELECT query, mean_exec_time, calls 
   FROM pg_stat_statements 
   ORDER BY mean_exec_time DESC 
   LIMIT 10;"
```

**Solutions**:

1. **Optimize database**
   ```bash
   ./scripts/optimize_database.sh
   ```

2. **Check Redis cache hit rate**
   ```bash
   docker exec newlookup_redis redis-cli -a "${REDIS_PASSWORD}" INFO stats | grep keyspace
   ```

3. **Review slow queries and add indexes**

---

## 🚨 Emergency Procedures

### Complete System Failure

```bash
# 1. Stop everything
docker-compose -f docker-compose.production.yml down

# 2. Check system resources
df -h
free -h
top

# 3. Clean if needed
docker system prune -af

# 4. Restore from backup
./scripts/restore_postgres.sh /opt/backups/postgres/latest.dump.gz

# 5. Start services
docker-compose -f docker-compose.production.yml up -d

# 6. Verify
./scripts/verify_deployment.sh
```

---

### Data Corruption

```bash
# 1. Stop all services immediately
docker-compose -f docker-compose.production.yml down

# 2. Restore from latest backup
./scripts/restore_postgres.sh /opt/backups/postgres/[latest_backup].dump.gz

# 3. Verify data integrity
docker exec newlookup_postgres psql -U newlookup -d newlookup -c \
  "SELECT count(*) FROM users;"

# 4. Restart services
docker-compose -f docker-compose.production.yml up -d
```

---

## 📞 Getting Help

If issues persist:

1. **Collect diagnostics**:
   ```bash
   ./scripts/health_check.sh > health_report.txt
   ./scripts/view_logs.sh all --errors > error_logs.txt
   docker-compose -f docker-compose.production.yml ps > container_status.txt
   ```

2. **Check documentation**:
   - [Production Deployment Guide](PRODUCTION_DEPLOYMENT.md)
   - [Infrastructure Files](INFRASTRUCTURE_FILES.md)
   - [Scripts README](../scripts/README.md)

3. **Review logs systematically**:
   - Application logs
   - Database logs
   - System logs
   - Docker logs

4. **Contact support** with:
   - Error messages
   - Steps to reproduce
   - System information
   - Recent changes made
