# 001. Google OAuth Authentication

Date: 2026-04-10
Status: Proposed

## Context

The application currently has no authentication. A new requirement (Issue #1) states that on page load the user must be prompted to authenticate with their Google account before seeing any application content. The prompt must show only a background and a "Sign in with Google" button — nothing else.

Current infrastructure constraints:
- Backend is a single Python 3.12 AWS Lambda exposed via a Lambda Function URL (no API Gateway).
- Frontend is a Svelte 5 SPA built with Vite, served from S3 behind CloudFront.
- No database, no session store, no custom domain — the CloudFront distribution uses its default `*.cloudfront.net` certificate.
- The hard constraint is near-zero AWS cost, which rules out services with fixed hourly charges (e.g., NAT Gateways, RDS, ElastiCache, Cognito's advanced-security tier).

Google OAuth has two common integration patterns:
1. **Backend-driven Authorization Code Flow** — the browser is redirected to Google; Google redirects back to a backend callback endpoint that exchanges the code for tokens, issues a session cookie, and redirects the browser to the SPA.
2. **Frontend-driven Implicit / PKCE flow with ID-token verification** — the browser handles the Google redirect entirely; the resulting ID token (JWT) is sent to the backend on every API call and verified there.

Because the frontend is a static SPA with no server-side rendering capability and the Lambda already owns all business logic, the cleanest boundary is: **the browser initiates the Google redirect, receives a Google ID token (via the Authorization Code + PKCE flow handled fully in the browser using Google's Identity Services library), and passes that short-lived ID token to the backend on every request. The backend verifies the token's signature and claims against Google's public JWKS endpoint and returns a short-lived signed session token (JWT) that the frontend stores in memory and attaches as a Bearer header on all subsequent Lambda calls.**

Session persistence across page reloads is handled by storing the session JWT in `sessionStorage` (cleared on tab close) rather than `localStorage` (persistent, larger XSS surface) or a cookie (requires `SameSite`/`Secure` configuration that is awkward with `*.cloudfront.net`).

No AWS Cognito, no DynamoDB sessions table, and no API Gateway are introduced, keeping the cost delta at zero (Lambda invocations for the token-exchange endpoint are billed identically to any other Lambda call; Google's JWKS endpoint is a free public HTTPS call).

## Decision

We adopt a **stateless JWT session pattern over Google Identity Services (GIS) browser flow**:

1. The frontend loads a `LoginPage` Svelte component that renders only a background and a "Sign in with Google" button. GIS's `google.accounts.id.initialize` / `renderButton` APIs drive the Google popup/redirect.
2. On successful Google sign-in, GIS delivers a **Google ID token** (a signed JWT) to a frontend callback.
3. The frontend POSTs the Google ID token to a new Lambda endpoint `POST /auth/session`.
4. The Lambda `auth` handler verifies the ID token by fetching Google's JWKS (`https://www.googleapis.com/oauth2/v3/certs`) and checking signature, `aud` (must equal the configured Google Client ID), `iss`, and `exp`. This verification is a pure function that receives the raw token string, the JWKS payload, and the current UTC timestamp as inputs.
5. On success, the Lambda signs and returns a short-lived **session JWT** (15-minute expiry, HS256, secret from Lambda environment variable). The payload contains `sub` (Google user ID), `email`, and `exp`.
6. The frontend stores the session JWT in `sessionStorage` and transitions from `LoginPage` to `AppPage`.
7. Every subsequent Lambda API call includes `Authorization: Bearer <session_jwt>`. A shared `verify_session_token` pure function (receiving the token string, secret, and current UTC timestamp) validates it at the top of every handler.
8. When the session JWT is expired or absent, the Lambda returns HTTP 401; the frontend reacts by clearing `sessionStorage` and rendering `LoginPage` again.

The Google Client ID is a build-time `VITE_GOOGLE_CLIENT_ID` environment variable injected into the Svelte app. The session-signing secret is a runtime Lambda environment variable `SESSION_SECRET`. Both are managed outside Terraform state (i.e., passed in as sensitive variables at deploy time) to avoid secrets in state files.

## Components

### Backend

**Module `auth.token_verifier`** (pure)
```
GoogleClaims:
  sub: str
  email: str
  exp: int
  aud: str
  iss: str

JwksPayload: dict  # raw parsed JSON from Google

VerificationError: typed exception

def verify_google_id_token(
    raw_token: str,
    jwks: JwksPayload,
    expected_audience: str,
    now_utc: int,          # Unix timestamp injected at boundary
) -> GoogleClaims
# Raises VerificationError on any failure.
```

**Module `auth.session_signer`** (pure)
```
SessionClaims:
  sub: str
  email: str
  exp: int

def sign_session_token(
    claims: SessionClaims,
    secret: str,
    now_utc: int,
    ttl_seconds: int,
) -> str   # signed JWT string

def verify_session_token(
    raw_token: str,
    secret: str,
    now_utc: int,
) -> SessionClaims
# Raises VerificationError on expiry or bad signature.
```

**Module `auth.jwks_client`** (side-effectful, boundary only)
```
def fetch_jwks(url: str) -> JwksPayload
# Makes HTTPS GET to Google's JWKS endpoint. Called only from the handler.
```

**Module `auth.handler`** (Lambda entry point, boundary)
```
AuthConfig:
  google_client_id: str
  session_secret: str
  jwks_url: str
  session_ttl_seconds: int

def handler(event: dict[str, object], context: object) -> dict[str, object]
# Reads AuthConfig from environment variables.
# Calls fetch_jwks (side effect).
# Reads current UTC timestamp (side effect).
# Delegates to verify_google_id_token and sign_session_token (pure).
# Returns { statusCode, headers, body }.
```

**Module `hello.guard`** (pure, shared)
```
def require_session(
    headers: dict[str, str],
    secret: str,
    now_utc: int,
) -> SessionClaims
# Extracts Bearer token from headers, calls verify_session_token.
# Raises VerificationError on failure.
```

`hello.handler.handler` is updated to call `require_session` before building the response, returning HTTP 401 on `VerificationError`.

### Frontend

**Component `LoginPage.svelte`**
- Loads the GIS script (`accounts.google.com/gsi/client`).
- Calls `google.accounts.id.initialize` with Client ID and a `callback` that receives the credential (Google ID token).
- Renders only a full-screen background div and the GIS-rendered button. No other text or controls.
- On credential receipt, calls `AuthService.exchangeToken(credential)`.

**Component `AppPage.svelte`**
- The existing `App.svelte` content, now rendered only when authenticated.
- Uses `AuthService.getSessionToken()` to attach the Bearer header on fetch calls.

**Module `auth_service.ts`** (stateful boundary adapter)
```typescript
interface SessionToken {
  raw: string
  expiresAtMs: number
}

interface AuthService {
  exchangeToken(googleIdToken: string): Promise<void>
  getSessionToken(): string | null   // null = not authenticated
  clearSession(): void
}
```
- `exchangeToken` POSTs to `VITE_API_URL/auth/session`, stores the returned JWT in `sessionStorage`.
- `getSessionToken` reads from `sessionStorage`, returns null if absent or client-side expiry check fails.
- `clearSession` removes from `sessionStorage`.

**Component `App.svelte`** (updated, routing root)
- Reads `AuthService.getSessionToken()` on mount.
- Renders `LoginPage` when null, `AppPage` otherwise.
- Listens for a 401 response from any fetch call (via a shared `apiFetch` wrapper) and calls `AuthService.clearSession()`, triggering re-render to `LoginPage`.

### AWS / Infrastructure

No new AWS services are added. The only Terraform changes are:

1. **Lambda module**: Add `POST /auth/session` as a recognized route inside the handler (the Lambda Function URL already accepts all HTTP methods; routing is handled in Python by inspecting `event["requestContext"]["http"]["method"]` and `event["rawPath"]`).
2. **Lambda CORS**: Change `allow_methods` from `["GET"]` to `["GET", "POST"]` and add `"authorization"` to `allow_headers`.
3. **Lambda environment variables**: Add `GOOGLE_CLIENT_ID`, `SESSION_SECRET`, `JWKS_URL` (defaulting to `https://www.googleapis.com/oauth2/v3/certs`), `SESSION_TTL_SECONDS` (defaulting to `900`).
4. **Frontend module**: Add `VITE_GOOGLE_CLIENT_ID` and `VITE_API_URL` to the Vite build step (already exists for `VITE_API_URL`; add the Client ID).

## Data Flow

```
Browser                         Lambda                    Google
  |                               |                          |
  |-- loads SPA ----------------->|                          |
  |<- LoginPage (button only) ----|                          |
  |                               |                          |
  |-- [user clicks button] ------>|                          |
  |                               |                          |
  |-- GIS popup ------------------------------------------>|
  |<- Google ID token (JWT) -------------------------------|
  |                               |                          |
  |-- POST /auth/session -------->|                          |
  |   { credential: "<id_token>" }|-- GET JWKS ------------->|
  |                               |<- JwksPayload ----------|
  |                               |                          |
  |                               |-- verify_google_id_token (pure)
  |                               |-- sign_session_token (pure)
  |                               |                          |
  |<- { session_token: "..." } ---|                          |
  |   store in sessionStorage     |                          |
  |                               |                          |
  |-- GET / (API call) ---------->|                          |
  |   Authorization: Bearer <jwt> |-- require_session (pure)|
  |                               |-- make_hello_response    |
  |<- 200 { message } ------------|                          |
```

## Boundary Map

| Location | Side effect | Enters domain as |
|---|---|---|
| `auth.handler` | Read env vars | `AuthConfig` struct |
| `auth.handler` | Read wall clock (`datetime.utcnow()`) | `now_utc: int` |
| `auth.jwks_client.fetch_jwks` | HTTPS GET to Google JWKS | `JwksPayload` |
| `auth.handler` | Write HTTP response | — |
| `hello.handler` | Read wall clock | `now_utc: int` |
| `AuthService.exchangeToken` | `fetch` POST to Lambda, `sessionStorage.setItem` | — |
| `AuthService.getSessionToken` | `sessionStorage.getItem` | `string \| null` |
| `LoginPage` (GIS callback) | Google popup, DOM render | `googleIdToken: string` |

All token verification and signing logic is pure (no I/O, no mutation of external state).

## Alternatives Considered

**AWS Cognito User Pools with Google as federated IdP.** Cognito handles the OAuth dance, token issuance, and refresh natively. Rejected because Cognito has no free tier after the first 50 MAU on the advanced-security features and adds a fixed operational surface (hosted UI domain, User Pool JWKS rotation) for a personal-scale app. The simple JWT approach costs nothing.

**Backend Authorization Code Flow (Lambda as OAuth callback).** Google redirects to a Lambda URL, which exchanges the code for tokens and sets a `Set-Cookie` header. Rejected because Lambda Function URLs with the default `*.cloudfront.net` domain make `Secure; SameSite=Strict` cookies reliable but the redirect URI registered in Google Cloud Console would need to be the raw Lambda Function URL (which changes on re-deploy unless pinned). It also requires storing refresh tokens somewhere (DynamoDB) or accepting short-lived sessions — introducing DB cost. The GIS browser flow avoids all of this.

**Store session in `localStorage` instead of `sessionStorage`.** Provides persistence across tab closes. Rejected because it increases the XSS token-theft window with no meaningful UX benefit for this app, and the 15-minute session TTL already requires re-authentication on next visit regardless.

## Consequences

**Easier:**
- No new AWS services or fixed-cost resources are required.
- Token verification is a pure function, making it trivially unit-testable without mocks.
- The LoginPage requirement (only background + button) maps directly to a dedicated Svelte component with no routing library needed.
- JWKS are fetched on demand per Lambda cold-start; given low traffic this is fine. If latency becomes a concern, the JWKS response can be cached in the Lambda process global scope between warm invocations.

**Harder:**
- The Lambda must be extended to handle routing (`rawPath` + method dispatch) since it currently has a single handler for all requests. A lightweight dispatcher must be added before any other business logic.
- The GIS library is a third-party script loaded from `accounts.google.com`. CSP headers must allow this origin; currently CloudFront sends no custom CSP headers, so none need changing, but this must be kept in mind if a CSP is added later.
- The session secret (`SESSION_SECRET`) must be rotated manually. There is no secret rotation mechanism. This is acceptable for a near-zero-cost personal app but is a commitment to document in an operational runbook.
- Google ID tokens are valid for 1 hour at Google's discretion; if the user's Google session is revoked, the Lambda has no way to know until the session JWT expires (up to 15 minutes). This is an accepted trade-off of the stateless approach.

**Open questions for the implementer:**
1. Should the JWKS response be cached in the Lambda module global scope between warm invocations to reduce latency and external calls? If yes, what cache TTL (Google rotates keys roughly every 6 hours)?
2. What Python library should be used for JWT signing/verification (`PyJWT` vs `python-jose` vs hand-rolled with `cryptography`)? `PyJWT` with `cryptography` extra is the most maintained option.
3. Should `SESSION_SECRET` be injected via AWS Systems Manager Parameter Store (free tier: 10,000 API calls/month) or as a plain Lambda environment variable? SSM is safer but adds a `boto3` call at cold-start.
4. The Google Client ID must be registered in Google Cloud Console with the CloudFront domain as an authorised JavaScript origin. The implementer must document this one-time manual step.
5. Is a 15-minute session TTL acceptable, or should a longer TTL (e.g., 8 hours) with a refresh mechanism be implemented? A refresh mechanism requires the frontend to detect near-expiry and POST a new Google ID token silently via GIS's `prompt: 'none'` mode.
