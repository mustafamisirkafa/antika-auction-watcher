# Antika Auction Watcher - Phase 1 Backend

AI-powered Instagram live auction monitoring and auto-bidding system.

## ??? Architecture

Phase 1 implements the core backend foundation:

- **FastAPI** - Modern Python web framework
- **PostgreSQL** - Relational database for data persistence
- **Redis** - Caching and Pub/Sub for real-time features
- **SQLModel** - Type-safe ORM with Pydantic integration
- **WebSocket** - Real-time bidirectional communication
- **JWT Authentication** - Secure user authentication

## ?? Project Structure

```
workspace/
??? backend/
?   ??? core/                 # Core configuration and security
?   ?   ??? config.py        # Application settings
?   ?   ??? security.py      # JWT and password hashing
?   ?   ??? encryption.py    # Data encryption utilities
?   ??? db/                  # Database models and setup
?   ?   ??? database.py      # Database engine and sessions
?   ?   ??? models.py        # SQLModel definitions
?   ??? routers/             # API endpoints
?   ?   ??? auth.py          # Authentication routes
?   ?   ??? items.py         # Item management routes
?   ?   ??? valuations.py   # Valuation routes
?   ?   ??? bids.py          # Bidding routes
?   ?   ??? websocket.py     # WebSocket endpoints
?   ??? services/            # Business logic
?   ?   ??? valuation/       # Valuation engine
?   ?   ?   ??? adapters.py  # Mock marketplace adapters
?   ?   ?   ??? estimator.py # Valuation estimator
?   ?   ??? bidding/         # Bidding engine
?   ?       ??? agent.py     # Bidding decision logic
?   ?       ??? instagram.py # Instagram integration
?   ??? realtime/            # Real-time layer
?   ?   ??? redis_manager.py    # Redis Pub/Sub
?   ?   ??? websocket_manager.py # WebSocket manager
?   ??? tests/               # Test suite
?   ??? main.py              # FastAPI application
?   ??? requirements.txt     # Python dependencies
??? docker-compose.yml       # Docker services
??? Makefile                 # Common commands
??? .env.example             # Environment variables template
```

## ?? Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Make (optional)

### Installation

1. **Clone and setup environment:**
   ```bash
   cp .env.example .env
   # Edit .env and update JWT_SECRET and ENCRYPTION_KEY
   ```

2. **Generate encryption key:**
   ```bash
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```

3. **Install dependencies:**
   ```bash
   make install
   # or
   pip install -r backend/requirements.txt
   ```

4. **Start services with Docker:**
   ```bash
   make docker-up
   # or
   docker-compose up -d
   ```

5. **Run migrations (if using Alembic):**
   ```bash
   make migrate-up
   ```

6. **Start development server:**
   ```bash
   make dev
   # or
   uvicorn backend.main:app --reload
   ```

The API will be available at `http://localhost:8000`

## ?? API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login and get JWT token
- `GET /api/v1/auth/me` - Get current user info

### Items
- `POST /api/v1/items` - Create auction item
- `GET /api/v1/items` - List items (with filters)
- `GET /api/v1/items/{item_id}` - Get item details
- `PATCH /api/v1/items/{item_id}` - Update item

### Valuations
- `POST /api/v1/valuations/estimate` - Estimate item value
- `GET /api/v1/valuations/item/{item_id}` - Get item valuations

### Bids
- `POST /api/v1/bids/decision` - Get bid recommendation
- `POST /api/v1/bids/place` - Place a bid
- `GET /api/v1/bids/item/{item_id}` - Get item bids
- `GET /api/v1/bids/user/me` - Get user's bids

### WebSocket
- `WS /ws/{channel}` - WebSocket connection for real-time updates
  - Channels: `valuations`, `bids`, `items`

## ?? Testing

Run tests with coverage:
```bash
make test
# or
pytest backend/tests/ -v --cov=backend
```

Run tests without coverage:
```bash
make test-fast
```

## ?? Code Quality

Run linting:
```bash
make lint
# or
pylint backend/
```

Format code:
```bash
make format
# or
black backend/
```

## ?? Docker Commands

```bash
make docker-up        # Start services
make docker-down      # Stop services
make docker-logs      # View logs
make docker-rebuild   # Rebuild containers
make db-shell         # Connect to PostgreSQL
make redis-cli        # Connect to Redis
```

## ?? Security Features

? **JWT Authentication** - Secure token-based auth  
? **Bcrypt Password Hashing** - Industry-standard password security  
? **Credential Encryption** - Encrypted Instagram credentials  
? **Environment Variables** - Secrets stored in .env  
? **Rate Limiting Ready** - Prepared for rate limiting implementation

## ?? Phase 1 Features

### ? Completed

- [x] FastAPI backend with async I/O
- [x] PostgreSQL database with SQLModel
- [x] Redis for caching and Pub/Sub
- [x] JWT authentication system
- [x] User registration and login
- [x] Item management API
- [x] Valuation engine with mock adapters (eBay, Etsy, Sahibinden)
- [x] Bidding agent with decision rules
- [x] Semi-auto bidding mode
- [x] Duplicate bid prevention
- [x] WebSocket real-time updates
- [x] Redis Pub/Sub broadcasting
- [x] Docker Compose setup
- [x] Comprehensive test suite
- [x] Code quality tools (pylint, black)

### ?? Phase 1 Goals Met

- ? Backend foundation (FastAPI, PostgreSQL, Redis)
- ? Valuation engine with mock adapters
- ? Semi-auto bidding engine
- ? Real-time layer (Redis Pub/Sub + WebSocket)
- ? Docker Compose environment
- ? 60%+ test coverage (Phase 1 requirement)

## ?? Workflow Example

1. **Register and login:**
   ```bash
   curl -X POST http://localhost:8000/api/v1/auth/register \
     -H "Content-Type: application/json" \
     -d '{"email":"user@example.com","username":"user","password":"pass123"}'
   ```

2. **Create an auction item:**
   ```bash
   curl -X POST http://localhost:8000/api/v1/items \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"title":"Vintage Watch","category":"antiques","current_price":100}'
   ```

3. **Get valuation estimate:**
   ```bash
   curl -X POST http://localhost:8000/api/v1/valuations/estimate \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"item_id":1}'
   ```

4. **Get bid decision:**
   ```bash
   curl -X POST http://localhost:8000/api/v1/bids/decision \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"item_id":1,"mode":"semi_auto"}'
   ```

5. **Place bid:**
   ```bash
   curl -X POST http://localhost:8000/api/v1/bids/place \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"item_id":1,"mode":"semi_auto"}'
   ```

## ?? Next Steps (Phase 2)

- [ ] Integrate real marketplace APIs (eBay, Etsy, Sahibinden)
- [ ] Add analytics and learning loop
- [ ] Build admin dashboard
- [ ] Implement real Instagram live integration
- [ ] Add performance monitoring
- [ ] Increase test coverage to 80%

## ??? Development

### Environment Variables

Required:
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `JWT_SECRET` - Secret key for JWT tokens
- `ENCRYPTION_KEY` - Key for encrypting sensitive data

Optional:
- `INSTAGRAM_USERNAME` - Instagram username
- `INSTAGRAM_PASSWORD` - Instagram password

### Making Changes

1. Create a feature branch
2. Make your changes
3. Run tests: `make test`
4. Run linting: `make lint`
5. Format code: `make format`
6. Commit changes

### Database Migrations

Create migration:
```bash
make migrate-create
```

Apply migrations:
```bash
make migrate-up
```

Rollback migration:
```bash
make migrate-down
```

## ?? License

Copyright ? 2024 Mustafa Misirkafa

## ?? Support

For questions or issues, please refer to the blueprint.yaml and rules.yaml files.
