# Production Deployment Checklist

Complete checklist for deploying NewLookup to production.

## 📋 Pre-Deployment

### Server Preparation
- [ ] Server provisioned (minimum: 16 vCPU / 32 GB RAM / 500 GB SSD)
- [ ] Ubuntu 22.04 LTS installed
- [ ] Root SSH access configured
- [ ] Domain name configured (optional)
- [ ] DNS records updated (if using domain)

### Software Installation
- [ ] Docker installed (`curl -fsSL https://get.docker.com | sh`)
- [ ] Docker Compose installed
- [ ] Git installed
- [ ] UFW firewall installed
- [ ] Fail2ban installed (optional but recommended)

### Security Setup
- [ ] UFW firewall configured and enabled
- [ ] SSH key-based authentication configured
- [ ] Root login disabled
- [ ] Password authentication disabled
- [ ] Fail2ban configured (optional)
- [ ] Non-root user created for application

### Bot Configuration
- [ ] All bot tokens obtained from @BotFather
  - [ ] Main bot token
  - [ ] Support bot token
  - [ ] Worker bot token
  - [ ] Seller bot token
  - [ ] Marketer bot token
- [ ] Bot usernames recorded
- [ ] Admin Telegram IDs collected
- [ ] Orders channel created and ID obtained

---

## 🔧 Deployment

### Code Setup
- [ ] Repository cloned to `/opt/newlookup`
- [ ] Correct branch checked out
- [ ] `.env` file created from `.env.production.example`
- [ ] All environment variables configured:
  - [ ] Database credentials
  - [ ] Redis password
  - [ ] Bot tokens
  - [ ] Admin credentials
  - [ ] Security keys (generated with `openssl rand -hex 32`)
  - [ ] Channel IDs
  - [ ] Web panel configuration

### Directory Structure
- [ ] `/opt/newlookup/data` created
- [ ] `/opt/newlookup/uploads` created
- [ ] `/opt/newlookup/media` created
- [ ] `/opt/newlookup/logs` created
- [ ] `/opt/backups/postgres` created
- [ ] `/opt/backups/uploads` created
- [ ] `/var/log/newlookup` created
- [ ] Correct permissions set (chown newlookup:newlookup)

### Database Setup
- [ ] PostgreSQL container started
- [ ] Database initialized
- [ ] Migrations applied (`alembic upgrade head`)
- [ ] Admin user created
- [ ] Test data loaded (if needed)

### Service Deployment
- [ ] Docker images built
- [ ] All containers started
- [ ] Container health checks passing
- [ ] No errors in logs

---

## ✅ Verification

### Container Status
- [ ] `newlookup_postgres` running and healthy
- [ ] `newlookup_redis` running and healthy
- [ ] `newlookup_main_bot` running
- [ ] `newlookup_support_bot` running
- [ ] `newlookup_worker_bot` running
- [ ] `newlookup_seller_bot` running
- [ ] `newlookup_marketer_bot` running
- [ ] `newlookup_web_panel` running
- [ ] `newlookup_celery_worker` running
- [ ] `newlookup_celery_beat` running

### Database Verification
- [ ] PostgreSQL responding to connections
- [ ] Database tables created (20+ tables)
- [ ] Indexes created
- [ ] Admin user can login
- [ ] Connection count normal (<100)

### Bot Verification
- [ ] Main bot responds to `/start`
- [ ] Support bot accessible
- [ ] Worker bot accessible
- [ ] Seller bot accessible
- [ ] Marketer bot accessible
- [ ] Bots can access database
- [ ] Bots can send messages

### Web Panel Verification
- [ ] Web panel accessible on port 8000
- [ ] Admin can login
- [ ] Dashboard loads correctly
- [ ] All pages accessible
- [ ] API endpoints responding
- [ ] No JavaScript errors in console

### Integration Tests
- [ ] User registration works
- [ ] Order creation works
- [ ] Payment processing works
- [ ] Seller registration works
- [ ] Worker registration works
- [ ] Notifications sent correctly
- [ ] File uploads work

---

## 📊 Monitoring Setup

### Monitoring Stack
- [ ] Monitoring stack started (`docker-compose.monitoring.yml`)
- [ ] Prometheus accessible on port 9090
- [ ] Grafana accessible on port 3000
- [ ] Node Exporter running
- [ ] PostgreSQL Exporter running
- [ ] Redis Exporter running
- [ ] cAdvisor running

### Grafana Configuration
- [ ] Grafana admin password changed
- [ ] Prometheus data source configured
- [ ] PostgreSQL data source configured (optional)
- [ ] Dashboards imported:
  - [ ] Node Exporter Full (ID: 1860)
  - [ ] PostgreSQL Database (ID: 9628)
  - [ ] Redis Dashboard (ID: 11835)
  - [ ] Docker Containers (ID: 893)
- [ ] Alert notifications configured (optional)

---

## 🔄 Backup Configuration

### Backup Scripts
- [ ] All backup scripts executable (`chmod +x scripts/*.sh`)
- [ ] PostgreSQL backup script tested
- [ ] Uploads backup script tested
- [ ] Restore script tested (on test data)
- [ ] Backup directories have correct permissions

### Cron Jobs
- [ ] Crontab configured (`crontab -e`)
- [ ] Daily PostgreSQL backup scheduled (3 AM)
- [ ] Daily uploads backup scheduled (4 AM)
- [ ] Health check scheduled (every 5 minutes)
- [ ] Log rotation scheduled (daily at 1 AM)
- [ ] Docker cleanup scheduled (weekly)
- [ ] Database vacuum scheduled (weekly)

### Backup Verification
- [ ] First backup completed successfully
- [ ] Backup files created in correct location
- [ ] Backup file sizes reasonable
- [ ] Restore tested successfully
- [ ] Backup retention working (old backups deleted)

---

## 🔒 Security Hardening

### Firewall
- [ ] UFW enabled
- [ ] Port 22 (SSH) allowed
- [ ] Port 80 (HTTP) allowed (if using domain)
- [ ] Port 443 (HTTPS) allowed (if using domain)
- [ ] Port 8000 restricted to trusted IPs (optional)
- [ ] All other ports blocked

### SSL/TLS (Optional but Recommended)
- [ ] Nginx installed
- [ ] Nginx configured as reverse proxy
- [ ] Certbot installed
- [ ] SSL certificate obtained
- [ ] Auto-renewal configured
- [ ] HTTPS redirect configured
- [ ] Security headers configured

### Application Security
- [ ] Strong passwords used for all services
- [ ] Secret keys generated securely
- [ ] `.env` file permissions restricted (600)
- [ ] No sensitive data in logs
- [ ] Rate limiting configured (Nginx)
- [ ] CORS configured correctly

---

## 🎯 Performance Optimization

### Database
- [ ] PostgreSQL configuration optimized
- [ ] Performance indexes created
- [ ] Connection pooling configured (PgBouncer - optional)
- [ ] Autovacuum configured
- [ ] Query logging enabled for slow queries

### Redis
- [ ] Redis configuration optimized
- [ ] Max memory set (2GB)
- [ ] Eviction policy configured (LRU)
- [ ] Persistence disabled (cache-only)

### Application
- [ ] Resource limits set for containers
- [ ] Logging configured (size limits)
- [ ] Connection pooling configured
- [ ] Celery workers configured (4 workers)

### System
- [ ] File descriptor limits increased
- [ ] Network parameters optimized
- [ ] Swap configured (if needed)

---

## 📝 Documentation

### Internal Documentation
- [ ] Deployment notes recorded
- [ ] Access credentials documented (securely)
- [ ] Architecture diagram created (optional)
- [ ] Runbook created for common tasks
- [ ] Incident response plan created (optional)

### Team Training
- [ ] Team trained on deployment process
- [ ] Team trained on monitoring tools
- [ ] Team trained on backup/restore procedures
- [ ] Team trained on troubleshooting
- [ ] On-call rotation established (optional)

---

## 🚀 Go-Live

### Final Checks
- [ ] All checklist items above completed
- [ ] Deployment verification script passed
- [ ] Health check script passing
- [ ] No critical errors in logs
- [ ] Monitoring dashboards showing green
- [ ] Backup system working
- [ ] Team ready for go-live

### Go-Live Steps
- [ ] Announce maintenance window (if applicable)
- [ ] Final backup created
- [ ] All services restarted
- [ ] Smoke tests passed
- [ ] User acceptance testing completed
- [ ] Go-live announced

### Post-Go-Live
- [ ] Monitor logs for 1 hour
- [ ] Monitor metrics for 24 hours
- [ ] Check backup completion next day
- [ ] Verify all scheduled tasks running
- [ ] Collect user feedback
- [ ] Document any issues encountered

---

## 📞 Emergency Contacts

### Key Personnel
- [ ] System administrator contact info documented
- [ ] Database administrator contact info documented
- [ ] Development team lead contact info documented
- [ ] On-call engineer contact info documented

### External Services
- [ ] Hosting provider support contact
- [ ] Domain registrar support contact
- [ ] SSL certificate provider support contact

---

## 🔧 Maintenance Schedule

### Daily
- [ ] Check health check logs
- [ ] Review error logs
- [ ] Monitor disk space
- [ ] Verify backups completed

### Weekly
- [ ] Review monitoring dashboards
- [ ] Check for security updates
- [ ] Review performance metrics
- [ ] Clean up old logs and backups

### Monthly
- [ ] Review and optimize database
- [ ] Update dependencies
- [ ] Review and update documentation
- [ ] Conduct disaster recovery drill

---

## ✅ Sign-Off

### Deployment Team
- [ ] System Administrator: _________________ Date: _______
- [ ] Database Administrator: _________________ Date: _______
- [ ] Development Lead: _________________ Date: _______
- [ ] Project Manager: _________________ Date: _______

### Approval
- [ ] Technical Lead Approval: _________________ Date: _______
- [ ] Business Owner Approval: _________________ Date: _______

---

**Deployment Status**: ⬜ Not Started | ⬜ In Progress | ⬜ Complete

**Go-Live Date**: _______________

**Notes**:
_____________________________________________________________________________
_____________________________________________________________________________
_____________________________________________________________________________
