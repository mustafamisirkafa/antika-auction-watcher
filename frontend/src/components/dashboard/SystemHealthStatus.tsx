/**
 * System Health Status Component (Phase 17)
 */
import React from 'react';
import { SystemHealthMetrics } from '@/api/analytics';
import { useTranslation } from '@/lib/i18n';

interface SystemHealthStatusProps {
  data: SystemHealthMetrics;
}

export function SystemHealthStatus({ data }: SystemHealthStatusProps) {
  const { t } = useTranslation();
  
  const getLatencyStatus = (latency: number, threshold: number) => {
    if (latency <= threshold * 0.5) return { color: 'text-green-600', bg: 'bg-green-100', status: t('analytics.system.excellent') };
    if (latency <= threshold) return { color: 'text-yellow-600', bg: 'bg-yellow-100', status: t('analytics.system.good') };
    return { color: 'text-red-600', bg: 'bg-red-100', status: t('analytics.system.slow') };
  };
  
  const getCacheStatus = (ratio: number) => {
    if (ratio >= 0.9) return { color: 'text-green-600', bg: 'bg-green-100', status: t('analytics.system.excellent') };
    if (ratio >= 0.7) return { color: 'text-yellow-600', bg: 'bg-yellow-100', status: t('analytics.system.good') };
    return { color: 'text-red-600', bg: 'bg-red-100', status: t('analytics.system.poor') };
  };
  
  const redisStatus = getLatencyStatus(data.redis_latency_ms, 10);
  const dbStatus = getLatencyStatus(data.db_latency_ms, 50);
  const cacheStatus = getCacheStatus(data.cache_hit_ratio);
  
  return (
    <div className="overflow-hidden rounded-lg bg-white shadow">
      <div className="p-5">
        <h3 className="text-lg font-medium text-gray-900">
          {t('analytics.system.title')}
        </h3>
        
        <div className="mt-4 space-y-4">
          {/* Redis Latency */}
          <div>
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-600">
                {t('analytics.system.redis_latency')}
              </span>
              <span className="text-sm font-semibold text-gray-900">
                {data.redis_latency_ms}ms
              </span>
            </div>
            <div className="mt-2">
              <div className={`rounded-md px-3 py-2 ${redisStatus.bg}`}>
                <p className={`text-sm font-medium ${redisStatus.color}`}>
                  {redisStatus.status}
                </p>
              </div>
            </div>
          </div>
          
          {/* Cache Hit Ratio */}
          <div>
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-600">
                {t('analytics.system.cache_hit_ratio')}
              </span>
              <span className="text-sm font-semibold text-gray-900">
                {(data.cache_hit_ratio * 100).toFixed(1)}%
              </span>
            </div>
            <div className="mt-2">
              <div className="h-2 w-full overflow-hidden rounded-full bg-gray-200">
                <div
                  className="h-2 bg-indigo-600"
                  style={{ width: `${data.cache_hit_ratio * 100}%` }}
                />
              </div>
            </div>
            <div className="mt-2">
              <div className={`rounded-md px-3 py-2 ${cacheStatus.bg}`}>
                <p className={`text-sm font-medium ${cacheStatus.color}`}>
                  {cacheStatus.status}
                </p>
              </div>
            </div>
          </div>
          
          {/* DB Latency */}
          <div>
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-600">
                {t('analytics.system.db_latency')}
              </span>
              <span className="text-sm font-semibold text-gray-900">
                {data.db_latency_ms}ms
              </span>
            </div>
            <div className="mt-2">
              <div className={`rounded-md px-3 py-2 ${dbStatus.bg}`}>
                <p className={`text-sm font-medium ${dbStatus.color}`}>
                  {dbStatus.status}
                </p>
              </div>
            </div>
          </div>
        </div>
        
        <div className="mt-4 border-t pt-3">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <svg
                className="h-5 w-5 text-green-500"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
            <p className="ml-3 text-sm font-medium text-gray-900">
              {t('analytics.system.all_systems_operational')}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
