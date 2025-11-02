# ?? Quick Start - Phase 3 Frontend

Get the Antika Auction Watcher frontend up and running in 5 minutes.

## Prerequisites

- ? Node.js 18+ installed
- ? npm or yarn
- ? Backend running on `http://127.0.0.1:8000` (Phase 1 + 2)

## Installation

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Copy environment variables
cp .env.example .env

# Done! Ready to run
```

## Running the Application

### Development Mode

```bash
npm run dev
```

Then open: **http://localhost:3000**

You should see:
- Dashboard with "Disconnected ??" status (if backend WebSocket not running)
- Empty auction feed waiting for data
- Beautiful UI with responsive layout

### With Backend Running

1. **Start Backend (Terminal 1):**
```bash
cd backend
make docker-up    # Start PostgreSQL + Redis
make dev          # Start FastAPI server
```

2. **Start Frontend (Terminal 2):**
```bash
cd frontend
npm run dev
```

3. **Open Browser:**
   - Frontend: http://localhost:3000
   - Backend: http://localhost:8000

You should see "Connected ?" status in top-right corner.

## Testing

### Run All Tests

```bash
npm test
```

**Expected Output:**
```
PASS  src/tests/test_websocket_feed.spec.ts (30+ tests)
PASS  src/tests/test_auction_store.spec.ts (20+ tests)
PASS  src/tests/test_auction_feed_render.spec.tsx (25+ tests)

Test Suites: 3 passed, 3 total
Tests:       75+ passed, 75+ total
Coverage:    70%+ overall
```

### Run with Coverage

```bash
npm run test:coverage
```

Open `coverage/index.html` in browser to see detailed coverage report.

### Run E2E Tests

```bash
npm run test:e2e
```

## Simulating WebSocket Events

### Option 1: Use wscat (Manual Testing)

```bash
# Install wscat
npm install -g wscat

# Connect to backend
wscat -c ws://127.0.0.1:8000/api/ws/auctions

# Send events (paste these in wscat):
```

**Auction Start:**
```json
{"event":"auction_start","item_id":"AUC-001","title":"Vintage Watch","startPrice":1000,"category":"watches","timestamp":"2025-11-02T20:00:00Z"}
```

**Bid Update:**
```json
{"event":"bid_update","item_id":"AUC-001","price":1200,"bidder":"user_42","timestamp":"2025-11-02T20:01:00Z"}
```

**Valuation Update:**
```json
{"event":"valuation_update","item_id":"AUC-001","valuation":1500,"confidence":0.85,"timestamp":"2025-11-02T20:02:00Z"}
```

**Auction End:**
```json
{"event":"auction_end","item_id":"AUC-001","finalPrice":1800,"winner":"user_99","timestamp":"2025-11-02T20:30:00Z"}
```

### Option 2: Mock WebSocket Server (for testing)

Create `mock-server.js`:
```javascript
const WebSocket = require('ws');
const wss = new WebSocket.Server({ port: 8000, path: '/api/ws/auctions' });

wss.on('connection', (ws) => {
  console.log('Client connected');
  
  // Send mock auction start after 1s
  setTimeout(() => {
    ws.send(JSON.stringify({
      event: 'auction_start',
      item_id: 'AUC-001',
      title: 'Antique Vase',
      startPrice: 500,
      category: 'antiques',
      timestamp: new Date().toISOString()
    }));
  }, 1000);
  
  // Send bid updates every 3s
  let price = 500;
  const interval = setInterval(() => {
    price += 50;
    ws.send(JSON.stringify({
      event: 'bid_update',
      item_id: 'AUC-001',
      price: price,
      bidder: `user_${Math.floor(Math.random() * 100)}`,
      timestamp: new Date().toISOString()
    }));
  }, 3000);
  
  ws.on('close', () => {
    clearInterval(interval);
    console.log('Client disconnected');
  });
});

console.log('Mock WebSocket server running on ws://localhost:8000/api/ws/auctions');
```

Run it:
```bash
npm install ws
node mock-server.js
```

## Project Structure

```
frontend/
??? src/
?   ??? components/
?   ?   ??? AuctionFeed.tsx       # Main feed component
?   ??? lib/
?   ?   ??? websocket.ts          # WebSocket client
?   ??? pages/
?   ?   ??? dashboard.tsx         # Main dashboard page
?   ??? store/
?   ?   ??? auctionStore.ts       # Zustand state
?   ??? tests/
?   ?   ??? *.spec.ts(x)          # Test files
?   ??? types/
?       ??? auction.ts            # TypeScript types
??? public/                        # Static assets
??? package.json
??? README.md
```

## Common Commands

| Command | Description |
|---------|-------------|
| `npm run dev` | Start development server |
| `npm test` | Run Jest tests |
| `npm run test:coverage` | Run tests with coverage |
| `npm run test:watch` | Run tests in watch mode |
| `npm run build` | Build for production |
| `npm run start` | Start production server |
| `npm run lint` | Run ESLint |

## Troubleshooting

### WebSocket Won't Connect

**Problem:** Dashboard shows "Disconnected ??"

**Solutions:**
1. Check backend is running: `curl http://127.0.0.1:8000/health`
2. Verify WebSocket endpoint: `wscat -c ws://127.0.0.1:8000/api/ws/auctions`
3. Check `.env` file has correct URL:
   ```
   NEXT_PUBLIC_WS_URL=ws://127.0.0.1:8000/api/ws/auctions
   ```
4. Check browser console for errors (F12)

### No Auctions Showing

**Problem:** Connected but no auction cards

**Solutions:**
1. Backend needs to send WebSocket events
2. Check browser DevTools ? Network ? WS tab
3. Use mock server (see above) or wscat to send test events
4. Verify event format matches specification

### Tests Failing

**Problem:** `npm test` shows errors

**Solutions:**
```bash
# Clear cache
rm -rf node_modules .next
npm install

# Update snapshots
npm test -- -u

# Run specific test
npm test -- test_websocket_feed
```

### Port 3000 Already in Use

**Problem:** `Error: Port 3000 is already in use`

**Solutions:**
```bash
# Option 1: Kill process on port 3000
lsof -ti:3000 | xargs kill -9

# Option 2: Use different port
PORT=3001 npm run dev
```

### TypeScript Errors

**Problem:** Type errors in IDE

**Solutions:**
```bash
# Restart TypeScript server in VSCode
Cmd+Shift+P ? "TypeScript: Restart TS Server"

# Or rebuild
npm run build
```

## Environment Variables

Create `.env` file:

```env
# Required
NEXT_PUBLIC_WS_URL=ws://127.0.0.1:8000/api/ws/auctions

# Optional (for future use)
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000/api/v1
```

## Next Steps

1. ? Frontend running locally
2. ? Tests passing (70%+ coverage)
3. ? Connected to backend WebSocket
4. ? Seeing live auction updates

**Ready for Phase 4:**
- User authentication
- Bid placement
- User settings
- Historical data

## Getting Help

- **Documentation:** See `frontend/README.md`
- **Implementation Details:** See `PHASE3_WEEK2_COMPLETE.md`
- **Backend Setup:** See `backend/README.md` or `QUICKSTART.md`
- **Issues:** Check browser console and backend logs

---

**Enjoy the live auction feed! ??**
