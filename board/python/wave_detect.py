#!/usr/bin/env python3
"""Keep the HAT camera on, detect a hand wave, and beep twice when it sees one.

Pure OpenCV motion analysis (no ML, no NPU needed). A "wave" = repeated
left<->right motion in the frame within a short time window.

Run on the board with the venv python (needs OpenCV):

  /home/root/sl2610-examples/.venv/bin/python3 /home/root/wave_detect.py
  ... wave_detect.py --duration 30        # auto-stop after 30s (0 = run forever)
  ... wave_detect.py --gain 400           # lower gain if the image is washed out
  ... wave_detect.py --sensitivity high   # easier to trigger

Press Ctrl+C to stop. The buzzer is always released on exit.
"""
import argparse
import collections
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hat  # reuse buzzer + camera-control helpers


def setup_camera(device, width, height, exposure, gain):
    import cv2
    cap = cv2.VideoCapture(device, cv2.CAP_V4L2)
    if not cap.isOpened():
        print(f"ERROR: could not open camera /dev/video{device}")
        return None
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    # Stream first, then apply manual exposure/gain (OV5647 is dark otherwise).
    for _ in range(15):
        cap.read()
        time.sleep(0.02)
    hat._set_cam_ctrl("auto_exposure", 1)        # 1 = manual
    hat._set_cam_ctrl("gain_automatic", 0)
    hat._set_cam_ctrl("white_balance_automatic", 1)
    hat._set_cam_ctrl("exposure", int(exposure))
    hat._set_cam_ctrl("analogue_gain", int(gain))
    return cap


def count_reversals(xs, min_step):
    """Count left<->right direction changes in a sequence of x positions.

    Uses extrema tracking with hysteresis (min_step) so small jitter is ignored.
    A wave (e.g. left-right-left) produces 2-3 reversals.
    """
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


def main(argv=None):
    p = argparse.ArgumentParser(description="Wave detector -> beeps twice on a wave")
    p.add_argument("--device", type=int, default=0)
    p.add_argument("--width", type=int, default=640)
    p.add_argument("--height", type=int, default=480)
    p.add_argument("--exposure", type=int, default=740)
    p.add_argument("--gain", type=int, default=1023)
    p.add_argument("--sensitivity", choices=list(SENSITIVITY), default="medium")
    p.add_argument("--cooldown", type=float, default=3.0,
                   help="seconds to wait after a beep before detecting again")
    p.add_argument("--duration", type=float, default=0.0,
                   help="auto-stop after N seconds (0 = run until Ctrl+C)")
    p.add_argument("--quiet", action="store_true", help="don't print live status")
    args = p.parse_args(argv)

    import cv2
    import numpy as np

    min_motion, need_reversals, min_step, window = SENSITIVITY[args.sensitivity]

    cap = setup_camera(args.device, args.width, args.height, args.exposure, args.gain)
    if cap is None:
        return 1

    print(f"Wave detector running (sensitivity={args.sensitivity}). "
          f"Wave your hand left-right in front of the camera. Ctrl+C to stop.")

    prev = None
    positions = collections.deque()   # (timestamp, normalized_cx)
    last_beep = 0.0
    frames = 0
    t_start = time.time()
    last_status = 0.0

    try:
        while True:
            ok, frame = cap.read()
            if not ok or frame is None:
                time.sleep(0.01)
                continue
            frames += 1
            now = time.time()

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (21, 21), 0)
            if prev is None:
                prev = gray
                continue

            delta = cv2.absdiff(prev, gray)
            prev = gray
            thresh = cv2.threshold(delta, 25, 255, cv2.THRESH_BINARY)[1]
            thresh = cv2.dilate(thresh, None, iterations=2)

            ys, xs = np.nonzero(thresh)
            motion_ratio = xs.size / float(thresh.size)

            if motion_ratio > min_motion:
                cx = float(xs.mean()) / thresh.shape[1]   # 0..1 across width
                positions.append((now, cx))

            while positions and now - positions[0][0] > window:
                positions.popleft()

            if len(positions) >= 5 and (now - last_beep) > args.cooldown:
                seq = [c for _, c in positions]
                span = max(seq) - min(seq)
                reversals = count_reversals(seq, min_step)
                if reversals >= need_reversals and span >= 0.15:
                    print(f"[{time.strftime('%H:%M:%S')}] WAVE detected "
                          f"(reversals={reversals}, span={span:.2f}) -> beep beep")
                    hat.beep(2)
                    hat.buzzer_off()      # belt-and-suspenders: never leave it on
                    last_beep = time.time()
                    positions.clear()

            if not args.quiet and (now - last_status) > 1.0:
                fps = frames / (now - t_start)
                bar = "#" * min(40, int(motion_ratio * 800))
                print(f"\rmotion {motion_ratio*100:5.2f}%  {fps:4.1f} fps  "
                      f"pts={len(positions):2d} {bar:<40}", end="", flush=True)
                last_status = now

            if args.duration and (now - t_start) >= args.duration:
                print("\nDuration reached, exiting.")
                break
    except KeyboardInterrupt:
        print("\nStopping.")
    finally:
        cap.release()
        hat.buzzer_off()
    return 0


if __name__ == "__main__":
    sys.exit(main())
