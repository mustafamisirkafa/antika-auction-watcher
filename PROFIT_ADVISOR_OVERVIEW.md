# Profit Advisor - System Overview

**Version:** 1.0  
**Last Updated:** November 2, 2025

---

## ?? What is the Profit Advisor?

The **Profit Advisor** is an AI-powered pre-auction intelligence system that analyzes upcoming auction items and recommends the maximum profitable bid based on real-time market data from multiple sources. It helps users make data-driven bidding decisions and avoid overpaying.

### Key Benefits

? **Data-Driven Decisions** - Bid confidently based on aggregated market data  
? **Risk Mitigation** - Confidence scoring and risk assessment for each item  
? **Time Savings** - Automated market research across multiple platforms  
? **Profit Optimization** - Target 15% ROI buffer on every bid  
? **Pre-Auction Intelligence** - Know the opportunity before auction starts

---

## ?? How It Works

### 1. Market Data Collection

The system queries **4 major marketplace APIs**:
- **eBay** - Global auction/marketplace data (1.0x baseline)
- **Etsy** - Handmade/vintage items (1.15x premium)
- **Sahibinden** - Turkish local marketplace (0.85x discount)
- **Letgo** - Local classifieds (0.80x discount)

For each auction item, it searches for similar products by:
- Title matching (keyword extraction)
- Category filtering
- Condition normalization

### 2. Data Aggregation

Results from all sources are combined using **weighted averaging**:

```
Market Average = ?(price_i ? sample_size_i) / ?(sample_size_i)
```

**Why weighted?**  
Larger sample sizes indicate more reliable data.  
Example: 50 eBay listings > 5 Etsy listings

### 3. Profit Calculation

**Target ROI Buffer:** 15%

```
Recommended Max Bid = Market Average ? 0.85
Profit Margin = (Market Avg - Max Bid) / Max Bid
Profit Amount = Market Avg - Max Bid
```

**Example:**
- Market Average: 1,000?
- Recommended Max Bid: 850?
- Profit Margin: 17.6%
- Profit Amount: 150?

### 4. Confidence Scoring

Confidence measures how reliable the estimate is (0-100%):

```
Confidence = (
    Liquidity Score        ? 35% +  # Market depth
    Volatility Stability   ? 30% +  # Price consistency
    Sample Size (norm)     ? 20% +  # Data quantity
    Visual Match (future)  ? 15%    # Image similarity
)
```

**Confidence Levels:**
- **High (80-100%):** Strong data, low volatility ? ?? Green
- **Medium (60-79%):** Moderate data, some uncertainty ? ?? Yellow
- **Low (0-59%):** Limited data, high volatility ? ?? Red

### 5. Risk Assessment

```python
if confidence >= 80% AND profit_margin >= 15% AND volatility < 30%:
    risk = "LOW"
elif confidence < 60% OR profit_margin < 5%:
    risk = "HIGH"
else:
    risk = "MEDIUM"
```

---

## ?? System Components

### Backend Services

**1. ProfitAdvisorService** (`backend/services/profit_advisor.py`)
- Core analysis engine
- Profit calculation logic
- Confidence and risk scoring
- Database persistence

**2. MarketFetcher** (`backend/services/market_fetcher.py`)
- Multi-source market data fetching
- Concurrent API calls (async)
- Weighted aggregation
- Deterministic pseudo-random data (development)

**3. Scheduler** (`backend/scheduler.py`)
- Nightly analysis job (03:00 AM)
- Background task orchestration
- APScheduler integration

### Database Models

**1. AuctionItem**
- Upcoming auction listings
- Team ownership
- Basic item metadata

**2. MarketReference**
- External market data snapshots
- Source, price, sample size
- Liquidity and volatility metrics

**3. ProfitEstimate**
- AI-generated profit analysis
- Recommended max bid
- Confidence and risk scores
- Expiration (24h caching)

### API Endpoints

```
POST   /api/v1/profit/items             # Create auction item
GET    /api/v1/profit/{team_id}         # Get team estimates
GET    /api/v1/profit/item/{item_id}    # Get item estimate
POST   /api/v1/profit/analyze           # Trigger analysis
GET    /api/v1/profit/market-references # Get market data
```

**Access Control:**  
All endpoints require PRO or ENTERPRISE plan (agent_limit >= 25).

### Frontend Components

**1. ProfitCard** (`frontend/src/components/ProfitCard.tsx`)
- Visual item analysis display
- Color-coded confidence and profit
- Auto-bid CTA (plan-gated)
- Market metrics visualization

**2. Profit Dashboard** (`frontend/src/pages/profit.tsx`)
- Tabbed interface (Insights + Comparisons)
- Filters (risk, confidence)
- Stats overview
- Auto-refresh (60s)
- Upgrade prompt for FREE users

**3. Dashboard Integration**
- "?? Profit Advisor" tab in main dashboard
- Lazy-loaded for performance
- WebSocket connection preserved

---

## ?? Profit Estimation Pipeline

### Stage 1: Input

```json
{
  "lot_id": "LOT-2025-1234",
  "title": "19th Century Silver Candleholder",
  "category": "silver",
  "starting_price": 800.0,
  "auction_date": "2025-11-10T14:00:00Z"
}
```

### Stage 2: Market Research

Concurrent async queries to:
1. eBay ? `avg_price: 1050?, samples: 28, liquidity: 0.85`
2. Etsy ? `avg_price: 1200?, samples: 12, liquidity: 0.90`
3. Sahibinden ? `avg_price: 950?, samples: 15, liquidity: 0.75`
4. Letgo ? `avg_price: 880?, samples: 8, liquidity: 0.65`

### Stage 3: Aggregation

```
Weighted Avg = (1050?28 + 1200?12 + 950?15 + 880?8) / (28+12+15+8)
             = 1,037?

Avg Liquidity = (0.85 + 0.90 + 0.75 + 0.65) / 4 = 0.79
Avg Volatility = 0.28
```

### Stage 4: Profit Calculation

```
Market Value: 1,037?
Recommended Max Bid: 1,037 ? 0.85 = 881?
Profit Margin: (1037 - 881) / 881 = 17.7%
Profit Amount: 156?
```

### Stage 5: Confidence & Risk

```
Confidence = 0.79 ? 0.35 + 0.72 ? 0.30 + 0.80 ? 0.20 + 0.0 ? 0.15
           = 0.653 (65.3%)
           
Risk = MEDIUM (confidence 60-80%, profit > 15%)
```

### Stage 6: Output

```json
{
  "estimated_value": 1037.0,
  "recommended_max_bid": 881.0,
  "profit_margin": 0.177,
  "profit_amount": 156.0,
  "confidence": 0.653,
  "risk_level": "medium",
  "market_volatility": 0.28,
  "liquidity_avg": 0.79
}
```

---

## ?? Access Control

### Plan Requirements

**Feature Access:**
| Plan       | Access | Agent Limit |
|------------|--------|-------------|
| FREE       | ? No   | 3           |
| PRO        | ? Yes  | 25          |
| ENTERPRISE | ? Yes  | 100         |

**Enforcement:**
```python
def check_profit_advisor_access(team_context):
    plan_limit = get_plan_limit(team_context.team.plan_code)
    if plan_limit < 25:  # PRO has agent_limit >= 25
        raise HTTPException(402, {
            "message": "Profit Advisor requires PRO or ENTERPRISE plan.",
            "current_plan": team_context.team.plan_code,
            "required_plan": "PRO",
            "upgrade_url": "/settings/plan"
        })
```

### User Experience

**FREE Users:**
- See "Upgrade to PRO" notice on Profit Dashboard
- API returns 402 Payment Required
- Beautiful upgrade CTA with feature benefits

**PRO/ENTERPRISE Users:**
- Full access to Profit Dashboard
- Auto-bid button enabled
- Nightly analysis for all their auction items
- Unlimited profit estimates

---

## ?? Nightly Analysis Workflow

### Schedule: Daily at 03:00 AM

**Process:**
1. Fetch all teams with upcoming auctions (auction_date > now)
2. For each team:
   - Get auction items (not yet analyzed or expired estimates)
   - Analyze each item concurrently
   - Save ProfitEstimate and MarketReferences
3. Log analysis summary (items analyzed, failures, avg confidence)

**Performance:**
- Async/await for I/O operations
- Batch processing (10 items at a time)
- Redis caching for recent estimates
- Database connection pooling

**Idempotency:**
- Checks for existing estimates (created < 24h ago)
- Uses `force_refresh=False` to skip recent analysis
- Handles failures gracefully (continues with next item)

---

## ?? Market Data Sources

### eBay
**Characteristics:**
- Global reach, large sample sizes
- Auction + Buy It Now prices
- Baseline pricing (1.0x multiplier)
- High liquidity

### Etsy
**Characteristics:**
- Premium handmade/vintage market
- Higher prices (1.15x multiplier)
- Niche categories (jewelry, art)
- Moderate liquidity

### Sahibinden
**Characteristics:**
- Turkish local marketplace
- Lower prices (0.85x multiplier)
- Great for Turkish antiques
- High liquidity (local demand)

### Letgo
**Characteristics:**
- Classified ads, lower prices
- Lowest prices (0.80x multiplier)
- Good for floor price estimates
- Variable liquidity

---

## ?? UI/UX Design

### Color Coding System

**Profit Margin:**
- ?? Green: ?20% margin (excellent opportunity)
- ?? Yellow: 10-19% margin (good opportunity)
- ?? Orange: <10% margin (marginal opportunity)

**Confidence:**
- ?? Green: ?80% (high confidence)
- ?? Yellow: 60-79% (medium confidence)
- ?? Red: <60% (low confidence)

**Risk Level:**
- ?? LOW: Safe bet, strong data
- ?? MEDIUM: Moderate uncertainty
- ?? HIGH: High volatility or low data

### Progress Bars

**Profit Margin:**
```
????????????????????????????????????
? ???????????????????????????????? ? 22%
????????????????????????????????????
```

**Confidence:**
```
Confidence: 82% ??
```

---

## ?? Testing Strategy

### Backend Tests (33 tests)

**Coverage Areas:**
- Profit calculation accuracy
- Confidence scoring logic
- Risk assessment rules
- Market data aggregation
- Plan-based access control
- API endpoint behavior
- Caching and refresh logic

### Frontend Tests (25 tests)

**Coverage Areas:**
- Component rendering
- Color-coded badges
- Plan gating UI
- Auto-bid button state
- Filters and tabs
- Empty and loading states
- Upgrade prompts

---

## ?? Success Metrics

**Key Performance Indicators:**
- **Accuracy:** % of estimates within 10% of actual resale value
- **Coverage:** % of auction items with profit estimates
- **Confidence:** Average confidence score across estimates
- **User Adoption:** % of PRO/ENTERPRISE users using Profit Advisor
- **Profitability:** ROI for bids placed via Auto-Bid

**Current Targets:**
- 80%+ accuracy
- 95%+ coverage
- 75%+ average confidence
- 60%+ user adoption (PRO+ users)

---

## ?? Future Roadmap

### Phase 10: Real-Time Bidding
- Auto-bid integration with Profit Advisor
- Bid only when confidence ? threshold
- Stop at recommended max bid

### Phase 11: Machine Learning
- Train model on actual win/loss data
- Optimize margin recommendations
- Predict auction competition

### Phase 12: Advanced Analytics
- Portfolio optimization
- Risk-adjusted returns
- Historical performance tracking

---

## ?? Related Documentation

- [PHASE9_COMPLETE.md](./PHASE9_COMPLETE.md) - Full implementation report
- [MARKET_ANALYSIS_FLOW.md](./MARKET_ANALYSIS_FLOW.md) - Analysis workflow
- [AI_PROFIT_PIPELINE.md](./AI_PROFIT_PIPELINE.md) - Technical pipeline

---

**Profit Advisor - Making Data-Driven Auction Bidding Accessible to All**
