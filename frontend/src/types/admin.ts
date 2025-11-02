/**
 * Type definitions for admin console
 */

export interface SystemMetrics {
  uptime: string
  requests_per_second: number
  response_time_ms: {
    p50: number
    p90: number
    p99: number
  }
  redis_hit_ratio: number
  queue_pending: number
}

export interface LearningLogEntry {
  timestamp: string
  category: string
  samples: number
  accuracy_before: number
  accuracy_after: number
  notes?: string
}

export interface LearningLogsResponse {
  logs: LearningLogEntry[]
  total: number
  limit: number
  offset: number
}

export interface ExportParams {
  from?: string
  to?: string
  category?: string
}

export type HealthLevel = 'excellent' | 'good' | 'warning' | 'critical'

export interface HealthThreshold {
  level: HealthLevel
  color: string
  bgColor: string
  borderColor: string
}
