# Prompt journey — build Gemy step by step

**How to use:** For each step, paste the prompt into your AI (Cursor chat). Let it create or change files. Then run the **Try it** line in PowerShell or on the board. Wait for the checkpoint before moving on.

---

## Step 1 — Meet the project (5 min)

**Say to the room:** “We’re going to teach a robot named Gemy to see, hear, and react — using AI to write the code for us.”

### Prompt 1A — orient the AI

```
I'm doing a code jam with a Coralboard SL2610 and Sensor HAT (camera, mic, buzzer, red/green/blue LEDs). The project is the gemy-coralboard-lab repo. Please read README.md and docs/CORALBOARD-GUIDE.md and give me a 5-bullet summary of what this repo does in plain English. No jargon.
```

**You should see:** A short summary mentioning Gemy, ADB, Control Center, and the HAT.

### Prompt 1B — check the board is connected

```
Help me verify ADB works. Give me the exact PowerShell commands to run from the repo root, and what success looks like. My board is plugged in via USB-C.
```

**Try it (PowerShell, repo root):**

```powershell
adb devices
```

**Checkpoint:** A line ending in `device` (not `unauthorized`).

---

## Step 2 — Make the buzzer and lights obey you (15 min)

**Say to the room:** “First we teach the robot body language — beeps and colors — one command at a time.”

### Prompt 2A — create hat.py

```
Create board/python/hat.py for the Coralboard Sensor HAT:
- Buzzer on GPIO BUZZERn (active low). IMPORTANT: gpioset latches on this board — every beep must end with the line driven HIGH (off).
- LEDs via /sys/class/leds red/green/blue:status
- Commands: beep, beep N, r2d2, siren, led, blink, rainbow, photo (camera needs venv OpenCV and fix dark OV5647 by setting exposure on /dev/v4l-subdev2 after stream starts)
- CLI: python3 hat.py beep, etc.
Keep it one file, well commented for beginners.
```

**Try it:**

```powershell
adb push board\python\hat.py /home/root/hat.py
adb shell python3 /home/root/hat.py beep
adb shell python3 /home/root/hat.py led green on
adb shell python3 /home/root/hat.py led all off
```

**Checkpoint:** You hear one short beep; green LED turns on then off.

### Prompt 2B — add fun buzzer patterns

```
Add to board/python/hat.py: r2d2, chirp, warble, alarm, and sos buzzer patterns (rhythm only, no pitch change). Ensure buzzer always ends OFF.
```

**Try it:**

```powershell
adb push board\python\hat.py /home/root/hat.py
adb shell python3 /home/root/hat.py r2d2
```

**Checkpoint:** A burst of short robotic beeps, then silence.

---

## Step 3 — Point-and-click HAT tester (10 min)

**Say to the room:** “Now we get buttons on the laptop so we don’t have to memorize commands.”

### Prompt 3A — Windows HAT GUI

```
Create windows/demos/hat-gui.ps1: a WinForms GUI that runs hat.py on the board via adb. Buttons for beep, beep x3, tone, siren, r2d2, warble, chirp, alarm, sos, red/green/blue LEDs, rainbow, take photo (venv python), and red STOP for buzzer off. Fix PowerShell $args collision by not naming a parameter $args. Push hat.py before camera commands.
```

**Try it:**

```powershell
powershell -ExecutionPolicy Bypass -File hat-gui.ps1
```

**Checkpoint:** A window opens; **Beep** makes a short sound; **STOP** silences the buzzer.

---

## Step 4 — Wave at the robot (15 min)

**Say to the room:** “Gemy will notice when you wave — using the camera, not magic.”

### Prompt 4A — wave detector

```
Create board/python/wave_detect.py: OpenCV on /dev/video0, motion detection, count horizontal reversals to detect a waving hand, then call hat.beep(2). Use hat.py from same folder. Include --sensitivity low|medium|high. Cap processing so it doesn't hog CPU. Always release camera and buzzer off on exit.
```

**Try it:**

```powershell
adb push board\python\wave_detect.py board\python\hat.py /home/root/
powershell -ExecutionPolicy Bypass -File wave-demo.ps1
```

Wave at the camera, then press **Ctrl+C**.

**Checkpoint:** Double beep when you wave; stops when you end the demo.

---

## Step 5 — Gemy hears you (20 min)

**Say to the room:** “We add ears. The board already has speech AI from the Gemma demos — we reuse it.”

### Prompt 5A — greeter with voice

```
Create board/python/greeter.py named Gemy:
- Import hat.py and sl2610-examples utils.speech (Moonshine + Silero VAD)
- Listen for speech; classify into: gemy (name), greet (hello/hi), funny (haha/lol), nice (thanks/good/love), mean (stupid/hate), neutral (anything else)
- Reactions: gemy = signature 3-note beep + green-blue-green LEDs; greet = double beep + green; funny = r2d2 + rainbow; nice = happy beeps + green/blue alternate; mean = sad beeps + red; neutral = one beep + blue
- Vision thread: same wave + hand-held-up detection as before
- Load speech model BEFORE camera loop; cap vision --fps 5; kill stale wave_detect on startup
- 1 second cooldown between reactions; idle watchdog turns all off after 20s quiet
```

**Try it:**

```powershell
adb push board\python\greeter.py board\python\hat.py /home/root/
powershell -ExecutionPolicy Bypass -File cleanup-board.ps1
powershell -ExecutionPolicy Bypass -File greet-demo.ps1
```

Wait for `[ears] listening`. Say **“Gemy”**, then **“hello”**, then **“that is funny haha”**.

**Checkpoint:** Terminal shows `[ears] heard: ... -> gemy` (or greet/funny/etc.) and the board reacts.

---

## Step 6 — Control Center on your desktop (10 min)

**Say to the room:** “One window to rule all demos — for the jam and for homework.”

### Prompt 6A — hub + shortcut

```
Create windows/hub/coralboard-hub.ps1 WinForms Control Center:
- Button 0 red: Clean up board (runs windows/setup/cleanup-board.ps1)
- Buttons: 1 internet NCM, 2 hat-gui, 3 Gemy greet-demo, 4 webrtc, 5 push images, 6 image classify, 7 Gemma voice, 8 adb shell
- Use windows/lib/Repo.ps1 Join-RobotPath for all script paths
- Show board connected + usb0 IP on refresh
Create windows/hub/make-shortcut.ps1 for desktop shortcut.
Create root-level thin .ps1 launchers that forward to windows/ scripts for backward compatibility.
```

**Try it:**

```powershell
powershell -ExecutionPolicy Bypass -File make-shortcut.ps1
powershell -ExecutionPolicy Bypass -File coralboard-hub.ps1
```

**Checkpoint:** Hub opens; **0. Clean up** then **3. Gemy** launches the greeter.

---

## Step 7 — Cleanup helper (5 min)

**Say to the room:** “Voice breaks if an old demo still holds the camera. This button fixes that.”

### Prompt 7A — cleanup-board

```
Create windows/setup/cleanup-board.ps1: adb wait-for-device, kill wave_detect.py and greeter.py and webrtc, free /dev/video0, gpioset buzzer off, hat led all off, print clear status. Used before starting Gemy.
Update greet-demo.ps1 to call cleanup-board first and push from board/python/.
```

**Try it:**

```powershell
powershell -ExecutionPolicy Bypass -File cleanup-board.ps1
```

**Checkpoint:** Message says camera free, no old demos.

---

## Step 8 — Gemy works without a laptop (10 min, optional)

**Say to the room:** “The board has a USER button. We can press it to start Gemy like a toy.”

### Prompt 8A — standalone

```
Create board/python/gemy-watcher.py: read USER button from /dev/input/event0 (Enter key), toggle greeter.py on/off, play gemy signature on start. Add board/systemd/gemy-watcher.service and gemy-autostart.service. Create windows/setup/install-gemy-standalone.ps1 to push files and enable watcher. Document in docs/CORALBOARD-GUIDE.md.
```

**Try it (once while USB connected):**

```powershell
powershell -ExecutionPolicy Bypass -File install-gemy-standalone.ps1
```

Unplug from PC data (or use a USB charger). Press **USER** on the board.

**Checkpoint:** Signature beep; say “Gemy” and it responds.

---

## Step 9 — Organize the repo (5 min, optional)

**Say to the room:** “Real projects keep files in folders. We’ll ask AI to tidy without breaking paths.”

### Prompt 9A — structure

```
Reorganize this repo: board/python, board/shell, board/systemd, windows/hub, windows/demos, windows/setup, windows/lib/Repo.ps1, drivers/ncm, drivers/cp210x, docs/, assets/, logs/. Move files, update all paths, keep root .ps1 as forwarders. Add windows/setup/verify-repo.ps1. Update README and docs. Do not break adb push paths on the board (/home/root/greeter.py etc).
```

**Try it:**

```powershell
powershell -ExecutionPolicy Bypass -File windows\setup\verify-repo.ps1
```

**Checkpoint:** “All checks passed.”

---

## Step 10 — Demo time (10 min)

**Say to the room:** “You built a robot with a name, a personality, and a face. Show your neighbor.”

### Final demo script

1. **Clean up board** (hub button 0)  
2. **Gemy** (button 3)  
3. Say: **“Gemy”** → signature hello  
4. Say: **“You are a good robot”** → nice lights  
5. Say: **“Haha that is funny”** → rainbow  
6. **Wave** → greet beep  
7. **Ctrl+C** — done  

### Prompt 10 — reflection (optional)

```
I'm a non-engineer who just built Gemy. Write 3 sentences I can put in my code jam submission: what I built, one thing I learned, one surprise. Friendly tone, no jargon.
```

---

## You finished

Technical details: [../02-HOW-WE-CODED-IT.md](../02-HOW-WE-CODED-IT.md)  
If something broke: [03-fix-it-prompts.md](03-fix-it-prompts.md)
