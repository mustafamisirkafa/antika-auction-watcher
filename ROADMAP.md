# Antika Auction Watcher - Product Roadmap

## Overview
Antika Auction Watcher is an AI-powered auction monitoring and bidding system designed for Turkish antique marketplaces. The system provides real-time valuation, profit estimation, automated bidding, and seller intelligence.

---

## ?? Vision
Enable intelligent, automated bidding with AI-driven insights for antique auctions, maximizing profit potential while minimizing risk.

---

## ? Completed Phases

### Phase 1: Backend Core (Week 1)
**Status:** ? Complete  
**Scope:**
- FastAPI backend with PostgreSQL
- JWT authentication
- Rate limiting
- Basic CRUD operations
- Docker setup

---

### Phase 2: AI Valuation Engine (Week 1-2)
**Status:** ? Complete  
**Scope:**
- Valuation estimator service
- Machine learning integration
- Learning service with feedback loop
- 80%+ test coverage

---

### Phase 3: Live Auction Feed (Week 2)
**Status:** ? Complete  
**Scope:**
- WebSocket client for real-time updates
- Zustand store for auction state
- AuctionFeed UI component
- Dashboard integration
- Auto-reconnect logic

---

### Phase 3 (Extension): Learning & Metrics Panels (Week 3)
**Status:** ? Complete  
**Scope:**
- LearningInsights component (model accuracy, efficiency)
- MetricsPanel component (system health, performance)
- Dashboard tabs integration
- Recharts visualizations
- 80%+ frontend coverage

---

### Phase 4: Admin Console (Week 3)
**Status:** ? Complete  
**Scope:**
- System health monitoring
- Learning logs table
- CSV export functionality (valuations, outcomes)
- Admin-only access control

---

### Phase 5: AI Auction Advisor (Week 4)
**Status:** ? Complete  
**Scope:**
- Multi-sense AI logic (Pattern, Market, Behavior, Risk)
- `/api/advisor/suggest` and `/api/advisor/analyze_batch` endpoints
- WebSocket `advisor_update` events
- AdvisorPanel UI component
- User behavior tracking

---

### Phase 6: AI Feedback Learning Loop (Week 4-5)
**Status:** ? Complete  
**Scope:**
- Feedback collector service
- Feedback learner with dynamic weight adjustment
- Background learning job (every 30 minutes)
- `/api/advisor/feedback` endpoint
- AdvisorPerformance visualization
- 80%+ backend & frontend coverage

---

### Phase 7: Production Deployment & Monitoring (Week 5)
**Status:** ? Complete  
**Scope:**
- Docker Compose production setup
- Nginx reverse proxy with HTTPS
- Prometheus + Alertmanager SLOs
- Loki + Promtail log aggregation
- Grafana dashboards
- Backup/restore scripts
- GitHub Actions CI/CD

---

### Phase 8: Access Control, Plans & Agent Quotas (Week 6)
**Status:** ? Complete  
**Scope:**
- Team-based access control
- Plan-based AI agent limits (FREE, PRO, ENTERPRISE)
- Budget tracking and usage statistics
- Agent manager service with Redis tracking
- Frontend settings pages (team, plan)
- AgentUsageBar component
- 80%+ coverage

---

### Phase 9: Profit Advisor / Pre-Auction Intelligence (Week 7)
**Status:** ? Complete  
**Scope:**
- AI-powered profit estimation before auctions go live
- Multi-source market data aggregation (eBay, Etsy, Sahibinden, Letgo)
- Profit margin and confidence scoring
- `ProfitEstimate` model with recommended max bid
- Nightly analysis scheduler
- Profit dashboard page with ProfitCard components
- PRO/ENTERPRISE plan gating
- 80%+ backend & frontend coverage

---

### Phase 10: Realtime AI Bidding Engine (AutoBid) (Week 8)
**Status:** ? Complete  
**Scope:**
- Redis Pub/Sub event bus
- Price detector with debouncing
- Valuation reactor (< 1.2s SLA)
- Bid policy engine (budget, rules, risk)
- Bid dispatcher with retry logic
- AutoBid orchestrator (? 3s end-to-end)
- User bidding rules (CRUD API)
- AutoBid control API (start/stop/status)
- Audit logging and Prometheus metrics
- WebSocket real-time events
- 80%+ backend coverage

---

### ~~Phase 10.5: Anti-Sniping & Bid Escalation~~ (Week 8)
**Status:** ? Removed  
**Reason:** Not relevant to system purpose (our engine itself is a bot)  
**Impact:** None ? AutoBid performance and logic unchanged

---

### Phase 11: Dynamic Valuation Feed (Week 9)
**Status:** ? Complete  
**Scope:**
- External market data integration (eBay, Etsy, Instagram, Sahibinden)
- MarketFeed Manager (API connections, normalization)
- ValuationFusion Core (weighted merge algorithm)
- ValuationCache Orchestrator (Redis, 10-min TTL, backoff)
- Integration with ValuationReactor and AutoBid Engine
- API endpoints: `/api/valuation/live`, `/refresh`, `/sources`, `/health`
- ? 3s total SLA maintained

---

### Phase 12: Seller Intelligence Layer (Week 10)
**Status:** ✅ Complete  
**Scope:**
- Seller behavioral analytics (pricing strategy, discount habits, reliability)
- SellerEngine service (per-seller metrics)
- SellerProfileBuilder (trust scoring, Redis + Postgres)
- API endpoints: `/api/sellers/{id}`, `/top`, `/trends`, `/refresh`
- Integration with AutoBid Engine (confidence adjustment via trust score)
- Audit logging extended with seller_id and seller_trust
- Redis caching (24h TTL)
- ≤ 3s AutoBid SLA maintained

---

### Phase 14: User Seller Preferences (Week 11)
**Status:** ✅ Complete  
**Scope:**
- User-controlled seller allowlists and blocklists
- CRUD API: `/api/user/prefs`, `/api/user/prefs/update`, `/api/user/prefs/check/{seller_id}`
- Redis caching (10-min TTL) + Postgres storage
- Event bus integration (`user_prefs.updated`)
- Integration with AutoBid Engine (bid filtering by user preference)
- Frontend UI: SellerPreferences page with add/remove actions
- Optimistic UI updates with React Query + Zustand
- 25 comprehensive tests (backend)
- ≤ 3s AutoBid SLA maintained

---

## ?? Planned Phases

### ~~Phase 13: Seller Reputation Alerts~~ (Week 11)
**Status:** ❌ Removed  
**Reason:** Unnecessary alert complexity; trust data already integrated into AutoBid decisions  
**Impact:** None — Seller trust scores remain available via API; real-time alerts deemed redundant

---

### ~~Phase 15: Seller Collaboration Network~~ (Week 12)
**Status:** ❌ Removed  
**Reason:** Unnecessary complexity; AutoBid already optimized via seller intelligence (Phase 12) and user preferences (Phase 14)  
**Impact:** None — Seller trust scores and user blocklists provide sufficient fraud protection

---

### Phase 16-TR: Full Turkish Localization (Week 12)
**Status:** ✅ Complete  
**Goal:** Convert entire application to Turkish as default language.

**Scope:**
- Frontend i18n library (`tr.json`, `i18n.ts`)
- All UI components localized to Turkish
- Backend i18n helper (`backend/core/i18n.py`)
- API responses in Turkish
- Date/time formatting (DD.MM.YYYY HH:mm)
- Currency formatting (₺ Turkish Lira)
- Configuration: default language = "tr"

**Success Criteria:**
- ✅ All UI visible text in Turkish
- ✅ All API success/error messages in Turkish
- ✅ Default language = Turkish
- ✅ i18n fallback works if missing key
- ✅ No broken routes or missing translations
- ✅ SLA ≤3s maintained

---

### Phase 17: Analytics Dashboard (Week 13)
**Status:** ✅ Complete  
**Goal:** Single-screen monitoring view with real-time system metrics.

**Scope:**
- Backend analytics router (`/api/analytics/overview`)
- 5 concurrent metric aggregations
- 15-second Redis cache
- Frontend dashboard page with 5 widgets
- Recharts visualizations
- 10-second auto-refresh
- Turkish localized labels
- Performance: <150ms backend response

**Success Criteria:**
- ✅ GET /api/analytics/overview functional (<150ms)
- ✅ 5 widgets display correctly
- ✅ Turkish labels visible
- ✅ Auto-refresh every 10s works
- ✅ SLA ≤3s maintained

---

### Phase 17: Mobile App (Week 14-16) [PLANNED]
**Goal:** Native mobile app for iOS and Android.

**Scope:**
- React Native or Flutter app
- Push notifications for bids, alerts, auction events
- Offline mode for viewing cached auctions
- Biometric authentication
- QR code scanner for auction items

**Success Criteria:**
- App launches in <2s
- 90%+ feature parity with web app
- Push notifications delivered in <5s

---

### Phase 18: AI Model Fine-Tuning (Week 17) [PLANNED]
**Goal:** Fine-tune valuation and trust models with production data.

**Scope:**
- Collect labeled dataset from audit logs
- Train custom transformer model for valuation
- Fine-tune trust scoring with historical seller data
- A/B testing framework for model comparison
- Model versioning and rollback

**Success Criteria:**
- Valuation accuracy +10% over baseline
- Trust score precision +15%
- Model inference time <500ms

---

### Phase 19: Advanced Analytics Dashboard (Week 18) [PLANNED]
**Goal:** Deep-dive analytics for power users.

**Scope:**
- Custom report builder
- Time-series analysis (profit trends, bid success rate)
- Category-specific insights
- Competitor analysis (compare with other teams)
- Export to PDF/Excel

**Success Criteria:**
- Dashboard loads in <1s
- 20+ pre-built report templates
- Export completes in <5s

---

### Phase 20: API Marketplace (Week 19-20) [PLANNED]
**Goal:** Public API for third-party integrations.

**Scope:**
- API key management
- Rate limiting per API key
- Webhooks for auction events
- Developer portal with documentation
- Usage analytics and billing

**Success Criteria:**
- API key provisioning automated
- 99.9% uptime SLA
- 10+ third-party integrations

---

## ?? Success Metrics (Overall)

| Metric | Current | Target (Q4 2025) |
|--------|---------|------------------|
| Test Coverage | 80% | 90% |
| AutoBid Success Rate | - | 85% |
| Valuation Accuracy | - | 90% |
| Seller Trust Precision | - | 95% |
| API Response Time (p99) | <230ms | <100ms |
| Active Users | - | 10,000 |
| AutoBid Auctions/Day | - | 500 |

---

## ?? Timeline Summary

| Phase | Duration | Status |
|-------|----------|--------|
| Phase 1-7 | Week 1-5 | ✅ Complete |
| Phase 8 | Week 6 | ✅ Complete |
| Phase 9 | Week 7 | ✅ Complete |
| Phase 10 | Week 8 | ✅ Complete |
| Phase 11 | Week 9 | ✅ Complete |
| Phase 12 | Week 10 | ✅ Complete |
| Phase 14 | Week 11 | ✅ Complete |
| Phase 17 | Week 13 | ✅ Complete |
| Phase 18-19 | Week 14-15 | 🚧 Planned |

---

## 📚 Related Documentation
- `CHANGELOG.md` - All changes by phase
- `PHASE17_ANALYTICS_DASHBOARD.md` - Analytics Dashboard (Latest)
- `PHASE16_TR_MODE.md` - Turkish Localization
- `PHASE14_COMPLETE_FULL.md` - User Seller Preferences
- `PHASE12_COMPLETE.md` - Seller Intelligence Layer
- `PHASE11_COMPLETE.md` - Dynamic Valuation Feed
- `PHASE10_COMPLETE.md` - AutoBid Engine
- `PHASE9_COMPLETE.md` - Profit Advisor
- `PHASE8_COMPLETE.md` - Access Control & Plans

---

_Last Updated: 2025-11-03_
