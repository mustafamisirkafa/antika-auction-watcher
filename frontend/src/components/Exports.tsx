/**
 * Exports Component - CSV export functionality with date range selection
 */

'use client'

import { useState } from 'react'
import { getValuationsExportUrl, getOutcomesExportUrl } from '@/lib/api'

export default function Exports() {
  const [valuationsFrom, setValuationsFrom] = useState('')
  const [valuationsTo, setValuationsTo] = useState('')
  const [outcomesFrom, setOutcomesFrom] = useState('')
  const [outcomesTo, setOutcomesTo] = useState('')
  const [outcomesCategory, setOutcomesCategory] = useState('')
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null)

  const showToast = (message: string, type: 'success' | 'error') => {
    setToast({ message, type })
    setTimeout(() => setToast(null), 5000)
  }

  const handleValuationsExport = () => {
    try {
      // Validate dates
      if (valuationsFrom && valuationsTo && new Date(valuationsFrom) > new Date(valuationsTo)) {
        showToast('Start date must be before end date', 'error')
        return
      }

      const url = getValuationsExportUrl({
        from: valuationsFrom || undefined,
        to: valuationsTo || undefined,
      })

      // Trigger download
      window.location.href = url
      showToast('Valuations export started', 'success')
    } catch (error) {
      showToast(
        error instanceof Error ? error.message : 'Failed to export valuations',
        'error'
      )
    }
  }

  const handleOutcomesExport = () => {
    try {
      // Validate dates
      if (outcomesFrom && outcomesTo && new Date(outcomesFrom) > new Date(outcomesTo)) {
        showToast('Start date must be before end date', 'error')
        return
      }

      const url = getOutcomesExportUrl({
        from: outcomesFrom || undefined,
        to: outcomesTo || undefined,
        category: outcomesCategory || undefined,
      })

      // Trigger download
      window.location.href = url
      showToast('Outcomes export started', 'success')
    } catch (error) {
      showToast(
        error instanceof Error ? error.message : 'Failed to export outcomes',
        'error'
      )
    }
  }

  const getTodayDate = () => {
    const today = new Date()
    return today.toISOString().split('T')[0]
  }

  const getLastMonthDate = () => {
    const lastMonth = new Date()
    lastMonth.setMonth(lastMonth.getMonth() - 1)
    return lastMonth.toISOString().split('T')[0]
  }

  const categories = [
    'antiques',
    'ceramics',
    'coins',
    'paintings',
    'furniture',
    'jewelry',
    'collectibles',
    'art',
    'books',
  ]

  return (
    <div className="space-y-6">
      {/* Toast Notification */}
      {toast && (
        <div
          className={`fixed top-4 right-4 z-50 px-6 py-4 rounded-lg shadow-lg border-2 animate-fade-in ${
            toast.type === 'success'
              ? 'bg-green-50 border-green-300 text-green-800'
              : 'bg-red-50 border-red-300 text-red-800'
          }`}
        >
          <div className="flex items-center">
            {toast.type === 'success' ? (
              <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                  clipRule="evenodd"
                />
              </svg>
            ) : (
              <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                  clipRule="evenodd"
                />
              </svg>
            )}
            <span className="font-medium">{toast.message}</span>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-2xl font-bold text-gray-900">?? Data Exports</h2>
        <p className="text-sm text-gray-600 mt-1">
          Export valuation and outcome data as CSV files
        </p>
      </div>

      {/* Valuations Export */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="flex items-center mb-4">
          <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mr-4">
            <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z"
              />
            </svg>
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Valuations Export</h3>
            <p className="text-sm text-gray-600">Export AI valuation estimates with confidence scores</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">From Date</label>
            <input
              type="date"
              value={valuationsFrom}
              onChange={(e) => setValuationsFrom(e.target.value)}
              max={getTodayDate()}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">To Date</label>
            <input
              type="date"
              value={valuationsTo}
              onChange={(e) => setValuationsTo(e.target.value)}
              max={getTodayDate()}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
          </div>
        </div>

        <div className="flex items-center justify-between">
          <div className="text-sm text-gray-600">
            {!valuationsFrom && !valuationsTo && 'All valuations will be exported'}
            {valuationsFrom && valuationsTo && `Exporting from ${valuationsFrom} to ${valuationsTo}`}
          </div>
          <div className="flex space-x-2">
            <button
              onClick={() => {
                setValuationsFrom(getLastMonthDate())
                setValuationsTo(getTodayDate())
              }}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
            >
              Last Month
            </button>
            <button
              onClick={handleValuationsExport}
              className="px-6 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors flex items-center"
            >
              <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                />
              </svg>
              Download CSV
            </button>
          </div>
        </div>
      </div>

      {/* Outcomes Export */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="flex items-center mb-4">
          <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center mr-4">
            <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Bid Outcomes Export</h3>
            <p className="text-sm text-gray-600">Export bid results with profitability metrics</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">From Date</label>
            <input
              type="date"
              value={outcomesFrom}
              onChange={(e) => setOutcomesFrom(e.target.value)}
              max={getTodayDate()}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">To Date</label>
            <input
              type="date"
              value={outcomesTo}
              onChange={(e) => setOutcomesTo(e.target.value)}
              max={getTodayDate()}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Category (Optional)</label>
            <select
              value={outcomesCategory}
              onChange={(e) => setOutcomesCategory(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            >
              <option value="">All Categories</option>
              {categories.map((cat) => (
                <option key={cat} value={cat}>
                  {cat.charAt(0).toUpperCase() + cat.slice(1)}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="flex items-center justify-between">
          <div className="text-sm text-gray-600">
            {!outcomesFrom && !outcomesTo && !outcomesCategory && 'All outcomes will be exported'}
            {(outcomesFrom || outcomesTo || outcomesCategory) && (
              <span>
                Exporting
                {outcomesFrom && outcomesTo && ` from ${outcomesFrom} to ${outcomesTo}`}
                {outcomesCategory && ` for category: ${outcomesCategory}`}
              </span>
            )}
          </div>
          <div className="flex space-x-2">
            <button
              onClick={() => {
                setOutcomesFrom(getLastMonthDate())
                setOutcomesTo(getTodayDate())
              }}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
            >
              Last Month
            </button>
            <button
              onClick={handleOutcomesExport}
              className="px-6 py-2 text-sm font-medium text-white bg-green-600 rounded-lg hover:bg-green-700 transition-colors flex items-center"
            >
              <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                />
              </svg>
              Download CSV
            </button>
          </div>
        </div>
      </div>

      {/* Export Information */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
        <div className="flex items-start">
          <svg className="w-5 h-5 text-blue-600 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
              clipRule="evenodd"
            />
          </svg>
          <div className="ml-3">
            <h4 className="text-sm font-medium text-blue-900">Export Information</h4>
            <div className="mt-2 text-sm text-blue-800 space-y-1">
              <p>? CSV files will download automatically to your browser's download folder</p>
              <p>? Date filters are optional - leave blank to export all data</p>
              <p>? Large exports may take a few seconds to generate</p>
              <p>? Files include headers with column descriptions</p>
              <p>? Timestamps are in UTC format</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
