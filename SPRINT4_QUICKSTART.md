# ?? Sprint 4: Load & Chaos Testing ? Quick Start Guide

This guide provides step-by-step instructions to run load tests and chaos experiments.

---

## ?? Prerequisites

### Required Tools
- **Docker** - For running k6 and backend services
- **Python 3.8+** - For report generation
- **Chaos Toolkit** (optional) - For chaos experiments
- **curl** - For API testing

### Required Services
- Backend API running (http://localhost:8000)
- Prometheus running (http://localhost:9090)
- Grafana running (http://localhost:3000)
- Redis running
- PostgreSQL running

### Installation

```bash
# Install Chaos Toolkit
pip install chaostoolkit chaostoolkit-kubernetes

# Or use Docker for k6 (no installation needed)
docker pull grafana/k6
```

---

## ? Quick Start

### Option 1: Run All Tests (Automated)

```bash
# Run load tests
./scripts/run_load_test.sh all

# Wait 5 minutes, then run chaos tests
./scripts/run_chaos_tests.sh all

# Generate report
python3 scripts/generate_sprint4_report.py
```

**Total time:** ~15-20 minutes

---

### Option 2: Run Individual Tests

#### Load Testing

```bash
# AutoBid endpoint test (100 VUs, 10 minutes)
./scripts/run_load_test.sh autobid

# API stress test (up to 200 VUs)
./scripts/run_load_test.sh stress

# Custom configuration
BASE_URL=http://localhost:8000 VUS=150 DURATION=15m ./scripts/run_load_test.sh autobid
```

#### Chaos Testing

```bash
# Redis failover test
./scripts/run_chaos_tests.sh redis

# API timeout test
./scripts/run_chaos_tests.sh api

# Database connection exhaustion
./scripts/run_chaos_tests.sh database

# Run all experiments
./scripts/run_chaos_tests.sh all
```

---

## ?? k6 Load Testing

### Test Scenarios

#### 1. AutoBid Load Test (`k6_autobid_test.js`)

**Purpose:** Validate AutoBid endpoint meets SLA under load

**Configuration:**
- Virtual Users: 100 (default)
- Duration: 10 minutes
- Ramp-up: 2 minutes
- Steady: 6 minutes
- Ramp-down: 2 minutes

**SLA Thresholds:**
- P95 latency < 3000ms
- Error rate < 1%

**Run:**
```bash
docker run --rm \
  -v $(pwd)/tests/load:/scripts \
  -e BASE_URL=http://host.docker.internal:8000 \
  -e VUS=100 \
  -e DURATION=10m \
  grafana/k6 run /scripts/k6_autobid_test.js
```

#### 2. API Stress Test (`k6_api_stress_test.js`)

**Purpose:** Identify system breaking point

**Configuration:**
- Peak Users: 200
- Tests: /health, /metrics, /plans, /analytics

**Run:**
```bash
docker run --rm \
  -v $(pwd)/tests/load:/scripts \
  -e BASE_URL=http://host.docker.internal:8000 \
  grafana/k6 run /scripts/k6_api_stress_test.js
```

### Understanding Results

```
? status is 200 or 201    ? Request succeeded
? response time < 3000ms   ? Within SLA
? status is 200 or 201    ? Request failed

Metrics:
  http_req_duration..........: avg=450ms  p95=2.1s ?
  http_req_failed............: 0.23% ?
  http_reqs..................: 50,000 (83.33/s)
```

---

## ?? Chaos Engineering

### Experiments

#### 1. Redis Failover (`redis_failover_experiment.yaml`)

**Purpose:** Validate Sentinel failover and graceful degradation

**Chaos Actions:**
1. Stop Redis master container
2. Wait 10 seconds
3. Verify backend responds (200 or 503)
4. Check circuit breaker opened
5. Restart Redis
6. Verify recovery

**Expected Behavior:**
- ? Backend switches to replica or returns 503
- ? No crashes or errors
- ? Circuit breaker opens
- ? Automatic recovery within 15s

**Run:**
```bash
BACKEND_URL=http://localhost:8000 \
REDIS_CONTAINER=redis \
chaos run tests/chaos/redis_failover_experiment.yaml
```

#### 2. External API Timeout (`instagram_api_timeout.yaml`)

**Purpose:** Validate circuit breaker and cache fallback

**Chaos Actions:**
1. Simulate API delay
2. Check circuit breaker metrics
3. Verify backend still responds
4. Confirm cache used
5. Validate P95 latency

**Expected Behavior:**
- ? Circuit breaker opens after failures
- ? System uses cached valuations
- ? P95 latency < 5s (degraded but acceptable)
- ? No cascading failures

**Run:**
```bash
chaos run tests/chaos/instagram_api_timeout.yaml
```

#### 3. Database Connection Exhaustion (`database_connection_exhaustion.yaml`)

**Purpose:** Validate PgBouncer pooling and connection management

**Chaos Actions:**
1. Create 50 concurrent database queries
2. Check connection metrics
3. Verify backend responsive
4. Confirm database running
5. Wait for recovery

**Expected Behavior:**
- ? PgBouncer manages connections
- ? Backend returns 429 (not crash)
- ? Database remains stable
- ? Recovery after load decreases

**Run:**
```bash
chaos run tests/chaos/database_connection_exhaustion.yaml
```

---

## ?? Monitoring During Tests

### Grafana Dashboard

1. Open Grafana: http://localhost:3000
2. Navigate to: **Dashboards ? Sprint 4: Performance Audit**
3. Observe real-time metrics during tests

**Key Panels:**
- HTTP Latency P95 (should stay < 3s)
- Request Rate (spikes during load test)
- Error Rate (should stay < 1%)
- Redis Availability
- Cache Hit Ratio
- AutoBid Latency Heatmap

### Prometheus Queries

```bash
# Check P95 latency
curl -G 'http://localhost:9090/api/v1/query' \
  --data-urlencode 'query=histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))'

# Check error rate
curl -G 'http://localhost:9090/api/v1/query' \
  --data-urlencode 'query=rate(http_requests_total{status_code=~"5.."}[5m])'

# Check Redis status
curl -G 'http://localhost:9090/api/v1/query' \
  --data-urlencode 'query=up{job="redis"}'
```

### Log Analysis (Loki)

```bash
# View logs during test
curl -G 'http://localhost:3100/loki/api/v1/query_range' \
  --data-urlencode 'query={job="backend"} |= "error"' \
  --data-urlencode 'limit=100'
```

---

## ?? Report Generation

### Automated Report

```bash
# Generate comprehensive report
python3 scripts/generate_sprint4_report.py

# Custom configuration
K6_RESULTS_DIR=tests/load/results \
CHAOS_RESULTS_DIR=tests/chaos/results \
PROMETHEUS_URL=http://localhost:9090 \
python3 scripts/generate_sprint4_report.py
```

**Output:** `SPRINT4_COMPLETE.md`

**Includes:**
- Executive summary
- Load test results (P95, P99, error rate)
- Chaos test results
- Prometheus metrics
- Recommendations
- Pass/fail determination

### Manual Result Analysis

```bash
# View k6 results
cat tests/load/results/*/k6_results.json | jq '.metrics.http_req_duration.p95'

# View chaos journals
cat tests/chaos/results/*/Redis_Failover_journal.json | jq '.status'
```

---

## ?? Troubleshooting

### Load Tests Failing

**Issue:** P95 latency > 3000ms

**Diagnosis:**
```bash
# Check backend logs
docker compose logs backend --tail=100

# Check system resources
docker stats

# Query Prometheus
curl 'http://localhost:9090/api/v1/query?query=http_request_duration_seconds_bucket'
```

**Solutions:**
- Reduce virtual users (VUS=50)
- Optimize slow database queries
- Increase backend replicas
- Check Redis performance

---

**Issue:** High error rate

**Diagnosis:**
```bash
# Check error logs
docker compose logs backend | grep ERROR

# Check Loki
curl 'http://localhost:3100/loki/api/v1/query_range?query={level="ERROR"}'
```

**Solutions:**
- Review error messages
- Check database connections
- Verify Redis availability
- Ensure all services running

---

### Chaos Tests Failing

**Issue:** Backend crashes during Redis failover

**Expected:** Backend should degrade gracefully (503)

**Actions:**
1. Check Sentinel configuration
2. Verify circuit breaker timeout
3. Review graceful degradation logic
4. Test manual Redis restart

---

**Issue:** Circuit breaker not opening

**Diagnosis:**
```bash
# Check circuit breaker metrics
curl http://localhost:8000/metrics | grep circuit_breaker

# Check failure count
curl http://localhost:9090/api/v1/query?query=circuit_breaker_failures_total
```

**Actions:**
1. Verify circuit breaker thresholds
2. Check failure count is incrementing
3. Review circuit breaker timeout settings
4. Test manual circuit breaker trigger

---

## ? Validation Checklist

### Load Tests
- [ ] k6 AutoBid test completed
- [ ] P95 latency < 3000ms
- [ ] Error rate < 1%
- [ ] API stress test completed
- [ ] No backend crashes
- [ ] Results saved to JSON

### Chaos Tests
- [ ] Redis failover experiment passed
- [ ] Backend recovered automatically
- [ ] API timeout experiment passed
- [ ] Circuit breaker opened correctly
- [ ] DB exhaustion experiment passed
- [ ] PgBouncer managed connections

### Monitoring
- [ ] Grafana dashboard shows data
- [ ] Prometheus metrics collected
- [ ] No gaps in time series
- [ ] Logs captured in Loki
- [ ] Alerts configured

### Reporting
- [ ] Report generated successfully
- [ ] All sections populated
- [ ] Pass/fail determination correct
- [ ] Recommendations relevant

---

## ?? Success Criteria

| Metric | Target | Status |
|--------|--------|--------|
| P95 Latency | < 3000ms | Check |
| P99 Latency | < 5000ms | Check |
| Error Rate | < 1% | Check |
| Redis Failover | Graceful | Check |
| API Timeout | No cascade | Check |
| DB Saturation | Managed | Check |
| Recovery Time | < 30s | Check |

---

## ?? Useful Commands

```bash
# Start observability stack
docker compose -f docker-compose.observability.yml up -d

# Start backend
docker compose up -d backend

# View all logs
docker compose logs -f

# Check container health
docker ps

# Stop all services
docker compose down

# Clean up test results
rm -rf tests/load/results/* tests/chaos/results/*

# Re-run failed experiment
chaos run tests/chaos/redis_failover_experiment.yaml --rollback-strategy=always
```

---

## ?? Additional Resources

- [k6 Documentation](https://k6.io/docs/)
- [Chaos Toolkit Documentation](https://chaostoolkit.org/reference/api/experiment/)
- [Prometheus Query Language](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Grafana Dashboards](https://grafana.com/docs/grafana/latest/dashboards/)

---

**? Sprint 4 load and chaos testing ready to execute!**

For detailed results and analysis, see [SPRINT4_COMPLETE.md](./SPRINT4_COMPLETE.md) after running tests.
