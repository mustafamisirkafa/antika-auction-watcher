# Agent Management Guide

**Last Updated:** November 2, 2025  
**Version:** 1.0

---

## Overview

This guide provides comprehensive instructions for managing AI auction agents in the Antika Auction Watcher platform, including creation, configuration, monitoring, and lifecycle management with plan-based quota enforcement.

---

## ?? Table of Contents

1. [Agent Types](#agent-types)
2. [Agent Lifecycle](#agent-lifecycle)
3. [Creating Agents](#creating-agents)
4. [Managing Agents](#managing-agents)
5. [Monitoring Usage](#monitoring-usage)
6. [Plan Limits](#plan-limits)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)

---

## ?? Agent Types

### 1. Watcher Agents

**Purpose:** Monitor auctions and send alerts

**Capabilities:**
- Track specific categories or sellers
- Real-time price monitoring
- Bid activity alerts
- Valuation updates
- Notification delivery

**Configuration Options:**
```json
{
  "name": "Ceramics Watcher",
  "type": "watcher",
  "category": "ceramics",
  "seller_filter": "antique_masters",
  "min_value": 500,
  "max_value": 5000,
  "notify_on": ["new_item", "bid_update", "ending_soon"]
}
```

**Typical Use Cases:**
- Monitoring rare item categories
- Tracking specific sellers
- Price range alerts
- Market research

---

### 2. Bidder Agents (PRO/ENTERPRISE only)

**Purpose:** Automated bidding with custom strategies

**Capabilities:**
- Automatic bid placement
- Strategy-based bidding (snipe, incremental, aggressive)
- Budget management
- Conflict resolution (multiple items)
- Risk assessment

**Configuration Options:**
```json
{
  "name": "Furniture Bidder",
  "type": "bidder",
  "category": "furniture",
  "max_bid": 2000,
  "strategy": "snipe",
  "confidence_threshold": 0.8,
  "auto_bid": true,
  "bid_increment": 50,
  "time_buffer_seconds": 30
}
```

**Bidding Strategies:**
- **Snipe:** Bid in last 30 seconds
- **Incremental:** Gradually increase bid
- **Aggressive:** Immediate maximum bid
- **Conservative:** Slow, calculated bidding

---

### 3. Analyzer Agents (ENTERPRISE only)

**Purpose:** Market analysis and trend detection

**Capabilities:**
- Historical price analysis
- Seller reputation tracking
- Market trend identification
- Valuation accuracy reporting
- Predictive analytics

**Configuration Options:**
```json
{
  "name": "Market Analyzer",
  "type": "analyzer",
  "analysis_type": "trend_detection",
  "lookback_days": 90,
  "categories": ["paintings", "sculptures"],
  "report_frequency": "daily"
}
```

---

## ?? Agent Lifecycle

### State Diagram

```
   [Creating]
       ?
   [Running] ?? [Paused]
       ?
   [Stopped]
```

### State Descriptions

**Creating**
- Agent configuration being validated
- Database record created
- Redis entry added
- Temporary state (< 1 second)

**Running**
- Agent actively monitoring/bidding
- Consuming compute resources
- Counts toward plan limit
- Receives notifications

**Paused**
- Agent temporarily halted
- Configuration preserved
- Still counts toward plan limit
- Can resume quickly

**Stopped**
- Agent permanently stopped
- Does NOT count toward plan limit
- Configuration saved
- Can be restarted (creates new agent)

---

## ?? Creating Agents

### Step-by-Step: Via Web UI

**1. Navigate to Dashboard**
```
/dashboard ? Click "Start Agent" button
```

**2. Check Available Slots**
- Agent usage bar shows current utilization
- Green: plenty of slots available
- Yellow: near limit (70-89% used)
- Red: at limit (90-100% used)

**3. Fill Agent Configuration**
```typescript
{
  name: "My Watcher",           // Required
  type: "watcher",              // Required
  category: "ceramics",         // Optional
  max_bid: 1000,               // For bidders only
  auto_bid: false              // For bidders only
}
```

**4. Submit**
- If slot available: Agent starts immediately
- If limit reached: See upgrade modal

**Example Modal (Limit Reached):**
```
?? Plan Limit Reached

You've reached your FREE plan limit of 3 active agents.

Current Usage:
? Active: 3/3 agents
? Daily Starts: 15

Options:
[Stop an Agent] [Upgrade to PRO]

Note: Stopping an agent frees a slot immediately.
```

---

### Step-by-Step: Via API

**1. Check Current Usage**

```bash
GET /api/v1/agents/usage/{team_id}
Authorization: Bearer {token}
X-Team-Id: 1
```

**Response:**
```json
{
  "active_agents": 2,
  "agent_limit": 3,
  "available_slots": 1
}
```

**2. Start Agent**

```bash
POST /api/v1/agents/start
Authorization: Bearer {token}
X-Team-Id: 1
Content-Type: application/json

{
  "name": "Ceramics Watcher",
  "type": "watcher",
  "config": {
    "category": "ceramics",
    "min_value": 500,
    "max_value": 5000
  }
}
```

**Success Response (201):**
```json
{
  "id": 15,
  "team_id": 1,
  "name": "Ceramics Watcher",
  "agent_type": "watcher",
  "status": "running",
  "created_by": 1,
  "created_at": "2025-11-02T12:00:00Z",
  "last_started_at": "2025-11-02T12:00:00Z",
  "last_stopped_at": null
}
```

**Error Response (402 - Limit Reached):**
```json
{
  "detail": {
    "message": "Plan limit reached. Your FREE plan allows 3 active agents. Upgrade to enable more.",
    "plan_code": "FREE",
    "upgrade_url": "/settings/plan"
  }
}
```

---

## ?? Managing Agents

### Listing Agents

**Web UI:**
```
/dashboard ? Agents tab ? View all agents
```

**API:**
```bash
GET /api/v1/agents
Authorization: Bearer {token}
X-Team-Id: 1
```

**Response:**
```json
[
  {
    "id": 15,
    "name": "Ceramics Watcher",
    "agent_type": "watcher",
    "status": "running",
    "created_at": "2025-11-02T12:00:00Z"
  },
  {
    "id": 16,
    "name": "Furniture Bidder",
    "agent_type": "bidder",
    "status": "paused",
    "created_at": "2025-11-02T13:00:00Z"
  }
]
```

---

### Stopping Agents

**When to Stop:**
- No longer needed
- Freeing slot for new agent
- End of auction season
- Budget constraints

**Effect:**
- Agent stops immediately
- Frees slot (available_slots + 1)
- Configuration saved
- Can restart later (creates new agent)

**API:**
```bash
POST /api/v1/agents/15/stop
Authorization: Bearer {token}
X-Team-Id: 1
```

**Response (200):**
```json
{
  "id": 15,
  "status": "stopped",
  "last_stopped_at": "2025-11-02T14:00:00Z"
}
```

---

### Pausing Agents

**When to Pause:**
- Temporary break (e.g., vacation)
- Testing other agents
- Troubleshooting issues
- Preserving configuration

**Effect:**
- Agent halts execution
- Still counts toward limit
- Can resume quickly
- No slot freed

**API:**
```bash
POST /api/v1/agents/15/pause
Authorization: Bearer {token}
X-Team-Id: 1
```

**Response (200):**
```json
{
  "id": 15,
  "status": "paused",
  "last_stopped_at": null
}
```

---

### Resuming Agents

**To Resume a Paused Agent:**

1. **Paused ? Running:** No API endpoint yet (future feature)
2. **Stopped ? New Agent:** Create new agent with same config

**Workaround (Stopped Agents):**
```bash
# Get original config
GET /api/v1/agents/15

# Start new agent with same config
POST /api/v1/agents/start
{
  "name": "Ceramics Watcher (Restart)",
  "type": "watcher",
  "config": {...}  # Copy from GET response
}
```

---

### Deleting Agents

**Currently:** Stop agent (soft delete)

**Future:** Hard delete API

```bash
# Future endpoint
DELETE /api/v1/agents/15
Authorization: Bearer {token}
X-Team-Id: 1
```

**Effect:**
- Agent removed from database
- Redis entries cleaned up
- Historical data preserved (usage snapshots)

---

## ?? Monitoring Usage

### Usage Dashboard

**Location:** `/settings/plan`

**Metrics Displayed:**
- **Active Agents:** Currently running + paused
- **Available Slots:** Remaining capacity
- **Daily Starts:** Agents started today
- **Utilization:** Percentage of limit used

**Example:**
```
???????????????????????????????????????
?  Current Usage                       ?
???????????????????????????????????????
?  Active Agents        15 / 25       ?
?  Available Slots      10             ?
?  Starts Today         42             ?
?  Utilization          60.0%          ?
???????????????????????????????????????
```

---

### Usage Bar

**Visual Indicator:**
```
Agent Usage: 15 / 25
[????????????????????] 60%

10 slots available
42 starts today
```

**Color Coding:**
- **Green (0-69%):** Healthy
- **Yellow (70-89%):** Warning
- **Red (90-100%):** Critical

---

### Historical Usage

**API Endpoint:**
```bash
GET /api/v1/usage/{team_id}/history?hours=24
Authorization: Bearer {token}
X-Team-Id: 1
```

**Response:**
```json
{
  "team_id": 1,
  "hours": 24,
  "avg_active_agents": 12.5,
  "max_active_agents": 18,
  "min_active_agents": 8,
  "total_starts": 156,
  "data_points": 24
}
```

---

## ?? Plan Limits

### Checking Limits

**Web UI:** `/settings/plan`

**API:**
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
  "available_slots": 10
}
```

---

### Handling Limit Reached

**Scenario 1: Stop Unused Agents**

1. **Identify idle agents:**
```bash
GET /api/v1/agents
# Find agents with low activity
```

2. **Stop idle agent:**
```bash
POST /api/v1/agents/12/stop
```

3. **Start new agent:**
```bash
POST /api/v1/agents/start
```

**Scenario 2: Upgrade Plan**

1. Navigate to `/settings/plan`
2. Compare plans
3. Click "Upgrade to PRO"
4. New limit immediately effective

**Scenario 3: Pause Temporarily**

1. Pause agent (keeps config, frees slot)
```bash
POST /api/v1/agents/12/pause
```

2. Start new agent

3. Resume paused agent later (future feature)

---

### Plan Comparison

| Plan | Agents | Monthly Cost | When to Upgrade |
|------|--------|--------------|-----------------|
| **FREE** | 3 | $0 | Need more than 3 agents |
| **PRO** | 25 | $49.99 | Running 20+ agents |
| **ENTERPRISE** | 100 | $199.99 | Running 80+ agents, need API |

---

## ?? Best Practices

### 1. Agent Naming

**Good Names:**
- `Ceramics_Watcher_Europe`
- `Furniture_Bidder_Budget1K`
- `Market_Analyzer_Q4_2025`

**Bad Names:**
- `Agent1`, `Agent2`, `Agent3`
- `test`, `temp`, `asdf`
- `my_agent_really_long_name_that_doesnt_fit_in_ui`

**Best Practice:**
```
{type}_{category}_{specific_detail}

Examples:
- watcher_paintings_impressionist
- bidder_furniture_victorian_max2k
- analyzer_ceramics_trending
```

---

### 2. Resource Optimization

**Consolidate Agents:**
```
? Bad: 10 separate watcher agents for 10 categories
? Good: 1 watcher agent monitoring 10 categories
```

**Stop Inactive Agents:**
```
# Check last activity
GET /api/v1/agents/15/stats

# If inactive > 7 days, consider stopping
POST /api/v1/agents/15/stop
```

**Use Pausing Strategically:**
```
? Pause: Weekend break, short-term test
? Pause: Long-term storage (use stop instead)
```

---

### 3. Configuration Management

**Save Configurations:**
```typescript
// Export agent configs
const configs = agents.map(a => ({
  name: a.name,
  type: a.agent_type,
  config: JSON.parse(a.config_json)
}));

localStorage.setItem('agent_templates', JSON.stringify(configs));
```

**Template Reuse:**
```typescript
// Load template
const template = templates.find(t => t.name === 'Ceramics Watcher');

// Create new agent from template
await createAgent({
  ...template,
  name: `${template.name} - ${region}`
});
```

---

### 4. Monitoring Alerts

**Set Up Notifications:**
- Agent started/stopped
- Limit approaching (85%)
- Limit reached (100%)
- Agent errors
- Budget exceeded (bidders)

**Example Alert:**
```
?? Agent Limit Warning

Your team is at 85% capacity (21/25 agents).

Consider:
? Stopping unused agents
? Upgrading to ENTERPRISE (100 agents)

[View Agents] [Upgrade Plan]
```

---

### 5. Team Collaboration

**Role Assignment:**
```
Owner ? Plan management, billing
Admin ? Add/remove team members
Analyst ? Start/stop agents, configure
Viewer ? Monitor dashboards
```

**Communication:**
- Document agent purposes
- Coordinate agent creation
- Avoid duplicate agents
- Share successful strategies

---

## ?? Troubleshooting

### Problem: "Plan limit reached" but I have stopped agents

**Cause:** Stopped agents don't count, but paused agents do

**Solution:**
```bash
# List all agents
GET /api/v1/agents

# Check for paused agents
# Convert paused ? stopped
POST /api/v1/agents/{paused_agent_id}/stop
```

---

### Problem: Agent not appearing in list

**Cause:** Wrong team context or agent recently created

**Solution:**
```bash
# Verify team ID
GET /api/v1/teams
# Ensure X-Team-Id matches

# Refresh agent list
GET /api/v1/agents
```

---

### Problem: Cannot start agent (403 Forbidden)

**Cause:** Insufficient role permissions

**Solution:**
```bash
# Check your role
GET /api/v1/teams/1/members

# If VIEWER, ask ADMIN to change role to ANALYST
```

---

### Problem: Usage stats not updating

**Cause:** Frontend cache or Redis sync issue

**Solution:**
```typescript
// Force refresh
useTeamStore.getState().refreshUsage();

// Or reload page
window.location.reload();
```

---

### Problem: Agent stuck in "creating" state

**Cause:** Backend error during creation

**Solution:**
```bash
# Check backend logs
docker logs antika_backend

# Manually cleanup (if needed)
# Stop agent (will transition to stopped)
POST /api/v1/agents/{agent_id}/stop
```

---

## ?? API Reference Quick Guide

### Agent Operations

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/agents` | GET | List all agents |
| `/api/v1/agents/start` | POST | Start new agent |
| `/api/v1/agents/{id}` | GET | Get agent details |
| `/api/v1/agents/{id}/stop` | POST | Stop agent |
| `/api/v1/agents/{id}/pause` | POST | Pause agent |
| `/api/v1/agents/usage/{team_id}` | GET | Get usage stats |

### Required Headers

```http
Authorization: Bearer {jwt_token}
X-Team-Id: {team_id}
Content-Type: application/json
```

### Example: Complete Agent Lifecycle

```bash
# 1. Check usage
GET /api/v1/agents/usage/1

# 2. Start agent
POST /api/v1/agents/start
{
  "name": "Test Watcher",
  "type": "watcher"
}

# 3. List agents
GET /api/v1/agents

# 4. Pause agent
POST /api/v1/agents/15/pause

# 5. Stop agent
POST /api/v1/agents/15/stop

# 6. Verify usage updated
GET /api/v1/agents/usage/1
```

---

## ?? Future Features

**Coming Soon:**
- Agent templates
- Bulk agent operations
- Agent performance metrics
- Agent scheduling (start/stop on schedule)
- Agent cloning
- Agent export/import

**Planned:**
- Machine learning-based agent optimization
- Agent collaboration (multi-agent strategies)
- Resource quotas (CPU/memory per agent)
- Agent marketplace (share configurations)

---

## ?? Support

**Questions?**
- Documentation: `/docs/agent-management`
- Community: `forum.antika-auction.com`
- Email: `support@antika-auction.com`

**Reporting Issues:**
```bash
# Include in support request:
1. Team ID
2. Agent ID (if applicable)
3. Steps to reproduce
4. Error messages (screenshots helpful)
5. Browser/OS info
```

---

**Document Version:** 1.0  
**Last Review:** November 2, 2025  
**Next Review:** December 1, 2025
