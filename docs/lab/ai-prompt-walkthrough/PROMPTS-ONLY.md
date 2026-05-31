# Prompts only — print-friendly

Copy each block into Cursor or ChatGPT. Run the matching command your instructor gives you.

---

**1A — Orient**

```
I'm doing a code jam with a Coralboard SL2610 and Sensor HAT (camera, mic, buzzer, red/green/blue LEDs). The project folder is called "robot". Please read README.md and docs/CORALBOARD-GUIDE.md and give me a 5-bullet summary of what this repo does in plain English. No jargon.
```

**1B — ADB check**

```
Help me verify ADB works. Give me the exact PowerShell commands to run from the repo root, and what success looks like. My board is plugged in via USB-C.
```

---

**2A — hat.py**

```
Create board/python/hat.py for the Coralboard Sensor HAT:
- Buzzer on GPIO BUZZERn (active low). IMPORTANT: gpioset latches on this board — every beep must end with the line driven HIGH (off).
- LEDs via /sys/class/leds red/green/blue:status
- Commands: beep, beep N, r2d2, siren, led, blink, rainbow, photo (camera needs venv OpenCV and fix dark OV5647 by setting exposure on /dev/v4l-subdev2 after stream starts)
- CLI: python3 hat.py beep, etc.
Keep it one file, well commented for beginners.
```

**2B — More beeps**

```
Add to board/python/hat.py: r2d2, chirp, warble, alarm, and sos buzzer patterns (rhythm only, no pitch change). Ensure buzzer always ends OFF.
```

---

**3A — HAT GUI**

```
Create windows/demos/hat-gui.ps1: a WinForms GUI that runs hat.py on the board via adb. Buttons for beep, beep x3, tone, siren, r2d2, warble, chirp, alarm, sos, red/green/blue LEDs, rainbow, take photo (venv python), and red STOP for buzzer off. Fix PowerShell $args collision by not naming a parameter $args. Push hat.py before camera commands.
```

---

**4A — Wave**

```
Create board/python/wave_detect.py: OpenCV on /dev/video0, motion detection, count horizontal reversals to detect a waving hand, then call hat.beep(2). Use hat.py from same folder. Include --sensitivity low|medium|high. Cap processing so it doesn't hog CPU. Always release camera and buzzer off on exit.
```

---

**5A — Gemy (full greeter)**

```
Create board/python/greeter.py named Gemy:
- Import hat.py and sl2610-examples utils.speech (Moonshine + Silero VAD)
- Listen for speech; classify into: gemy (name), greet (hello/hi), funny (haha/lol), nice (thanks/good/love), mean (stupid/hate), neutral (anything else)
- Reactions: gemy = signature 3-note beep + green-blue-green LEDs; greet = double beep + green; funny = r2d2 + rainbow; nice = happy beeps + green/blue alternate; mean = sad beeps + red; neutral = one beep + blue
- Vision thread: same wave + hand-held-up detection as before
- Load speech model BEFORE camera loop; cap vision --fps 5; kill stale wave_detect on startup
- 1 second cooldown between reactions; idle watchdog turns all off after 20s quiet
```

---

**6A — Control Center**

```
Create windows/hub/coralboard-hub.ps1 WinForms Control Center:
- Button 0 red: Clean up board (runs windows/setup/cleanup-board.ps1)
- Buttons: 1 internet NCM, 2 hat-gui, 3 Gemy greet-demo, 4 webrtc, 5 push images, 6 image classify, 7 Gemma voice, 8 adb shell
- Use windows/lib/Repo.ps1 Join-RobotPath for all script paths
- Show board connected + usb0 IP on refresh
Create windows/hub/make-shortcut.ps1 for desktop shortcut.
Create root-level thin .ps1 launchers that forward to windows/ scripts for backward compatibility.
```

---

**7A — Cleanup**

```
Create windows/setup/cleanup-board.ps1: adb wait-for-device, kill wave_detect.py and greeter.py and webrtc, free /dev/video0, gpioset buzzer off, hat led all off, print clear status. Used before starting Gemy.
Update greet-demo.ps1 to call cleanup-board first and push from board/python/.
```

---

**8A — Standalone USER button (optional)**

```
Create board/python/gemy-watcher.py: read USER button from /dev/input/event0 (Enter key), toggle greeter.py on/off, play gemy signature on start. Add board/systemd/gemy-watcher.service and gemy-autostart.service. Create windows/setup/install-gemy-standalone.ps1 to push files and enable watcher. Document in docs/CORALBOARD-GUIDE.md.
```

---

**9A — Organize repo (optional)**

```
Reorganize this repo: board/python, board/shell, board/systemd, windows/hub, windows/demos, windows/setup, windows/lib/Repo.ps1, drivers/ncm, drivers/cp210x, docs/, assets/, logs/. Move files, update all paths, keep root .ps1 as forwarders. Add windows/setup/verify-repo.ps1. Update README and docs. Do not break adb push paths on the board (/home/root/greeter.py etc).
```

---

**10 — Reflection**

```
I'm a non-engineer who just built Gemy. Write 3 sentences I can put in my code jam submission: what I built, one thing I learned, one surprise. Friendly tone, no jargon.
```

---

**Fix voice**

```
Gemy greeter: wave triggers beep but speech never shows [ears] heard. Check for wave_detect.py holding camera, CPU starvation, and fix greeter.py load speech before camera, fps cap, cleanup-board.ps1. Apply fixes to this repo.
```

**Fix buzzer stuck**

```
The HAT buzzer is stuck on loud. Give adb commands using hat.py buzzer off and gpioset gpiochip0 6=1. Explain in one sentence why (GPIO latch).
```
