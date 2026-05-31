# Troubleshooting

## Board frozen / cannot talk to Gemy (start here)

### Symptom
No `[ears] heard`, red LED solid, buzzer stuck, or PowerShell stopped updating. `adb devices` may be **empty**.

### Recovery (in order)

1. **Unplug USB-C** from the PC, wait **15–20 seconds**, plug back in.
2. Confirm: `adb devices` shows `grinn-astra-2619-coral    device`
3. From repo root:

```powershell
.\recover-board.ps1
```

(`cleanup-board.ps1 -Quick` is the same fast path; full cleanup is slower.)

4. Restart **without Gemma** until voice works:

```powershell
.\greet-demo.ps1 -NoGemmaMood
```

5. When stable, push latest code and try Gemma again:

```powershell
.\greet-demo.ps1
```

### If buzzer will not stop

```powershell
adb shell "gpioset gpiochip0 6=1; python3 /home/root/hat.py force-off"
```

### What usually caused it

- First **Gemma** load on the NPU (1–3 min) while the ears thread waits — feels frozen; heartbeat may still blink in logs.
- STT fragment like **`Is the sky`** (no color word) used to trigger that load — fixed in latest `gemy_qa.py` + `greeter.py`.
- Old builds **killed** the Gemma worker every phrase → repeated long loads.

See [LEARNINGS.md](LEARNINGS.md) for the full lesson summary.

### Read the trace log (after a freeze)

`greet-demo.ps1` appends to **`/home/root/gemy.log`**. Look for **`[trace]`** lines (always on unless `GEMY_TRACE=0`):

```powershell
adb shell tail -100 /home/root/gemy.log
```

| Last `[trace]` line | Likely cause |
|---------------------|----------------|
| `phase listen_wait` + `listen_wait_progress` climbing | Moonshine/mic blocked (NPU or hung VAD) |
| `npu_busy_before_listen` / `ensure_npu_*` | Gemma preload vs ears fighting for NPU |
| `prewarm_P_start` then freeze | Gemma loading on NPU |
| `classify_C_start` / `classify_C_hung` | Gemma assist blocked ears too long |
| `stuck_detected` | Stuck guard fired — check line after it for `stuck_recovered` |
| `watchdog` with `prewarm=1` while you spoke | Preload not cancelled before listen |

Every **30s** you should see `[trace] watchdog` with `phase=`, `npu=`, `prewarm=`, `reacting=`. If those stop, the process hung or adb dropped.

Extra detail: `[diag]` lines when started with `--pc-start` (Control Center / greet-demo default).

---

## Voice does not work / no LED when I talk

### Symptom
Waving might work, but speaking does nothing. No `[ears] heard:` lines in terminal.

### Most common cause: stale process or wrong session
Another **`greeter.py`** instance or a leftover demo may hold the camera or mic path.

```powershell
.\recover-board.ps1
# or: .\cleanup-board.ps1
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

First start: **10–20 seconds** for Moonshine. First Gemma check can take **up to ~90 s** (model load); later checks ~**12 s** max, then neutral.

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
4. Grep the log for **`[stability] STUCK`**, **`listen_once hung`**, or missing **`heartbeat pulse`** lines.

**Hardware liveness smoke (adb):** runs greeter ~45s, counts **`[stability] heartbeat pulse N`** lines, and checks **`/proc/meminfo`** MemAvailable + greeter RSS:

```powershell
powershell -ExecutionPolicy Bypass -File windows\setup\gemy-heartbeat-smoke.ps1
# or full PC suite + liveness:
powershell -ExecutionPolicy Bypass -File windows\setup\test-gemy.ps1 -HeartbeatSmoke
```

Default smoke uses **`--no-speech --no-gemma-mood`** (heartbeat only, no NPU/mic). Add **`-WithGemma`** or **`-WithSpeech`** to stress heavier paths.

See `.cursor/rules/coralboard-stability-first.mdc`.

---

## Joke heard but no rainbow

Push latest **`hat.py`** + **`greeter.py`**. Reactions must use **`hat.gemy_funny()`** (one GPIO lock, sequential sound + LED).

---

## Gemma returned weird mood / crash

Unknown labels map to **neutral** via `mood_for_reaction` / `resolve_reaction_kind`. Update from repo if crashes persist.

### Board “frozen” after a short question (e.g. “is the sky…”)

- **Looks like:** log shows `text='Is the sky'` (no color word) then `[gemma] first mood check` / NPU load.
- **Cause:** STT cut the phrase; old code still loaded Gemma on the fragment.
- **Fix:** Push latest `gemy_qa.py` + `greeter.py` — incomplete stubs → **neutral**, no Gemma. Say the full line: **“Is the sky green”** → two red beeps (**no**) without Gemma.
- **Verify:** log shows `incomplete question (heard fragment) -> neutral, skip Gemma`.

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
