#!/bin/bash
# Removes the background job (keeps your workout files).
PLIST="$HOME/Library/LaunchAgents/com.amizuno.ironman-zwift-sync.plist"
launchctl bootout "gui/$(id -u)" "$PLIST" 2>/dev/null || true
rm -f "$PLIST"
echo "Zwift auto-sync removed."
