#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="$REPO_ROOT/.local.pid"

if [ -f "$PID_FILE" ]; then
  echo "Already running (found $PID_FILE). Run local_kill.sh first."
  exit 1
fi

echo "==> Starting backend on http://localhost:8000"
cd "$REPO_ROOT/backend"
uv run python dev_server.py &
BACKEND_PID=$!

echo "==> Starting frontend on http://localhost:5173"
cd "$REPO_ROOT/frontend"
npm run dev &
FRONTEND_PID=$!

echo "$BACKEND_PID $FRONTEND_PID" > "$PID_FILE"
echo "==> Both servers running (pids: backend=$BACKEND_PID frontend=$FRONTEND_PID)"
echo "    Run scripts/local_kill.sh to stop."
