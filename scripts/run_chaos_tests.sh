#!/bin/bash
# Sprint 4: Chaos Testing Runner
# Executes Chaos Toolkit experiments to validate system resilience

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

# Configuration
BACKEND_URL=${BACKEND_URL:-"http://localhost:8000"}
TEST_TYPE=${1:-"all"}  # redis, api, database, or all

print_header "Sprint 4: Chaos Testing"

echo ""
echo "?? Configuration:"
echo "   Backend URL: $BACKEND_URL"
echo "   Test Type: $TEST_TYPE"
echo ""

# Check prerequisites
echo "?? Checking prerequisites..."

if ! command -v chaos &> /dev/null; then
    print_warning "Chaos Toolkit not installed"
    echo ""
    echo "   Install with:"
    echo "   pip install chaostoolkit chaostoolkit-kubernetes"
    echo ""
    echo "   Or use Docker:"
    echo "   docker run --rm -v $(pwd):/workspace chaostoolkit/chaostoolkit run /workspace/tests/chaos/redis_failover_experiment.yaml"
    echo ""
    exit 1
fi
print_success "Chaos Toolkit is installed"

# Check if backend is healthy
echo "?? Checking backend health..."
if ! curl -sf "$BACKEND_URL/health" > /dev/null 2>&1; then
    print_error "Backend is not reachable at $BACKEND_URL"
    echo "   Please ensure the backend is running"
    exit 1
fi
print_success "Backend is healthy"

# Create results directory
mkdir -p tests/chaos/results
RESULTS_DIR="tests/chaos/results/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$RESULTS_DIR"

echo ""
print_header "Running Chaos Experiments"
echo ""

# Function to run a single experiment
run_experiment() {
    local exp_name=$1
    local exp_file=$2
    
    echo "?? Running $exp_name..."
    echo ""
    
    if BACKEND_URL="$BACKEND_URL" chaos run "tests/chaos/$exp_file" \
        --journal-path="$RESULTS_DIR/${exp_name}_journal.json"; then
        
        print_success "$exp_name completed"
        return 0
    else
        print_error "$exp_name failed"
        return 1
    fi
}

# Run experiments based on type
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

case $TEST_TYPE in
    redis)
        TOTAL_TESTS=1
        run_experiment "Redis Failover" "redis_failover_experiment.yaml"
        [ $? -eq 0 ] && PASSED_TESTS=$((PASSED_TESTS + 1)) || FAILED_TESTS=$((FAILED_TESTS + 1))
        ;;
    
    api)
        TOTAL_TESTS=1
        run_experiment "API Timeout" "instagram_api_timeout.yaml"
        [ $? -eq 0 ] && PASSED_TESTS=$((PASSED_TESTS + 1)) || FAILED_TESTS=$((FAILED_TESTS + 1))
        ;;
    
    database)
        TOTAL_TESTS=1
        run_experiment "DB Connection Exhaustion" "database_connection_exhaustion.yaml"
        [ $? -eq 0 ] && PASSED_TESTS=$((PASSED_TESTS + 1)) || FAILED_TESTS=$((FAILED_TESTS + 1))
        ;;
    
    all)
        echo "?? Running all chaos experiments..."
        echo ""
        
        TOTAL_TESTS=3
        
        # Redis failover
        run_experiment "Redis Failover" "redis_failover_experiment.yaml"
        [ $? -eq 0 ] && PASSED_TESTS=$((PASSED_TESTS + 1)) || FAILED_TESTS=$((FAILED_TESTS + 1))
        
        echo ""
        echo "? Waiting 30 seconds before next experiment..."
        sleep 30
        
        # API timeout
        run_experiment "API Timeout" "instagram_api_timeout.yaml"
        [ $? -eq 0 ] && PASSED_TESTS=$((PASSED_TESTS + 1)) || FAILED_TESTS=$((FAILED_TESTS + 1))
        
        echo ""
        echo "? Waiting 30 seconds before next experiment..."
        sleep 30
        
        # Database connection exhaustion
        run_experiment "DB Connection Exhaustion" "database_connection_exhaustion.yaml"
        [ $? -eq 0 ] && PASSED_TESTS=$((PASSED_TESTS + 1)) || FAILED_TESTS=$((FAILED_TESTS + 1))
        ;;
    
    *)
        print_error "Unknown test type: $TEST_TYPE"
        echo "   Valid options: redis, api, database, all"
        exit 1
        ;;
esac

echo ""
print_header "Chaos Test Results"
echo ""

# Display results
echo "?? Test Summary:"
echo "   Total: $TOTAL_TESTS"
echo "   Passed: $PASSED_TESTS"
echo "   Failed: $FAILED_TESTS"
echo ""

echo "?? Results saved to: $RESULTS_DIR"

# Check system status
echo ""
echo "?? System Status After Chaos:"
echo ""

# Check backend
if curl -sf "$BACKEND_URL/health" > /dev/null 2>&1; then
    print_success "Backend is healthy"
else
    print_warning "Backend may need recovery"
fi

# Check Redis
if docker ps --filter name=redis --format "{{.Status}}" | grep -q "Up"; then
    print_success "Redis is running"
else
    print_warning "Redis may be stopped (check if intentional)"
fi

# Check database
if docker ps --filter name=postgres --format "{{.Status}}" | grep -q "Up"; then
    print_success "Database is running"
else
    print_error "Database is not running"
fi

echo ""
echo "?? View metrics:"
echo "   Prometheus: http://localhost:9090"
echo "   Grafana: http://localhost:3000/d/sprint4-performance"
echo ""

echo ""
print_header "Summary"
echo ""

if [ $FAILED_TESTS -eq 0 ]; then
    print_success "All chaos experiments passed!"
    echo ""
    echo "?? System demonstrated resilience under:"
    echo "   ? Redis failover"
    echo "   ? External API timeouts"
    echo "   ? Database connection exhaustion"
    echo ""
    echo "?? Generate final report:"
    echo "   python3 scripts/generate_sprint4_report.py"
    echo ""
    exit 0
else
    print_error "$FAILED_TESTS chaos experiments failed"
    echo ""
    echo "?? Review experiment journals in: $RESULTS_DIR"
    echo "?? Check system logs for errors"
    echo ""
    exit 1
fi
