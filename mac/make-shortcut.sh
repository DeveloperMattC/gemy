#!/usr/bin/env bash
# Create a Desktop shortcut that opens Gemy Control Center (Mac hub).
#   ./mac/make-shortcut.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HUB="$ROOT/mac/start-hub.sh"
DESKTOP="${HOME}/Desktop"
CMD_PATH="$DESKTOP/Gemy Control Center.command"
APP_PATH="$DESKTOP/Gemy Control Center.app"

if [[ ! -x "$HUB" && ! -f "$HUB" ]]; then
  echo "ERROR: Missing hub launcher: $HUB" >&2
  exit 1
fi
chmod +x "$HUB" "$ROOT/mac/"*.sh 2>/dev/null || true

# Double-clickable .command (opens Terminal, starts hub, opens browser).
cat > "$CMD_PATH" <<EOF
#!/bin/bash
cd $(printf '%q' "$ROOT") || exit 1
exec ./mac/start-hub.sh
EOF
chmod +x "$CMD_PATH"

# Optional: real .app so it looks like a normal Mac app (no .command extension).
# Uses Terminal so you can see hub logs / Ctrl+C to stop.
TMP_SCRIPT="$(mktemp)"
cat > "$TMP_SCRIPT" <<EOF
tell application "Terminal"
  activate
  do script "cd $(printf '%q' "$ROOT") && ./mac/start-hub.sh"
end tell
EOF
rm -rf "$APP_PATH"
osacompile -o "$APP_PATH" "$TMP_SCRIPT" >/dev/null
rm -f "$TMP_SCRIPT"

echo ""
echo "Desktop shortcuts created:"
echo "  $APP_PATH"
echo "  $CMD_PATH"
echo ""
echo "Double-click either one. Keep the Terminal window open while using the UI."
echo "First open: if macOS blocks it, right-click → Open → Open."
