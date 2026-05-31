# Troubleshooting

## Voice does not work / no LED when I talk

### Symptom
Waving might work, but speaking does nothing. No `[ears] heard:` lines in terminal.

### Most common cause: stale process or wrong session
Another **`greeter.py`** instance or a leftover demo may hold the camera or mic path.

```powershell
powershell -ExecutionPolicy Bypass -File cleanup-board.ps1
```

Then launch **`greet-demo.ps1`** or Control Center → **Start Gemy — voice**.

Check:

```powershell
adb shell ps -ef | findstr greeter
adb shell fuser /dev/video0
```

### Speech model still loading
Wait until terminal shows:

```
[ears] listening (moods: ...)
```

First start: **10–20 seconds** for Moonshine. Gemma assist (if on) is capped at **5 s** per phrase; then neutral.

**Freeze debugging:** watch **`[diag]`** lines — last phase before hang (`listen_wait`, `gemma_assist`, `react_*`). Red **session heartbeat** should blink ~every 1.6 s.

### Hung at `listen_wait`
Moonshine can block up to **60 s**; stability then resets the mic. If stuck, run **`cleanup-board.ps1`** and restart. Try **`greet-demo.ps1 -NoGemmaMood`** to isolate NPU issues.

### Camera starving speech (2 CPU cores)
If `[ears] listening` appears but no transcripts under load:

- Keep `--fps` at **5** (default) or lower.
- Test mic-only: `greet-demo.ps1 -NoVision`

### Camera held by another process
```
ERROR: could not open camera /dev/video0
[vision] OFF (camera busy or missing). Voice still works.
```

Run **`cleanup-board.ps1`** or kill the PID from `adb shell fuser /dev/video0`.

---

## Buzzer stuck on loud

Emergency:

```bash
gpioset gpiochip0 6=1
python3 /home/root/hat.py buzzer off
```

Or Control Center → **Stop buzzer & reset board**.

Root cause: GPIO latch — use updated `hat.py` (always drives line HIGH in `finally`).

---

## Camera photo black / dark greeter vision

After stream starts, set exposure on subdev:

```bash
v4l2-ctl -d /dev/v4l-subdev2 --set-ctrl=exposure=740,analogue_gain=1023
```

Or run greeter with `--gain 600` in a brighter room.

---

## `adb` not found

```powershell
winget install Google.PlatformTools
```

Open a **new** terminal.

---

## `udhcpc: no lease`

```powershell
powershell -ExecutionPolicy Bypass -File install-ncm-signed.ps1
```

Then on board: `udhcpc -i usb0`

---

## Terminal shows heard text but wrong reaction

Check the transcript:

```
[ears] heard: '...' -> funny
```

Moonshine mis-hears words — extend keyword lists in `greeter.py`. Math: supports **plus**, **times**, and follow-up **“is it equal to …”** — see [08-GEMY-MOODS-AND-REACTIONS.md](08-GEMY-MOODS-AND-REACTIONS.md).

---

## Board frozen / red heartbeat stopped

1. **`cleanup-board.ps1`** or Control Center reset.
2. Restart with **`greet-demo.ps1 -NoGemmaMood`** (keywords only).
3. Do not use **`--gemma-mood-serial`** (disabled — NPU freeze).

See `.cursor/rules/coralboard-stability-first.mdc`.

---

## Joke heard but no rainbow

Push latest **`hat.py`** + **`greeter.py`**. Reactions must use **`hat.gemy_funny()`** (one GPIO lock, sequential sound + LED).

---

## Gemma returned weird mood / crash

Unknown labels map to **neutral** via `mood_for_reaction` / `resolve_reaction_kind`. Update from repo if crashes persist.

---

## Control Center does nothing

- Leave the PowerShell hub window open; browser at `http://127.0.0.1:8765/`
- Click **Refresh** — board must show connected
- Run directly: `powershell -ExecutionPolicy Bypass -File coralboard-hub.ps1`

---

## Quick diagnostic (instructor)

```powershell
adb shell ps -ef | findstr -i "greeter gemma"
adb shell fuser /dev/video0
adb shell tail -20 /home/root/gemy.log
```

Expected: one **`greeter.py`**, camera owned by that greeter or free.
