/**
 * User Preferences Zustand Store (Phase 14)
 */
import { create } from 'zustand';
import { SellerItem, UserPreferencesResponse } from '@/api/userPrefs';

interface UserPrefsState {
  allowlist: SellerItem[];
  blocklist: SellerItem[];
  loading: boolean;
  error: string | null;
  
  // Actions
  setPreferences: (prefs: UserPreferencesResponse) => void;
  addToAllowlist: (seller: SellerItem) => void;
  removeFromAllowlist: (seller_id: string, source: string) => void;
  addToBlocklist: (seller: SellerItem) => void;
  removeFromBlocklist: (seller_id: string, source: string) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  reset: () => void;
}

const initialState = {
  allowlist: [],
  blocklist: [],
  loading: false,
  error: null,
};

export const useUserPrefsStore = create<UserPrefsState>((set) => ({
  ...initialState,
  
  setPreferences: (prefs) =>
    set({
      allowlist: prefs.allowlist,
      blocklist: prefs.blocklist,
      loading: false,
      error: null,
    }),
  
  addToAllowlist: (seller) =>
    set((state) => {
      // Remove from blocklist if present
      const newBlocklist = state.blocklist.filter(
        (s) => !(s.seller_id === seller.seller_id && s.source === seller.source)
      );
      
      // Add to allowlist if not already present
      const exists = state.allowlist.some(
        (s) => s.seller_id === seller.seller_id && s.source === seller.source
      );
      
      return {
        allowlist: exists ? state.allowlist : [...state.allowlist, seller],
        blocklist: newBlocklist,
      };
    }),
  
  removeFromAllowlist: (seller_id, source) =>
    set((state) => ({
      allowlist: state.allowlist.filter(
        (s) => !(s.seller_id === seller_id && s.source === source)
      ),
    })),
  
  addToBlocklist: (seller) =>
    set((state) => {
      // Remove from allowlist if present
      const newAllowlist = state.allowlist.filter(
        (s) => !(s.seller_id === seller.seller_id && s.source === seller.source)
      );
      
      // Add to blocklist if not already present
      const exists = state.blocklist.some(
        (s) => s.seller_id === seller.seller_id && s.source === seller.source
      );
      
      return {
        allowlist: newAllowlist,
        blocklist: exists ? state.blocklist : [...state.blocklist, seller],
      };
    }),
  
  removeFromBlocklist: (seller_id, source) =>
    set((state) => ({
      blocklist: state.blocklist.filter(
        (s) => !(s.seller_id === seller_id && s.source === source)
      ),
    })),
  
  setLoading: (loading) => set({ loading }),
  
  setError: (error) => set({ error }),
  
  reset: () => set(initialState),
}));
