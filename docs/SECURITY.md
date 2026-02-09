# Security

## Overview

GenAI Auto implements multiple security layers for a production-ready PoC:

| Feature | Implementation | Status |
|---------|---------------|--------|
| Authentication | JWT (HS256) with Argon2 hashing | Implemented |
| PII Protection | Regex-based masking in logs | Implemented |
| Input Validation | Pydantic schema enforcement | Implemented |
| Human Handoff | Safety and sensitivity detection | Implemented |
| Rate Limiting | Configurable per endpoint | Implemented |
| TLS/HTTPS | Via reverse proxy (not built-in) | Requires setup |
| API Key Rotation | Not implemented | PoC limitation |

---

## Authentication (JWT)

**Implementation**: `src/api/auth/jwt_auth.py`

### How It Works

1. User registers with email/password
2. Password hashed with **Argon2** (OWASP recommended, no 72-byte limit)
3. Server returns **access token** (30 min) + **refresh token** (7 days)
4. Client sends access token in `Authorization: Bearer <token>` header
5. On expiry, client uses refresh token to get new access token

### Configuration

```bash
JWT_SECRET_KEY=<generate with: openssl rand -hex 32>
JWT_ALGORITHM=HS256
JWT_ACCESS_EXPIRE_MINUTES=30
JWT_REFRESH_EXPIRE_DAYS=7
```

### Token Payload

```json
{
  "sub": "user-uuid",
  "email": "user@example.com",
  "name": "User Name",
  "type": "access",
  "exp": 1707500000,
  "iat": 1707498200
}
```

### Endpoints Requiring Authentication

| Endpoint | Auth Required |
|----------|:------------:|
| POST /api/v1/auth/register | No |
| POST /api/v1/auth/login | No |
| POST /api/v1/auth/refresh | No (uses refresh token) |
| GET /api/v1/auth/me | Yes |
| POST /api/v1/chat | Optional |
| POST /api/v1/documents/upload | Yes |
| POST /api/v1/documents/ingest-text | Yes |
| POST /api/v1/documents/search | Optional |
| GET /api/v1/documents/ | Yes |
| DELETE /api/v1/documents/{source} | Yes |
| WS /ws/chat | No (PoC mode) |
| GET /api/v1/metrics | No |

---

## PII Protection

**Implementation**: `src/api/pii.py`

### Masked Patterns

| Data Type | Pattern | Masked As |
|-----------|---------|-----------|
| SSN (US) | `\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b` | `***-**-****` |
| Email | `[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z\|a-z]{2,}` | `***@***.***` |
| Phone (US) | `(?:\+1\s?)?(?:\(?\d{3}\)?\s?)?[-.\s]?\d{3}[-.\s]?\d{4}` | `(***) ***-****` |
| Credit Card | `(?:\d{4}[-\s]?){3}\d{4}` | `**** **** **** ****` |
| VIN | `[A-HJ-NPR-Z0-9]{17}` | `*****************` |
| License Plate | `[A-Z0-9]{1,7}` | `*******` |

### PIILogger

Wraps structlog to automatically mask PII in all log outputs:

```python
from src.api.pii import PIIMasker, PIILogger

masker = PIIMasker()
logger = PIILogger()

# PII automatically masked in logs
logger.info("User registered", email="john@example.com")
# Output: "User registered" email="***@***.***"
```

### Configuration

```bash
MASK_PII=true  # Enable/disable PII masking
```

---

## Human Handoff & Safety Detection

**Implementation**: `src/api/handoff.py`

### Escalation Triggers

| Trigger | Condition | Priority |
|---------|-----------|----------|
| Low Confidence | Score < 0.7 (configurable) | Medium |
| User Request | Keywords: "speak to human", "real person", etc. | High |
| Sensitive Topics | Keywords: accident, injury, lawsuit, legal, recall | High |
| Safety Concerns | Keywords: brake failure, airbag, fuel leak, fire, smoke | Critical |
| Complex Issues | Manual escalation by agent | Medium |
| Repeated Failures | Multiple failed attempts | Medium |

### Webhook Integration

When configured, escalation sends POST to `HUMAN_SUPPORT_WEBHOOK`:

```json
{
  "escalation_id": "uuid",
  "session_id": "session-123",
  "reason": "safety",
  "confidence_score": 0.45,
  "conversation_summary": "Customer reported brake failure...",
  "last_user_message": "My brakes are not working"
}
```

### Configuration

```bash
CONFIDENCE_THRESHOLD=0.7
HUMAN_SUPPORT_WEBHOOK=https://your-webhook.com/escalations
```

---

## Input Validation

All API inputs validated with **Pydantic** schemas:

- Email format validation
- Password minimum length (8+ characters)
- Message content required (non-empty)
- Document type must be valid enum value
- File type validation for uploads (PDF, DOCX, TXT, MD)

---

## Known PoC Limitations

These are intentional simplifications for the PoC that should be addressed for production:

| Limitation | Risk | Production Fix |
|------------|------|----------------|
| No TLS in Docker | Traffic in plaintext | Add reverse proxy (Nginx/Traefik) with Let's Encrypt |
| WebSocket no auth | Anyone can connect to chat | Add JWT validation on WS connect |
| CORS allows all origins | Cross-origin requests | Restrict to specific domains |
| JWT secret in .env | Secret in plaintext file | Use secrets manager (AWS/GCP/Azure) |
| No API key rotation | Stale credentials | Implement key rotation policy |
| No brute force protection | Password guessing | Add account lockout or CAPTCHA |
| No audit logging | No security trail | Add audit log for sensitive operations |

---

## Production Security Checklist

Before deploying to production:

- [ ] **Secrets**: Change `JWT_SECRET_KEY` (use `openssl rand -hex 32`)
- [ ] **Secrets**: Set strong `POSTGRES_PASSWORD`
- [ ] **Secrets**: Use a secrets manager for all credentials
- [ ] **TLS**: Configure HTTPS via reverse proxy
- [ ] **CORS**: Restrict `allow_origins` to specific domains
- [ ] **WebSocket**: Add authentication to `/ws/chat`
- [ ] **Rate Limiting**: Configure appropriate limits per endpoint
- [ ] **Firewall**: Restrict database/Redis ports (not exposed publicly)
- [ ] **Network**: Use Docker network isolation
- [ ] **Updates**: Keep dependencies updated (run `pip-audit` or `safety check`)
- [ ] **Monitoring**: Enable security alerts in Alertmanager
- [ ] **Backup**: Configure automated database backups
- [ ] **Logging**: Verify PII masking is enabled (`MASK_PII=true`)

---

## Source Files

- JWT Authentication: `src/api/auth/jwt_auth.py`
- PII Masking: `src/api/pii.py`
- Human Handoff: `src/api/handoff.py`
- Input Validation: Pydantic models in route files
- CORS Configuration: `src/api/main.py`
