Cup Guard — macOS install (v2.2)

TRY IN THIS ORDER:

=== 1. The .app ===
1. Unzip CupGuard-macOS-arm64.zip
2. Drag CupGuard.app → Applications
3. Terminal:  xattr -cr /Applications/CupGuard.app
4. Right-click CupGuard.app → Open → Open

=== 2. If the icon bounces (won't open) ===
Double-click "Run Cup Guard.command" in the zip folder.
It runs the app from Terminal and saves errors to:
  ~/Library/Logs/CupGuard/launch.log
Send that log to whoever sent you this.

=== 3. If Screen Time blocks everything ===
A parent must allow Cup Guard under:
  Screen Time → Content & Privacy Restrictions → Allowed Apps

=== 4. Nuclear option (always works if you have internet) ===
Double-click install-from-source.sh in Terminal:
  bash install-from-source.sh
That installs from GitHub and puts "Run Cup Guard" on your Desktop.
Grant permissions to Terminal instead of Cup Guard.

Permissions (in System Settings → Privacy & Security):
  • Screen Recording — see the cup
  • Input Monitoring — 0 hotkey
  • Accessibility — E/Q keys
