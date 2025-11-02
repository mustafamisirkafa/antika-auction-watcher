# ?? Quick Start - Phase 3 Week 3 (Learning & Metrics)

Get the Learning Insights and Metrics panels running in 5 minutes.

## Prerequisites

- ? Phase 3 Week 2 frontend already running (see QUICKSTART_PHASE3.md)
- ? Backend with admin API endpoints running
- ? Node.js 18+ and npm

## Installation

```bash
# Navigate to frontend (if not already there)
cd frontend

# Install new dependencies (recharts + swr)
npm install

# Already have .env configured from Week 2
# No additional environment variables needed
```

## Running

```bash
# Start development server
npm run dev

# Open http://localhost:3000
```

## Using the New Features

### 1. Access Learning Insights

1. Open dashboard: http://localhost:3000/dashboard
2. Click the **?? Learning Insights** tab
3. You should see:
   - Overall accuracy meter
   - Learning efficiency badge
   - Category performance chart
   - Confidence trend line

**Note:** Data auto-refreshes every 60 seconds.

### 2. Access System Metrics

1. Click the **?? Metrics** tab
2. You should see:
   - System uptime
   - Requests per second
   - Queue size
   - Cache hit ratio
   - Response time distribution

**Color indicators:**
- ?? Green: Excellent
- ?? Blue: Good
- ?? Yellow: Warning
- ?? Red: Critical

### 3. Switch Between Tabs

```
[?? Live Feed] | [?? Learning Insights] | [?? Metrics]
```

**Important:** WebSocket connection stays active when switching tabs!

## Testing Backend Integration

### Option 1: Use Real Backend

Ensure backend is running:
```bash
cd ../backend
make dev
```

Backend must have these endpoints:
- `GET /api/v1/admin/learning/metrics` - Learning data
- `GET /api/v1/admin/metrics/dashboard` - System metrics

### Option 2: Mock API Responses

Create `mock-api-server.js`:
```javascript
const http = require('http');

const server = http.createServer((req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Content-Type', 'application/json');

  if (req.url.includes('/learning/metrics')) {
    res.end(JSON.stringify({
      overall_accuracy: 85.2,
      learning_efficiency: 0.87,
      confidence_trend: [0.70, 0.75, 0.82, 0.87],
      category_accuracy: {
        ceramics: 82,
        coins: 88,
        paintings: 93,
        furniture: 76
      },
      last_training: new Date().toISOString()
    }));
  } else if (req.url.includes('/metrics/dashboard')) {
    res.end(JSON.stringify({
      uptime: '3d 8h 15m',
      redis_hit_ratio: 0.94,
      requests_per_second: 127,
      response_time_ms: {
        p50: 95,
        p90: 145,
        p99: 210
      },
      queue_pending: 8
    }));
  } else {
    res.statusCode = 404;
    res.end('Not found');
  }
});

server.listen(8000, () => {
  console.log('Mock API server on http://localhost:8000');
});
```

Run it:
```bash
node mock-api-server.js
```

Update `.env`:
```env
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000/api/v1
```

## Testing

### Run All Tests (Including New Ones)

```bash
npm test
```

**Should show:**
```
PASS  test_learning_insights.spec.tsx (60+ tests)
PASS  test_metrics_panel.spec.tsx (70+ tests)
PASS  test_dashboard_tabs.spec.tsx (50+ tests)
... (previous tests)

Tests: 255+ passed, 255+ total
Coverage: 81%+ overall
```

### Run Specific Test Suite

```bash
# Learning Insights tests
npm test test_learning_insights

# Metrics Panel tests
npm test test_metrics_panel

# Dashboard tabs tests
npm test test_dashboard_tabs
```

### Check Coverage

```bash
npm run test:coverage
```

## Troubleshooting

### API Connection Errors

**Problem:** Red error banner showing "Failed to Load Learning Metrics"

**Solutions:**
1. Check backend is running: `curl http://127.0.0.1:8000/api/v1/admin/learning/metrics`
2. Check CORS is enabled in backend
3. Verify `.env` has correct API URL
4. Check browser console for detailed errors

### Charts Not Rendering

**Problem:** Charts show empty or loading forever

**Solutions:**
1. Check API returns valid data format
2. Verify data has expected fields
3. Check browser console for Recharts errors
4. Try refreshing the page

### Tabs Not Switching

**Problem:** Clicking tabs doesn't change content

**Solutions:**
1. Check browser console for errors
2. Clear browser cache
3. Rebuild: `rm -rf .next && npm run dev`

### Tests Failing

**Problem:** New tests show errors

**Solutions:**
```bash
# Clear jest cache
npm test -- --clearCache

# Update snapshots
npm test -- -u

# Run with verbose output
npm test -- --verbose
```

## Feature Checklist

After setup, verify these work:

### Learning Insights Tab
- [ ] Overall accuracy displays (e.g., 82.5%)
- [ ] Learning efficiency shows colored badge
- [ ] Category chart renders with bars
- [ ] Confidence trend shows line chart
- [ ] "Auto-refresh: 60s" indicator visible
- [ ] Data updates every 60 seconds

### Metrics Tab
- [ ] Uptime displays (e.g., "5d 12h 42m")
- [ ] RPS shows with color (green/yellow/red)
- [ ] Queue count displays
- [ ] Cache hit ratio shows percentage
- [ ] Response time chart renders (p50/p90/p99)
- [ ] Cache radial chart displays
- [ ] Performance thresholds legend visible

### Tab Navigation
- [ ] All three tabs clickable
- [ ] Content switches when clicking tabs
- [ ] WebSocket stays connected (check top-right status)
- [ ] Connection status visible on all tabs
- [ ] No errors in console

### Performance
- [ ] Tab switches are instant (no lag)
- [ ] Charts render smoothly
- [ ] No memory leaks (check DevTools)
- [ ] Mobile responsive

## Next Steps

1. ? Learning & Metrics panels working
2. ? Tests passing (255+ tests, 81%+ coverage)
3. ? Connected to backend API
4. ? Auto-refresh functioning

**Ready for Phase 3 Week 4:**
- User authentication UI
- Bid placement interface
- User settings management
- Historical data views

## API Endpoints Reference

### Learning Metrics
```
GET /api/v1/admin/learning/metrics

Response:
{
  "overall_accuracy": 82.5,
  "learning_efficiency": 0.89,
  "confidence_trend": [0.72, 0.75, 0.81, 0.84],
  "category_accuracy": {
    "ceramics": 79,
    "coins": 85
  },
  "last_training": "2025-11-02T18:45:00Z"
}
```

### System Metrics
```
GET /api/v1/admin/metrics/dashboard

Response:
{
  "uptime": "5d 12h 42m",
  "redis_hit_ratio": 0.92,
  "requests_per_second": 135,
  "response_time_ms": {
    "p50": 110,
    "p90": 160,
    "p99": 230
  },
  "queue_pending": 14
}
```

## Getting Help

- **Frontend Docs:** See `frontend/README.md`
- **Full Report:** See `PHASE3_WEEK3_COMPLETE.md`
- **Backend Setup:** See `backend/README.md`
- **Issues:** Check browser console and backend logs

---

**Enjoy the learning & metrics visualization! ??**
