# How we coded it — developer walkthrough

This document explains **design decisions and implementation** for each layer of the lab. Use it when reviewing code for a workshop submission or when extending the project.

---

## 1. Project layers

```
Windows host                         Coralboard (Linux)
─────────────────                    ────────────────────
coralboard-hub.ps1          adb      greeter.py  ← main lab app
greet-demo.ps1              ───►     hat.py      ← hardware abstraction
install-ncm-signed.ps1               sl2610-examples/utils/speech.py
hat-gui.ps1                          sl2610-examples/.venv (OpenCV, Moonshine)
```

**Pattern:** PowerShell launchers handle `adb push`, process cleanup, and opening an interactive terminal. Python on the board does real-time sensing and actuation.

---

## 2. `hat.py` — hardware abstraction

### 2.1 Buzzer via GPIO (`gpioset`)

The HAT buzzer is an **active buzzer** on GPIO line `BUZZERn` (typically `gpiochip0` line 6):

- Line **LOW** → buzzer **ON**
- Line **HIGH** → buzzer **OFF**

We use `gpiofind BUZZERn` when available, else fall back to the known mapping.

**Critical bug we fixed:** On this board, `libgpiod` v1 **latches** the output when `gpioset` exits. Early code used timed pulses that exited while the line was still LOW → **buzzer stuck on**.

**Fix:** Never rely on `gpioset --mode=time` alone. Every pattern:

1. `_buzzer_set(True)` → sleep in Python → `_buzzer_set(False)` in a `finally` block.

```python
def _play(pattern):
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
```

Patterns (`beep`, `r2d2`, `siren`, etc.) are lists of `(on_ms, gap_ms)` tuples. There is **no PWM** — pitch is fixed; personality comes from **rhythm**.

### 2.2 LEDs via sysfs

Board status LEDs appear as:

```
/sys/class/leds/red:status/brightness
/sys/class/leds/green:status/brightness
/sys/class/leds/blue:status/brightness
```

Before writing brightness, set `trigger` to `none` so the kernel LED driver does not fight our values. Max brightness is `1` on this platform.

### 2.3 Camera via OpenCV + V4L2 subdev

The OV5647 sensor exposes:

- Capture: `/dev/video0` (OpenCV `VideoCapture(..., CAP_V4L2)`)
- Controls: `/dev/v4l-subdev2` (exposure, gain)

**Black photo bug:** Setting exposure on the subdev **before** streaming often has no effect. `hat.py photo` and `greeter.py` read several warmup frames, **then** set manual exposure and analogue gain.

```python
hat._set_cam_ctrl("exposure", 740)
hat._set_cam_ctrl("analogue_gain", 1023)
```

---

## 3. `greeter.py` — Gemy (multimodal greeting robot)

### 3.1 Thread model

| Thread | Responsibility |
|--------|----------------|
| **Main** | Vision loop: camera read, wave + hand-up detection |
| **ears** (daemon) | Speech: VAD + Moonshine + sentiment → `react()` |
| **idle** (daemon) | After 20 s inactivity → force buzzer/LED off |

Shared state: `Greeter` instance with lock, cooldown timestamp, `last_activity`.

### 3.2 Reaction dispatcher

All outputs go through `Greeter.react(kind, why)`:

- Enforces **3 s cooldown** (configurable).
- Calls `REACTIONS[kind]()`.
- Always ends with `hat.buzzer_off()` and `hat.led_off_all()`.

**Sound + light:** Each mood calls a **`hat.gemy_*()`** helper that holds one **`_hw_lock`** and runs buzzer + LEDs **in sequence**. Do not run `r2d2` and `rainbow` in parallel threads — the lock hid the rainbow.

| `kind` | Helper | LEDs (summary) |
|--------|--------|----------------|
| `gemy` | `gemy_name_ack()` | Mini rainbow after name beep |
| `greet` | `gemy_greet()` | Rainbow + double beep |
| `funny` | `gemy_funny()` | Color blips + R2D2 + **2× rainbow** |
| `nice` | `gemy_nice()` | Rising beeps + rainbow + green/blue |
| `mean` | `gemy_mean()` | Red blinks + descending beeps |
| `sad` | `gemy_sad()` | Blue cry flashes + quiet whimpers |
| `yes` | `gemy_yes()` | Chirps + rainbow + green |
| `no` | `gemy_no()` | Red blinks + descending tones |
| `neutral` | `gemy_neutral()` | Soft beep + gentle rainbow |

See [08-GEMY-MOODS-AND-REACTIONS.md](08-GEMY-MOODS-AND-REACTIONS.md).

### 3.3 Vision — wave detection

> **Gemma 3 does not power the wave demo.** Vision is OpenCV motion math in `wave_detect.py` / `greeter.py` `vision_loop()`. Gemma 3 on this board is text-only and lives in `sl2610-examples/gemma_translate/` for translation demos. Full map: [07-WAVE-VISION-AND-GEMMA.md](07-WAVE-VISION-AND-GEMMA.md).

No ML/NPU. Algorithm per frame (on downscaled 320×240 gray):

1. Gaussian blur → `absdiff` vs previous frame → threshold → dilate.
2. Compute horizontal centroid of motion pixels.
3. Track centroid over ~2 s window.
4. Count left/right **reversals**; if enough reversals and sufficient horizontal span → **wave**.

Sensitivity presets (`low` / `medium` / `high`) tune motion threshold, reversal count, and min step size.

### 3.4 Vision — hand held up

Maintain a **running average background** (`accumulateWeighted`). Foreground = `absdiff` from background. If **upper 55%** of frame has enough foreground **and** frame-to-frame motion is low for **0.7 s** → hand held up (still pose, not waving).

### 3.5 Speech — reuse official stack

```python
sys.path.insert(0, "/home/root/sl2610-examples")
from utils.speech import (
    MoonshineTranscriber, SileroSpeechSegmenter,
    SoundDeviceAudioSource, SpeechRecognizer,
)
```

`SpeechRecognizer.listen_once()` blocks until VAD finds an utterance and Moonshine returns non-empty text.

### 3.6 Sentiment — keywords first, Gemma assist second

After Moonshine transcribes speech:

1. **`classify_utterance()`** — off, yes, no, joke tracker, name, then **`classify_keywords()`** (mean, sad, funny, nice, greet).
2. If still `None` and **`--gemma-mood`**: **`try_gemma_mood_assist()`** (subprocess worker, lazy NPU load).
3. **`resolve_reaction_kind()`** — unknown label → **neutral** (never crash `react()`).

Valid moods: `gemy`, `greet`, `funny`, `nice`, `mean`, `sad`, `yes`, `no`, `neutral`, `off`.

**`gemma_mood.mood_for_reaction()`** maps Gemma output + aliases; garbage → `None` → neutral.

**Stability:** `--gemma-mood-serial` is disabled. Worker prints `READY` without loading the model; first unclear phrase loads Gemma (up to 90 s timeout). Boot uses `--no-gemma-mood`.

Joke detection: **`KnockKnockTracker`** + riddle phrases ("why did the chicken…") + keyword `FUNNY` set.

Full flow: [08-GEMY-MOODS-AND-REACTIONS.md](08-GEMY-MOODS-AND-REACTIONS.md).

Moonshine transcripts are imperfect; keywords are forgiving (e.g. `"ha ha"` substring, `haha` prefix).

### 3.7 CPU contention — why voice “stopped working”

The Coralboard has **2 CPU cores**. An uncapped OpenCV loop (~35 fps) starved Moonshine.

**Mitigations coded:**

1. **`--fps` default 8** — sleep between frames to yield CPU.
2. **Downscale** frames to 320×240 before processing.
3. **Open camera before** starting speech thread (avoid init race).
4. **`_stop_stale_demos()`** — kill leftover `wave_detect.py` / duplicate greeter holding `/dev/video0`.
5. **`greet-demo.ps1`** — `pkill` stale processes before launch.

### 3.8 Startup cleanup

```python
def _stop_stale_demos():
    # scan ps -ef, kill other wave_detect.py / greeter.py PIDs
```

`wave_detect.py` is the **legacy wave-only** script with **no microphone**. If it is left running, students hear nothing — a common lab failure mode.

---

## 4. Windows launchers

### 4.1 `greet-demo.ps1`

1. `adb push` `greeter.py`, `hat.py`
2. `pkill` old demos on board
3. `adb shell -t` run venv python with `-u` (unbuffered stdout)

Students see `[ears] heard: ...` lines in real time.

### 4.2 `install-ncm-signed.ps1`

One-time / per-boot fix for:

- Custom-signed **UsbNcm** driver binding
- **Internet Connection Sharing** from host Wi-Fi/Ethernet to the NCM adapter

Without this, `udhcpc -i usb0` fails and HuggingFace model downloads break.

### 4.3 `coralboard-hub.ps1`

WinForms **Control Center** — one button per demo, connection status, `adb shell` shortcut. Button 3 launches `greet-demo.ps1`.

### 4.4 `hat-gui.ps1`

WinForms panel for manual HAT testing. **Bug fixed:** parameter named `$args` shadowed PowerShell’s automatic `$args`; renamed to `$hatArgs`.

---

## 5. Legacy and optional components

| File | Status |
|------|--------|
| `wave_detect.py` | Superseded by `greeter.py` vision; no speech |
| `webrtc-stream.sh` + `webrtc-view.ps1` | Browser video stream; separate extension |
| `gemma_text.py` | Minimal Gemma text translation |
| `connect-gemma.ps1` | Official voice translation demo launcher |

---

## 6. File dependency graph

```
greeter.py
  ├── hat.py (buzzer, LED, camera helpers)
  └── sl2610-examples/utils/speech.py
        ├── sounddevice → ALSA mic
        ├── Silero VAD
        └── Moonshine STT

greet-demo.ps1
  ├── adb → push greeter.py, hat.py
  └── adb shell → venv python greeter.py
```

---

## 7. Extension ideas for advanced labs

1. Replace keyword sentiment with **Gemma 3** text classification (higher latency, needs NPU/CPU budget).
2. Add **YOLOv8** person detection for hand-up instead of background subtraction.
3. Log transcripts to a CSV for classroom analytics.
4. Add MQTT/WebSocket to drive LEDs from a web UI.
5. Package reactions as a **state machine** diagram students must implement.

---

## 8. Key lessons for embedded + edge AI labs

1. **Always release hardware** in `finally` blocks (GPIO latch, camera fd).
2. **Measure CPU contention** before blaming the ML model.
3. **Reuse vendor speech stacks** instead of reintegrating from scratch.
4. **Launcher scripts** are part of the product — students run Windows, not the board directly.
5. **Explicit process hygiene** on shared `/dev/video0` resources.
