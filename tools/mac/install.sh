#!/bin/bash
# One-time setup. Run in Terminal:  bash ~/Documents/Zwift/Workouts/.ironman-sync/install.sh
set -e
HERE="$HOME/Documents/Zwift/Workouts/.ironman-sync"
LABEL="com.amizuno.ironman-zwift-sync"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
chmod +x "$HERE/sync.sh"
mkdir -p "$HOME/Library/LaunchAgents"
cat > "$PLIST" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key><array><string>/bin/bash</string><string>$HERE/sync.sh</string></array>
  <key>StartInterval</key><integer>1800</integer>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>$HERE/launchd.log</string>
  <key>StandardErrorPath</key><string>$HERE/launchd.log</string>
</dict></plist>
PL
launchctl bootout "gui/$(id -u)" "$PLIST" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
echo "Installed. Checking the first run..."
sleep 8
if grep -q "Operation not permitted" "$HERE/launchd.log" 2>/dev/null; then
  echo
  echo "macOS blocked the background job from reaching your Documents folder."
  echo "Fix: System Settings → Privacy & Security → Full Disk Access → + → press Cmd+Shift+G,"
  echo "type /bin/bash, add it and switch it on. Then run this install command again."
  exit 1
fi
bash "$HERE/sync.sh"
echo "Done. Recent activity:"; tail -n 5 "$HERE/sync.log" 2>/dev/null || echo "(up to date, nothing new)"
echo "Restart Zwift to see new workouts under Custom Workouts."
