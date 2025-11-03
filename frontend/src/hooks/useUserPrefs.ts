/**
 * React Query Hook for User Preferences (Phase 14)
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getUserPrefs, updateUserPrefs, UpdatePreferenceRequest } from '@/api/userPrefs';
import { useUserPrefsStore } from '@/store/userPrefsStore';
import { useAuth } from '@/hooks/useAuth';
import { toast } from 'react-hot-toast';

/**
 * Hook to fetch and manage user preferences
 */
export function useUserPrefs() {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const { setPreferences, setLoading, setError } = useUserPrefsStore();
  
  // Fetch preferences
  const query = useQuery({
    queryKey: ['userPrefs'],
    queryFn: async () => {
      if (!token) throw new Error('Not authenticated');
      const data = await getUserPrefs(token);
      setPreferences(data);
      return data;
    },
    enabled: !!token,
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchOnWindowFocus: false,
  });
  
  // Update preferences mutation
  const mutation = useMutation({
    mutationFn: async (request: UpdatePreferenceRequest) => {
      if (!token) throw new Error('Not authenticated');
      return updateUserPrefs(token, request);
    },
    onMutate: async (variables) => {
      setLoading(true);
      
      // Optimistic update
      const { addToAllowlist, removeFromAllowlist, addToBlocklist, removeFromBlocklist } =
        useUserPrefsStore.getState();
      
      const seller = {
        seller_id: variables.seller_id,
        source: variables.source,
        reason: variables.reason,
      };
      
      switch (variables.action) {
        case 'add_allow':
          addToAllowlist(seller);
          break;
        case 'remove_allow':
          removeFromAllowlist(variables.seller_id, variables.source);
          break;
        case 'add_block':
          addToBlocklist(seller);
          break;
        case 'remove_block':
          removeFromBlocklist(variables.seller_id, variables.source);
          break;
      }
    },
    onSuccess: (data) => {
      setLoading(false);
      toast.success(data.message);
      
      // Invalidate and refetch
      queryClient.invalidateQueries({ queryKey: ['userPrefs'] });
    },
    onError: (error: any) => {
      setLoading(false);
      const message = error.response?.data?.detail || error.message || 'Failed to update preferences';
      setError(message);
      toast.error(message);
      
      // Revert optimistic update by refetching
      queryClient.invalidateQueries({ queryKey: ['userPrefs'] });
    },
  });
  
  return {
    preferences: query.data,
    isLoading: query.isLoading || mutation.isPending,
    error: query.error || mutation.error,
    updatePreference: mutation.mutate,
    refetch: query.refetch,
  };
}
