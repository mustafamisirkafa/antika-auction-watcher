# Observability Guide - Antika Auction Watcher

**Version:** 1.0.0  
**Stack:** Prometheus + Loki + Grafana

---

## ?? Overview

Comprehensive observability setup with metrics, logs, and alerts for the Antika platform.

---

## ?? Metrics (Prometheus)

### Key SLOs (Service Level Objectives)

| Metric | Target | Alert Threshold | Alert After |
|--------|--------|----------------|-------------|
| API p99 Latency | <400ms | >400ms | 5 minutes |
| Redis Hit Ratio | >80% | <80% | 10 minutes |
| API Uptime | >99.9% | Down | 1 minute |
| Error Rate | <1% | >5% | 5 minutes |

### Scrape Endpoints

**Backend API** (`backend:8000/metrics`):
```
http_requests_total
http_request_duration_seconds
advisor_recommendations_total
advisor_accuracy_rate
advisor_feedback_pending_count
websocket_connections_active
database_queries_total
cache_hits_total
cache_misses_total
```

**Redis** (`redis_exporter:9121/metrics`):
```
redis_up
redis_connected_clients
redis_keyspace_hits_total
redis_keyspace_misses_total
redis_memory_used_bytes
redis_commands_processed_total
```

**PostgreSQL** (`postgres_exporter:9187/metrics`):
```
pg_up
pg_stat_database_numbackends
pg_stat_database_xact_commit
pg_stat_database_xact_rollback
pg_database_size_bytes
pg_locks_count
```

### Custom Metrics

Add to `backend/middleware/metrics.py`:

```python
from prometheus_client import Counter, Histogram, Gauge

# Advisor metrics
advisor_recommendations = Counter(
    'advisor_recommendations_total',
    'Total recommendations generated',
    ['recommendation_level']
)

advisor_accuracy = Gauge(
    'advisor_accuracy_rate',
    'Current advisor accuracy rate'
)

feedback_pending = Gauge(
    'advisor_feedback_pending_count',
    'Pending feedback entries'
)

# API metrics
http_requests = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint']
)
```

---

## ?? Logs (Loki)

### Log Sources

1. **Application Logs** (via Promtail):
   - Backend API logs (`/var/log/backend/*.log`)
   - Learning loop logs (`/var/log/learning/*.log`)
   - Nginx access/error logs (`/var/log/nginx/*.log`)

2. **Container Logs** (via Docker):
   - All container stdout/stderr
   - Automatically labeled with service name

### Log Queries (Grafana Explore)

**All backend errors:**
```logql
{job="backend"} |= "ERROR"
```

**API requests by status:**
```logql
{job="nginx"} | json | status >= 500
```

**Learning loop activity:**
```logql
{job="learning_loop"} |= "Learning cycle"
```

**WebSocket connections:**
```logql
{job="backend"} |= "WebSocket" |= "connected"
```

**Rate-limited requests:**
```logql
{job="nginx"} | json | status="429"
```

### Log Levels

- **ERROR**: Service failures, exceptions
- **WARNING**: Degraded performance, retries
- **INFO**: Normal operations, requests
- **DEBUG**: Detailed debugging (disabled in prod)

---

## ?? Alerts

### Critical Alerts (Immediate Response)

**APIDown:**
- **Condition:** Backend API unreachable for >1 minute
- **Action:** Check container status, restart if needed
- **Escalation:** Page on-call engineer

**PostgreSQLDown / RedisDown:**
- **Condition:** Database/cache unreachable for >1 minute
- **Action:** Check container health, check disk space
- **Escalation:** Page DBA

**HighErrorRate:**
- **Condition:** >5% HTTP 5xx errors for >5 minutes
- **Action:** Check backend logs, rollback if recent deploy
- **Escalation:** Alert development team

### Warning Alerts (Monitor)

**HighAPILatency:**
- **Condition:** p99 latency >400ms for >5 minutes
- **Action:** Check database queries, Redis performance
- **Escalation:** Create ticket for optimization

**LowRedisCacheHitRatio:**
- **Condition:** Hit ratio <80% for >10 minutes
- **Action:** Review cache key patterns, increase TTL
- **Escalation:** Alert backend team

**FeedbackBacklog:**
- **Condition:** >100 pending feedback entries for >30 minutes
- **Action:** Check learning loop logs, restart if stuck
- **Escalation:** Alert ML team

**AdvisorAccuracyDrop:**
- **Condition:** Accuracy drops >5% in 1 hour
- **Action:** Review recent weight changes, check feedback quality
- **Escalation:** Alert ML team

### Alert Routing

```
Critical alerts ? ops@antika-auction.com + oncall@antika-auction.com
Warning alerts ? devops@antika-auction.com
API alerts ? api-team@antika-auction.com
Database alerts ? dba@antika-auction.com
ML/Advisor alerts ? ml-team@antika-auction.com
```

---

## ?? Grafana Dashboards

### 1. Antika Overview Dashboard

**Panels:**
- System uptime
- Requests per second
- Error rate (24h)
- Active WebSocket connections
- Database connections
- Redis hit ratio
- API p50/p90/p99 latency
- Queue pending jobs

### 2. API Performance Dashboard

**Panels:**
- Request rate by endpoint
- Latency heatmap
- Error rate by status code
- Request duration histogram
- Top slowest endpoints
- Rate-limited requests

### 3. Learning Loop Dashboard

**Panels:**
- Accuracy trend over time
- Feedback pending count
- Learning cycle duration
- Weight evolution (pattern, market, behavior, risk)
- Feedback distribution (helpful/not helpful)
- Recommendations by level

### 4. Database Metrics Dashboard

**Panels:**
- Query rate
- Connection pool usage
- Transaction rate
- Lock waits
- Table sizes
- Index usage
- Cache hit ratio

### 5. Redis Cache Dashboard

**Panels:**
- Memory usage
- Hit/miss ratio
- Commands per second
- Key count by pattern
- Evictions
- Connected clients

---

## ?? Querying & Analysis

### Prometheus Queries

**API p99 latency:**
```promql
histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))
```

**Redis hit ratio:**
```promql
redis_keyspace_hits_total / (redis_keyspace_hits_total + redis_keyspace_misses_total)
```

**Error rate:**
```promql
rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])
```

**Active WebSocket connections:**
```promql
websocket_connections_active
```

**Advisor accuracy:**
```promql
advisor_accuracy_rate
```

### Loki Queries

**Error log analysis:**
```logql
sum(count_over_time({job="backend"} |= "ERROR" [1h])) by (level)
```

**Request volume by endpoint:**
```logql
sum(rate({job="nginx"} | json | __error__="" [5m])) by (request)
```

**Learning loop executions:**
```logql
{job="learning_loop"} |= "Learning cycle" | pattern "<_> complete" 
```

---

## ?? SLI/SLO Monitoring

### Service Level Indicators (SLIs)

**Availability:**
```promql
# Uptime percentage (last 30 days)
avg_over_time(up{job="backend_api"}[30d]) * 100
```

**Latency:**
```promql
# Percentage of requests < 400ms
sum(rate(http_request_duration_seconds_bucket{le="0.4"}[5m])) 
/ 
sum(rate(http_request_duration_seconds_count[5m])) * 100
```

**Error Budget:**
```promql
# Remaining error budget (1% over 30 days)
100 - (sum(rate(http_requests_total{status=~"5.."}[30d])) 
/ 
sum(rate(http_requests_total[30d])) * 100)
```

---

## ?? Alert Testing

### Manual Alert Trigger

```bash
# Test HighAPILatency alert
curl -X POST http://localhost:9090/api/v1/alerts

# Check Alertmanager
curl http://localhost:9093/api/v2/alerts
```

### Silence Alerts

**Via Alertmanager UI:**
1. Go to http://localhost:9093
2. Click "Silences"
3. Create new silence with matchers

**Via API:**
```bash
curl -X POST http://localhost:9093/api/v2/silences \
  -H "Content-Type: application/json" \
  -d '{
    "matchers": [{"name": "alertname", "value": "HighAPILatency"}],
    "startsAt": "2025-11-02T10:00:00Z",
    "endsAt": "2025-11-02T12:00:00Z",
    "createdBy": "admin",
    "comment": "Planned maintenance"
  }'
```

---

## ?? Performance Benchmarks

### Baseline Metrics (Production)

- **API p50:** <100ms
- **API p90:** <200ms
- **API p99:** <400ms
- **Redis hit ratio:** >85%
- **Database connections:** <50
- **WebSocket connections:** 100-500 concurrent
- **Advisor processing:** <50ms per recommendation

### Capacity Planning

- **Requests per second:** 100-200 (normal), 500 (peak)
- **Database size growth:** ~1GB/month
- **Redis memory:** 2-4GB typical
- **Log volume:** ~5GB/month

---

## ??? Troubleshooting Observability

### Prometheus Not Scraping

```bash
# Check targets in Prometheus
curl http://localhost:9090/api/v1/targets

# Check service connectivity
docker exec antika_prometheus nc -zv backend 8000
```

### Loki Not Receiving Logs

```bash
# Check Promtail status
docker logs antika_promtail

# Check Loki ingestion
curl http://localhost:3100/ready

# Query Loki directly
curl -G -s "http://localhost:3100/loki/api/v1/query" \
  --data-urlencode 'query={job="backend"}' | jq
```

### Grafana Datasource Issues

```bash
# Check datasource health
docker exec antika_grafana curl -s http://prometheus:9090/-/healthy

# Test Prometheus query
docker exec antika_grafana curl -s http://prometheus:9090/api/v1/query?query=up
```

---

**Observability Stack Complete** ?  
For deployment, see `DEPLOYMENT_GUIDE.md`  
For incidents, see `RUNBOOK.md`
