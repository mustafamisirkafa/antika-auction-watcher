/**
 * Metrics Panel - Displays system health and performance metrics
 */

'use client'

import useSWR from 'swr'
import {
  LineChart,
  Line,
  RadialBarChart,
  RadialBar,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
  PolarAngleAxis,
} from 'recharts'
import {
  SystemMetrics,
  ResponseTimeItem,
  MetricsPanelProps,
  PerformanceLevel,
} from '@/types/metrics'
import { fetchSystemMetrics } from '@/lib/api'

export default function MetricsPanel({
  autoRefresh = true,
  refreshInterval = 60000, // 60 seconds
}: MetricsPanelProps) {
  // Fetch data with SWR
  const { data, error, isLoading } = useSWR<SystemMetrics>(
    '/api/admin/stats',
    fetchSystemMetrics,
    {
      refreshInterval: autoRefresh ? refreshInterval : 0,
      revalidateOnFocus: false,
      revalidateOnReconnect: true,
    }
  )

  const getPerformanceLevel = (
    value: number,
    thresholds: { excellent: number; good: number; warning: number }
  ): PerformanceLevel => {
    if (value <= thresholds.excellent) return 'excellent'
    if (value <= thresholds.good) return 'good'
    if (value <= thresholds.warning) return 'warning'
    return 'critical'
  }

  const getPerformanceColor = (level: PerformanceLevel) => {
    const colors = {
      excellent: { text: 'text-green-600', bg: 'bg-green-100', border: 'border-green-300', hex: '#10b981' },
      good: { text: 'text-blue-600', bg: 'bg-blue-100', border: 'border-blue-300', hex: '#3b82f6' },
      warning: { text: 'text-yellow-600', bg: 'bg-yellow-100', border: 'border-yellow-300', hex: '#f59e0b' },
      critical: { text: 'text-red-600', bg: 'bg-red-100', border: 'border-red-300', hex: '#ef4444' },
    }
    return colors[level]
  }

  const getCacheHealthLevel = (hitRatio: number): PerformanceLevel => {
    if (hitRatio >= 0.9) return 'excellent'
    if (hitRatio >= 0.75) return 'good'
    if (hitRatio >= 0.6) return 'warning'
    return 'critical'
  }

  const getQueueHealthLevel = (pending: number): PerformanceLevel => {
    if (pending <= 10) return 'excellent'
    if (pending <= 50) return 'good'
    if (pending <= 100) return 'warning'
    return 'critical'
  }

  const getRpsHealthLevel = (rps: number): PerformanceLevel => {
    if (rps <= 200) return 'excellent'
    if (rps <= 500) return 'good'
    if (rps <= 800) return 'warning'
    return 'critical'
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6">
        <div className="flex items-start">
          <svg
            className="w-6 h-6 text-red-500 mt-0.5"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
              clipRule="evenodd"
            />
          </svg>
          <div className="ml-3">
            <h3 className="text-sm font-medium text-red-800">Failed to Load System Metrics</h3>
            <p className="text-sm text-red-700 mt-1">
              {error instanceof Error ? error.message : 'Unable to fetch data from the server.'}
            </p>
            <p className="text-xs text-red-600 mt-2">
              Make sure the backend is running on {process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}
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
          <p className="text-gray-600">Loading system metrics...</p>
        </div>
      </div>
    )
  }

  if (!data) {
    return null
  }

  // Transform response time data for chart
  const responseTimeData: ResponseTimeItem[] = [
    { metric: 'p50', value: data.response_time_ms.p50 },
    { metric: 'p90', value: data.response_time_ms.p90 },
    { metric: 'p99', value: data.response_time_ms.p99 },
  ]

  // Radial bar data for cache hit ratio
  const cacheData = [
    {
      name: 'Hit Ratio',
      value: data.redis_hit_ratio * 100,
      fill: getPerformanceColor(getCacheHealthLevel(data.redis_hit_ratio)).hex,
    },
  ]

  const cacheLevel = getCacheHealthLevel(data.redis_hit_ratio)
  const cacheColors = getPerformanceColor(cacheLevel)
  
  const queueLevel = getQueueHealthLevel(data.queue_pending)
  const queueColors = getPerformanceColor(queueLevel)
  
  const rpsLevel = getRpsHealthLevel(data.requests_per_second)
  const rpsColors = getPerformanceColor(rpsLevel)

  // Response time performance level
  const p99Level = getPerformanceLevel(data.response_time_ms.p99, {
    excellent: 200,
    good: 400,
    warning: 800,
  })
  const p99Colors = getPerformanceColor(p99Level)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-gray-900">?? System Metrics</h2>
          <div className="flex items-center space-x-2">
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
              <span className="text-sm text-gray-600">Live</span>
            </div>
            {autoRefresh && (
              <span className="text-xs text-gray-500 ml-4">
                Auto-refresh: {refreshInterval / 1000}s
              </span>
            )}
          </div>
        </div>

        {/* Key Metrics Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* System Uptime */}
          <div className="bg-gradient-to-br from-purple-50 to-purple-100 rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <div className="text-xs font-medium text-purple-900">System Uptime</div>
              <svg className="w-5 h-5 text-purple-600" fill="currentColor" viewBox="0 0 20 20">
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
            <div className="text-2xl font-bold text-purple-700">{data.uptime}</div>
            <div className="text-xs text-purple-600 mt-1">Since last restart</div>
          </div>

          {/* Requests per Second */}
          <div className={`rounded-lg p-4 border-2 ${rpsColors.bg} ${rpsColors.border}`}>
            <div className="flex items-center justify-between mb-2">
              <div className={`text-xs font-medium ${rpsColors.text}`}>Requests/sec</div>
              <svg className={`w-5 h-5 ${rpsColors.text}`} fill="currentColor" viewBox="0 0 20 20">
                <path d="M2 11a1 1 0 011-1h2a1 1 0 011 1v5a1 1 0 01-1 1H3a1 1 0 01-1-1v-5zM8 7a1 1 0 011-1h2a1 1 0 011 1v9a1 1 0 01-1 1H9a1 1 0 01-1-1V7zM14 4a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1h-2a1 1 0 01-1-1V4z" />
              </svg>
            </div>
            <div className={`text-2xl font-bold ${rpsColors.text}`}>
              {data.requests_per_second}
            </div>
            <div className={`text-xs mt-1 ${rpsColors.text}`}>
              {rpsLevel === 'excellent' && '? Normal load'}
              {rpsLevel === 'good' && '?? Moderate load'}
              {rpsLevel === 'warning' && '?? High load'}
              {rpsLevel === 'critical' && '?? Critical load'}
            </div>
          </div>

          {/* Queue Pending */}
          <div className={`rounded-lg p-4 border-2 ${queueColors.bg} ${queueColors.border}`}>
            <div className="flex items-center justify-between mb-2">
              <div className={`text-xs font-medium ${queueColors.text}`}>Queue Pending</div>
              <svg className={`w-5 h-5 ${queueColors.text}`} fill="currentColor" viewBox="0 0 20 20">
                <path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z" />
                <path
                  fillRule="evenodd"
                  d="M4 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v11a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm3 4a1 1 0 000 2h.01a1 1 0 100-2H7zm3 0a1 1 0 000 2h3a1 1 0 100-2h-3zm-3 4a1 1 0 100 2h.01a1 1 0 100-2H7zm3 0a1 1 0 100 2h3a1 1 0 100-2h-3z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
            <div className={`text-2xl font-bold ${queueColors.text}`}>
              {data.queue_pending}
            </div>
            <div className={`text-xs mt-1 ${queueColors.text}`}>
              {queueLevel === 'excellent' && '? Queue healthy'}
              {queueLevel === 'good' && '?? Moderate queue'}
              {queueLevel === 'warning' && '?? Queue building'}
              {queueLevel === 'critical' && '?? Queue critical'}
            </div>
          </div>

          {/* Cache Hit Ratio */}
          <div className={`rounded-lg p-4 border-2 ${cacheColors.bg} ${cacheColors.border}`}>
            <div className="flex items-center justify-between mb-2">
              <div className={`text-xs font-medium ${cacheColors.text}`}>Cache Hit Ratio</div>
              <svg className={`w-5 h-5 ${cacheColors.text}`} fill="currentColor" viewBox="0 0 20 20">
                <path d="M3 12v3c0 1.657 3.134 3 7 3s7-1.343 7-3v-3c0 1.657-3.134 3-7 3s-7-1.343-7-3z" />
                <path d="M3 7v3c0 1.657 3.134 3 7 3s7-1.343 7-3V7c0 1.657-3.134 3-7 3S3 8.657 3 7z" />
                <path d="M17 5c0 1.657-3.134 3-7 3S3 6.657 3 5s3.134-3 7-3 7 1.343 7 3z" />
              </svg>
            </div>
            <div className={`text-2xl font-bold ${cacheColors.text}`}>
              {(data.redis_hit_ratio * 100).toFixed(1)}%
            </div>
            <div className={`text-xs mt-1 ${cacheColors.text}`}>
              {cacheLevel === 'excellent' && '? Excellent caching'}
              {cacheLevel === 'good' && '?? Good caching'}
              {cacheLevel === 'warning' && '?? Cache warming'}
              {cacheLevel === 'critical' && '?? Cache issues'}
            </div>
          </div>
        </div>
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Response Time Distribution */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Response Time Distribution
          </h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={responseTimeData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="metric"
                tick={{ fontSize: 12 }}
                label={{ value: 'Percentile', position: 'insideBottom', offset: -5 }}
              />
              <YAxis
                tick={{ fontSize: 12 }}
                label={{ value: 'Time (ms)', angle: -90, position: 'insideLeft' }}
              />
              <Tooltip
                formatter={(value: number) => `${value} ms`}
                contentStyle={{
                  backgroundColor: 'rgba(255, 255, 255, 0.95)',
                  border: '1px solid #e5e7eb',
                  borderRadius: '8px',
                }}
              />
              <Bar dataKey="value" radius={[8, 8, 0, 0]}>
                {responseTimeData.map((entry, index) => {
                  const level = getPerformanceLevel(entry.value, {
                    excellent: 200,
                    good: 400,
                    warning: 800,
                  })
                  return (
                    <Cell key={`cell-${index}`} fill={getPerformanceColor(level).hex} />
                  )
                })}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <div className="mt-4 grid grid-cols-3 gap-4 text-center text-sm">
            <div>
              <div className="font-semibold text-gray-700">p50</div>
              <div className="text-2xl font-bold text-blue-600">{data.response_time_ms.p50}ms</div>
            </div>
            <div>
              <div className="font-semibold text-gray-700">p90</div>
              <div className="text-2xl font-bold text-yellow-600">{data.response_time_ms.p90}ms</div>
            </div>
            <div>
              <div className="font-semibold text-gray-700">p99</div>
              <div className={`text-2xl font-bold ${p99Colors.text}`}>{data.response_time_ms.p99}ms</div>
            </div>
          </div>
        </div>

        {/* Cache Health Radial Chart */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Redis Cache Performance
          </h3>
          <ResponsiveContainer width="100%" height={300}>
            <RadialBarChart
              cx="50%"
              cy="50%"
              innerRadius="60%"
              outerRadius="90%"
              data={cacheData}
              startAngle={180}
              endAngle={0}
            >
              <PolarAngleAxis type="number" domain={[0, 100]} angleAxisId={0} tick={false} />
              <RadialBar
                background
                dataKey="value"
                cornerRadius={10}
                fill={cacheData[0].fill}
              />
              <text
                x="50%"
                y="50%"
                textAnchor="middle"
                dominantBaseline="middle"
                className="text-4xl font-bold"
                fill={cacheColors.hex}
              >
                {(data.redis_hit_ratio * 100).toFixed(1)}%
              </text>
            </RadialBarChart>
          </ResponsiveContainer>
          <div className="mt-4 space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Cache Hits</span>
              <span className="text-sm font-semibold text-green-600">
                ~{Math.round(data.redis_hit_ratio * 100)}%
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Cache Misses</span>
              <span className="text-sm font-semibold text-red-600">
                ~{Math.round((1 - data.redis_hit_ratio) * 100)}%
              </span>
            </div>
            <div className="pt-2 border-t">
              <div className={`text-xs text-center p-2 rounded ${cacheColors.bg} ${cacheColors.text}`}>
                {cacheLevel === 'excellent' && '? Cache performing excellently'}
                {cacheLevel === 'good' && '?? Cache performing well'}
                {cacheLevel === 'warning' && '?? Cache hit rate could be improved'}
                {cacheLevel === 'critical' && '?? Cache performance needs attention'}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Performance Legend */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Performance Thresholds</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div>
            <div className="text-sm font-medium text-gray-700 mb-2">Response Time (p99)</div>
            <div className="space-y-1 text-xs">
              <div className="flex items-center">
                <div className="w-3 h-3 bg-green-500 rounded mr-2"></div>
                <span>&lt;200ms: Excellent</span>
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
            <div className="text-sm font-medium text-gray-700 mb-2">Requests/Second</div>
            <div className="space-y-1 text-xs">
              <div className="flex items-center">
                <div className="w-3 h-3 bg-green-500 rounded mr-2"></div>
                <span>&lt;200: Normal</span>
              </div>
              <div className="flex items-center">
                <div className="w-3 h-3 bg-blue-500 rounded mr-2"></div>
                <span>200-500: Moderate</span>
              </div>
              <div className="flex items-center">
                <div className="w-3 h-3 bg-yellow-500 rounded mr-2"></div>
                <span>500-800: High</span>
              </div>
              <div className="flex items-center">
                <div className="w-3 h-3 bg-red-500 rounded mr-2"></div>
                <span>&gt;800: Critical</span>
              </div>
            </div>
          </div>

          <div>
            <div className="text-sm font-medium text-gray-700 mb-2">Queue Size</div>
            <div className="space-y-1 text-xs">
              <div className="flex items-center">
                <div className="w-3 h-3 bg-green-500 rounded mr-2"></div>
                <span>&lt;10: Healthy</span>
              </div>
              <div className="flex items-center">
                <div className="w-3 h-3 bg-blue-500 rounded mr-2"></div>
                <span>10-50: Moderate</span>
              </div>
              <div className="flex items-center">
                <div className="w-3 h-3 bg-yellow-500 rounded mr-2"></div>
                <span>50-100: Building</span>
              </div>
              <div className="flex items-center">
                <div className="w-3 h-3 bg-red-500 rounded mr-2"></div>
                <span>&gt;100: Critical</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* System Status Summary */}
      <div className="bg-gradient-to-r from-blue-50 to-purple-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-start">
          <svg className="w-5 h-5 text-blue-600 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
              clipRule="evenodd"
            />
          </svg>
          <div className="ml-3 text-sm text-blue-800">
            <p className="font-medium">System Health Summary</p>
            <p className="mt-1">
              System has been running for <span className="font-semibold">{data.uptime}</span>.
              Processing <span className="font-semibold">{data.requests_per_second}</span> requests/sec
              with <span className="font-semibold">{data.response_time_ms.p99}ms</span> p99 latency.
              Cache hit ratio: <span className="font-semibold">{(data.redis_hit_ratio * 100).toFixed(1)}%</span>.
              Queue: <span className="font-semibold">{data.queue_pending}</span> pending jobs.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
