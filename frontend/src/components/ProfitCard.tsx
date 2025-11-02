/**
 * Profit Card Component
 * Displays profit estimate for an upcoming auction item
 */
import React from 'react';

interface ProfitEstimate {
  id: number;
  estimated_value: float;
  recommended_max_bid: number;
  profit_margin: number;
  profit_amount: number;
  confidence: number;
  risk_level: 'low' | 'medium' | 'high';
  market_volatility: number;
  liquidity_avg: number;
}

interface AuctionItem {
  id: number;
  lot_id: string;
  title: string;
  category: string;
  image_url?: string;
  starting_price: number;
  auction_date: string;
  source: string;
}

interface ProfitCardProps {
  estimate: ProfitEstimate;
  auctionItem: AuctionItem;
  onAutoBid?: (maxBid: number) => void;
  canAutoBid?: boolean;
}

export default function ProfitCard({
  estimate,
  auctionItem,
  onAutoBid,
  canAutoBid = false,
}: ProfitCardProps) {
  // Confidence color
  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'text-green-600 bg-green-100';
    if (confidence >= 0.6) return 'text-yellow-600 bg-yellow-100';
    return 'text-red-600 bg-red-100';
  };

  // Risk level color
  const getRiskColor = (risk: string) => {
    if (risk === 'low') return 'text-green-600';
    if (risk === 'medium') return 'text-yellow-600';
    return 'text-red-600';
  };

  // Profit bar color
  const getProfitBarColor = (margin: number) => {
    if (margin >= 0.20) return 'bg-green-500';
    if (margin >= 0.10) return 'bg-yellow-500';
    return 'bg-orange-500';
  };

  // Format currency
  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('tr-TR', {
      style: 'currency',
      currency: 'TRY',
    }).format(amount);
  };

  // Format percentage
  const formatPercent = (value: number) => {
    return `${(value * 100).toFixed(1)}%`;
  };

  // Format date
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('tr-TR', {
      day: 'numeric',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="bg-white rounded-lg shadow-md hover:shadow-lg transition-shadow border border-gray-200 overflow-hidden">
      {/* Header with image */}
      <div className="flex">
        {/* Image */}
        {auctionItem.image_url ? (
          <div className="w-32 h-32 flex-shrink-0">
            <img
              src={auctionItem.image_url}
              alt={auctionItem.title}
              className="w-full h-full object-cover"
            />
          </div>
        ) : (
          <div className="w-32 h-32 flex-shrink-0 bg-gray-200 flex items-center justify-center">
            <svg
              className="w-12 h-12 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
              />
            </svg>
          </div>
        )}

        {/* Content */}
        <div className="flex-1 p-4">
          {/* Title and category */}
          <div className="mb-2">
            <h3 className="text-lg font-semibold text-gray-900 line-clamp-2">
              {auctionItem.title}
            </h3>
            <div className="flex items-center gap-2 mt-1">
              <span className="text-xs px-2 py-1 bg-blue-100 text-blue-700 rounded">
                {auctionItem.category}
              </span>
              <span className="text-xs text-gray-500">{auctionItem.lot_id}</span>
            </div>
          </div>

          {/* Auction details */}
          <div className="text-sm text-gray-600 space-y-1">
            <div className="flex items-center">
              <span className="font-medium mr-2">Auction:</span>
              <span>{formatDate(auctionItem.auction_date)}</span>
            </div>
            <div className="flex items-center">
              <span className="font-medium mr-2">Source:</span>
              <span>{auctionItem.source}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Profit analysis */}
      <div className="p-4 border-t border-gray-200 bg-gray-50">
        {/* Price comparison */}
        <div className="grid grid-cols-3 gap-4 mb-4">
          <div>
            <div className="text-xs text-gray-600 mb-1">Starting Price</div>
            <div className="text-lg font-semibold text-gray-900">
              {formatCurrency(auctionItem.starting_price)}
            </div>
          </div>
          <div>
            <div className="text-xs text-gray-600 mb-1">AI Max Bid</div>
            <div className="text-lg font-bold text-blue-600">
              {formatCurrency(estimate.recommended_max_bid)}
            </div>
          </div>
          <div>
            <div className="text-xs text-gray-600 mb-1">Market Avg</div>
            <div className="text-lg font-semibold text-gray-700">
              {formatCurrency(estimate.estimated_value)}
            </div>
          </div>
        </div>

        {/* Profit margin bar */}
        <div className="mb-4">
          <div className="flex justify-between items-center mb-1">
            <span className="text-sm font-medium text-gray-700">Profit Margin</span>
            <span className={`text-sm font-bold ${estimate.profit_margin >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {estimate.profit_margin >= 0 ? '+' : ''}
              {formatPercent(estimate.profit_margin)}
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
            <div
              className={`${getProfitBarColor(estimate.profit_margin)} h-full rounded-full transition-all duration-500`}
              style={{ width: `${Math.min(Math.max(estimate.profit_margin * 100, 0), 100)}%` }}
            />
          </div>
          <div className="text-xs text-gray-600 mt-1">
            Est. Profit: {formatCurrency(estimate.profit_amount)}
          </div>
        </div>

        {/* Confidence and risk */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-600">Confidence:</span>
            <span className={`text-sm font-semibold px-2 py-1 rounded ${getConfidenceColor(estimate.confidence)}`}>
              {formatPercent(estimate.confidence)}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-600">Risk:</span>
            <span className={`text-sm font-semibold ${getRiskColor(estimate.risk_level)}`}>
              {estimate.risk_level.toUpperCase()}
            </span>
          </div>
        </div>

        {/* Market metrics */}
        <div className="grid grid-cols-2 gap-3 mb-4 text-xs">
          <div className="bg-white p-2 rounded">
            <div className="text-gray-600">Liquidity</div>
            <div className="font-semibold">{formatPercent(estimate.liquidity_avg)}</div>
          </div>
          <div className="bg-white p-2 rounded">
            <div className="text-gray-600">Volatility</div>
            <div className="font-semibold">{formatPercent(estimate.market_volatility)}</div>
          </div>
        </div>

        {/* Auto-bid button */}
        {onAutoBid && (
          <button
            onClick={() => onAutoBid(estimate.recommended_max_bid)}
            disabled={!canAutoBid}
            className={`w-full py-2 px-4 rounded-lg font-semibold transition-colors ${
              canAutoBid
                ? 'bg-blue-600 hover:bg-blue-700 text-white'
                : 'bg-gray-300 text-gray-500 cursor-not-allowed'
            }`}
          >
            {canAutoBid ? (
              <span>Auto-Bid until {formatCurrency(estimate.recommended_max_bid)}</span>
            ) : (
              <span>Auto-Bid (Upgrade to PRO)</span>
            )}
          </button>
        )}
      </div>
    </div>
  );
}
