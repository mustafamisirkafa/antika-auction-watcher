# Changelog

All notable changes to Antika Auction Watcher will be documented in this file.

## [Unreleased]

### Added
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
- ?? **Phase 10.5 Anti-Sniping Tactic Engine**
  - **Reason:** Not relevant to system purpose (our engine itself is a bot)
  - **Impact:** None ? AutoBid performance and logic unchanged
  - Removed anti-sniping guard, sniping policy, delay queue, and timing intelligence services
  - Removed anti-sniping configuration settings
  - AutoBid Engine remains fully functional with Phase 10 features

## [1.0.0] - 2025-11-02

### Added
- Phase 1-7: Core backend and frontend infrastructure
- User authentication and authorization
- Real-time auction monitoring
- AI valuation engine
- Learning and metrics panels
- Admin console
- Production deployment configuration
