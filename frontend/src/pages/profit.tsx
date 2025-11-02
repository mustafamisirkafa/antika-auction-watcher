/**
 * Profit Advisor Dashboard Page
 * Pre-auction intelligence and profit estimation
 */
import React, { useState, useEffect } from 'react';
import Head from 'next/head';
import { useTeamStore } from '@/store/teamStore';
import ProfitCard from '@/components/ProfitCard';

type TabType = 'insights' | 'comparisons';

interface ProfitEstimate {
  id: number;
  estimated_value: number;
  recommended_max_bid: number;
  profit_margin: number;
  profit_amount: number;
  confidence: number;
  risk_level: 'low' | 'medium' | 'high';
  market_volatility: number;
  liquidity_avg: number;
  auction_item: AuctionItem;
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

export default function ProfitDashboard() {
  const { currentTeam, currentPlan } = useTeamStore();
  const [activeTab, setActiveTab] = useState<TabType>('insights');
  const [estimates, setEstimates] = useState<ProfitEstimate[]>([]);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [filterRisk, setFilterRisk] = useState<string>('all');
  const [filterConfidence, setFilterConfidence] = useState<number>(0);

  const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api/v1';

  // Check if user has access (PRO/ENTERPRISE)
  const hasAccess = currentPlan && currentPlan.agent_limit >= 25;

  useEffect(() => {
    if (currentTeam && hasAccess) {
      fetchEstimates();
    }
  }, [currentTeam, hasAccess]);

  // Auto-refresh every 60 seconds
  useEffect(() => {
    if (!currentTeam || !hasAccess) return;

    const interval = setInterval(() => {
      fetchEstimates();
    }, 60000);

    return () => clearInterval(interval);
  }, [currentTeam, hasAccess]);

  const fetchEstimates = async () => {
    if (!currentTeam) return;

    try {
      const response = await fetch(`${API_BASE_URL}/profit/${currentTeam.id}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'X-Team-Id': currentTeam.id.toString(),
        },
      });

      if (!response.ok) throw new Error('Failed to fetch estimates');

      const data = await response.json();
      setEstimates(data);
    } catch (error) {
      console.error('Failed to fetch profit estimates:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyze = async () => {
    if (!currentTeam) return;

    setAnalyzing(true);
    try {
      const response = await fetch(`${API_BASE_URL}/profit/analyze`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'X-Team-Id': currentTeam.id.toString(),
        },
        body: JSON.stringify({
          auction_item_ids: null, // Analyze all
          force_refresh: true,
        }),
      });

      if (!response.ok) throw new Error('Analysis failed');

      const data = await response.json();
      setEstimates(data.estimates);
      alert(`Successfully analyzed ${data.analyzed_count} items!`);
    } catch (error) {
      console.error('Analysis failed:', error);
      alert('Failed to run profit analysis');
    } finally {
      setAnalyzing(false);
    }
  };

  const handleAutoBid = (itemId: number, maxBid: number) => {
    // Placeholder for auto-bid logic
    alert(`Auto-bid setup for item ${itemId} with max bid ${maxBid} ?`);
  };

  // Filter estimates
  const filteredEstimates = estimates.filter((est) => {
    if (filterRisk !== 'all' && est.risk_level !== filterRisk) return false;
    if (est.confidence < filterConfidence) return false;
    return true;
  });

  // Sort by profit margin (descending)
  const sortedEstimates = [...filteredEstimates].sort(
    (a, b) => b.profit_margin - a.profit_margin
  );

  // Calculate stats
  const stats = {
    total: estimates.length,
    high_confidence: estimates.filter((e) => e.confidence >= 0.8).length,
    profitable: estimates.filter((e) => e.profit_margin >= 0.15).length,
    avg_margin: estimates.length > 0
      ? estimates.reduce((sum, e) => sum + e.profit_margin, 0) / estimates.length
      : 0,
  };

  // Upgrade notice
  if (!hasAccess) {
    return (
      <>
        <Head>
          <title>Profit Advisor - Antika Auction Watcher</title>
        </Head>

        <div className="min-h-screen bg-gray-50 p-6">
          <div className="max-w-4xl mx-auto">
            <div className="bg-gradient-to-r from-blue-600 to-blue-800 rounded-lg shadow-lg p-8 text-white text-center">
              <svg
                className="w-20 h-20 mx-auto mb-4 opacity-80"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
                />
              </svg>
              <h1 className="text-3xl font-bold mb-4">AI Profit Advisor</h1>
              <p className="text-xl mb-6 text-blue-100">
                Get AI-powered profit estimates and bid recommendations for upcoming auctions
              </p>
              <div className="bg-white bg-opacity-20 rounded-lg p-6 mb-6">
                <p className="text-lg mb-4">
                  This feature is available for <strong>PRO</strong> and <strong>ENTERPRISE</strong> plans
                </p>
                <p className="text-sm text-blue-100">
                  Your current plan: <strong>{currentPlan?.code || 'FREE'}</strong>
                </p>
              </div>
              <a
                href="/settings/plan"
                className="inline-block bg-white text-blue-600 px-8 py-3 rounded-lg font-semibold hover:bg-blue-50 transition-colors"
              >
                Upgrade to PRO
              </a>
            </div>

            {/* Feature preview */}
            <div className="mt-8 bg-white rounded-lg shadow-md p-6">
              <h2 className="text-2xl font-bold mb-4">What You Get:</h2>
              <div className="space-y-4">
                <div className="flex items-start">
                  <svg className="w-6 h-6 text-green-500 mr-3 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                  <div>
                    <h3 className="font-semibold">AI-Powered Profit Estimates</h3>
                    <p className="text-gray-600">Get recommended maximum bids based on real market data</p>
                  </div>
                </div>
                <div className="flex items-start">
                  <svg className="w-6 h-6 text-green-500 mr-3 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                  <div>
                    <h3 className="font-semibold">Market Analysis</h3>
                    <p className="text-gray-600">Compare prices across eBay, Etsy, Sahibinden, and Letgo</p>
                  </div>
                </div>
                <div className="flex items-start">
                  <svg className="w-6 h-6 text-green-500 mr-3 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                  <div>
                    <h3 className="font-semibold">Risk Assessment</h3>
                    <p className="text-gray-600">Confidence scores and risk levels for every item</p>
                  </div>
                </div>
                <div className="flex items-start">
                  <svg className="w-6 h-6 text-green-500 mr-3 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                  <div>
                    <h3 className="font-semibold">Auto-Bid Integration</h3>
                    <p className="text-gray-600">One-click auto-bid setup with recommended limits</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </>
    );
  }

  return (
    <>
      <Head>
        <title>Profit Advisor - Antika Auction Watcher</title>
      </Head>

      <div className="min-h-screen bg-gray-50">
        {/* Header */}
        <div className="bg-white border-b shadow-sm">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-3xl font-bold text-gray-900">AI Profit Advisor</h1>
                <p className="text-gray-600 mt-1">
                  Pre-auction intelligence and bid recommendations
                </p>
              </div>
              <button
                onClick={handleAnalyze}
                disabled={analyzing}
                className={`px-6 py-3 rounded-lg font-semibold transition-colors ${
                  analyzing
                    ? 'bg-gray-400 cursor-not-allowed'
                    : 'bg-blue-600 hover:bg-blue-700 text-white'
                }`}
              >
                {analyzing ? (
                  <span className="flex items-center">
                    <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Analyzing...
                  </span>
                ) : (
                  '?? Refresh Analysis'
                )}
              </button>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-4 gap-4 mt-6">
              <div className="bg-blue-50 rounded-lg p-4">
                <div className="text-sm text-gray-600">Total Items</div>
                <div className="text-2xl font-bold text-blue-600">{stats.total}</div>
              </div>
              <div className="bg-green-50 rounded-lg p-4">
                <div className="text-sm text-gray-600">High Confidence</div>
                <div className="text-2xl font-bold text-green-600">{stats.high_confidence}</div>
              </div>
              <div className="bg-purple-50 rounded-lg p-4">
                <div className="text-sm text-gray-600">Profitable (?15%)</div>
                <div className="text-2xl font-bold text-purple-600">{stats.profitable}</div>
              </div>
              <div className="bg-yellow-50 rounded-lg p-4">
                <div className="text-sm text-gray-600">Avg Margin</div>
                <div className="text-2xl font-bold text-yellow-600">
                  {(stats.avg_margin * 100).toFixed(1)}%
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Tabs and Filters */}
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          {/* Tabs */}
          <div className="flex space-x-4 mb-6 border-b">
            <button
              onClick={() => setActiveTab('insights')}
              className={`px-6 py-3 font-semibold transition-colors border-b-2 ${
                activeTab === 'insights'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-600 hover:text-gray-900'
              }`}
            >
              ?? Pre-Auction Insights
            </button>
            <button
              onClick={() => setActiveTab('comparisons')}
              className={`px-6 py-3 font-semibold transition-colors border-b-2 ${
                activeTab === 'comparisons'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-600 hover:text-gray-900'
              }`}
            >
              ?? Market Comparisons
            </button>
          </div>

          {/* Filters */}
          <div className="bg-white rounded-lg shadow-sm p-4 mb-6 flex items-center gap-4">
            <label className="flex items-center gap-2">
              <span className="text-sm font-medium text-gray-700">Risk:</span>
              <select
                value={filterRisk}
                onChange={(e) => setFilterRisk(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">All</option>
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
              </select>
            </label>
            <label className="flex items-center gap-2">
              <span className="text-sm font-medium text-gray-700">Min Confidence:</span>
              <input
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={filterConfidence}
                onChange={(e) => setFilterConfidence(parseFloat(e.target.value))}
                className="w-32"
              />
              <span className="text-sm font-semibold">{(filterConfidence * 100).toFixed(0)}%</span>
            </label>
            <div className="flex-1"></div>
            <div className="text-sm text-gray-600">
              Showing {sortedEstimates.length} of {estimates.length} items
            </div>
          </div>

          {/* Content */}
          {loading ? (
            <div className="text-center py-12">
              <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
              <p className="text-gray-600 mt-4">Loading profit estimates...</p>
            </div>
          ) : sortedEstimates.length === 0 ? (
            <div className="bg-white rounded-lg shadow-sm p-12 text-center">
              <p className="text-gray-600 text-lg">No profit estimates found</p>
              <p className="text-gray-500 mt-2">Try adjusting your filters or run a new analysis</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
              {sortedEstimates.map((estimate) => (
                <ProfitCard
                  key={estimate.id}
                  estimate={estimate}
                  auctionItem={estimate.auction_item}
                  onAutoBid={(maxBid) => handleAutoBid(estimate.auction_item.id, maxBid)}
                  canAutoBid={currentPlan?.agent_limit >= 25}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
