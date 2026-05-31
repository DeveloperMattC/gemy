# Meet Gemy — Coralboard Code Lab (SL2610 + Sensor HAT)

**Teach edge AI on real hardware:** wave detection, on-device speech, buzzer + RGB personality — on the [Synaptics Coralboard](https://www.synaptics.com/) with Sensor HAT. Windows host scripts included.

Lab documentation for the **[gemy-coralboard-lab](https://github.com/DeveloperMattC/gemy-coralboard-lab)** repo. Source code lives at the project root:

| Location | Contents |
|----------|----------|
| `../board/python/` | `greeter.py` (Gemy), `hat.py`, `gemy-watcher.py` |
| `../windows/demos/` | `greet-demo.ps1`, `hat-gui.ps1`, … |
| `../windows/setup/` | `cleanup-board.ps1`, `install-gemy-standalone.ps1` |
| `../docs/CORALBOARD-GUIDE.md` | Operator guide |

Run demos from the **repo root** (e.g. `.\greet-demo.ps1`) or see [../README.md](../README.md).

---

This package is for teaching and submitting a hands-on lab built around the **Synaptics Coralboard (SL2610)** and its **Sensor HAT** (camera, PDM microphone, buzzer, RGB LEDs).

Participants connect a Windows host to the board over USB, share internet, then build and run **Gemy** — a multimodal greeting robot that reacts to its name, waves, raised hands, and spoken phrases with distinct light-and-sound personalities.

---

## Lab package contents

| Path | Audience | Purpose |
|------|----------|---------|
| **[ai-prompt-walkthrough/](ai-prompt-walkthrough/)** | **Non-engineers / code jam** | **Build Gemy by pasting AI prompts — no coding required** |
| [01-STUDENT-LAB.md](01-STUDENT-LAB.md) | Students | Step-by-step lab exercises (connect → hardware → greeting robot) |
| [02-HOW-WE-CODED-IT.md](02-HOW-WE-CODED-IT.md) | Developers / reviewers | How each component was designed and implemented |
| [03-ARCHITECTURE.md](03-ARCHITECTURE.md) | Everyone | System diagram, threads, data flow |
| [04-TROUBLESHOOTING.md](04-TROUBLESHOOTING.md) | Students + instructors | Common failures and fixes |
| [05-INSTRUCTOR-GUIDE.md](05-INSTRUCTOR-GUIDE.md) | Instructors | Setup checklist, timing, assessment ideas |
| [06-STANDALONE-GEMY.md](06-STANDALONE-GEMY.md) | Everyone | Run Gemy with USER button, no PC/internet |

Source code: `../../board/python/`, `../../windows/` (see [../../README.md](../../README.md)).

The parent project also has [CORALBOARD-GUIDE.md](../CORALBOARD-GUIDE.md) as a day-to-day operator reference; this code lab is structured for **submission and classroom use**.

---

## Learning objectives

By the end of the lab, participants can:

1. Connect a Coralboard to a Windows PC with **ADB** and **USB NCM** networking.
2. Control HAT hardware (buzzer, LEDs, camera) from Python using **GPIO**, **sysfs**, and **V4L2**.
3. Explain why **GPIO latching** matters for the buzzer and how we fixed stuck-on behavior.
4. Run **on-device speech-to-text** (Moonshine + Silero VAD) alongside **OpenCV** vision on a 2-core embedded Linux system.
5. Design a **reaction dispatcher** that maps inputs (vision + sentiment) to concurrent LED and buzzer patterns.
6. Debug resource contention (camera vs microphone) and stale processes holding `/dev/video0`.

---

## Hardware and software prerequisites

### Hardware

- Synaptics Coralboard (SL2610) with Sensor HAT attached
- USB-C cable (data-capable) to a Windows 10/11 PC
- Optional: CP210x USB-UART driver if using the HAT serial console (see official board guide)

### Host (one-time setup)

- **ADB** (Android Platform Tools) on Windows PATH
- **Signed NCM driver** + Internet Connection Sharing — see `scripts/install-ncm-signed.ps1` and official Coralboard getting-started docs
- PowerShell with permission to run local scripts (`ExecutionPolicy Bypass` for lab scripts)

### Board (one-time setup)

- Examples repo at `/home/root/sl2610-examples` with `.venv` and dependencies (OpenCV, sounddevice, Moonshine, Gemma demos)
- Lab scripts pushed to `/home/root/` (`greeter.py`, `hat.py`, etc.)

---

## Quick start (instructor smoke test)

```powershell
cd path\to\gemy-coralboard-lab

# 1. Re-arm USB internet sharing (admin UAC)
.\install-ncm-signed.ps1

# 2. Push lab scripts (or greet-demo does this)
adb wait-for-device
adb push board\python\greeter.py board\python\hat.py /home/root/

# 3. On board: get IP
adb shell udhcpc -i usb0

# 4. Run Gemy
.\greet-demo.ps1
```

Wait for `[ears] listening`, then say **Gemy**, **hello**, **you are funny**, **good robot**, and a neutral phrase like **what time is it**.

---

## Submission notes (Google / workshop)

When adapting this for Google Codelabs or an internal workshop:

- Replace placeholder author/org fields in [docs/05-INSTRUCTOR-GUIDE.md](docs/05-INSTRUCTOR-GUIDE.md).
- Add your branding, duration (suggested **90–120 minutes**), and links to official Coralboard documentation.
- Include a **rubric** or completion checklist from the student lab doc.
- Optional extensions: Gemma translation demo (`connect-gemma.ps1`), image classification (`connect-demo.ps1`), WebRTC browser stream (`webrtc-view.ps1`).

---

## License and attribution

Lab materials describe integration with Synaptics Coralboard examples (`sl2610-examples`), Moonshine STT, and OpenCV. Follow the license terms of those upstream projects and the Coralboard SDK when redistributing.
