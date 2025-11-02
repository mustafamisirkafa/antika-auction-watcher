# Access Control Overview

**Last Updated:** November 2, 2025  
**Version:** 1.0

---

## Overview

Antika Auction Watcher implements a comprehensive **team-based access control system** with hierarchical roles and granular permissions. This document details the architecture, implementation, and usage of the access control mechanisms.

---

## ??? Architecture

### Core Components

```
???????????????????????????????????????????????????????????
?                    Team Entity                           ?
?  ? Owner (single user)                                  ?
?  ? Plan (FREE/PRO/ENTERPRISE)                           ?
?  ? Members (1-N users)                                  ?
???????????????????????????????????????????????????????????
                          ?
                          ??????????????????????????????????????????????
                          ?             ?              ?               ?
                     ???????????   ??????????    ??????????    ?????????????
                     ?  OWNER  ?   ? ADMIN  ?    ?ANALYST ?    ?  VIEWER   ?
                     ?  (Full) ?   ?(Manage)?    ?(Execute?    ? (Read-    ?
                     ?  Access ?   ?        ?    ?  & View?    ?  Only)    ?
                     ???????????   ??????????    ??????????    ?????????????
```

### Data Model

**Team**
```python
class Team(SQLModel, table=True):
    id: int
    name: str
    owner_id: int  # Foreign key to User
    plan_code: str  # FREE, PRO, ENTERPRISE
    created_at: datetime
```

**Membership**
```python
class Membership(SQLModel, table=True):
    id: int
    team_id: int
    user_id: int
    role: str  # OWNER, ADMIN, ANALYST, VIEWER
    joined_at: datetime
    invited_by: int  # Foreign key to User
```

**MemberRole (Enum)**
```python
class MemberRole(str, Enum):
    OWNER = "OWNER"      # Full control
    ADMIN = "ADMIN"      # Manage members & agents
    ANALYST = "ANALYST"  # Execute & view
    VIEWER = "VIEWER"    # Read-only
```

---

## ?? Role Hierarchy

### Permission Matrix

| Action | VIEWER | ANALYST | ADMIN | OWNER |
|--------|--------|---------|-------|-------|
| **View agents** | ? | ? | ? | ? |
| **View team** | ? | ? | ? | ? |
| **View analytics** | ? | ? | ? | ? |
| **Start/stop agents** | ? | ? | ? | ? |
| **Configure agents** | ? | ? | ? | ? |
| **Pause agents** | ? | ? | ? | ? |
| **Export data** | ? | ? | ? | ? |
| **Add members** | ? | ? | ? | ? |
| **Remove members** | ? | ? | ? | ? |
| **Change roles** | ? | ? | ? | ? |
| **Change plan** | ? | ? | ? | ? |
| **Delete team** | ? | ? | ? | ? |
| **Transfer ownership** | ? | ? | ? | ? |

### Role Descriptions

#### ?? OWNER

**Purpose:** Full administrative control over the team

**Permissions:**
- All ADMIN permissions
- Manage billing and subscriptions
- Delete team
- Transfer ownership
- Cannot be removed or demoted

**Typical Users:**
- Account creator
- Business owner
- Primary administrator

**Limitations:**
- Only one owner per team
- Owner role cannot be changed
- Owner cannot leave team (must transfer ownership first)

**Example:**
```python
if team_context.is_owner():
    # Can perform any action
    delete_team(team_id)
    change_plan(team_id, "ENTERPRISE")
```

---

#### ??? ADMIN

**Purpose:** Team management without financial control

**Permissions:**
- All ANALYST permissions
- Add/remove team members
- Change member roles (except OWNER)
- Manage team settings
- View all team data

**Typical Users:**
- Team managers
- Department heads
- Senior analysts

**Limitations:**
- Cannot access billing
- Cannot delete team
- Cannot change owner role
- Cannot remove owner

**Example:**
```python
if team_context.is_admin():
    # Can manage members
    add_member(team_id, user_id, "ANALYST")
    change_role(team_id, user_id, "VIEWER")
```

---

#### ?? ANALYST

**Purpose:** Execute operations and analyze data

**Permissions:**
- All VIEWER permissions
- Start/stop/pause agents
- Configure agent settings
- Export data to CSV
- Create reports

**Typical Users:**
- Auction analysts
- Data scientists
- Operations staff

**Limitations:**
- Cannot manage team members
- Cannot change team settings
- Read-only access to team configuration

**Example:**
```python
if team_context.is_analyst():
    # Can manage agents
    start_agent(team_id, config, user_id)
    export_data(team_id, "valuations.csv")
```

---

#### ?? VIEWER

**Purpose:** Read-only monitoring and observation

**Permissions:**
- View active agents
- View auctions and valuations
- View dashboards and analytics
- Receive notifications (if enabled)

**Typical Users:**
- Stakeholders
- Observers
- Auditors
- Junior staff

**Limitations:**
- No write operations
- Cannot start/stop agents
- Cannot export data
- Cannot change any settings

**Example:**
```python
if team_context.can_view():
    # Can only view
    agents = get_active_agents(team_id)
    stats = get_usage_stats(team_id)
```

---

## ?? TeamContext Class

### Implementation

```python
class TeamContext:
    """Team context attached to request for access control."""
    
    def __init__(
        self,
        team_id: int,
        team: Team,
        user_id: int,
        membership: Membership,
        role: str
    ):
        self.team_id = team_id
        self.team = team
        self.user_id = user_id
        self.membership = membership
        self.role = role
    
    # Permission checks
    def is_owner(self) -> bool:
        return self.role == MemberRole.OWNER
    
    def is_admin(self) -> bool:
        return self.role in [MemberRole.OWNER, MemberRole.ADMIN]
    
    def is_analyst(self) -> bool:
        return self.role in [MemberRole.OWNER, MemberRole.ADMIN, MemberRole.ANALYST]
    
    def can_manage_agents(self) -> bool:
        return self.is_analyst()
    
    def can_manage_members(self) -> bool:
        return self.is_admin()
    
    def can_view(self) -> bool:
        return True  # All roles can view
```

### Usage in Endpoints

```python
@router.post("/agents/start")
async def start_agent(
    agent_data: AgentStartRequest,
    team_context: TeamContext = Depends(get_team_context)
):
    # Check permissions
    if not team_context.can_manage_agents():
        raise HTTPException(403, "Insufficient permissions")
    
    # Perform action
    agent = await agent_manager.start_agent(
        team_context.team_id,
        agent_config,
        team_context.user_id
    )
    
    return agent
```

---

## ??? Middleware & Dependencies

### 1. Team Context Extraction

**Function:** `get_team_context(request, db, user_id, require_team=True)`

**Process:**
1. Extract `X-Team-Id` header
2. Validate team exists
3. Check user is team member
4. Load membership and role
5. Create TeamContext object

**Example Request:**
```http
POST /api/v1/agents/start
Authorization: Bearer {jwt_token}
X-Team-Id: 1
Content-Type: application/json

{
  "name": "Ceramics Watcher",
  "type": "watcher"
}
```

### 2. Role Requirement Decorator

**Function:** `@require_role(min_role: MemberRole)`

**Usage:**
```python
@router.get("/agents")
@require_role(MemberRole.VIEWER)  # Minimum required role
async def list_agents(team_context: TeamContext):
    # All roles can access (VIEWER and above)
    pass

@router.post("/agents/start")
@require_role(MemberRole.ANALYST)  # Higher requirement
async def start_agent(team_context: TeamContext):
    # Only ANALYST, ADMIN, OWNER can access
    pass
```

### 3. Global Middleware

**Class:** `TeamContextMiddleware`

**Purpose:**
- Extract X-Team-Id header globally
- Attach to request state
- Skip for public endpoints

**Public Endpoints (no team required):**
- `/health`
- `/api/v1/auth/*`
- `/api/v1/plans`
- `/docs`, `/openapi.json`

---

## ?? Access Control Flows

### 1. User Creates Team

```
1. User registers (POST /auth/register)
   ?
2. User creates team (POST /teams)
   {
     "name": "My Team",
     "plan_code": "FREE"
   }
   ?
3. Backend creates Team record
   - owner_id = current_user.id
   - plan_code = "FREE"
   ?
4. Backend creates Membership record
   - team_id = new_team.id
   - user_id = current_user.id
   - role = "OWNER"
   ?
5. Return team with member_count = 1
```

### 2. Owner Adds Member

```
1. Owner invites user (POST /teams/1/members)
   Authorization: Bearer {owner_token}
   X-Team-Id: 1
   {
     "user_id": 2,
     "role": "ANALYST"
   }
   ?
2. Backend validates:
   - Current user is member of team 1 ?
   - Current user role is ADMIN or OWNER ?
   - Target user (id=2) exists ?
   - Target user not already member ?
   ?
3. Backend creates Membership record
   - team_id = 1
   - user_id = 2
   - role = "ANALYST"
   - invited_by = current_user.id
   ?
4. Return membership details
   (In production: send invitation email)
```

### 3. Member Starts Agent

```
1. Member starts agent (POST /agents/start)
   Authorization: Bearer {member_token}
   X-Team-Id: 1
   {
     "name": "Watcher",
     "type": "watcher"
   }
   ?
2. Backend extracts team context
   - X-Team-Id: 1
   - User ID from JWT
   ?
3. Backend validates membership
   - User is member of team 1 ?
   - User role: ANALYST ?
   ?
4. Backend checks permissions
   - ANALYST can_manage_agents() ? True ?
   ?
5. Backend checks plan limits
   - Active agents: 2
   - Plan limit: 25
   - Can start: Yes ?
   ?
6. Backend creates agent
   - team_id = 1
   - created_by = user_id
   - Add to Redis active set
   ?
7. Return agent details
```

### 4. Non-Member Attempts Access

```
1. User tries to access team (GET /teams/1)
   Authorization: Bearer {other_user_token}
   X-Team-Id: 1
   ?
2. Backend extracts team context
   - X-Team-Id: 1
   - User ID: 99 (not a member)
   ?
3. Backend looks up membership
   - Query: team_id=1 AND user_id=99
   - Result: None ?
   ?
4. Backend raises HTTPException
   - Status: 403 Forbidden
   - Detail: "User 99 is not a member of team 1"
   ?
5. Return error to client
```

---

## ?? Security Measures

### 1. Header-Based Team Selection

**Why X-Team-Id?**
- Explicit team context per request
- Prevents accidental cross-team access
- Supports users with multiple team memberships

**Validation:**
```python
# Every protected endpoint
team_id = request.headers.get("X-Team-Id")
if not team_id:
    raise HTTPException(400, "X-Team-Id header required")

# Verify membership
membership = db.query(Membership).filter(
    Membership.team_id == team_id,
    Membership.user_id == current_user.id
).first()

if not membership:
    raise HTTPException(403, "User not member of team")
```

### 2. Role Immutability

**Owner Role:**
- Cannot be changed by any user (including owner)
- Only way to change owner: transfer ownership API (future)
- Owner cannot be removed from team

**Enforcement:**
```python
@router.patch("/teams/{team_id}/members/{user_id}")
async def update_member_role(role_update: MembershipUpdate):
    membership = get_membership(team_id, user_id)
    
    if membership.role == MemberRole.OWNER:
        raise HTTPException(400, "Cannot change owner role")
    
    membership.role = role_update.role
    db.commit()
```

### 3. Hierarchical Validation

**Role Hierarchy:**
```python
role_hierarchy = {
    MemberRole.VIEWER: 1,
    MemberRole.ANALYST: 2,
    MemberRole.ADMIN: 3,
    MemberRole.OWNER: 4
}

def can_assign_role(assigner_role: str, target_role: str) -> bool:
    """Admin can only assign roles below their own."""
    assigner_level = role_hierarchy[assigner_role]
    target_level = role_hierarchy[target_role]
    return assigner_level > target_level
```

**Example:**
- ADMIN (level 3) can assign ANALYST (2) or VIEWER (1)
- ADMIN cannot assign OWNER (4) or another ADMIN (3)

### 4. Audit Logging

**Track sensitive operations:**
```python
logger.info(
    "Member role changed",
    extra={
        "team_id": team_id,
        "target_user_id": user_id,
        "old_role": old_role,
        "new_role": new_role,
        "changed_by": current_user.id,
        "timestamp": datetime.utcnow()
    }
)
```

---

## ?? API Examples

### List User's Teams

```bash
GET /api/v1/teams
Authorization: Bearer {token}
```

**Response:**
```json
[
  {
    "id": 1,
    "name": "My Team",
    "owner_id": 1,
    "plan_code": "PRO",
    "created_at": "2025-11-01T00:00:00Z",
    "member_count": 5
  }
]
```

### Get Team Members

```bash
GET /api/v1/teams/1/members
Authorization: Bearer {token}
X-Team-Id: 1
```

**Response:**
```json
[
  {
    "id": 1,
    "team_id": 1,
    "user_id": 1,
    "user_email": "owner@example.com",
    "role": "OWNER",
    "joined_at": "2025-11-01T00:00:00Z"
  },
  {
    "id": 2,
    "team_id": 1,
    "user_id": 2,
    "user_email": "analyst@example.com",
    "role": "ANALYST",
    "joined_at": "2025-11-02T00:00:00Z"
  }
]
```

### Add Team Member

```bash
POST /api/v1/teams/1/members
Authorization: Bearer {token}
X-Team-Id: 1
Content-Type: application/json

{
  "user_id": 3,
  "role": "VIEWER"
}
```

**Response:**
```json
{
  "id": 3,
  "team_id": 1,
  "user_id": 3,
  "user_email": "viewer@example.com",
  "role": "VIEWER",
  "joined_at": "2025-11-02T12:00:00Z"
}
```

### Update Member Role

```bash
PATCH /api/v1/teams/1/members/3
Authorization: Bearer {token}
X-Team-Id: 1
Content-Type: application/json

{
  "role": "ANALYST"
}
```

### Remove Member

```bash
DELETE /api/v1/teams/1/members/3
Authorization: Bearer {token}
X-Team-Id: 1
```

**Response:** 204 No Content

---

## ?? Future Enhancements

**1. Invitation System**
- Email-based invitations
- Invitation tokens (expire after 7 days)
- Accept/decline invitation flow

**2. Custom Roles**
- User-defined roles (ENTERPRISE plan)
- Granular permission builder
- Role templates

**3. SSO Integration**
- SAML 2.0 support
- OAuth 2.0 / OIDC
- Auto-role assignment based on SAML attributes

**4. Multi-Team Management**
- Team hierarchies (parent/child teams)
- Cross-team agent sharing
- Consolidated billing

**5. Advanced Audit**
- Full audit trail (who changed what, when)
- Compliance exports (SOC2, GDPR)
- Real-time security alerts

**6. API Keys**
- Team-level API keys (ENTERPRISE)
- Scoped permissions per key
- Key rotation and expiration

---

## ??? Troubleshooting

### Error: "X-Team-Id header required"

**Cause:** Missing header in request

**Solution:**
```typescript
fetch('/api/v1/agents', {
  headers: {
    'Authorization': `Bearer ${token}`,
    'X-Team-Id': '1'  // Add this
  }
})
```

### Error: "User X is not a member of team Y"

**Cause:** User trying to access team they don't belong to

**Solution:**
1. Check user's team memberships: `GET /api/v1/teams`
2. Ensure correct X-Team-Id header
3. If needed, have admin add user to team

### Error: "Insufficient permissions to manage agents"

**Cause:** VIEWER trying to start agent

**Solution:**
1. Check user role: `GET /api/v1/teams/{id}/members`
2. Have ADMIN/OWNER change role to ANALYST or ADMIN

### Error: "Cannot change owner role"

**Cause:** Attempting to change OWNER role

**Solution:**
- Owner role is permanent for current owner
- To change ownership, use transfer ownership API (future feature)

---

**Document Version:** 1.0  
**Last Review:** November 2, 2025  
**Next Review:** December 1, 2025
