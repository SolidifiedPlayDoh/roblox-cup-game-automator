#!/usr/bin/env bash
# Install Cup Guard from source — works when the .app won't open (Screen Time, Gatekeeper, etc.)
set -euo pipefail

REPO="${CUPGUARD_REPO:-SolidifiedPlayDoh/roblox-cup-game-automator}"
DIR="${1:-$HOME/cup-guard}"

echo "Installing Cup Guard to $DIR"
command -v git >/dev/null || { echo "Install git first: xcode-select --install"; exit 1; }

if [[ ! -d "$DIR/.git" ]]; then
  git clone "https://github.com/${REPO}.git" "$DIR"
else
  git -C "$DIR" pull --ff-only
fi

cd "$DIR"
command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

uv venv --python 3.12
uv pip install -e .

cat > "$HOME/Desktop/Run Cup Guard.command" <<'LAUNCHER'
#!/bin/bash
cd "$HOME/cup-guard"
./run.sh
LAUNCHER
chmod +x "$HOME/Desktop/Run Cup Guard.command"
xattr -cr "$HOME/Desktop/Run Cup Guard.command" 2>/dev/null || true

echo ""
echo "Done. Double-click 'Run Cup Guard' on your Desktop."
echo "Grant Screen Recording + Accessibility to Terminal when macOS asks."
