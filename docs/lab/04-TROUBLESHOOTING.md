# Troubleshooting

## Voice does not work / no LED when I talk

### Symptom
Waving might work, but speaking does nothing. No `[ears] heard:` lines in terminal.

### Most common cause: wrong demo running
**`wave_detect.py` has no microphone.** Check:

```powershell
adb shell ps -ef | findstr wave_detect
adb shell fuser /dev/video0
```

Fix:

```powershell
adb shell pkill -9 -f wave_detect.py
adb shell pkill -9 -f /home/root/greeter.py
```

Then launch **`greet-demo.ps1`**, not `wave-demo.ps1`.

### Speech model still loading
Wait until terminal shows:

```
[ears] on. Greet ...
```

First start: **10–20 seconds** after vision starts.

### Camera starving speech (2 CPU cores)
If `[ears] on` appears but no transcripts under load:

- Do not raise `--fps` above ~10.
- Test mic-only: `greet-demo.ps1 -NoVision`
- Confirm Gemma voice demo works alone (`connect-gemma.ps1`)

### Camera held by another process
```
ERROR: could not open camera /dev/video0
[vision] OFF (camera busy or missing). Voice still works.
```

Kill holder: `adb shell fuser /dev/video0` then kill that PID.

---

## Buzzer stuck on loud

Emergency:

```bash
gpioset gpiochip0 6=1
python3 /home/root/hat.py buzzer off
```

Root cause: GPIO latch — always use updated `hat.py` that drives line HIGH in `finally`.

---

## Camera photo black / dark greeter vision

After stream starts, set exposure on subdev:

```bash
v4l2-ctl -d /dev/v4l-subdev2 --set-ctrl=exposure=740,analogue_gain=1023
```

Or run greeter with `--gain 600` in brighter room.

---

## `adb` not found

Install Platform Tools, **open new terminal**:

```powershell
winget install Google.PlatformTools
```

---

## `udhcpc: no lease`

Host NCM/ICS not active. Run as admin:

```powershell
powershell -ExecutionPolicy Bypass -File install-ncm-signed.ps1
```

Then on board: `udhcpc -i usb0`

---

## Terminal shows heard text but wrong reaction

Moonshine mis-hears words. Check actual transcript in:

```
[ears] heard: '...' -> funny
```

Extend `FUNNY` / `NICE` / `MEAN` sets in `greeter.py` if needed.

---

## Hub button does nothing

- Click **Refresh connection** — board must show connected.
- Run hub script directly:

```powershell
powershell -ExecutionPolicy Bypass -File coralboard-hub.ps1
```

---

## WebRTC stream fails

- Port **8090** serves viewer (8080 used by `swupdate`).
- Signalling on **8443**.
- See `webrtc-view.ps1` and `webrtc-stream.sh status`.

---

## Quick diagnostic script (instructor)

```powershell
adb shell ps -ef | findstr -i "greeter wave_detect gemma"
adb shell fuser /dev/video0
adb shell /home/root/sl2610-examples/.venv/bin/python3 -c "import sounddevice as sd; print(sd.query_devices())"
```

Expected for voice lab: **`greeter.py` running**, camera free or owned by that greeter only, ALSA devices listed.
