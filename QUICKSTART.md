# ?? Quick Start Guide - Antika Auction Watcher

Get up and running in under 5 minutes!

## Prerequisites Check

```bash
# Check Python version (need 3.11+)
python --version

# Check Docker
docker --version
docker-compose --version

# Check Make (optional but recommended)
make --version
```

## ?? Fast Track (3 Steps)

### Step 1: Environment Setup (30 seconds)

```bash
# Copy environment template
cp .env.example .env

# Generate encryption key
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Copy the output and paste it as ENCRYPTION_KEY in .env

# Set a secure JWT secret (or generate one)
# Edit .env and update JWT_SECRET
```

### Step 2: Install Dependencies (1-2 minutes)

```bash
# Install Python packages
pip install -r backend/requirements.txt

# Or use Make
make install
```

### Step 3: Start Services (1 minute)

```bash
# Start PostgreSQL and Redis with Docker
docker-compose up -d

# Wait for services to be healthy (check with)
docker-compose ps

# Start the backend
uvicorn backend.main:app --reload

# Or use Make
make dev
```

**?? Done! Your API is running at http://localhost:8000**

---

## ?? First API Calls

### 1. Check Health

```bash
curl http://localhost:8000/health
```

### 2. Register a User

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "demo@example.com",
    "username": "demo",
    "password": "demo123456"
  }'
```

### 3. Login and Get Token

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d "username=demo&password=demo123456"

# Save the access_token from the response
export TOKEN="your_access_token_here"
```

### 4. Create an Auction Item

```bash
curl -X POST http://localhost:8000/api/v1/items \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Vintage Rolex Watch",
    "description": "Rare 1970s Rolex Submariner",
    "category": "jewelry",
    "current_price": 1500,
    "seller_name": "AntikaSeller",
    "image_url": "https://example.com/watch.jpg"
  }'

# Note the item ID from response
export ITEM_ID=1
```

### 5. Get Valuation Estimate

```bash
curl -X POST http://localhost:8000/api/v1/valuations/estimate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"item_id\": $ITEM_ID}"
```

### 6. Get Bid Recommendation

```bash
curl -X POST http://localhost:8000/api/v1/bids/decision \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"item_id\": $ITEM_ID, \"mode\": \"semi_auto\"}"
```

### 7. Place a Bid

```bash
curl -X POST http://localhost:8000/api/v1/bids/place \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"item_id\": $ITEM_ID, \"mode\": \"semi_auto\"}"
```

---

## ?? Run Tests

```bash
# Quick test run
pytest backend/tests/ -v

# With coverage
pytest backend/tests/ --cov=backend --cov-report=html

# Or use Make
make test
```

---

## ?? Docker Commands

```bash
# Start all services
make docker-up

# Stop all services
make docker-down

# View logs
make docker-logs

# Rebuild containers
make docker-rebuild

# Connect to PostgreSQL
make db-shell

# Connect to Redis
make redis-cli
```

---

## ?? Interactive API Documentation

Once the server is running, visit:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

These provide interactive API documentation where you can test all endpoints!

---

## ?? Troubleshooting

### Port Already in Use

```bash
# Check what's using port 8000
lsof -i :8000

# Or use a different port
uvicorn backend.main:app --reload --port 8001
```

### Database Connection Error

```bash
# Make sure Docker services are running
docker-compose ps

# Restart services
docker-compose restart

# Check logs
docker-compose logs postgres
```

### Module Not Found Error

```bash
# Make sure you're in the workspace root
pwd  # should show /workspace or your project path

# Reinstall dependencies
pip install -r backend/requirements.txt
```

### Redis Connection Error

```bash
# Check Redis is running
docker-compose ps redis

# Test Redis connection
docker-compose exec redis redis-cli ping
# Should return "PONG"
```

---

## ?? What's Next?

1. **Explore the API:** Use the Swagger UI at http://localhost:8000/docs
2. **Run Tests:** `make test` to ensure everything works
3. **Read the Docs:** Check `README.md` for detailed documentation
4. **Review Code:** Start with `backend/main.py` to see the app structure
5. **Check Implementation:** See `PHASE1_IMPLEMENTATION.md` for complete details

---

## ?? Key Files Reference

| File | Purpose |
|------|---------|
| `backend/main.py` | FastAPI application entry point |
| `backend/core/config.py` | Configuration and settings |
| `backend/routers/` | API endpoint definitions |
| `backend/services/` | Business logic (valuation, bidding) |
| `backend/db/models.py` | Database models |
| `.env` | Environment variables (not in git) |
| `docker-compose.yml` | Service definitions |
| `Makefile` | Common commands |

---

## ?? Pro Tips

1. **Use Make:** All common commands are in the Makefile
2. **Check Logs:** `docker-compose logs -f` for real-time logs
3. **Hot Reload:** Changes auto-reload in development mode
4. **Environment:** Always check `.env` first if something doesn't work
5. **Tests:** Run tests before making changes to ensure baseline

---

## ?? Need Help?

- Check `README.md` for comprehensive documentation
- Review `PHASE1_IMPLEMENTATION.md` for implementation details
- Look at `blueprint.yaml` for project requirements
- See `rules.yaml` for coding standards

---

**Happy Coding! ??**
