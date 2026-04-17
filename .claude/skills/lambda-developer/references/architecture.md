# Architecture

## Overview

```
Browser
  │
  ▼
CloudFront distribution
  ├── /auth/*         → auth Lambda Function URL
  ├── /profile*       → profile Lambda Function URL
  ├── /relations*     → relations Lambda Function URL
  ├── /log*           → log Lambda Function URL
  └── /*  (default)   → app Lambda Function URL

Each Lambda Function URL:
  - authorization_type = "NONE"  (CloudFront is the edge; Lambdas trust the session JWT)
  - CORS headers emitted by the Lambda itself (CloudFront passes them through)
```

## Lambda Layer (shared code)

**Layer path in zip**: `python/`

Modules in the layer (source: `backend/src/`):
- `auth.py` — JWT sign/verify, Google token verification, `SessionClaims`
- `session_guard.py` — `require_session`, `CORS_HEADERS`

Every Lambda has the layer attached. Handlers import from these as top-level modules (no package prefix).

## Lambda functions

| Name suffix | Handler | Routes handled |
|---|---|---|
| `auth-handler` | `auth_handler.handler` | `POST /auth/session` |
| `app-handler` | `app.handler.handler` | `GET /` |
| `profile-handler` | `profile.handler.handler` | `GET /profile`, `PUT /profile`, `GET /profile/tags` |
| `relations-handler` | `relations.handler.handler` | `GET/POST /relations`, `POST /relations/{id}/confirm`, `DELETE /relations/{id}`, `GET /relations/labels` |
| `log-handler` | `log.handler.handler` | `GET /log`, `POST /log`, `PUT /log/{entry_id}`, `DELETE /log/{entry_id}` |

Each handler is **standalone** — it reads its own env vars, constructs its own clients, and handles its own routing. There is no shared dispatcher in prod; routing happens at CloudFront.

## CloudFront path routing

CloudFront uses ordered cache behaviors:

| Path pattern | Origin | Notes |
|---|---|---|
| `/auth/*` | auth Lambda Function URL | `POST /auth/session` hits here |
| `/profile` | profile Lambda Function URL | exact path |
| `/profile/*` | profile Lambda Function URL | sub-paths |
| `/relations` | relations Lambda Function URL | exact path |
| `/relations/*` | relations Lambda Function URL | sub-paths |
| `/log` | log Lambda Function URL | exact path |
| `/log/*` | log Lambda Function URL | sub-paths |
| `/*` (default) | app Lambda Function URL | catch-all |

CloudFront is also the origin for the frontend static assets (S3).

## Environment variables per Lambda

| Variable | auth | app | profile | relations | log |
|---|---|---|---|---|---|
| `SESSION_SECRET` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `JWKS_URL` | ✓ | — | — | — | — |
| `GOOGLE_CLIENT_ID` | ✓ | — | — | — | — |
| `SESSION_TTL_SECONDS` | ✓ | — | — | — | — |
| `PROFILES_TABLE_NAME` | — | ✓ | ✓ | ✓ | ✓ |

## Cost profile

- Lambda: pay per invocation, free tier covers ~1M req/month
- Lambda Layer: no additional cost
- CloudFront: pay per request + transfer; free tier covers 10M req/month
- All near-zero at personal scale
