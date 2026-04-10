#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Kill background backend on exit
BACKEND_PID=""
cleanup() {
  if [ -n "$BACKEND_PID" ]; then
    kill "$BACKEND_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

echo "==> Starting backend on http://localhost:8000"
cd "$REPO_ROOT/backend"
uv run python -m dev.server &
BACKEND_PID=$!

echo "==> Waiting for backend..."
for i in $(seq 1 20); do
  if curl -s http://localhost:8000/ >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

echo "==> Installing integration test dependencies"
cd "$REPO_ROOT/integration_tests"
npm install --silent

echo "==> Running e2e tests (Playwright will start Vite automatically)"
npm run test:e2e
