/**
 * Admin Console Page - System management and monitoring
 */

'use client'

import { useState, lazy, Suspense } from 'react'
import Head from 'next/head'
import { useRouter } from 'next/router'

// Lazy load components
const SystemHealth = lazy(() => import('@/components/SystemHealth'))
const LearningLogs = lazy(() => import('@/components/LearningLogs'))
const Exports = lazy(() => import('@/components/Exports'))

type AdminTab = 'health' | 'logs' | 'exports'

export default function AdminPage() {
  const router = useRouter()
  const [activeTab, setActiveTab] = useState<AdminTab>('health')

  const tabs = [
    { id: 'health' as AdminTab, label: 'System Health', icon: '?' },
    { id: 'logs' as AdminTab, label: 'Learning Logs', icon: '??' },
    { id: 'exports' as AdminTab, label: 'Data Exports', icon: '??' },
  ]

  const handleBackToDashboard = () => {
    router.push('/dashboard')
  }

  return (
    <>
      <Head>
        <title>Admin Console - Antika Auction Watcher</title>
        <meta name="description" content="System administration and monitoring" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>

      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
        {/* Header */}
        <header className="bg-white shadow-sm border-b sticky top-0 z-50">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center py-4">
              {/* Logo & Title */}
              <div className="flex items-center space-x-3">
                <button
                  onClick={handleBackToDashboard}
                  className="w-10 h-10 bg-gradient-to-br from-gray-500 to-gray-700 rounded-lg flex items-center justify-center hover:from-gray-600 hover:to-gray-800 transition-colors"
                  title="Back to Dashboard"
                >
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
                      d="M10 19l-7-7m0 0l7-7m-7 7h18"
                    />
                  </svg>
                </button>
                <div>
                  <h1 className="text-2xl font-bold text-gray-900">Admin Console</h1>
                  <p className="text-sm text-gray-500">System management and monitoring</p>
                </div>
              </div>

              {/* Actions */}
              <div className="flex items-center space-x-4">
                <span className="text-sm text-gray-600">
                  Administrator Access
                </span>
              </div>
            </div>

            {/* Tabs */}
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
                  <span>{tab.label}</span>
                </button>
              ))}
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Tab Content with Lazy Loading */}
          {activeTab === 'health' && (
            <Suspense
              fallback={
                <div className="bg-white rounded-lg shadow-md p-8">
                  <div className="flex flex-col items-center justify-center py-12">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mb-4"></div>
                    <p className="text-gray-600">Loading system health...</p>
                  </div>
                </div>
              }
            >
              <SystemHealth />
            </Suspense>
          )}

          {activeTab === 'logs' && (
            <Suspense
              fallback={
                <div className="bg-white rounded-lg shadow-md p-8">
                  <div className="flex flex-col items-center justify-center py-12">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mb-4"></div>
                    <p className="text-gray-600">Loading learning logs...</p>
                  </div>
                </div>
              }
            >
              <LearningLogs />
            </Suspense>
          )}

          {activeTab === 'exports' && (
            <Suspense
              fallback={
                <div className="bg-white rounded-lg shadow-md p-8">
                  <div className="flex flex-col items-center justify-center py-12">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mb-4"></div>
                    <p className="text-gray-600">Loading export options...</p>
                  </div>
                </div>
              }
            >
              <Exports />
            </Suspense>
          )}
        </main>

        {/* Footer */}
        <footer className="bg-white border-t mt-12">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
            <div className="text-center text-sm text-gray-500">
              <p>Antika Auction Watcher - Admin Console (Phase 4)</p>
              <p className="mt-1">
                {activeTab === 'health' && (
                  <span>
                    Health API: <code className="px-2 py-1 bg-gray-100 rounded text-xs">/api/v1/admin/stats</code>
                  </span>
                )}
                {activeTab === 'logs' && (
                  <span>
                    Logs API: <code className="px-2 py-1 bg-gray-100 rounded text-xs">/api/v1/learning/history</code>
                  </span>
                )}
                {activeTab === 'exports' && (
                  <span>
                    Export APIs: <code className="px-2 py-1 bg-gray-100 rounded text-xs">/api/v1/admin/exports/*.csv</code>
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
