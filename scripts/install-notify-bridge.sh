#!/bin/bash
# Installs the booking-alert texter as a launchd agent that runs every minute.
# Usage: ./scripts/install-notify-bridge.sh <notify_token>   (token only needed the first time)
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
APP_DIR="$HOME/Library/Application Support/BrassyMonkeyNotify"
PLIST="$HOME/Library/LaunchAgents/com.brassymonkey.notify.plist"
LABEL="com.brassymonkey.notify"

mkdir -p "$APP_DIR"
cp "$HERE/notify_bridge.py" "$APP_DIR/notify_bridge.py"

if [ "${1:-}" != "" ]; then
  umask 077
  printf 'NOTIFY_TOKEN=%s\nDRY_RUN=0\n' "$1" > "$APP_DIR/config.env"
fi
if [ ! -f "$APP_DIR/config.env" ]; then
  echo "No config.env yet. Run again with the notify token." >&2
  exit 1
fi

cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/python3</string>
    <string>$APP_DIR/notify_bridge.py</string>
  </array>
  <key>StartInterval</key><integer>60</integer>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>$APP_DIR/bridge.log</string>
  <key>StandardErrorPath</key><string>$APP_DIR/bridge.log</string>
</dict>
</plist>
EOF

launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
echo "Installed $LABEL. Log: $APP_DIR/bridge.log"
