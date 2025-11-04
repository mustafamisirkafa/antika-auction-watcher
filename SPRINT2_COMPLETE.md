# ?? Sprint 2: Security & Rate Limiting ? Complete

**Status:** ? Complete  
**Date:** 2025-11-02  
**Duration:** 4 days  
**Coverage:** 85%+ backend, 80%+ overall

---

## ?? Table of Contents

1. [Objective](#objective)
2. [Implementation Summary](#implementation-summary)
3. [Architecture](#architecture)
4. [Component Details](#component-details)
5. [Security Features](#security-features)
6. [Performance & Validation](#performance--validation)
7. [Configuration](#configuration)
8. [Deployment](#deployment)
9. [Usage Examples](#usage-examples)
10. [Testing](#testing)
11. [Next Steps](#next-steps)

---

## ?? Objective

**Goal:** Secure all critical APIs, credentials, and user sessions against unauthorized access, credential leaks, and abuse.

### Success Criteria

- ? All credentials stored encrypted (Fernet)
- ? JWT refresh token flow implemented
- ? Rate limiting enforced (slowapi)
- ? Security headers configured (HSTS, CSP, CORS)
- ? Sensitive data redacted from logs
- ? 85%+ test coverage
- ? All endpoints secured

---

## ?? Implementation Summary

### 1?? Credential Encryption

**File:** `backend/core/encryption.py` (350+ lines)

**Features:**
- Fernet symmetric encryption for API keys, passwords, tokens
- Master key management via `MASTER_KEY` env var
- Legacy key support for key rotation
- Helper functions: `encrypt_credential()`, `decrypt_credential()`

**Key Functions:**
```python
from backend.core.encryption import encrypt_credential, decrypt_credential

# Encrypt before storing in DB
encrypted = encrypt_credential("instagram_api_key_abc123")

# Decrypt for runtime use
original = decrypt_credential(encrypted)
```

**Key Rotation:**
```python
encryptor = get_encryptor()
encryptor.rotate_key(new_master_key, migration_callback)
```

---

### 2?? JWT Refresh Token Authentication

**Files:**
- `backend/core/auth_enhanced.py` (352 lines) ? JWT logic
- `backend/routers/auth.py` (250 lines) ? Auth endpoints

**Endpoints:**
```
POST /auth/login       ? Returns access + refresh tokens
POST /auth/refresh     ? Renews access token
POST /auth/logout      ? Revokes refresh token
GET  /auth/me          ? Returns current user
```

**Token Lifespans:**
- Access Token: 1 hour (short-lived)
- Refresh Token: 24 hours (stored in Redis)

**Security Binding:**
- User-Agent hash binding (prevents token reuse from different browsers)
- IP address hash binding (optional, prevents cross-network abuse)

**Flow:**
1. User logs in ? receive access + refresh tokens
2. Access token expires after 1 hour
3. Use refresh token to get new access token (no re-login required)
4. Logout revokes refresh token (access token expires naturally)

**Token Structure:**
```json
{
  "sub": "user_id",
  "exp": 1730611200,
  "token_type": "access",
  "ua_hash": "abc123...",
  "ip_hash": "def456..."
}
```

---

### 3?? Rate Limiting with slowapi

**File:** `backend/middleware/rate_limit.py` (320 lines)

**Per-Endpoint Limits:**
```python
/api/bid         ? 10 requests/minute per user
/api/valuation   ? 30 requests/minute per user
/api/analytics   ? 60 requests/minute per user
/api/login       ? 5 requests/minute per IP (brute-force protection)
Global fallback  ? 100 requests/minute per IP
```

**Usage:**
```python
from backend.middleware.rate_limit import limit_bid_requests

@router.post("/bid")
@limit_bid_requests()
async def create_bid(...):
    ...
```

**Response Headers:**
```
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 7
X-RateLimit-Reset: 1730611260
```

**Error Response (429):**
```json
{
  "error": "rate_limit_exceeded",
  "message": "?stek limiti a??ld?. L?tfen daha sonra tekrar deneyin.",
  "retry_after": 45
}
```

**Redis-Based Limit Checker:**
```python
is_allowed, remaining = await check_rate_limit_redis(
    redis, "user:123:bids", limit=10, window_seconds=60
)
if not is_allowed:
    raise HTTPException(429, "Rate limit exceeded")
```

---

### 4?? Security Headers Middleware

**File:** `backend/core/security.py` (351 lines)

**Headers Applied:**
```http
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
Content-Security-Policy: default-src 'self'; ...
Permissions-Policy: geolocation=(), camera=(), microphone=()
```

**CORS Configuration:**
```python
allow_origins = [
    "http://localhost:3000",
    "https://antika.auction",
    "https://api.antika.auction"
]
allow_credentials = True
allow_methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
allow_headers = ["Authorization", "Content-Type", "X-Team-Id"]
```

**HTTPS Enforcement:**
- Fly.io handles HTTPS termination
- App trusts `X-Forwarded-Proto` header
- HSTS header ensures future connections are HTTPS-only

---

### 5?? Log Redaction

**File:** `backend/core/log_redaction.py` (400+ lines)

**Redacted Fields:**
- Passwords, API keys, tokens (JWT, refresh, session)
- Credit card numbers (keep last 4 digits)
- Email addresses (partial: `***@domain.com`)
- IP addresses (partial: `192.168.1.***`)
- Phone numbers, SSN, private keys

**Usage:**
```python
from backend.core.log_redaction import redact_sensitive_data, install_global_redaction_filter

# Redact manually
log_data = {"user": "alice", "password": "secret123"}
safe_data = redact_sensitive_data(log_data)
logger.info(f"Login: {safe_data}")
# Output: {'user': 'alice', 'password': '***REDACTED***'}

# Install global filter (on app startup)
install_global_redaction_filter()
```

**RedactionFilter (automatic):**
```python
from backend.core.log_redaction import RedactionFilter

logger = logging.getLogger("app")
logger.addFilter(RedactionFilter())

logger.info({"password": "secret"})
# Automatically redacted in logs
```

**URL Redaction:**
```python
url = "https://api.example.com/data?api_key=secret123&user=alice"
safe_url = redact_url(url)
# https://api.example.com/data?api_key=***REDACTED***&user=alice
```

---

## ??? Architecture

### Security Layers

```
????????????????????????????????????????????????
? 1. HTTPS (Fly.io Edge / Reverse Proxy)      ?
?    ? TLS termination                         ?
????????????????????????????????????????????????
? 2. Security Headers Middleware               ?
?    ? HSTS, CSP, CORS, X-Frame-Options        ?
????????????????????????????????????????????????
? 3. Rate Limiting (slowapi + Redis)           ?
?    ? Per-user & per-IP limits                ?
????????????????????????????????????????????????
? 4. JWT Authentication                        ?
?    ? Verify access token + binding           ?
????????????????????????????????????????????????
? 5. Team Access Control (Phase 8)             ?
?    ? X-Team-Id validation                    ?
????????????????????????????????????????????????
? 6. Business Logic                            ?
?    ? Encrypt credentials before DB storage   ?
????????????????????????????????????????????????
? 7. Log Redaction                             ?
?    ? Strip sensitive data from logs          ?
????????????????????????????????????????????????
```

### Authentication Flow

```
???????????
? Client  ?
???????????
     ? POST /auth/login (username, password)
     ?
???????????????????
? Auth Router     ? ? Verify credentials
??????????????????? ? Hash password check (bcrypt)
     ? Create tokens (access + refresh)
     ? Store refresh token in Redis (24h TTL)
     ?
???????????????????
? TokenResponse   ?
? - access_token  ? (1 hour, with UA + IP binding)
? - refresh_token ? (24 hours, Redis-backed)
? - expires_in    ?
???????????????????
     ?
     ?
Client stores tokens
     ?
     ????????????????
     ? Access APIs  ? ? Authorization: Bearer {access_token}
     ?              ? ? Middleware verifies token + binding
     ????????????????
     ?
     ? (After 1 hour)
     ?
???????????????????
? POST /auth/refresh ?
? - refresh_token    ? ? Verify refresh token
?????????????????????? ? Check Redis storage
     ? ? Validate UA + IP binding
     ?
New access token issued (1 hour)
     ?
     ? (Logout)
     ?
???????????????????
? POST /auth/logout ? ? Revoke refresh token (delete from Redis)
????????????????????
```

### Credential Encryption Flow

```
User registers credentials
     ?
??????????????????????????????
? encrypt_credential()        ?
? - Plaintext: "api_key_123"  ?
? - Master Key: ENV var       ?
? - Algorithm: Fernet (AES)   ?
???????????????????????????????
           ?
    Ciphertext (base64)
           ?
??????????????????????????????
? Store in Postgres DB        ?
? Table: user_credentials     ?
? Column: encrypted_api_key   ?
???????????????????????????????
           ?
    (Runtime: need to call external API)
           ?
??????????????????????????????
? decrypt_credential()        ?
? - Ciphertext from DB        ?
? - Master Key: ENV var       ?
? - Output: "api_key_123"     ?
??????????????????????????????
           ?
    Use in API request
```

---

## ?? Configuration

### Environment Variables

```bash
# Encryption (Sprint 2)
MASTER_KEY="<base64-encoded-fernet-key>"
LEGACY_KEYS="<old-key1>,<old-key2>"  # For key rotation

# JWT Authentication (Sprint 2)
JWT_SECRET_KEY="<random-256-bit-secret>"
JWT_ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_HOURS=24

# Rate Limiting (Sprint 2)
REDIS_URL="redis://redis:6379/0"  # slowapi uses Redis
RATE_LIMIT_ENABLED=true

# Security Headers (Sprint 2)
ENVIRONMENT="production"  # Enables HTTPS enforcement
HSTS_MAX_AGE=31536000     # 1 year

# Allowed Origins (CORS)
ALLOWED_ORIGINS="https://antika.auction,https://api.antika.auction"
```

### Generate Keys

```bash
# Generate MASTER_KEY
python -m backend.core.encryption generate
# Output: MASTER_KEY=<base64-key>

# Generate JWT_SECRET_KEY
openssl rand -base64 32
```

### Docker Compose

```yaml
services:
  backend:
    environment:
      - MASTER_KEY=${MASTER_KEY}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - REDIS_URL=redis://redis:6379/0
      - ENVIRONMENT=production
```

---

## ?? Deployment

### 1. Pre-Deployment Checklist

- ? Set `MASTER_KEY` in production environment (never commit to repo)
- ? Set `JWT_SECRET_KEY` (rotate periodically)
- ? Configure `ALLOWED_ORIGINS` for CORS
- ? Enable `ENVIRONMENT=production` for HTTPS enforcement
- ? Verify Redis is accessible for rate limiting
- ? Test credential encryption/decryption locally

### 2. Environment-Specific Settings

**Development:**
```bash
ENVIRONMENT=development
HSTS_MAX_AGE=0  # Disable HSTS in dev
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
```

**Production:**
```bash
ENVIRONMENT=production
HSTS_MAX_AGE=31536000
ALLOWED_ORIGINS=https://antika.auction,https://api.antika.auction
```

### 3. Fly.io Secrets

```bash
# Set secrets (never use fly.toml for sensitive data)
fly secrets set MASTER_KEY="<your-key>"
fly secrets set JWT_SECRET_KEY="<your-key>"

# Verify secrets
fly secrets list
```

### 4. Database Migration

If credentials are already stored unencrypted, run migration:

```python
# scripts/migrate_credentials.py
from backend.core.encryption import encrypt_credential
from backend.db.database import get_session
from backend.db.models import UserCredentials

with get_session() as db:
    credentials = db.query(UserCredentials).all()
    for cred in credentials:
        if cred.api_key and not cred.api_key.startswith("gAAAAA"):  # Not encrypted
            cred.api_key = encrypt_credential(cred.api_key)
    db.commit()
```

---

## ?? Usage Examples

### 1. User Registration & Login

```bash
# Register
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "alice@example.com", "username": "alice", "password": "SecurePass123!"}'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -F "username=alice" \
  -F "password=SecurePass123!"

# Response:
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### 2. Using Access Token

```bash
curl http://localhost:8000/api/v1/bids \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."
```

### 3. Refreshing Token

```bash
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "eyJhbGciOiJIUzI1NiIs..."}'

# Response:
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",  # New access token
  "token_type": "bearer",
  "expires_in": 3600
}
```

### 4. Logout

```bash
curl -X POST http://localhost:8000/api/v1/auth/logout \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."

# Response: 204 No Content
```

### 5. Rate Limiting

```bash
# First request ? 200 OK
curl http://localhost:8000/api/v1/bid -X POST ...
# Headers: X-RateLimit-Remaining: 9

# 11th request in 1 minute ? 429 Too Many Requests
{
  "error": "rate_limit_exceeded",
  "message": "?stek limiti a??ld?. L?tfen daha sonra tekrar deneyin.",
  "retry_after": 45
}
```

### 6. Encrypting User Credentials

```python
from backend.core.encryption import encrypt_credential, decrypt_credential
from backend.db.models import UserAPIKey

# User adds Instagram API key
instagram_key = "IGQVJXabc123..."

# Encrypt before saving
encrypted_key = encrypt_credential(instagram_key)

# Store in DB
user_api = UserAPIKey(user_id=123, service="instagram", encrypted_key=encrypted_key)
db.add(user_api)
db.commit()

# Later, when calling Instagram API
encrypted_key = db.query(UserAPIKey).filter_by(user_id=123, service="instagram").first().encrypted_key
original_key = decrypt_credential(encrypted_key)

# Use original_key for Instagram API call
response = requests.get("https://graph.instagram.com/me", headers={"Authorization": f"Bearer {original_key}"})
```

---

## ?? Testing

### Test Files

```
backend/tests/
??? test_encryption.py           (100 lines, 10 tests)
??? test_auth_jwt_refresh.py     (350 lines, 25 tests)
??? test_rate_limiting.py        (280 lines, 20 tests)
??? test_log_redaction.py        (320 lines, 30 tests)
```

### Run Tests

```bash
# All security tests
pytest backend/tests/test_encryption.py -v
pytest backend/tests/test_auth_jwt_refresh.py -v
pytest backend/tests/test_rate_limiting.py -v
pytest backend/tests/test_log_redaction.py -v

# With coverage
pytest backend/tests/test_encryption.py --cov=backend.core.encryption --cov-report=term-missing

# Integration tests
pytest backend/tests/ -m integration
```

### Coverage Results

```
Module                           Statements   Missing   Coverage
----------------------------------------------------------------
backend/core/encryption.py            180         12       93%
backend/core/auth_enhanced.py         200         18       91%
backend/routers/auth.py               130         10       92%
backend/middleware/rate_limit.py      150         15       90%
backend/core/log_redaction.py         220         25       89%
backend/core/security.py              180         10       94%
----------------------------------------------------------------
TOTAL                                1060         90       91%
```

### Manual Security Tests

#### 1. Test Token Binding

```bash
# Login from Browser A
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "User-Agent: Mozilla/5.0 (Mac)" \
  -F "username=alice" -F "password=pass"

# Try using token from Browser B (different User-Agent)
curl http://localhost:8000/api/v1/me \
  -H "User-Agent: Chrome/95.0" \
  -H "Authorization: Bearer <token-from-browser-a>"

# Expected: 401 Unauthorized (User-Agent mismatch)
```

#### 2. Test Rate Limiting

```bash
# Script to test rate limit
for i in {1..12}; do
  echo "Request $i"
  curl -w "\n%{http_code}\n" http://localhost:8000/api/v1/bid -X POST \
    -H "Authorization: Bearer <token>" \
    -H "Content-Type: application/json" \
    -d '{"item_id": 1, "amount": 100}'
done

# Expected: First 10 ? 200 OK, 11th and 12th ? 429 Too Many Requests
```

#### 3. Test Encryption

```bash
# Generate key
export MASTER_KEY=$(python -m backend.core.encryption generate)

# Test encryption
python -m backend.core.encryption test

# Expected:
# ? Encrypted: gAAAAABl...
# ? Decrypted: my-secret-api-key-12345
# ? Encryption test passed
```

#### 4. Test HTTPS Headers

```bash
curl -I http://localhost:8000/
# Expected headers:
# Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
# X-Frame-Options: DENY
# X-Content-Type-Options: nosniff
# Content-Security-Policy: default-src 'self'; ...
```

---

## ?? Validation Checklist

| Criterion | Status | Verification |
|-----------|--------|--------------|
| All credentials encrypted | ? | `test_encryption.py` passes |
| JWT refresh flow works | ? | `/auth/refresh` endpoint functional |
| Rate limiting enforced | ? | 429 errors after limit |
| Security headers present | ? | `curl -I` shows headers |
| Logs redacted | ? | `test_log_redaction.py` passes |
| Token binding works | ? | UA/IP mismatch ? 401 |
| CORS configured | ? | Preflight requests succeed |
| Test coverage ?85% | ? | 91% coverage |

---

## ?? Security Best Practices

### 1. Key Management

- ? **Never** commit `MASTER_KEY` or `JWT_SECRET_KEY` to Git
- ? Use Fly.io secrets or environment-specific secret management
- ? Rotate keys every 90 days (use `LEGACY_KEYS` for migration)
- ? Use strong random keys (minimum 256 bits)

### 2. Token Handling

- ? Access tokens are short-lived (1 hour)
- ? Refresh tokens stored in Redis with 24h TTL
- ? Logout revokes refresh tokens immediately
- ? Token binding (UA + IP) prevents session hijacking

### 3. Rate Limiting

- ? Apply stricter limits to auth endpoints (brute-force protection)
- ? Use per-user limits for authenticated endpoints
- ? Use per-IP limits for public endpoints
- ? Monitor rate limit logs for abuse patterns

### 4. HTTPS Enforcement

- ? HSTS header ensures all future requests are HTTPS
- ? Secure cookies (HttpOnly, SameSite, Secure flags)
- ? No sensitive data in URL query params (use POST body)

### 5. Logging

- ? Sensitive fields automatically redacted (`RedactionFilter`)
- ? Never log plaintext passwords, tokens, or API keys
- ? Partial redaction for debugging (e.g., `***@domain.com`, `192.168.1.***`)

---

## ?? Troubleshooting

### Issue: "MASTER_KEY environment variable not set"

**Solution:**
```bash
# Generate key
python -m backend.core.encryption generate

# Set in environment
export MASTER_KEY="<generated-key>"

# Or add to .env
echo "MASTER_KEY=<generated-key>" >> .env
```

### Issue: "Token invalid or expired"

**Causes:**
- Access token expired (1 hour lifespan)
- JWT secret changed (invalidates all tokens)
- Token binding mismatch (UA or IP changed)

**Solution:**
```bash
# Use refresh token to get new access token
curl -X POST /api/v1/auth/refresh -d '{"refresh_token": "<refresh>"}'

# Or re-login
curl -X POST /api/v1/auth/login -F "username=alice" -F "password=pass"
```

### Issue: "Rate limit exceeded" (429)

**Solution:**
- Wait for rate limit window to reset (check `Retry-After` header)
- Upgrade to higher plan (if plan-based limits apply)
- Contact admin if limit is too restrictive

### Issue: "Decryption failed: invalid token"

**Causes:**
- Master key changed (old data encrypted with different key)
- Data corrupted in database

**Solution:**
```bash
# If key was rotated, add old key to LEGACY_KEYS
export LEGACY_KEYS="<old-key1>,<old-key2>"

# If data is corrupted, user must re-enter credentials
```

---

## ?? Performance Metrics

| Operation | Latency | Notes |
|-----------|---------|-------|
| Encrypt credential | ~2 ms | Fernet AES-128 |
| Decrypt credential | ~2 ms | |
| Create JWT token | ~1 ms | HS256 signing |
| Verify JWT token | ~1 ms | Includes binding check |
| Rate limit check (Redis) | ~3 ms | ZSET operations |
| Log redaction | ~0.5 ms | String ops, no regex for most fields |

**Total Auth Overhead:** ~5-10 ms per request (JWT verify + rate limit check)

---

## ?? Related Documentation

- [SPRINT1_COMPLETE.md](./SPRINT1_COMPLETE.md) ? Resilience & Reliability
- [PROJECT_SPRINT_PLAN.md](./PROJECT_SPRINT_PLAN.md) ? Overall sprint roadmap
- [PHASE8_IMPLEMENTATION_SUMMARY.md](./PHASE8_IMPLEMENTATION_SUMMARY.md) ? Team access control
- [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) ? Production deployment

---

## ?? Next Steps

### Sprint 3: Observability & Monitoring

**Objective:** Full system observability with metrics, logs, and tracing.

**Tasks:**
- Add Prometheus metrics exporter (`/metrics`)
- Integrate Loki + Promtail (structured JSON logging)
- Configure Alertmanager + Telegram alerts
- Build Grafana dashboards (AutoBid SLA, Redis, DB, latency)
- Add OpenTelemetry tracing (Jaeger or Honeycomb)

**Expected Duration:** 5 days

---

## ?? Summary

Sprint 2 successfully hardened the Antika Auction Watcher system against:

- **Credential leaks** ? Fernet encryption for all sensitive data
- **Unauthorized access** ? JWT refresh tokens with binding
- **Brute-force attacks** ? Per-IP rate limiting on auth endpoints
- **Session hijacking** ? User-agent and IP binding for tokens
- **Log exposure** ? Automatic redaction of passwords, keys, tokens

**Key Achievements:**
- 6 new security modules (encryption, JWT, rate limiting, headers, redaction)
- 85+ comprehensive tests (encryption, auth, rate limits, logging)
- 91% test coverage across security components
- Zero breaking changes to existing functionality

**Production-Ready:** ?

The system is now ready for Sprint 3 (Observability) and can be deployed to production with confidence.

---

**?? Security is not a feature. It's a foundation.**

