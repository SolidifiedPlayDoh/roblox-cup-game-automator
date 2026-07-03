#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPO="$(cd "$ROOT/.." && pwd)"
DIST="$REPO/dist"
APP="$DIST/CupGuard.app"
BIN_NAME=CupGuard
EXEC_BUILD="$ROOT/.build/release/$BIN_NAME"
EXEC="$APP/Contents/MacOS/$BIN_NAME"
FRAMEWORKS="$APP/Contents/Frameworks"

cd "$ROOT"

# Release build — no Xcode toolchain rpath baked in when we strip below.
swift build -c release \
  -Xswiftc -O \
  -Xlinker -dead_strip \
  -Xlinker -rpath -Xlinker @executable_path/../Frameworks \
  -Xlinker -rpath -Xlinker /usr/lib/swift

if [[ ! -f "$EXEC_BUILD" ]]; then
  echo "Build failed: missing $EXEC_BUILD" >&2
  exit 1
fi

rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources" "$FRAMEWORKS"

cp "$EXEC_BUILD" "$EXEC"
chmod +x "$EXEC"

# Remove developer-machine rpaths (Xcode). These break launch on Macs without Xcode.
while IFS= read -r rpath; do
  case "$rpath" in
    *Xcode*|*Toolchain*|*Developer*)
      install_name_tool -delete_rpath "$rpath" "$EXEC" 2>/dev/null || true
      ;;
  esac
done < <(otool -l "$EXEC" | awk '/cmd LC_RPATH/{getline; getline; print $2}')

install_name_tool -add_rpath @executable_path/../Frameworks "$EXEC" 2>/dev/null || true

cat > "$APP/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>CFBundleDevelopmentRegion</key>
	<string>en</string>
	<key>CFBundleExecutable</key>
	<string>CupGuard</string>
	<key>CFBundleIdentifier</key>
	<string>com.solidifiedplaydoh.cupguard</string>
	<key>CFBundleInfoDictionaryVersion</key>
	<string>6.0</string>
	<key>CFBundleName</key>
	<string>Cup Guard</string>
	<key>CFBundleDisplayName</key>
	<string>Cup Guard</string>
	<key>CFBundlePackageType</key>
	<string>APPL</string>
	<key>CFBundleShortVersionString</key>
	<string>2.2.0</string>
	<key>CFBundleVersion</key>
	<string>5</string>
	<key>LSMinimumSystemVersion</key>
	<string>13.0</string>
	<key>NSHighResolutionCapable</key>
	<true/>
	<key>NSPrincipalClass</key>
	<string>NSApplication</string>
	<key>NSScreenCaptureUsageDescription</key>
	<string>Cup Guard watches the red cup rim on your screen.</string>
	<key>NSListenEventUsageDescription</key>
	<string>Cup Guard listens for the 0 key to calibrate on the cup rim.</string>
</dict>
</plist>
PLIST

# Bundle Swift runtime into the app so it launches without Xcode on the machine.
if xcrun --find swift-stdlib-tool >/dev/null 2>&1; then
  xcrun swift-stdlib-tool --copy --platform macosx \
    --scan-executable "$EXEC" \
    --destination "$FRAMEWORKS"
fi

# Launcher script — if Gatekeeper blocks the binary, this still runs from Terminal.
cat > "$DIST/Run Cup Guard.command" <<'CMD'
#!/bin/bash
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
APP="$DIR/CupGuard.app"
BIN="$APP/Contents/MacOS/CupGuard"
LOG="$HOME/Library/Logs/CupGuard/launch.log"
mkdir -p "$(dirname "$LOG")"

if [[ ! -x "$BIN" ]]; then
  echo "CupGuard.app not found next to this script."
  read -r -p "Press Enter…"
  exit 1
fi

xattr -cr "$APP" 2>/dev/null || true
echo "=== $(date) ===" >> "$LOG"
"$BIN" 2>&1 | tee -a "$LOG"
echo "Exit: ${PIPESTATUS[0]}" | tee -a "$LOG"
read -r -p "Press Enter to close…"
CMD
chmod +x "$DIST/Run Cup Guard.command"

cp "$REPO/share/README.txt" "$DIST/README.txt"
cp "$REPO/scripts/install-from-source.sh" "$DIST/install-from-source.sh"
chmod +x "$DIST/install-from-source.sh"

codesign --force --deep --sign - "$APP"

echo "=== RPATH check (should NOT list Xcode) ==="
otool -l "$EXEC" | awk '/cmd LC_RPATH/{getline; getline; print "  rpath:", $2}'

cd "$DIST"
rm -f CupGuard-native.zip CupGuard-macOS-arm64.zip
ditto -c -k --sequesterRsrc --keepParent CupGuard.app CupGuard-macOS-arm64.zip

zip CupGuard-macOS-arm64.zip "Run Cup Guard.command" README.txt install-from-source.sh

echo ""
echo "Built:"
ls -lh CupGuard-macOS-arm64.zip "$EXEC"
