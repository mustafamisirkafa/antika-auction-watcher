/**
 * Zustand store for real-time auction state management
 */

import { create } from 'zustand'
import { AuctionItem, WebSocketEvent } from '@/types/auction'

interface AuctionStore {
  // State
  auctions: Record<string, AuctionItem>
  recentlyUpdated: Set<string>
  
  // Actions
  addOrUpdateAuction: (eventData: WebSocketEvent) => void
  clearAuctions: () => void
  getAuction: (id: string) => AuctionItem | undefined
  getActiveAuctions: () => AuctionItem[]
  getEndedAuctions: () => AuctionItem[]
  markAsUpdated: (id: string) => void
  clearUpdatedMark: (id: string) => void
}

export const useAuctionStore = create<AuctionStore>((set, get) => ({
  // Initial state
  auctions: {},
  recentlyUpdated: new Set(),

  // Add or update auction based on WebSocket event
  addOrUpdateAuction: (eventData: WebSocketEvent) => {
    const { event } = eventData

    switch (event) {
      case 'auction_start':
        set((state) => ({
          auctions: {
            ...state.auctions,
            [eventData.item_id]: {
              id: eventData.item_id,
              title: eventData.title || 'Untitled Auction',
              image: eventData.image,
              currentPrice: eventData.startPrice || 0,
              valuation: eventData.valuation,
              confidence: eventData.confidence,
              status: 'active',
              lastBidAt: eventData.timestamp,
              category: eventData.category,
            },
          },
          recentlyUpdated: new Set(state.recentlyUpdated).add(eventData.item_id),
        }))
        
        // Clear updated mark after animation
        setTimeout(() => get().clearUpdatedMark(eventData.item_id), 500)
        break

      case 'bid_update':
        set((state) => {
          const existing = state.auctions[eventData.item_id]
          if (!existing) {
            // Create new auction if doesn't exist
            return {
              auctions: {
                ...state.auctions,
                [eventData.item_id]: {
                  id: eventData.item_id,
                  title: eventData.title || `Item ${eventData.item_id}`,
                  image: eventData.image,
                  currentPrice: eventData.price,
                  status: 'active',
                  lastBidAt: eventData.timestamp,
                  bidder: eventData.bidder,
                },
              },
              recentlyUpdated: new Set(state.recentlyUpdated).add(eventData.item_id),
            }
          }

          return {
            auctions: {
              ...state.auctions,
              [eventData.item_id]: {
                ...existing,
                currentPrice: eventData.price,
                lastBidAt: eventData.timestamp,
                bidder: eventData.bidder,
              },
            },
            recentlyUpdated: new Set(state.recentlyUpdated).add(eventData.item_id),
          }
        })
        
        setTimeout(() => get().clearUpdatedMark(eventData.item_id), 500)
        break

      case 'valuation_update':
        set((state) => {
          const existing = state.auctions[eventData.item_id]
          if (!existing) return state

          return {
            auctions: {
              ...state.auctions,
              [eventData.item_id]: {
                ...existing,
                valuation: eventData.valuation,
                confidence: eventData.confidence,
              },
            },
            recentlyUpdated: new Set(state.recentlyUpdated).add(eventData.item_id),
          }
        })
        
        setTimeout(() => get().clearUpdatedMark(eventData.item_id), 500)
        break

      case 'auction_end':
        set((state) => {
          const existing = state.auctions[eventData.item_id]
          if (!existing) return state

          return {
            auctions: {
              ...state.auctions,
              [eventData.item_id]: {
                ...existing,
                status: 'ended',
                currentPrice: eventData.finalPrice || existing.currentPrice,
                bidder: eventData.winner || existing.bidder,
                lastBidAt: eventData.timestamp,
              },
            },
          }
        })
        break

      default:
        console.warn('[AuctionStore] Unknown event type:', event)
    }
  },

  // Clear all auctions
  clearAuctions: () => {
    set({ auctions: {}, recentlyUpdated: new Set() })
  },

  // Get single auction by ID
  getAuction: (id: string) => {
    return get().auctions[id]
  },

  // Get all active auctions
  getActiveAuctions: () => {
    return Object.values(get().auctions)
      .filter((auction) => auction.status === 'active')
      .sort((a, b) => new Date(b.lastBidAt).getTime() - new Date(a.lastBidAt).getTime())
  },

  // Get all ended auctions
  getEndedAuctions: () => {
    return Object.values(get().auctions)
      .filter((auction) => auction.status === 'ended')
      .sort((a, b) => new Date(b.lastBidAt).getTime() - new Date(a.lastBidAt).getTime())
  },

  // Mark auction as recently updated (for animation)
  markAsUpdated: (id: string) => {
    set((state) => ({
      recentlyUpdated: new Set(state.recentlyUpdated).add(id),
    }))
  },

  // Clear updated mark
  clearUpdatedMark: (id: string) => {
    set((state) => {
      const updated = new Set(state.recentlyUpdated)
      updated.delete(id)
      return { recentlyUpdated: updated }
    })
  },
}))
