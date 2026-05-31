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
  python3 hat.py buzzer on            # turn on (max 2s) then off
  python3 hat.py force-off            # emergency: buzzer + all LEDs off
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
import threading
import time

# ---- INVIOLABLE SAFETY (Gemy + all hat.py users) ----------------------------
# Buzzer or any LED must NEVER stay ON longer than this (seconds). GPIO can latch.
MAX_OUTPUT_ON_SEC = 2.0
_LED_PATH = "/sys/class/leds/{color}:status"
_COLORS = ("red", "green", "blue")

_buzzer_on_at = None
_led_on_at = {}  # color -> monotonic time LED was turned on
_safety_lock = threading.Lock()
_hw_lock = threading.RLock()  # one GPIO user at a time (vision + speech threads)
_watchdog_started = False


def _gpio_buzzer_off_hard():
    """Drive buzzer line HIGH several times (latched GPIO)."""
    chip, line = _find_buzzer()
    for _ in range(4):
        subprocess.run(
            ["gpioset", chip, f"{line}=1"],
            check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )


def _cap_sec(sec):
    return min(float(sec), MAX_OUTPUT_ON_SEC)


def _cap_ms(ms):
    return min(int(ms), int(MAX_OUTPUT_ON_SEC * 1000))


def start_safety_watchdog():
    """Background thread: force buzzer/LEDs off if stuck on > MAX_OUTPUT_ON_SEC."""
    global _watchdog_started
    if _watchdog_started:
        return
    _watchdog_started = True

    def _loop():
        while True:
            time.sleep(0.15)
            safety_enforce()

    threading.Thread(target=_loop, name="hat-safety", daemon=True).start()


def safety_enforce():
    """Force outputs off when over the time limit (or always safe to call)."""
    global _buzzer_on_at
    now = time.monotonic()
    buzzer_stuck = False
    with _safety_lock:
        if _buzzer_on_at is not None and (now - _buzzer_on_at) >= MAX_OUTPUT_ON_SEC:
            buzzer_stuck = True
        led_stuck = [c for c, t0 in list(_led_on_at.items())
                     if (now - t0) >= MAX_OUTPUT_ON_SEC]
    if buzzer_stuck:
        with _hw_lock:
            _gpio_buzzer_off_hard()
            with _safety_lock:
                _buzzer_on_at = None
    for c in led_stuck:
        _led_set_tracked(c, False)


def force_all_off():
    """Emergency: buzzer off + all LEDs off (clears safety timers)."""
    global _buzzer_on_at
    with _hw_lock:
        _gpio_buzzer_off_hard()
        with _safety_lock:
            _buzzer_on_at = None
            _led_on_at.clear()
        for c in _COLORS:
            base = _LED_PATH.format(color=c)
            _write(f"{base}/trigger", "none")
            _write(f"{base}/brightness", 0)


def hold_led(color, sec, off_gap=0.0):
    """Turn LED on up to MAX_OUTPUT_ON_SEC, then off (never leaves it latched on)."""
    sec = _cap_sec(sec)
    with _hw_lock:
        led(color, True)
        time.sleep(sec)
        led(color, False)
    if off_gap > 0:
        time.sleep(off_gap)


def pulse_leds(colors, sec, off_gap=0.0):
    """Turn one or more colors on briefly, then all off."""
    sec = _cap_sec(sec)
    if isinstance(colors, str):
        colors = (colors,)
    led_off_all()
    for c in colors:
        led(c, True)
    time.sleep(sec)
    led_off_all()
    if off_gap > 0:
        time.sleep(off_gap)


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
    global _buzzer_on_at
    chip, line = _find_buzzer()
    val = 0 if on else 1
    subprocess.run(["gpioset", chip, f"{line}={val}"], check=False,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    with _safety_lock:
        _buzzer_on_at = time.monotonic() if on else None


def buzzer_off():
    """Force the buzzer OFF (line high)."""
    _buzzer_set(False)


def buzzer_on(hold_sec=2):
    """Turn the buzzer on briefly (max MAX_OUTPUT_ON_SEC), then off."""
    hold_sec = _cap_sec(hold_sec)
    try:
        _buzzer_set(True)
        time.sleep(hold_sec)
    finally:
        _buzzer_set(False)


def buzzer_pulse(ms):
    """One tone of `ms` milliseconds (capped), then guaranteed OFF."""
    ms = _cap_ms(ms)
    try:
        _buzzer_set(True)
        time.sleep(ms / 1000.0)
    finally:
        _buzzer_set(False)


def _play(pattern):
    """Play [(on_ms, gap_ms), ...]; each ON segment capped; always ends OFF."""
    with _hw_lock:
        try:
            for on_ms, gap_ms in pattern:
                on_ms = _cap_ms(on_ms)
                if on_ms > 0:
                    _buzzer_set(True)
                    time.sleep(on_ms / 1000.0)
                    _buzzer_set(False)
                if gap_ms > 0:
                    time.sleep(gap_ms / 1000.0)
        finally:
            _gpio_buzzer_off_hard()
            with _safety_lock:
                _buzzer_on_at = None


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


def _run_parallel(buzzer_fn, led_fn):
    threads = [
        threading.Thread(target=buzzer_fn, daemon=True),
        threading.Thread(target=led_fn, daemon=True),
    ]
    try:
        for t in threads:
            t.start()
        for t in threads:
            t.join()
    finally:
        force_all_off()


def gemy_intro():
    """Startup hello (beeps + lights). Each tone <= MAX_OUTPUT_ON_SEC."""
    with _hw_lock:
        try:
            _play([
                (55, 42), (55, 42), (92, 52),
                (48, 36), (48, 36), (66, 46),
                (60, 28), (102, 36), (56, 30), (120, 0),
            ])
            for _ in range(2):
                hold_led("green", 0.11, 0.07)
            hold_led("blue", 0.12, 0.06)
            pulse_leds(("green", "blue"), 0.22)
        finally:
            force_all_off()


def gemy_intro_short():
    """Quick hello when starting from PC (avoids long beep storm with autostart)."""
    with _hw_lock:
        try:
            _play([(55, 38), (55, 38), (95, 0)])
            pulse_leds(("green", "blue"), 0.18)
        finally:
            force_all_off()


def gemy_goodbye():
    """Shutdown: soft descending beeps + blue fade (bye Gemy)."""
    def leds():
        for ms in (0.20, 0.16, 0.12):
            hold_led("blue", ms, 0.06)

    def beeps():
        _play([(120, 70), (95, 80), (70, 90), (50, 0)])

    _run_parallel(beeps, leds)
    force_all_off()


def gemy_yes():
    """Affirmative: one green light beep."""
    with _hw_lock:
        try:
            led("green", True)
            try:
                _buzzer_set(True)
                time.sleep(_cap_sec(0.16))
            finally:
                _buzzer_set(False)
            led("green", False)
        finally:
            _hw_release_under_lock()


def _leds_off_under_lock():
    for c in _COLORS:
        led(c, False)


def _rainbow_under_lock(cycles=2, dwell_ms=130):
    """RGB sweep; caller must hold _hw_lock."""
    dwell_s = _cap_sec(dwell_ms / 1000.0)
    for _ in range(max(1, int(cycles))):
        for c in _COLORS:
            _leds_off_under_lock()
            led(c, True)
            time.sleep(dwell_s)
            led(c, False)


def _hw_release_under_lock():
    _gpio_buzzer_off_hard()
    with _safety_lock:
        _buzzer_on_at = None
    for c in _COLORS:
        base = _LED_PATH.format(color=c)
        _write(f"{base}/trigger", "none")
        _write(f"{base}/brightness", 0)


def gemy_funny():
    """Joke / laugh: ha-ha-ha bursts + rapid green flashes (giggle, not R2D2)."""
    with _hw_lock:
        try:
            # Three clear "Ha!" then faster giggles (active buzzer = rhythm only).
            laugh = [
                (90, 55), (85, 50), (95, 45),
                (55, 32), (50, 28), (55, 26), (48, 24),
                (42, 22), (45, 20), (40, 18), (48, 16),
                (38, 14), (42, 12), (36, 11), (50, 10),
                (34, 9), (40, 8), (32, 7), (55, 6),
                (30, 5), (45, 0),
            ]
            for on_ms, gap_ms in laugh:
                on_ms = _cap_ms(on_ms)
                gap_ms = min(int(gap_ms), 90)
                led("green", True)
                if on_ms > 0:
                    try:
                        _buzzer_set(True)
                        time.sleep(on_ms / 1000.0)
                    finally:
                        _buzzer_set(False)
                led("green", False)
                if gap_ms > 0:
                    time.sleep(gap_ms / 1000.0)
            # Joy flash: green + blue together (brief "can't stop laughing").
            led("green", True)
            led("blue", True)
            try:
                _buzzer_set(True)
                time.sleep(_cap_sec(0.14))
            finally:
                _buzzer_set(False)
            _leds_off_under_lock()
        finally:
            _hw_release_under_lock()


def gemy_greet():
    """Hello: rainbow sweep + friendly double beep."""
    with _hw_lock:
        try:
            _rainbow_under_lock(cycles=1, dwell_ms=130)
            _play([(95, 55), (110, 0)])
        finally:
            _hw_release_under_lock()


def gemy_nice():
    """Happy woohoo: green LED + rising cheer beeps (woo-woo-hoo!, one lock)."""
    with _hw_lock:
        try:

            def _cheer(on_ms: int, pause_s: float) -> None:
                """One cheer pulse: green on + beep (length = pitch feel on active buzzer)."""
                on_ms = _cap_ms(on_ms)
                _led_set_tracked("green", True)
                try:
                    _buzzer_set(True)
                    time.sleep(on_ms / 1000.0)
                finally:
                    _buzzer_set(False)
                _led_set_tracked("green", False)
                if pause_s > 0:
                    time.sleep(pause_s)

            # "Woo-hoo!" — short woo-woo, then longer rising hoo notes
            for on_ms, pause in (
                (55, 0.09),
                (60, 0.09),
                (85, 0.10),
                (110, 0.12),
                (145, 0.14),
                (185, 0.16),
                (220, 0.0),
            ):
                _cheer(on_ms, pause)
        finally:
            _hw_release_under_lock()


def gemy_neutral():
    """Unclassified: soft beep + gentle rainbow."""
    with _hw_lock:
        try:
            _play([(70, 0)])
            _rainbow_under_lock(cycles=1, dwell_ms=160)
        finally:
            _hw_release_under_lock()


def gemy_no():
    """Negative: two red light beeps."""
    with _hw_lock:
        try:
            for pause_s in (0.12, 0.0):
                led("red", True)
                try:
                    _buzzer_set(True)
                    time.sleep(_cap_sec(0.16))
                finally:
                    _buzzer_set(False)
                led("red", False)
                if pause_s > 0:
                    time.sleep(pause_s)
        finally:
            _hw_release_under_lock()


def gemy_sad():
    """Empathetic 'bohooo' cry: blue LED only, descending whimper beeps (one lock)."""
    with _hw_lock:
        try:
            _leds_off_under_lock()

            def _sob(on_ms: int, pause_s: float) -> None:
                """One cry: blue on + buzz, then off (active buzzer = rhythm only)."""
                on_ms = _cap_ms(on_ms)
                _led_set_tracked("blue", True)
                try:
                    _buzzer_set(True)
                    time.sleep(on_ms / 1000.0)
                finally:
                    _buzzer_set(False)
                _led_set_tracked("blue", False)
                if pause_s > 0:
                    time.sleep(pause_s)

            # "Bohooo" — longer cries trailing down (no rainbow, blue only)
            for on_ms, pause in (
                (130, 0.16),
                (115, 0.14),
                (100, 0.18),
                (90, 0.16),
                (78, 0.18),
                (68, 0.16),
                (58, 0.14),
                (50, 0.0),
            ):
                _sob(on_ms, pause)
        finally:
            _hw_release_under_lock()


def gemy_mean():
    """Mean / insult: sad descending beeps + slow red blinks (one lock)."""
    with _hw_lock:
        try:
            steps = [(420, 0.20, 0.14), (320, 0.20, 0.14), (240, 0.24, 0.0)]
            for on_ms, blink_s, pause_s in steps:
                on_ms = _cap_ms(on_ms)
                blink_s = _cap_sec(blink_s)
                led("red", True)
                try:
                    _buzzer_set(True)
                    time.sleep(min(on_ms / 1000.0, blink_s))
                finally:
                    _buzzer_set(False)
                led("red", False)
                if pause_s > 0:
                    time.sleep(pause_s)
            for _ in range(2):
                led("red", True)
                time.sleep(_cap_sec(0.16))
                led("red", False)
                time.sleep(0.12)
        finally:
            _hw_release_under_lock()


def gemy_name_ack():
    """Short 'Ge-my!' + mini rainbow when someone says the robot's name."""
    with _hw_lock:
        try:
            _play([(55, 32), (55, 32), (120, 0)])
            _rainbow_under_lock(cycles=1, dwell_ms=100)
        finally:
            _hw_release_under_lock()


# ---- LEDs -------------------------------------------------------------------
def _write(path, value):
    try:
        with open(path, "w") as f:
            f.write(str(value))
        return True
    except OSError as e:
        print(f"  (could not write {path}: {e})")
        return False


def _led_set_tracked(color, on):
    """Write one LED and update safety timers."""
    global _led_on_at
    base = _LED_PATH.format(color=color)
    _write(f"{base}/trigger", "none")
    _write(f"{base}/brightness", 1 if on else 0)
    with _safety_lock:
        if on:
            _led_on_at[color] = time.monotonic()
        else:
            _led_on_at.pop(color, None)


def led(color, on):
    """Turn an LED on/off. color = red|green|blue|all, on = True/False."""
    color = color.lower()
    targets = _COLORS if color == "all" else (color,)
    for c in targets:
        if c not in _COLORS:
            print(f"Unknown color '{c}'. Use: red, green, blue, all.")
            continue
        _led_set_tracked(c, bool(on))


def led_off_all():
    force_all_off()


def blink(color, times=5, on_ms=250, off_ms=250):
    on_ms = _cap_ms(on_ms)
    for _ in range(int(times)):
        led(color, True)
        time.sleep(on_ms / 1000.0)
        led(color, False)
        time.sleep(off_ms / 1000.0)
    led_off_all()


def rainbow(cycles=3, dwell_ms=300):
    with _hw_lock:
        try:
            _rainbow_under_lock(cycles=cycles, dwell_ms=dwell_ms)
        finally:
            _hw_release_under_lock()


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

    sub.add_parser("gemy-intro", help="Gemy startup hello (beeps + lights)")
    sub.add_parser("gemy-name", help="short Ge-my! name ack")
    sub.add_parser("gemy-yes", help="affirmative yes chirps + green")
    sub.add_parser("gemy-no", help="negative no tones + red")
    sub.add_parser("gemy-goodbye", help="Gemy shutdown goodbye")

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
    elif args.cmd == "gemy-intro":
        gemy_intro()
    elif args.cmd == "gemy-name":
        gemy_name_ack()
    elif args.cmd == "gemy-yes":
        gemy_yes()
    elif args.cmd == "gemy-no":
        gemy_no()
    elif args.cmd == "gemy-goodbye":
        gemy_goodbye()
    elif args.cmd == "force-off":
        force_all_off()
    elif args.cmd == "photo":
        photo(args.path, args.width, args.height, args.device,
              exposure=args.exposure, gain=args.gain)


if __name__ == "__main__":
    start_safety_watchdog()
    main()
