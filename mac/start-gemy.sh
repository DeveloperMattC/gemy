#!/usr/bin/env bash
# Start greeter.py that is ALREADY on the Coralboard via adb.
# Default: never adb push (protects an advanced board copy).
#
#   ./mac/start-gemy.sh
#   ./mac/start-gemy.sh --no-vision
#   ./mac/start-gemy.sh --no-gemma-mood
#   ./mac/start-gemy.sh --allow-push   # opt-in: sync board/python from this repo first
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
NO_VISION=0
NO_SPEECH=0
NO_GEMMA=0
ALLOW_PUSH=0
SKIP_CLEANUP=0
SENSITIVITY=medium

usage() {
  sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'
  exit 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-vision) NO_VISION=1 ;;
    --no-speech) NO_SPEECH=1 ;;
    --no-gemma-mood) NO_GEMMA=1 ;;
    --allow-push|--push) ALLOW_PUSH=1 ;;
    --no-push) ALLOW_PUSH=0 ;;
    --skip-cleanup) SKIP_CLEANUP=1 ;;
    --sensitivity) SENSITIVITY="${2:-medium}"; shift ;;
    -h|--help) usage ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
  shift
done

if ! command -v adb >/dev/null 2>&1; then
  echo "ERROR: adb not found. Install: brew install android-platform-tools" >&2
  exit 1
fi

if ! adb devices 2>/dev/null | grep -q $'\tdevice'; then
  echo "ERROR: No Coralboard on ADB. Plug USB-C (data cable), wait ~20s." >&2
  exit 1
fi

echo ""
echo "  Gemy (Mac) — using board-resident greeter"
if [[ "$ALLOW_PUSH" -eq 1 ]]; then
  echo "  WARNING: will push this repo's board/python onto the board"
else
  echo "  (no push — advanced board code is left alone)"
fi
echo ""

adb wait-for-device >/dev/null

if [[ "$ALLOW_PUSH" -eq 1 ]]; then
  echo "==> Pushing repo scripts to /home/root/ ..."
  for f in greeter.py hat.py gemma_mood.py gemma_mood_worker.py \
           gemy_diag.py gemy_trace.py gemy_stability.py gemy_empathy.py \
           gemy_fallback.py gemy_classify.py gemy_math.py gemy_qa.py \
           gemy_phrase_buffer.py gemy_heartbeat_smoke.py gemy_reactions.py; do
    local="$ROOT/board/python/$f"
    if [[ -f "$local" ]]; then
      adb push "$local" "/home/root/$f" >/dev/null
      echo "  OK  $f"
    fi
  done
fi

if ! adb shell "test -f /home/root/greeter.py && echo yes" | grep -q yes; then
  echo "ERROR: /home/root/greeter.py missing on board." >&2
  echo "  This script will not invent it. Use --allow-push only if you intend to overwrite." >&2
  exit 1
fi

if [[ "$SKIP_CLEANUP" -eq 0 ]]; then
  echo "==> Cleaning board (stop old demos, buzzer off)..."
  bash "$ROOT/mac/cleanup-board.sh" || true
fi

PY="/home/root/sl2610-examples/.venv/bin/python3"
OPTS="--sensitivity $SENSITIVITY --cooldown 3 --pc-start"
[[ "$NO_SPEECH" -eq 1 ]] && OPTS+=" --no-speech"
[[ "$NO_VISION" -eq 1 ]] && OPTS+=" --no-vision"
# Match Windows greet-demo default: local moods only (stable).
OPTS+=" --no-gemma-mood"

CMD="$PY -u /home/root/greeter.py $OPTS"

echo "==> Starting Gemy on the board..."
echo "  Wait for [ears] listening. Say Gemy turn off to stop."
echo "  Log: adb shell tail -80 /home/root/gemy.log"
echo ""

# Interactive tty so Moonshine/greeter behave like Windows greet-demo.
exec adb shell -t "$CMD 2>&1 | tee -a /home/root/gemy.log"
