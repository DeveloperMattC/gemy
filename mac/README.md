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

**Speech stack required:** “Update board” only copies Gemy’s Python files. Voice needs Synaptics `sl2610-examples` + its `.venv` on the board. If **Speech stack** is red in the UI, or the board log says `…/sl2610-examples/.venv/bin/python3: No such file or directory`, do [Speech stack missing](#speech-stack-missing-on-the-board) below first.

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

`brew` is for your **Mac only** (installs `adb`). Do **not** run Homebrew on the Coralboard — it is Yocto Linux, not macOS.

After you plug in USB-C you should see a line ending in `device` (often `grinn-astra-…`).

Open a shell **on the board** anytime:

```bash
adb shell
# you should see root@grinn-astra-…:/#
ls /home/root
exit
```

Optional Desktop icon:

```bash
./mac/make-shortcut.sh
```

Double-click **Gemy Control Center**. If macOS blocks it: right-click → **Open** → **Open**. Keep the Terminal window open while you use the browser UI.

---

## Speech stack missing on the board

**Symptom**

- Control Center **Speech stack** stays red (“Need sl2610-examples on board”).
- Board log: `/home/root/sl2610-examples/.venv/bin/python3: No such file or directory`.
- HAT beep works (`hat.py beep`), but **Start Gemy — voice** fails.

**Check**

```bash
adb shell "test -x /home/root/sl2610-examples/.venv/bin/python3 && echo OK || echo MISSING"
adb shell "ls /home/root/sl2610-examples 2>&1 | head -n 5"
```

If that prints `MISSING` / `No such file`, install the Synaptics examples stack. Gemy’s **Update board** button will not fix this by itself.

### Install speech stack from your Mac (works without board internet)

Do this on the Mac (repo root or any temp dir). The board only needs USB/`adb`.

1. **Clone Synaptics examples** (includes an offline `wheelhouse/` for aarch64):

```bash
mkdir -p /tmp/gemy-board-setup && cd /tmp/gemy-board-setup
git clone --depth 1 https://github.com/synaptics-astra-demos/sl2610-examples.git
```

2. **Download Moonshine models on the Mac**, then write the small manifest the loader expects:

```bash
cd /tmp/gemy-board-setup/sl2610-examples
python3 -m pip install --user 'huggingface_hub==0.31.4'
python3 - <<'PY'
from pathlib import Path
from huggingface_hub import snapshot_download
import json
from datetime import datetime, timezone

dest = Path("models/Synaptics/moonshine-tiny-bf16-torq")
snapshot_download(repo_id="Synaptics/moonshine-tiny-bf16-torq", local_dir=str(dest))
files = ["encoder.vmfb", "decoder.vmfb", "decoder_token_embeddings.npy", "tokenizer.json"]
for name in files:
    assert (dest / name).exists(), name
(dest / ".manifest.json").write_text(json.dumps({
    "repo_id": "Synaptics/moonshine-tiny-bf16-torq",
    "files": files,
    "timestamp": datetime.now(timezone.utc).isoformat(),
}, indent=2))
print("models ok")
PY
```

3. **Push the tree to the board** (use `COPYFILE_DISABLE=1` so macOS does not add `._*` junk files):

```bash
cd /tmp/gemy-board-setup
COPYFILE_DISABLE=1 tar --exclude='.git' -cf sl2610-examples.tar sl2610-examples
adb push sl2610-examples.tar /home/root/sl2610-examples.tar
adb shell 'cd /home/root && rm -rf sl2610-examples && tar -xf sl2610-examples.tar && rm sl2610-examples.tar'
# Extra cleanup if you already pushed without COPYFILE_DISABLE:
adb shell 'find /home/root/sl2610-examples -name "._*" -exec rm -f {} \;'
```

4. **Create the venv and install deps offline** (from the board’s `wheelhouse/`):

```bash
adb shell 'set -e
cd /home/root/sl2610-examples
python3 -m venv .venv --system-site-packages
. .venv/bin/activate
cd speech_to_text
pip install --no-index --find-links=../wheelhouse -r requirements.txt
cd ..
./configs/install_portaudio.sh
test -x .venv/bin/python3 && echo SPEECH_STACK_READY
'
```

5. **Patch Moonshine embeddings load** (macOS `._*` files and numpy void/`bf16` `.npy` can break `np.load`; skip hidden names and allow pickle for that file):

```bash
adb shell 'python3 - <<'"'"'PY'"'"'
from pathlib import Path
p = Path("/home/root/sl2610-examples/utils/moonshine/runner.py")
text = p.read_text()
old = """    def _load_embeddings(model_dir: Path) -> np.ndarray | None:
        paths = list(model_dir.glob(\"*token_embeddings.npy\"))
        if not paths:
            return None
        arr = np.load(paths[0])
"""
new = """    def _load_embeddings(model_dir: Path) -> np.ndarray | None:
        paths = [
            path for path in model_dir.glob(\"*token_embeddings.npy\")
            if not path.name.startswith(\"._\")
        ]
        if not paths:
            return None
        arr = np.load(paths[0], allow_pickle=True)
"""
if old not in text:
    raise SystemExit("already patched or upstream changed — open runner.py and fix _load_embeddings by hand")
p.write_text(text.replace(old, new, 1))
print("patched")
PY'
```

6. **Verify, then start Gemy**:

```bash
adb shell "test -x /home/root/sl2610-examples/.venv/bin/python3 && echo OK"
# From this repo:
./mac/start-gemy.sh --no-vision
# Wait for: [ears] listening
```

Or refresh Control Center — **Speech stack** should turn green — then **Start Gemy — voice**.

### Optional: board internet via Mac (for `git clone` / `pip` on the board)

If you prefer to install **on the board** instead of pushing from the Mac:

1. **System Settings → General → Sharing → Internet Sharing**
2. Share from: **Wi-Fi** (or your internet interface)
3. To devices using: **NCM Device** (not Thunderbolt / random USB Ethernet adapters)
4. Turn Internet Sharing **On**
5. On the board:

```bash
adb shell
udhcpc -i usb0
ping -c 2 8.8.8.8
cd /home/root
git clone https://github.com/synaptics-astra-demos/sl2610-examples.git
cd sl2610-examples
python3 -m venv .venv --system-site-packages
source .venv/bin/activate
pip install -r requirements.txt
cd speech_to_text && pip install -r requirements.txt && python setup_demo.py
cd .. && ./configs/install_portaudio.sh
```

If `udhcpc` never gets a lease, Sharing is usually pointed at the wrong interface — check **NCM Device** again.

### After install — what success looks like

| Check | Expect |
|-------|--------|
| `adb shell test -x /home/root/sl2610-examples/.venv/bin/python3` | exit 0 / `OK` |
| Control Center **Speech stack** | green |
| Start Gemy | `[ears] listening` in log / Terminal |
| Say “Hello” | greet reaction (beep / lights) |

Still stuck: `./mac/recover-board.sh`, then `./mac/start-gemy.sh --no-vision`, then `adb shell tail -80 /home/root/gemy.log`.

---

## Everyday controls

| Want to… | Do this |
|----------|---------|
| Open the UI | `./mac/start-hub.sh` or Desktop shortcut |
| Install / refresh lab Gemy onto the board | **Update board from this repo** (confirm) |
| Run Gemy without changing board files | **Start Gemy — voice** |
| Fix red **Speech stack** / missing `.venv` | [Speech stack missing](#speech-stack-missing-on-the-board) |
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
| **Speech stack** (`sl2610-examples` venv) | Required before voice works | Usually already present |
| **Start Gemy** | After update (+ speech stack if needed) | Anytime |
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
