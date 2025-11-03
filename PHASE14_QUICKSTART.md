# Phase 14: User Seller Preferences ? Quick Start

## ?? API Endpoints

### Base URL
```
http://localhost:8000/api/user/prefs
```

---

## 1?? Get User Preferences

**Endpoint:** `GET /api/user/prefs`  
**Auth:** JWT Required

```bash
curl -X GET "http://localhost:8000/api/user/prefs" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Response:**
```json
{
  "user_id": 1,
  "team_id": 1,
  "allowlist": [
    {
      "seller_id": "trusted-seller-001",
      "source": "ebay",
      "reason": null
    }
  ],
  "blocklist": [
    {
      "seller_id": "suspect-seller-042",
      "source": "etsy",
      "reason": null
    }
  ],
  "updated_at": "2025-11-03T12:00:00Z"
}
```

---

## 2?? Add Seller to Blocklist

**Endpoint:** `POST /api/user/prefs/update`  
**Auth:** JWT Required

```bash
curl -X POST "http://localhost:8000/api/user/prefs/update" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "add_block",
    "seller_id": "bad-seller-123",
    "source": "etsy",
    "reason": "Low trust score, poor reviews"
  }'
```

**Response:**
```json
{
  "success": true,
  "message": "Seller added to blocklist",
  "affected_list": "blocklist",
  "seller_id": "bad-seller-123",
  "new_total": 2,
  "updated_at": "2025-11-03T12:05:00Z"
}
```

---

## 3?? Add Seller to Allowlist

```bash
curl -X POST "http://localhost:8000/api/user/prefs/update" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "add_allow",
    "seller_id": "trusted-seller-456",
    "source": "ebay",
    "reason": "Excellent track record"
  }'
```

---

## 4?? Remove Seller from Blocklist

```bash
curl -X POST "http://localhost:8000/api/user/prefs/update" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "remove_block",
    "seller_id": "bad-seller-123",
    "source": "etsy"
  }'
```

---

## 5?? Check if Seller is Allowed

**Endpoint:** `GET /api/user/prefs/check/{seller_id}`  
**Auth:** JWT Required

```bash
curl -X GET "http://localhost:8000/api/user/prefs/check/bad-seller-123?source=etsy" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Response (Blocked):**
```json
{
  "allowed": false,
  "reason": "Seller is blocklisted"
}
```

**Response (Allowed):**
```json
{
  "allowed": true,
  "reason": "No restrictions"
}
```

---

## ?? Actions Reference

| Action | Description | Effect |
|--------|-------------|--------|
| `add_allow` | Add to allowlist | Removes from blocklist if present |
| `remove_allow` | Remove from allowlist | No effect on blocklist |
| `add_block` | Add to blocklist | Removes from allowlist if present |
| `remove_block` | Remove from blocklist | No effect on allowlist |

---

## ?? Preference Logic

### Blocklist Priority
- **Always blocks** ? highest priority
- Overrides allowlist if present in both

### Allowlist Behavior
1. **Empty allowlist** (default)
   - All sellers allowed (except blocklisted)
   - "Open" mode

2. **Populated allowlist**
   - Only allowlisted sellers allowed
   - "Restricted" mode
   - All non-allowlisted sellers blocked

---

## ?? Decision Flow

```
Check seller ? In blocklist? ? YES ? DENIED
               ? NO
               Allowlist empty? ? YES ? ALLOWED
               ? NO
               In allowlist? ? YES ? ALLOWED
               ? NO
               DENIED
```

---

## ?? Testing Scenarios

### Scenario 1: Block a Specific Seller
```bash
# Add to blocklist
POST /api/user/prefs/update
{
  "action": "add_block",
  "seller_id": "suspect-seller",
  "source": "ebay"
}

# Verify blocked
GET /api/user/prefs/check/suspect-seller?source=ebay
? {"allowed": false, "reason": "Seller is blocklisted"}
```

### Scenario 2: Restrict to Trusted Sellers Only
```bash
# Add first trusted seller
POST /api/user/prefs/update
{
  "action": "add_allow",
  "seller_id": "trusted-seller-1",
  "source": "ebay"
}

# Add second trusted seller
POST /api/user/prefs/update
{
  "action": "add_allow",
  "seller_id": "trusted-seller-2",
  "source": "etsy"
}

# Check unknown seller (will be blocked)
GET /api/user/prefs/check/unknown-seller?source=ebay
? {"allowed": false, "reason": "Seller not in allowlist"}

# Check trusted seller (will be allowed)
GET /api/user/prefs/check/trusted-seller-1?source=ebay
? {"allowed": true, "reason": "Seller is allowlisted"}
```

### Scenario 3: Switch from Block to Allow
```bash
# Initially blocked
POST /api/user/prefs/update
{
  "action": "add_block",
  "seller_id": "seller-x",
  "source": "ebay"
}

# Change mind, add to allowlist (auto-removes from blocklist)
POST /api/user/prefs/update
{
  "action": "add_allow",
  "seller_id": "seller-x",
  "source": "ebay"
}

# Verify now allowed
GET /api/user/prefs/check/seller-x?source=ebay
? {"allowed": true, "reason": "Seller is allowlisted"}
```

---

## ?? Integration with AutoBid (Pending)

### Future Integration Point
```python
# In AutoBid Engine (bid_policy.py)
async def evaluate_bid_decision(...):
    # Check user preferences
    seller_check = await user_prefs_service.check_seller_allowed(
        user_id=user_id,
        team_id=team_id,
        seller_id=auction.seller_id,
        source=auction.source
    )
    
    if not seller_check["allowed"]:
        return {
            "ok": False,
            "status": "blocked",
            "reason": f"Seller blocked: {seller_check['reason']}",
            "blocked_by": "user_preference"
        }
    
    # Continue with normal bid evaluation...
```

---

## ?? Documentation

- **Detailed Docs:** `PHASE14_IMPLEMENTATION_SUMMARY.md`
- **API Reference:** `PHASE14_API_COMPLETE.md`
- **OpenAPI/Swagger:** `http://localhost:8000/docs`

---

## ?? Tips

1. **Start Open, Block Gradually**
   - Leave allowlist empty initially
   - Add sellers to blocklist as issues arise
   - Keeps flexibility while protecting from bad actors

2. **Use Allowlist for High-Value Auctions**
   - When bidding on expensive items
   - Restrict to sellers you've vetted
   - Reduces risk of fraud

3. **Check Before Manual Bids**
   - Use `/check/{seller_id}` endpoint
   - Verify seller status before placing manual bids
   - Consistent with AutoBid behavior

---

_Phase 14 Quick Start Guide ? API Ready!_
