/**
 * Type definitions for learning and system metrics
 */

export interface LearningMetrics {
  overall_accuracy: number
  learning_efficiency: number
  confidence_trend: number[]
  category_accuracy: Record<string, number>
  last_training: string
}

export interface SystemMetrics {
  uptime: string
  redis_hit_ratio: number
  requests_per_second: number
  response_time_ms: {
    p50: number
    p90: number
    p99: number
  }
  queue_pending: number
}

export interface CategoryAccuracyItem {
  category: string
  accuracy: number
}

export interface ConfidenceTrendItem {
  index: number
  confidence: number
}

export interface ResponseTimeItem {
  metric: string
  value: number
}

export interface LearningInsightsProps {
  autoRefresh?: boolean
  refreshInterval?: number
}

export interface MetricsPanelProps {
  autoRefresh?: boolean
  refreshInterval?: number
}

export type PerformanceLevel = 'excellent' | 'good' | 'warning' | 'critical'

export interface PerformanceIndicator {
  level: PerformanceLevel
  color: string
  bgColor: string
  label: string
}
