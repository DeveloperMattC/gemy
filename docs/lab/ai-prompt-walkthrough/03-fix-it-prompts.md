# Fix-it prompts (when something breaks)

Paste into the AI. Stay in the **gemy** repo folder.

---

## ADB does not see the board

```
adb devices shows nothing or unauthorized on Windows 11 + Coralboard USB-C. Short checklist: cable, boot wait, adb kill-server, drivers. Commands only.
```

---

## No internet on the board (udhcpc fails)

```
udhcpc -i usb0 says no lease. Point me to install-ncm-signed.ps1 and explain NCM/ICS in plain English.
```

---

## Buzzer will not stop

```
HAT buzzer stuck ON. adb commands: hat.py buzzer off and gpioset gpiochip0 6=1. One sentence on GPIO latch.
```

---

## “Does Gemma watch the camera?”

```
Explain: greeter.py vision_loop uses OpenCV motion only — no Gemma, no training. Gemma 3 is text-only (mood assist + optional sl2610-examples/gemma_translate). Point to docs/lab/07-WAVE-VISION-AND-GEMMA.md.
```

---

## Voice does not work but waving works

```
Gemy: wave works, no [ears] heard. Stale greeter or busy /dev/video0. Fix with cleanup-board.ps1, greeter speech-before-camera, --fps 5, -NoGemmaMood if frozen.
```

---

## Hung at listen_wait after speaking

```
Gemy log stops at [ears] listen_wait Moonshine listen_once. Explain gemy_stability listen timeout (60s), stuck guard, cleanup-board.ps1 restart.
```

---

## Camera photo is black

```
OV5647 photo black. Fix exposure/gain on /dev/v4l-subdev2 after stream starts in hat.py.
```

---

## Control Center / hub issues

```
coralboard-hub.ps1 or browser Control Center not starting Gemy. Check HubServer.ps1, Join-RobotPath in Repo.ps1, greet-demo.ps1 paths.
```

---

## Wrong mood / math wrong

```
Moonshine mis-hears or math quiz returns neutral. Explain _try_math_yes_no (plus, times, follow-up). Widen keyword lists in greeter.py.
```

---

## Start over

```
Full board reset from repo root: cleanup-board.ps1 — one PowerShell command.
```
