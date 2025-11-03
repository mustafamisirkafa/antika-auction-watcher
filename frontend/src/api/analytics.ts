/**
 * Analytics API Client (Phase 17)
 */
import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface AutoBidMetrics {
  active_bids: number;
  sla_p95: number;
  last_bid_ms: number;
}

export interface ValuationMetrics {
  avg_market_value: number;
  trend_delta: number;
  demand_score: number;
}

export interface SellerTrustMetrics {
  trusted: number;
  medium: number;
  risky: number;
}

export interface UserPrefsMetrics {
  allowlist: number;
  blocklist: number;
}

export interface SystemHealthMetrics {
  redis_latency_ms: number;
  cache_hit_ratio: number;
  db_latency_ms: number;
}

export interface AnalyticsOverview {
  autobid: AutoBidMetrics;
  valuation: ValuationMetrics;
  sellers: SellerTrustMetrics;
  user_prefs: UserPrefsMetrics;
  system: SystemHealthMetrics;
  timestamp: string;
}

/**
 * Get analytics overview
 * Aggregated metrics from all system components
 */
export async function getAnalyticsOverview(token: string): Promise<AnalyticsOverview> {
  const response = await axios.get(`${API_BASE_URL}/api/analytics/overview`, {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });
  return response.data;
}
