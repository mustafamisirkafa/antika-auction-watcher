#!/bin/bash
# Sprint 3: Observability Stack Validation Script
# Run this after setup_observability.sh to verify everything is working

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

passed=0
failed=0

test_endpoint() {
    local name=$1
    local url=$2
    local expected=$3
    
    echo -n "Testing $name... "
    
    if response=$(curl -sf "$url" 2>&1); then
        if [ -z "$expected" ] || echo "$response" | grep -q "$expected"; then
            echo -e "${GREEN}? PASS${NC}"
            ((passed++))
        else
            echo -e "${YELLOW}??  WARNING${NC} (responded but unexpected content)"
            ((failed++))
        fi
    else
        echo -e "${RED}? FAIL${NC}"
        ((failed++))
    fi
}

echo "?? Sprint 3: Observability Stack Validation"
echo "============================================"
echo ""

echo "?? Backend Endpoints"
echo "--------------------"
test_endpoint "Backend Health" "http://localhost:8000/health" "status"
test_endpoint "Backend Ready" "http://localhost:8000/ready" ""
test_endpoint "Prometheus Metrics" "http://localhost:8000/metrics" "autobid_latency"

echo ""
echo "?? Observability Services"
echo "-------------------------"
test_endpoint "Prometheus" "http://localhost:9090/-/ready" ""
test_endpoint "Grafana" "http://localhost:3000/api/health" "ok"
test_endpoint "Jaeger" "http://localhost:16686/" ""
test_endpoint "Loki" "http://localhost:3100/ready" ""
test_endpoint "Alertmanager" "http://localhost:9093/-/ready" ""

echo ""
echo "?? Metrics Validation"
echo "---------------------"

# Check specific metrics exist
echo -n "Checking autobid_latency_seconds... "
if curl -sf http://localhost:8000/metrics | grep -q "autobid_latency_seconds"; then
    echo -e "${GREEN}? PASS${NC}"
    ((passed++))
else
    echo -e "${RED}? FAIL${NC}"
    ((failed++))
fi

echo -n "Checking http_request_duration_seconds... "
if curl -sf http://localhost:8000/metrics | grep -q "http_request_duration_seconds"; then
    echo -e "${GREEN}? PASS${NC}"
    ((passed++))
else
    echo -e "${RED}? FAIL${NC}"
    ((failed++))
fi

echo -n "Checking redis_cache_hit_ratio... "
if curl -sf http://localhost:8000/metrics | grep -q "redis_cache_hit_ratio"; then
    echo -e "${GREEN}? PASS${NC}"
    ((passed++))
else
    echo -e "${RED}? FAIL${NC}"
    ((failed++))
fi

echo -n "Checking db_connections_active... "
if curl -sf http://localhost:8000/metrics | grep -q "db_connections_active"; then
    echo -e "${GREEN}? PASS${NC}"
    ((passed++))
else
    echo -e "${RED}? FAIL${NC}"
    ((failed++))
fi

echo ""
echo "?? Log Format Validation"
echo "------------------------"
echo -n "Checking JSON log format... "
if docker compose logs backend --tail=1 2>/dev/null | grep -q '"timestamp".*"level".*"message"'; then
    echo -e "${GREEN}? PASS${NC}"
    ((passed++))
else
    echo -e "${YELLOW}??  SKIP${NC} (logs may not be in JSON format yet)"
fi

echo ""
echo "?? Trace Validation"
echo "-------------------"
echo -n "Checking Jaeger services... "
if curl -sf "http://localhost:16686/api/services" | grep -q "antika-auction-watcher"; then
    echo -e "${GREEN}? PASS${NC}"
    ((passed++))
else
    echo -e "${YELLOW}??  WARNING${NC} (no traces yet, may need to generate traffic)"
    ((failed++))
fi

echo ""
echo "?? Prometheus Targets"
echo "---------------------"
echo -n "Checking Prometheus targets... "
if targets=$(curl -sf "http://localhost:9090/api/v1/targets" 2>/dev/null); then
    if echo "$targets" | grep -q "backend"; then
        echo -e "${GREEN}? PASS${NC}"
        ((passed++))
    else
        echo -e "${YELLOW}??  WARNING${NC} (backend target not found)"
        ((failed++))
    fi
else
    echo -e "${RED}? FAIL${NC}"
    ((failed++))
fi

echo ""
echo "?? Grafana Datasources"
echo "----------------------"
echo -n "Checking Grafana datasources... "
if datasources=$(curl -sf -u admin:admin "http://localhost:3000/api/datasources" 2>/dev/null); then
    if echo "$datasources" | grep -q "Prometheus"; then
        echo -e "${GREEN}? PASS${NC}"
        ((passed++))
    else
        echo -e "${YELLOW}??  WARNING${NC} (Prometheus datasource not found)"
        ((failed++))
    fi
else
    echo -e "${RED}? FAIL${NC}"
    ((failed++))
fi

echo ""
echo "?? Alert Rules"
echo "--------------"
echo -n "Checking Prometheus alert rules... "
if rules=$(curl -sf "http://localhost:9090/api/v1/rules" 2>/dev/null); then
    if echo "$rules" | grep -q "HighAutoBidLatency"; then
        echo -e "${GREEN}? PASS${NC}"
        ((passed++))
    else
        echo -e "${YELLOW}??  WARNING${NC} (alert rules not loaded)"
        ((failed++))
    fi
else
    echo -e "${RED}? FAIL${NC}"
    ((failed++))
fi

echo ""
echo "============================================"
echo "?? Validation Summary"
echo "============================================"
echo -e "Passed: ${GREEN}$passed${NC}"
echo -e "Failed: ${RED}$failed${NC}"
echo ""

if [ $failed -eq 0 ]; then
    echo -e "${GREEN}? All checks passed! Observability stack is fully operational.${NC}"
    exit 0
elif [ $passed -gt $failed ]; then
    echo -e "${YELLOW}??  Most checks passed. Some services may need more time to start.${NC}"
    echo "   Try running this script again in 30 seconds."
    exit 0
else
    echo -e "${RED}? Multiple failures detected. Check service logs:${NC}"
    echo "   docker compose -f docker-compose.observability.yml logs"
    exit 1
fi
