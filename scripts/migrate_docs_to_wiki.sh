#!/usr/bin/env bash
set -euo pipefail

WIKI_REPO="git@github.com:Salamahin/chai-s-romashkoi.wiki.git"
WIKI_DIR=$(mktemp -d)
DOCS_DIR="$(cd "$(dirname "$0")/.." && pwd)/docs/adr"

git clone "$WIKI_REPO" "$WIKI_DIR"
mkdir -p "$WIKI_DIR/adr"
cp "$DOCS_DIR"/*.md "$WIKI_DIR/adr/"

cd "$WIKI_DIR"
git add .
git commit -m "Migrate ADRs from docs/ to wiki"
git push
rm -rf "$WIKI_DIR"
echo "Migration complete."
