#!/bin/sh
# Start Gemy after board power-on (used by gemy-autostart.service).
# Waits for Linux + venv python, cleans stale demos, runs greeter.

PY=/home/root/sl2610-examples/.venv/bin/python3
LOG=/home/root/gemy.log

# Let USB/audio/camera subsystems come up after power-on.
sleep 20

# Wait up to 2 min for the examples venv (first boot after flash may be slower).
n=0
while [ ! -x "$PY" ] && [ "$n" -lt 60 ]; do
    sleep 2
    n=$((n + 1))
done
if [ ! -x "$PY" ]; then
    echo "--- boot $(date) ERROR: $PY not found ---" >> "$LOG"
    exit 1
fi

pkill -9 -f wave_detect.py 2>/dev/null
pkill -9 -f /home/root/greeter.py 2>/dev/null
for _ in 1 2 3; do
    gpioset gpiochip0 6=1 2>/dev/null
done
python3 /home/root/hat.py force-off 2>/dev/null

echo "--- boot $(date) ---" >> "$LOG"
cd /home/root
# Voice-only at boot (no camera). Gemma loads in a worker process (see gemma_mood_worker.py).
exec "$PY" -u /home/root/greeter.py --cooldown 3 --no-vision --no-intro --no-gemma-mood >> "$LOG" 2>&1