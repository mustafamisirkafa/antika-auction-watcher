/**
 * Seller Trust Distribution Pie Chart (Phase 17)
 */
import React from 'react';
import { SellerTrustMetrics } from '@/api/analytics';
import { useTranslation } from '@/lib/i18n';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';

interface SellerTrustPieProps {
  data: SellerTrustMetrics;
}

const COLORS = {
  trusted: '#10B981',
  medium: '#F59E0B',
  risky: '#EF4444',
};

export function SellerTrustPie({ data }: SellerTrustPieProps) {
  const { t } = useTranslation();
  
  const chartData = [
    { name: t('analytics.seller_trust.trusted'), value: data.trusted, color: COLORS.trusted },
    { name: t('analytics.seller_trust.medium'), value: data.medium, color: COLORS.medium },
    { name: t('analytics.seller_trust.risky'), value: data.risky, color: COLORS.risky },
  ].filter(item => item.value > 0);
  
  const total = data.trusted + data.medium + data.risky;
  
  if (total === 0) {
    return (
      <div className="overflow-hidden rounded-lg bg-white shadow">
        <div className="p-5">
          <h3 className="text-lg font-medium text-gray-900">
            {t('analytics.seller_trust.title')}
          </h3>
          <div className="mt-8 text-center text-sm text-gray-500">
            {t('analytics.seller_trust.no_data')}
          </div>
        </div>
      </div>
    );
  }
  
  return (
    <div className="overflow-hidden rounded-lg bg-white shadow">
      <div className="p-5">
        <h3 className="text-lg font-medium text-gray-900">
          {t('analytics.seller_trust.title')}
        </h3>
        
        <div className="mt-4 h-48">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ percent }) => `${(percent * 100).toFixed(0)}%`}
                outerRadius={60}
                fill="#8884d8"
                dataKey="value"
              >
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>
        
        <div className="mt-4 space-y-2 border-t pt-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <div className="h-3 w-3 rounded-full bg-green-500" />
              <span className="ml-2 text-sm text-gray-600">
                {t('analytics.seller_trust.trusted')}
              </span>
            </div>
            <span className="text-sm font-medium text-gray-900">{data.trusted}</span>
          </div>
          
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <div className="h-3 w-3 rounded-full bg-yellow-500" />
              <span className="ml-2 text-sm text-gray-600">
                {t('analytics.seller_trust.medium')}
              </span>
            </div>
            <span className="text-sm font-medium text-gray-900">{data.medium}</span>
          </div>
          
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <div className="h-3 w-3 rounded-full bg-red-500" />
              <span className="ml-2 text-sm text-gray-600">
                {t('analytics.seller_trust.risky')}
              </span>
            </div>
            <span className="text-sm font-medium text-gray-900">{data.risky}</span>
          </div>
          
          <div className="flex items-center justify-between border-t pt-2">
            <span className="text-sm font-medium text-gray-600">
              {t('analytics.seller_trust.total')}
            </span>
            <span className="text-sm font-semibold text-gray-900">{total}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
