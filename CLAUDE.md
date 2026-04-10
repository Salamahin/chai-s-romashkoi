# Constitution

* Web-based with adaptive design
* Python backend
* TypeScript + Svelte frontend
* Deployed to AWS with near-zero cost as a hard constraint via terraform

# File Map

## Backend (`backend/`)
- `pyproject.toml` — Python project config, ruff/mypy settings
- `src/dev/server.py` — FastAPI local dev server; always authenticates as `dev@local.dev`, no Google OAuth
- `src/auth.py` — pure auth functions (Lambda Layer in prod)
- `src/session_guard.py` — `require_session` + `CORS_HEADERS` (Lambda Layer in prod)
- `src/auth_handler.py` — Lambda entry point for `POST /auth/session`
- `src/app/handler.py` — Lambda entry point for `GET /`
- `src/profile/handler.py` — Lambda entry point for `GET /profile`, `PUT /profile`, `GET /profile/tags`
- `src/profile/domain.py` — pure domain types and patch logic
- `src/profile/repository.py` — DynamoDB adapter for profile entries
- `src/profile/tags.py` — known-tags query over a profile
- `tests/` — pytest unit tests; DynamoDB tests use moto (`mock_aws`)

## Frontend (`frontend/`)
- `vite.config.ts` — in dev mode, aliases `LoginPage.svelte` → `LoginPage.dev.svelte` and `auth_service` → `auth_service.dev.ts`
- `src/lib/auth_service.ts` — production auth service (Google OAuth token exchange)
- `src/lib/auth_service.dev.ts` — dev auth service (calls FastAPI `/auth/session` with no credential)
- `src/lib/LoginPage.svelte` — production login page (Google Sign-In button)
- `src/lib/LoginPage.dev.svelte` — dev login page (plain "Login as dev@local.dev" button)

## Integration Tests (`integration_tests/`)
- `playwright.config.ts` — Chromium only, auto-starts Vite; backend must be running on :8000
- `tests/login.test.ts` — e2e: click dev login button, assert app message appears

## Infrastructure (`deploy/`)

## Scripts (`scripts/`)
- `local_run.sh` — start backend (:8000) and frontend (:5173)
- `local_kill.sh` — stop both
- `e2e.sh` — start backend, run Playwright e2e suite

## Claude Configuration (`.claude/`)

## Docs (`docs/`)
- `adr/` — Architecture Decision Records (produced by architect agent)
