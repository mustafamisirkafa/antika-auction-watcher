/**
 * Auction Feed component - displays live auction cards in a grid
 */

'use client'

import { useEffect, useState } from 'react'
import { AuctionItem } from '@/types/auction'
import { useAuctionStore } from '@/store/auctionStore'
import { useFeedback } from '@/store/userBehavior'
import AdvisorPanel from './AdvisorPanel'

interface AuctionCardProps {
  auction: AuctionItem
  isRecentlyUpdated: boolean
}

function AuctionCard({ auction, isRecentlyUpdated }: AuctionCardProps) {
  const [showAnimation, setShowAnimation] = useState(false)
  const [showAdvisor, setShowAdvisor] = useState(true)
  const { addFeedback } = useFeedback()

  useEffect(() => {
    if (isRecentlyUpdated) {
      setShowAnimation(true)
      const timer = setTimeout(() => setShowAnimation(false), 500)
      return () => clearTimeout(timer)
    }
  }, [isRecentlyUpdated])
  
  const handleAdvisorFeedback = (feedbackType: string) => {
    addFeedback({
      itemId: auction.id,
      recommendationId: `rec_${auction.id}_${Date.now()}`,
      feedbackType: feedbackType as 'helpful' | 'not_helpful' | 'accurate' | 'inaccurate'
    })
  }

  const confidenceColor = (confidence?: number) => {
    if (!confidence) return 'bg-gray-300'
    if (confidence >= 0.8) return 'bg-green-500'
    if (confidence >= 0.6) return 'bg-yellow-500'
    return 'bg-red-500'
  }

  const confidenceText = (confidence?: number) => {
    if (!confidence) return 'Unknown'
    return `${(confidence * 100).toFixed(0)}%`
  }

  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('tr-TR', {
      style: 'currency',
      currency: 'TRY',
    }).format(price)
  }

  const formatTime = (timestamp: string) => {
    try {
      const date = new Date(timestamp)
      return date.toLocaleTimeString('tr-TR', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      })
    } catch {
      return timestamp
    }
  }

  const priceChange = auction.valuation && auction.currentPrice
    ? ((auction.currentPrice / auction.valuation) * 100)
    : null

  return (
    <div
      className={`
        bg-white rounded-lg shadow-md overflow-hidden border-2 transition-all duration-300
        ${auction.status === 'active' ? 'border-green-400' : 'border-gray-300'}
        ${showAnimation ? 'animate-bid-update' : ''}
        hover:shadow-lg hover:scale-105
      `}
    >
      {/* Image */}
      <div className="relative h-48 bg-gradient-to-br from-gray-100 to-gray-200">
        {auction.image ? (
          <img
            src={auction.image}
            alt={auction.title}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="flex items-center justify-center h-full">
            <svg
              className="w-20 h-20 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
              />
            </svg>
          </div>
        )}
        
        {/* Status Badge */}
        <div className="absolute top-2 right-2">
          <span
            className={`
              px-2 py-1 text-xs font-semibold rounded-full
              ${auction.status === 'active'
                ? 'bg-green-500 text-white'
                : 'bg-gray-500 text-white'
              }
            `}
          >
            {auction.status === 'active' ? 'LIVE' : 'ENDED'}
          </span>
        </div>

        {/* Category Badge */}
        {auction.category && (
          <div className="absolute bottom-2 left-2">
            <span className="px-2 py-1 text-xs font-medium bg-black bg-opacity-60 text-white rounded">
              {auction.category}
            </span>
          </div>
        )}
      </div>

      {/* Content */}
      <div className="p-4">
        {/* Title */}
        <h3 className="text-lg font-semibold text-gray-800 mb-2 truncate">
          {auction.title}
        </h3>

        {/* Current Price */}
        <div className="mb-3">
          <div className="text-sm text-gray-600 mb-1">Current Bid</div>
          <div className={`text-2xl font-bold ${showAnimation ? 'text-yellow-600' : 'text-gray-900'}`}>
            {formatPrice(auction.currentPrice)}
          </div>
          {auction.bidder && (
            <div className="text-xs text-gray-500 mt-1">
              Bidder: {auction.bidder}
            </div>
          )}
        </div>

        {/* AI Valuation */}
        {auction.valuation && (
          <div className="mb-3 p-2 bg-blue-50 rounded">
            <div className="flex justify-between items-center mb-1">
              <span className="text-sm font-medium text-blue-900">AI Valuation</span>
              <span className="text-sm font-bold text-blue-700">
                {formatPrice(auction.valuation)}
              </span>
            </div>
            
            {/* Confidence Bar */}
            <div className="mt-2">
              <div className="flex justify-between text-xs text-gray-600 mb-1">
                <span>Confidence</span>
                <span className="font-semibold">{confidenceText(auction.confidence)}</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className={`h-2 rounded-full transition-all duration-300 ${confidenceColor(auction.confidence)}`}
                  style={{ width: `${(auction.confidence || 0) * 100}%` }}
                />
              </div>
            </div>

            {/* Price vs Valuation */}
            {priceChange !== null && (
              <div className="mt-2 text-xs">
                {priceChange < 80 ? (
                  <span className="text-green-600 font-semibold">
                    ?? {(100 - priceChange).toFixed(0)}% below valuation
                  </span>
                ) : priceChange > 100 ? (
                  <span className="text-red-600 font-semibold">
                    ?? {(priceChange - 100).toFixed(0)}% above valuation
                  </span>
                ) : (
                  <span className="text-yellow-600 font-semibold">
                    ? {priceChange.toFixed(0)}% of valuation
                  </span>
                )}
              </div>
            )}
          </div>
        )}

        {/* Bidder */}
        {auction.bidder && (
          <div className="mt-2 text-sm text-gray-600">
            <span className="font-medium">Bidder:</span> {auction.bidder}
          </div>
        )}
        
        {/* AI Advisor Panel */}
        {auction.status === 'active' && showAdvisor && (
          <div className="mt-4">
            <AdvisorPanel 
              itemId={auction.id}
              compact={true}
              onFeedback={handleAdvisorFeedback}
            />
          </div>
        )}

        {/* Last Update Time */}
        <div className="text-xs text-gray-500 border-t pt-2">
          Last update: {formatTime(auction.lastBidAt)}
        </div>
      </div>
    </div>
  )
}

interface AuctionFeedProps {
  showEnded?: boolean
}

export default function AuctionFeed({ showEnded = false }: AuctionFeedProps) {
  const { getActiveAuctions, getEndedAuctions, recentlyUpdated } = useAuctionStore()
  
  const activeAuctions = getActiveAuctions()
  const endedAuctions = getEndedAuctions()
  const displayAuctions = showEnded ? endedAuctions : activeAuctions

  if (displayAuctions.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16">
        <div className="text-gray-400 mb-4">
          <svg
            className="w-24 h-24"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
            />
          </svg>
        </div>
        <h3 className="text-xl font-semibold text-gray-600 mb-2">
          {showEnded ? 'No Ended Auctions Yet' : 'No Live Auctions'}
        </h3>
        <p className="text-gray-500 text-center max-w-md">
          {showEnded
            ? 'Completed auctions will appear here once they end.'
            : 'Waiting for live auction data. Make sure you\'re connected to the WebSocket server.'}
        </p>
      </div>
    )
  }

  return (
    <div>
      <div className="mb-4 flex justify-between items-center">
        <h2 className="text-2xl font-semibold text-gray-800">
          {showEnded ? 'Ended Auctions' : 'Live Auctions'}
          <span className="ml-2 text-sm font-normal text-gray-500">
            ({displayAuctions.length})
          </span>
        </h2>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {displayAuctions.map((auction) => (
          <AuctionCard
            key={auction.id}
            auction={auction}
            isRecentlyUpdated={recentlyUpdated.has(auction.id)}
          />
        ))}
      </div>
    </div>
  )
}
