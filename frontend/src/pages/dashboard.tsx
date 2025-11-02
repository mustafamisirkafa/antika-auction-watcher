/**
 * Dashboard page - Main view with live auctions, learning insights, and system metrics
 */

'use client'

import { useEffect, useState, lazy, Suspense } from 'react'
import Head from 'next/head'
import { useAuctionStore } from '@/store/auctionStore'
import { useWebSocket } from '@/lib/websocket'
import AuctionFeed from '@/components/AuctionFeed'
import { ConnectionStatus } from '@/types/auction'

// Lazy load heavy components
const LearningInsights = lazy(() => import('@/components/LearningInsights'))
const MetricsPanel = lazy(() => import('@/components/MetricsPanel'))

type TabType = 'feed' | 'learning' | 'metrics'

export default function Dashboard() {
  const { addOrUpdateAuction, clearAuctions } = useAuctionStore()
  const { connect, disconnect, onEvent, onStatusChange } = useWebSocket()
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected')
  const [activeTab, setActiveTab] = useState<TabType>('feed')
  const [showEnded, setShowEnded] = useState(false)
  const [stats, setStats] = useState({ active: 0, ended: 0, total: 0 })

  // Connect to WebSocket on mount (stays connected across tabs)
  useEffect(() => {
    console.log('[Dashboard] Mounting, connecting to WebSocket')
    
    // Subscribe to connection status
    const unsubscribeStatus = onStatusChange((status) => {
      console.log('[Dashboard] Connection status:', status)
      setConnectionStatus(status)
    })

    // Subscribe to WebSocket events
    const unsubscribeEvents = onEvent((event) => {
      console.log('[Dashboard] Received event:', event)
      addOrUpdateAuction(event)
    })

    // Connect
    connect()

    // Cleanup on unmount (NOT on tab change)
    return () => {
      console.log('[Dashboard] Unmounting, disconnecting')
      unsubscribeStatus()
      unsubscribeEvents()
      disconnect()
    }
  }, [connect, disconnect, onEvent, onStatusChange, addOrUpdateAuction])

  // Update stats
  useEffect(() => {
    const interval = setInterval(() => {
      const { getActiveAuctions, getEndedAuctions, auctions } = useAuctionStore.getState()
      setStats({
        active: getActiveAuctions().length,
        ended: getEndedAuctions().length,
        total: Object.keys(auctions).length,
      })
    }, 1000)

    return () => clearInterval(interval)
  }, [])

  const getStatusColor = () => {
    switch (connectionStatus) {
      case 'connected':
        return 'bg-green-500'
      case 'connecting':
        return 'bg-yellow-500 animate-pulse'
      case 'disconnected':
        return 'bg-gray-400'
      case 'error':
        return 'bg-red-500'
      default:
        return 'bg-gray-400'
    }
  }

  const getStatusText = () => {
    switch (connectionStatus) {
      case 'connected':
        return 'Connected ?'
      case 'connecting':
        return 'Connecting...'
      case 'disconnected':
        return 'Disconnected ??'
      case 'error':
        return 'Connection Error ?'
      default:
        return 'Unknown'
    }
  }

  const handleClearAuctions = () => {
    if (confirm('Are you sure you want to clear all auctions?')) {
      clearAuctions()
    }
  }

  const tabs = [
    { id: 'feed' as TabType, label: '?? Live Feed', icon: '??' },
    { id: 'learning' as TabType, label: '?? Learning Insights', icon: '??' },
    { id: 'metrics' as TabType, label: '?? Metrics', icon: '??' },
  ]

  return (
    <>
      <Head>
        <title>Dashboard - Antika Auction Watcher</title>
        <meta name="description" content="Real-time auction monitoring with AI valuation" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>

      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
        {/* Header */}
        <header className="bg-white shadow-sm border-b sticky top-0 z-50">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center py-4">
              {/* Logo & Title */}
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 bg-gradient-to-br from-primary-500 to-primary-700 rounded-lg flex items-center justify-center">
                  <svg
                    className="w-6 h-6 text-white"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                    />
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                    />
                  </svg>
                </div>
                <div>
                  <h1 className="text-2xl font-bold text-gray-900">Antika Auction Watcher</h1>
                  <p className="text-sm text-gray-500">Real-time AI-powered auction monitoring</p>
                </div>
              </div>

              {/* Connection Status */}
              <div className="flex items-center space-x-4">
                {/* Stats (only show on Feed tab) */}
                {activeTab === 'feed' && (
                  <div className="hidden md:flex items-center space-x-4 text-sm">
                    <div className="flex items-center space-x-2">
                      <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                      <span className="text-gray-600">
                        <span className="font-semibold text-gray-900">{stats.active}</span> Active
                      </span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <div className="w-2 h-2 bg-gray-400 rounded-full"></div>
                      <span className="text-gray-600">
                        <span className="font-semibold text-gray-900">{stats.ended}</span> Ended
                      </span>
                    </div>
                  </div>
                )}

                {/* Connection Badge */}
                <div className="flex items-center space-x-2 px-3 py-2 rounded-lg bg-gray-50">
                  <div className={`w-2 h-2 rounded-full ${getStatusColor()}`}></div>
                  <span className="text-sm font-medium text-gray-700">
                    {getStatusText()}
                  </span>
                </div>
              </div>
            </div>

            {/* Main Tabs */}
            <div className="flex space-x-1 border-b">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`px-6 py-3 text-sm font-medium transition-colors flex items-center space-x-2 ${
                    activeTab === tab.id
                      ? 'text-primary-600 border-b-2 border-primary-600 bg-primary-50'
                      : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                  }`}
                >
                  <span>{tab.icon}</span>
                  <span>{tab.label.replace(/^[^ ]+ /, '')}</span>
                </button>
              ))}
            </div>

            {/* Sub-tabs for Feed */}
            {activeTab === 'feed' && (
              <div className="flex space-x-1 py-2">
                <button
                  onClick={() => setShowEnded(false)}
                  className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                    !showEnded
                      ? 'bg-primary-100 text-primary-700'
                      : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                  }`}
                >
                  Active Auctions ({stats.active})
                </button>
                <button
                  onClick={() => setShowEnded(true)}
                  className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                    showEnded
                      ? 'bg-primary-100 text-primary-700'
                      : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                  }`}
                >
                  Ended Auctions ({stats.ended})
                </button>
              </div>
            )}
          </div>
        </header>

        {/* Main Content */}
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Connection Warning (show on all tabs) */}
          {connectionStatus !== 'connected' && activeTab === 'feed' && (
            <div
              className={`mb-6 p-4 rounded-lg border ${
                connectionStatus === 'error'
                  ? 'bg-red-50 border-red-200'
                  : 'bg-yellow-50 border-yellow-200'
              }`}
            >
              <div className="flex items-start">
                <svg
                  className={`w-5 h-5 ${
                    connectionStatus === 'error' ? 'text-red-500' : 'text-yellow-500'
                  } mt-0.5`}
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fillRule="evenodd"
                    d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                    clipRule="evenodd"
                  />
                </svg>
                <div className="ml-3">
                  <h3
                    className={`text-sm font-medium ${
                      connectionStatus === 'error' ? 'text-red-800' : 'text-yellow-800'
                    }`}
                  >
                    {connectionStatus === 'error'
                      ? 'Connection Error'
                      : 'Connecting to WebSocket'}
                  </h3>
                  <p
                    className={`text-sm mt-1 ${
                      connectionStatus === 'error' ? 'text-red-700' : 'text-yellow-700'
                    }`}
                  >
                    {connectionStatus === 'error'
                      ? 'Unable to connect to the auction feed. Make sure the backend server is running on ws://127.0.0.1:8000.'
                      : 'Establishing connection to the live auction feed...'}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Tab Content with Lazy Loading */}
          {activeTab === 'feed' && (
            <>
              {/* Action Buttons */}
              <div className="mb-6 flex justify-between items-center">
                <div className="text-sm text-gray-600">
                  Last updated: {new Date().toLocaleTimeString('tr-TR')}
                </div>
                <button
                  onClick={handleClearAuctions}
                  className="px-4 py-2 text-sm font-medium text-red-600 hover:text-red-700 hover:bg-red-50 rounded-lg transition-colors"
                >
                  Clear All
                </button>
              </div>

              {/* Auction Feed */}
              <AuctionFeed showEnded={showEnded} />
            </>
          )}

          {activeTab === 'learning' && (
            <Suspense
              fallback={
                <div className="bg-white rounded-lg shadow-md p-8">
                  <div className="flex flex-col items-center justify-center py-12">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mb-4"></div>
                    <p className="text-gray-600">Loading learning insights...</p>
                  </div>
                </div>
              }
            >
              <LearningInsights autoRefresh={true} refreshInterval={60000} />
            </Suspense>
          )}

          {activeTab === 'metrics' && (
            <Suspense
              fallback={
                <div className="bg-white rounded-lg shadow-md p-8">
                  <div className="flex flex-col items-center justify-center py-12">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mb-4"></div>
                    <p className="text-gray-600">Loading system metrics...</p>
                  </div>
                </div>
              }
            >
              <MetricsPanel autoRefresh={true} refreshInterval={60000} />
            </Suspense>
          )}
        </main>

        {/* Footer */}
        <footer className="bg-white border-t mt-12">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
            <div className="text-center text-sm text-gray-500">
              <p>Antika Auction Watcher - Phase 3 Week 3 Implementation</p>
              <p className="mt-1">
                {activeTab === 'feed' && (
                  <span>
                    WebSocket: <code className="px-2 py-1 bg-gray-100 rounded text-xs">ws://127.0.0.1:8000/api/ws/auctions</code>
                  </span>
                )}
                {activeTab === 'learning' && (
                  <span>
                    Learning API: <code className="px-2 py-1 bg-gray-100 rounded text-xs">/api/v1/admin/learning/metrics</code>
                  </span>
                )}
                {activeTab === 'metrics' && (
                  <span>
                    Metrics API: <code className="px-2 py-1 bg-gray-100 rounded text-xs">/api/v1/admin/metrics/dashboard</code>
                  </span>
                )}
              </p>
            </div>
          </div>
        </footer>
      </div>
    </>
  )
}
