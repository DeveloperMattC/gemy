#!/usr/bin/env python3
"""
Simple Coralboard Sensor-HAT control: buzzer, LEDs, camera.

Run from the board (any python3 works for buzzer/LED; camera needs OpenCV):

  # Buzzer (active buzzer = fixed pitch; patterns vary the rhythm)
  python3 hat.py beep                 # single short beep
  python3 hat.py beep 3               # three beeps
  python3 hat.py buzz 800             # one 800 ms tone
  python3 hat.py siren                # warbling siren
  python3 hat.py r2d2                 # R2D2-style chatter
  python3 hat.py warble               # fast two-length warble
  python3 hat.py chirp                # quick chirps
  python3 hat.py alarm                # slow insistent alarm
  python3 hat.py sos                  # morse SOS
  python3 hat.py buzzer on            # turn on (~2s, max 5s) then off
  python3 hat.py buzzer off           # force off

  # LEDs (red / green / blue / all)
  python3 hat.py led red on
  python3 hat.py led green off
  python3 hat.py led all off
  python3 hat.py blink blue 5
  python3 hat.py rainbow              # cycle red->green->blue

  # Camera
  python3 hat.py photo                # saves /home/root/hat_photo.jpg
  python3 hat.py photo /home/root/me.jpg --width 1280 --height 720

You can also import it:
  >>> import hat
  >>> hat.beep(2)
  >>> hat.led("green", True)
  >>> hat.photo("/home/root/pic.jpg")
"""
import argparse
import subprocess
import sys
import time

# ---- Buzzer -----------------------------------------------------------------
# HAT buzzer = GPIO line "BUZZERn" (gpiochip0 line 6). It's an ACTIVE buzzer:
# driving the line LOW (=0) turns the tone ON, HIGH (=1) turns it OFF.
#
# IMPORTANT: this board LATCHES the GPIO output at the last value gpioset wrote
# (libgpiod v1, "exit" mode). So a naive timed pulse leaves the line stuck ON.
# We instead drive ON, sleep in Python, then ALWAYS drive OFF. Every routine
# ends with the line HIGH (off). There is no PWM on the buzzer, so we can't
# change pitch -- patterns vary rhythm (beep/gap lengths) instead.
_BUZZER_NAME = "BUZZERn"
_buzzer_chip = "gpiochip0"
_buzzer_line = "6"
_buzzer_found = False


def _find_buzzer():
    global _buzzer_chip, _buzzer_line, _buzzer_found
    if not _buzzer_found:
        try:
            out = subprocess.check_output(["gpiofind", _BUZZER_NAME], text=True).split()
            if len(out) == 2:
                _buzzer_chip, _buzzer_line = out[0], out[1]
        except Exception:
            pass  # fall back to the known default (gpiochip0 line 6)
        _buzzer_found = True
    return _buzzer_chip, _buzzer_line


def _buzzer_set(on):
    """Latch the buzzer ON (drive line LOW) or OFF (drive line HIGH)."""
    chip, line = _find_buzzer()
    val = 0 if on else 1
    subprocess.run(["gpioset", chip, f"{line}={val}"], check=False,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def buzzer_off():
    """Force the buzzer OFF (line high)."""
    _buzzer_set(False)


def buzzer_on(hold_sec=2):
    """Turn the buzzer on for a short hold (max 5s, blocks), then off."""
    hold_sec = max(0.0, min(float(hold_sec), 5.0))
    try:
        _buzzer_set(True)
        time.sleep(hold_sec)
    finally:
        _buzzer_set(False)


def buzzer_pulse(ms):
    """One tone of `ms` milliseconds, then guaranteed OFF."""
    try:
        _buzzer_set(True)
        time.sleep(max(0, int(ms)) / 1000.0)
    finally:
        _buzzer_set(False)


def _play(pattern):
    """Play [(on_ms, gap_ms), ...]; always ends with the buzzer OFF."""
    try:
        for on_ms, gap_ms in pattern:
            if on_ms > 0:
                _buzzer_set(True)
                time.sleep(on_ms / 1000.0)
                _buzzer_set(False)
            if gap_ms > 0:
                time.sleep(gap_ms / 1000.0)
    finally:
        _buzzer_set(False)


def beep(count=1, on_ms=120, off_ms=100):
    """One or more short beeps."""
    _play([(int(on_ms), int(off_ms))] * int(count))


def siren(cycles=4):
    """Warbling two-length siren."""
    pat = []
    for _ in range(int(cycles)):
        pat += [(90, 30), (170, 60)]
    _play(pat)


# ---- Fun robotic buzzer patterns -------------------------------------------
def r2d2(rounds=14):
    """R2D2-style excited chatter: random short beeps and gaps."""
    import random
    pat = [(random.choice([25, 35, 45, 60, 80]),
            random.choice([20, 30, 40, 55])) for _ in range(int(rounds))]
    _play(pat)


def chirp(times=6):
    """Quick rising-energy chirps (fast, short)."""
    _play([(30, 35)] * int(times))


def warble(cycles=10):
    """Two-length warble, faster than the siren."""
    pat = []
    for _ in range(int(cycles)):
        pat += [(40, 25), (75, 25)]
    _play(pat)


def alarm(cycles=5):
    """Slow, insistent alarm beeps."""
    _play([(260, 130)] * int(cycles))


def sos():
    """Morse SOS: ... --- ..."""
    dot, dash, gap, lgap = 120, 320, 110, 260
    pat = [(dot, gap)] * 3 + [(dash, gap)] * 3 + [(dot, gap)] * 3
    pat[2] = (dot, lgap)
    pat[5] = (dash, lgap)
    _play(pat)


# ---- LEDs -------------------------------------------------------------------
# Controllable status LEDs on the board.
_LED_PATH = "/sys/class/leds/{color}:status"
_COLORS = ("red", "green", "blue")


def _write(path, value):
    try:
        with open(path, "w") as f:
            f.write(str(value))
        return True
    except OSError as e:
        print(f"  (could not write {path}: {e})")
        return False


def led(color, on):
    """Turn an LED on/off. color = red|green|blue|all, on = True/False."""
    color = color.lower()
    targets = _COLORS if color == "all" else (color,)
    for c in targets:
        if c not in _COLORS:
            print(f"Unknown color '{c}'. Use: red, green, blue, all.")
            continue
        base = _LED_PATH.format(color=c)
        _write(f"{base}/trigger", "none")          # detach any blink trigger
        _write(f"{base}/brightness", 1 if on else 0)  # max_brightness is 1


def led_off_all():
    led("all", False)


def blink(color, times=5, on_ms=250, off_ms=250):
    for _ in range(int(times)):
        led(color, True)
        time.sleep(on_ms / 1000.0)
        led(color, False)
        time.sleep(off_ms / 1000.0)


def rainbow(cycles=3, dwell_ms=300):
    for _ in range(int(cycles)):
        for c in _COLORS:
            led_off_all()
            led(c, True)
            time.sleep(dwell_ms / 1000.0)
    led_off_all()


# ---- Camera -----------------------------------------------------------------
# Sensor control node (OV5647 on the HAT). Exposure/gain live here, NOT on
# /dev/video0, and they only "stick" once the stream is already running.
_CAM_CTRL_DEV = "/dev/v4l-subdev2"


def _set_cam_ctrl(name, val, dev=_CAM_CTRL_DEV):
    subprocess.run(["v4l2-ctl", "-d", dev, "-c", f"{name}={val}"],
                   check=False, capture_output=True)


def photo(path="/home/root/hat_photo.jpg", width=1280, height=720, device=0,
          exposure=740, gain=1023, settle_frames=130):
    """Capture a frame from the HAT camera (OV5647) and save it as a JPEG.

    The sensor boots in manual mode with low gain (dark/black frames). We start
    the stream, then set manual exposure + high gain mid-stream (the only point
    at which the controls take effect), let it settle, and save the brightest
    frame. Lower `gain` (e.g. 400) if a well-lit scene looks washed out/noisy.
    """
    import cv2
    import numpy as np

    cap = cv2.VideoCapture(device, cv2.CAP_V4L2)
    if not cap.isOpened():
        print(f"ERROR: could not open camera /dev/video{device}")
        return False
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    # Start streaming before applying sensor controls.
    for _ in range(15):
        cap.read()
        time.sleep(0.02)

    _set_cam_ctrl("auto_exposure", 1)            # 1 = Manual Mode
    _set_cam_ctrl("gain_automatic", 0)
    _set_cam_ctrl("white_balance_automatic", 1)
    _set_cam_ctrl("exposure", int(exposure))
    _set_cam_ctrl("analogue_gain", int(gain))

    best, best_mean = None, -1.0
    for _ in range(max(30, settle_frames)):
        ok, f = cap.read()
        if ok and f is not None:
            m = float(np.mean(f))
            if m > best_mean:
                best_mean, best = m, f
        time.sleep(0.01)
    cap.release()

    if best is None:
        print("ERROR: failed to capture a frame")
        return False
    cv2.imwrite(path, best)
    h, w = best.shape[:2]
    note = "  (dark - add light or raise gain)" if best_mean < 12 else ""
    print(f"Saved {w}x{h} photo to {path} (brightness={best_mean:.1f}){note}")
    return True


# ---- CLI --------------------------------------------------------------------
def _bool_state(s):
    return str(s).lower() in ("on", "1", "true", "yes")


def main(argv=None):
    p = argparse.ArgumentParser(
        description="Coralboard sensor-HAT control (buzzer / LED / camera)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("beep", help="short beep(s)")
    s.add_argument("count", nargs="?", default=1, type=int)

    s = sub.add_parser("buzz", help="single tone of N milliseconds")
    s.add_argument("ms", nargs="?", default=400, type=int)

    sub.add_parser("siren", help="warbling siren")
    sub.add_parser("r2d2", help="R2D2-style chatter")
    sub.add_parser("warble", help="fast two-length warble")
    sub.add_parser("chirp", help="quick chirps")
    sub.add_parser("alarm", help="slow insistent alarm")
    sub.add_parser("sos", help="morse SOS")

    s = sub.add_parser("buzzer", help="buzzer on/off")
    s.add_argument("state")

    s = sub.add_parser("led", help="led <red|green|blue|all> <on|off>")
    s.add_argument("color")
    s.add_argument("state")

    s = sub.add_parser("blink", help="blink an led N times")
    s.add_argument("color")
    s.add_argument("times", nargs="?", default=5, type=int)

    sub.add_parser("rainbow", help="cycle red/green/blue")

    s = sub.add_parser("photo", help="capture a photo from the camera")
    s.add_argument("path", nargs="?", default="/home/root/hat_photo.jpg")
    s.add_argument("--width", type=int, default=1280)
    s.add_argument("--height", type=int, default=720)
    s.add_argument("--device", type=int, default=0)
    s.add_argument("--exposure", type=int, default=740, help="4-740")
    s.add_argument("--gain", type=int, default=1023, help="16-1023 (lower if too bright)")

    args = p.parse_args(argv)

    if args.cmd == "beep":
        beep(args.count)
    elif args.cmd == "buzz":
        buzzer_pulse(args.ms)
    elif args.cmd == "siren":
        siren()
    elif args.cmd == "r2d2":
        r2d2()
    elif args.cmd == "warble":
        warble()
    elif args.cmd == "chirp":
        chirp()
    elif args.cmd == "alarm":
        alarm()
    elif args.cmd == "sos":
        sos()
    elif args.cmd == "buzzer":
        if _bool_state(args.state):
            buzzer_on()
        else:
            buzzer_off()
    elif args.cmd == "led":
        led(args.color, _bool_state(args.state))
    elif args.cmd == "blink":
        blink(args.color, args.times)
    elif args.cmd == "rainbow":
        rainbow()
    elif args.cmd == "photo":
        photo(args.path, args.width, args.height, args.device,
              exposure=args.exposure, gain=args.gain)


if __name__ == "__main__":
    main()
