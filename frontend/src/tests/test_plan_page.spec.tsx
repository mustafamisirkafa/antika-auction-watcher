/**
 * Tests for Plan Settings Page (Phase 8)
 */
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import PlanSettings from '@/pages/settings/plan';
import { useTeamStore } from '@/store/teamStore';

// Mock the team store
jest.mock('@/store/teamStore');

// Mock fetch
global.fetch = jest.fn();

const mockUsageStats = {
  team_id: 1,
  plan_code: 'FREE',
  agent_limit: 3,
  active_agents: 2,
  available_slots: 1,
  daily_starts: 5,
  total_agents: 4,
  utilization_percent: 66.67,
};

const mockPlan = {
  code: 'FREE' as const,
  agent_limit: 3,
  description: 'Up to 3 AI watcher agents, no autobid',
  features: ['3 active agents', 'Manual bidding only', 'Basic analytics'],
  price_monthly: 0,
};

const mockPlans = [
  mockPlan,
  {
    code: 'PRO' as const,
    agent_limit: 25,
    description: 'Up to 25 watcher/bidder agents',
    features: ['25 active agents', 'Automatic bidding', 'Advanced analytics'],
    price_monthly: 49.99,
  },
  {
    code: 'ENTERPRISE' as const,
    agent_limit: 100,
    description: 'Up to 100 agents + advanced analysis',
    features: ['100 active agents', 'Custom strategies', 'API access'],
    price_monthly: 199.99,
  },
];

const mockTeam = {
  id: 1,
  name: 'Test Team',
  owner_id: 1,
  plan_code: 'FREE',
  created_at: '2025-11-01T00:00:00Z',
};

describe('PlanSettings', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    
    (global.fetch as jest.Mock).mockImplementation((url: string) => {
      if (url.includes('/plans')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockPlans),
        });
      }
      return Promise.reject(new Error('Unknown URL'));
    });
  });

  test('renders page without team', () => {
    (useTeamStore as any).mockReturnValue({
      currentTeam: null,
      currentPlan: null,
      usageStats: null,
      fetchCurrentPlan: jest.fn(),
      fetchUsageStats: jest.fn(),
      refreshUsage: jest.fn(),
    });

    render(<PlanSettings />);
    
    expect(screen.getByText(/No team selected/i)).toBeInTheDocument();
  });

  test('renders usage stats correctly', async () => {
    (useTeamStore as any).mockReturnValue({
      currentTeam: mockTeam,
      currentPlan: mockPlan,
      usageStats: mockUsageStats,
      fetchCurrentPlan: jest.fn(),
      fetchUsageStats: jest.fn(),
      refreshUsage: jest.fn(),
    });

    render(<PlanSettings />);
    
    await waitFor(() => {
      expect(screen.getByText('2')).toBeInTheDocument(); // Active agents
      expect(screen.getByText('1')).toBeInTheDocument(); // Available slots
      expect(screen.getByText('5')).toBeInTheDocument(); // Daily starts
    });
  });

  test('displays usage progress bar', async () => {
    (useTeamStore as any).mockReturnValue({
      currentTeam: mockTeam,
      currentPlan: mockPlan,
      usageStats: mockUsageStats,
      fetchCurrentPlan: jest.fn(),
      fetchUsageStats: jest.fn(),
      refreshUsage: jest.fn(),
    });

    render(<PlanSettings />);
    
    await waitFor(() => {
      expect(screen.getByText('Agent Usage')).toBeInTheDocument();
      expect(screen.getByText('2 / 3')).toBeInTheDocument();
      expect(screen.getByText('1 slot available')).toBeInTheDocument();
    });
  });

  test('displays correct utilization percentage', async () => {
    (useTeamStore as any).mockReturnValue({
      currentTeam: mockTeam,
      currentPlan: mockPlan,
      usageStats: mockUsageStats,
      fetchCurrentPlan: jest.fn(),
      fetchUsageStats: jest.fn(),
      refreshUsage: jest.fn(),
    });

    render(<PlanSettings />);
    
    await waitFor(() => {
      expect(screen.getByText('66.7%')).toBeInTheDocument();
    });
  });

  test('renders all plan cards', async () => {
    (useTeamStore as any).mockReturnValue({
      currentTeam: mockTeam,
      currentPlan: mockPlan,
      usageStats: mockUsageStats,
      fetchCurrentPlan: jest.fn(),
      fetchUsageStats: jest.fn(),
      refreshUsage: jest.fn(),
    });

    render(<PlanSettings />);
    
    await waitFor(() => {
      expect(screen.getByText('FREE')).toBeInTheDocument();
      expect(screen.getByText('PRO')).toBeInTheDocument();
      expect(screen.getByText('ENTERPRISE')).toBeInTheDocument();
    });
  });

  test('shows current plan badge', async () => {
    (useTeamStore as any).mockReturnValue({
      currentTeam: mockTeam,
      currentPlan: mockPlan,
      usageStats: mockUsageStats,
      fetchCurrentPlan: jest.fn(),
      fetchUsageStats: jest.fn(),
      refreshUsage: jest.fn(),
    });

    render(<PlanSettings />);
    
    await waitFor(() => {
      expect(screen.getByText('Current Plan')).toBeInTheDocument();
    });
  });

  test('handles upgrade button click', async () => {
    const alertMock = jest.spyOn(window, 'alert').mockImplementation(() => {});
    
    (useTeamStore as any).mockReturnValue({
      currentTeam: mockTeam,
      currentPlan: mockPlan,
      usageStats: mockUsageStats,
      fetchCurrentPlan: jest.fn(),
      fetchUsageStats: jest.fn(),
      refreshUsage: jest.fn(),
    });

    render(<PlanSettings />);
    
    await waitFor(() => {
      const upgradeButtons = screen.getAllByText(/Upgrade to/i);
      expect(upgradeButtons.length).toBeGreaterThan(0);
    });

    const proUpgradeButton = screen.getByText('Upgrade to PRO');
    fireEvent.click(proUpgradeButton);
    
    expect(alertMock).toHaveBeenCalledWith(expect.stringContaining('Upgrade to PRO'));
    
    alertMock.mockRestore();
  });

  test('displays feature comparison matrix', async () => {
    (useTeamStore as any).mockReturnValue({
      currentTeam: mockTeam,
      currentPlan: mockPlan,
      usageStats: mockUsageStats,
      fetchCurrentPlan: jest.fn(),
      fetchUsageStats: jest.fn(),
      refreshUsage: jest.fn(),
    });

    render(<PlanSettings />);
    
    await waitFor(() => {
      expect(screen.getByText('Feature Comparison')).toBeInTheDocument();
      expect(screen.getByText('Active Agents')).toBeInTheDocument();
      expect(screen.getByText('Automatic Bidding')).toBeInTheDocument();
      expect(screen.getByText('Advanced Analytics')).toBeInTheDocument();
    });
  });

  test('displays FAQ section', async () => {
    (useTeamStore as any).mockReturnValue({
      currentTeam: mockTeam,
      currentPlan: mockPlan,
      usageStats: mockUsageStats,
      fetchCurrentPlan: jest.fn(),
      fetchUsageStats: jest.fn(),
      refreshUsage: jest.fn(),
    });

    render(<PlanSettings />);
    
    await waitFor(() => {
      expect(screen.getByText('Frequently Asked Questions')).toBeInTheDocument();
      expect(screen.getByText(/What happens if I reach my agent limit/i)).toBeInTheDocument();
    });
  });
});
