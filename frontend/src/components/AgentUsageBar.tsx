/**
 * Agent Usage Bar Component
 * Shows progress bar for active agents vs limit
 */
import React from 'react';

interface AgentUsageBarProps {
  activeAgents: number;
  agentLimit: number;
  dailyStarts?: number;
}

export default function AgentUsageBar({
  activeAgents,
  agentLimit,
  dailyStarts,
}: AgentUsageBarProps) {
  const utilizationPercent = (activeAgents / agentLimit) * 100;
  const available = agentLimit - activeAgents;

  // Color based on utilization
  let barColor = 'bg-green-500';
  let textColor = 'text-green-700';
  let bgColor = 'bg-green-100';

  if (utilizationPercent >= 90) {
    barColor = 'bg-red-500';
    textColor = 'text-red-700';
    bgColor = 'bg-red-100';
  } else if (utilizationPercent >= 70) {
    barColor = 'bg-yellow-500';
    textColor = 'text-yellow-700';
    bgColor = 'bg-yellow-100';
  }

  return (
    <div className="space-y-2">
      {/* Header */}
      <div className="flex justify-between items-center">
        <span className="text-sm font-medium text-gray-700">Agent Usage</span>
        <span className={`text-sm font-semibold ${textColor}`}>
          {activeAgents} / {agentLimit}
        </span>
      </div>

      {/* Progress Bar */}
      <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
        <div
          className={`${barColor} h-full rounded-full transition-all duration-500 ease-out`}
          style={{ width: `${Math.min(utilizationPercent, 100)}%` }}
        />
      </div>

      {/* Stats */}
      <div className="flex justify-between items-center text-xs">
        <span className="text-gray-600">
          {available > 0 ? (
            <>
              {available} slot{available !== 1 ? 's' : ''} available
            </>
          ) : (
            <span className={textColor}>Limit reached</span>
          )}
        </span>
        {dailyStarts !== undefined && (
          <span className="text-gray-500">{dailyStarts} starts today</span>
        )}
      </div>

      {/* Warning when near limit */}
      {utilizationPercent >= 90 && available > 0 && (
        <div className={`${bgColor} border border-${textColor.replace('text-', '')} rounded-md p-2 text-xs ${textColor}`}>
          ?? You're running low on agent slots. Consider stopping unused agents or upgrading your plan.
        </div>
      )}

      {/* At limit message */}
      {available === 0 && (
        <div className="bg-red-100 border border-red-500 rounded-md p-2 text-xs text-red-700">
          ?? You've reached your plan limit. Stop an agent or upgrade to start more.
        </div>
      )}
    </div>
  );
}
