/**
 * Team Store for Antika Auction Watcher
 * Manages current team context, plan info, and agent usage
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface TeamMember {
  id: number;
  user_id: number;
  user_email: string;
  role: 'OWNER' | 'ADMIN' | 'ANALYST' | 'VIEWER';
  joined_at: string;
}

export interface Plan {
  code: 'FREE' | 'PRO' | 'ENTERPRISE';
  agent_limit: number;
  description: string;
  features: string[];
  price_monthly: number;
}

export interface Team {
  id: number;
  name: string;
  owner_id: number;
  plan_code: string;
  created_at: string;
  member_count?: number;
}

export interface UsageStats {
  team_id: number;
  plan_code: string;
  agent_limit: number;
  active_agents: number;
  available_slots: number;
  daily_starts: number;
  total_agents: number;
  utilization_percent: number;
}

interface TeamStore {
  // Current team
  currentTeam: Team | null;
  currentPlan: Plan | null;
  usageStats: UsageStats | null;
  
  // Team list
  teams: Team[];
  
  // Loading states
  loading: boolean;
  error: string | null;
  
  // Actions
  setCurrentTeam: (team: Team) => void;
  fetchTeams: () => Promise<void>;
  fetchCurrentPlan: () => Promise<void>;
  fetchUsageStats: (teamId: number) => Promise<void>;
  refreshUsage: () => void;
  clearTeam: () => void;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api/v1';

export const useTeamStore = create<TeamStore>()(
  persist(
    (set, get) => ({
      currentTeam: null,
      currentPlan: null,
      usageStats: null,
      teams: [],
      loading: false,
      error: null,

      setCurrentTeam: (team: Team) => {
        set({ currentTeam: team });
        // Fetch plan and usage when team changes
        get().fetchCurrentPlan();
        get().fetchUsageStats(team.id);
      },

      fetchTeams: async () => {
        set({ loading: true, error: null });
        
        try {
          const response = await fetch(`${API_BASE_URL}/teams`, {
            headers: {
              'Authorization': `Bearer ${localStorage.getItem('token')}`,
            },
          });

          if (!response.ok) {
            throw new Error('Failed to fetch teams');
          }

          const teams = await response.json();
          set({ teams, loading: false });

          // Set first team as current if none selected
          if (!get().currentTeam && teams.length > 0) {
            get().setCurrentTeam(teams[0]);
          }
        } catch (error) {
          set({ error: (error as Error).message, loading: false });
        }
      },

      fetchCurrentPlan: async () => {
        const team = get().currentTeam;
        if (!team) return;

        try {
          const response = await fetch(`${API_BASE_URL}/plans/${team.plan_code}`);
          
          if (!response.ok) {
            throw new Error('Failed to fetch plan');
          }

          const plan = await response.json();
          set({ currentPlan: plan });
        } catch (error) {
          console.error('Failed to fetch plan:', error);
        }
      },

      fetchUsageStats: async (teamId: number) => {
        try {
          const response = await fetch(`${API_BASE_URL}/agents/usage/${teamId}`, {
            headers: {
              'Authorization': `Bearer ${localStorage.getItem('token')}`,
              'X-Team-Id': teamId.toString(),
            },
          });

          if (!response.ok) {
            throw new Error('Failed to fetch usage stats');
          }

          const stats = await response.json();
          set({ usageStats: stats });
        } catch (error) {
          console.error('Failed to fetch usage stats:', error);
        }
      },

      refreshUsage: () => {
        const team = get().currentTeam;
        if (team) {
          get().fetchUsageStats(team.id);
        }
      },

      clearTeam: () => {
        set({
          currentTeam: null,
          currentPlan: null,
          usageStats: null,
        });
      },
    }),
    {
      name: 'team-storage',
      partialize: (state) => ({
        currentTeam: state.currentTeam,
        teams: state.teams,
      }),
    }
  )
);

// Auto-refresh usage every 30 seconds
if (typeof window !== 'undefined') {
  setInterval(() => {
    const store = useTeamStore.getState();
    if (store.currentTeam) {
      store.refreshUsage();
    }
  }, 30000);
}
