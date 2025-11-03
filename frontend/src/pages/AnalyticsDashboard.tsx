/**
 * Analytics Dashboard Page (Phase 17)
 * Single-screen monitoring view with 5 widgets
 */
import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { getAnalyticsOverview } from '@/api/analytics';
import { useAuth } from '@/hooks/useAuth';
import { useTranslation, formatDate } from '@/lib/i18n';
import { AutoBidCard } from '@/components/dashboard/AutoBidCard';
import { ValuationChart } from '@/components/dashboard/ValuationChart';
import { SellerTrustPie } from '@/components/dashboard/SellerTrustPie';
import { UserPrefsBars } from '@/components/dashboard/UserPrefsBars';
import { SystemHealthStatus } from '@/components/dashboard/SystemHealthStatus';

export default function AnalyticsDashboard() {
  const { token } = useAuth();
  const { t } = useTranslation();
  
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['analytics-overview'],
    queryFn: async () => {
      if (!token) throw new Error('Not authenticated');
      return getAnalyticsOverview(token);
    },
    enabled: !!token,
    refetchInterval: 10000, // Refresh every 10 seconds
    staleTime: 5000,
  });
  
  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-current border-r-transparent" />
          <p className="mt-4 text-sm text-gray-500">{t('common.loading')}</p>
        </div>
      </div>
    );
  }
  
  if (error) {
    return (
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="rounded-md bg-red-50 p-4">
          <h3 className="text-sm font-medium text-red-800">{t('common.error')}</h3>
          <div className="mt-2 text-sm text-red-700">
            {error instanceof Error ? error.message : t('analytics.error_loading')}
          </div>
          <button
            onClick={() => refetch()}
            className="mt-3 rounded-md bg-red-100 px-3 py-1 text-sm font-medium text-red-800 hover:bg-red-200"
          >
            {t('common.refresh')}
          </button>
        </div>
      </div>
    );
  }
  
  if (!data) {
    return null;
  }
  
  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">{t('analytics.title')}</h1>
            <p className="mt-2 text-sm text-gray-600">{t('analytics.description')}</p>
          </div>
          <div className="text-right">
            <p className="text-xs text-gray-500">{t('analytics.last_updated')}</p>
            <p className="text-sm font-medium text-gray-900">
              {formatDate(data.timestamp, true)}
            </p>
          </div>
        </div>
      </div>
      
      {/* Widgets Grid */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2 xl:grid-cols-3">
        {/* AutoBid Card - Full width on mobile, spans 1 col on lg+  */}
        <div className="xl:col-span-1">
          <AutoBidCard data={data.autobid} />
        </div>
        
        {/* Valuation Chart - Full width on mobile, spans 2 cols on xl */}
        <div className="lg:col-span-2 xl:col-span-2">
          <ValuationChart data={data.valuation} />
        </div>
        
        {/* Seller Trust Pie */}
        <div className="xl:col-span-1">
          <SellerTrustPie data={data.sellers} />
        </div>
        
        {/* User Prefs Bars */}
        <div className="xl:col-span-1">
          <UserPrefsBars data={data.user_prefs} />
        </div>
        
        {/* System Health - Full width on mobile, spans 1 col on lg+ */}
        <div className="xl:col-span-1">
          <SystemHealthStatus data={data.system} />
        </div>
      </div>
      
      {/* Footer Info */}
      <div className="mt-8 rounded-lg border border-gray-200 bg-gray-50 p-4">
        <div className="flex items-center">
          <svg
            className="h-5 w-5 text-gray-400"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path
              fillRule="evenodd"
              d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
              clipRule="evenodd"
            />
          </svg>
          <p className="ml-3 text-sm text-gray-600">
            {t('analytics.auto_refresh_info')}
          </p>
        </div>
      </div>
    </div>
  );
}
