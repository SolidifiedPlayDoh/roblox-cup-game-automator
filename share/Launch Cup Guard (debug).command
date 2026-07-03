#!/bin/bash
# Double-click this if Cup Guard bounces and disappears.
# It runs the app from Terminal so you can see any error text.
set -euo pipefail

APP="${1:-/Applications/CupGuard.app}"
BIN="$APP/Contents/MacOS/CupGuard"
LOG="$HOME/Library/Logs/CupGuard/launch.log"

if [[ ! -x "$BIN" ]]; then
  echo "Cup Guard not found at: $APP"
  echo "Drag CupGuard.app into /Applications first, or pass the path:"
  echo "  $0 ~/Downloads/CupGuard.app"
  read -r -p "Press Enter to close…"
  exit 1
fi

echo "Launching Cup Guard…"
echo "Log file: $LOG"
echo

xattr -cr "$APP" 2>/dev/null || true
"$BIN" 2>&1 | tee -a "$LOG"
status=${PIPESTATUS[0]}
echo
echo "Exit code: $status"
read -r -p "Press Enter to close…"
exit "$status"
