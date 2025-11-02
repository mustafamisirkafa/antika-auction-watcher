/**
 * Tests for Agent Limit Modal and Enforcement (Phase 8)
 */
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import AgentUsageBar from '@/components/AgentUsageBar';
import PlanCard from '@/components/PlanCard';

describe('AgentUsageBar', () => {
  test('renders with available slots', () => {
    render(<AgentUsageBar activeAgents={2} agentLimit={5} dailyStarts={10} />);
    
    expect(screen.getByText('Agent Usage')).toBeInTheDocument();
    expect(screen.getByText('2 / 5')).toBeInTheDocument();
    expect(screen.getByText('3 slots available')).toBeInTheDocument();
    expect(screen.getByText('10 starts today')).toBeInTheDocument();
  });

  test('renders at limit', () => {
    render(<AgentUsageBar activeAgents={5} agentLimit={5} dailyStarts={20} />);
    
    expect(screen.getByText('5 / 5')).toBeInTheDocument();
    expect(screen.getByText('Limit reached')).toBeInTheDocument();
    expect(screen.getByText(/reached your plan limit/i)).toBeInTheDocument();
  });

  test('shows warning when near limit (90%)', () => {
    render(<AgentUsageBar activeAgents={9} agentLimit={10} dailyStarts={15} />);
    
    expect(screen.getByText(/running low on agent slots/i)).toBeInTheDocument();
  });

  test('uses green color for low utilization', () => {
    const { container } = render(
      <AgentUsageBar activeAgents={2} agentLimit={10} dailyStarts={5} />
    );
    
    const progressBar = container.querySelector('.bg-green-500');
    expect(progressBar).toBeInTheDocument();
  });

  test('uses yellow color for medium utilization', () => {
    const { container } = render(
      <AgentUsageBar activeAgents={8} agentLimit={10} dailyStarts={15} />
    );
    
    const progressBar = container.querySelector('.bg-yellow-500');
    expect(progressBar).toBeInTheDocument();
  });

  test('uses red color for high utilization', () => {
    const { container } = render(
      <AgentUsageBar activeAgents={10} agentLimit={10} dailyStarts={25} />
    );
    
    const progressBar = container.querySelector('.bg-red-500');
    expect(progressBar).toBeInTheDocument();
  });

  test('displays singular slot text correctly', () => {
    render(<AgentUsageBar activeAgents={2} agentLimit={3} dailyStarts={5} />);
    
    expect(screen.getByText('1 slot available')).toBeInTheDocument();
  });

  test('displays plural slots text correctly', () => {
    render(<AgentUsageBar activeAgents={2} agentLimit={10} dailyStarts={5} />);
    
    expect(screen.getByText('8 slots available')).toBeInTheDocument();
  });
});

describe('PlanCard', () => {
  const freePlan = {
    code: 'FREE' as const,
    agent_limit: 3,
    description: 'Up to 3 AI watcher agents, no autobid',
    features: ['3 active agents', 'Manual bidding only', 'Basic analytics'],
    price_monthly: 0,
  };

  const proPlan = {
    code: 'PRO' as const,
    agent_limit: 25,
    description: 'Up to 25 watcher/bidder agents',
    features: ['25 active agents', 'Automatic bidding', 'Advanced analytics'],
    price_monthly: 49.99,
  };

  test('renders plan details correctly', () => {
    render(<PlanCard plan={freePlan} />);
    
    expect(screen.getByText('FREE')).toBeInTheDocument();
    expect(screen.getByText('Up to 3 AI watcher agents, no autobid')).toBeInTheDocument();
    expect(screen.getByText('$0')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument(); // Agent limit
  });

  test('shows current plan badge', () => {
    render(<PlanCard plan={freePlan} current={true} />);
    
    expect(screen.getByText('Current Plan')).toBeInTheDocument();
    expect(screen.getByText('Active Plan')).toBeInTheDocument();
  });

  test('shows upgrade button for non-current plans', () => {
    const onUpgrade = jest.fn();
    render(<PlanCard plan={proPlan} current={false} onUpgrade={onUpgrade} />);
    
    const upgradeButton = screen.getByText('Upgrade to PRO');
    expect(upgradeButton).toBeInTheDocument();
    
    fireEvent.click(upgradeButton);
    expect(onUpgrade).toHaveBeenCalledTimes(1);
  });

  test('does not show upgrade button for current plan', () => {
    render(<PlanCard plan={freePlan} current={true} />);
    
    expect(screen.queryByText(/Upgrade to/i)).not.toBeInTheDocument();
  });

  test('renders all features', () => {
    render(<PlanCard plan={freePlan} />);
    
    expect(screen.getByText('3 active agents')).toBeInTheDocument();
    expect(screen.getByText('Manual bidding only')).toBeInTheDocument();
    expect(screen.getByText('Basic analytics')).toBeInTheDocument();
  });

  test('applies correct color scheme for FREE plan', () => {
    const { container } = render(<PlanCard plan={freePlan} />);
    
    expect(container.querySelector('.border-gray-300')).toBeInTheDocument();
    expect(container.querySelector('.bg-gray-100')).toBeInTheDocument();
  });

  test('applies correct color scheme for PRO plan', () => {
    const { container } = render(<PlanCard plan={proPlan} />);
    
    expect(container.querySelector('.border-blue-400')).toBeInTheDocument();
    expect(container.querySelector('.bg-blue-50')).toBeInTheDocument();
  });

  test('displays correct tooltip text', () => {
    render(<PlanCard plan={freePlan} />);
    
    expect(screen.getByText('Limited to 3 active agents')).toBeInTheDocument();
  });

  test('shows monthly pricing', () => {
    render(<PlanCard plan={proPlan} />);
    
    expect(screen.getByText('$49.99')).toBeInTheDocument();
    expect(screen.getByText('/month')).toBeInTheDocument();
  });
});
