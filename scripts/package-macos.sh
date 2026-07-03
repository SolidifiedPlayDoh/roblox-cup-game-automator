#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

uv run --python 3.12 pyinstaller CupGuard.spec --noconfirm

APP="$ROOT/dist/CupGuard.app"
codesign --force --deep --sign - "$APP"

cp "$ROOT/share/Launch Cup Guard (debug).command" "$ROOT/dist/"
cp "$ROOT/share/README.txt" "$ROOT/dist/"

cd "$ROOT/dist"
rm -f CupGuard-share.zip
zip -r CupGuard-share.zip CupGuard.app "Launch Cup Guard (debug).command" README.txt
ditto -c -k --sequesterRsrc --keepParent CupGuard.app CupGuard-macOS-arm64.zip

echo "Built:"
ls -lh CupGuard-share.zip CupGuard-macOS-arm64.zip
