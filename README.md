# About

**chai c romashkoi** is aimed to help a group of close relatives to watch out
their lifestyle such as food habits and working out sessions.

## Local Development

### One-time setup

1. Create `backend/.env`:
   ```
   SESSION_SECRET=any-random-string
   ```

2. Create `frontend/.env`:
   ```
   VITE_API_URL=http://localhost:8000
   ```

In local mode the Google OAuth flow is bypassed — a hardcoded `dev@local.dev` user is used instead. `GOOGLE_CLIENT_ID` is only required for production deployment. `VITE_RELATIONS_API_URL` is not required locally; the relations service falls back to `http://localhost:8000` automatically.

### Running

```bash
bash scripts/local_run.sh   # start backend (:8000) and frontend (:5173)
bash scripts/local_kill.sh  # stop both
```

### E2E tests

```bash
bash scripts/e2e.sh
```

Starts the backend, installs integration test dependencies if needed, then runs Playwright (which starts Vite automatically). Tests validate the full local login flow: button click → token exchange → app page.

### Set GitHub Actions secrets

| Secret name | Value |
|---|---|
| `GOOGLE_CLIENT_ID` | Google OAuth client ID from Google Cloud Console |
| `SESSION_SECRET` | A random string used to sign session JWTs (e.g. `openssl rand -hex 32`) |

`ci.yml` and `e2e.yml` require no secrets — the dev backend always authenticates as `dev@local.dev` and does not validate Google tokens.

## Development Dependencies

| Tool | Version | Purpose |
|------|---------|---------|
| [Python](https://www.python.org/) | >=3.12 | Backend runtime |
| [uv](https://docs.astral.sh/uv/) | latest | Python package manager |
| [Node.js](https://nodejs.org/) | >=20 | Frontend runtime |
| [Terraform](https://www.terraform.io/) | latest | Infrastructure provisioning |
