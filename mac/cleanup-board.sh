#!/usr/bin/env bash
# Stop leftover demos on the Coralboard; free camera / buzzer / LEDs.
# Does not push any files.
#
#   ./mac/cleanup-board.sh
set -euo pipefail

if ! command -v adb >/dev/null 2>&1; then
  echo "ERROR: adb not found." >&2
  exit 1
fi

echo "Waiting for board..."
adb wait-for-device >/dev/null 2>&1 || true

echo "Stopping boot autostart service and old demos..."
adb shell "systemctl stop gemy-autostart.service 2>/dev/null; pkill -9 -f gemy-boot.sh 2>/dev/null; true" >/dev/null 2>&1 || true

adb shell "pkill -9 -f wave_detect.py 2>/dev/null; pkill -9 -f /home/root/greeter.py 2>/dev/null; pkill -9 -f gemma_mood_worker.py 2>/dev/null; pkill -9 -f gemma_mood.py 2>/dev/null; pkill -9 -f gemy-boot.sh 2>/dev/null; pkill -9 -f webrtc-stream.sh 2>/dev/null; true" >/dev/null 2>&1 || true
sleep 1

echo "Force buzzer OFF (GPIO)..."
adb shell "for i in 1 2 3 4 5; do gpioset gpiochip0 6=1 2>/dev/null; sleep 0.15; done; true" >/dev/null 2>&1 || true
sleep 1

FUSER_OUT="$(adb shell "fuser /dev/video0 2>/dev/null" 2>/dev/null | tr -d '\r' || true)"
if [[ -n "${FUSER_OUT// /}" ]]; then
  echo "Releasing camera (was held by PID $FUSER_OUT)..."
  for procId in $FUSER_OUT; do
    if [[ "$procId" =~ ^[0-9]+$ ]]; then
      adb shell "kill -9 $procId 2>/dev/null" >/dev/null 2>&1 || true
    fi
  done
  sleep 1
fi

echo "Buzzer off, LEDs off..."
adb shell "gpioset gpiochip0 6=1 2>/dev/null; python3 /home/root/hat.py force-off 2>/dev/null; true" >/dev/null 2>&1 || true

CAM="$(adb shell "fuser /dev/video0 2>/dev/null || echo free" 2>/dev/null | tr -d '\r' | tr -d '\n' || true)"
PROCS="$(adb shell "ps -ef 2>/dev/null | grep -E 'wave_detect|greeter.py|gemma_mood' | grep -v grep || true" 2>/dev/null | tr -d '\r' || true)"

if { [[ -z "$CAM" ]] || [[ "$CAM" == "free" ]]; } && [[ -z "${PROCS// /}" ]]; then
  echo "Board clean - camera free, no greeter/wave demos running."
  exit 0
fi

echo "Cleanup done (check below if something still looks wrong):"
[[ -n "${PROCS// /}" ]] && echo "  Still running: $PROCS"
[[ -n "$CAM" && "$CAM" != "free" ]] && echo "  Camera still held: $CAM"
exit 1
