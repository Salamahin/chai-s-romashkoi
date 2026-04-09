#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../../../../" && pwd)"

echo "Killing leftover processes..."
pkill -f "dev_server.py" 2>/dev/null || true
pkill -f "vite" 2>/dev/null || true

echo "Starting backend..."
cd "$REPO_ROOT/backend" && uv run python dev_server.py &>/tmp/backend.log &

echo "Starting frontend..."
cd "$REPO_ROOT/frontend" && npm run dev &>/tmp/frontend.log &

echo "Waiting for initialization..."
sleep 4

echo "--- Backend ---"
curl -s http://localhost:8000/ || echo "FAILED"

echo ""
echo "--- Frontend ---"
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost:5173/ || echo "FAILED"
