# Changelog

All notable changes to Antika Auction Watcher will be documented in this file.

## [Unreleased]

### Added

- 🔐 **Sprint 2: Security & Rate Limiting** (2025-11-02)
  - **Credential Encryption:** Fernet-based encryption for API keys, passwords, tokens
    - `backend/core/encryption.py` - Master key management + legacy key rotation
    - `encrypt_credential()` and `decrypt_credential()` helpers
    - Environment-based key configuration (`MASTER_KEY`, `LEGACY_KEYS`)
  - **JWT Refresh Token Authentication:** Enhanced auth with access + refresh token flow
    - `backend/core/auth_enhanced.py` - JWT token creation, verification, binding
    - `backend/routers/auth.py` - Updated with `/auth/refresh`, `/auth/logout` endpoints
    - Access token: 1 hour (with user-agent + IP binding)
    - Refresh token: 24 hours (Redis-backed, revocable)
    - Token binding prevents session hijacking
  - **Rate Limiting:** Per-user and per-IP request limits (slowapi)
    - `backend/middleware/rate_limit.py` - Configurable rate limiters
    - Per-endpoint limits: `/api/bid` (10/min), `/api/valuation` (30/min), `/api/login` (5/min)
    - Global fallback: 100 requests/minute per IP
    - JSON error responses with Turkish messages
    - Rate limit headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`
  - **Security Headers:** HSTS, CSP, CORS, X-Frame-Options
    - `backend/core/security.py` - SecurityHeadersMiddleware
    - HSTS (1 year, includeSubDomains, preload)
    - Content-Security-Policy, Permissions-Policy, X-XSS-Protection
    - Secure CORS configuration with allowed origins whitelist
  - **Log Redaction:** Automatic sensitive data scrubbing
    - `backend/core/log_redaction.py` - RedactionFilter for logging
    - Redacts: passwords, tokens, API keys, credit cards, emails (partial), IPs (partial)
    - Pattern-based detection (JWT, email, phone, credit card)
    - URL redaction for query params and userinfo
    - Global filter installation on app startup
  - **Comprehensive Testing:** 85+ tests across security modules
    - `test_encryption.py` (10 tests) - Encrypt/decrypt, key rotation, edge cases
    - `test_auth_jwt_refresh.py` (25 tests) - Token creation, verification, binding, refresh flow
    - `test_rate_limiting.py` (20 tests) - Rate limit enforcement, Redis integration
    - `test_log_redaction.py` (30 tests) - Redaction patterns, filtering, edge cases
  - **Configuration:** New environment variables for security
    - `MASTER_KEY` - Fernet encryption key (required)
    - `JWT_SECRET_KEY` - JWT signing key (required)
    - `ACCESS_TOKEN_EXPIRE_MINUTES=60`, `REFRESH_TOKEN_EXPIRE_HOURS=24`
    - `ALLOWED_ORIGINS` - CORS whitelist
  - **Performance:** ~5-10ms auth overhead per request (JWT + rate limit check)
  - **Coverage:** 91% test coverage across security components
  - **Documentation:** `SPRINT2_COMPLETE.md` (detailed implementation guide)

- 📊 **Phase 17: Analytics Dashboard**
  - Backend analytics router (`GET /api/analytics/overview`)
  - Aggregates 5 system metrics concurrently
  - 15-second Redis cache for performance
  - Frontend dashboard page with 5 widgets:
    - AutoBid status card (active bids, SLA p95)
    - Valuation chart (market value trends, demand score)
    - Seller trust pie chart (trust distribution)
    - User preferences bars (allowlist/blocklist impact)
    - System health status (Redis, cache, DB latency)
  - Recharts integration for visualizations
  - React Query with 10-second auto-refresh
  - Turkish localized analytics labels (40+ translations)
  - Performance: <150ms backend response time
  - 8 comprehensive unit tests
  - Responsive grid layout (mobile → desktop)

- 🌍 **Phase 16-TR: Full Turkish Localization**
  - Frontend i18n library with 150+ Turkish translations
  - `frontend/src/i18n/tr.json` - Complete translation dictionary
  - `frontend/src/lib/i18n.ts` - i18n helper functions
  - All UI components localized (SellerPreferences, SellerListTable)
  - Backend i18n helper (`backend/core/i18n.py`)
  - Turkish API response messages (50+ success/error translations)
  - Turkish date/time formatting (DD.MM.YYYY HH:mm)
  - Turkish currency formatting (₺ Turkish Lira)
  - Configuration: default language = "tr"
  - Fallback strategy for missing translations
  - Performance maintained: ≤3s SLA

- 🚀 **Phase 14: User Seller Preferences**
  - Per-user allowlist and blocklist for sellers
  - API endpoints: GET /api/user/prefs, POST /api/user/prefs/update
  - Redis caching (10-minute TTL) + Postgres storage
  - Event bus integration (user_prefs.updated events)
  - Integration with AutoBid Engine for bid filtering
  - Check seller allowed endpoint for real-time validation

- 🚀 **Phase 12: Seller Intelligence Layer**
  - Per-seller behavioral analytics (pricing strategy, discount habits, reliability)
  - Seller profile builder with trust scoring
  - Integration with AutoBid Engine (confidence adjustment via seller trust)
  - API endpoints: seller profiles, top sellers, market trends, refresh
  - Redis caching (24h TTL) + Postgres storage
  - Audit logging extended with seller_id and seller_trust fields

- ?? **Phase 11: Dynamic Valuation Feed**
  - External market data integration (eBay, Etsy, Instagram, Sahibinden)
  - Data fusion engine with weighted merge algorithm
  - Redis caching with 10-minute TTL and backoff logic
  - Real-time valuation updates for AutoBid Engine
  - API endpoints: live valuation, manual refresh, source list, health status
  - Fuses internal bid data and external market signals for adaptive pricing

- Phase 10: Realtime AI Bidding Engine (AutoBid)
  - Event bus service (Redis Pub/Sub)
  - Price detector with debouncing
  - Valuation reactor (<1.2s SLA)
  - Bid policy engine
  - Bid dispatcher with retry logic
  - AutoBid engine orchestrator
  - Bidding rules model and CRUD API
  - AutoBid control API (start/stop/status)
  - Audit logging and metrics
  - WebSocket events for real-time UI updates

- Phase 9: Profit Advisor / Pre-Auction Intelligence
  - AI-powered profit estimation
  - Multi-source market data aggregation
  - Profit margin calculation
  - Confidence scoring and risk assessment
  - Nightly analysis scheduler
  - Profit dashboard page
  - ProfitCard component

- Phase 8: Access Control, Plans & Agent Quotas
  - Team-based access control
  - Plan-based AI agent limits
  - Budget tracking
  - Usage statistics

### Removed
- ✂️ **Phase 15: Seller Collaboration Network**
  - **Reason:** Unnecessary complexity; AutoBid already optimized via seller intelligence (Phase 12) and user preferences (Phase 14)
  - **Impact:** None — Seller trust scores and user blocklists provide sufficient fraud protection
  - Removed to maintain lean architecture and performance stability
  - Focus remains on direct seller intelligence and user-controlled preferences

- ✂️ **Phase 13: Seller Reputation Alerts**
  - **Reason:** Unnecessary alert complexity; trust data already integrated into AutoBid
  - **Impact:** None — Seller trust scores remain available via API
  - Removed to maintain lean, reactive-only architecture
  - Real-time alerts deemed redundant with existing AutoBid trust integration

- ✂️ **Phase 10.5 Anti-Sniping Tactic Engine**
  - **Reason:** Not relevant to system purpose (our engine itself is a bot)
  - **Impact:** None — AutoBid performance and logic unchanged
  - Removed anti-sniping guard, sniping policy, delay queue, and timing intelligence services
  - Removed anti-sniping configuration settings
  - AutoBid Engine remains fully functional with Phase 10 features

## [1.0.0] - 2025-11-02

### Added
- 🚀 **Phase 12: Seller Intelligence Layer**
  - Per-seller behavioral analytics (pricing strategy, discount habits, reliability)
  - Seller profile builder with trust scoring
  - Integration with AutoBid Engine (confidence adjustment via seller trust)
  - API endpoints: seller profiles, top sellers, market trends, refresh
  - Redis caching (24h TTL) + Postgres storage
  - Audit logging extended with seller_id and seller_trust fields

- Phase 1-7: Core backend and frontend infrastructure
- User authentication and authorization
- Real-time auction monitoring
- AI valuation engine
- Learning and metrics panels
- Admin console
- Production deployment configuration
