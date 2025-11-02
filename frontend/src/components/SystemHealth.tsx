/**
 * System Health Component - Real-time system metrics with color-coded indicators
 */

'use client'

import { useEffect } from 'react'
import useSWR from 'swr'
import { SystemMetrics, HealthLevel } from '@/types/admin'
import { fetchAdminStats } from '@/lib/api'

export default function SystemHealth() {
  // Fetch data with 10 second auto-refresh
  const { data, error, isLoading, mutate } = useSWR<SystemMetrics>(
    '/api/admin/stats',
    fetchAdminStats,
    {
      refreshInterval: 10000, // 10 seconds
      revalidateOnFocus: false,
      revalidateOnReconnect: true,
    }
  )

  useEffect(() => {
    // Force refresh on mount
    mutate()
  }, [mutate])

  const getHealthLevel = (
    value: number,
    thresholds: { excellent: number; good: number; warning: number },
    isReverse?: boolean
  ): HealthLevel => {
    if (isReverse) {
      // Higher is better (e.g., cache hit ratio)
      if (value >= thresholds.excellent) return 'excellent'
      if (value >= thresholds.good) return 'good'
      if (value >= thresholds.warning) return 'warning'
      return 'critical'
    } else {
      // Lower is better (e.g., response time)
      if (value <= thresholds.excellent) return 'excellent'
      if (value <= thresholds.good) return 'good'
      if (value <= thresholds.warning) return 'warning'
      return 'critical'
    }
  }

  const getHealthColor = (level: HealthLevel) => {
    const colors = {
      excellent: {
        text: 'text-green-700',
        bg: 'bg-green-100',
        border: 'border-green-300',
        dot: 'bg-green-500',
      },
      good: {
        text: 'text-blue-700',
        bg: 'bg-blue-100',
        border: 'border-blue-300',
        dot: 'bg-blue-500',
      },
      warning: {
        text: 'text-yellow-700',
        bg: 'bg-yellow-100',
        border: 'border-yellow-300',
        dot: 'bg-yellow-500',
      },
      critical: {
        text: 'text-red-700',
        bg: 'bg-red-100',
        border: 'border-red-300',
        dot: 'bg-red-500',
      },
    }
    return colors[level]
  }

  const getHealthLabel = (level: HealthLevel) => {
    const labels = {
      excellent: '? Excellent',
      good: '?? Good',
      warning: '?? Warning',
      critical: '?? Critical',
    }
    return labels[level]
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6">
        <div className="flex items-start">
          <svg className="w-6 h-6 text-red-500 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
              clipRule="evenodd"
            />
          </svg>
          <div className="ml-3">
            <h3 className="text-sm font-medium text-red-800">Failed to Load System Health</h3>
            <p className="text-sm text-red-700 mt-1">
              {error instanceof Error ? error.message : 'Unable to fetch system metrics'}
            </p>
          </div>
        </div>
      </div>
    )
  }

  if (isLoading && !data) {
    return (
      <div className="bg-white rounded-lg shadow-md p-8">
        <div className="flex flex-col items-center justify-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mb-4"></div>
          <p className="text-gray-600">Loading system health...</p>
        </div>
      </div>
    )
  }

  if (!data) {
    return null
  }

  // Calculate health levels
  const rpsLevel = getHealthLevel(data.requests_per_second, {
    excellent: 200,
    good: 500,
    warning: 800,
  })

  const p99Level = getHealthLevel(data.response_time_ms.p99, {
    excellent: 200,
    good: 400,
    warning: 800,
  })

  const cacheLevel = getHealthLevel(
    data.redis_hit_ratio,
    {
      excellent: 0.9,
      good: 0.75,
      warning: 0.6,
    },
    true
  )

  const queueLevel = getHealthLevel(data.queue_pending, {
    excellent: 10,
    good: 50,
    warning: 100,
  })

  const rpsColors = getHealthColor(rpsLevel)
  const p99Colors = getHealthColor(p99Level)
  const cacheColors = getHealthColor(cacheLevel)
  const queueColors = getHealthColor(queueLevel)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-gray-900">? System Health</h2>
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
            <span className="text-sm text-gray-600">Auto-refresh: 10s</span>
          </div>
        </div>

        {/* System Uptime */}
        <div className="bg-gradient-to-br from-purple-50 to-purple-100 rounded-lg p-6 mb-6">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-medium text-purple-900 mb-1">System Uptime</div>
              <div className="text-4xl font-bold text-purple-700">{data.uptime}</div>
            </div>
            <svg className="w-16 h-16 text-purple-600" fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z"
                clipRule="evenodd"
              />
            </svg>
          </div>
        </div>

        {/* Metrics Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Requests per Second */}
          <div className={`rounded-lg border-2 p-4 ${rpsColors.bg} ${rpsColors.border}`}>
            <div className="flex items-center justify-between mb-2">
              <div className={`text-xs font-medium ${rpsColors.text}`}>Requests/sec</div>
              <div className={`w-2 h-2 rounded-full ${rpsColors.dot}`}></div>
            </div>
            <div className={`text-3xl font-bold ${rpsColors.text} mb-2`}>
              {data.requests_per_second}
            </div>
            <div className={`text-xs ${rpsColors.text}`}>{getHealthLabel(rpsLevel)}</div>
          </div>

          {/* Response Time p99 */}
          <div className={`rounded-lg border-2 p-4 ${p99Colors.bg} ${p99Colors.border}`}>
            <div className="flex items-center justify-between mb-2">
              <div className={`text-xs font-medium ${p99Colors.text}`}>Response p99</div>
              <div className={`w-2 h-2 rounded-full ${p99Colors.dot}`}></div>
            </div>
            <div className={`text-3xl font-bold ${p99Colors.text} mb-2`}>
              {data.response_time_ms.p99}ms
            </div>
            <div className={`text-xs ${p99Colors.text}`}>{getHealthLabel(p99Level)}</div>
          </div>

          {/* Redis Hit Ratio */}
          <div className={`rounded-lg border-2 p-4 ${cacheColors.bg} ${cacheColors.border}`}>
            <div className="flex items-center justify-between mb-2">
              <div className={`text-xs font-medium ${cacheColors.text}`}>Cache Hit Ratio</div>
              <div className={`w-2 h-2 rounded-full ${cacheColors.dot}`}></div>
            </div>
            <div className={`text-3xl font-bold ${cacheColors.text} mb-2`}>
              {(data.redis_hit_ratio * 100).toFixed(1)}%
            </div>
            <div className={`text-xs ${cacheColors.text}`}>{getHealthLabel(cacheLevel)}</div>
          </div>

          {/* Queue Pending */}
          <div className={`rounded-lg border-2 p-4 ${queueColors.bg} ${queueColors.border}`}>
            <div className="flex items-center justify-between mb-2">
              <div className={`text-xs font-medium ${queueColors.text}`}>Queue Pending</div>
              <div className={`w-2 h-2 rounded-full ${queueColors.dot}`}></div>
            </div>
            <div className={`text-3xl font-bold ${queueColors.text} mb-2`}>
              {data.queue_pending}
            </div>
            <div className={`text-xs ${queueColors.text}`}>{getHealthLabel(queueLevel)}</div>
          </div>
        </div>
      </div>

      {/* Additional Metrics */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Response Time Percentiles</h3>
        <div className="grid grid-cols-3 gap-4">
          <div className="text-center p-4 bg-gray-50 rounded-lg">
            <div className="text-sm text-gray-600 mb-1">p50 (Median)</div>
            <div className="text-2xl font-bold text-gray-900">
              {data.response_time_ms.p50}ms
            </div>
          </div>
          <div className="text-center p-4 bg-gray-50 rounded-lg">
            <div className="text-sm text-gray-600 mb-1">p90</div>
            <div className="text-2xl font-bold text-gray-900">
              {data.response_time_ms.p90}ms
            </div>
          </div>
          <div className="text-center p-4 bg-gray-50 rounded-lg">
            <div className="text-sm text-gray-600 mb-1">p99</div>
            <div className="text-2xl font-bold text-gray-900">
              {data.response_time_ms.p99}ms
            </div>
          </div>
        </div>
      </div>

      {/* Thresholds Legend */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Performance Thresholds</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div>
            <div className="text-sm font-medium text-gray-700 mb-2">Requests/sec</div>
            <div className="space-y-1 text-xs">
              <div className="flex items-center">
                <div className="w-3 h-3 bg-green-500 rounded mr-2"></div>
                <span>?200: Excellent</span>
              </div>
              <div className="flex items-center">
                <div className="w-3 h-3 bg-blue-500 rounded mr-2"></div>
                <span>200-500: Good</span>
              </div>
              <div className="flex items-center">
                <div className="w-3 h-3 bg-yellow-500 rounded mr-2"></div>
                <span>500-800: Warning</span>
              </div>
              <div className="flex items-center">
                <div className="w-3 h-3 bg-red-500 rounded mr-2"></div>
                <span>&gt;800: Critical</span>
              </div>
            </div>
          </div>

          <div>
            <div className="text-sm font-medium text-gray-700 mb-2">Response Time (p99)</div>
            <div className="space-y-1 text-xs">
              <div className="flex items-center">
                <div className="w-3 h-3 bg-green-500 rounded mr-2"></div>
                <span>?200ms: Excellent</span>
              </div>
              <div className="flex items-center">
                <div className="w-3 h-3 bg-blue-500 rounded mr-2"></div>
                <span>200-400ms: Good</span>
              </div>
              <div className="flex items-center">
                <div className="w-3 h-3 bg-yellow-500 rounded mr-2"></div>
                <span>400-800ms: Warning</span>
              </div>
              <div className="flex items-center">
                <div className="w-3 h-3 bg-red-500 rounded mr-2"></div>
                <span>&gt;800ms: Critical</span>
              </div>
            </div>
          </div>

          <div>
            <div className="text-sm font-medium text-gray-700 mb-2">Cache Hit Ratio</div>
            <div className="space-y-1 text-xs">
              <div className="flex items-center">
                <div className="w-3 h-3 bg-green-500 rounded mr-2"></div>
                <span>?90%: Excellent</span>
              </div>
              <div className="flex items-center">
                <div className="w-3 h-3 bg-blue-500 rounded mr-2"></div>
                <span>75-90%: Good</span>
              </div>
              <div className="flex items-center">
                <div className="w-3 h-3 bg-yellow-500 rounded mr-2"></div>
                <span>60-75%: Warning</span>
              </div>
              <div className="flex items-center">
                <div className="w-3 h-3 bg-red-500 rounded mr-2"></div>
                <span>&lt;60%: Critical</span>
              </div>
            </div>
          </div>

          <div>
            <div className="text-sm font-medium text-gray-700 mb-2">Queue Size</div>
            <div className="space-y-1 text-xs">
              <div className="flex items-center">
                <div className="w-3 h-3 bg-green-500 rounded mr-2"></div>
                <span>?10: Excellent</span>
              </div>
              <div className="flex items-center">
                <div className="w-3 h-3 bg-blue-500 rounded mr-2"></div>
                <span>10-50: Good</span>
              </div>
              <div className="flex items-center">
                <div className="w-3 h-3 bg-yellow-500 rounded mr-2"></div>
                <span>50-100: Warning</span>
              </div>
              <div className="flex items-center">
                <div className="w-3 h-3 bg-red-500 rounded mr-2"></div>
                <span>&gt;100: Critical</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
