#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "==> Linting backend"
cd "$REPO_ROOT/backend"
uv run ruff check src/
uv run mypy src/

echo "==> Packaging Lambda"
rm -rf dist
mkdir -p dist/package
uv export --no-dev --format requirements-txt > /tmp/requirements.txt
if [ -s /tmp/requirements.txt ]; then
  pip install -q -r /tmp/requirements.txt -t dist/package/
fi
cp -r src/hello dist/package/
cd dist/package && zip -qr ../function.zip . && cd "$REPO_ROOT/backend"

echo "==> Deploying Lambda"
cd "$REPO_ROOT/deploy"
terraform init -input=false
terraform apply -input=false -auto-approve -target=module.lambda

LAMBDA_URL=$(terraform output -raw lambda_function_url)
echo "Lambda URL: $LAMBDA_URL"

echo "==> Building frontend"
cd "$REPO_ROOT/frontend"
npm install
VITE_API_URL="$LAMBDA_URL" npm run build

echo "==> Deploying frontend"
cd "$REPO_ROOT/deploy"
terraform apply -input=false -auto-approve

CF_URL=$(terraform output -raw cloudfront_url)
echo ""
echo "Done! App available at: $CF_URL"
