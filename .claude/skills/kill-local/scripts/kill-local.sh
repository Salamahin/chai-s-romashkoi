#!/usr/bin/env bash
set -euo pipefail

echo "Killing backend..."
pkill -f "dev_server.py" 2>/dev/null && echo "done" || echo "not running"

echo "Killing frontend..."
pkill -f "vite" 2>/dev/null && echo "done" || echo "not running"
