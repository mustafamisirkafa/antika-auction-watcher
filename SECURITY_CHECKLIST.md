# Security Checklist - Antika Auction Watcher

**Version:** 1.0.0  
**Last Review:** November 2, 2025

---

## ?? Pre-Deployment Security

### Infrastructure Security

- [ ] **Server Hardening**
  - [ ] Latest OS security patches applied
  - [ ] Unnecessary services disabled
  - [ ] Firewall configured (UFW/iptables)
  - [ ] Fail2ban installed and configured
  - [ ] SSH key-based authentication only
  - [ ] Root login disabled

- [ ] **Network Security**
  - [ ] Private Docker network configured
  - [ ] Only necessary ports exposed (80, 443, 3001)
  - [ ] Internal services not exposed to internet
  - [ ] VPN for admin access (recommended)

- [ ] **Docker Security**
  - [ ] Containers run as non-root user
  - [ ] Resource limits set (CPU, memory)
  - [ ] Docker socket not mounted in containers
  - [ ] Secrets not in Dockerfiles or docker-compose
  - [ ] Official base images used

### Application Security

- [ ] **Authentication & Authorization**
  - [ ] JWT tokens with short expiry (15 min)
  - [ ] Refresh tokens with rotation
  - [ ] Password requirements enforced (min 12 chars, complexity)
  - [ ] Bcrypt for password hashing (cost factor ?12)
  - [ ] RBAC implemented for admin endpoints
  - [ ] Session management with Redis

- [ ] **API Security**
  - [ ] Rate limiting enabled (10 req/s API, 5 req/m auth)
  - [ ] Input validation on all endpoints (Pydantic)
  - [ ] SQL injection prevention (SQLModel/SQLAlchemy)
  - [ ] XSS prevention (CSP headers)
  - [ ] CSRF protection for state-changing operations
  - [ ] Request size limits (20MB max)

- [ ] **Data Protection**
  - [ ] Sensitive data encrypted at rest (Fernet)
  - [ ] TLS 1.2+ for all connections
  - [ ] Database credentials encrypted
  - [ ] Instagram credentials stored with encryption
  - [ ] PII data minimization
  - [ ] Data retention policies implemented

### SSL/TLS Configuration

- [ ] **Certificates**
  - [ ] Valid SSL certificate (Let's Encrypt or commercial)
  - [ ] Certificate auto-renewal configured
  - [ ] Certificate expiry monitoring (7-day alert)
  - [ ] Strong cipher suites only (TLSv1.2+)
  - [ ] HSTS header enabled (max-age=31536000)

- [ ] **Nginx Security Headers**
  - [ ] Strict-Transport-Security
  - [ ] X-Frame-Options: SAMEORIGIN
  - [ ] X-Content-Type-Options: nosniff
  - [ ] X-XSS-Protection: 1; mode=block
  - [ ] Content-Security-Policy configured
  - [ ] Referrer-Policy set

### Secrets Management

- [ ] **Environment Variables**
  - [ ] All secrets in `.env` file (not committed)
  - [ ] Strong passwords (32+ characters)
  - [ ] Unique passwords per service
  - [ ] Secrets rotated regularly (quarterly)

- [ ] **Secret Rotation Schedule**
  - [ ] POSTGRES_PASSWORD - Quarterly
  - [ ] REDIS_PASSWORD - Quarterly
  - [ ] SECRET_KEY - Annually
  - [ ] SMTP_PASSWORD - As needed
  - [ ] GRAFANA_PASSWORD - Quarterly

---

## ??? Runtime Security

### Monitoring

- [ ] **Security Monitoring**
  - [ ] Failed login attempts tracked
  - [ ] Rate limit violations logged
  - [ ] Unusual access patterns detected
  - [ ] Admin action audit log enabled
  - [ ] File integrity monitoring (AIDE/Tripwire)

- [ ] **Vulnerability Scanning**
  - [ ] Docker images scanned (Trivy/Snyk)
  - [ ] Dependencies scanned for CVEs
  - [ ] Regular security audits scheduled
  - [ ] OWASP Top 10 mitigations verified

### Access Control

- [ ] **SSH Access**
  - [ ] Key-based authentication only
  - [ ] Whitelist of allowed IPs (if possible)
  - [ ] MFA enabled (Google Authenticator)
  - [ ] Session timeout configured

- [ ] **Database Access**
  - [ ] No direct external access
  - [ ] Application user has minimal privileges
  - [ ] Admin user separate from app user
  - [ ] Connection pooling configured

- [ ] **Redis Access**
  - [ ] Password protected
  - [ ] No external access
  - [ ] Dangerous commands disabled (FLUSHALL, CONFIG)

### Backup Security

- [ ] **Backup Protection**
  - [ ] Backups encrypted at rest
  - [ ] Backup access restricted
  - [ ] Backup integrity verified
  - [ ] Offsite backup storage
  - [ ] Restore tested monthly

---

## ?? Security Audit Tasks

### Monthly Tasks

- [ ] Review access logs for anomalies
- [ ] Check for failed authentication attempts
- [ ] Verify SSL certificate expiry (should be >30 days)
- [ ] Review rate limiting effectiveness
- [ ] Check for outdated dependencies

### Quarterly Tasks

- [ ] Rotate database passwords
- [ ] Rotate Redis passwords
- [ ] Review and update firewall rules
- [ ] Penetration testing (internal)
- [ ] Security training for team

### Annual Tasks

- [ ] External security audit
- [ ] Disaster recovery drill
- [ ] Review and update security policies
- [ ] Compliance review (GDPR, etc.)
- [ ] Rotate application SECRET_KEY

---

## ?? Incident Response

### Security Incident Checklist

1. **Detect & Contain**
   - [ ] Identify affected systems
   - [ ] Isolate compromised services
   - [ ] Enable detailed logging
   - [ ] Block malicious IPs

2. **Investigate**
   - [ ] Review logs (Loki)
   - [ ] Check access patterns
   - [ ] Identify attack vector
   - [ ] Assess data exposure

3. **Remediate**
   - [ ] Patch vulnerabilities
   - [ ] Rotate compromised credentials
   - [ ] Update firewall rules
   - [ ] Deploy fixes

4. **Document**
   - [ ] Create incident report
   - [ ] Timeline of events
   - [ ] Root cause analysis
   - [ ] Lessons learned

5. **Prevent**
   - [ ] Update security policies
   - [ ] Add monitoring/alerts
   - [ ] Team training
   - [ ] Security hardening

---

## ?? Compliance

### GDPR Compliance

- [ ] Data processing documented
- [ ] User consent collected
- [ ] Right to deletion implemented
- [ ] Data portability (CSV exports)
- [ ] Privacy policy published
- [ ] Data breach notification procedure

### Data Handling

- [ ] **Personal Data Inventory**
  - User email, password hash
  - Bidding history
  - Feedback data
  - Instagram credentials (encrypted)

- [ ] **Data Protection**
  - Encryption at rest and in transit
  - Access controls enforced
  - Audit logging enabled
  - Regular backups

---

## ? Security Verification Commands

### SSL/TLS Test

```bash
# Check SSL configuration
openssl s_client -connect your-domain.com:443 -tls1_2

# Test with SSLLabs
curl -s "https://api.ssllabs.com/api/v3/analyze?host=your-domain.com"
```

### Security Headers Test

```bash
curl -I https://your-domain.com | grep -E "Strict-Transport|X-Frame|X-Content|Content-Security"
```

### Password Strength Test

```bash
# Check bcrypt cost factor
docker compose -f infra/docker-compose.prod.yml exec backend python -c "
from backend.core.security import hash_password
import time
start = time.time()
hash_password('test123456')
print(f'Hashing time: {time.time() - start:.3f}s')
"
# Should be >0.2s (cost factor 12+)
```

### Rate Limiting Test

```bash
# Hammer API endpoint
for i in {1..20}; do
  curl -s -o /dev/null -w "%{http_code}\n" https://your-domain.com/api/v1/advisor/health &
done
wait
# Should see some 429 (Too Many Requests)
```

---

## ?? Security Best Practices

### Code Security

1. **Input Validation**
   - Validate all user inputs
   - Sanitize for SQL injection
   - Escape HTML/JavaScript
   - Use Pydantic models

2. **Error Handling**
   - Don't expose stack traces
   - Generic error messages to users
   - Detailed logs internally
   - Rate limit error responses

3. **Dependencies**
   - Pin versions in requirements.txt
   - Regular `pip audit` / `npm audit`
   - Automated dependency updates (Dependabot)

### Infrastructure Security

1. **Least Privilege**
   - Services run with minimal permissions
   - Database users have only needed grants
   - File permissions restrictive (600/700)

2. **Network Segmentation**
   - Frontend/backend on same private network
   - Database not exposed externally
   - Redis not exposed externally
   - Admin tools on separate network/VPN

3. **Regular Updates**
   - Weekly security patches
   - Monthly dependency updates
   - Quarterly major version upgrades

---

## ?? Security Contacts

- **Security Team:** security@antika-auction.com
- **Bug Bounty:** See SECURITY.md
- **Incident Response:** oncall@antika-auction.com

---

**Security Checklist Version:** 1.0.0  
**Next Review:** February 2, 2026
