/**
 * Plan Settings Page
 * Display current plan, agent quota, and upgrade options
 */
import React, { useEffect, useState } from 'react';
import { useTeamStore, Plan } from '@/store/teamStore';
import PlanCard from '@/components/PlanCard';
import AgentUsageBar from '@/components/AgentUsageBar';

export default function PlanSettings() {
  const { currentTeam, currentPlan, usageStats, fetchCurrentPlan, fetchUsageStats } =
    useTeamStore();
  const [allPlans, setAllPlans] = useState<Plan[]>([]);
  const [loading, setLoading] = useState(false);

  const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api/v1';

  useEffect(() => {
    fetchPlans();
    if (currentTeam) {
      fetchCurrentPlan();
      fetchUsageStats(currentTeam.id);
    }
  }, [currentTeam]);

  const fetchPlans = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/plans`);

      if (!response.ok) throw new Error('Failed to fetch plans');

      const plans = await response.json();
      setAllPlans(plans);
    } catch (error) {
      console.error('Failed to fetch plans:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleUpgrade = (planCode: string) => {
    // In a real app, this would open a payment/upgrade modal
    alert(
      `Upgrade to ${planCode} plan.\n\nIn production, this would:\n1. Open payment modal\n2. Process payment\n3. Update team plan\n4. Refresh limits`
    );
  };

  if (!currentTeam) {
    return (
      <div className="p-6">
        <div className="bg-yellow-100 border border-yellow-400 text-yellow-800 p-4 rounded-lg">
          ?? No team selected. Please select a team first.
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Plan & Usage</h1>
        <p className="text-gray-600 mt-1">Manage your subscription and agent quotas</p>
      </div>

      {/* Current Usage */}
      {usageStats && (
        <div className="bg-white rounded-lg shadow-md p-6 mb-8">
          <h2 className="text-xl font-semibold mb-4">Current Usage</h2>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
            <div className="bg-blue-50 rounded-lg p-4">
              <div className="text-sm text-gray-600 mb-1">Active Agents</div>
              <div className="text-3xl font-bold text-blue-700">
                {usageStats.active_agents}
              </div>
              <div className="text-sm text-gray-500">
                of {usageStats.agent_limit} available
              </div>
            </div>

            <div className="bg-green-50 rounded-lg p-4">
              <div className="text-sm text-gray-600 mb-1">Available Slots</div>
              <div className="text-3xl font-bold text-green-700">
                {usageStats.available_slots}
              </div>
              <div className="text-sm text-gray-500">ready to use</div>
            </div>

            <div className="bg-purple-50 rounded-lg p-4">
              <div className="text-sm text-gray-600 mb-1">Starts Today</div>
              <div className="text-3xl font-bold text-purple-700">
                {usageStats.daily_starts}
              </div>
              <div className="text-sm text-gray-500">agent activations</div>
            </div>
          </div>

          <AgentUsageBar
            activeAgents={usageStats.active_agents}
            agentLimit={usageStats.agent_limit}
            dailyStarts={usageStats.daily_starts}
          />

          <div className="mt-4 p-3 bg-gray-50 rounded-lg">
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-600">Utilization:</span>
              <span className="font-semibold text-gray-900">
                {usageStats.utilization_percent.toFixed(1)}%
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Current Plan */}
      {currentPlan && (
        <div className="bg-gradient-to-r from-blue-600 to-blue-800 rounded-lg shadow-lg p-6 mb-8 text-white">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold mb-2">
                You're on the {currentPlan.code} Plan
              </h2>
              <p className="text-blue-100">{currentPlan.description}</p>
            </div>
            <div className="text-right">
              <div className="text-4xl font-bold">${currentPlan.price_monthly}</div>
              <div className="text-blue-200">per month</div>
            </div>
          </div>
        </div>
      )}

      {/* Plan Comparison */}
      <div className="mb-8">
        <h2 className="text-2xl font-bold mb-6">Compare Plans</h2>

        {loading ? (
          <div className="text-center py-12 text-gray-500">Loading plans...</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {allPlans.map((plan) => (
              <PlanCard
                key={plan.code}
                plan={plan}
                current={currentPlan?.code === plan.code}
                onUpgrade={
                  currentPlan?.code !== plan.code
                    ? () => handleUpgrade(plan.code)
                    : undefined
                }
              />
            ))}
          </div>
        )}
      </div>

      {/* Plan Features Matrix */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h3 className="text-xl font-semibold mb-4">Feature Comparison</h3>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b-2 border-gray-200">
                <th className="text-left py-3 px-4 font-semibold text-gray-700">Feature</th>
                <th className="text-center py-3 px-4 font-semibold text-gray-700">FREE</th>
                <th className="text-center py-3 px-4 font-semibold text-gray-700">PRO</th>
                <th className="text-center py-3 px-4 font-semibold text-gray-700">
                  ENTERPRISE
                </th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-gray-100">
                <td className="py-3 px-4 font-medium">Active Agents</td>
                <td className="text-center py-3 px-4">3</td>
                <td className="text-center py-3 px-4">25</td>
                <td className="text-center py-3 px-4">100</td>
              </tr>
              <tr className="border-b border-gray-100">
                <td className="py-3 px-4 font-medium">Automatic Bidding</td>
                <td className="text-center py-3 px-4">?</td>
                <td className="text-center py-3 px-4">?</td>
                <td className="text-center py-3 px-4">?</td>
              </tr>
              <tr className="border-b border-gray-100">
                <td className="py-3 px-4 font-medium">Advanced Analytics</td>
                <td className="text-center py-3 px-4">?</td>
                <td className="text-center py-3 px-4">?</td>
                <td className="text-center py-3 px-4">?</td>
              </tr>
              <tr className="border-b border-gray-100">
                <td className="py-3 px-4 font-medium">Data Retention</td>
                <td className="text-center py-3 px-4">7 days</td>
                <td className="text-center py-3 px-4">30 days</td>
                <td className="text-center py-3 px-4">Unlimited</td>
              </tr>
              <tr className="border-b border-gray-100">
                <td className="py-3 px-4 font-medium">API Access</td>
                <td className="text-center py-3 px-4">?</td>
                <td className="text-center py-3 px-4">?</td>
                <td className="text-center py-3 px-4">?</td>
              </tr>
              <tr className="border-b border-gray-100">
                <td className="py-3 px-4 font-medium">Support</td>
                <td className="text-center py-3 px-4">Community</td>
                <td className="text-center py-3 px-4">Priority</td>
                <td className="text-center py-3 px-4">Dedicated</td>
              </tr>
              <tr className="border-b border-gray-100">
                <td className="py-3 px-4 font-medium">SLA</td>
                <td className="text-center py-3 px-4">-</td>
                <td className="text-center py-3 px-4">-</td>
                <td className="text-center py-3 px-4">99.9%</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* FAQ Section */}
      <div className="mt-8 bg-gray-50 rounded-lg p-6">
        <h3 className="text-lg font-semibold mb-4">Frequently Asked Questions</h3>
        <div className="space-y-4">
          <div>
            <h4 className="font-medium text-gray-900 mb-1">
              What happens if I reach my agent limit?
            </h4>
            <p className="text-sm text-gray-600">
              You won't be able to start new agents until you stop existing ones or upgrade
              your plan. Running agents will continue to operate normally.
            </p>
          </div>
          <div>
            <h4 className="font-medium text-gray-900 mb-1">Can I downgrade my plan?</h4>
            <p className="text-sm text-gray-600">
              Yes, you can downgrade at any time. Changes take effect at the end of your
              current billing cycle.
            </p>
          </div>
          <div>
            <h4 className="font-medium text-gray-900 mb-1">
              What's the difference between watcher and bidder agents?
            </h4>
            <p className="text-sm text-gray-600">
              Watcher agents monitor auctions and send alerts. Bidder agents can automatically
              place bids based on your strategy (PRO and ENTERPRISE plans only).
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
