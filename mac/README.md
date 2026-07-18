# Gemy on a Mac

Use this folder to open **Gemy Control Center** on macOS and talk to a Coralboard over USB.

The Code Jam lab on **Windows** is still under [`windows/`](../windows/). This Mac path is for controlling and monitoring the board from a Mac.

---

## Which kind of board do you have?

Pick **one** path. You almost never need both.

### A) Brand-new board (no Gemy yet, or you want *this* lab’s Gemy)

Your board is empty of Gemy, or you’re happy to install the scripts from this repo.

1. Install ADB once (see [Setup](#setup-once) below).
2. Plug in USB-C. Wait ~20 seconds.
3. Open Control Center: `./mac/start-hub.sh`  
   (or double-click the Desktop shortcut from `./mac/make-shortcut.sh`)
4. Click **Update board from this repo** and confirm.  
   That copies this Mac’s Gemy scripts onto the board.
5. Click **Start Gemy — voice**. Wait for `[ears] listening` in the Terminal window.
6. Say **“Gemy”**.

**Note:** The board still needs the usual Coral speech stack (`sl2610-examples` venv). “Update board” installs *Gemy’s* Python files; it does not flash a blank factory board from zero. If **Speech stack** stays red in the UI, follow the Coralboard / lab setup docs first.

### B) Advanced board (Gemy already newer / customized)

Your Coralboard already runs a better or custom Gemy than this repo. **Do not overwrite it.**

1. Install ADB once (see [Setup](#setup-once) below).
2. Plug in USB-C. Wait ~20 seconds.
3. Open Control Center: `./mac/start-hub.sh`
4. **Skip** **Update board from this repo**.
5. Use **Refresh**, **board log**, and **Start Gemy** to monitor and run what’s *already* on the board.

Refresh and Start never copy files by themselves. Only the **Update board** button (after you confirm) overwrites the board.

---

## Setup (once)

```bash
brew install android-platform-tools
adb devices
```

After you plug in USB-C you should see a line ending in `device` (often `grinn-astra-…`).

Optional Desktop icon:

```bash
./mac/make-shortcut.sh
```

Double-click **Gemy Control Center**. If macOS blocks it: right-click → **Open** → **Open**. Keep the Terminal window open while you use the browser UI.

---

## Everyday controls

| Want to… | Do this |
|----------|---------|
| Open the UI | `./mac/start-hub.sh` or Desktop shortcut |
| Install / refresh lab Gemy onto the board | **Update board from this repo** (confirm) |
| Run Gemy without changing board files | **Start Gemy — voice** |
| See what the board is doing | **Board log** / **Reload log** |
| Stop beeps / reset | **Stop buzzer & reset board** |
| Recover after a freeze | `./mac/recover-board.sh` |

CLI alternatives (same rules — no push unless you ask):

```bash
./mac/start-gemy.sh --no-vision     # start board’s existing greeter
./mac/cleanup-board.sh
./mac/recover-board.sh
./mac/start-gemy.sh --allow-push    # same as Update board, then start
```

---

## Quick reminder

| | New / lab board | Advanced board |
|--|-----------------|----------------|
| **Update board from this repo** | Yes — once (or when you want this repo’s scripts) | **No** |
| **Start Gemy** | After update | Anytime |
| **Refresh** | Safe (does not push) | Safe (does not push) |

---

## Layout

```
mac/
  start-hub.sh          # Control Center (browser)
  make-shortcut.sh      # Desktop icon
  start-gemy.sh         # start greeter (no push by default)
  cleanup-board.sh
  recover-board.sh
  hub/                  # UI + local server
```

## Windows

Full jam deploy lives under `windows/`. If the board is ahead of this repo on Windows too:

```powershell
.\greet-demo.ps1 -NoPush
# or before the hub:
$env:GEMY_NO_PUSH = "1"
```
