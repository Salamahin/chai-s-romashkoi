#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="$REPO_ROOT/backend"
DIST="$BACKEND/dist"

rm -rf "$DIST" && mkdir -p "$DIST"

# --- Shared layer ---
# Export only production deps (no dev group) to a pip-compatible requirements file.
# --no-emit-project excludes the project package itself; handler source goes in
# separate handler zips, not in the layer.
cd "$BACKEND"
uv export --no-dev --no-emit-project -o "$DIST/requirements.txt"

# pip (not uv) is used here because uv does not support --target installation
# for layer assembly.
LAYER_DIR="$DIST/layer/python"
mkdir -p "$LAYER_DIR"
pip install --quiet -t "$LAYER_DIR" -r "$DIST/requirements.txt"

# Lambda layer structure must be python/<packages>/ so that the runtime resolves
# imports under /opt/python/.
cd "$DIST/layer"
zip -qr "$DIST/layer.zip" python/

# auth_handler.py is the sole entry-point file; auth.py and session_guard.py
# are shared utilities that live in the layer and are NOT bundled here.
cd "$BACKEND/src"
zip -qj "$DIST/auth.zip" auth_handler.py
zip -qr "$DIST/app.zip" app/
zip -qr "$DIST/profile.zip" profile/
zip -qr "$DIST/relations.zip" relations/
zip -qr "$DIST/log.zip" log/

echo "Lambda zips written to $DIST"
