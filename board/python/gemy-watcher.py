#!/usr/bin/env python3
"""Watch the Coralboard USER button and start/stop Gemy (greeter.py).

The board labels this the Enter Button (gpio-keys, usually /dev/input/event0).
Short press: toggle Gemy on/off. A short Gemy signature beep plays when starting.

Run on the board (often via systemd gemy-watcher.service):
  python3 /home/root/gemy-watcher.py

No PC or internet needed once greeter.py, hat.py, and speech models are on the board.
"""
import os
import struct
import subprocess
import sys
import time

sys.path.insert(0, "/home/root")
import hat

EVENT_SIZE = 24
EVENT_FMT = "qqHHi"
EV_KEY = 1
KEY_ENTER = 28

PY = "/home/root/sl2610-examples/.venv/bin/python3"
GREETER = "/home/root/greeter.py"
LOG = "/home/root/gemy.log"
INPUT_DEV = "/dev/input/event0"


def greeter_running():
    try:
        out = subprocess.check_output(["ps", "-ef"], text=True, errors="replace")
        return "/home/root/greeter.py" in out
    except Exception:
        return False


def stop_greeter():
    subprocess.run(
        ["pkill", "-9", "-f", "/home/root/greeter.py"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    subprocess.run(
        ["pkill", "-9", "-f", "wave_detect.py"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(0.5)
    hat.buzzer_off()
    hat.led_off_all()


def start_greeter():
    stop_greeter()
    with open(LOG, "ab", buffering=0) as log:
        log.write(f"\n--- start {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n".encode())
    subprocess.Popen(
        [PY, "-u", GREETER],
        stdout=open(LOG, "ab"),
        stderr=subprocess.STDOUT,
        start_new_session=True,
        cwd="/home/root",
    )
    time.sleep(0.3)
    try:
        import greeter
        greeter.REACTIONS["gemy"]()
    except Exception:
        hat.beep(2)
        hat.led("green", True)
        time.sleep(0.2)
        hat.led("green", False)
    finally:
        hat.buzzer_off()
        hat.led_off_all()
    print("[gemy-watcher] Gemy started.", flush=True)


def toggle_gemy():
    if greeter_running():
        print("[gemy-watcher] Stopping Gemy...", flush=True)
        stop_greeter()
        print("[gemy-watcher] Gemy stopped.", flush=True)
    else:
        print("[gemy-watcher] Starting Gemy...", flush=True)
        start_greeter()


def find_input_device():
    if os.path.exists(INPUT_DEV):
        return INPUT_DEV
    by_name = "/sys/class/input/event0/device/name"
    if os.path.exists(by_name):
        with open(by_name) as f:
            if "key" in f.read().lower():
                return INPUT_DEV
    return INPUT_DEV


def main():
    dev = find_input_device()
    if not os.path.exists(dev):
        print(f"[gemy-watcher] ERROR: {dev} not found. Is this a Coralboard?")
        return 1
    if not os.path.exists(GREETER):
        print(f"[gemy-watcher] ERROR: {GREETER} missing. Push greeter.py to /home/root/.")
        return 1

    print(f"[gemy-watcher] Ready. Press USER button on board to start/stop Gemy.", flush=True)
    print(f"[gemy-watcher] Log: {LOG}", flush=True)

    with open(dev, "rb") as f:
        while True:
            data = f.read(EVENT_SIZE)
            if len(data) < EVENT_SIZE:
                time.sleep(0.05)
                continue
            _sec, _usec, ev_type, code, value = struct.unpack(EVENT_FMT, data)
            if ev_type == EV_KEY and code == KEY_ENTER and value == 1:
                toggle_gemy()
                time.sleep(0.4)


if __name__ == "__main__":
    try:
        sys.exit(main() or 0)
    except KeyboardInterrupt:
        stop_greeter()
        sys.exit(0)
