# Run Gemy without a PC

## Short answer

| Question | Answer |
|----------|--------|
| Does Gemy work without a PC? | **Yes**, after a one-time install while USB is connected. |
| Does it start on its own when powered? | **Only if** boot autostart is enabled (`GemyFeatures.ps1` → `$GemyBootAutostart = $true` + `install-gemy-standalone.ps1`). **Default in repo: autostart OFF.** |
| Does it need internet? | **No** at runtime if speech models are already on the board. |
| Is there a board button? | **Yes** — **USER** toggles Gemy on/off (watcher service). |

## Boot vs PC start

| Mode | Typical flags | Gemma | Vision |
|------|----------------|-------|--------|
| **PC Control Center** | `--gemma-mood` (default) | Assist when unclear | Optional |
| **Boot** (`gemy-boot.sh`) | `--no-gemma-mood --no-vision` | Off (stable) | Off |

Boot is **voice-only and keyword moods** so the 2 GB board stays stable. Use the PC for camera + Gemma assist + full intro beep.

## One-time install (PC connected)

```powershell
cd path\to\robot
powershell -ExecutionPolicy Bypass -File install-gemy-standalone.ps1
```

Pushes `greeter.py`, `hat.py`, `gemma_mood*.py`, `gemy-watcher.py`, `gemy-boot.sh`, and systemd units.

## Daily use (no PC)

1. Power the board (USB charger or power bank).
2. If autostart enabled: wait ~30–90 s for `[ears] listening` (check `/home/root/gemy.log`).
3. Say **Gemy**, jokes, hello, etc.
4. Press **USER** to stop/start (if watcher enabled).

## PC session vs standalone

| Mode | How to start |
|------|----------------|
| **With PC** | Gemy Control Center → **Start Gemy** |
| **Standalone** | `install-gemy-standalone.ps1` once + power (if autostart on) |

## Troubleshooting

- **Nothing on boot:** `adb shell systemctl status gemy-autostart` and `tail -50 /home/root/gemy.log`
- **USER button does nothing:** `adb shell systemctl status gemy-watcher`
- **No voice:** PC → Control Center → Refresh + Start Gemy
- **Freeze on boot:** ensure `gemy-boot.sh` includes `--no-gemma-mood` (default in repo)

Moods reference: [08-GEMY-MOODS-AND-REACTIONS.md](08-GEMY-MOODS-AND-REACTIONS.md).
