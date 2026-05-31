# Student lab — technical track

**Duration:** 90–120 min · **Level:** beginner → intermediate

> **Easier path?** Most people should start with **[CODE-JAM.md](CODE-JAM.md)** (rounds + scorecard). This doc is the same journey with more hardware detail.

---

## What you build

**Gemy** — greeting robot on the Sensor HAT. Full mood table: [08-GEMY-MOODS-AND-REACTIONS.md](08-GEMY-MOODS-AND-REACTIONS.md).

---

## Part 0 — Hardware (5 min)

The **Sensor HAT** is not a second computer — camera, mic, buzzer, LEDs on the main Coralboard.

| HAT | Linux | Our code |
|-----|-------|----------|
| Buzzer | GPIO line 6 | `hat.py` |
| RGB LEDs | `/sys/class/leds/` | `hat.py` |
| Camera | `/dev/video0` | `greeter.py` vision |
| Mic | ALSA / sounddevice | Moonshine in `greeter.py` |

Three brains (do not mix up): OpenCV vision · Moonshine + keywords · optional Gemma 3 mood assist. [07-WAVE-VISION-AND-GEMMA.md](07-WAVE-VISION-AND-GEMMA.md)

---

## Part 1 — Connect (15 min)

```powershell
winget install Google.PlatformTools
adb devices          # must show "device"
adb shell udhcpc -i usb0
```

Or use **Control Center** (`make-shortcut.ps1`) and click **Refresh**.

**Pass:** `adb shell` works; optional `ping 8.8.8.8` if internet needed.

---

## Part 2 — HAT hardware (20 min)

```powershell
adb push board\python\hat.py /home/root/hat.py
adb shell python3 /home/root/hat.py beep
adb shell python3 /home/root/hat.py rainbow
adb shell python3 /home/root/hat.py led all off
```

Or **HAT test panel** from Control Center.

**Discussion:** Buzzer GPIO latches — always end with off. See [02-HOW-WE-CODED-IT.md](02-HOW-WE-CODED-IT.md).

**Pass:** Beep, LED, optional photo via HAT panel.

---

## Part 3 — Speech (15 min)

Gemy uses **Moonshine STT** on the HAT mic (same stack as Synaptics speech examples).

You do not need a separate Gemma translation demo to prove the mic — start Gemy directly:

```powershell
.\cleanup-board.ps1
.\greet-demo.ps1
```

Wait for `[ears] listening`. Say **"Gemy"** and **"hello"**.

**Pass:** Log shows `[ears] heard: ...`

---

## Part 4 — Full Gemy (25 min)

```powershell
.\greet-demo.ps1              # voice only
.\greet-demo.ps1              # use Control Center "camera + voice" for waves
```

Test matrix (same as [CODE-JAM.md](CODE-JAM.md) Round 4):

| Say | Expected |
|-----|----------|
| Gemy | gemy |
| Hello | greet |
| Joke / haha | funny + rainbow |
| Thank you | nice |
| You are stupid | mean + red |
| Nobody likes you | sad + blue |
| Yeah / no way | yes / no |
| Is 7 times 6 equal to 44? → is it equal to 42? | no → yes |

Wave and hand-up when camera mode is on.

**Pass:** 5+ moods + wave or hand-up.

---

## Part 5 — Experiments (15 min)

Pick two:

1. `greet-demo.ps1 -NoGemmaMood` — keywords only (debug)
2. `greet-demo.ps1 -NoVision` — mic only, no camera CPU
3. Edit `FUNNY` / `NICE` / `MEAN` in `greeter.py`, push, rerun
4. `--cooldown 1` — what breaks socially?

---

## Part 6 — Cleanup

```powershell
.\cleanup-board.ps1
```

Ctrl+C greeter first if running.

---

## Completion checklist

- [ ] Board online via ADB
- [ ] HAT beep + LED + photo
- [ ] `[ears] listening` + voice reactions
- [ ] Wave or hand-up (camera mode)
- [ ] 5+ moods observed
- [ ] Cleanup run

**Next:** [02-HOW-WE-CODED-IT.md](02-HOW-WE-CODED-IT.md) · **Stuck:** [04-TROUBLESHOOTING.md](04-TROUBLESHOOTING.md)
