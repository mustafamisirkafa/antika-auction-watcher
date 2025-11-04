#!/bin/bash
# Sprint 3: Observability Stack Setup & Validation
# This script automates the complete deployment of the observability stack

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Progress indicator
step=1
total_steps=8

print_step() {
    echo -e "${BLUE}[Step $step/$total_steps]${NC} $1"
    ((step++))
}

print_success() {
    echo -e "${GREEN}? $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}??  $1${NC}"
}

print_error() {
    echo -e "${RED}? $1${NC}"
}

echo "?? Sprint 3: Observability Stack Setup"
echo "======================================="
echo ""

# Step 1: Check prerequisites
print_step "Checking prerequisites..."
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed"
    exit 1
fi
print_success "Docker is installed"

if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed"
    exit 1
fi
print_success "Python 3 is installed"

# Step 2: Generate keys if .env doesn't exist
print_step "Setting up environment variables..."
if [ ! -f .env ]; then
    print_warning ".env not found, creating..."
    
    # Generate MASTER_KEY
    MASTER_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
    
    # Generate JWT_SECRET_KEY
    JWT_SECRET=$(python3 -c "import os,binascii; print(binascii.hexlify(os.urandom(32)).decode())")
    
    # Create .env file
    cat > .env << EOF
# Sprint 3: Observability Configuration
MASTER_KEY=$MASTER_KEY
JWT_SECRET_KEY=$JWT_SECRET
REFRESH_TOKEN_TTL=86400
DATABASE_URL=postgresql://antika:antika_password@postgres:5432/antika_auction
REDIS_URL=redis://redis:6379/0
PROMETHEUS_ENABLED=true
PROMETHEUS_SCRAPE_PATH=/metrics
LOKI_URL=http://loki:3100
JAEGER_HOST=jaeger
JAEGER_PORT=6831
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
GRAFANA_USER=admin
GRAFANA_PASSWORD=admin
LOG_LEVEL=INFO
ENVIRONMENT=development
EOF
    print_success ".env created with generated keys"
else
    print_success ".env already exists"
fi

# Step 3: Stop existing containers
print_step "Stopping existing containers (if any)..."
docker compose -f docker-compose.observability.yml down 2>/dev/null || true
docker compose -f docker-compose.sentinel.yml down 2>/dev/null || true
print_success "Existing containers stopped"

# Step 4: Start observability stack
print_step "Starting observability services..."
echo "   - Prometheus (metrics collection)"
echo "   - Alertmanager (alert routing)"
echo "   - Grafana (dashboards)"
echo "   - Loki (log aggregation)"
echo "   - Promtail (log shipper)"
echo "   - Jaeger (distributed tracing)"
echo "   - Redis exporter"
echo "   - Postgres exporter"

docker compose -f docker-compose.observability.yml up -d

if [ $? -eq 0 ]; then
    print_success "Observability stack started"
else
    print_error "Failed to start observability stack"
    exit 1
fi

# Step 5: Wait for services to be healthy
print_step "Waiting for services to be healthy..."
echo "   This may take 30-60 seconds..."

sleep 10  # Initial wait

# Check service health
services=("prometheus" "grafana" "loki" "jaeger" "alertmanager")
for service in "${services[@]}"; do
    for i in {1..30}; do
        if docker ps | grep -q "$service.*Up"; then
            print_success "$service is healthy"
            break
        fi
        if [ $i -eq 30 ]; then
            print_warning "$service may not be fully healthy"
        fi
        sleep 2
    done
done

# Step 6: Start backend application
print_step "Starting backend application..."
# Check if we need to start Sentinel stack first
if docker compose -f docker-compose.sentinel.yml config &>/dev/null; then
    docker compose -f docker-compose.sentinel.yml up -d
    sleep 5
fi

# Start backend
if [ -f docker-compose.yml ]; then
    docker compose up -d backend
    print_success "Backend started"
fi

# Wait for backend to be ready
echo "   Waiting for backend to be ready..."
for i in {1..20}; do
    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        print_success "Backend is ready"
        break
    fi
    sleep 3
done

# Step 7: Run smoke tests
print_step "Running smoke tests..."

# Test /metrics endpoint
echo -n "   Testing /metrics... "
if curl -sf http://localhost:8000/metrics | grep -q "autobid_latency"; then
    print_success "Metrics endpoint OK"
else
    print_warning "Metrics endpoint may not be fully functional"
fi

# Test /health endpoint
echo -n "   Testing /health... "
if curl -sf http://localhost:8000/health | grep -q "status"; then
    print_success "Health endpoint OK"
else
    print_warning "Health endpoint may not be responding"
fi

# Test /ready endpoint
echo -n "   Testing /ready... "
if curl -sf http://localhost:8000/ready > /dev/null 2>&1; then
    print_success "Readiness endpoint OK"
else
    print_warning "Readiness endpoint may not be responding"
fi

# Test Prometheus
echo -n "   Testing Prometheus... "
if curl -sf http://localhost:9090/-/ready > /dev/null 2>&1; then
    print_success "Prometheus OK"
else
    print_warning "Prometheus may not be ready"
fi

# Test Grafana
echo -n "   Testing Grafana... "
if curl -sf http://localhost:3000/api/health > /dev/null 2>&1; then
    print_success "Grafana OK"
else
    print_warning "Grafana may not be ready"
fi

# Test Jaeger
echo -n "   Testing Jaeger... "
if curl -sf http://localhost:16686/ > /dev/null 2>&1; then
    print_success "Jaeger OK"
else
    print_warning "Jaeger may not be ready"
fi

# Step 8: Display access information
print_step "Setup complete! Access your observability stack:"
echo ""
echo "??????????????????????????????????????????????"
echo ""
echo "?? Grafana Dashboard:"
echo "   URL: ${GREEN}http://localhost:3000${NC}"
echo "   Username: admin"
echo "   Password: admin"
echo ""
echo "?? Jaeger Tracing:"
echo "   URL: ${GREEN}http://localhost:16686${NC}"
echo ""
echo "?? Prometheus Metrics:"
echo "   URL: ${GREEN}http://localhost:9090${NC}"
echo ""
echo "?? Loki Logs (via Grafana):"
echo "   URL: ${GREEN}http://localhost:3000/explore${NC}"
echo "   Select: Loki datasource"
echo ""
echo "?? Alertmanager:"
echo "   URL: ${GREEN}http://localhost:9093${NC}"
echo ""
echo "?? Backend API:"
echo "   Health: ${GREEN}http://localhost:8000/health${NC}"
echo "   Metrics: ${GREEN}http://localhost:8000/metrics${NC}"
echo "   Ready: ${GREEN}http://localhost:8000/ready${NC}"
echo ""
echo "??????????????????????????????????????????????"
echo ""

# Display container status
print_step "Container status:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "prometheus|grafana|loki|jaeger|alertmanager|backend" || true

echo ""
print_success "Sprint 3 observability stack deployed successfully!"
echo ""
echo "?? Next steps:"
echo "   1. Open Grafana and explore pre-configured dashboards"
echo "   2. Check /metrics endpoint for Prometheus metrics"
echo "   3. View traces in Jaeger UI"
echo "   4. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env for alerts"
echo ""
echo "?? Useful commands:"
echo "   - View logs: docker compose -f docker-compose.observability.yml logs -f"
echo "   - Restart: docker compose -f docker-compose.observability.yml restart"
echo "   - Stop: docker compose -f docker-compose.observability.yml down"
echo ""
