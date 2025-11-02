/**
 * Tests for Team Settings Page (Phase 8)
 */
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import TeamSettings from '@/pages/settings/team';
import { useTeamStore } from '@/store/teamStore';

// Mock the team store
jest.mock('@/store/teamStore');

// Mock fetch
global.fetch = jest.fn();

const mockTeam = {
  id: 1,
  name: 'Test Team',
  owner_id: 1,
  plan_code: 'PRO',
  created_at: '2025-11-01T00:00:00Z',
  member_count: 3,
};

const mockMembers = [
  {
    id: 1,
    team_id: 1,
    user_id: 1,
    user_email: 'owner@example.com',
    role: 'OWNER',
    joined_at: '2025-11-01T00:00:00Z',
  },
  {
    id: 2,
    team_id: 1,
    user_id: 2,
    user_email: 'admin@example.com',
    role: 'ADMIN',
    joined_at: '2025-11-02T00:00:00Z',
  },
  {
    id: 3,
    team_id: 1,
    user_id: 3,
    user_email: 'viewer@example.com',
    role: 'VIEWER',
    joined_at: '2025-11-03T00:00:00Z',
  },
];

describe('TeamSettings', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    
    (global.fetch as jest.Mock).mockImplementation((url: string) => {
      if (url.includes('/members')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockMembers),
        });
      }
      return Promise.reject(new Error('Unknown URL'));
    });

    Storage.prototype.getItem = jest.fn(() => 'fake_token');
  });

  test('renders page without team', () => {
    (useTeamStore as any).mockReturnValue({
      currentTeam: null,
      loading: false,
      error: null,
    });

    render(<TeamSettings />);
    
    expect(screen.getByText(/No team selected/i)).toBeInTheDocument();
  });

  test('renders team information', async () => {
    (useTeamStore as any).mockReturnValue({
      currentTeam: mockTeam,
      loading: false,
      error: null,
    });

    render(<TeamSettings />);
    
    await waitFor(() => {
      expect(screen.getByText('Team Information')).toBeInTheDocument();
      expect(screen.getByText('Test Team')).toBeInTheDocument();
      expect(screen.getByText('PRO')).toBeInTheDocument();
    });
  });

  test('loads and displays team members', async () => {
    (useTeamStore as any).mockReturnValue({
      currentTeam: mockTeam,
      loading: false,
      error: null,
    });

    render(<TeamSettings />);
    
    await waitFor(() => {
      expect(screen.getByText('owner@example.com')).toBeInTheDocument();
      expect(screen.getByText('admin@example.com')).toBeInTheDocument();
      expect(screen.getByText('viewer@example.com')).toBeInTheDocument();
    });
  });

  test('displays correct role badges', async () => {
    (useTeamStore as any).mockReturnValue({
      currentTeam: mockTeam,
      loading: false,
      error: null,
    });

    render(<TeamSettings />);
    
    await waitFor(() => {
      const ownerBadge = screen.getAllByText('OWNER');
      const adminBadge = screen.getAllByText('ADMIN');
      const viewerBadge = screen.getAllByText('VIEWER');
      
      expect(ownerBadge.length).toBeGreaterThan(0);
      expect(adminBadge.length).toBeGreaterThan(0);
      expect(viewerBadge.length).toBeGreaterThan(0);
    });
  });

  test('shows add member button', async () => {
    (useTeamStore as any).mockReturnValue({
      currentTeam: mockTeam,
      loading: false,
      error: null,
    });

    render(<TeamSettings />);
    
    await waitFor(() => {
      expect(screen.getByText('+ Add Member')).toBeInTheDocument();
    });
  });

  test('toggles add member form', async () => {
    (useTeamStore as any).mockReturnValue({
      currentTeam: mockTeam,
      loading: false,
      error: null,
    });

    render(<TeamSettings />);
    
    await waitFor(() => {
      const addButton = screen.getByText('+ Add Member');
      fireEvent.click(addButton);
    });
    
    expect(screen.getByText('Email Address')).toBeInTheDocument();
    expect(screen.getByText('Send Invitation')).toBeInTheDocument();
  });

  test('handles change role action', async () => {
    (global.fetch as jest.Mock).mockImplementationOnce((url: string) => {
      if (url.includes('/members')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockMembers),
        });
      }
      return Promise.reject(new Error('Unknown URL'));
    }).mockImplementationOnce((url: string, options: any) => {
      if (options?.method === 'PATCH') {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ ...mockMembers[1], role: 'ANALYST' }),
        });
      }
      return Promise.reject(new Error('Unknown request'));
    });

    (useTeamStore as any).mockReturnValue({
      currentTeam: mockTeam,
      loading: false,
      error: null,
    });

    render(<TeamSettings />);
    
    await waitFor(() => {
      const roleSelects = screen.getAllByRole('combobox');
      expect(roleSelects.length).toBeGreaterThan(0);
    });
  });

  test('prevents removing owner', async () => {
    (useTeamStore as any).mockReturnValue({
      currentTeam: mockTeam,
      loading: false,
      error: null,
    });

    render(<TeamSettings />);
    
    await waitFor(() => {
      const removeButtons = screen.queryAllByText('Remove');
      // Owner row should not have a remove button
      // Only 2 remove buttons for ADMIN and VIEWER
      expect(removeButtons.length).toBe(2);
    });
  });

  test('displays role descriptions', async () => {
    (useTeamStore as any).mockReturnValue({
      currentTeam: mockTeam,
      loading: false,
      error: null,
    });

    render(<TeamSettings />);
    
    await waitFor(() => {
      expect(screen.getByText('Role Descriptions')).toBeInTheDocument();
      expect(screen.getByText(/Full control over team, billing/i)).toBeInTheDocument();
      expect(screen.getByText(/Can manage members, agents/i)).toBeInTheDocument();
      expect(screen.getByText(/Read-only access/i)).toBeInTheDocument();
    });
  });

  test('handles loading state', () => {
    (useTeamStore as any).mockReturnValue({
      currentTeam: mockTeam,
      loading: true,
      error: null,
    });

    render(<TeamSettings />);
    
    expect(screen.getByText('Loading members...')).toBeInTheDocument();
  });
});
