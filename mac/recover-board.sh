#!/usr/bin/env bash
# Emergency recover: kill Gemma worker / greeter, buzzer off. No push.
#
#   ./mac/recover-board.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if ! command -v adb >/dev/null 2>&1; then
  echo "ERROR: adb not found." >&2
  exit 1
fi

if ! adb devices 2>/dev/null | grep -q $'\tdevice'; then
  echo "Board not on ADB. Unplug USB-C 15–20s, replug, wait for boot, then retry." >&2
  exit 1
fi

echo "==> Recover: stop Gemy processes + Gemma worker..."
adb shell "pkill -9 -f greeter.py 2>/dev/null; pkill -9 -f gemma_mood_worker.py 2>/dev/null; pkill -9 -f gemma_mood.py 2>/dev/null; pkill -9 -f gemy-boot.sh 2>/dev/null; true" >/dev/null 2>&1 || true
bash "$ROOT/mac/cleanup-board.sh" || true
echo "Done. Restart with: ./mac/start-gemy.sh --no-gemma-mood"
echo "  Log: adb shell tail -80 /home/root/gemy.log"
