/**
 * Seller List Table Component (Phase 14)
 */
import React from 'react';
import { SellerItem } from '@/api/userPrefs';
import { TrashIcon } from '@heroicons/react/24/outline';

interface SellerListTableProps {
  listType: 'allowlist' | 'blocklist';
  sellers: SellerItem[];
  onRemove: (seller_id: string, source: string) => void;
  loading?: boolean;
}

export function SellerListTable({
  listType,
  sellers,
  onRemove,
  loading = false,
}: SellerListTableProps) {
  const isEmpty = sellers.length === 0;
  
  return (
    <div className="overflow-hidden bg-white shadow sm:rounded-lg">
      <div className="px-4 py-5 sm:px-6">
        <h3 className="text-lg font-medium leading-6 text-gray-900">
          {listType === 'allowlist' ? 'Allowlist' : 'Blocklist'}
        </h3>
        <p className="mt-1 max-w-2xl text-sm text-gray-500">
          {listType === 'allowlist'
            ? 'Sellers you want to bid on. If set, only these sellers are allowed.'
            : 'Sellers you want to avoid. Always blocked from AutoBid.'}
        </p>
      </div>
      
      {isEmpty ? (
        <div className="border-t border-gray-200 px-4 py-12 text-center">
          <p className="text-sm text-gray-500">
            {listType === 'allowlist'
              ? 'No sellers in allowlist. All sellers allowed (except blocklisted).'
              : 'No sellers in blocklist. No restrictions applied.'}
          </p>
        </div>
      ) : (
        <div className="border-t border-gray-200">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th
                  scope="col"
                  className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500"
                >
                  Seller ID
                </th>
                <th
                  scope="col"
                  className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500"
                >
                  Source
                </th>
                <th
                  scope="col"
                  className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500"
                >
                  Reason
                </th>
                <th scope="col" className="relative px-6 py-3">
                  <span className="sr-only">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 bg-white">
              {sellers.map((seller) => (
                <tr key={`${seller.seller_id}:${seller.source}`} className="hover:bg-gray-50">
                  <td className="whitespace-nowrap px-6 py-4 text-sm font-medium text-gray-900">
                    {seller.seller_id}
                  </td>
                  <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-500">
                    <span
                      className={`inline-flex rounded-full px-2 py-1 text-xs font-semibold ${
                        seller.source === 'ebay'
                          ? 'bg-blue-100 text-blue-800'
                          : seller.source === 'etsy'
                          ? 'bg-orange-100 text-orange-800'
                          : 'bg-gray-100 text-gray-800'
                      }`}
                    >
                      {seller.source}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500">
                    {seller.reason || '?'}
                  </td>
                  <td className="whitespace-nowrap px-6 py-4 text-right text-sm font-medium">
                    <button
                      onClick={() => onRemove(seller.seller_id, seller.source)}
                      disabled={loading}
                      className="text-red-600 hover:text-red-900 disabled:opacity-50"
                      title="Remove"
                    >
                      <TrashIcon className="h-5 w-5" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      
      <div className="border-t border-gray-200 bg-gray-50 px-4 py-3">
        <p className="text-sm text-gray-700">
          Total: <span className="font-semibold">{sellers.length}</span> seller
          {sellers.length !== 1 ? 's' : ''}
        </p>
      </div>
    </div>
  );
}
