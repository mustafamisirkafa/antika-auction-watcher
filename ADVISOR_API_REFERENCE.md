# AI Advisor API Reference

**Version:** 1.0.0  
**Base URL:** `/api/v1/advisor`

---

## Endpoints

### 1. Get Suggestion

**GET** `/advisor/suggest/{item_id}`

Get AI recommendation for a specific auction item.

#### Parameters

| Name    | Type   | Location | Required | Description        |
|---------|--------|----------|----------|--------------------|
| item_id | string | path     | Yes      | Item identifier    |

#### Response

```json
{
  "item_id": "item123",
  "recommendation": "buy",
  "confidence": 0.85,
  "suggested_max_bid": 550.0,
  "reasoning": [
    "? Buy: Good opportunity, recommended to bid",
    "?? Pattern: Analyzed 4 similar ceramics items. Win rate: 75%, profitability rate: 66%.",
    "?? Market: Competition level: 2 bidders. Auction ending soon (30 min remaining).",
    "?? Behavior: Based on your activity: ceramics is familiar to you. Price within your typical range.",
    "? Risk: Risk assessment: Low risk. No major concerns identified."
  ],
  "risk_level": "low",
  "pattern_sense": {
    "score": 0.82,
    "confidence": 0.75,
    "reasoning": "Analyzed 4 similar ceramics items. Historical win rate: 75%, profitability rate: 66%.",
    "factors": {
      "win_rate": 0.75,
      "profitability_rate": 0.66,
      "price_advantage": 1.0,
      "undervalued": 1.0
    }
  },
  "market_sense": {
    "score": 0.72,
    "confidence": 0.8,
    "reasoning": "Competition level: 2 bidders. Auction ending soon (30 min remaining).",
    "factors": {
      "competition": 0.8,
      "bidder_count": 2,
      "urgency": 0.5
    }
  },
  "behavior_sense": {
    "score": 0.78,
    "confidence": 0.65,
    "reasoning": "Based on your activity: ceramics is familiar to you. Price within your typical range.",
    "factors": {
      "category_familiarity": 0.5,
      "price_comfort": 0.9,
      "explicit_preference": 1.0
    }
  },
  "risk_sense": {
    "score": 0.88,
    "confidence": 0.8,
    "reasoning": "Risk assessment: Low risk. No major concerns identified.",
    "factors": {
      "seller_trustworthiness": 0.9,
      "dispute_risk": 0.9,
      "condition_risk": 0.7
    }
  },
  "timestamp": "2025-11-02T18:45:00Z",
  "expires_at": "2025-11-02T19:15:00Z"
}
```

#### Status Codes

- `200 OK`: Recommendation generated successfully
- `500 Internal Server Error`: Failed to generate recommendation

---

### 2. Batch Analysis

**POST** `/advisor/analyze_batch`

Analyze multiple items in batch for efficiency.

#### Request Body

```json
{
  "item_ids": ["item1", "item2", "item3"],
  "user_id": "user123",
  "include_details": true
}
```

#### Parameters

| Name            | Type     | Required | Description                              |
|-----------------|----------|----------|------------------------------------------|
| item_ids        | string[] | Yes      | List of item IDs (1-50)                  |
| user_id         | string   | No       | User identifier for personalization      |
| include_details | boolean  | No       | Include full sense details (default: true) |

#### Response

```json
{
  "recommendations": [
    {
      "item_id": "item1",
      "recommendation": "buy",
      "confidence": 0.85,
      ...
    },
    {
      "item_id": "item2",
      "recommendation": "watch",
      "confidence": 0.62,
      ...
    }
  ],
  "total_analyzed": 2,
  "processing_time_ms": 87.5
}
```

#### Status Codes

- `200 OK`: Batch analysis completed
- `400 Bad Request`: Invalid request (e.g., too many items)
- `500 Internal Server Error`: Batch analysis failed

---

### 3. Submit Feedback

**POST** `/advisor/feedback`

Submit user feedback on a recommendation.

#### Request Body

```json
{
  "item_id": "item123",
  "recommendation_id": "rec456",
  "feedback_type": "helpful",
  "comment": "Great advice, won the auction!",
  "actual_outcome": {
    "won": true,
    "final_price": 550,
    "profitable": true
  }
}
```

#### Parameters

| Name              | Type   | Required | Description                                            |
|-------------------|--------|----------|--------------------------------------------------------|
| item_id           | string | Yes      | Item identifier                                        |
| recommendation_id | string | Yes      | Recommendation identifier                              |
| feedback_type     | string | Yes      | One of: helpful, not_helpful, accurate, inaccurate     |
| comment           | string | No       | Optional feedback comment                              |
| actual_outcome    | object | No       | What actually happened (for learning)                  |

#### Response

```json
{
  "status": "success",
  "message": "Feedback received and will be used to improve recommendations",
  "feedback_id": "fb_item123_1699024800",
  "timestamp": "2025-11-02T18:45:00Z"
}
```

#### Status Codes

- `200 OK`: Feedback received
- `500 Internal Server Error`: Failed to submit feedback

---

### 4. Get Statistics

**GET** `/advisor/stats`

Get advisor performance statistics.

#### Response

```json
{
  "total_recommendations": 1247,
  "accuracy_rate": 0.78,
  "avg_confidence": 0.73,
  "recommendations_by_level": {
    "strong_buy": 156,
    "buy": 423,
    "watch": 512,
    "skip": 124,
    "avoid": 32
  },
  "user_satisfaction": {
    "helpful": 892,
    "not_helpful": 143,
    "accurate": 756,
    "inaccurate": 98
  },
  "avg_processing_time_ms": 45,
  "last_updated": "2025-11-02T18:45:00Z"
}
```

#### Status Codes

- `200 OK`: Statistics retrieved

---

### 5. Get Explanation

**GET** `/advisor/explanation`

Get explanation of how the advisor works.

#### Response

```json
{
  "advisor_version": "1.0.0",
  "senses": [
    {
      "name": "PatternSense",
      "weight": 0.30,
      "description": "Analyzes historical patterns for similar items",
      "factors": [
        "Win rate for similar items",
        "Profitability rate",
        "Price trends",
        "Valuation alignment"
      ]
    },
    ...
  ],
  "recommendation_levels": {
    "strong_buy": "Excellent opportunity with high confidence",
    "buy": "Good opportunity, recommended to bid",
    "watch": "Interesting but wait for better timing",
    "skip": "Not recommended at current conditions",
    "avoid": "High risk, do not bid"
  },
  "risk_levels": {
    "low": "Minimal risk, safe to bid",
    "medium": "Some risk, proceed with caution",
    "high": "Significant risk, consider carefully",
    "very_high": "Extreme risk, avoid unless necessary"
  }
}
```

#### Status Codes

- `200 OK`: Explanation retrieved

---

### 6. Health Check

**GET** `/advisor/health`

Check advisor service health.

#### Response

```json
{
  "status": "healthy",
  "service": "advisor",
  "version": "1.0.0",
  "timestamp": "2025-11-02T18:45:00Z"
}
```

#### Status Codes

- `200 OK`: Service is healthy

---

## WebSocket Events

### advisor_update

Broadcast when a new recommendation is generated or updated.

#### Event Structure

```json
{
  "event": "advisor_update",
  "timestamp": "2025-11-02T18:45:00Z",
  "item_id": "item123",
  "recommendation": "buy",
  "confidence": 0.85,
  "suggested_max_bid": 550.0,
  "risk_level": "low",
  "reasoning": [
    "? Buy: Good opportunity, recommended to bid",
    "?? Pattern: Analyzed 4 similar ceramics items.",
    "?? Market: Competition level: 2 bidders."
  ]
}
```

#### Subscription

Connect to WebSocket channel: `/ws/auctions`

```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/ws/auctions')

ws.onmessage = (event) => {
  const data = JSON.parse(event.data)
  if (data.event === 'advisor_update') {
    console.log('New recommendation:', data)
  }
}
```

---

## Data Models

### RecommendationLevel

- `strong_buy` - Highly recommended
- `buy` - Recommended
- `watch` - Monitor but don't bid yet
- `skip` - Not recommended
- `avoid` - Do not bid

### RiskLevel

- `low` - Minimal risk
- `medium` - Acceptable risk
- `high` - Significant risk
- `very_high` - Extreme risk

### SenseScore

```typescript
{
  score: number        // 0.0 to 1.0
  confidence: number   // 0.0 to 1.0
  reasoning: string    // Human-readable explanation
  factors: object      // Individual factor scores
}
```

---

## Error Handling

### Error Response Format

```json
{
  "detail": "Error message describing what went wrong"
}
```

### Common Errors

| Code | Description                          |
|------|--------------------------------------|
| 400  | Invalid request parameters           |
| 404  | Item not found                       |
| 500  | Internal server error                |

---

## Rate Limiting

- **Endpoint**: `/advisor/suggest/{item_id}`
  - Limit: 60 requests per minute per IP
  - Burst: 10 requests per second

- **Endpoint**: `/advisor/analyze_batch`
  - Limit: 20 requests per minute per IP
  - Max items per request: 50

---

## Best Practices

1. **Cache Recommendations**: Recommendations expire after 30 minutes
2. **Batch When Possible**: Use batch endpoint for multiple items
3. **Submit Feedback**: Help improve accuracy by submitting feedback
4. **WebSocket for Real-time**: Subscribe to WebSocket for live updates
5. **Handle Errors Gracefully**: Always handle potential API failures

---

## Example Usage

### Python

```python
import httpx

async def get_recommendation(item_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"http://localhost:8000/api/v1/advisor/suggest/{item_id}"
        )
        return response.json()

recommendation = await get_recommendation("item123")
print(f"Recommendation: {recommendation['recommendation']}")
print(f"Max bid: ${recommendation['suggested_max_bid']}")
```

### JavaScript/TypeScript

```typescript
async function getRecommendation(itemId: string) {
  const response = await fetch(
    `http://localhost:8000/api/v1/advisor/suggest/${itemId}`
  )
  return await response.json()
}

const rec = await getRecommendation('item123')
console.log(`Recommendation: ${rec.recommendation}`)
console.log(`Confidence: ${(rec.confidence * 100).toFixed(0)}%`)
```

### cURL

```bash
# Get recommendation
curl -X GET "http://localhost:8000/api/v1/advisor/suggest/item123"

# Batch analysis
curl -X POST "http://localhost:8000/api/v1/advisor/analyze_batch" \
  -H "Content-Type: application/json" \
  -d '{
    "item_ids": ["item1", "item2"],
    "include_details": true
  }'

# Submit feedback
curl -X POST "http://localhost:8000/api/v1/advisor/feedback" \
  -H "Content-Type: application/json" \
  -d '{
    "item_id": "item123",
    "recommendation_id": "rec456",
    "feedback_type": "helpful"
  }'
```

---

**API Reference Complete** ?  
For logic details, see `AI_LOGIC_OVERVIEW.md`  
For implementation details, see `PHASE5_COMPLETE.md`
