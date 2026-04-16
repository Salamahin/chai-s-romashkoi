#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "==> Installing integration test dependencies"
cd "$REPO_ROOT/integration_tests"
npm install --silent

echo "==> Running e2e tests (Playwright will start mock server, backend, and Vite automatically)"
npm run test:e2e
