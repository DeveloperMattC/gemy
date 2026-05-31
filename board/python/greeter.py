#!/usr/bin/env python3
"""Gemy — the Coralboard greeting robot. Beeps back (and flashes LEDs) when it
sees you wave, sees a hand held up, hears its name ("Gemy"), or speaks to it
on the HAT microphone.

Run on the board with the venv python (OpenCV + sounddevice + Moonshine):

  /home/root/sl2610-examples/.venv/bin/python3 /home/root/greeter.py
  ... greeter.py --no-speech            # vision only (wave + hand-up)
  ... greeter.py --no-vision            # ears only ("hello"/"hi")
  ... greeter.py --sensitivity high --gain 600
  ... greeter.py --audio-device 0       # pick the HAT mic explicitly

Ctrl+C to stop. Buzzer/LED/camera are always released on exit.
"""
import argparse
import collections
import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "/home/root/sl2610-examples")   # for utils.speech
import hat


def _stop_stale_demos():
    """Kill leftover wave_detect.py or duplicate greeter holding camera/mic."""
    import subprocess
    me = str(os.getpid())
    try:
        out = subprocess.check_output(["ps", "-ef"], text=True, errors="replace")
    except Exception:
        return
    killed = []
    for line in out.splitlines():
        if "wave_detect.py" not in line and "greeter.py" not in line:
            continue
        if "grep" in line:
            continue
        parts = line.split()
        if len(parts) < 2 or not parts[1].isdigit():
            continue
        pid = parts[1]
        if pid == me:
            continue
        try:
            os.kill(int(pid), 9)
            killed.append(pid)
        except OSError:
            pass
    if killed:
        print(f"[startup] stopped old demo PID(s): {', '.join(killed)}")
        time.sleep(1.0)


# ---- reactions: light + sound personalities --------------------------------
def _concurrent(*fns):
    """Run the given no-arg callables at the same time and wait for all."""
    ts = [threading.Thread(target=f, daemon=True) for f in fns]
    for t in ts:
        t.start()
    for t in ts:
        t.join()


def _react_gemy():
    # "You called my name!" — signature Ge-my! rhythm + green-blue-green LEDs.
    def leds():
        for color, ms in (("green", 0.14), ("blue", 0.14), ("green", 0.22)):
            hat.led_off_all()
            hat.led(color, True)
            time.sleep(ms)
        hat.led_off_all()

    def beeps():
        hat._play([(55, 35), (55, 35), (220, 0)])

    _concurrent(leds, beeps)


def _react_greet():
    # Friendly hello: double beep + a green flash, together.
    _concurrent(
        lambda: hat.beep(2),
        lambda: (hat.led("green", True), time.sleep(0.45), hat.led("green", False)),
    )


def _react_funny():
    # "That's funny!": rainbow lights + an R2D2 giggle, together.
    _concurrent(
        lambda: hat.r2d2(22),
        lambda: hat.rainbow(cycles=2, dwell_ms=110),
    )


def _react_nice():
    # "Aww, thanks!": cheerful little rising beeps + green/blue back-and-forth.
    def leds():
        for _ in range(3):
            hat.led("green", True); time.sleep(0.16); hat.led("green", False)
            hat.led("blue", True);  time.sleep(0.16); hat.led("blue", False)
    def beeps():
        hat._play([(70, 50), (70, 50), (150, 0)])
    _concurrent(leds, beeps)


def _react_mean():
    # "...that's mean": slow droopy "aww" beeps + red glow for a moment.
    def leds():
        hat.led("red", True); time.sleep(1.6); hat.led("red", False)
    def beeps():
        hat._play([(500, 180), (380, 220), (700, 0)])
    _concurrent(leds, beeps)


def _react_neutral():
    # "heard you, not sure what you mean": one short beep + a blue blip.
    _concurrent(
        lambda: hat.beep(1),
        lambda: (hat.led("blue", True), time.sleep(0.35), hat.led("blue", False)),
    )


REACTIONS = {
    "gemy":    _react_gemy,
    "greet":   _react_greet,
    "funny":   _react_funny,
    "nice":    _react_nice,
    "mean":    _react_mean,
    "neutral": _react_neutral,
}

_LABELS = {
    "gemy":    "Hi, I'm Gemy!",
    "greet":   "Hi!",
    "funny":   "haha, that's funny!",
    "nice":    "aww, thanks!",
    "mean":    "...hey, that's mean",
    "neutral": "hmm, ok",
}

# Heard-name triggers (Moonshine may spell slightly wrong)
GEMY_NAMES = {"gemy", "gemi", "jemmy", "jimmy"}


# ---- sentiment / intent of what was heard ----------------------------------
FUNNY = {"haha", "hahaha", "lol", "lmao", "rofl", "hehe", "heh",
         "funny", "hilarious", "joke", "joking", "kidding"}
NICE = {"good", "great", "nice", "love", "lovely", "awesome", "amazing",
        "wonderful", "cute", "sweet", "smart", "clever", "thanks", "thank",
        "pretty", "beautiful", "cool", "best", "wow", "adorable", "brilliant"}
MEAN = {"stupid", "dumb", "hate", "idiot", "ugly", "useless", "terrible",
        "awful", "suck", "sucks", "annoying", "worst", "bad", "shut", "lame",
        "garbage", "trash"}


def classify_text(low, words, greet_set):
    if words & GEMY_NAMES or "gemy" in low:
        return "gemy"
    if (words & FUNNY) or "ha ha" in low \
            or any(w.startswith(("haha", "hehe", "lol")) for w in words):
        return "funny"
    if words & MEAN:
        return "mean"
    if words & NICE:
        return "nice"
    if words & greet_set:
        return "greet"
    return None


# ---- shared reaction dispatcher --------------------------------------------
class Greeter:
    def __init__(self, cooldown=3.0, idle_timeout=20.0):
        self.cooldown = cooldown
        self.idle_timeout = idle_timeout
        self._lock = threading.Lock()
        self._last = 0.0
        self.last_activity = time.time()
        self._idle = False

    def react(self, kind, why=""):
        now = time.time()
        with self._lock:
            if now - self._last < self.cooldown:
                return
            self._last = now
            self.last_activity = now
            self._idle = False
        print(f"[{time.strftime('%H:%M:%S')}] {_LABELS.get(kind, kind)}  ({kind} <- {why})")
        try:
            REACTIONS.get(kind, _react_greet)()
        finally:
            hat.buzzer_off()
            hat.led_off_all()

    def greet(self, why):
        self.react("greet", why)

    def idle_check(self):
        """Safety net: after a quiet stretch, make sure nothing is left on."""
        if not self._idle and (time.time() - self.last_activity) > self.idle_timeout:
            self._idle = True
            hat.buzzer_off()
            hat.led_off_all()
            print(f"[{time.strftime('%H:%M:%S')}] (idle) all LEDs off, buzzer off.")


# ---- vision: wave + hand held up -------------------------------------------
def count_reversals(xs, min_step):
    direction = 0
    reversals = 0
    anchor = xs[0]
    for x in xs[1:]:
        if x - anchor > min_step:
            if direction == -1:
                reversals += 1
            direction = 1
            anchor = x
        elif anchor - x > min_step:
            if direction == 1:
                reversals += 1
            direction = -1
            anchor = x
    return reversals


SENSITIVITY = {
    #            min_motion  reversals  min_step  window
    "low":      (0.010,      4,         0.10,     2.0),
    "medium":   (0.005,      3,         0.08,     2.2),
    "high":     (0.003,      3,         0.06,     2.5),
}


def open_camera(args):
    """Open + prime the camera and apply exposure/gain. Returns cap or None."""
    import cv2
    cap = cv2.VideoCapture(args.device, cv2.CAP_V4L2)
    if not cap.isOpened():
        print(f"ERROR: could not open camera /dev/video{args.device} (vision off)")
        return None
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
    for _ in range(15):
        cap.read()
        time.sleep(0.02)
    hat._set_cam_ctrl("auto_exposure", 1)
    hat._set_cam_ctrl("gain_automatic", 0)
    hat._set_cam_ctrl("white_balance_automatic", 1)
    hat._set_cam_ctrl("exposure", int(args.exposure))
    hat._set_cam_ctrl("analogue_gain", int(args.gain))
    return cap


def vision_loop(greeter, args, stop_event, cap):
    import cv2
    import numpy as np

    min_motion, need_reversals, min_step, window = SENSITIVITY[args.sensitivity]

    print(f"[vision] on (sensitivity={args.sensitivity}). Wave or hold a hand up.")

    prev = None
    bg = None
    positions = collections.deque()
    hand_since = None
    frames = 0
    t_start = time.time()
    last_status = 0.0

    # Hand-up tuning: lots of "foreground" in the upper region, held still.
    HAND_FG = 0.06           # >=6% of the upper region differs from background
    HAND_STILL = 0.012       # frame-to-frame motion below this = "held, not waving"
    HAND_HOLD_S = 0.7        # must persist this long

    # Cap the vision rate. Sleeping each iteration hands the 2 CPU cores back to
    # the speech thread (Moonshine/VAD) so the mic isn't starved; ~12 fps is
    # plenty to see a wave or a held-up hand.
    target_dt = (1.0 / args.fps) if getattr(args, "fps", 0) else 0.0
    next_t = time.time()

    fails = 0
    frame_n = 0
    try:
        while not stop_event.is_set():
            if target_dt:
                sleep_for = next_t - time.time()
                if sleep_for > 0:
                    time.sleep(sleep_for)
                next_t = time.time() + target_dt
            if args.duration and (time.time() - t_start) >= args.duration:
                stop_event.set()
                break
            ok, frame = cap.read()
            frame_n += 1
            if frame_n % 2 != 0:
                continue
            if not ok or frame is None:
                fails += 1
                if fails > 150:
                    print("\n[vision] camera stopped delivering frames; vision off.")
                    break
                time.sleep(0.01)
                continue
            fails = 0
            frames += 1
            now = time.time()

            # Downscale for cheap processing (ratios stay resolution-independent).
            if frame.shape[1] > 360:
                frame = cv2.resize(frame, (320, 240))
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (15, 15), 0)
            if prev is None:
                prev = gray
                bg = gray.astype("float32")
                continue

            # consecutive-frame motion (for waving + "is it moving")
            delta = cv2.absdiff(prev, gray)
            prev = gray
            mthresh = cv2.threshold(delta, 25, 255, cv2.THRESH_BINARY)[1]
            mthresh = cv2.dilate(mthresh, None, iterations=2)
            mxs = np.nonzero(mthresh)[1]
            motion_ratio = mxs.size / float(mthresh.size)

            # ---- wave: horizontal oscillation -------------------------------
            if motion_ratio > min_motion:
                cx = float(mxs.mean()) / mthresh.shape[1]
                positions.append((now, cx))
            while positions and now - positions[0][0] > window:
                positions.popleft()
            if len(positions) >= 5:
                seq = [c for _, c in positions]
                if (max(seq) - min(seq) >= 0.15
                        and count_reversals(seq, min_step) >= need_reversals):
                    greeter.greet("wave")
                    positions.clear()

            # ---- hand held up: sustained still foreground in upper region ---
            cv2.accumulateWeighted(gray, bg, 0.05)
            fg = cv2.absdiff(gray, cv2.convertScaleAbs(bg))
            fgmask = cv2.threshold(fg, 30, 255, cv2.THRESH_BINARY)[1]
            h = fgmask.shape[0]
            upper = fgmask[0:int(h * 0.55), :]
            fg_upper = np.count_nonzero(upper) / float(upper.size)
            if fg_upper > HAND_FG and motion_ratio < HAND_STILL:
                if hand_since is None:
                    hand_since = now
                elif now - hand_since >= HAND_HOLD_S:
                    greeter.greet("hand up")
                    hand_since = None
            else:
                hand_since = None

            if not args.quiet and (now - last_status) > 1.0:
                fps = frames / (now - t_start)
                print(f"\r[vision] {fps:4.1f} fps  motion {motion_ratio*100:4.1f}%  "
                      f"upperFG {fg_upper*100:4.1f}%   ", end="", flush=True)
                last_status = now

    finally:
        stop_event.set()   # ensure other threads wind down if vision exits


# ---- ears: listen for speech (load model BEFORE camera when possible) ------
def build_speech(args):
    """Load Moonshine + mic. Call in main thread before vision hogs CPU."""
    try:
        from utils.speech import (
            MoonshineTranscriber, SileroSpeechSegmenter,
            SoundDeviceAudioSource, SpeechRecognizer,
        )
    except Exception as e:
        print(f"[ears] speech unavailable ({e})")
        return None, None

    device = args.audio_device
    if device is not None:
        try:
            device = int(device)
        except ValueError:
            pass

    print("[ears] loading speech model (~10-20s)...", flush=True)
    try:
        transcriber = MoonshineTranscriber(None, suppress_native_logs=True)
        source = SoundDeviceAudioSource(device=device, suppress_native_logs=True)
        segmenter = SileroSpeechSegmenter()
        recognizer = SpeechRecognizer(transcriber=transcriber, source=source,
                                      segmenter=segmenter)
        print("[ears] model ready.", flush=True)
        return recognizer, source
    except Exception as e:
        print(f"[ears] could not start microphone ({e})")
        return None, None


def speech_loop(greeter, args, stop_event, recognizer, source):
    keywords = set(k.strip().lower() for k in args.keywords.split(","))
    print(f"[ears] listening. Say 'Gemy' for its signature hello, or "
          f"hello/funny/nice/mean/anything else.", flush=True)
    try:
        with recognizer:
            while not stop_event.is_set():
                t = recognizer.listen_once(stop_event=stop_event)
                if t is None:
                    break
                text = t.text.strip()
                if not text:
                    continue
                words = set(w.strip(".,!?;:'\"").lower() for w in text.split())
                kind = classify_text(text.lower(), words, keywords) or "neutral"
                print(f"\n[ears] heard: {text!r} -> {kind}", flush=True)
                greeter.react(kind, f'heard "{text}"')
    except Exception as e:
        import traceback
        print(f"[ears] stopped: {e}", flush=True)
        traceback.print_exc()
    finally:
        try:
            source.stop()
        except Exception:
            pass


def main(argv=None):
    p = argparse.ArgumentParser(description="Gemy — greeting robot (wave / hand-up / voice)")
    p.add_argument("--device", type=int, default=0, help="camera /dev/videoN")
    p.add_argument("--width", type=int, default=640)
    p.add_argument("--height", type=int, default=480)
    p.add_argument("--exposure", type=int, default=740)
    p.add_argument("--gain", type=int, default=1023)
    p.add_argument("--sensitivity", choices=list(SENSITIVITY), default="medium")
    p.add_argument("--fps", type=float, default=5.0,
                   help="cap vision frame rate so the mic gets CPU (0=uncapped)")
    p.add_argument("--cooldown", type=float, default=1.0,
                   help="min seconds between reactions (lower = more responsive)")
    p.add_argument("--keywords", default="hello,hi,hey,hiya")
    p.add_argument("--audio-device", default=None, help="mic index/name (default: system default)")
    p.add_argument("--no-speech", action="store_true", help="disable the microphone trigger")
    p.add_argument("--no-vision", action="store_true", help="disable the camera triggers")
    p.add_argument("--duration", type=float, default=0.0, help="auto-stop after N s (0=forever)")
    p.add_argument("--idle-timeout", type=float, default=20.0,
                   help="after N s of no reaction, force LEDs + buzzer off")
    p.add_argument("--quiet", action="store_true")
    args = p.parse_args(argv)

    _stop_stale_demos()

    greeter = Greeter(cooldown=args.cooldown, idle_timeout=args.idle_timeout)
    stop_event = threading.Event()

    print("Gemy starting. Triggers: "
          + ("wave + hand-up" if not args.no_vision else "")
          + (" + " if (not args.no_vision and not args.no_speech) else "")
          + ('say "Gemy" / hello / hi / ...' if not args.no_speech else "")
          + ". Ctrl+C to stop.")

    # Load speech on the main thread BEFORE the camera loop (2 cores: model load
    # must not compete with OpenCV at 30+ fps).
    recognizer = source = None
    if not args.no_speech:
        recognizer, source = build_speech(args)
        if recognizer is None:
            args.no_speech = True

    cap = None
    if not args.no_vision:
        cap = open_camera(args)
        if cap is None:
            args.no_vision = True
            print("[vision] OFF (camera busy or missing). Voice still works.")

    def idle_loop():
        while not stop_event.is_set():
            greeter.idle_check()
            time.sleep(2.0)

    threads = []
    if recognizer is not None:
        threads.append(threading.Thread(target=speech_loop,
                                        args=(greeter, args, stop_event,
                                              recognizer, source),
                                        name="ears", daemon=True))
    threads.append(threading.Thread(target=idle_loop, name="idle", daemon=True))
    for t in threads:
        t.start()

    try:
        if args.no_vision:
            t0 = time.time()
            while not stop_event.is_set():
                time.sleep(0.2)
                if args.duration and (time.time() - t0) >= args.duration:
                    break
        else:
            vision_loop(greeter, args, stop_event, cap)   # runs in main thread
    except KeyboardInterrupt:
        print("\nStopping.")
    finally:
        stop_event.set()
        for t in threads:
            t.join(timeout=2.0)
        if cap is not None:
            cap.release()
        hat.buzzer_off()
        hat.led("all", False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
