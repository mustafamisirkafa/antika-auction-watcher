/**
 * Type definitions for auction-related data structures
 */

export interface AuctionItem {
  id: string
  title: string
  image?: string
  currentPrice: number
  valuation?: number
  confidence?: number
  status: 'active' | 'ended'
  lastBidAt: string
  bidder?: string
  category?: string
}

export interface WebSocketEvent {
  event: string
  timestamp: string
  [key: string]: any
}

export interface BidUpdateEvent extends WebSocketEvent {
  event: 'bid_update'
  item_id: string
  price: number
  bidder: string
}

export interface ValuationUpdateEvent extends WebSocketEvent {
  event: 'valuation_update'
  item_id: string
  valuation: number
  confidence: number
}

export interface AuctionStartEvent extends WebSocketEvent {
  event: 'auction_start'
  item_id: string
  title: string
  image?: string
  startPrice: number
  category?: string
}

export interface AuctionEndEvent extends WebSocketEvent {
  event: 'auction_end'
  item_id: string
  finalPrice: number
  winner?: string
}

export type AuctionWebSocketEvent = 
  | BidUpdateEvent 
  | ValuationUpdateEvent 
  | AuctionStartEvent 
  | AuctionEndEvent

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error'
