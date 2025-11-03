/**
 * Add Seller Modal Component (Phase 14)
 */
import React, { useState, Fragment } from 'react';
import { Dialog, Transition } from '@headlessui/react';
import { XMarkIcon } from '@heroicons/react/24/outline';
import { UpdatePreferenceRequest } from '@/api/userPrefs';

interface AddSellerModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (request: UpdatePreferenceRequest) => void;
  loading?: boolean;
}

export function AddSellerModal({
  isOpen,
  onClose,
  onSubmit,
  loading = false,
}: AddSellerModalProps) {
  const [sellerId, setSellerId] = useState('');
  const [source, setSource] = useState('ebay');
  const [listType, setListType] = useState<'allow' | 'block'>('block');
  const [reason, setReason] = useState('');
  
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!sellerId.trim()) return;
    
    const action = listType === 'allow' ? 'add_allow' : 'add_block';
    
    onSubmit({
      action,
      seller_id: sellerId.trim(),
      source,
      reason: reason.trim() || undefined,
    });
    
    // Reset form
    setSellerId('');
    setSource('ebay');
    setListType('block');
    setReason('');
  };
  
  return (
    <Transition.Root show={isOpen} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={onClose}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" />
        </Transition.Child>
        
        <div className="fixed inset-0 z-10 overflow-y-auto">
          <div className="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
              enterTo="opacity-100 translate-y-0 sm:scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 translate-y-0 sm:scale-100"
              leaveTo="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
            >
              <Dialog.Panel className="relative transform overflow-hidden rounded-lg bg-white px-4 pb-4 pt-5 text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-lg sm:p-6">
                <div className="absolute right-0 top-0 pr-4 pt-4">
                  <button
                    type="button"
                    className="rounded-md bg-white text-gray-400 hover:text-gray-500"
                    onClick={onClose}
                  >
                    <span className="sr-only">Close</span>
                    <XMarkIcon className="h-6 w-6" aria-hidden="true" />
                  </button>
                </div>
                
                <div className="sm:flex sm:items-start">
                  <div className="mt-3 w-full text-center sm:mt-0 sm:text-left">
                    <Dialog.Title
                      as="h3"
                      className="text-lg font-semibold leading-6 text-gray-900"
                    >
                      Add Seller Preference
                    </Dialog.Title>
                    
                    <form onSubmit={handleSubmit} className="mt-6 space-y-4">
                      {/* Seller ID */}
                      <div>
                        <label
                          htmlFor="seller_id"
                          className="block text-sm font-medium text-gray-700"
                        >
                          Seller ID *
                        </label>
                        <input
                          type="text"
                          id="seller_id"
                          value={sellerId}
                          onChange={(e) => setSellerId(e.target.value)}
                          required
                          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
                          placeholder="e.g., seller-123"
                        />
                      </div>
                      
                      {/* Source */}
                      <div>
                        <label
                          htmlFor="source"
                          className="block text-sm font-medium text-gray-700"
                        >
                          Marketplace Source *
                        </label>
                        <select
                          id="source"
                          value={source}
                          onChange={(e) => setSource(e.target.value)}
                          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
                        >
                          <option value="ebay">eBay</option>
                          <option value="etsy">Etsy</option>
                          <option value="amazon">Amazon</option>
                          <option value="sahibinden">Sahibinden</option>
                          <option value="letgo">Letgo</option>
                        </select>
                      </div>
                      
                      {/* List Type */}
                      <div>
                        <label className="block text-sm font-medium text-gray-700">
                          Add to *
                        </label>
                        <div className="mt-2 space-y-2">
                          <div className="flex items-center">
                            <input
                              id="allowlist"
                              name="listType"
                              type="radio"
                              value="allow"
                              checked={listType === 'allow'}
                              onChange={(e) => setListType(e.target.value as 'allow' | 'block')}
                              className="h-4 w-4 border-gray-300 text-indigo-600 focus:ring-indigo-500"
                            />
                            <label
                              htmlFor="allowlist"
                              className="ml-3 block text-sm font-medium text-gray-700"
                            >
                              Allowlist (trusted sellers)
                            </label>
                          </div>
                          <div className="flex items-center">
                            <input
                              id="blocklist"
                              name="listType"
                              type="radio"
                              value="block"
                              checked={listType === 'block'}
                              onChange={(e) => setListType(e.target.value as 'allow' | 'block')}
                              className="h-4 w-4 border-gray-300 text-indigo-600 focus:ring-indigo-500"
                            />
                            <label
                              htmlFor="blocklist"
                              className="ml-3 block text-sm font-medium text-gray-700"
                            >
                              Blocklist (avoid these sellers)
                            </label>
                          </div>
                        </div>
                      </div>
                      
                      {/* Reason */}
                      <div>
                        <label
                          htmlFor="reason"
                          className="block text-sm font-medium text-gray-700"
                        >
                          Reason (optional)
                        </label>
                        <textarea
                          id="reason"
                          value={reason}
                          onChange={(e) => setReason(e.target.value)}
                          rows={3}
                          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
                          placeholder="Why are you adding this seller?"
                        />
                      </div>
                      
                      {/* Actions */}
                      <div className="mt-5 sm:mt-4 sm:flex sm:flex-row-reverse">
                        <button
                          type="submit"
                          disabled={loading || !sellerId.trim()}
                          className="inline-flex w-full justify-center rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 disabled:opacity-50 sm:ml-3 sm:w-auto"
                        >
                          {loading ? 'Adding...' : 'Add Seller'}
                        </button>
                        <button
                          type="button"
                          onClick={onClose}
                          disabled={loading}
                          className="mt-3 inline-flex w-full justify-center rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50 disabled:opacity-50 sm:mt-0 sm:w-auto"
                        >
                          Cancel
                        </button>
                      </div>
                    </form>
                  </div>
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition.Root>
  );
}
