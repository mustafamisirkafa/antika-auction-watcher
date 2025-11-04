# ?? Sprint 3: Observability Stack ? Quick Start Guide

This guide provides step-by-step instructions to deploy and validate the complete observability stack.

---

## ?? Prerequisites

- Docker & Docker Compose installed
- Python 3.8+ installed
- Ports available: 3000, 9090, 9093, 3100, 16686, 8000
- Minimum 4GB RAM available

---

## ? Quick Setup (Automated)

### Option 1: One-Command Setup

```bash
# From project root
./scripts/setup_observability.sh
```

This script will:
- ? Check prerequisites
- ? Generate encryption keys
- ? Create .env file
- ? Start all observability services
- ? Start backend application
- ? Run smoke tests
- ? Display access URLs

**Total time:** ~2-3 minutes

---

### Option 2: Manual Setup

#### Step 1: Environment Configuration

```bash
# Copy example .env (if not exists)
cp .env.example .env

# Generate encryption keys
python3 -c "from cryptography.fernet import Fernet; print(f'MASTER_KEY={Fernet.generate_key().decode()}')" >> .env
python3 -c "import os,binascii; print(f'JWT_SECRET_KEY={binascii.hexlify(os.urandom(32)).decode()}')" >> .env
```

#### Step 2: Start Services

```bash
# Start observability stack
docker compose -f docker-compose.observability.yml up -d

# Wait 30 seconds for services to start
sleep 30

# Start backend (optional: start Redis Sentinel first)
docker compose -f docker-compose.sentinel.yml up -d
docker compose up -d backend
```

#### Step 3: Verify Services

```bash
# Check container status
docker ps

# Expected containers:
# - prometheus
# - alertmanager
# - grafana
# - loki
# - promtail
# - jaeger
# - redis-exporter
# - postgres-exporter
# - backend (if started)
```

---

## ? Validation

### Automated Validation

```bash
./scripts/validate_observability.sh
```

This script tests:
- Backend health endpoints
- Observability service availability
- Metrics exposure
- Log format
- Trace collection
- Prometheus targets
- Grafana datasources
- Alert rules

**Expected output:** All checks pass ?

---

### Manual Validation

#### 1. Test Backend Metrics

```bash
# Check metrics endpoint
curl http://localhost:8000/metrics

# Expected: Prometheus format output with metrics like:
# - autobid_latency_seconds
# - http_request_duration_seconds
# - redis_cache_hit_ratio
# - db_connections_active
```

#### 2. Test Health Endpoints

```bash
# Health check
curl http://localhost:8000/health
# Expected: {"status": "healthy"}

# Readiness check
curl http://localhost:8000/ready
# Expected: {"status": "ready", "checks": {...}}
```

#### 3. Access Observability UIs

Open in browser:
- **Grafana:** http://localhost:3000 (admin/admin)
- **Jaeger:** http://localhost:16686
- **Prometheus:** http://localhost:9090
- **Alertmanager:** http://localhost:9093

#### 4. Verify Metrics Collection

```bash
# Query Prometheus for backend metrics
curl -G 'http://localhost:9090/api/v1/query' \
  --data-urlencode 'query=up{job="backend"}'

# Expected: {"status":"success", "data": {"result": [...]}}
```

#### 5. Check Grafana Dashboards

1. Login to Grafana (http://localhost:3000)
2. Navigate to **Dashboards**
3. Verify datasources are configured:
   - Prometheus
   - Loki
   - Jaeger

#### 6. Verify Traces in Jaeger

1. Open Jaeger UI (http://localhost:16686)
2. Select service: `antika-auction-watcher`
3. Click "Find Traces"
4. You should see traces after generating some traffic

---

## ?? Generate Test Traffic

To populate metrics and traces, generate some API traffic:

```bash
# Generate test requests
for i in {1..10}; do
  curl http://localhost:8000/health
  curl http://localhost:8000/api/v1/plans
  sleep 1
done

# Check updated metrics
curl http://localhost:8000/metrics | grep http_requests_total
```

---

## ?? Configure Telegram Alerts (Optional)

### Step 1: Create Telegram Bot

1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Send `/newbot` and follow instructions
3. Copy the bot token (format: `123456:ABC-DEF1234...`)

### Step 2: Get Chat ID

1. Send a message to your bot
2. Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
3. Copy the `chat.id` value

### Step 3: Update Configuration

```bash
# Edit .env file
nano .env

# Add:
TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIJKlmNOPQRs...
TELEGRAM_CHAT_ID=-1001234567890

# Restart Alertmanager
docker compose -f docker-compose.observability.yml restart alertmanager
```

### Step 4: Test Alerts

```bash
# Trigger a test alert
curl -X POST http://localhost:9093/api/v1/alerts \
  -H 'Content-Type: application/json' \
  -d '[{
    "labels": {
      "alertname": "TestAlert",
      "severity": "warning",
      "component": "test"
    },
    "annotations": {
      "summary": "Test alert from Sprint 3 setup"
    }
  }]'

# Check Telegram for notification
```

---

## ?? Troubleshooting

### Services Not Starting

```bash
# Check logs
docker compose -f docker-compose.observability.yml logs

# Common issues:
# - Port already in use: Change ports in docker-compose.observability.yml
# - Insufficient memory: Increase Docker memory limit to 4GB+
# - Permission denied: Run with sudo or add user to docker group
```

### Metrics Not Appearing

```bash
# Verify backend is exposing metrics
curl http://localhost:8000/metrics

# Check Prometheus targets
curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job: .labels.job, health: .health}'

# Verify Prometheus can reach backend
docker exec prometheus wget -qO- http://backend:8000/metrics
```

### Logs Not in Loki

```bash
# Check Promtail logs
docker compose -f docker-compose.observability.yml logs promtail

# Verify Loki is receiving logs
curl http://localhost:3100/loki/api/v1/label

# Check log format (should be JSON)
docker compose logs backend --tail=10
```

### Traces Not in Jaeger

```bash
# Check Jaeger logs
docker compose -f docker-compose.observability.yml logs jaeger

# Verify tracing is enabled in backend
grep "JAEGER_ENABLED=true" .env

# Generate traffic to create traces
curl http://localhost:8000/api/v1/plans
```

### Telegram Alerts Not Sending

```bash
# Verify bot token
curl "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getMe"

# Check Alertmanager config
docker exec alertmanager cat /etc/alertmanager/alertmanager.yml | grep telegram -A5

# View Alertmanager logs
docker compose -f docker-compose.observability.yml logs alertmanager
```

---

## ?? Next Steps

After successful setup:

1. **Explore Grafana Dashboards**
   - AutoBid SLA metrics
   - System health
   - Performance overview

2. **Configure Custom Alerts**
   - Edit `infra/prometheus/alerts.yml`
   - Add team-specific thresholds
   - Restart Prometheus

3. **Set up Long-term Storage**
   - Configure Prometheus remote write
   - Set up Loki retention policies
   - Enable Jaeger persistent storage

4. **Integration Testing**
   - Run load tests (Sprint 4)
   - Verify SLA monitoring
   - Test alert routing

5. **Documentation**
   - Create runbooks for common alerts
   - Document escalation procedures
   - Set up on-call rotation

---

## ?? Useful Commands

```bash
# View all logs
docker compose -f docker-compose.observability.yml logs -f

# Restart specific service
docker compose -f docker-compose.observability.yml restart prometheus

# Stop all services
docker compose -f docker-compose.observability.yml down

# Remove all data (reset)
docker compose -f docker-compose.observability.yml down -v

# Update services
docker compose -f docker-compose.observability.yml pull
docker compose -f docker-compose.observability.yml up -d

# Export metrics
curl http://localhost:8000/metrics > metrics_$(date +%Y%m%d_%H%M%S).txt

# Query Prometheus
curl -G 'http://localhost:9090/api/v1/query' \
  --data-urlencode 'query=autobid_latency_seconds_bucket'

# Search Jaeger traces
curl 'http://localhost:16686/api/traces?service=antika-auction-watcher&limit=10'
```

---

## ?? Expected Results

After successful setup, you should see:

### Grafana
- ? 3 datasources configured
- ? Dashboards with live data
- ? No connection errors

### Prometheus
- ? All targets UP
- ? 12 alert rules loaded
- ? Metrics from backend

### Jaeger
- ? Service `antika-auction-watcher` visible
- ? Traces with multiple spans
- ? <2ms trace overhead

### Loki
- ? JSON logs ingested
- ? Trace IDs correlated
- ? Queryable via Grafana

### Alertmanager
- ? Rules evaluated
- ? Telegram receiver configured
- ? No firing alerts (in healthy state)

---

## ? Validation Checklist

- [ ] All Docker containers running
- [ ] Backend /metrics endpoint accessible
- [ ] Prometheus collecting metrics
- [ ] Grafana dashboards showing data
- [ ] Jaeger showing traces
- [ ] Loki ingesting logs
- [ ] Alert rules loaded
- [ ] Telegram bot configured (optional)
- [ ] No errors in container logs

---

**? Sprint 3 observability stack deployed and validated successfully!**

For detailed documentation, see [SPRINT3_COMPLETE.md](./SPRINT3_COMPLETE.md)
