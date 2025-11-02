/**
 * Advisor Performance Component - Visualizes learning progress and accuracy
 */

'use client'

import { useState, useEffect } from 'react'
import useSWR from 'swr'
import { fetchJson } from '@/lib/api'
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

interface LearningProgress {
  total_cycles: number
  avg_accuracy: number
  accuracy_trend: number[]
  recent_improvement: number
  current_weights: {
    pattern: number
    market: number
    behavior: number
    risk: number
  }
  latest_cycle: any
}

interface FeedbackSummary {
  total_feedback: number
  helpful_count: number
  not_helpful_count: number
  accurate_count: number
  inaccurate_count: number
  accuracy_rate: number
  helpfulness_rate: number
  win_rate: number
}

export default function AdvisorPerformance() {
  const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api/v1'
  
  const { data: progress, error: progressError } = useSWR<LearningProgress>(
    '/api/advisor/learning/progress',
    () => fetchJson(`${API_BASE_URL}/advisor/learning/progress`),
    { refreshInterval: 60000 }
  )
  
  const { data: summary, error: summaryError } = useSWR<FeedbackSummary>(
    '/api/advisor/feedback/summary',
    () => fetchJson(`${API_BASE_URL}/advisor/feedback/summary?days=30`),
    { refreshInterval: 60000 }
  )

  if (progressError || summaryError) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6">
        <p className="text-red-600">Failed to load performance data</p>
      </div>
    )
  }

  if (!progress || !summary) {
    return (
      <div className="bg-white rounded-lg shadow-md p-8">
        <div className="flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mr-3"></div>
          <span className="text-gray-600">Loading performance data...</span>
        </div>
      </div>
    )
  }

  // Prepare accuracy trend data for chart
  const accuracyData = progress.accuracy_trend.map((acc, idx) => ({
    cycle: idx + 1,
    accuracy: acc * 100
  }))

  // Prepare weights data for chart
  const weightsData = [
    { sense: 'Pattern', weight: progress.current_weights.pattern * 100 },
    { sense: 'Market', weight: progress.current_weights.market * 100 },
    { sense: 'Behavior', weight: progress.current_weights.behavior * 100 },
    { sense: 'Risk', weight: progress.current_weights.risk * 100 }
  ]

  // Prepare feedback data for chart
  const feedbackData = [
    { type: 'Helpful', count: summary.helpful_count },
    { type: 'Not Helpful', count: summary.not_helpful_count },
    { type: 'Accurate', count: summary.accurate_count },
    { type: 'Inaccurate', count: summary.inaccurate_count }
  ]

  return (
    <div className="space-y-6">
      {/* Header Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-gradient-to-br from-blue-500 to-blue-600 text-white rounded-lg p-6">
          <div className="text-sm opacity-90 mb-1">Total Feedback</div>
          <div className="text-3xl font-bold">{summary.total_feedback}</div>
        </div>
        
        <div className="bg-gradient-to-br from-green-500 to-green-600 text-white rounded-lg p-6">
          <div className="text-sm opacity-90 mb-1">Accuracy Rate</div>
          <div className="text-3xl font-bold">{(summary.accuracy_rate * 100).toFixed(1)}%</div>
        </div>
        
        <div className="bg-gradient-to-br from-purple-500 to-purple-600 text-white rounded-lg p-6">
          <div className="text-sm opacity-90 mb-1">Learning Cycles</div>
          <div className="text-3xl font-bold">{progress.total_cycles}</div>
        </div>
        
        <div className={`bg-gradient-to-br ${progress.recent_improvement >= 0 ? 'from-emerald-500 to-emerald-600' : 'from-red-500 to-red-600'} text-white rounded-lg p-6`}>
          <div className="text-sm opacity-90 mb-1">Recent Improvement</div>
          <div className="text-3xl font-bold">{(progress.recent_improvement * 100).toFixed(1)}%</div>
        </div>
      </div>

      {/* Accuracy Trend Chart */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">?? Accuracy Trend Over Time</h3>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={accuracyData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="cycle" label={{ value: 'Learning Cycle', position: 'insideBottom', offset: -5 }} />
            <YAxis label={{ value: 'Accuracy (%)', angle: -90, position: 'insideLeft' }} />
            <Tooltip formatter={(value) => `${Number(value).toFixed(1)}%`} />
            <Legend />
            <Line type="monotone" dataKey="accuracy" stroke="#10B981" strokeWidth={2} name="Accuracy" />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Current Weights */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">?? Current Sense Weights</h3>
        <ResponsiveContainer width="100%" height={250}>
          <BarChart data={weightsData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="sense" />
            <YAxis label={{ value: 'Weight (%)', angle: -90, position: 'insideLeft' }} />
            <Tooltip formatter={(value) => `${Number(value).toFixed(1)}%`} />
            <Bar dataKey="weight" fill="#3B82F6" name="Weight" />
          </BarChart>
        </ResponsiveContainer>
        <div className="grid grid-cols-4 gap-4 mt-4">
          {weightsData.map((item) => (
            <div key={item.sense} className="text-center">
              <div className="text-sm text-gray-600">{item.sense}</div>
              <div className="text-xl font-bold text-gray-900">{item.weight.toFixed(1)}%</div>
            </div>
          ))}
        </div>
      </div>

      {/* Feedback Distribution */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">?? Feedback Distribution</h3>
        <ResponsiveContainer width="100%" height={250}>
          <BarChart data={feedbackData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="type" />
            <YAxis />
            <Tooltip />
            <Bar dataKey="count" fill="#8B5CF6" name="Count" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
