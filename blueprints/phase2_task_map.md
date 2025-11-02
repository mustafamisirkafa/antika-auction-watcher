# ?? Phase 2 Task Map - Real Integrations & Analytics

**Duration:** 4 weeks (Weeks 7-10)  
**Test Coverage Target:** 80%  
**Total Estimated Hours:** ~205 hours  
**Priority:** High

---

## ?? Overview

Phase 2 transforms the system from mock adapters to real marketplace integrations, adds comprehensive analytics, and builds an admin dashboard for monitoring. All Phase 2 work must follow **strict enforcement** rules from `rules.yaml`.

### Key Changes from Phase 1
- ? No mock data allowed
- ? 80% minimum test coverage (up from 60%)
- ? Performance monitoring required
- ? Strict security enforcement
- ? Rate limiting mandatory

---

## ?? Task Categories

```
???????????????????????????????????????????????????????????????
?  Module                    ?  Hours ?  Priority ?  Tests    ?
???????????????????????????????????????????????????????????????
?  Marketplace Integrations  ?   40   ?   HIGH    ?   45+     ?
?  Valuation V2              ?   30   ?   HIGH    ?   28+     ?
?  Analytics & Learning      ?   35   ?   HIGH    ?   35+     ?
?  Admin API                 ?   25   ?   MEDIUM  ?   32+     ?
?  Rate Limiting             ?   20   ?   HIGH    ?   17+     ?
?  Database Optimization     ?   15   ?   MEDIUM  ?   13+     ?
?  Admin Frontend            ?   40   ?   MEDIUM  ?   N/A     ?
???????????????????????????????????????????????????????????????
?  TOTAL                     ?  205   ?           ?  170+     ?
???????????????????????????????????????????????????????????????
```

---

## ??? Week-by-Week Breakdown

### Week 7: Marketplace API Integrations

**Focus:** Replace all mock adapters with real API clients

#### Day 1-2: eBay API Integration
```
?? eBay API Client (backend/services/marketplace/ebay_client.py)
?
?? [HIGH] OAuth 2.0 Authentication (4h, 5 tests)
?  ?? Implement token acquisition and refresh
?
?? [HIGH] Finding API Client (6h, 8 tests)
?  ?? findItemsAdvanced endpoint
?  ?? findCompletedItems endpoint
?  ?? Response parsing and validation
?
?? [HIGH] Shopping API Client (4h, 6 tests)
?  ?? GetSingleItem endpoint
?  ?? Item details extraction
?
?? [MED] Rate Limiting Wrapper (3h, 4 tests)
?  ?? 10 calls/sec enforcement
?  ?? 5,000 calls/day tracking
?
?? [MED] Redis Response Caching (3h, 4 tests)
?  ?? 1-hour TTL for listings
?
?? [HIGH] Error Handling (4h, 6 tests)
   ?? Retry logic with exponential backoff
   ?? Circuit breaker pattern
   ?? Fallback to cached data

   ? Deliverable: Fully functional eBay client
   ?? Tests: 33 unit + integration tests
   ??  Total: 24 hours
```

#### Day 3-4: Etsy API Integration
```
?? Etsy API Client (backend/services/marketplace/etsy_client.py)
?
?? [HIGH] OAuth 2.0 Authentication (4h, 5 tests)
?  ?? Implement OAuth flow for Etsy API v3
?
?? [HIGH] Listings API Client (5h, 7 tests)
?  ?? getListingsByShop endpoint
?  ?? findAllListingsActive endpoint
?  ?? Response parsing
?
?? [MED] Rate Limiting Wrapper (3h, 4 tests)
?  ?? 10 calls/sec enforcement
?
?? [MED] Redis Response Caching (3h, 4 tests)
?  ?? 2-hour TTL for listings
?
?? [HIGH] Error Handling (4h, 6 tests)
   ?? Retry logic
   ?? Fallback strategies

   ? Deliverable: Fully functional Etsy client
   ?? Tests: 26 unit + integration tests
   ??  Total: 19 hours
```

#### Day 5: Sahibinden Scraper
```
?? Sahibinden Scraper (backend/services/marketplace/sahibinden_scraper.py)
?
?? [HIGH] BeautifulSoup Scraper (6h, 8 tests)
?  ?? HTML fetching with requests
?  ?? User agent rotation
?  ?? robots.txt compliance
?
?? [HIGH] Rate Limiting (4h, 5 tests)
?  ?? 1 request per 2 seconds
?
?? [HIGH] Data Extraction (5h, 7 tests)
?  ?? Parse listing cards
?  ?? Extract prices, titles, locations
?  ?? Handle Turkish characters
?
?? [MED] Caching Layer (3h, 4 tests)
?  ?? 24-hour TTL for listings
?
?? [HIGH] Error Handling (4h, 6 tests)
   ?? Handle missing elements
   ?? Detect anti-scraping blocks
   ?? Retry with backoff

   ? Deliverable: Working Sahibinden scraper
   ?? Tests: 30 unit tests
   ??  Total: 22 hours
```

#### Week 7 Summary
- ? 3 marketplace clients implemented
- ? Rate limiting on all external APIs
- ? Caching layer active
- ? 89 tests written
- ??  65 hours total

---

### Week 8: Valuation V2 & Analytics Foundation

**Focus:** Integrate real APIs into valuation engine and start analytics

#### Day 1-2: Enhanced Valuation Engine
```
?? Real Estimator (backend/services/valuation/real_estimator.py)
?
?? [HIGH] Adapter Integration (5h, 8 tests)
?  ?? Replace mock adapters with real ones
?  ?? Maintain backward compatibility
?  ?? Adapter health checking
?
?? [HIGH] Weighted Source Scoring (4h, 6 tests)
?  ?? Source reliability scores
?  ?? Data freshness weighting
?  ?? Source availability tracking
?
?? [HIGH] Category-Specific Logic (5h, 8 tests)
?  ?? Antiques valuation rules
?  ?? Jewelry pricing logic
?  ?? Collectibles estimation
?  ?? Art valuation methodology
?
?? [MED] Confidence Refinement (4h, 6 tests)
?  ?? Multi-factor confidence calculation
?  ?? Historical accuracy tracking
?  ?? Outlier detection
?
?? [LOW] Item Caching (3h, 4 tests)
   ?? Redis cache for frequent items

   ? Deliverable: Production-ready valuation engine
   ?? Tests: 32 tests
   ??  Total: 21 hours
```

#### Day 3: Valuation Caching
```
?? Cache Manager (backend/services/valuation/cache_manager.py)
?
?? [LOW] Cache Key Generation (2h, 4 tests)
?  ?? Item signature hashing
?
?? [MED] TTL-Based Invalidation (3h, 5 tests)
?  ?? Dynamic TTL based on category
?  ?? Manual cache invalidation API
?
?? [MED] Cache Warming (4h, 6 tests)
   ?? Popular items pre-caching
   ?? Background refresh jobs

   ? Deliverable: Smart caching system
   ?? Tests: 15 tests
   ??  Total: 9 hours
```

#### Day 4-5: Analytics Foundation
```
?? Outcome Tracker (backend/services/analytics/outcome_tracker.py)
?
?? [HIGH] Data Models (4h, 6 tests)
?  ?? BidOutcome model
?  ?? ProfitAnalysis model
?  ?? Database migrations
?
?? [HIGH] Recording Service (5h, 7 tests)
?  ?? Capture bid outcomes
?  ?? Record actual resale prices
?  ?? Track profit/loss
?
?? [MED] Profitability Calculation (4h, 6 tests)
?  ?? ROI calculation
?  ?? Margin analysis
?  ?? Success rate tracking
?
?? [MED] Aggregation Queries (4h, 6 tests)
?  ?? Category-wise metrics
?  ?? Time-series analysis
?  ?? Seller performance
?
?? [LOW] Export Functionality (3h, 4 tests)
   ?? CSV export
   ?? JSON API endpoint

   ? Deliverable: Bid outcome tracking system
   ?? Tests: 29 tests
   ??  Total: 20 hours
```

#### Week 8 Summary
- ? Real APIs integrated into valuation
- ? Smart caching implemented
- ? Outcome tracking active
- ? 76 tests written
- ??  50 hours total

---

### Week 9: Learning Loop & Admin Dashboard

**Focus:** Implement ML learning loop and admin backend

#### Day 1-2: Learning Service
```
?? Learning Service (backend/services/analytics/learning_service.py)
?
?? [HIGH] Category-Wise Learning (6h, 8 tests)
?  ?? Per-category margin optimization
?  ?? Historical outcome analysis
?  ?? Trend detection
?
?? [HIGH] Safety Margin Adjustment (5h, 7 tests)
?  ?? Dynamic margin calculation
?  ?? Risk-adjusted margins
?  ?? Conservative vs aggressive modes
?
?? [HIGH] Confidence Tuning (5h, 7 tests)
?  ?? Confidence score calibration
?  ?? Source weight adjustment
?  ?? Category confidence factors
?
?? [MED] Retraining Scheduler (4h, 5 tests)
?  ?? Nightly batch retraining
?  ?? Incremental learning
?  ?? Model versioning
?
?? [MED] Performance Metrics (4h, 6 tests)
   ?? Learning curve tracking
   ?? Model accuracy metrics
   ?? A/B testing support

   ? Deliverable: Self-improving learning system
   ?? Tests: 33 tests
   ??  Total: 24 hours
```

#### Day 3: Metrics Collection
```
?? Metrics Collector (backend/services/analytics/metrics_collector.py)
?
?? [MED] Collection Middleware (4h, 6 tests)
?  ?? Request/response metrics
?
?? [LOW] Response Time Tracking (3h, 4 tests)
?  ?? P50, P95, P99 percentiles
?  ?? Per-endpoint timing
?
?? [LOW] API Usage Tracking (3h, 4 tests)
?  ?? External API call counts
?  ?? Cost estimation
?
?? [MED] Database Performance (4h, 5 tests)
?  ?? Slow query detection
?  ?? Query count per endpoint
?
?? [MED] Aggregation Service (4h, 6 tests)
   ?? Time-series rollups
   ?? Metrics dashboard API

   ? Deliverable: Comprehensive metrics system
   ?? Tests: 25 tests
   ??  Total: 18 hours
```

#### Day 4-5: Admin API
```
?? Admin Routes (backend/routers/admin.py)
?
?? [HIGH] Admin Authentication (4h, 6 tests)
?  ?? Role-based access control (RBAC)
?  ?? Admin JWT middleware
?  ?? Permission checks
?
?? [MED] System Health Endpoints (4h, 6 tests)
?  ?? /admin/health/services
?  ?? /admin/health/database
?  ?? /admin/health/redis
?
?? [MED] User Management (5h, 8 tests)
?  ?? List users
?  ?? Update user roles
?  ?? Suspend/activate users
?  ?? User activity logs
?
?? [MED] Analytics Dashboard (5h, 8 tests)
?  ?? /admin/analytics/overview
?  ?? /admin/analytics/bids
?  ?? /admin/analytics/valuations
?  ?? /admin/analytics/profitability
?
?? [MED] Configuration Management (4h, 6 tests)
?  ?? View system config
?  ?? Update config values
?  ?? Feature flags
?
?? [LOW] Audit Logs (3h, 4 tests)
   ?? Admin action logging
   ?? Audit log retrieval

   ? Deliverable: Full admin API
   ?? Tests: 38 tests
   ??  Total: 25 hours
```

#### Week 9 Summary
- ? Learning loop operational
- ? Metrics collection active
- ? Admin API complete
- ? 96 tests written
- ??  67 hours total

---

### Week 10: Rate Limiting, Performance & Polish

**Focus:** Implement rate limiting, optimize performance, and finalize

#### Day 1-2: Rate Limiting System
```
?? Rate Limiter (backend/middleware/rate_limiter.py)
?
?? [HIGH] Sliding Window Limiter (5h, 8 tests)
?  ?? Redis-based implementation
?  ?? Configurable time windows
?  ?? Distributed rate limiting
?
?? [MED] Per-User Limiting (4h, 6 tests)
?  ?? User-specific limits
?  ?? Anonymous vs authenticated
?  ?? Premium user tiers
?
?? [MED] Per-Endpoint Limits (3h, 5 tests)
?  ?? Endpoint-specific configuration
?  ?? Critical endpoint protection
?  ?? Bulk operation limits
?
?? [LOW] Rate Limit Headers (2h, 3 tests)
?  ?? X-RateLimit-Limit
?  ?? X-RateLimit-Remaining
?  ?? X-RateLimit-Reset
?
?? [LOW] Exceeded Handler (2h, 4 tests)
   ?? 429 response formatting
   ?? Retry-After header

   ? Deliverable: Production-grade rate limiting
   ?? Tests: 26 tests
   ??  Total: 16 hours
```

#### Day 3: Performance Optimization
```
?? Performance Middleware (backend/middleware/performance.py)
?
?? [LOW] Request Timing (3h, 4 tests)
?  ?? Automatic request duration logging
?
?? [MED] Slow Query Detection (4h, 5 tests)
?  ?? Query execution time tracking
?  ?? N+1 query detection
?  ?? Query optimization suggestions
?
?? [MED] Memory Tracking (3h, 4 tests)
   ?? Per-request memory usage

   ? Deliverable: Performance monitoring active
   ?? Tests: 13 tests
   ??  Total: 10 hours
```

#### Day 3 (cont): Database Optimization
```
?? Database Optimization (backend/db/)
?
?? [MED] Composite Indexes (3h, 5 tests)
?  ?? (user_id, created_at) for bids
?  ?? (item_id, source) for valuations
?  ?? (category, status) for items
?
?? [MED] Query Optimization (4h, 6 tests)
?  ?? Valuation aggregation queries
?  ?? Analytics dashboard queries
?  ?? Admin user listing queries
?
?? [LOW] Connection Pooling (3h, 4 tests)
?  ?? Optimize pool size and overflow
?
?? [MED] Query Result Caching (4h, 6 tests)
   ?? Cache frequent queries
   ?? Smart invalidation

   ? Deliverable: Optimized database layer
   ?? Tests: 21 tests
   ??  Total: 14 hours
```

#### Day 4-5: Testing & Documentation
```
?? Final Testing & Documentation
?
?? [HIGH] Achieve 80% Coverage (8h)
?  ?? Fill coverage gaps
?  ?? Integration test suites
?  ?? Edge case testing
?
?? [MED] Load Testing (6h)
?  ?? Locust test scenarios
?  ?? Rate limiter stress test
?  ?? Database load test
?  ?? API performance test
?
?? [HIGH] API Documentation (4h)
?  ?? eBay integration guide
?  ?? Etsy integration guide
?  ?? Admin API reference
?  ?? Rate limiting docs
?
?? [MED] Deployment Updates (3h)
?  ?? Update .env.example
?  ?? Docker compose changes
?  ?? Migration guide
?  ?? Deployment checklist
?
?? [LOW] Code Review & Cleanup (2h)
   ?? Remove dead code
   ?? Fix linting issues
   ?? Final audit run

   ? Deliverable: Production-ready Phase 2
   ??  Total: 23 hours
```

#### Week 10 Summary
- ? Rate limiting deployed
- ? Performance optimized
- ? 80%+ test coverage achieved
- ? Documentation complete
- ??  63 hours total

---

## ?? Success Checklist

### Technical Requirements
- [ ] All mock adapters replaced with real integrations
- [ ] eBay API client functional with OAuth
- [ ] Etsy API client functional with OAuth
- [ ] Sahibinden scraper respecting rate limits
- [ ] 80%+ test coverage achieved
- [ ] Rate limiting on all endpoints
- [ ] Admin dashboard backend complete
- [ ] Learning loop adjusting margins automatically
- [ ] Metrics collection and monitoring active
- [ ] Database queries optimized
- [ ] All security rules enforced
- [ ] Load tests passing

### Documentation Requirements
- [ ] API integration guides written
- [ ] Admin API documented
- [ ] Rate limiting explained
- [ ] Deployment guide updated
- [ ] API credentials setup guide created

### Quality Gates (from rules.yaml)
- [ ] No unused imports
- [ ] No dead code
- [ ] All functions use snake_case
- [ ] All classes use PascalCase
- [ ] Public functions have docstrings
- [ ] Pylint score >= 9.0
- [ ] All tests passing
- [ ] No files exceed 500 lines

---

## ?? Tracking Metrics

### Development Velocity
```
Target: 51.25 hours/week
Actual: [To be tracked]

Week 7: __ / 51 hours
Week 8: __ / 51 hours
Week 9: __ / 51 hours
Week 10: __ / 52 hours
```

### Test Coverage Progress
```
Target: 80% minimum

marketplace_integrations: __% / 85%
valuation_v2: __% / 85%
analytics_service: __% / 80%
admin_api: __% / 80%
rate_limiting: __% / 90%
```

### Code Quality
```
Pylint Score: __ / 9.0
Files > 400 lines: __
Files > 500 lines: 0 (hard limit)
Security issues: 0
```

---

## ?? Quick Reference Commands

### Start Phase 2 Development
```bash
# Switch to phase 2 branch
git checkout -b phase-2-real-integrations

# Update environment with new API keys
cp .env.example .env.phase2
# Edit .env.phase2 with eBay/Etsy credentials

# Install any new dependencies
make install

# Run existing tests to ensure baseline
make test
```

### During Development
```bash
# Run tests for specific module
pytest backend/tests/test_marketplace.py -v

# Check test coverage
pytest --cov=backend/services/marketplace --cov-report=html

# Run quality audit
python backend/scripts/audit_quality.py

# Check rate limiter
redis-cli KEYS "rate_limit:*"
```

### Before Committing
```bash
# Format code
make format

# Run linter
make lint

# Run full test suite
make test

# Check coverage
pytest --cov=backend --cov-fail-under=80
```

---

## ?? Support & Resources

- **Phase 2 Blueprint:** `blueprints/phase2.yaml`
- **Rules:** `rules.yaml` (Phase 2 section)
- **Main Blueprint:** `blueprint.yaml`
- **Quality Audit:** `backend/scripts/audit_quality.py`

---

**Ready to start Phase 2!** ??

Follow this task map sequentially for optimal development flow. Update checkboxes as you complete tasks. Target: 4 weeks to full Phase 2 completion.
