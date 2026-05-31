# Run Gemy without a PC

## Short answer

| Question | Answer |
|----------|--------|
| Does Gemy work without a PC? | **Yes**, after a one-time install while USB is connected. |
| Does it need internet? | **No** at runtime, if speech models are already on the board. |
| Is there a board button? | **Yes** — the Coralboard **USER** button (Enter Button) toggles Gemy on/off. |

The Sensor HAT does **not** add a separate app button; it has **reset** (reboots the board).

## Physical controls

| Control | Where | What it does for Gemy |
|---------|--------|------------------------|
| **USER button** | On the Coralboard (Enter Button) | Short press **starts/stops** Gemy (after `install-gemy-standalone.ps1`) |
| **RESET** | Board or Sensor HAT | Reboots Linux — stops Gemy until you press USER again (or autostart) |
| Boot switch | Board | eMMC vs SD — not related to Gemy |

## One-time install (PC connected)

```powershell
cd path\to\gemy-coralboard-lab
powershell -ExecutionPolicy Bypass -File install-gemy-standalone.ps1
```

This pushes `greeter.py`, `hat.py`, `gemy-watcher.py` and enables `gemy-watcher.service`.

## Daily use (no PC)

1. Power the board (USB power bank or charger).
2. Wait ~30 s for Linux to boot.
3. **Press USER** → signature beep → talk to Gemy or wave.
4. **Press USER again** → Gemy stops.

## Optional: autostart on boot

```powershell
powershell -ExecutionPolicy Bypass -File install-gemy-standalone.ps1 -AutostartOnBoot
```

Gemy runs as soon as the board finishes booting; USER button still toggles off/on.

## Troubleshooting

- **Button does nothing:** `adb shell systemctl status gemy-watcher` (only when PC attached for debug).
- **No voice:** run `cleanup-board.ps1` once from PC; ensure `wave_detect.py` is not running.
- **Models missing offline:** connect PC once, run Gemma voice demo or greeter to cache models, then reinstall standalone.
