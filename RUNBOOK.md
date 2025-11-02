# Production Runbook - Antika Auction Watcher

**Version:** 1.0.0  
**Team:** DevOps & SRE

---

## ?? Quick Reference

### Emergency Contacts

- **On-Call Engineer:** oncall@antika-auction.com
- **DevOps Team:** devops@antika-auction.com
- **Database Team:** dba@antika-auction.com
- **ML Team:** ml-team@antika-auction.com

### Critical Endpoints

- **Application:** https://your-domain.com
- **Admin:** https://your-domain.com/admin
- **API Health:** https://your-domain.com/health
- **Grafana:** https://your-domain.com:3001
- **Prometheus:** http://localhost:9090 (SSH tunnel)
- **Alertmanager:** http://localhost:9093 (SSH tunnel)

---

## ?? Common Incidents

### 1. API is Down (Critical)

**Alert:** `APIDown`  
**Symptoms:** 
- Health check failing
- 502/503 errors from nginx
- No responses from backend

**Diagnosis:**

```bash
# Check container status
docker compose -f infra/docker-compose.prod.yml ps backend

# Check backend logs
docker compose -f infra/docker-compose.prod.yml logs --tail=100 backend

# Check resource usage
docker stats antika_backend
```

**Resolution:**

```bash
# Restart backend
docker compose -f infra/docker-compose.prod.yml restart backend

# If still failing, check database connection
docker compose -f infra/docker-compose.prod.yml logs postgres

# Force recreate
docker compose -f infra/docker-compose.prod.yml up -d --force-recreate backend

# Rollback if needed
git checkout <previous-commit>
docker compose -f infra/docker-compose.prod.yml up -d --force-recreate
```

**Escalation:** If not resolved in 15 minutes, page senior engineer.

---

### 2. High API Latency

**Alert:** `HighAPILatency` (p99 >400ms for 5m)  
**Symptoms:**
- Slow page loads
- Timeouts
- User complaints

**Diagnosis:**

```bash
# Check slow queries
docker compose -f infra/docker-compose.prod.yml exec postgres psql -U antika_user -d antika_db -c "
SELECT query, mean_exec_time, calls 
FROM pg_stat_statements 
ORDER BY mean_exec_time DESC 
LIMIT 10;
"

# Check Redis latency
docker compose -f infra/docker-compose.prod.yml exec redis redis-cli --latency

# Check connection pool
# Look for database_connections_active metric in Grafana
```

**Resolution:**

```bash
# Option 1: Clear Redis cache (force refresh)
docker compose -f infra/docker-compose.prod.yml exec redis redis-cli FLUSHDB

# Option 2: Restart services
docker compose -f infra/docker-compose.prod.yml restart backend

# Option 3: Scale up
docker compose -f infra/docker-compose.prod.yml up -d --scale backend=3

# Option 4: Optimize database
docker compose -f infra/docker-compose.prod.yml exec postgres psql -U antika_user -d antika_db -c "VACUUM ANALYZE;"
```

**Prevention:**
- Add database indexes for slow queries
- Increase Redis memory
- Optimize advisor calculations
- Enable query result caching

---

### 3. Low Redis Cache Hit Ratio

**Alert:** `LowRedisCacheHitRatio` (<80% for 10m)  
**Symptoms:**
- Increased database load
- Slower response times
- Higher latency

**Diagnosis:**

```bash
# Check Redis stats
docker compose -f infra/docker-compose.prod.yml exec redis redis-cli INFO stats

# Check memory usage
docker compose -f infra/docker-compose.prod.yml exec redis redis-cli INFO memory

# Check eviction policy
docker compose -f infra/docker-compose.prod.yml exec redis redis-cli CONFIG GET maxmemory-policy
```

**Resolution:**

```bash
# Increase Redis max memory
docker compose -f infra/docker-compose.prod.yml exec redis redis-cli CONFIG SET maxmemory 4gb

# Change eviction policy if needed
docker compose -f infra/docker-compose.prod.yml exec redis redis-cli CONFIG SET maxmemory-policy allkeys-lru

# Restart Redis
docker compose -f infra/docker-compose.prod.yml restart redis
```

**Prevention:**
- Increase Redis memory allocation
- Review cache key TTLs
- Implement cache warming for popular items

---

### 4. Database Connection Exhaustion

**Alert:** `HighDatabaseConnections`  
**Symptoms:**
- "Too many connections" errors
- New requests failing
- Degraded performance

**Diagnosis:**

```bash
# Check active connections
docker compose -f infra/docker-compose.prod.yml exec postgres psql -U antika_user -d antika_db -c "
SELECT count(*) FROM pg_stat_activity;
"

# Check connection sources
docker compose -f infra/docker-compose.prod.yml exec postgres psql -U antika_user -d antika_db -c "
SELECT application_name, count(*) 
FROM pg_stat_activity 
GROUP BY application_name;
"
```

**Resolution:**

```bash
# Kill idle connections
docker compose -f infra/docker-compose.prod.yml exec postgres psql -U antika_user -d antika_db -c "
SELECT pg_terminate_backend(pid) 
FROM pg_stat_activity 
WHERE state = 'idle' 
AND state_change < NOW() - INTERVAL '10 minutes';
"

# Restart backend to reset connection pool
docker compose -f infra/docker-compose.prod.yml restart backend

# Increase max_connections (edit postgresql.conf)
docker compose -f infra/docker-compose.prod.yml exec postgres psql -U antika_user -d antika_db -c "
ALTER SYSTEM SET max_connections = 200;
SELECT pg_reload_conf();
"
```

**Prevention:**
- Implement connection pooling (PgBouncer)
- Set connection pool limits in backend
- Monitor connection usage

---

### 5. Learning Loop Not Processing Feedback

**Alert:** `FeedbackBacklog` (>100 pending for 30m)  
**Symptoms:**
- Advisor weights not updating
- Feedback accumulating
- No learning cycles in logs

**Diagnosis:**

```bash
# Check learning loop logs
docker compose -f infra/docker-compose.prod.yml logs --tail=100 learning_loop

# Check if container is running
docker compose -f infra/docker-compose.prod.yml ps learning_loop

# Check Redis for pending feedback
docker compose -f infra/docker-compose.prod.yml exec redis redis-cli HLEN advisor:feedback:pending
```

**Resolution:**

```bash
# Restart learning loop
docker compose -f infra/docker-compose.prod.yml restart learning_loop

# Manually trigger learning cycle
docker compose -f infra/docker-compose.prod.yml exec learning_loop python -m backend.tasks.feedback_learning_loop --once

# Check for errors in logs
docker compose -f infra/docker-compose.prod.yml logs learning_loop | grep ERROR
```

**Prevention:**
- Add health check for learning loop
- Monitor pending feedback count
- Set up alerts for stuck cycles

---

### 6. WebSocket Connection Failures

**Alert:** `WebSocketConnectionFailures`  
**Symptoms:**
- Dashboard not updating in real-time
- "Disconnected" status in UI
- Connection errors in browser console

**Diagnosis:**

```bash
# Check nginx WebSocket proxy
docker compose -f infra/docker-compose.prod.yml logs nginx | grep -i websocket

# Check backend WebSocket handler
docker compose -f infra/docker-compose.prod.yml logs backend | grep -i websocket

# Test WebSocket directly
wscat -c wss://your-domain.com/api/v1/ws/auctions
```

**Resolution:**

```bash
# Restart nginx
docker compose -f infra/docker-compose.prod.yml restart nginx

# Restart backend
docker compose -f infra/docker-compose.prod.yml restart backend

# Check nginx config
docker compose -f infra/docker-compose.prod.yml exec nginx nginx -t
```

**Prevention:**
- Increase WebSocket timeouts
- Add WebSocket-specific monitoring
- Implement client reconnection logic (already done)

---

### 7. Disk Space Running Low

**Alert:** `DiskSpaceLow` (<10% free)  
**Symptoms:**
- Services failing to write
- Database errors
- Log rotation issues

**Diagnosis:**

```bash
# Check disk usage
df -h

# Find large directories
du -sh /var/lib/docker/*
du -sh /opt/antika/infra/logs/*
```

**Resolution:**

```bash
# Clean Docker system
docker system prune -af --volumes

# Clean old logs
find /opt/antika/infra/logs -type f -mtime +7 -delete

# Clean old backups
find /backups -type f -mtime +90 -delete

# Rotate logs immediately
docker compose -f infra/docker-compose.prod.yml kill -s USR1 nginx
```

**Prevention:**
- Configure log rotation (logrotate)
- Set retention policies
- Monitor disk usage proactively
- Add disk space alerts at 20% free

---

## ?? Maintenance Procedures

### Planned Maintenance

**Pre-Maintenance:**

```bash
# 1. Notify users (if applicable)
# 2. Create backup
cd /opt/antika/scripts
./backup_redis.sh
./export_csv.sh 7

# 3. Enable maintenance mode (optional)
docker compose -f infra/docker-compose.prod.yml exec nginx sh -c "
echo 'Maintenance mode' > /usr/share/nginx/html/maintenance.html
"
```

**During Maintenance:**

```bash
# Stop services
docker compose -f infra/docker-compose.prod.yml stop backend frontend

# Perform updates
git pull
docker compose -f infra/docker-compose.prod.yml build

# Run migrations
docker compose -f infra/docker-compose.prod.yml up -d postgres redis
docker compose -f infra/docker-compose.prod.yml run --rm backend alembic upgrade head

# Restart all
docker compose -f infra/docker-compose.prod.yml up -d
```

**Post-Maintenance:**

```bash
# Verify health
curl https://your-domain.com/health

# Check logs
docker compose -f infra/docker-compose.prod.yml logs --tail=50 backend

# Monitor for 15 minutes
watch -n 5 'docker compose -f infra/docker-compose.prod.yml ps'
```

### Database Maintenance

```bash
# Vacuum and analyze (run during low traffic)
docker compose -f infra/docker-compose.prod.yml exec postgres psql -U antika_user -d antika_db -c "
VACUUM ANALYZE;
"

# Reindex (if query performance degrading)
docker compose -f infra/docker-compose.prod.yml exec postgres psql -U antika_user -d antika_db -c "
REINDEX DATABASE antika_db;
"

# Check database size
docker compose -f infra/docker-compose.prod.yml exec postgres psql -U antika_user -d antika_db -c "
SELECT pg_size_pretty(pg_database_size('antika_db'));
"
```

---

## ?? Performance Optimization

### Database Optimization

```sql
-- Find slow queries
SELECT query, mean_exec_time, calls 
FROM pg_stat_statements 
ORDER BY mean_exec_time DESC 
LIMIT 20;

-- Find missing indexes
SELECT schemaname, tablename, attname, n_distinct, correlation
FROM pg_stats
WHERE schemaname = 'public'
ORDER BY n_distinct DESC;

-- Check index usage
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
ORDER BY idx_scan ASC;
```

### Redis Optimization

```bash
# Check slow commands
docker compose -f infra/docker-compose.prod.yml exec redis redis-cli SLOWLOG GET 10

# Optimize memory
docker compose -f infra/docker-compose.prod.yml exec redis redis-cli CONFIG SET maxmemory-policy allkeys-lru

# Check fragmentation
docker compose -f infra/docker-compose.prod.yml exec redis redis-cli INFO memory | grep fragmentation
```

---

## ?? Disaster Recovery

### Full System Recovery

**Scenario:** Complete server failure

```bash
# 1. Provision new server (same specs)

# 2. Install Docker and dependencies
curl -fsSL https://get.docker.com | sh

# 3. Clone repository
git clone <repo> /opt/antika
cd /opt/antika

# 4. Restore SSL certificates
# Copy from backup or regenerate with certbot

# 5. Restore environment variables
# Recreate .env with same values

# 6. Restore Redis data
./scripts/restore_redis.sh /backups/redis/latest.rdb.gz

# 7. Restore database (if needed)
# Import from backup dump

# 8. Start services
cd infra
docker compose -f docker-compose.prod.yml up -d

# 9. Verify health
curl https://your-domain.com/health
```

### RTO/RPO Targets

- **RTO (Recovery Time Objective):** 2 hours
- **RPO (Recovery Point Objective):** 1 hour (hourly backups)

---

## ?? Daily Operations

### Morning Checks

```bash
# 1. Check all services running
docker compose -f infra/docker-compose.prod.yml ps

# 2. Check overnight alerts
curl http://localhost:9093/api/v2/alerts

# 3. Review error logs
docker compose -f infra/docker-compose.prod.yml logs --since 24h --tail=100 backend | grep ERROR

# 4. Check disk space
df -h

# 5. Check backup status
ls -lh /backups/redis/ | tail -3
```

### Deployment Procedure

```bash
# 1. Create pre-deployment backup
./scripts/backup_redis.sh
./scripts/export_csv.sh 1

# 2. Run tests locally
cd backend && pytest
cd frontend && npm test

# 3. Tag release
git tag -a v1.x.x -m "Release v1.x.x"
git push origin v1.x.x

# 4. Deploy via GitHub Actions (automatic on main branch)
# Or manual deployment:
docker compose -f infra/docker-compose.prod.yml pull
docker compose -f infra/docker-compose.prod.yml up -d

# 5. Run migrations
docker compose -f infra/docker-compose.prod.yml exec backend alembic upgrade head

# 6. Smoke test
curl https://your-domain.com/health
curl https://your-domain.com/api/v1/advisor/health

# 7. Monitor for 30 minutes
watch -n 10 'docker compose -f infra/docker-compose.prod.yml ps; echo "---"; docker stats --no-stream'
```

---

## ?? Investigation Tools

### Log Analysis

```bash
# Search logs for error pattern
docker compose -f infra/docker-compose.prod.yml logs backend | grep -i "error\|exception\|failed"

# Follow logs in real-time
docker compose -f infra/docker-compose.prod.yml logs -f --tail=50 backend

# Export logs for analysis
docker compose -f infra/docker-compose.prod.yml logs --since 1h backend > backend_logs_$(date +%Y%m%d_%H%M%S).log
```

### Database Queries

```bash
# Connect to database
docker compose -f infra/docker-compose.prod.yml exec postgres psql -U antika_user -d antika_db

# Active queries
SELECT pid, age(clock_timestamp(), query_start), usename, query 
FROM pg_stat_activity 
WHERE query != '<IDLE>' AND query NOT ILIKE '%pg_stat_activity%' 
ORDER BY query_start DESC;

# Lock waits
SELECT * FROM pg_locks WHERE NOT granted;

# Table sizes
SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Redis Inspection

```bash
# Connect to Redis
docker compose -f infra/docker-compose.prod.yml exec redis redis-cli -a <password>

# Key statistics
INFO keyspace
DBSIZE

# Memory usage
INFO memory

# Find large keys
redis-cli --bigkeys

# Monitor commands in real-time
MONITOR
```

---

## ?? Capacity Planning

### When to Scale

**Vertical Scaling (Upgrade Server):**
- CPU usage >80% sustained
- Memory usage >85% sustained
- Disk I/O bottlenecks

**Horizontal Scaling (Add Servers):**
- Request rate >500 req/s
- WebSocket connections >1000
- Database read load high

### Scaling Procedures

**Backend Scaling:**

```bash
# Add more backend instances
docker compose -f infra/docker-compose.prod.yml up -d --scale backend=3

# Update nginx upstream
# Add servers to backend_api upstream block
```

**Database Scaling:**

- Setup read replicas
- Implement connection pooling (PgBouncer)
- Consider managed database (RDS, Cloud SQL)

---

## ?? Testing in Production

### Smoke Tests

```bash
# Health checks
curl https://your-domain.com/health
curl https://your-domain.com/api/v1/advisor/health

# API functionality
curl -X GET https://your-domain.com/api/v1/advisor/suggest/test123

# WebSocket
wscat -c wss://your-domain.com/api/v1/ws/auctions
```

### Load Testing

```bash
# Install hey (HTTP load generator)
go install github.com/rakyll/hey@latest

# Test API endpoint
hey -n 1000 -c 10 https://your-domain.com/api/v1/advisor/health

# Monitor during test
watch -n 1 'docker stats --no-stream'
```

---

## ?? Escalation Matrix

| Severity | Response Time | Escalation Path |
|----------|--------------|-----------------|
| Critical | 15 minutes | On-call ? Senior Engineer ? CTO |
| High | 1 hour | DevOps ? Team Lead |
| Medium | 4 hours | DevOps ? Create ticket |
| Low | Next business day | Create ticket |

---

## ? Health Check Script

```bash
#!/bin/bash
# health_check.sh

echo "=== Antika Health Check ==="

# API
if curl -sf https://your-domain.com/health > /dev/null; then
    echo "? API: Healthy"
else
    echo "? API: Down"
fi

# Frontend
if curl -sf https://your-domain.com > /dev/null; then
    echo "? Frontend: Healthy"
else
    echo "? Frontend: Down"
fi

# Database
if docker exec antika_postgres pg_isready -U antika_user > /dev/null 2>&1; then
    echo "? PostgreSQL: Healthy"
else
    echo "? PostgreSQL: Down"
fi

# Redis
if docker exec antika_redis redis-cli ping > /dev/null 2>&1; then
    echo "? Redis: Healthy"
else
    echo "? Redis: Down"
fi

# Prometheus
if curl -sf http://localhost:9090/-/healthy > /dev/null; then
    echo "? Prometheus: Healthy"
else
    echo "? Prometheus: Down"
fi

# Grafana
if curl -sf http://localhost:3001/api/health > /dev/null; then
    echo "? Grafana: Healthy"
else
    echo "? Grafana: Down"
fi

echo "=== End Health Check ==="
```

---

**Runbook Version:** 1.0.0  
**Last Updated:** November 2, 2025  
**Next Review:** December 2, 2025
