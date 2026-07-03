#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPO="$(cd "$ROOT/.." && pwd)"
DIST="$REPO/dist"
APP="$DIST/CupGuard.app"
BIN_NAME=CupGuard

cd "$ROOT"
swift build -c release 2>&1

EXEC="$ROOT/.build/release/$BIN_NAME"
if [[ ! -f "$EXEC" ]]; then
  echo "Build failed: missing $EXEC" >&2
  exit 1
fi

rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"

cp "$EXEC" "$APP/Contents/MacOS/$BIN_NAME"

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
	<string>2.1.0</string>
	<key>CFBundleVersion</key>
	<string>4</string>
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

codesign --force --deep --sign - "$APP"

# Embed Swift runtime so older macOS versions can launch the binary.
if xcrun --find swift-stdlib-tool >/dev/null 2>&1; then
  xcrun swift-stdlib-tool --copy --platform macosx \
    --scan-executable "$APP/Contents/MacOS/$BIN_NAME" \
    --destination "$APP/Contents/Frameworks" || true
  codesign --force --deep --sign - "$APP"
fi

cd "$DIST"
rm -f CupGuard-native.zip CupGuard-macOS-arm64.zip
ditto -c -k --sequesterRsrc --keepParent CupGuard.app CupGuard-macOS-arm64.zip
cp CupGuard-macOS-arm64.zip CupGuard-native.zip

echo "Built native app:"
echo "  $APP"
echo "  $DIST/CupGuard-macOS-arm64.zip"
ls -lh "$APP/Contents/MacOS/$BIN_NAME" "$DIST/CupGuard-macOS-arm64.zip"
