#!/bin/bash
# Sprint 4: Load Testing Runner
# Executes k6 load tests and generates reports

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
BASE_URL=${BASE_URL:-"http://host.docker.internal:8000"}
TEST_TYPE=${1:-"autobid"}  # autobid, stress, or all
VUS=${VUS:-100}
DURATION=${DURATION:-"10m"}

print_header "Sprint 4: k6 Load Testing"

echo ""
echo "?? Configuration:"
echo "   Target URL: $BASE_URL"
echo "   Test Type: $TEST_TYPE"
echo "   Virtual Users: $VUS"
echo "   Duration: $DURATION"
echo ""

# Check prerequisites
echo "?? Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed"
    exit 1
fi
print_success "Docker is installed"

# Check if backend is healthy
echo "?? Checking backend health..."
if ! curl -sf "$BASE_URL/health" > /dev/null 2>&1; then
    print_error "Backend is not reachable at $BASE_URL"
    echo "   Please ensure the backend is running:"
    echo "   docker compose up -d backend"
    exit 1
fi
print_success "Backend is healthy"

# Create results directory
mkdir -p tests/load/results
RESULTS_DIR="tests/load/results/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$RESULTS_DIR"

echo ""
print_header "Running Load Tests"
echo ""

# Function to run a single test
run_test() {
    local test_name=$1
    local test_file=$2
    
    echo "?? Running $test_name..."
    echo ""
    
    if docker run --rm \
        -v "$(pwd)/tests/load:/scripts" \
        -e BASE_URL="$BASE_URL" \
        -e VUS="$VUS" \
        -e DURATION="$DURATION" \
        grafana/k6 run "/scripts/$test_file"; then
        
        print_success "$test_name completed"
        
        # Copy results
        if [ -f "tests/load/k6_results.json" ]; then
            cp "tests/load/k6_results.json" "$RESULTS_DIR/${test_name}_results.json"
        fi
        
        return 0
    else
        print_error "$test_name failed"
        return 1
    fi
}

# Run tests based on type
case $TEST_TYPE in
    autobid)
        run_test "AutoBid Load Test" "k6_autobid_test.js"
        TEST_RESULT=$?
        ;;
    
    stress)
        run_test "API Stress Test" "k6_api_stress_test.js"
        TEST_RESULT=$?
        ;;
    
    all)
        echo "?? Running all load tests..."
        echo ""
        
        run_test "AutoBid Load Test" "k6_autobid_test.js"
        AUTOBID_RESULT=$?
        
        echo ""
        echo "? Waiting 30 seconds before next test..."
        sleep 30
        
        run_test "API Stress Test" "k6_api_stress_test.js"
        STRESS_RESULT=$?
        
        if [ $AUTOBID_RESULT -eq 0 ] && [ $STRESS_RESULT -eq 0 ]; then
            TEST_RESULT=0
        else
            TEST_RESULT=1
        fi
        ;;
    
    *)
        print_error "Unknown test type: $TEST_TYPE"
        echo "   Valid options: autobid, stress, all"
        exit 1
        ;;
esac

echo ""
print_header "Test Results"
echo ""

# Display results location
echo "?? Results saved to: $RESULTS_DIR"

# Check Prometheus for actual latency
echo ""
echo "?? Checking Prometheus metrics..."
if curl -sf "http://localhost:9090/api/v1/query?query=histogram_quantile(0.95,rate(http_request_duration_seconds_bucket[5m]))" > /dev/null 2>&1; then
    print_success "Prometheus metrics available"
    echo "   View at: http://localhost:9090/graph"
else
    print_warning "Prometheus metrics not available"
fi

# Check Grafana dashboard
echo ""
echo "?? View results in Grafana:"
echo "   URL: http://localhost:3000/d/sprint4-performance"
echo "   Dashboard: Sprint 4 Performance Audit"

echo ""
print_header "Summary"
echo ""

if [ $TEST_RESULT -eq 0 ]; then
    print_success "All load tests passed!"
    echo ""
    echo "?? Next steps:"
    echo "   1. Review detailed results in $RESULTS_DIR"
    echo "   2. Check Grafana dashboard for visualizations"
    echo "   3. Run chaos tests: ./scripts/run_chaos_tests.sh"
    echo ""
    exit 0
else
    print_error "Some load tests failed"
    echo ""
    echo "?? Troubleshooting:"
    echo "   1. Check backend logs: docker compose logs backend"
    echo "   2. Verify system resources: docker stats"
    echo "   3. Check for errors in Loki: http://localhost:3000/explore"
    echo ""
    exit 1
fi
