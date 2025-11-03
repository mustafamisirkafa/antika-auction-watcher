/**
 * AutoBid Status Card Component (Phase 17)
 */
import React from 'react';
import { AutoBidMetrics } from '@/api/analytics';
import { useTranslation } from '@/lib/i18n';

interface AutoBidCardProps {
  data: AutoBidMetrics;
}

export function AutoBidCard({ data }: AutoBidCardProps) {
  const { t } = useTranslation();
  
  const getSLAStatus = (sla: number) => {
    if (sla <= 2.5) return { color: 'text-green-600', bg: 'bg-green-50', label: t('analytics.autobid.excellent') };
    if (sla <= 3.0) return { color: 'text-yellow-600', bg: 'bg-yellow-50', label: t('analytics.autobid.good') };
    return { color: 'text-red-600', bg: 'bg-red-50', label: t('analytics.autobid.slow') };
  };
  
  const slaStatus = getSLAStatus(data.sla_p95);
  
  return (
    <div className="overflow-hidden rounded-lg bg-white shadow">
      <div className="p-5">
        <div className="flex items-center">
          <div className="flex-shrink-0">
            <svg
              className="h-6 w-6 text-indigo-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M13 10V3L4 14h7v7l9-11h-7z"
              />
            </svg>
          </div>
          <div className="ml-5 w-0 flex-1">
            <dl>
              <dt className="truncate text-sm font-medium text-gray-500">
                {t('analytics.autobid.title')}
              </dt>
              <dd className="mt-1 flex items-baseline">
                <div className="text-2xl font-semibold text-gray-900">
                  {data.active_bids}
                </div>
                <div className="ml-2 text-sm text-gray-500">
                  {t('analytics.autobid.active')}
                </div>
              </dd>
            </dl>
          </div>
        </div>
        
        <div className="mt-4 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-500">{t('analytics.autobid.sla_p95')}</span>
            <span className={`text-sm font-semibold ${slaStatus.color}`}>
              {data.sla_p95.toFixed(2)}s
            </span>
          </div>
          
          <div className={`rounded-md p-2 ${slaStatus.bg}`}>
            <div className="flex">
              <div className="ml-3">
                <p className={`text-sm font-medium ${slaStatus.color}`}>
                  {slaStatus.label}
                </p>
              </div>
            </div>
          </div>
          
          <div className="flex items-center justify-between border-t pt-2">
            <span className="text-xs text-gray-500">{t('analytics.autobid.last_bid')}</span>
            <span className="text-xs font-medium text-gray-900">
              {data.last_bid_ms}ms
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
