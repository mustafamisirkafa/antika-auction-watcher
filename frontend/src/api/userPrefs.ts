/**
 * User Preferences API Client (Phase 14)
 */
import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface SellerItem {
  seller_id: string;
  source: string;
  reason?: string | null;
}

export interface UserPreferencesResponse {
  user_id: number;
  team_id: number;
  allowlist: SellerItem[];
  blocklist: SellerItem[];
  updated_at: string;
}

export interface UpdatePreferenceRequest {
  action: 'add_allow' | 'remove_allow' | 'add_block' | 'remove_block';
  seller_id: string;
  source: string;
  reason?: string;
}

export interface UpdatePreferenceResponse {
  success: boolean;
  message: string;
  affected_list: string;
  seller_id: string;
  new_total: number;
  updated_at: string;
}

export interface CheckSellerResponse {
  allowed: boolean;
  reason: string;
}

/**
 * Get user's seller preferences
 */
export async function getUserPrefs(token: string): Promise<UserPreferencesResponse> {
  const response = await axios.get(`${API_BASE_URL}/api/user/prefs`, {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });
  return response.data;
}

/**
 * Update user's seller preferences
 */
export async function updateUserPrefs(
  token: string,
  request: UpdatePreferenceRequest
): Promise<UpdatePreferenceResponse> {
  const response = await axios.post(
    `${API_BASE_URL}/api/user/prefs/update`,
    request,
    {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    }
  );
  return response.data;
}

/**
 * Check if a seller is allowed
 */
export async function checkSeller(
  token: string,
  seller_id: string,
  source: string
): Promise<CheckSellerResponse> {
  const response = await axios.get(
    `${API_BASE_URL}/api/user/prefs/check/${seller_id}`,
    {
      params: { source },
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    }
  );
  return response.data;
}
