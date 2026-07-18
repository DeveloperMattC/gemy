# Gemy on macOS — control & monitor (no overwrite)

The **board** runs Linux Python (`/home/root/greeter.py`). This folder is the **Mac host** side: Control Center UI + shell helpers over USB ADB.

**Windows lab path stays in `windows/`.** Use that on a Windows PC for Code Jam / full deploy.

## Critical: board code protection

Your Coralboard may have a newer Gemy than this repo. Mac helpers **do not `adb push` by default**.

| Action | Pushes repo → board? |
|--------|----------------------|
| `./mac/start-hub.sh` | No |
| Refresh in Control Center | No |
| Start Gemy buttons | No (runs board’s existing greeter) |
| `./mac/start-gemy.sh` | No |
| `./mac/cleanup-board.sh` / `recover-board.sh` | No |
| `./mac/start-gemy.sh --allow-push` or hub `--allow-push` | **Yes — overwrites** |

## Setup (once)

```bash
brew install android-platform-tools
adb devices   # should show grinn-astra-… device after USB-C plug-in
```

## Control Center (browser UI)

```bash
./mac/start-hub.sh
```

Opens `http://127.0.0.1:8765/` — status, start/stop, board log, processes. Keep that terminal open.

### Desktop shortcut

```bash
./mac/make-shortcut.sh
```

Puts **Gemy Control Center.app** (and a `.command` fallback) on your Desktop. Double-click to open the hub + browser. If macOS blocks it the first time: right-click → **Open** → **Open**.

## CLI options

```bash
./mac/start-gemy.sh                 # voice+camera, board moods, no push
./mac/start-gemy.sh --no-vision     # voice only
./mac/start-gemy.sh --no-gemma-mood # force keyword-only flags
./mac/cleanup-board.sh              # stop demos, buzzer/LEDs off
./mac/recover-board.sh              # after a hang (no push)
```

Tail log without the UI:

```bash
adb shell tail -f /home/root/gemy.log
```

## Layout

```
mac/
  start-hub.sh          # Control Center
  start-gemy.sh         # start board greeter (no push)
  cleanup-board.sh
  recover-board.sh
  hub/hub_server.py     # local HTTP API + UI
  hub/www/              # Mac-tuned Control Center pages
```

## Windows parity

On Windows, full demos still live under `windows/`. Prefer:

```powershell
.\greet-demo.ps1 -NoPush
```

when the board is ahead of this repo (same “don’t overwrite” idea).
