# Rules

* Never read, write, or search files outside the project root directory. This is strictly prohibited.
* Always use `uv run` for Python commands in `backend/` (e.g. `uv run pytest`, `uv run ruff`, `uv run mypy`) — never `python3 -m` or bare `python`.
* Infrastructure resources managed by Terraform must be changed via Terraform config and the CD pipeline, not direct `aws` CLI writes. Read-only CLI calls (describe, get, list) are fine for diagnosis; fixes go through Terraform.

# Constitution

* Web-based with adaptive design
* Python backend
* TypeScript + Svelte frontend
* Deployed to AWS with near-zero cost as a hard constraint via terraform

# File Map

## Backend (`backend/`)
- `pyproject.toml` — Python project config, ruff/mypy settings
- `src/dev/server.py` — FastAPI local dev server; always authenticates as `dev@local.dev`; routes all prod endpoints plus dev-only helpers: `POST /test/seed-relation`, `POST /test/clear-relations`, `POST /test/seed-log-entry`, `POST /test/clear-log`; supports mock OAuth via `OAUTH_MOCK_TOKEN_ENDPOINT` env var for e2e tests
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
- `src/log/handler.py` — Lambda entry point for `GET /log`, `POST /log`, `PUT /log/{entry_id}`, `DELETE /log/{entry_id}`; supports `week_start`/`week_end` query params for time-windowed fetches
- `src/log/domain.py` — pure domain types (`LogEntry`, `LogEntryPatch`) and helpers (`make_entry`, `apply_patch`, `to_response_dict`)
- `src/log/repository.py` — DynamoDB adapter for log entries; keyed by `USER#<email>` / `LOG#<logged_at>#<entry_id>`
- `tests/` — pytest unit tests; DynamoDB tests use moto (`mock_aws`)

## Frontend (`frontend/`)
- `vite.config.ts` — in non-production mode, aliases `LoginPage.svelte` → `LoginPage.e2e.svelte` (used for both dev and e2e test runs)
- `src/lib/auth_service.ts` — production auth service (Google OAuth token exchange)
- `src/lib/auth_service.dev.ts` — dev auth service (calls FastAPI `/auth/session` with no credential)
- `src/lib/LoginPage.svelte` — production login page (Google Sign-In button)
- `src/lib/LoginPage.dev.svelte` — dev login page (plain "Login as dev@local.dev" button)
- `src/lib/LoginPage.e2e.svelte` — e2e login page; exchanges OAuth code via mock token endpoint; aliased in place of `LoginPage.svelte` in non-production builds
- `src/lib/ChatPage.svelte` — main chat/log interface; shows weekly log entries, handles message send/edit/delete
- `src/lib/ChatMessageList.svelte` — scrollable list of log entries for the current week
- `src/lib/ChatMessageRow.svelte` — individual log entry row with edit and delete actions
- `src/lib/ProfilePage.svelte` — profile editing page with back button; renders `ProfileEditor` and `RelationsPanel`
- `src/lib/ProfileEditor.svelte` — profile entry list with add/remove/edit; uses `TagCombobox`
- `src/lib/ProfileEntryRow.svelte` — single profile entry row (tag + text display/edit)
- `src/lib/RelationsPanel.svelte` — relations section: pending-received (confirm/reject), pending-sent (delete), confirmed (delete), and send form
- `src/lib/RelationRow.svelte` — single relation row with direction-aware action buttons
- `src/lib/LabelCombobox.svelte` — label input with autocomplete (mirrors TagCombobox pattern)
- `src/lib/TagCombobox.svelte` — tag input with autocomplete dropdown for profile entries
- `src/lib/chat_types.ts` — TypeScript types for log/chat messages
- `src/lib/home_service.ts` — API client for `GET /` (`HomeData` with `pending_relations_count`)
- `src/lib/log_service.ts` — API client for all `/log` endpoints; supports week-windowed fetches
- `src/lib/profile_service.ts` — API client for all `/profile` endpoints
- `src/lib/relations_service.ts` — API client for all `/relations` endpoints; base URL from `VITE_RELATIONS_API_URL`, falls back to `http://localhost:8000` in dev
- `src/lib/http_utils.ts` — shared `assertOk` helper used by all service modules

## Integration Tests (`integration_tests/`)
- `playwright.config.ts` — Chromium only, auto-starts Vite; backend must be running on :8000
- `start-mock-server.mjs` — local OAuth mock server used by `local_run.sh` for e2e auth flows
- `tests/login.test.ts` — e2e: login flow, assert Profile button visible
- `tests/profile.test.ts` — e2e: profile CRUD and tag autocomplete
- `tests/relations.test.ts` — e2e: send/confirm/reject/delete relations and badge count
- `tests/log.test.ts` — e2e: chat/log interface; message send, edit, delete, week navigation

## Infrastructure (`deploy/`)
- `main.tf` — root Terraform config; composes `modules/lambda` and `modules/frontend`
- `domain.tf` — custom domain setup: ACM certificate + Route53 records for `chaisromashkoi.org`
- `variables.tf` / `outputs.tf` — input variables and stack outputs
- `bootstrap/` — separate Terraform workspace for S3 state backend and DynamoDB lock table
- `modules/lambda/` — five Lambda functions (auth, app, profile, relations, log) + shared Lambda Layer (auth + session_guard) + single DynamoDB table with GSIs for profile, relations, and log access patterns
- `modules/frontend/` — S3 bucket + CloudFront distribution with six origins: S3 (static assets), auth Lambda, app Lambda, profile Lambda, relations Lambda, log Lambda

## Scripts (`scripts/`)
- `local_run.sh` — start backend (:8000), mock OAuth server, and frontend (:5173)
- `local_kill.sh` — stop both
- `e2e.sh` — start backend, run Playwright e2e suite
- `publish_adr.sh <file>` — push a local ADR file to the GitHub wiki and delete it locally
- `build_lambdas.sh` — package Lambda functions and shared layer into zips for the CD pipeline

## Claude Configuration (`.claude/`)

### Agents (`.claude/agents/`)
Subagents spawned by skills via the `Agent` tool:
- `python_developer.md` — implements backend changes; runs ruff + mypy + pytest after every edit
- `frontend_developer.md` — implements frontend changes; runs svelte-check after every edit
- `infrastructure_engineer.md` — modifies Terraform in `deploy/`; runs `terraform validate` + `terraform plan` after every change
- `dynamodb_architect.md` — designs DynamoDB schemas and access patterns; produces table/index definitions (no code or Terraform)

### Skills (`.claude/skills/`)
User-invocable slash commands:
- `/feature` — create a GitHub issue from a rough description
- `/analyze <issue>` — explore the codebase, produce an ADR, publish to the wiki, comment on the issue
- `/implement <issue>` — read the ADR, create a branch, dispatch to subagents, run all tests
- `/commit` — stage, write a commit message, and commit
- `python-developer` — reference skill loaded by `python_developer` agent (style guide + examples)
- `lambda-developer` — reference skill loaded by `python_developer` and `infrastructure_engineer` agents (Lambda architecture + conventions)

### Hooks (`.claude/hooks/`)
- `check_file_access.py` — blocks any tool call that reads or writes outside the project root

## Docs (GitHub Wiki)
- `adr/` — Architecture Decision Records; published by the architect agent via `scripts/publish_adr.sh`
- To read an existing ADR, clone the wiki inside the project: `git clone https://github.com/Salamahin/chai-s-romashkoi.wiki.git .wiki && cat .wiki/adr/<NNN>-<slug>.md` (delete `.wiki/` afterwards)
- ADR files must not be committed to this repo. They live exclusively in the GitHub wiki. If any `docs/adr/` ADR files are found locally, delete them.
