/**
 * Learning Insights Panel - Displays AI model performance metrics
 */

'use client'

import { useState, useEffect } from 'react'
import useSWR from 'swr'
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
} from 'recharts'
import {
  LearningMetrics,
  CategoryAccuracyItem,
  ConfidenceTrendItem,
  LearningInsightsProps,
} from '@/types/metrics'
import { fetchLearningMetrics } from '@/lib/api'

export default function LearningInsights({
  autoRefresh = true,
  refreshInterval = 60000, // 60 seconds
}: LearningInsightsProps) {
  const [previousAccuracy, setPreviousAccuracy] = useState<number | null>(null)
  const [isImproving, setIsImproving] = useState(false)

  // Fetch data with SWR
  const { data, error, isLoading } = useSWR<LearningMetrics>(
    '/api/learning/metrics',
    fetchLearningMetrics,
    {
      refreshInterval: autoRefresh ? refreshInterval : 0,
      revalidateOnFocus: false,
      revalidateOnReconnect: true,
    }
  )

  // Track accuracy improvements
  useEffect(() => {
    if (data && data.overall_accuracy) {
      if (previousAccuracy !== null) {
        const improvement = data.overall_accuracy - previousAccuracy
        setIsImproving(improvement >= 3)
      }
      setPreviousAccuracy(data.overall_accuracy)
    }
  }, [data?.overall_accuracy])

  const getEfficiencyColor = (efficiency: number) => {
    if (efficiency >= 0.8) return { text: 'text-green-600', bg: 'bg-green-100', border: 'border-green-300' }
    if (efficiency >= 0.6) return { text: 'text-yellow-600', bg: 'bg-yellow-100', border: 'border-yellow-300' }
    return { text: 'text-red-600', bg: 'bg-red-100', border: 'border-red-300' }
  }

  const getAccuracyColor = (accuracy: number) => {
    if (accuracy >= 80) return '#10b981' // green
    if (accuracy >= 60) return '#f59e0b' // yellow
    return '#ef4444' // red
  }

  const formatTimestamp = (timestamp: string) => {
    try {
      const date = new Date(timestamp)
      return date.toLocaleString('tr-TR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    } catch {
      return timestamp
    }
  }

  // Transform data for charts
  const categoryData: CategoryAccuracyItem[] = data?.category_accuracy
    ? Object.entries(data.category_accuracy)
        .map(([category, accuracy]) => ({
          category: category.charAt(0).toUpperCase() + category.slice(1),
          accuracy,
        }))
        .sort((a, b) => b.accuracy - a.accuracy)
    : []

  const confidenceTrendData: ConfidenceTrendItem[] = data?.confidence_trend
    ? data.confidence_trend.map((confidence, index) => ({
        index: index + 1,
        confidence: confidence * 100,
      }))
    : []

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
            <h3 className="text-sm font-medium text-red-800">Failed to Load Learning Metrics</h3>
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
          <p className="text-gray-600">Loading learning metrics...</p>
        </div>
      </div>
    )
  }

  if (!data) {
    return null
  }

  const efficiencyColors = getEfficiencyColor(data.learning_efficiency)

  return (
    <div className="space-y-6">
      {/* Header with Key Metrics */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-gray-900">?? Learning Insights</h2>
          <div className="flex items-center space-x-2">
            {isImproving && (
              <span className="px-3 py-1 bg-green-100 text-green-700 text-sm font-medium rounded-full flex items-center animate-pulse">
                <svg className="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                  <path
                    fillRule="evenodd"
                    d="M12 7a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0V8.414l-4.293 4.293a1 1 0 01-1.414 0L8 10.414l-4.293 4.293a1 1 0 01-1.414-1.414l5-5a1 1 0 011.414 0L11 10.586 14.586 7H12z"
                    clipRule="evenodd"
                  />
                </svg>
                Model Improving
              </span>
            )}
            {autoRefresh && (
              <span className="text-xs text-gray-500">
                Auto-refresh: {refreshInterval / 1000}s
              </span>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Overall Accuracy */}
          <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-lg p-6">
            <div className="text-sm font-medium text-blue-900 mb-2">Overall Accuracy</div>
            <div className="text-4xl font-bold text-blue-700">
              {data.overall_accuracy.toFixed(1)}%
            </div>
            <div className="mt-2">
              <div className="w-full bg-blue-200 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all duration-500"
                  style={{ width: `${data.overall_accuracy}%` }}
                />
              </div>
            </div>
          </div>

          {/* Learning Efficiency */}
          <div className={`rounded-lg p-6 border-2 ${efficiencyColors.bg} ${efficiencyColors.border}`}>
            <div className={`text-sm font-medium mb-2 ${efficiencyColors.text}`}>
              Learning Efficiency
            </div>
            <div className={`text-4xl font-bold ${efficiencyColors.text}`}>
              {(data.learning_efficiency * 100).toFixed(1)}%
            </div>
            <div className="mt-2 text-xs text-gray-600">
              {data.learning_efficiency >= 0.8 && '? Excellent learning rate'}
              {data.learning_efficiency >= 0.6 && data.learning_efficiency < 0.8 && '?? Moderate learning rate'}
              {data.learning_efficiency < 0.6 && '? Needs improvement'}
            </div>
          </div>

          {/* Last Training */}
          <div className="bg-gradient-to-br from-purple-50 to-purple-100 rounded-lg p-6">
            <div className="text-sm font-medium text-purple-900 mb-2">Last Training</div>
            <div className="text-lg font-semibold text-purple-700">
              {formatTimestamp(data.last_training)}
            </div>
            <div className="mt-2 text-xs text-purple-600">
              <div className="flex items-center">
                <svg className="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z"
                    clipRule="evenodd"
                  />
                </svg>
                Model last retrained
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Category Accuracy Bar Chart */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Category Performance
          </h3>
          {categoryData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={categoryData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="category"
                  angle={-45}
                  textAnchor="end"
                  height={80}
                  tick={{ fontSize: 12 }}
                />
                <YAxis
                  domain={[0, 100]}
                  tick={{ fontSize: 12 }}
                  label={{ value: 'Accuracy (%)', angle: -90, position: 'insideLeft' }}
                />
                <Tooltip
                  formatter={(value: number) => `${value.toFixed(1)}%`}
                  contentStyle={{
                    backgroundColor: 'rgba(255, 255, 255, 0.95)',
                    border: '1px solid #e5e7eb',
                    borderRadius: '8px',
                  }}
                />
                <Bar dataKey="accuracy" radius={[8, 8, 0, 0]}>
                  {categoryData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={getAccuracyColor(entry.accuracy)} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-[300px] text-gray-500">
              No category data available
            </div>
          )}
          <div className="mt-4 flex items-center justify-center space-x-4 text-xs">
            <div className="flex items-center">
              <div className="w-3 h-3 bg-green-500 rounded mr-1"></div>
              <span className="text-gray-600">?80% Excellent</span>
            </div>
            <div className="flex items-center">
              <div className="w-3 h-3 bg-yellow-500 rounded mr-1"></div>
              <span className="text-gray-600">60-80% Good</span>
            </div>
            <div className="flex items-center">
              <div className="w-3 h-3 bg-red-500 rounded mr-1"></div>
              <span className="text-gray-600">&lt;60% Needs Work</span>
            </div>
          </div>
        </div>

        {/* Confidence Trend Line Chart */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Confidence Trend
          </h3>
          {confidenceTrendData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={confidenceTrendData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="index"
                  label={{ value: 'Sample', position: 'insideBottom', offset: -5 }}
                  tick={{ fontSize: 12 }}
                />
                <YAxis
                  domain={[0, 100]}
                  tick={{ fontSize: 12 }}
                  label={{ value: 'Confidence (%)', angle: -90, position: 'insideLeft' }}
                />
                <Tooltip
                  formatter={(value: number) => `${value.toFixed(1)}%`}
                  contentStyle={{
                    backgroundColor: 'rgba(255, 255, 255, 0.95)',
                    border: '1px solid #e5e7eb',
                    borderRadius: '8px',
                  }}
                />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="confidence"
                  stroke="#3b82f6"
                  strokeWidth={3}
                  dot={{ fill: '#3b82f6', r: 4 }}
                  activeDot={{ r: 6 }}
                  name="Confidence"
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-[300px] text-gray-500">
              No trend data available
            </div>
          )}
          <div className="mt-4 text-center text-sm text-gray-600">
            {confidenceTrendData.length > 1 && (
              <span>
                Trend:{' '}
                {confidenceTrendData[confidenceTrendData.length - 1].confidence >
                confidenceTrendData[0].confidence ? (
                  <span className="text-green-600 font-semibold">? Improving</span>
                ) : (
                  <span className="text-red-600 font-semibold">? Declining</span>
                )}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Summary */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-start">
          <svg className="w-5 h-5 text-blue-600 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
              clipRule="evenodd"
            />
          </svg>
          <div className="ml-3 text-sm text-blue-800">
            <p className="font-medium">Model Status</p>
            <p className="mt-1">
              The AI model is currently operating with{' '}
              <span className="font-semibold">{data.overall_accuracy.toFixed(1)}%</span> accuracy
              across {categoryData.length} categories. Learning efficiency is at{' '}
              <span className="font-semibold">
                {(data.learning_efficiency * 100).toFixed(1)}%
              </span>
              .
              {isImproving && (
                <span className="text-green-700 font-semibold">
                  {' '}Model accuracy has improved by 3%+ since last check!
                </span>
              )}
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
