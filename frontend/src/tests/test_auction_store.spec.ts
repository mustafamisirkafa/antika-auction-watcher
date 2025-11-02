/**
 * Tests for Zustand auction store
 */

import { useAuctionStore } from '@/store/auctionStore'
import { WebSocketEvent } from '@/types/auction'

describe('AuctionStore', () => {
  beforeEach(() => {
    // Reset store before each test
    useAuctionStore.getState().clearAuctions()
  })

  describe('Initial State', () => {
    test('should have empty auctions initially', () => {
      const { auctions } = useAuctionStore.getState()
      expect(Object.keys(auctions)).toHaveLength(0)
    })

    test('should have empty recentlyUpdated set initially', () => {
      const { recentlyUpdated } = useAuctionStore.getState()
      expect(recentlyUpdated.size).toBe(0)
    })
  })

  describe('auction_start Event', () => {
    test('should add new auction on auction_start', () => {
      const event: WebSocketEvent = {
        event: 'auction_start',
        item_id: 'AUC-1',
        title: 'Vintage Watch',
        startPrice: 1000,
        timestamp: '2025-11-02T10:00:00Z',
        category: 'antiques',
      }

      useAuctionStore.getState().addOrUpdateAuction(event)

      const { auctions } = useAuctionStore.getState()
      expect(auctions['AUC-1']).toBeDefined()
      expect(auctions['AUC-1'].title).toBe('Vintage Watch')
      expect(auctions['AUC-1'].currentPrice).toBe(1000)
      expect(auctions['AUC-1'].status).toBe('active')
    })

    test('should mark auction as recently updated', () => {
      const event: WebSocketEvent = {
        event: 'auction_start',
        item_id: 'AUC-1',
        title: 'Test',
        startPrice: 100,
        timestamp: '2025-11-02T10:00:00Z',
      }

      useAuctionStore.getState().addOrUpdateAuction(event)

      const { recentlyUpdated } = useAuctionStore.getState()
      expect(recentlyUpdated.has('AUC-1')).toBe(true)
    })
  })

  describe('bid_update Event', () => {
    test('should update existing auction on bid_update', () => {
      // First create an auction
      const startEvent: WebSocketEvent = {
        event: 'auction_start',
        item_id: 'AUC-1',
        title: 'Watch',
        startPrice: 1000,
        timestamp: '2025-11-02T10:00:00Z',
      }
      useAuctionStore.getState().addOrUpdateAuction(startEvent)

      // Then update with bid
      const bidEvent: WebSocketEvent = {
        event: 'bid_update',
        item_id: 'AUC-1',
        price: 1200,
        bidder: 'user_42',
        timestamp: '2025-11-02T10:05:00Z',
      }
      useAuctionStore.getState().addOrUpdateAuction(bidEvent)

      const { auctions } = useAuctionStore.getState()
      expect(auctions['AUC-1'].currentPrice).toBe(1200)
      expect(auctions['AUC-1'].bidder).toBe('user_42')
      expect(auctions['AUC-1'].lastBidAt).toBe('2025-11-02T10:05:00Z')
    })

    test('should create auction if not exists on bid_update', () => {
      const bidEvent: WebSocketEvent = {
        event: 'bid_update',
        item_id: 'AUC-NEW',
        price: 500,
        bidder: 'user_1',
        timestamp: '2025-11-02T10:00:00Z',
      }

      useAuctionStore.getState().addOrUpdateAuction(bidEvent)

      const { auctions } = useAuctionStore.getState()
      expect(auctions['AUC-NEW']).toBeDefined()
      expect(auctions['AUC-NEW'].currentPrice).toBe(500)
      expect(auctions['AUC-NEW'].status).toBe('active')
    })
  })

  describe('valuation_update Event', () => {
    test('should update valuation and confidence', () => {
      // Create auction first
      const startEvent: WebSocketEvent = {
        event: 'auction_start',
        item_id: 'AUC-1',
        title: 'Item',
        startPrice: 1000,
        timestamp: '2025-11-02T10:00:00Z',
      }
      useAuctionStore.getState().addOrUpdateAuction(startEvent)

      // Update valuation
      const valuationEvent: WebSocketEvent = {
        event: 'valuation_update',
        item_id: 'AUC-1',
        valuation: 1500,
        confidence: 0.85,
        timestamp: '2025-11-02T10:02:00Z',
      }
      useAuctionStore.getState().addOrUpdateAuction(valuationEvent)

      const { auctions } = useAuctionStore.getState()
      expect(auctions['AUC-1'].valuation).toBe(1500)
      expect(auctions['AUC-1'].confidence).toBe(0.85)
    })

    test('should not create auction if not exists', () => {
      const valuationEvent: WebSocketEvent = {
        event: 'valuation_update',
        item_id: 'NON-EXISTENT',
        valuation: 1500,
        confidence: 0.85,
        timestamp: '2025-11-02T10:00:00Z',
      }

      useAuctionStore.getState().addOrUpdateAuction(valuationEvent)

      const { auctions } = useAuctionStore.getState()
      expect(auctions['NON-EXISTENT']).toBeUndefined()
    })
  })

  describe('auction_end Event', () => {
    test('should mark auction as ended', () => {
      // Create auction
      const startEvent: WebSocketEvent = {
        event: 'auction_start',
        item_id: 'AUC-1',
        title: 'Item',
        startPrice: 1000,
        timestamp: '2025-11-02T10:00:00Z',
      }
      useAuctionStore.getState().addOrUpdateAuction(startEvent)

      // End auction
      const endEvent: WebSocketEvent = {
        event: 'auction_end',
        item_id: 'AUC-1',
        finalPrice: 1800,
        winner: 'user_99',
        timestamp: '2025-11-02T11:00:00Z',
      }
      useAuctionStore.getState().addOrUpdateAuction(endEvent)

      const { auctions } = useAuctionStore.getState()
      expect(auctions['AUC-1'].status).toBe('ended')
      expect(auctions['AUC-1'].currentPrice).toBe(1800)
      expect(auctions['AUC-1'].bidder).toBe('user_99')
    })
  })

  describe('clearAuctions', () => {
    test('should clear all auctions', () => {
      // Add some auctions
      const event1: WebSocketEvent = {
        event: 'auction_start',
        item_id: 'AUC-1',
        title: 'Item 1',
        startPrice: 1000,
        timestamp: '2025-11-02T10:00:00Z',
      }
      const event2: WebSocketEvent = {
        event: 'auction_start',
        item_id: 'AUC-2',
        title: 'Item 2',
        startPrice: 2000,
        timestamp: '2025-11-02T10:01:00Z',
      }

      useAuctionStore.getState().addOrUpdateAuction(event1)
      useAuctionStore.getState().addOrUpdateAuction(event2)

      // Clear
      useAuctionStore.getState().clearAuctions()

      const { auctions, recentlyUpdated } = useAuctionStore.getState()
      expect(Object.keys(auctions)).toHaveLength(0)
      expect(recentlyUpdated.size).toBe(0)
    })
  })

  describe('getAuction', () => {
    test('should get auction by id', () => {
      const event: WebSocketEvent = {
        event: 'auction_start',
        item_id: 'AUC-1',
        title: 'Test Item',
        startPrice: 1000,
        timestamp: '2025-11-02T10:00:00Z',
      }
      useAuctionStore.getState().addOrUpdateAuction(event)

      const auction = useAuctionStore.getState().getAuction('AUC-1')
      expect(auction).toBeDefined()
      expect(auction?.title).toBe('Test Item')
    })

    test('should return undefined for non-existent auction', () => {
      const auction = useAuctionStore.getState().getAuction('NON-EXISTENT')
      expect(auction).toBeUndefined()
    })
  })

  describe('getActiveAuctions', () => {
    test('should return only active auctions', () => {
      const events: WebSocketEvent[] = [
        {
          event: 'auction_start',
          item_id: 'AUC-1',
          title: 'Active 1',
          startPrice: 1000,
          timestamp: '2025-11-02T10:00:00Z',
        },
        {
          event: 'auction_start',
          item_id: 'AUC-2',
          title: 'Active 2',
          startPrice: 2000,
          timestamp: '2025-11-02T10:01:00Z',
        },
        {
          event: 'auction_start',
          item_id: 'AUC-3',
          title: 'Will End',
          startPrice: 3000,
          timestamp: '2025-11-02T10:02:00Z',
        },
      ]

      events.forEach(e => useAuctionStore.getState().addOrUpdateAuction(e))

      // End one auction
      useAuctionStore.getState().addOrUpdateAuction({
        event: 'auction_end',
        item_id: 'AUC-3',
        finalPrice: 3500,
        timestamp: '2025-11-02T11:00:00Z',
      })

      const activeAuctions = useAuctionStore.getState().getActiveAuctions()
      expect(activeAuctions).toHaveLength(2)
      expect(activeAuctions.every(a => a.status === 'active')).toBe(true)
    })

    test('should sort by lastBidAt descending', () => {
      const events: WebSocketEvent[] = [
        {
          event: 'auction_start',
          item_id: 'AUC-1',
          title: 'Older',
          startPrice: 1000,
          timestamp: '2025-11-02T10:00:00Z',
        },
        {
          event: 'auction_start',
          item_id: 'AUC-2',
          title: 'Newer',
          startPrice: 2000,
          timestamp: '2025-11-02T10:05:00Z',
        },
      ]

      events.forEach(e => useAuctionStore.getState().addOrUpdateAuction(e))

      const activeAuctions = useAuctionStore.getState().getActiveAuctions()
      expect(activeAuctions[0].id).toBe('AUC-2') // Newer first
      expect(activeAuctions[1].id).toBe('AUC-1')
    })
  })

  describe('getEndedAuctions', () => {
    test('should return only ended auctions', () => {
      const events: WebSocketEvent[] = [
        {
          event: 'auction_start',
          item_id: 'AUC-1',
          title: 'Active',
          startPrice: 1000,
          timestamp: '2025-11-02T10:00:00Z',
        },
        {
          event: 'auction_start',
          item_id: 'AUC-2',
          title: 'Ended 1',
          startPrice: 2000,
          timestamp: '2025-11-02T09:00:00Z',
        },
        {
          event: 'auction_start',
          item_id: 'AUC-3',
          title: 'Ended 2',
          startPrice: 3000,
          timestamp: '2025-11-02T09:30:00Z',
        },
      ]

      events.forEach(e => useAuctionStore.getState().addOrUpdateAuction(e))

      // End two auctions
      useAuctionStore.getState().addOrUpdateAuction({
        event: 'auction_end',
        item_id: 'AUC-2',
        finalPrice: 2500,
        timestamp: '2025-11-02T10:00:00Z',
      })
      useAuctionStore.getState().addOrUpdateAuction({
        event: 'auction_end',
        item_id: 'AUC-3',
        finalPrice: 3500,
        timestamp: '2025-11-02T10:30:00Z',
      })

      const endedAuctions = useAuctionStore.getState().getEndedAuctions()
      expect(endedAuctions).toHaveLength(2)
      expect(endedAuctions.every(a => a.status === 'ended')).toBe(true)
    })
  })

  describe('markAsUpdated and clearUpdatedMark', () => {
    test('should mark and clear updated status', () => {
      const { markAsUpdated, clearUpdatedMark, recentlyUpdated } = useAuctionStore.getState()

      markAsUpdated('AUC-1')
      expect(recentlyUpdated.has('AUC-1')).toBe(true)

      clearUpdatedMark('AUC-1')
      const { recentlyUpdated: updated } = useAuctionStore.getState()
      expect(updated.has('AUC-1')).toBe(false)
    })
  })

  describe('Unknown Event Type', () => {
    test('should handle unknown event gracefully', () => {
      const consoleSpy = jest.spyOn(console, 'warn').mockImplementation()

      const event: WebSocketEvent = {
        event: 'unknown_event',
        timestamp: '2025-11-02T10:00:00Z',
      }

      useAuctionStore.getState().addOrUpdateAuction(event)

      expect(consoleSpy).toHaveBeenCalledWith(
        expect.stringContaining('[AuctionStore] Unknown event type'),
        'unknown_event'
      )

      consoleSpy.mockRestore()
    })
  })
})
