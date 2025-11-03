/**
 * User Preferences Impact Bars (Phase 17)
 */
import React from 'react';
import { UserPrefsMetrics } from '@/api/analytics';
import { useTranslation } from '@/lib/i18n';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';

interface UserPrefsBarsProps {
  data: UserPrefsMetrics;
}

export function UserPrefsBars({ data }: UserPrefsBarsProps) {
  const { t } = useTranslation();
  
  const chartData = [
    {
      name: t('analytics.user_prefs.allowlist'),
      value: data.allowlist,
      fill: '#10B981',
    },
    {
      name: t('analytics.user_prefs.blocklist'),
      value: data.blocklist,
      fill: '#EF4444',
    },
  ];
  
  const total = data.allowlist + data.blocklist;
  
  return (
    <div className="overflow-hidden rounded-lg bg-white shadow">
      <div className="p-5">
        <h3 className="text-lg font-medium text-gray-900">
          {t('analytics.user_prefs.title')}
        </h3>
        
        <div className="mt-4">
          <div className="text-3xl font-semibold text-gray-900">{total}</div>
          <p className="mt-1 text-sm text-gray-500">
            {t('analytics.user_prefs.total_entries')}
          </p>
        </div>
        
        <div className="mt-4 h-32">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip />
              <Bar dataKey="value" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        
        <div className="mt-4 space-y-2 border-t pt-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <div className="h-3 w-3 rounded bg-green-500" />
              <span className="ml-2 text-sm text-gray-600">
                {t('analytics.user_prefs.allowlist')}
              </span>
            </div>
            <span className="text-sm font-medium text-gray-900">{data.allowlist}</span>
          </div>
          
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <div className="h-3 w-3 rounded bg-red-500" />
              <span className="ml-2 text-sm text-gray-600">
                {t('analytics.user_prefs.blocklist')}
              </span>
            </div>
            <span className="text-sm font-medium text-gray-900">{data.blocklist}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
