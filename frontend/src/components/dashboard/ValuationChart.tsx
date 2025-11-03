/**
 * Valuation Chart Component (Phase 17)
 */
import React from 'react';
import { ValuationMetrics } from '@/api/analytics';
import { useTranslation, formatCurrency } from '@/lib/i18n';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface ValuationChartProps {
  data: ValuationMetrics;
}

export function ValuationChart({ data }: ValuationChartProps) {
  const { t } = useTranslation();
  
  // Generate trend line data (simplified visualization)
  const trendData = [
    { time: t('analytics.valuation.previous'), value: data.avg_market_value * (1 - data.trend_delta) },
    { time: t('analytics.valuation.current'), value: data.avg_market_value },
  ];
  
  const getTrendColor = () => {
    if (data.trend_delta > 0.05) return 'text-green-600';
    if (data.trend_delta < -0.05) return 'text-red-600';
    return 'text-gray-600';
  };
  
  const getTrendIcon = () => {
    if (data.trend_delta > 0) {
      return (
        <svg className="h-5 w-5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M5.293 9.707a1 1 0 010-1.414l4-4a1 1 0 011.414 0l4 4a1 1 0 01-1.414 1.414L11 7.414V15a1 1 0 11-2 0V7.414L6.707 9.707a1 1 0 01-1.414 0z" clipRule="evenodd" />
        </svg>
      );
    }
    if (data.trend_delta < 0) {
      return (
        <svg className="h-5 w-5 text-red-500" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M14.707 10.293a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 111.414-1.414L9 12.586V5a1 1 0 012 0v7.586l2.293-2.293a1 1 0 011.414 0z" clipRule="evenodd" />
        </svg>
      );
    }
    return null;
  };
  
  return (
    <div className="overflow-hidden rounded-lg bg-white shadow">
      <div className="p-5">
        <h3 className="text-lg font-medium text-gray-900">
          {t('analytics.valuation.title')}
        </h3>
        
        <div className="mt-4">
          <div className="flex items-baseline">
            <div className="text-3xl font-semibold text-gray-900">
              {formatCurrency(data.avg_market_value)}
            </div>
            <div className={`ml-2 flex items-baseline text-sm font-semibold ${getTrendColor()}`}>
              {getTrendIcon()}
              <span className="ml-1">
                {(data.trend_delta * 100).toFixed(1)}%
              </span>
            </div>
          </div>
          <p className="mt-1 text-sm text-gray-500">
            {t('analytics.valuation.avg_market_value')}
          </p>
        </div>
        
        <div className="mt-4 h-32">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={trendData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip formatter={(value: any) => formatCurrency(value)} />
              <Line
                type="monotone"
                dataKey="value"
                stroke="#4F46E5"
                strokeWidth={2}
                dot={{ r: 4 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
        
        <div className="mt-4 flex items-center justify-between border-t pt-3">
          <span className="text-sm text-gray-500">{t('analytics.valuation.demand_score')}</span>
          <div className="flex items-center">
            <div className="h-2 w-24 overflow-hidden rounded-full bg-gray-200">
              <div
                className="h-2 bg-indigo-600"
                style={{ width: `${data.demand_score * 100}%` }}
              />
            </div>
            <span className="ml-2 text-sm font-medium text-gray-900">
              {(data.demand_score * 100).toFixed(0)}%
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
