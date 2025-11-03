/**
 * Seller Preferences Page (Phase 14 + Phase 16-TR)
 * Turkish Localization
 */
import React, { useState } from 'react';
import { PlusIcon, InformationCircleIcon } from '@heroicons/react/24/outline';
import { SellerListTable } from '@/components/SellerListTable';
import { AddSellerModal } from '@/components/AddSellerModal';
import { useUserPrefs } from '@/hooks/useUserPrefs';
import { useUserPrefsStore } from '@/store/userPrefsStore';
import { useTranslation } from '@/lib/i18n';

export default function SellerPreferencesPage() {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const { preferences, isLoading, error, updatePreference } = useUserPrefs();
  const { allowlist, blocklist } = useUserPrefsStore();
  const { t } = useTranslation();
  
  const handleRemoveFromAllowlist = (seller_id: string, source: string) => {
    updatePreference({
      action: 'remove_allow',
      seller_id,
      source,
    });
  };
  
  const handleRemoveFromBlocklist = (seller_id: string, source: string) => {
    updatePreference({
      action: 'remove_block',
      seller_id,
      source,
    });
  };
  
  const handleAddSeller = (request: any) => {
    updatePreference(request);
    setIsModalOpen(false);
  };
  
  if (isLoading && !preferences) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-current border-r-transparent align-[-0.125em] motion-reduce:animate-[spin_1.5s_linear_infinite]" />
          <p className="mt-4 text-sm text-gray-500">{t('seller_preferences.loading_preferences')}</p>
        </div>
      </div>
    );
  }
  
  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">{t('seller_preferences.title')}</h1>
        <p className="mt-2 text-sm text-gray-600">
          {t('seller_preferences.description')}
        </p>
      </div>
      
      {/* Error Alert */}
      {error && (
        <div className="mb-6 rounded-md bg-red-50 p-4">
          <div className="flex">
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">{t('messages.error_loading_preferences')}</h3>
              <div className="mt-2 text-sm text-red-700">
                {typeof error === 'string' ? error : t('common.error')}
              </div>
            </div>
          </div>
        </div>
      )}
      
      {/* Info Card */}
      <div className="mb-6 rounded-lg border border-blue-200 bg-blue-50 p-4">
        <div className="flex">
          <div className="flex-shrink-0">
            <InformationCircleIcon className="h-5 w-5 text-blue-400" aria-hidden="true" />
          </div>
          <div className="ml-3 flex-1">
            <h3 className="text-sm font-medium text-blue-800">{t('seller_preferences.info_title')}</h3>
            <div className="mt-2 text-sm text-blue-700">
              <ul className="list-disc space-y-1 pl-5">
                <li>{t('seller_preferences.info_blocklist')}</li>
                <li>{t('seller_preferences.info_allowlist_empty')}</li>
                <li>{t('seller_preferences.info_allowlist_set')}</li>
                <li>{t('seller_preferences.info_mutual_exclusion')}</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
      
      {/* Add Button */}
      <div className="mb-6">
        <button
          onClick={() => setIsModalOpen(true)}
          className="inline-flex items-center rounded-md bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600"
        >
          <PlusIcon className="-ml-0.5 mr-1.5 h-5 w-5" aria-hidden="true" />
          {t('seller_preferences.add_seller')}
        </button>
      </div>
      
      {/* Statistics */}
      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="overflow-hidden rounded-lg bg-white px-4 py-5 shadow sm:p-6">
          <dt className="truncate text-sm font-medium text-gray-500">{t('seller_preferences.allowlist_size')}</dt>
          <dd className="mt-1 text-3xl font-semibold tracking-tight text-gray-900">
            {allowlist.length}
          </dd>
          <p className="mt-1 text-xs text-gray-500">
            {allowlist.length === 0
              ? t('seller_preferences.allowlist_mode_open')
              : t('seller_preferences.allowlist_mode_restricted')}
          </p>
        </div>
        
        <div className="overflow-hidden rounded-lg bg-white px-4 py-5 shadow sm:p-6">
          <dt className="truncate text-sm font-medium text-gray-500">{t('seller_preferences.blocklist_size')}</dt>
          <dd className="mt-1 text-3xl font-semibold tracking-tight text-gray-900">
            {blocklist.length}
          </dd>
          <p className="mt-1 text-xs text-gray-500">
            {blocklist.length === 0 ? t('seller_preferences.blocklist_status_none') : t('seller_preferences.blocklist_status_active')}
          </p>
        </div>
      </div>
      
      {/* Lists */}
      <div className="space-y-6">
        {/* Allowlist */}
        <SellerListTable
          listType="allowlist"
          sellers={allowlist}
          onRemove={handleRemoveFromAllowlist}
          loading={isLoading}
        />
        
        {/* Blocklist */}
        <SellerListTable
          listType="blocklist"
          sellers={blocklist}
          onRemove={handleRemoveFromBlocklist}
          loading={isLoading}
        />
      </div>
      
      {/* Add Seller Modal */}
      <AddSellerModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSubmit={handleAddSeller}
        loading={isLoading}
      />
    </div>
  );
}
