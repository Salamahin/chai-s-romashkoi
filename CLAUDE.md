# Constitution

* Web-based with adaptive design
* Python backend
* TypeScript + Svelte frontend
* Deployed to AWS with near-zero cost as a hard constraint via terraform

# File Map

## Backend (`backend/`)
- `pyproject.toml` — Python project config, ruff/mypy settings
- `src/dev/server.py` — FastAPI local dev server; always authenticates as `dev@local.dev`, no Google OAuth; includes `/test/seed-relation` helper (dev-only, not routed in prod)
- `src/auth.py` — pure auth functions (Lambda Layer in prod)
- `src/session_guard.py` — `require_session` + `CORS_HEADERS` (Lambda Layer in prod)
- `src/auth_handler.py` — Lambda entry point for `POST /auth/session`
- `src/app/handler.py` — Lambda entry point for `GET /`; returns `pending_relations_count` for the home badge
- `src/app/dispatcher.py` — single-Lambda dispatcher that routes to the above handlers by path
- `src/profile/handler.py` — Lambda entry point for `GET /profile`, `PUT /profile`, `GET /profile/tags`
- `src/profile/domain.py` — pure domain types and patch logic
- `src/profile/repository.py` — DynamoDB adapter for profile entries
- `src/profile/tags.py` — known-tags query over a profile
- `src/relations/handler.py` — Lambda entry point for `GET/POST /relations`, `POST /relations/{id}/confirm`, `DELETE /relations/{id}`, `GET /relations/labels`
- `src/relations/domain.py` — pure domain types (`RelationRecord`) and business logic (`build_send_records`, `build_confirmed_records`, `normalise_label`)
- `src/relations/repository.py` — DynamoDB adapter for relations; uses `transact_write_items` for all pair operations; reads `PROFILES_TABLE_NAME` env var
- `src/relations/label_suggestions.py` — derives distinct label set from a collection of `RelationRecord`
- `tests/` — pytest unit tests; DynamoDB tests use moto (`mock_aws`)

## Frontend (`frontend/`)
- `vite.config.ts` — in dev mode, aliases `LoginPage.svelte` → `LoginPage.dev.svelte` and `auth_service` → `auth_service.dev.ts`
- `src/lib/auth_service.ts` — production auth service (Google OAuth token exchange)
- `src/lib/auth_service.dev.ts` — dev auth service (calls FastAPI `/auth/session` with no credential)
- `src/lib/LoginPage.svelte` — production login page (Google Sign-In button)
- `src/lib/LoginPage.dev.svelte` — dev login page (plain "Login as dev@local.dev" button)
- `src/lib/HomePage.svelte` — post-login home page; fetches pending badge count, navigates to ProfilePage
- `src/lib/ProfilePage.svelte` — profile editing page with back button; renders `RelationsPanel` below profile entries
- `src/lib/RelationsPanel.svelte` — relations section: pending-received (confirm/reject), pending-sent (delete), confirmed (delete), and send form
- `src/lib/RelationRow.svelte` — single relation row with direction-aware action buttons
- `src/lib/LabelCombobox.svelte` — label input with autocomplete (mirrors TagCombobox pattern)
- `src/lib/home_service.ts` — API client for `GET /` (`HomeData` with `pending_relations_count`)
- `src/lib/relations_service.ts` — API client for all `/relations` endpoints; base URL from `VITE_RELATIONS_API_URL`, falls back to `http://localhost:8000` in dev
- `src/lib/http_utils.ts` — shared `assertOk` helper used by all service modules

## Integration Tests (`integration_tests/`)
- `playwright.config.ts` — Chromium only, auto-starts Vite; backend must be running on :8000
- `tests/login.test.ts` — e2e: login flow, assert Profile button visible
- `tests/profile.test.ts` — e2e: profile CRUD and tag autocomplete
- `tests/relations.test.ts` — e2e: send/confirm/reject/delete relations and badge count

## Infrastructure (`deploy/`)

## Scripts (`scripts/`)
- `local_run.sh` — start backend (:8000) and frontend (:5173)
- `local_kill.sh` — stop both
- `e2e.sh` — start backend, run Playwright e2e suite

## Claude Configuration (`.claude/`)

## Docs (`docs/`)
- `adr/` — Architecture Decision Records (produced by architect agent)
