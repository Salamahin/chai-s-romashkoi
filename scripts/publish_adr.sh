#!/usr/bin/env bash
set -euo pipefail

FILE="$1"
FILENAME=$(basename "$FILE")
WIKI_REPO="git@github.com:Salamahin/chai-s-romashkoi.wiki.git"
WIKI_DIR=$(mktemp -d)

git clone "$WIKI_REPO" "$WIKI_DIR"
mkdir -p "$WIKI_DIR/adr"
cp "$FILE" "$WIKI_DIR/adr/$FILENAME"

cd "$WIKI_DIR"
git add "adr/$FILENAME"
git commit -m "Add ADR: $FILENAME"
git push
rm -rf "$WIKI_DIR"
rm -f "$FILE"
echo "Published $FILENAME to wiki."
