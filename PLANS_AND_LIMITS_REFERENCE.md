# Plans & Limits Reference

**Last Updated:** November 2, 2025  
**Version:** 1.0

---

## Overview

This document provides detailed specifications for all subscription plans, agent limits, and quota enforcement mechanisms in the Antika Auction Watcher platform.

---

## ?? Subscription Plans

### FREE Plan

**Target Audience:** Individual hobbyists and small-scale collectors

**Price:** $0/month

**Agent Limit:** 3 active agents

**Features:**
- ? 3 active agents (watchers only)
- ? Manual bidding
- ? Basic analytics dashboard
- ? 7-day data retention
- ? Email notifications
- ? Community support (forum)
- ? No automatic bidding
- ? No CSV export
- ? No API access

**Limitations:**
- Cannot create bidder agents
- Limited historical data access
- Standard support response time (48-72 hours)
- No priority queue for AI recommendations

**Typical Use Case:**
```
A casual antique collector who wants to monitor a few specific 
auction categories without active bidding automation.
```

---

### PRO Plan

**Target Audience:** Professional dealers and serious collectors

**Price:** $49.99/month

**Agent Limit:** 25 active agents

**Features:**
- ? 25 active agents (watchers + bidders)
- ? Automatic bidding with custom strategies
- ? Advanced analytics & insights
- ? 30-day data retention
- ? Learning insights panel
- ? Email + SMS notifications
- ? CSV export functionality
- ? Priority support (24-hour response)
- ? AI advisor with performance tracking
- ? No API access
- ? No white-label options

**Limitations:**
- No custom integrations
- Standard SLA (no guaranteed uptime)
- Shared AI processing queue

**Typical Use Case:**
```
A professional antique dealer managing multiple auction streams 
with automated bidding for high-value items across various categories.
```

---

### ENTERPRISE Plan

**Target Audience:** Large-scale dealers, auction houses, investment firms

**Price:** $199.99/month (custom pricing available for >100 agents)

**Agent Limit:** 100 active agents

**Features:**
- ? 100 active agents (unlimited types)
- ? Custom agent strategies & algorithms
- ? Real-time market analysis
- ? Unlimited data retention
- ? Full API access (REST + WebSocket)
- ? White-label options
- ? Dedicated account manager
- ? Priority AI processing queue
- ? Custom integrations
- ? Multi-team management
- ? Advanced role-based access control
- ? 99.9% SLA guarantee
- ? 24/7 dedicated support (1-hour response)

**Additional Enterprise Options:**
- Custom agent development
- On-premise deployment
- SSO integration (SAML, OAuth)
- Compliance certifications (SOC2, HIPAA)
- Training & onboarding sessions

**Typical Use Case:**
```
An auction house or investment firm managing hundreds of simultaneous 
auctions with complex bidding strategies and integration into existing 
enterprise systems.
```

---

## ?? Agent Quotas & Enforcement

### How Limits Work

**1. Active Agent Count**
- **Definition:** Agents with status = `running` or `paused`
- **Tracked In:** Redis SET `team:{id}:active_agents`
- **Enforcement:** Before starting a new agent, system checks:
  ```python
  active_count = redis.scard(f"team:{team_id}:active_agents")
  if active_count >= plan.agent_limit:
      raise HTTPException(402, "Plan limit reached")
  ```

**2. Agent States**
- `running` ? Counts toward limit
- `paused` ? Counts toward limit (paused but not deleted)
- `stopped` ? Does NOT count toward limit

**3. Freed Slots**
- Stopping an agent immediately frees a slot
- Slot becomes available for new agent creation
- No cooldown or waiting period

### Daily Start Counter

**Purpose:** Track agent creation frequency for abuse detection

**Implementation:**
- Redis key: `team:{id}:starts:{YYYY-MM-DD}`
- Increments on each `start_agent()` call
- Resets automatically at midnight UTC
- Stored for 30 days (auto-expiring)

**Example Usage:**
```python
today = datetime.utcnow().strftime("%Y-%m-%d")
daily_starts = await redis.get(f"team:{team_id}:starts:{today}")
```

**Future Use Cases:**
- Rate limiting (e.g., max 100 starts per day)
- Abuse detection (unusual spike in starts)
- Usage analytics and billing
- Plan upgrade recommendations

---

## ?? Usage Statistics

### Metrics Tracked

**1. Active Agents**
```python
{
  "active_agents": 15,        # Currently running/paused
  "agent_limit": 25,          # Plan-defined limit
  "available_slots": 10,      # Remaining capacity
  "utilization_percent": 60.0 # (active / limit) * 100
}
```

**2. Daily Activity**
```python
{
  "daily_starts": 42,  # Agents started today
  "total_agents": 20   # All agents (active + stopped)
}
```

**3. Historical Snapshots**
- Recorded hourly by `usage_tracker.py`
- Stored in `usage` table
- Includes: `active_agents`, `daily_starts`, `timestamp`
- Retention: 30 days (configurable)

**4. Summary Statistics**
```python
{
  "avg_active_agents": 12.5,  # Average over period
  "max_active_agents": 18,    # Peak usage
  "min_active_agents": 8,     # Lowest usage
  "total_starts": 156,        # Cumulative starts
  "data_points": 24           # Number of snapshots
}
```

---

## ?? Limit Enforcement Flow

### Starting a New Agent

```
1. User clicks "Start Agent" button
   ?
2. Frontend checks usageStats.available_slots
   ?
3. If available_slots = 0:
      Show "Upgrade Plan" modal
      Prevent API call
   ?
4. If available_slots > 0:
      Call POST /api/agents/start
   ?
5. Backend AgentManager.start_agent():
      a. Get team plan ? get_plan_limit()
      b. Count active agents ? redis.scard()
      c. If active >= limit:
            Raise HTTPException 402
      d. Else:
            Create agent in DB
            Add to Redis SET
            Increment daily counter
            Return agent config
   ?
6. Frontend updates usageStats
   Frontend refreshes agent list
```

### Error Handling

**HTTP 402 Payment Required**
```json
{
  "status_code": 402,
  "detail": {
    "message": "Plan limit reached. Your FREE plan allows 3 active agents.",
    "plan_code": "FREE",
    "upgrade_url": "/settings/plan",
    "current_active": 3,
    "plan_limit": 3
  }
}
```

**Frontend Response:**
```typescript
if (error.status === 402) {
  if (confirm('Plan limit reached. Upgrade now?')) {
    window.location.href = error.detail.upgrade_url;
  }
}
```

---

## ?? Plan Upgrades & Downgrades

### Upgrade Process

**1. User Action**
- Navigate to `/settings/plan`
- Click "Upgrade to PRO" button
- Confirm upgrade (alert/modal)

**2. Backend (Future Implementation)**
```python
# Payment processing
stripe.create_subscription(team_id, "PRO")

# Update team plan
team.plan_code = "PRO"
db.commit()

# Immediately effective - no restart needed
```

**3. Effect on Agents**
- Existing agents continue running
- New higher limit immediately available
- No disruption to active monitoring

### Downgrade Process

**1. User Action**
- Navigate to `/settings/plan`
- Request downgrade (requires owner role)
- Effective at end of billing cycle

**2. Backend Handling**
```python
if active_agents > new_plan.agent_limit:
    # Send warning email
    # Grace period: 7 days
    # After grace: oldest agents auto-stopped
```

**3. Agent Handling**
- If active agents > new limit:
  - User notified to stop agents
  - Auto-stop oldest agents after grace period
  - User can choose which agents to keep

---

## ?? Utilization Thresholds

### Color-Coded Warnings

**Green (0-69% utilization)**
```
Status: Healthy
Action: None required
UI Color: Green (#10B981)
```

**Yellow (70-89% utilization)**
```
Status: Warning
Action: Consider stopping unused agents or upgrading
UI Color: Yellow (#F59E0B)
Message: "?? You're running low on agent slots."
```

**Red (90-100% utilization)**
```
Status: Critical
Action: Stop agents or upgrade immediately
UI Color: Red (#EF4444)
Message: "?? You've reached your plan limit."
```

### Auto-Recommendations

**At 90% utilization:**
```
"You're running low on agent slots. 
Consider stopping unused agents or upgrading your plan."
```

**At 100% utilization:**
```
"You've reached your plan limit. 
Stop an agent or upgrade to start more."

[Upgrade to PRO] [View Agents]
```

---

## ?? Quota Calculation Examples

### Example 1: FREE Plan User

**Scenario:**
- Plan: FREE (3 agent limit)
- Active agents: 2 running
- Stopped agents: 1

**Calculation:**
```
Active Count = 2 (running)
Available Slots = 3 - 2 = 1
Utilization = (2 / 3) ? 100 = 66.67%
Status = Green (healthy)
Can Start New Agent = Yes
```

### Example 2: PRO Plan at Limit

**Scenario:**
- Plan: PRO (25 agent limit)
- Active agents: 20 running, 5 paused
- Stopped agents: 10

**Calculation:**
```
Active Count = 20 + 5 = 25 (running + paused)
Available Slots = 25 - 25 = 0
Utilization = (25 / 25) ? 100 = 100%
Status = Red (at limit)
Can Start New Agent = No
```

### Example 3: ENTERPRISE with Headroom

**Scenario:**
- Plan: ENTERPRISE (100 agent limit)
- Active agents: 65 running, 10 paused
- Stopped agents: 50

**Calculation:**
```
Active Count = 65 + 10 = 75
Available Slots = 100 - 75 = 25
Utilization = (75 / 100) ? 100 = 75%
Status = Yellow (warning)
Can Start New Agent = Yes (25 slots available)
```

---

## ??? Administrative Tools

### Adjusting Plan Limits

**Method 1: Update Plan Definitions**
```python
# backend/services/plan_seeder.py
PLAN_DEFINITIONS = [
    {
        "code": PlanCode.PRO,
        "agent_limit": 50,  # Changed from 25
        # ...
    }
]

# Restart application to apply
```

**Method 2: Database Update (Hot Fix)**
```sql
UPDATE plans SET agent_limit = 50 WHERE code = 'PRO';
-- Takes effect immediately
```

### Resetting Usage Counters

**Clear daily starts:**
```bash
redis-cli DEL "team:1:starts:2025-11-02"
```

**Sync Redis with DB (cleanup stale entries):**
```python
await agent_manager.cleanup_stale_agents(team_id)
```

### Manual Override (Emergency)

**Temporarily increase limit (Redis only):**
```python
# Not recommended - for emergencies only
# Bypasses plan limits
await redis.sadd(f"team:{team_id}:active_agents", "manual_override_agent")
```

---

## ?? Monitoring & Alerts

### Metrics to Monitor

**1. Plan Distribution**
```sql
SELECT plan_code, COUNT(*) as team_count
FROM teams
GROUP BY plan_code;
```

**2. Average Utilization**
```sql
SELECT 
  t.plan_code,
  AVG(u.active_agents::float / p.agent_limit) as avg_utilization
FROM usage u
JOIN teams t ON u.team_id = t.id
JOIN plans p ON t.plan_code = p.code
WHERE u.timestamp > NOW() - INTERVAL '24 hours'
GROUP BY t.plan_code;
```

**3. Teams Near Limit**
```sql
SELECT t.id, t.name, u.active_agents, p.agent_limit
FROM teams t
JOIN usage u ON u.team_id = t.id
JOIN plans p ON t.plan_code = p.code
WHERE u.active_agents >= p.agent_limit * 0.9
ORDER BY u.active_agents DESC;
```

### Prometheus Metrics

```python
# backend/middleware/metrics.py
agent_usage_total = Gauge(
    'agent_usage_total',
    'Total active agents across all teams'
)

agent_limit_exceeded_total = Counter(
    'agent_limit_exceeded_total',
    'Number of times agent limit was reached'
)

plan_upgrade_requests_total = Counter(
    'plan_upgrade_requests_total',
    'Number of plan upgrade requests'
)
```

---

## ?? Security Considerations

### Quota Bypass Prevention

**1. Redis Integrity**
- Periodic sync between Redis and database
- `cleanup_stale_agents()` removes orphaned entries
- Database is source of truth

**2. Rate Limiting**
- Prevent rapid agent creation/deletion cycles
- Daily start counter for abuse detection
- API rate limits on `/api/agents/start` endpoint

**3. Team Context Validation**
- Every agent operation requires valid X-Team-Id
- Membership verification before agent access
- Role-based permissions enforced

### Audit Logging

**Track agent operations:**
```python
log.info(
    "Agent started",
    extra={
        "team_id": team_id,
        "agent_id": agent.id,
        "user_id": user_id,
        "plan_code": team.plan_code,
        "active_agents": active_count,
        "daily_starts": daily_starts
    }
)
```

---

## ?? API Examples

### Check Current Usage

```bash
GET /api/v1/agents/usage/1
Authorization: Bearer {token}
X-Team-Id: 1
```

**Response:**
```json
{
  "team_id": 1,
  "plan_code": "PRO",
  "agent_limit": 25,
  "active_agents": 15,
  "available_slots": 10,
  "daily_starts": 42,
  "total_agents": 20,
  "utilization_percent": 60.0
}
```

### List Plans

```bash
GET /api/v1/plans
```

**Response:**
```json
[
  {
    "code": "FREE",
    "agent_limit": 3,
    "description": "Up to 3 AI watcher agents, no autobid",
    "features": ["3 active agents", "Manual bidding only"],
    "price_monthly": 0.0
  },
  {
    "code": "PRO",
    "agent_limit": 25,
    "description": "Up to 25 watcher/bidder agents",
    "features": ["25 active agents", "Automatic bidding"],
    "price_monthly": 49.99
  }
]
```

---

## ?? Future Enhancements

**1. Dynamic Limits**
- Per-user overrides (e.g., beta testers)
- Temporary limit boosts for events
- Graduated limits based on usage history

**2. Resource Quotas**
- CPU/memory limits per agent
- Network bandwidth quotas
- Storage limits for historical data

**3. Usage-Based Pricing**
- Pay-per-agent model
- Overage charges above plan limit
- Volume discounts for large teams

**4. Advanced Analytics**
- Predictive limit warnings
- Usage optimization recommendations
- Idle agent detection and auto-stop

---

**Document Version:** 1.0  
**Last Review:** November 2, 2025  
**Next Review:** December 1, 2025
