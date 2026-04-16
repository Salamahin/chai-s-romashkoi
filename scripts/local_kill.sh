#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="$REPO_ROOT/.local.pid"

if [ ! -f "$PID_FILE" ]; then
  echo "Nothing running (no $PID_FILE found)."
  exit 0
fi

read -r MOCK_PID BACKEND_PID FRONTEND_PID < "$PID_FILE"

kill "$MOCK_PID" 2>/dev/null && echo "Stopped mock OAuth server (pid $MOCK_PID)" || echo "Mock server already stopped"
kill "$BACKEND_PID" 2>/dev/null && echo "Stopped backend (pid $BACKEND_PID)" || echo "Backend already stopped"
kill "$FRONTEND_PID" 2>/dev/null && echo "Stopped frontend (pid $FRONTEND_PID)" || echo "Frontend already stopped"

rm "$PID_FILE"
