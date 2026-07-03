Cup Guard — macOS install

1. Download CupGuard-macOS-arm64.zip from GitHub Releases (not AirDrop).
2. Double-click the zip to unzip.
3. Drag CupGuard.app into Applications.
4. Open Terminal and run:

   xattr -cr /Applications/CupGuard.app

5. Right-click CupGuard.app in Applications → Open → Open.
   (Required the first time — macOS blocks unsigned apps on double-click.)

6. In the app, tap Allow for each permission, or use Request all permissions.

7. In System Settings → Privacy & Security, enable Cup Guard for:
   - Screen Recording
   - Input Monitoring (for the 0 hotkey)
   - Accessibility (for E/Q keys)

Screen Time: if the app bounces and never opens, a parent must allow Cup Guard under
Screen Time → Content & Privacy Restrictions → Allowed Apps.

Still broken? Run in Terminal:

   /Applications/CupGuard.app/Contents/MacOS/CupGuard

Send the output. Log: ~/Library/Logs/CupGuard/native.log
