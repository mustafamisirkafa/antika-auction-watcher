/**
 * Plan Card Component
 * Displays plan details with features and pricing
 */
import React from 'react';

interface Plan {
  code: 'FREE' | 'PRO' | 'ENTERPRISE';
  agent_limit: number;
  description: string;
  features: string[];
  price_monthly: number;
}

interface PlanCardProps {
  plan: Plan;
  current?: boolean;
  onUpgrade?: () => void;
}

const planColors = {
  FREE: {
    bg: 'bg-gray-100',
    border: 'border-gray-300',
    text: 'text-gray-700',
    button: 'bg-gray-500 hover:bg-gray-600',
  },
  PRO: {
    bg: 'bg-blue-50',
    border: 'border-blue-400',
    text: 'text-blue-700',
    button: 'bg-blue-600 hover:bg-blue-700',
  },
  ENTERPRISE: {
    bg: 'bg-yellow-50',
    border: 'border-yellow-500',
    text: 'text-yellow-700',
    button: 'bg-yellow-600 hover:bg-yellow-700',
  },
};

export default function PlanCard({ plan, current = false, onUpgrade }: PlanCardProps) {
  const colors = planColors[plan.code];

  return (
    <div
      className={`relative p-6 rounded-lg border-2 ${colors.border} ${colors.bg} transition-all ${
        current ? 'ring-4 ring-offset-2 ring-blue-400' : ''
      }`}
    >
      {current && (
        <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
          <span className="bg-blue-600 text-white px-3 py-1 rounded-full text-sm font-semibold">
            Current Plan
          </span>
        </div>
      )}

      <div className="text-center mb-4">
        <h3 className={`text-2xl font-bold ${colors.text}`}>{plan.code}</h3>
        <p className="text-gray-600 text-sm mt-1">{plan.description}</p>
      </div>

      <div className="text-center mb-6">
        <span className="text-4xl font-bold">${plan.price_monthly}</span>
        <span className="text-gray-600">/month</span>
      </div>

      <div className="mb-6">
        <div className="flex items-center justify-center mb-2">
          <span className="text-3xl font-bold text-gray-800">{plan.agent_limit}</span>
          <span className="text-gray-600 ml-2">AI Agents</span>
        </div>
        <div className="text-center text-sm text-gray-500">
          {plan.code === 'FREE' && 'Limited to 3 active agents'}
          {plan.code === 'PRO' && 'Up to 25 AI agents'}
          {plan.code === 'ENTERPRISE' && 'Unlimited access, prioritized AI queue'}
        </div>
      </div>

      <ul className="space-y-2 mb-6">
        {plan.features.map((feature, index) => (
          <li key={index} className="flex items-start">
            <svg
              className={`w-5 h-5 ${colors.text} mr-2 flex-shrink-0 mt-0.5`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M5 13l4 4L19 7"
              />
            </svg>
            <span className="text-gray-700 text-sm">{feature}</span>
          </li>
        ))}
      </ul>

      {!current && onUpgrade && (
        <button
          onClick={onUpgrade}
          className={`w-full py-2 px-4 rounded-lg text-white font-semibold ${colors.button} transition-colors`}
        >
          Upgrade to {plan.code}
        </button>
      )}

      {current && (
        <div className="w-full py-2 px-4 rounded-lg bg-gray-300 text-gray-600 font-semibold text-center">
          Active Plan
        </div>
      )}
    </div>
  );
}
