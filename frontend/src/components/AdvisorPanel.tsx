/**
 * AI Advisor Panel Component
 * Displays AI-powered bidding recommendations with multi-sense analysis
 */

'use client'

import { useState, useEffect } from 'react'
import { fetchJson } from '@/lib/api'

export interface AdvisorRecommendation {
  item_id: string
  recommendation: 'strong_buy' | 'buy' | 'watch' | 'skip' | 'avoid'
  confidence: number
  suggested_max_bid?: number
  reasoning: string[]
  risk_level: 'low' | 'medium' | 'high' | 'very_high'
  pattern_sense: SenseScore
  market_sense: SenseScore
  behavior_sense: SenseScore
  risk_sense: SenseScore
  timestamp: string
  expires_at: string
}

export interface SenseScore {
  score: number
  confidence: number
  reasoning: string
  factors: Record<string, number>
}

interface AdvisorPanelProps {
  itemId: string
  compact?: boolean
  onFeedback?: (feedbackType: string) => void
}

export default function AdvisorPanel({ itemId, compact = false, onFeedback }: AdvisorPanelProps) {
  const [recommendation, setRecommendation] = useState<AdvisorRecommendation | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showDetails, setShowDetails] = useState(false)

  useEffect(() => {
    loadRecommendation()
  }, [itemId])

  const loadRecommendation = async () => {
    try {
      setLoading(true)
      setError(null)
      
      const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api/v1'
      const data = await fetchJson<AdvisorRecommendation>(
        `${API_BASE_URL}/advisor/suggest/${itemId}`
      )
      
      setRecommendation(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load recommendation')
    } finally {
      setLoading(false)
    }
  }

  const getRecommendationStyle = (level: string) => {
    const styles = {
      strong_buy: {
        bg: 'bg-gradient-to-r from-green-500 to-green-600',
        text: 'text-white',
        icon: '??',
        label: 'Strong Buy'
      },
      buy: {
        bg: 'bg-gradient-to-r from-blue-500 to-blue-600',
        text: 'text-white',
        icon: '?',
        label: 'Buy'
      },
      watch: {
        bg: 'bg-gradient-to-r from-yellow-400 to-yellow-500',
        text: 'text-gray-900',
        icon: '??',
        label: 'Watch'
      },
      skip: {
        bg: 'bg-gradient-to-r from-gray-400 to-gray-500',
        text: 'text-white',
        icon: '??',
        label: 'Skip'
      },
      avoid: {
        bg: 'bg-gradient-to-r from-red-500 to-red-600',
        text: 'text-white',
        icon: '?',
        label: 'Avoid'
      }
    }
    return styles[level as keyof typeof styles] || styles.watch
  }

  const getRiskStyle = (level: string) => {
    const styles = {
      low: { color: 'text-green-600', bg: 'bg-green-100', label: 'Low Risk' },
      medium: { color: 'text-yellow-600', bg: 'bg-yellow-100', label: 'Medium Risk' },
      high: { color: 'text-orange-600', bg: 'bg-orange-100', label: 'High Risk' },
      very_high: { color: 'text-red-600', bg: 'bg-red-100', label: 'Very High Risk' }
    }
    return styles[level as keyof typeof styles] || styles.medium
  }

  const handleFeedback = (type: string) => {
    if (onFeedback) {
      onFeedback(type)
    }
  }

  if (loading) {
    return (
      <div className={`${compact ? 'p-3' : 'p-4'} bg-gray-50 rounded-lg border border-gray-200`}>
        <div className="flex items-center justify-center">
          <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-primary-600 mr-2"></div>
          <span className="text-sm text-gray-600">Analyzing...</span>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className={`${compact ? 'p-3' : 'p-4'} bg-red-50 rounded-lg border border-red-200`}>
        <div className="flex items-center text-sm text-red-600">
          <svg className="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
              clipRule="evenodd"
            />
          </svg>
          {error}
        </div>
      </div>
    )
  }

  if (!recommendation) {
    return null
  }

  const recStyle = getRecommendationStyle(recommendation.recommendation)
  const riskStyle = getRiskStyle(recommendation.risk_level)

  // Compact version for auction cards
  if (compact) {
    return (
      <div className="space-y-2">
        <div className={`${recStyle.bg} ${recStyle.text} rounded-lg p-3`}>
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center">
              <span className="text-lg mr-2">{recStyle.icon}</span>
              <span className="font-semibold text-sm">{recStyle.label}</span>
            </div>
            <div className="text-xs opacity-90">
              {(recommendation.confidence * 100).toFixed(0)}% confident
            </div>
          </div>
          
          {recommendation.suggested_max_bid && (
            <div className="text-sm opacity-95">
              Max bid: ${recommendation.suggested_max_bid.toFixed(2)}
            </div>
          )}
        </div>

        {recommendation.reasoning.length > 0 && (
          <div className="text-xs text-gray-600 space-y-1">
            {recommendation.reasoning.slice(0, 2).map((reason, idx) => (
              <div key={idx} className="flex items-start">
                <span className="mr-1">?</span>
                <span>{reason}</span>
              </div>
            ))}
          </div>
        )}

        <button
          onClick={() => setShowDetails(!showDetails)}
          className="text-xs text-primary-600 hover:text-primary-700 font-medium"
        >
          {showDetails ? 'Hide details' : 'Show full analysis'}
        </button>

        {showDetails && (
          <div className="space-y-2 pt-2 border-t border-gray-200">
            <div className="grid grid-cols-2 gap-2 text-xs">
              <SenseBar label="Pattern" score={recommendation.pattern_sense.score} />
              <SenseBar label="Market" score={recommendation.market_sense.score} />
              <SenseBar label="Behavior" score={recommendation.behavior_sense.score} />
              <SenseBar label="Risk" score={recommendation.risk_sense.score} />
            </div>
            
            <div className={`${riskStyle.bg} ${riskStyle.color} px-2 py-1 rounded text-xs text-center font-medium`}>
              {riskStyle.label}
            </div>

            {/* Feedback buttons */}
            <div className="flex space-x-2">
              <button
                onClick={() => handleFeedback('helpful')}
                className="flex-1 text-xs bg-green-100 text-green-700 hover:bg-green-200 px-2 py-1 rounded"
              >
                ?? Helpful
              </button>
              <button
                onClick={() => handleFeedback('not_helpful')}
                className="flex-1 text-xs bg-red-100 text-red-700 hover:bg-red-200 px-2 py-1 rounded"
              >
                ?? Not Helpful
              </button>
            </div>
          </div>
        )}
      </div>
    )
  }

  // Full version for standalone display
  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-bold text-gray-900">?? AI Advisor</h3>
        <button
          onClick={loadRecommendation}
          className="text-sm text-primary-600 hover:text-primary-700"
        >
          ?? Refresh
        </button>
      </div>

      {/* Main Recommendation */}
      <div className={`${recStyle.bg} ${recStyle.text} rounded-lg p-4 mb-4`}>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center">
            <span className="text-3xl mr-3">{recStyle.icon}</span>
            <div>
              <div className="text-xl font-bold">{recStyle.label}</div>
              <div className="text-sm opacity-90">
                Confidence: {(recommendation.confidence * 100).toFixed(1)}%
              </div>
            </div>
          </div>
          
          {recommendation.suggested_max_bid && (
            <div className="text-right">
              <div className="text-sm opacity-90">Suggested Max Bid</div>
              <div className="text-2xl font-bold">
                ${recommendation.suggested_max_bid.toFixed(2)}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Risk Level */}
      <div className={`${riskStyle.bg} ${riskStyle.color} rounded-lg px-4 py-3 mb-4 text-center font-semibold`}>
        {riskStyle.label}
      </div>

      {/* Reasoning */}
      <div className="mb-4">
        <h4 className="font-semibold text-gray-900 mb-2">Key Insights</h4>
        <div className="space-y-2">
          {recommendation.reasoning.map((reason, idx) => (
            <div key={idx} className="flex items-start text-sm text-gray-700">
              <span className="mr-2">?</span>
              <span>{reason}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Sense Scores */}
      <div className="space-y-3 mb-4">
        <h4 className="font-semibold text-gray-900">Analysis Breakdown</h4>
        
        <div className="space-y-2">
          <SenseBarFull
            label="?? Pattern Sense"
            score={recommendation.pattern_sense.score}
            confidence={recommendation.pattern_sense.confidence}
            reasoning={recommendation.pattern_sense.reasoning}
          />
          <SenseBarFull
            label="?? Market Sense"
            score={recommendation.market_sense.score}
            confidence={recommendation.market_sense.confidence}
            reasoning={recommendation.market_sense.reasoning}
          />
          <SenseBarFull
            label="?? Behavior Sense"
            score={recommendation.behavior_sense.score}
            confidence={recommendation.behavior_sense.confidence}
            reasoning={recommendation.behavior_sense.reasoning}
          />
          <SenseBarFull
            label="?? Risk Sense"
            score={recommendation.risk_sense.score}
            confidence={recommendation.risk_sense.confidence}
            reasoning={recommendation.risk_sense.reasoning}
          />
        </div>
      </div>

      {/* Feedback */}
      <div className="border-t border-gray-200 pt-4">
        <div className="text-sm text-gray-600 mb-2">Was this recommendation helpful?</div>
        <div className="flex space-x-2">
          <button
            onClick={() => handleFeedback('helpful')}
            className="flex-1 bg-green-100 text-green-700 hover:bg-green-200 px-4 py-2 rounded-lg font-medium text-sm"
          >
            ?? Yes, Helpful
          </button>
          <button
            onClick={() => handleFeedback('not_helpful')}
            className="flex-1 bg-red-100 text-red-700 hover:bg-red-200 px-4 py-2 rounded-lg font-medium text-sm"
          >
            ?? Not Helpful
          </button>
        </div>
      </div>

      {/* Timestamp */}
      <div className="mt-4 text-xs text-gray-500 text-center">
        Generated {new Date(recommendation.timestamp).toLocaleTimeString()}
      </div>
    </div>
  )
}

// Helper Components
function SenseBar({ label, score }: { label: string; score: number }) {
  const percentage = Math.round(score * 100)
  const colorClass = score > 0.7 ? 'bg-green-500' : score > 0.4 ? 'bg-yellow-500' : 'bg-red-500'
  
  return (
    <div>
      <div className="flex justify-between text-xs text-gray-600 mb-1">
        <span>{label}</span>
        <span>{percentage}%</span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2">
        <div
          className={`${colorClass} h-2 rounded-full transition-all duration-300`}
          style={{ width: `${percentage}%` }}
        ></div>
      </div>
    </div>
  )
}

function SenseBarFull({
  label,
  score,
  confidence,
  reasoning
}: {
  label: string
  score: number
  confidence: number
  reasoning: string
}) {
  const percentage = Math.round(score * 100)
  const colorClass = score > 0.7 ? 'bg-green-500' : score > 0.4 ? 'bg-yellow-500' : 'bg-red-500'
  
  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span className="font-medium text-gray-700">{label}</span>
        <span className="text-gray-600">
          {percentage}% (confidence: {Math.round(confidence * 100)}%)
        </span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-3 mb-1">
        <div
          className={`${colorClass} h-3 rounded-full transition-all duration-300`}
          style={{ width: `${percentage}%` }}
        ></div>
      </div>
      <div className="text-xs text-gray-600">{reasoning}</div>
    </div>
  )
}
