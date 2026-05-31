# Fix-it prompts (when something breaks)

Paste these into the AI when a step fails. Stay in the **gemy-coralboard-lab** repo folder.

---

## ADB does not see the board

```
adb devices shows nothing or unauthorized. I'm on Windows 11 with Coralboard USB-C. Give me a short checklist: cable, wait for boot, adb kill-server, drivers, and what "unauthorized" means. Commands only.
```

---

## No internet on the board (udhcpc fails)

```
udhcpc -i usb0 on Coralboard says no lease. Point me to install-ncm-signed.ps1 in this repo and explain in plain English what NCM and Internet Connection Sharing do. I may need admin.
```

---

## Buzzer will not stop

```
The HAT buzzer is stuck on loud. Give adb commands using hat.py buzzer off and gpioset gpiochip0 6=1. Explain in one sentence why (GPIO latch).
```

---

## “Does Gemma watch the camera for waves?”

```
Explain in plain English: wave_detect.py and greeter.py vision use OpenCV motion only — no Gemma 3, no training. Gemma 3 on Coralboard is text-only in sl2610-examples/gemma_translate for translation. Point me to docs/lab/07-WAVE-VISION-AND-GEMMA.md in this repo.
```

---

## Voice does not work but waving works

```
Gemy greeter: wave triggers beep but speech never shows [ears] heard. Check for wave_detect.py holding camera, CPU starvation, and fix greeter.py load speech before camera, fps cap, cleanup-board.ps1. Apply fixes to this repo.
```

---

## Camera photo is black

```
hat.py photo on Coralboard OV5647 is black. Fix by setting exposure and gain on /dev/v4l-subdev2 after stream starts. Update board/python/hat.py.
```

---

## AI put files in the wrong place

```
Reorganize files to match this repo standard: board/python for greeter.py hat.py, windows/demos for PowerShell launchers, windows/setup for cleanup-board.ps1. Fix paths and root forwarders. Run verify-repo.ps1 logic.
```

---

## Hub button does nothing

```
coralboard-hub.ps1 buttons don't launch scripts. Fix Join-RobotPath in windows/lib/Repo.ps1 and hub script paths. Root forwarders should call windows/ scripts.
```

---

## Speech hears me but wrong mood

```
Moonshine mis-transcribes. Widen GEMY_NAMES and FUNNY NICE MEAN keyword lists in greeter.py for jam demo. Show me what you changed.
```

---

## Start over on the board

```
Run full cleanup: kill greeter wave_detect webrtc, free video0, buzzer off, leds off. Give me one PowerShell command from repo root using cleanup-board.ps1
```
