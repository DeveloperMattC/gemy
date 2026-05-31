# Student lab: Build Gemy — the Coralboard greeting robot

**Duration:** 90–120 minutes  
**Level:** Intermediate (Python, basic Linux, embedded concepts)

---

## What you will build

**Gemy** — a greeting robot on the Coralboard Sensor HAT:

| Input | Reaction |
|-------|----------|
| Say **"Gemy"** (its name) | Signature *Ge-my!* three-note beep + green-blue-green LED wave |
| Wave at the camera | Double beep + green LED |
| Hold a hand up (still, upper frame) | Double beep + green LED |
| Say "hello" / "hi" | Double beep + green LED |
| Say something funny ("haha", "lol") | Rainbow LEDs + R2D2-style buzzer |
| Say something nice ("good robot", "thanks") | Happy beeps + green/blue alternation |
| Say something mean ("stupid", "hate") | Sad beeps + red LED |
| Say anything else | One beep + blue LED |
| 20 s of silence | Force all LEDs and buzzer off |

---

## Part 0 — Understand the hardware

The **Sensor HAT** is not a second computer. It is peripherals on the Coralboard:

| HAT feature | Linux interface | Our wrapper |
|-------------|-----------------|-------------|
| Buzzer | GPIO `BUZZERn` (gpiochip0 line 6) | `hat.py` → `gpioset` |
| RGB status LEDs | `/sys/class/leds/{red,green,blue}:status` | `hat.py` → sysfs brightness |
| OV5647 camera | `/dev/video0`, controls on `/dev/v4l-subdev2` | `hat.py photo`, OpenCV in `greeter.py` |
| PDM microphone | ALSA / `sounddevice` | `utils.speech` (Moonshine) |

The board runs **Yocto Linux** (Poky). You access it from Windows with **ADB** (`adb shell`).

---

## Part 1 — Connect the board (15 min)

### Step 1.1 — Install ADB on Windows

```powershell
winget install Google.PlatformTools
```

Open a **new** PowerShell window and verify:

```powershell
adb version
```

### Step 1.2 — Plug in and open a shell

1. Connect USB-C to the Coralboard.
2. Wait ~20 seconds for boot.
3. Run:

```powershell
adb shell
```

You should see a `root@...#` prompt.

### Step 1.3 — Enable USB networking on the board

Inside `adb shell`:

```bash
udhcpc -i usb0
ping -c 2 8.8.8.8
```

If `udhcpc` fails with "no lease", the host NCM driver or Internet Connection Sharing is not active — ask your instructor to run `install-ncm-signed.ps1` (admin).

### Step 1.4 — Verify examples environment

```bash
ls /home/root/sl2610-examples/.venv/bin/python3
```

This Python has OpenCV, sounddevice, and the speech stack preinstalled.

**Checkpoint:** You can `adb shell`, board has internet, venv exists.

---

## Part 2 — Control the HAT manually (20 min)

### Step 2.1 — Push `hat.py`

From Windows, in the repo root (or use `.\hat-gui.ps1` which pushes automatically):

```powershell
adb push board\python\hat.py /home/root/hat.py
```

### Step 2.2 — Buzzer patterns

```bash
python3 /home/root/hat.py beep
python3 /home/root/hat.py beep 3
python3 /home/root/hat.py r2d2
python3 /home/root/hat.py buzzer off    # always run if buzzer sticks on
```

**Discussion:** Why does `buzzer off` matter? (GPIO output latches on this board — see [02-HOW-WE-CODED-IT.md](02-HOW-WE-CODED-IT.md).)

### Step 2.3 — LEDs

```bash
python3 /home/root/hat.py led red on
python3 /home/root/hat.py led all off
python3 /home/root/hat.py rainbow
python3 /home/root/hat.py led all off
```

### Step 2.4 — Camera photo

```bash
python3 /home/root/hat.py photo /home/root/lab_test.jpg
```

Pull the image to your PC:

```powershell
adb pull /home/root/lab_test.jpg .
```

If the image is very dark, the lab script sets exposure after the stream starts (same technique as `greeter.py`).

**Checkpoint:** Buzzer stops after each command, LEDs turn off, photo is visible.

### Step 2.5 — Optional GUI

From Windows:

```powershell
powershell -ExecutionPolicy Bypass -File hat-gui.ps1
```

---

## Part 3 — Speech on the board (15 min)

The greeting robot reuses the **same speech pipeline** as the official Gemma voice translation demo.

### Step 3.1 — Run Gemma voice demo (reference)

From Windows:

```powershell
powershell -ExecutionPolicy Bypass -File connect-gemma.ps1
```

Speak in English; confirm translation works. This proves the **microphone and Moonshine STT** work.

Stop with Ctrl+C.

### Step 3.2 — Understand the pipeline

1. **SoundDevice** captures audio from the HAT mic.
2. **Silero VAD** segments speech from silence.
3. **Moonshine** transcribes each segment to text.
4. Our code classifies text with simple word lists (not an LLM).

**Checkpoint:** Gemma demo hears you clearly.

---

## Part 4 — Deploy the greeting robot (25 min)

### Step 4.1 — Push lab scripts

```powershell
adb push board\python\greeter.py board\python\hat.py /home/root/
# or: .\greet-demo.ps1
```

### Step 4.2 — Launch from Windows

```powershell
powershell -ExecutionPolicy Bypass -File greet-demo.ps1
```

The launcher:

- Stops any old `wave_detect.py` (camera-only, **no voice**)
- Pushes latest `greeter.py` and `hat.py`
- Runs the greeter with unbuffered output

### Step 4.3 — Wait for readiness

In the terminal, wait for:

```
[ears] on. Greet (hello, hey, hi, hiya), make it laugh, be nice, or be mean and it reacts.
```

First launch takes **10–20 seconds** while Moonshine loads.

### Step 4.4 — Test each reaction

| Say this (approx.) | Expected |
|--------------------|----------|
| **"Gemy"** or **"Hey Gemy"** | `-> gemy` — signature three-note beep, green-blue-green |
| "Hello" | `[ears] heard: ... -> greet` — double beep, green |
| "That is so funny haha" | `-> funny` — rainbow + R2D2 |
| "Good robot thank you" | `-> nice` — happy beeps, green/blue |
| "You are stupid" | `-> mean` — sad beeps, red |
| "What time is it" | `-> neutral` — one beep, blue |

Also try **waving** at the camera and **holding a hand up** in the upper half of the frame.

**Checkpoint:** Terminal shows `[ears] heard: ...` and hardware reacts within 3 s cooldown between reactions.

### Step 4.5 — Control Center (optional)

```powershell
powershell -ExecutionPolicy Bypass -File make-shortcut.ps1
```

Use desktop **Coralboard Control Center** → button **0. Clean up board**, then **3. Gemy**.

---

## Part 5 — Experiments (15 min)

Pick at least two:

1. **Sensitivity:** `greet-demo.ps1 -Sensitivity high` — wave detection only; does speech still work?
2. **Mic only:** `greet-demo.ps1 -NoVision` — faster speech test without camera CPU load.
3. **Extend word lists:** Edit `FUNNY`, `NICE`, or `MEAN` in `greeter.py`, push, rerun.
4. **Cooldown:** Run with `--cooldown 1` on the board — what breaks socially?
5. **FPS:** Run with `--fps 20` — does voice stop? Why? (2 CPU cores.)

---

## Part 6 — Cleanup

Always end a session cleanly:

```bash
# Ctrl+C in greeter terminal, then:
python3 /home/root/hat.py buzzer off
python3 /home/root/hat.py led all off
```

Verify camera is free:

```bash
fuser /dev/video0 || echo "camera free"
```

---

## Lab completion checklist

- [ ] Board online via `udhcpc -i usb0`
- [ ] `hat.py` beep, LED, photo work
- [ ] Gemma voice demo hears speech
- [ ] Greeting robot shows `[ears] on`
- [ ] At least 4 reaction types observed (greet, funny, nice, mean/neutral)
- [ ] Wave or hand-up triggers greet
- [ ] Hardware off after Ctrl+C
- [ ] Can explain why `wave_detect.py` must not run alongside voice lab

---

## Next steps

- Read [02-HOW-WE-CODED-IT.md](02-HOW-WE-CODED-IT.md) for implementation details.
- See [04-TROUBLESHOOTING.md](04-TROUBLESHOOTING.md) if voice or camera fail.
