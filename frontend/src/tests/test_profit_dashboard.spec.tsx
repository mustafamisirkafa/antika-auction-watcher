/**
 * Tests for Profit Dashboard Page (Phase 9)
 */
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import ProfitDashboard from '@/pages/profit';
import { useTeamStore } from '@/store/teamStore';

// Mock the team store
jest.mock('@/store/teamStore');

// Mock fetch
global.fetch = jest.fn();

const mockProPlan = {
  code: 'PRO' as const,
  agent_limit: 25,
  description: 'Up to 25 watcher/bidder agents',
  features: ['25 active agents', 'Automatic bidding'],
  price_monthly: 49.99,
};

const mockFreePlan = {
  code: 'FREE' as const,
  agent_limit: 3,
  description: 'Up to 3 AI watcher agents',
  features: ['3 active agents'],
  price_monthly: 0,
};

const mockTeam = {
  id: 1,
  name: 'Test Team',
  owner_id: 1,
  plan_code: 'PRO',
  created_at: '2025-11-01T00:00:00Z',
};

const mockEstimates = [
  {
    id: 1,
    auction_item_id: 1,
    estimated_value: 1160.0,
    recommended_max_bid: 950.0,
    profit_margin: 0.22,
    profit_amount: 210.0,
    confidence: 0.82,
    risk_level: 'low',
    market_volatility: 0.25,
    liquidity_avg: 0.87,
    auction_item: {
      id: 1,
      lot_id: 'LOT-001',
      title: 'Silver Candleholder',
      category: 'silver',
      image_url: 'https://example.com/image.jpg',
      starting_price: 800.0,
      auction_date: '2025-11-10T14:00:00Z',
      source: "Christie's",
    },
  },
  {
    id: 2,
    auction_item_id: 2,
    estimated_value: 2500.0,
    recommended_max_bid: 2100.0,
    profit_margin: 0.15,
    profit_amount: 400.0,
    confidence: 0.65,
    risk_level: 'medium',
    market_volatility: 0.40,
    liquidity_avg: 0.70,
    auction_item: {
      id: 2,
      lot_id: 'LOT-002',
      title: 'Antique Vase',
      category: 'ceramics',
      starting_price: 1800.0,
      auction_date: '2025-11-12T10:00:00Z',
      source: "Sotheby's",
    },
  },
];

describe('ProfitDashboard', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    Storage.prototype.getItem = jest.fn(() => 'fake_token');
  });

  test('shows upgrade notice for FREE plan', () => {
    (useTeamStore as any).mockReturnValue({
      currentTeam: mockTeam,
      currentPlan: mockFreePlan,
    });

    render(<ProfitDashboard />);
    
    expect(screen.getByText('AI Profit Advisor')).toBeInTheDocument();
    expect(screen.getByText(/PRO.*ENTERPRISE/i)).toBeInTheDocument();
    expect(screen.getByText('Upgrade to PRO')).toBeInTheDocument();
  });

  test('renders dashboard for PRO plan', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => mockEstimates,
    });

    (useTeamStore as any).mockReturnValue({
      currentTeam: mockTeam,
      currentPlan: mockProPlan,
    });

    render(<ProfitDashboard />);
    
    await waitFor(() => {
      expect(screen.getByText('AI Profit Advisor')).toBeInTheDocument();
      expect(screen.queryByText('Upgrade to PRO')).not.toBeInTheDocument();
    });
  });

  test('displays stats correctly', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => mockEstimates,
    });

    (useTeamStore as any).mockReturnValue({
      currentTeam: mockTeam,
      currentPlan: mockProPlan,
    });

    render(<ProfitDashboard />);
    
    await waitFor(() => {
      expect(screen.getByText('Total Items')).toBeInTheDocument();
      expect(screen.getByText('2')).toBeInTheDocument(); // Total count
    });
  });

  test('renders profit cards', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => mockEstimates,
    });

    (useTeamStore as any).mockReturnValue({
      currentTeam: mockTeam,
      currentPlan: mockProPlan,
    });

    render(<ProfitDashboard />);
    
    await waitFor(() => {
      expect(screen.getByText('Silver Candleholder')).toBeInTheDocument();
      expect(screen.getByText('Antique Vase')).toBeInTheDocument();
    });
  });

  test('handles tab switching', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => mockEstimates,
    });

    (useTeamStore as any).mockReturnValue({
      currentTeam: mockTeam,
      currentPlan: mockProPlan,
    });

    render(<ProfitDashboard />);
    
    await waitFor(() => {
      const insightsTab = screen.getByText(/Pre-Auction Insights/i);
      const comparisonsTab = screen.getByText(/Market Comparisons/i);
      
      expect(insightsTab).toBeInTheDocument();
      expect(comparisonsTab).toBeInTheDocument();
    });
  });

  test('handles analysis trigger', async () => {
    (global.fetch as jest.Mock)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockEstimates,
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ analyzed_count: 2, estimates: mockEstimates }),
      });

    (useTeamStore as any).mockReturnValue({
      currentTeam: mockTeam,
      currentPlan: mockProPlan,
    });

    const alertMock = jest.spyOn(window, 'alert').mockImplementation(() => {});

    render(<ProfitDashboard />);
    
    await waitFor(() => {
      const refreshButton = screen.getByText(/Refresh Analysis/i);
      fireEvent.click(refreshButton);
    });

    await waitFor(() => {
      expect(alertMock).toHaveBeenCalledWith(expect.stringContaining('Successfully analyzed'));
    });

    alertMock.mockRestore();
  });

  test('applies risk filter', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => mockEstimates,
    });

    (useTeamStore as any).mockReturnValue({
      currentTeam: mockTeam,
      currentPlan: mockProPlan,
    });

    render(<ProfitDashboard />);
    
    await waitFor(() => {
      const riskFilter = screen.getByRole('combobox', { name: /risk/i });
      expect(riskFilter).toBeInTheDocument();
    });
  });

  test('displays empty state', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => [],
    });

    (useTeamStore as any).mockReturnValue({
      currentTeam: mockTeam,
      currentPlan: mockProPlan,
    });

    render(<ProfitDashboard />);
    
    await waitFor(() => {
      expect(screen.getByText(/No profit estimates found/i)).toBeInTheDocument();
    });
  });

  test('handles loading state', () => {
    (global.fetch as jest.Mock).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    );

    (useTeamStore as any).mockReturnValue({
      currentTeam: mockTeam,
      currentPlan: mockProPlan,
    });

    render(<ProfitDashboard />);
    
    expect(screen.getByText(/Loading profit estimates/i)).toBeInTheDocument();
  });
});
