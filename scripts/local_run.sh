#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="$REPO_ROOT/.local.pid"

if [ -f "$PID_FILE" ]; then
  echo "Already running (found $PID_FILE). Run local_kill.sh first."
  exit 1
fi

echo "==> Starting mock OAuth server on http://localhost:4444"
cd "$REPO_ROOT/integration_tests"
node start-mock-server.mjs &
MOCK_PID=$!

echo "==> Waiting for mock server..."
for i in $(seq 1 20); do
  if curl -sf http://localhost:4444/.well-known/openid-configuration > /dev/null 2>&1; then
    break
  fi
  sleep 0.5
done

export OAUTH_MOCK_TOKEN_ENDPOINT=http://localhost:4444/token
export OAUTH_VALID_ISSUERS=http://localhost:4444
export JWKS_URL=http://localhost:4444/jwks
export OAUTH_REDIRECT_URI=http://localhost:5173/
export GOOGLE_CLIENT_ID=e2e-client
export VITE_OAUTH_ISSUER_URL=http://localhost:4444
export VITE_GOOGLE_CLIENT_ID=e2e-client

echo "==> Starting backend on http://localhost:8000"
cd "$REPO_ROOT/backend"
uv run python -m dev.server &
BACKEND_PID=$!

echo "==> Starting frontend on http://localhost:5173"
cd "$REPO_ROOT/frontend"
npm run dev &
FRONTEND_PID=$!

echo "$MOCK_PID $BACKEND_PID $FRONTEND_PID" > "$PID_FILE"
echo "==> All servers running (pids: mock=$MOCK_PID backend=$BACKEND_PID frontend=$FRONTEND_PID)"
echo "    Run scripts/local_kill.sh to stop."
