#!/bin/bash
# Sprint 4: Validation Script
# Verifies all load and chaos testing components are in place

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() {
    echo -e "${BLUE}??????????????????????????????????????????${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}??????????????????????????????????????????${NC}"
}

print_success() {
    echo -e "${GREEN}? $1${NC}"
}

print_error() {
    echo -e "${RED}? $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}??  $1${NC}"
}

print_info() {
    echo -e "${BLUE}??  $1${NC}"
}

# Counters
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0

check() {
    local description=$1
    local command=$2
    
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    
    if eval "$command" > /dev/null 2>&1; then
        print_success "$description"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
        return 0
    else
        print_error "$description"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        return 1
    fi
}

print_header "Sprint 4: Load & Chaos Testing Validation"
echo ""

# Load Test Files
print_info "Checking load test files..."
check "k6 AutoBid test exists" "test -f tests/load/k6_autobid_test.js"
check "k6 stress test exists" "test -f tests/load/k6_api_stress_test.js"
check "Load test runner exists" "test -x scripts/run_load_test.sh"
echo ""

# Chaos Test Files
print_info "Checking chaos experiment files..."
check "Redis failover experiment exists" "test -f tests/chaos/redis_failover_experiment.yaml"
check "API timeout experiment exists" "test -f tests/chaos/instagram_api_timeout.yaml"
check "DB exhaustion experiment exists" "test -f tests/chaos/database_connection_exhaustion.yaml"
check "Chaos test runner exists" "test -x scripts/run_chaos_tests.sh"
echo ""

# Reporting Tools
print_info "Checking reporting tools..."
check "Report generator exists" "test -x scripts/generate_sprint4_report.py"
check "Python 3 available" "command -v python3"
echo ""

# Grafana Dashboard
print_info "Checking Grafana dashboard..."
check "Sprint 4 dashboard exists" "test -f infra/grafana/provisioning/dashboards/json/sprint4_performance.json"
echo ""

# Documentation
print_info "Checking documentation..."
check "SPRINT4_COMPLETE.md exists" "test -f SPRINT4_COMPLETE.md"
check "SPRINT4_QUICKSTART.md exists" "test -f SPRINT4_QUICKSTART.md"
echo ""

# Prerequisites
print_info "Checking prerequisites..."
check "Docker available" "command -v docker"
check "curl available" "command -v curl"
echo ""

# Services (optional checks)
print_info "Checking services (optional)..."
if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    print_success "Backend is running"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
else
    print_warning "Backend not running (start with: docker compose up -d backend)"
fi
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

if curl -sf http://localhost:9090/-/healthy > /dev/null 2>&1; then
    print_success "Prometheus is running"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
else
    print_warning "Prometheus not running (start with: docker compose -f docker-compose.observability.yml up -d)"
fi
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

if curl -sf http://localhost:3000/api/health > /dev/null 2>&1; then
    print_success "Grafana is running"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
else
    print_warning "Grafana not running (start with: docker compose -f docker-compose.observability.yml up -d)"
fi
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

echo ""
print_header "Validation Summary"
echo ""

echo "Total Checks: $TOTAL_CHECKS"
echo "Passed: $PASSED_CHECKS"
echo "Failed: $FAILED_CHECKS"
echo ""

if [ $FAILED_CHECKS -eq 0 ]; then
    print_success "All critical checks passed!"
    echo ""
    echo "?? Ready to run tests:"
    echo ""
    echo "  Load Testing:"
    echo "    ./scripts/run_load_test.sh autobid"
    echo "    ./scripts/run_load_test.sh all"
    echo ""
    echo "  Chaos Testing:"
    echo "    ./scripts/run_chaos_tests.sh redis"
    echo "    ./scripts/run_chaos_tests.sh all"
    echo ""
    echo "  Report Generation:"
    echo "    python3 scripts/generate_sprint4_report.py"
    echo ""
    echo "?? Documentation:"
    echo "    cat SPRINT4_COMPLETE.md"
    echo "    cat SPRINT4_QUICKSTART.md"
    echo ""
    exit 0
else
    print_error "$FAILED_CHECKS critical checks failed"
    echo ""
    echo "Please fix the issues above before running tests."
    echo ""
    exit 1
fi
