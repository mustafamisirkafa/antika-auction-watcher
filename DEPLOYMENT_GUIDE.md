# Antika Auction Watcher - Production Deployment Guide

**Version:** 1.0.0  
**Last Updated:** November 2, 2025

---

## ?? Overview

Complete guide for deploying Antika Auction Watcher to production with Docker Compose, including monitoring, logging, and operational procedures.

---

## ?? Prerequisites

### Server Requirements

**Minimum Specifications:**
- **OS:** Ubuntu 22.04 LTS or similar
- **CPU:** 4 cores
- **RAM:** 8 GB
- **Disk:** 100 GB SSD
- **Network:** Static IP, domain name configured

**Recommended Specifications:**
- **CPU:** 8 cores
- **RAM:** 16 GB
- **Disk:** 200 GB SSD

### Software Requirements

```bash
# Docker & Docker Compose
docker --version  # >= 24.0
docker compose version  # >= 2.20

# Other tools
git --version
curl --version
openssl version
```

---

## ?? Initial Setup

### 1. Server Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Install Docker Compose (if not included)
sudo apt install docker-compose-plugin

# Create application directory
sudo mkdir -p /opt/antika
sudo chown $USER:$USER /opt/antika
cd /opt/antika
```

### 2. Clone Repository

```bash
git clone https://github.com/your-org/antika-auction-watcher.git
cd antika-auction-watcher
```

### 3. SSL Certificates

**Option A: Let's Encrypt (Recommended)**

```bash
# Install certbot
sudo apt install certbot

# Generate certificates
sudo certbot certonly --standalone -d your-domain.com

# Copy to project
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem infra/nginx/ssl/
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem infra/nginx/ssl/
sudo chown $USER:$USER infra/nginx/ssl/*

# Setup auto-renewal
sudo crontab -e
# Add: 0 0 * * * certbot renew --quiet && docker restart antika_nginx
```

**Option B: Self-Signed (Development)**

```bash
cd infra/nginx/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout privkey.pem -out fullchain.pem \
  -subj "/CN=your-domain.com"
```

### 4. Environment Configuration

```bash
cd infra
cp .env.example .env
```

Edit `.env`:

```bash
# Database
POSTGRES_PASSWORD=<generate-strong-password>

# Redis
REDIS_PASSWORD=<generate-strong-password>

# Application
SECRET_KEY=<generate-secret-key>
DOMAIN=your-domain.com

# Monitoring
GRAFANA_PASSWORD=<admin-password>

# Alerts (optional)
SMTP_USERNAME=alerts@your-domain.com
SMTP_PASSWORD=<smtp-password>
```

**Generate Secrets:**

```bash
# Generate random passwords
openssl rand -base64 32

# Generate Django-style secret key
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

### 5. Update Nginx Configuration

Edit `infra/nginx/nginx.conf` and replace `your-domain.com` with your actual domain.

---

## ??? Deployment

### Full Stack Deployment

```bash
cd /opt/antika/infra

# Pull images (if using pre-built)
docker compose -f docker-compose.prod.yml pull

# Start all services
docker compose -f docker-compose.prod.yml up -d

# Check status
docker compose -f docker-compose.prod.yml ps

# View logs
docker compose -f docker-compose.prod.yml logs -f
```

### Service-by-Service Verification

```bash
# Check individual services
docker compose -f docker-compose.prod.yml ps postgres     # Database
docker compose -f docker-compose.prod.yml ps redis        # Cache
docker compose -f docker-compose.prod.yml ps backend      # API
docker compose -f docker-compose.prod.yml ps frontend     # UI
docker compose -f docker-compose.prod.yml ps nginx        # Proxy
docker compose -f docker-compose.prod.yml ps prometheus   # Metrics
docker compose -f docker-compose.prod.yml ps grafana      # Dashboards

# Health checks
curl https://your-domain.com/health                       # API health
curl https://your-domain.com                              # Frontend
curl http://localhost:9090/-/healthy                      # Prometheus
curl http://localhost:3001/api/health                     # Grafana
```

### Database Migrations

```bash
# Run migrations
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head

# Create initial admin user (if needed)
docker compose -f docker-compose.prod.yml exec backend python -m backend.scripts.create_admin
```

---

## ?? Configuration

### Nginx Tuning

Edit `infra/nginx/nginx.conf`:

```nginx
# Adjust worker processes based on CPU cores
worker_processes auto;  # or specific number

# Adjust rate limits
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;  # Adjust rate
```

### Prometheus Retention

Edit `infra/docker-compose.prod.yml`:

```yaml
prometheus:
  command:
    - '--storage.tsdb.retention.time=30d'  # Adjust retention
```

### Loki Retention

Edit `infra/loki/loki.yml`:

```yaml
limits_config:
  retention_period: 30d  # Adjust log retention
```

---

## ?? Monitoring Access

### Grafana

**URL:** `https://your-domain.com:3001`  
**Username:** `admin`  
**Password:** (from `.env` GRAFANA_PASSWORD)

**Pre-provisioned Dashboards:**
- Antika Overview
- API Performance
- Database Metrics
- Redis Cache
- Learning Loop Status

### Prometheus

**URL:** `http://localhost:9090` (internal only)

### Alertmanager

**URL:** `http://localhost:9093` (internal only)

---

## ?? Updates & Rollbacks

### Update Application

```bash
cd /opt/antika

# Pull latest code
git pull origin main

# Rebuild and restart
cd infra
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d

# Run migrations if needed
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

### Rollback

```bash
# Rollback to previous version
git checkout <previous-commit>
docker compose -f docker-compose.prod.yml up -d --force-recreate
```

---

## ?? Backup & Restore

### Automated Backups

```bash
# Setup cron jobs
crontab -e

# Add these lines:
0 2 * * * /opt/antika/scripts/backup_redis.sh >> /var/log/backup_redis.log 2>&1
0 3 * * * /opt/antika/scripts/export_csv.sh 30 >> /var/log/export_csv.log 2>&1
```

### Manual Backup

```bash
cd /opt/antika/scripts

# Backup Redis
./backup_redis.sh

# Export CSV data (last 30 days)
./export_csv.sh 30

# Backup location
ls -lh /backups/redis/
ls -lh /backups/exports/
```

### Restore

```bash
# Restore Redis from backup
./restore_redis.sh /backups/redis/latest.rdb.gz

# Restore from specific backup
./restore_redis.sh /backups/redis/redis_backup_20251102_120000.rdb.gz
```

---

## ?? Security

### Firewall Configuration

```bash
# UFW setup
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 80/tcp      # HTTP
sudo ufw allow 443/tcp     # HTTPS
sudo ufw allow 3001/tcp    # Grafana (restrict to VPN if possible)
sudo ufw enable
```

### SSH Hardening

```bash
# Edit /etc/ssh/sshd_config
sudo vi /etc/ssh/sshd_config

# Disable root login
PermitRootLogin no

# Use key-based authentication only
PasswordAuthentication no

# Restart SSH
sudo systemctl restart sshd
```

### Regular Updates

```bash
# System updates
sudo apt update && sudo apt upgrade -y

# Docker images
docker compose -f infra/docker-compose.prod.yml pull
docker compose -f infra/docker-compose.prod.yml up -d
```

---

## ?? Troubleshooting

### Services Won't Start

```bash
# Check logs
docker compose -f infra/docker-compose.prod.yml logs <service-name>

# Check resource usage
docker stats

# Restart specific service
docker compose -f infra/docker-compose.prod.yml restart <service-name>
```

### Database Connection Issues

```bash
# Check PostgreSQL logs
docker compose -f infra/docker-compose.prod.yml logs postgres

# Connect to database
docker compose -f infra/docker-compose.prod.yml exec postgres psql -U antika_user -d antika_db

# Check connections
\l
\dt
```

### Redis Issues

```bash
# Check Redis logs
docker compose -f infra/docker-compose.prod.yml logs redis

# Connect to Redis
docker compose -f infra/docker-compose.prod.yml exec redis redis-cli -a <password>

# Check keys
KEYS *
DBSIZE
INFO
```

### High CPU/Memory

```bash
# Check resource usage
docker stats

# Restart resource-heavy services
docker compose -f infra/docker-compose.prod.yml restart backend learning_loop

# Scale down if needed
docker compose -f infra/docker-compose.prod.yml scale learning_loop=0
```

---

## ?? Scaling

### Horizontal Scaling

```bash
# Scale backend instances
docker compose -f infra/docker-compose.prod.yml up -d --scale backend=3

# Add load balancing to nginx
upstream backend_api {
    server backend:8000;
    server backend:8001;
    server backend:8002;
}
```

### Database Scaling

- Consider PostgreSQL read replicas
- Use connection pooling (PgBouncer)
- Optimize queries with indexes

### Redis Scaling

- Enable Redis Cluster mode
- Add read replicas
- Consider Redis Sentinel for HA

---

## ? Post-Deployment Checklist

- [ ] All services running (`docker compose ps`)
- [ ] Health checks passing
- [ ] SSL certificates valid
- [ ] Grafana dashboards loading
- [ ] Alerts configured and tested
- [ ] Backups running
- [ ] Firewall configured
- [ ] Domain DNS configured
- [ ] Logs being collected
- [ ] Monitoring data flowing
- [ ] WebSocket connections working
- [ ] API endpoints responding
- [ ] Frontend loading correctly

---

## ?? Support

- **Documentation:** `/docs` in repository
- **Runbook:** `RUNBOOK.md`
- **Security:** `SECURITY_CHECKLIST.md`
- **Observability:** `OBSERVABILITY.md`

---

**Deployment Guide Version:** 1.0.0  
**Infrastructure:** Docker Compose Production Stack  
**Last Updated:** November 2, 2025
