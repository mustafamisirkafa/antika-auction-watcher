# Antika Auction Watcher - Frontend

Real-time auction monitoring dashboard with AI-powered valuation, built with Next.js, TypeScript, and WebSocket.

## ?? Phase 3 / Week 2 Implementation

This frontend application provides:
- **Live Auction Feed**: Real-time updates via WebSocket
- **AI Valuation Display**: Confidence scores and price recommendations
- **Bid Tracking**: Monitor current bids and bidder information
- **Responsive UI**: Built with Tailwind CSS for all screen sizes
- **State Management**: Zustand for reactive real-time data

## ?? Quick Start

### Prerequisites

- Node.js 18+ and npm
- Backend server running on `http://127.0.0.1:8000`

### Installation

```bash
# Install dependencies
npm install

# Copy environment file
cp .env.example .env

# Start development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## ?? Project Structure

```
frontend/
??? src/
?   ??? components/
?   ?   ??? AuctionFeed.tsx       # Main auction feed component
?   ??? lib/
?   ?   ??? websocket.ts          # WebSocket client with auto-reconnect
?   ??? pages/
?   ?   ??? _app.tsx              # Next.js app wrapper
?   ?   ??? _document.tsx         # HTML document
?   ?   ??? index.tsx             # Landing page (redirects to dashboard)
?   ?   ??? dashboard.tsx         # Main dashboard page
?   ??? store/
?   ?   ??? auctionStore.ts       # Zustand state management
?   ??? styles/
?   ?   ??? globals.css           # Global styles & Tailwind
?   ??? tests/
?   ?   ??? test_websocket_feed.spec.ts       # WebSocket tests
?   ?   ??? test_auction_feed_render.spec.tsx # Component tests
?   ?   ??? test_auction_store.spec.ts        # Store tests
?   ??? types/
?       ??? auction.ts            # TypeScript type definitions
??? package.json
??? tsconfig.json
??? tailwind.config.js
??? jest.config.js
??? playwright.config.ts
??? README.md
```

## ?? WebSocket Integration

### Connection

The application connects to: `ws://127.0.0.1:8000/api/ws/auctions`

### Supported Events

1. **auction_start** - New auction begins
```json
{
  "event": "auction_start",
  "item_id": "AUC-231",
  "title": "Vintage Watch",
  "startPrice": 1000,
  "category": "antiques",
  "image": "https://...",
  "timestamp": "2025-11-02T19:12:45Z"
}
```

2. **bid_update** - New bid placed
```json
{
  "event": "bid_update",
  "item_id": "AUC-231",
  "price": 1280,
  "bidder": "user_42",
  "timestamp": "2025-11-02T19:12:45Z"
}
```

3. **valuation_update** - AI valuation calculated
```json
{
  "event": "valuation_update",
  "item_id": "AUC-231",
  "valuation": 1500,
  "confidence": 0.85,
  "timestamp": "2025-11-02T19:12:45Z"
}
```

4. **auction_end** - Auction completes
```json
{
  "event": "auction_end",
  "item_id": "AUC-231",
  "finalPrice": 1800,
  "winner": "user_99",
  "timestamp": "2025-11-02T20:00:00Z"
}
```

### Auto-Reconnect

The WebSocket client automatically reconnects on disconnect:
- **Exponential backoff**: 3s, 6s, 15s, 30s, 75s...
- **Max attempts**: 10
- **Heartbeat**: Ping every 30 seconds to keep connection alive

## ?? UI Features

### Dashboard

- **Connection Status**: Visual indicator (? Connected / ?? Disconnected)
- **Live Stats**: Active and ended auction counts
- **Tab Navigation**: Switch between active and ended auctions
- **Auto-refresh**: Real-time updates without page reload

### Auction Cards

Each card displays:
- Item image or placeholder
- Title and category badge
- Current bid with animation on update
- Status badge (LIVE / ENDED)
- AI valuation and confidence bar
- Price vs valuation indicator
- Last update timestamp
- Bidder information

### Animations

- **Bid Update**: Yellow flash animation on price change
- **Confidence Bar**: Smooth width transition
- **Hover Effects**: Scale and shadow on card hover

## ?? Testing

### Unit Tests (Jest)

```bash
# Run all tests
npm test

# Run with coverage
npm run test:coverage

# Watch mode
npm run test:watch
```

**Coverage Target**: 70%+

**Test Files**:
- `test_websocket_feed.spec.ts` - WebSocket client (connection, reconnect, events)
- `test_auction_store.spec.ts` - Zustand store (state updates, filtering)
- `test_auction_feed_render.spec.tsx` - Component rendering (display, animations)

### E2E Tests (Playwright)

```bash
# Run e2e tests
npm run test:e2e

# Run with UI
npx playwright test --ui
```

## ?? Configuration

### Environment Variables

Create `.env` file:

```env
NEXT_PUBLIC_WS_URL=ws://127.0.0.1:8000/api/ws/auctions
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000/api/v1
```

### Tailwind Theme

Customized in `tailwind.config.js`:
- Primary color palette (blue)
- Custom animations (fade-in, bid-update, pulse-soft)
- Responsive breakpoints

## ?? Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start development server (port 3000) |
| `npm run build` | Build for production |
| `npm run start` | Start production server |
| `npm run lint` | Run ESLint |
| `npm test` | Run Jest unit tests |
| `npm run test:coverage` | Run tests with coverage report |
| `npm run test:e2e` | Run Playwright e2e tests |

## ??? Architecture

### State Flow

```
WebSocket Server
    ?
WebSocket Client (lib/websocket.ts)
    ?
Event Handlers
    ?
Zustand Store (store/auctionStore.ts)
    ?
React Components (components/AuctionFeed.tsx)
    ?
UI Updates (with animations)
```

### Component Hierarchy

```
Dashboard (pages/dashboard.tsx)
  ??? Header (connection status, tabs)
  ??? Connection Warning (if disconnected)
  ??? AuctionFeed (components/AuctionFeed.tsx)
      ??? AuctionCard ? N
          ??? Image/Placeholder
          ??? Status Badge
          ??? Title & Category
          ??? Current Price
          ??? AI Valuation Section
          ?   ??? Valuation Amount
          ?   ??? Confidence Bar
          ?   ??? Price vs Valuation
          ??? Last Update Time
```

## ?? Success Criteria

? **WebSocket auto-reconnects on drop**  
? **New bids instantly update UI**  
? **Confidence/valuation visually reflect AI model output**  
? **All UI updates reactive without reload**  
? **70%+ Jest/Playwright coverage achieved**

## ?? Deployment

### Build for Production

```bash
npm run build
npm run start
```

### Docker (Optional)

```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
```

## ?? Troubleshooting

### WebSocket Connection Failed

1. Ensure backend is running: `http://127.0.0.1:8000/health`
2. Check WebSocket endpoint: `ws://127.0.0.1:8000/api/ws/auctions`
3. Verify CORS settings in backend
4. Check browser console for errors

### No Auctions Appearing

1. Verify WebSocket connection status (top-right indicator)
2. Check backend is sending events
3. Open browser DevTools ? Network ? WS tab
4. Verify event format matches specifications

### Build Errors

```bash
# Clear Next.js cache
rm -rf .next

# Clear node modules
rm -rf node_modules
npm install

# Rebuild
npm run build
```

## ?? Technologies

- **Next.js 14** - React framework
- **TypeScript** - Type safety
- **Tailwind CSS** - Styling
- **Zustand** - State management
- **WebSocket API** - Real-time communication
- **Jest** - Unit testing
- **Playwright** - E2E testing
- **React Testing Library** - Component testing

## ?? Contributing

1. Follow TypeScript strict mode
2. Write tests for new features (70%+ coverage)
3. Use Tailwind for styling (no inline styles)
4. Follow React best practices (hooks, functional components)
5. Test WebSocket reconnection scenarios

## ?? License

MIT License - See LICENSE file for details

---

**Built for Antika Auction Watcher - Phase 3 / Week 2**  
Real-time AI-powered auction monitoring
