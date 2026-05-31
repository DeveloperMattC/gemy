# Coralboard: Connect, Share Internet & Run AI Demos

A simple, follow-along guide for your setup (Windows 10 host + Coralboard over USB-C).

Everything below has been tested and works on this machine.

> **Repo layout:** scripts live in `board/` (on-device), `windows/` (PC launchers),
> `drivers/`, and `docs/`. From the repo root you can still run `.\greet-demo.ps1`,
> `.\coralboard-hub.ps1`, etc. — those are shortcuts to `windows\…`.

---

## What's already set up (one-time, done)

- **ADB** (Android Platform-Tools) is installed on Windows.
- The **UsbNcm Host Device** network driver is installed and bound to the board
  (this is what lets the board use your PC's internet over USB).
- The examples repo is cloned on the board at `/home/root/sl2610-examples`
  with its Python virtual environment (`.venv`) and dependencies installed.

You normally only need the **"Every time"** steps below.

---

## Easiest way: Gemy Control Center

Double-click **"Gemy Control Center"** on your Windows desktop (`windows\hub\make-shortcut.ps1` to create it).

A small PowerShell window starts a **local web dashboard** and opens it in your browser (`http://127.0.0.1:8765/`). Leave that window open while you use the dashboard; close it to stop the server.

On load it **checks everything automatically**:

- **System status** — ADB, USB driver, board connection, scripts, speech stack, boot autostart  
- **Sync** — latest Gemy scripts pushed when the board is connected  
- **Board log** — tail of `/home/root/gemy.log` for greeter output  
- **Toasts** — each action reports success or failure in the page  

Actions:

- **Start Gemy — voice only** (recommended)  
- **Start Gemy — with camera**  
- **HAT test panel** — buzzer, LEDs, camera  
- **Stop buzzer and reset board**  

Other Synaptics demos live in `/home/root/sl2610-examples` on the board if installed.

**Gemy is one click:** it pushes `greeter.py`, `hat.py`, `gemma_mood.py`, `gemma_mood_worker.py`, `gemy_stability.py`, and `gemy_diag.py`,
runs cleanup (stops old greeter / legacy demos, frees the camera), then starts
Gemy in a terminal. Wait until you see **`[ears] listening`** (~15–30 s first time).
Use **Stop buzzer & reset board** if something is stuck after you stop Gemy.

---

## Every time: get online + open a shell

### 1. Plug in the board
Connect the Coralboard to your PC with the USB-C cable. Wait ~20s for it to boot.

### 2. (Windows) Re-arm internet sharing
Windows tends to drop Internet Connection Sharing after a reboot. Re-run the setup
script to re-enable it (this does NOT reinstall anything, it just re-arms sharing):

```powershell
powershell -ExecutionPolicy Bypass -File install-ncm-signed.ps1
```

> A UAC prompt will pop up — click **Yes**.
> Tip: if internet already works on the board, you can skip this step.

### 3. Open a shell on the board
In any terminal (Cursor terminal, PowerShell, etc.):

```powershell
adb shell
```

You should land at a `root@...#` prompt on the board.

> If `adb` isn't recognized, open a **new** terminal (so it picks up the PATH),
> or close/reopen Cursor.

### 4. (On the board) Get an IP via DHCP

```bash
udhcpc -i usb0
```

Expected: `lease of 192.168.137.xx obtained from 192.168.137.1`.

### 5. (On the board) Confirm internet

```bash
ping -c 2 8.8.8.8        # should get replies
ping -c 2 github.com     # confirms DNS works too
```

> Note: pinging the host `192.168.137.1` may time out (Windows firewall blocks it).
> That's fine — what matters is that `8.8.8.8` and `github.com` reply.

---

## Run a demo

All demos live in `/home/root/sl2610-examples`. First, activate the Python
environment (do this once per shell session):

```bash
cd /home/root/sl2610-examples
source .venv/bin/activate
```

### Quickest demo — Image Classification (headless, no camera/display)

```bash
cd Image_classification
python3 classification.py \
  --model ../models/mbv2.vmfb \
  --image ../samples/cat.jpg \
  --labels labels.json \
  --device torq
```

Expected output (runs on the Coral NPU in ~7 ms):

```text
[2/4] Running model on board...
Time: 6.983ms
[4/4] Classification Results:
  1. Persian cat : 0.476562
  ...
Top Prediction: Persian cat
```

A result image is saved on the board at
`/home/root/sl2610-examples/Image_classification/output_classification.jpg`.

You can pull it to your PC (from a **Windows** terminal, not the board shell):

```powershell
adb pull /home/root/sl2610-examples/Image_classification/output_classification.jpg .\output_classification.jpg
```

Try your own image: `adb push myphoto.jpg /home/root/` then point `--image` at it.

---

## Other demos

Each demo folder has its own `README.md` with exact commands. From the board:

```bash
cat /home/root/sl2610-examples/<DemoFolder>/README.md
```

| Demo | Folder | Needs camera? | Needs mic? | Extra setup |
|------|--------|---------------|-----------|-------------|
| Image classification | `Image_classification` | No | No | None (works now) |
| Object detection | `Object_detection` | Yes (sensor hat cam) | No | — |
| Gemma translate | `gemma_translate` | No | Yes (voice) | model + PortAudio (DONE) |
| Speech to text | `speech_to_text` | No | Yes | PortAudio (see below) |
| Function calling | `Function_calling` | No | Yes (voice) | PortAudio |
| Jellectronica | `jellectronica` | No | Yes | PortAudio |

---

## Gemma 3 translation demo (on board — optional)

> **Not used for Gemy or wave detection.** Waving uses OpenCV in `greeter.py` only.
> Map of all “brains”: [docs/lab/07-WAVE-VISION-AND-GEMMA.md](lab/07-WAVE-VISION-AND-GEMMA.md).

Translates English → Spanish/French/Italian using **Gemma 3 270M** on the NPU.
Prompts and CLI live **on the board** (not in this repo):

```
/home/root/sl2610-examples/gemma_translate/
  translation.py
  cli_translate.py
  common_args.py
```

### Quick test (adb shell)

```bash
cd /home/root/sl2610-examples && source .venv/bin/activate
cd gemma_translate
python3 cli_translate.py
```

Pick the HAT mic (usually device `0`), choose a language, speak English.

> To add languages, edit `common_args.py` on the board.
> Switching demos may change `torq-runtime` versions — reinstall demo `requirements.txt` if another NPU demo breaks.

---

## Custom sensor-HAT demo: `hat.py` (buzzer / LEDs / camera)

A simple script at `/home/root/hat.py` controls the HAT hardware with one-line
commands. Buzzer and LED commands work with any `python3`; the camera needs the
venv (for OpenCV).

```bash
cd /home/root

# Buzzer  (it's an ACTIVE buzzer = one fixed pitch; patterns vary the rhythm)
python3 hat.py beep             # one short beep
python3 hat.py beep 3           # three beeps
python3 hat.py buzz 800         # one 800 ms tone
python3 hat.py siren            # warbling siren
python3 hat.py r2d2             # R2D2-style chatter
python3 hat.py warble           # fast two-length warble
python3 hat.py chirp            # quick chirps
python3 hat.py alarm            # slow insistent alarm
python3 hat.py sos              # morse SOS
python3 hat.py buzzer off       # force buzzer off

# Note: the buzzer GPIO LATCHES its last value, so hat.py always drives the line
# OFF at the end of every pattern (no more "stuck on"). There is no PWM on the
# buzzer, so pitch can't change -- only the on/off rhythm.

# LEDs  (red / green / blue / all)
python3 hat.py led green on
python3 hat.py led all off
python3 hat.py blink blue 5
python3 hat.py rainbow

# Camera (use the venv python for OpenCV)
/home/root/sl2610-examples/.venv/bin/python3 hat.py photo /home/root/hat_photo.jpg
```

Pull a photo to your PC to view it (from a **Windows** terminal):

```powershell
adb pull /home/root/hat_photo.jpg .\hat_photo.jpg
```

You can also use it from a Python prompt:

```python
import hat
hat.beep(2)
hat.led("green", True)
hat.rainbow()
hat.photo("/home/root/pic.jpg")
```

### HAT test panel (point-and-click GUI)

Instead of typing commands, open the control panel from a **Windows** terminal:

```powershell
powershell -ExecutionPolicy Bypass -File hat-gui.ps1
```

It runs `hat.py` on the board over `adb` and gives you buttons for:
- **Buzzer**: Beep, Beep x3, Tone (adjustable ms), Siren, and a red **STOP** (force off).
- **LEDs**: Red / Green / Blue toggle buttons (light up when on), All ON/OFF, Blink, Rainbow.
- **Camera**: Take Photo (adjustable gain), shows the captured image inline, and "Open in viewer".

The photo is captured with the venv Python (OpenCV), pulled to your PC, and
displayed in the window.

Camera notes (important):
- The OV5647 sensor boots in **manual exposure with low gain**, so a naive
  capture is **black**. `hat.py photo` fixes this by starting the stream first,
  then setting manual exposure + high gain on the sensor control node
  `/dev/v4l-subdev2` (the only point where the controls take effect).
- If a well-lit scene looks too bright/noisy, lower the gain:
  `... hat.py photo /home/root/pic.jpg --gain 400`
  (`--gain` 16-1023, `--exposure` 4-740).

Hardware notes:
- Buzzer = GPIO line `BUZZERn` (active-low; the script handles that).
- LEDs = `/sys/class/leds/{red,green,blue}:status` (on=1, off=0).
- Camera = `/dev/video0` (OV5647), exposure/gain on `/dev/v4l-subdev2`.

> Emergency buzzer off (if it ever gets stuck on):
> `adb shell 'gpioset gpiochip0 6=1'`

---

### One-time setup some demos need

Run these **on the board** (from the repo root) before mic/NPU-heavy demos:

```bash
cd /home/root/sl2610-examples
./configs/install_portaudio.sh   # microphone support (no reboot)
./configs/patch_kernel.sh        # updates NPU kernel module (REBOOT after)
```

> `patch_kernel.sh` requires a reboot to take effect. After reboot, redo the
> "Every time" steps (re-arm ICS + `udhcpc -i usb0`).

### Headless vs display
Most demos have a headless and a display version. For display output, the demo
README will tell you to set:

```bash
export XDG_RUNTIME_DIR=/var/run/user/0
export WAYLAND_DISPLAY=wayland-1
```
(Only needed if you have a MIPI display attached.)

---

## Transferring files (no network needed)

### Easy way: adb push to `samples/`

Use **`adb push`** from Windows (no separate GUI script in this repo):

```powershell
adb push .\myphoto.jpg /home/root/sl2610-examples/samples/
```

Then classify from the board shell (replace the filename):

```bash
python3 classification.py --model ../models/mbv2.vmfb --image ../samples/YOURFILE.jpg --labels labels.json --device torq
```

### Manual way: command line

From a **Windows** terminal:

```powershell
adb push  <local-file>  /home/root/sl2610-examples/samples/   # PC  -> board (samples)
adb push  <local-file>  /home/root/                           # PC  -> board (home)
adb pull  /home/root/<file>  "C:\path\on\pc"                  # board -> PC
```

---

## Getting started with the board's Linux

**There is only one Linux here — it runs on the Coralboard itself, not on the
sensor HAT.** The HAT is just a peripheral board (mic, buzzer, LEDs, camera)
wired into the Coralboard's GPIO/I2C/CSI. Every `adb shell` already drops you
into this Linux as the `root` user. There's nothing separate to "install" or
"boot" on the HAT.

What it is:
- **Distro:** Yocto / Poky **5.0.9 "scarthgap"** (Synaptics Astra SDK OOBE image)
- **Kernel:** Linux **6.12.62**, `aarch64` (64-bit Arm)
- **CPU/RAM:** 2 cores, ~1.9 GB RAM
- **Init/network:** `systemd`, `NetworkManager`, `dnsmasq` (the board's USB end
  also runs a DHCP server for `usb0`)
- **Desktop:** `weston` (Wayland) is installed but **headless by default** — you
  drive it over USB with `adb`. A display can be enabled via U-boot dtbo
  overlays (see `coral-boardguide.md`).

Storage layout (eMMC — there's no SD/USB boot):

```bash
df -h
# /dev/mmcblk0p14  ->  /        rootfs (~2.3G, gets full — don't fill it)
# /dev/mmcblk0p18  ->  /home    big partition (~8.7G free) — put your files here
```

> Tip: keep your projects and large files under `/home/root/...` (on the roomy
> `/home` partition). The root filesystem `/` is small and ~95% full.

### Open a shell

```powershell
adb shell                 # interactive root shell on the board
adb shell 'uname -a'      # run one command and exit
```

### First things to try

```bash
whoami                    # -> root
cat /etc/os-release       # distro/version
uname -a                  # kernel + arch
free -h                   # memory
df -h                     # disk
ip -brief addr            # network interfaces (usb0 = link to your PC)
systemctl --type=service --state=running   # what's running
ls /home/root             # your stuff: sl2610-examples, hat.py, demos/
```

### Everyday Linux on the board

- **Shell:** `bash` is available (`/bin/bash`); many core utils are **BusyBox**,
  so some flags differ from desktop Linux (e.g. `head -2` style options may be
  missing — use `head -n 2`).
- **Editor:** `vi` is present. For quick edits it's easier to `adb pull` a file,
  edit it on your PC, and `adb push` it back.
- **Python:** `python3` is **3.12.9**. The demos use a venv at
  `/home/root/sl2610-examples/.venv` (has OpenCV, the NPU runtime, etc.).
- **Packages:** this is a Yocto image, not Debian/Ubuntu — treat the rootfs as
  mostly read-only/fixed. Don't rely on installing system packages; install
  Python deps into a venv instead (`python3 -m venv` + `pip`).
- **Internet:** the board reaches the internet through your PC over `usb0`
  (see "Share your PC's internet" above) — `udhcpc -i usb0`, then `ping 8.8.8.8`.
- **Services:** managed with `systemctl` (e.g. `systemctl status NetworkManager`).
- **Logs:** `journalctl -b` (current boot), `dmesg` (kernel).

### Hardware from Linux (the HAT)

These are standard Linux interfaces — the HAT just exposes them:

```bash
ls /sys/class/leds/                 # status LEDs (red/green/blue)
gpiodetect && gpioinfo              # GPIO lines (buzzer = BUZZERn)
v4l2-ctl --list-devices             # cameras (OV5647 on /dev/video0)
aplay -l ; arecord -l               # audio out/in (HAT PDM mic)
```

The ready-made `hat.py` wraps the buzzer/LEDs/camera (see the section above), or
use the point-and-click `hat-gui.ps1` from Windows.

### Gemy — the greeting robot (waves, voice, and its name)

**Gemy** (`greeter.py`) keeps the HAT camera streaming **and** listens on the HAT microphone,
then reacts with light + sound depending on what it sees and the *tone* of what it hears:

- **"Gemy"** (its name) -> **signature hello**: three-note *Ge-my!* beep + green-blue-green LED wave.
- **Wave** — a hand moving left<->right (OpenCV motion, no ML/NPU) -> double beep + green flash.
- **Hand held up** — a still hand/object in the upper frame for ~0.7 s -> double beep + green flash.
- **"hello" / "hi"** (also "hey"/"hiya") -> double beep + green flash.
- **Something funny** (jokes, "haha", knock-knock, chicken joke) -> R2D2 chatter + **rainbow** sweeps.
- **Being nice** ("thanks", "love you", "awesome") -> happy beeps + **rainbow** + green/blue sparkle.
- **Being mean** ("stupid", "hate you", "shut up") -> louder sad beeps + **red** blinks.
- **Being sad** ("nobody likes you", "sad news", "lonely") -> quiet whimpers + **blue** cry flashes.
- **"yes"** ("yeah", "for sure", "I agree") -> **one green** light beep.
- **"no"** ("nope", "no way") -> **two red** light beeps.
- **Anything else** -> soft beep + gentle **rainbow** (neutral).
- **Idle** — after ~20 s with no reaction it force-clears everything (LEDs off, buzzer off).
- **"Gemy turn off"** (or **stop**, **go to sleep**, **goodbye Gemy**) → goodbye beeps + blue fade, then Gemy exits.

Speech is transcribed by **Moonshine**. **Moods** use **keyword rules first** (`greeter.py`), then optional **Gemma 3 assist** (`--gemma-mood`, default from PC) only when keywords miss. Invalid Gemma output → **neutral** (no crash). Use `--no-gemma-mood` for keywords-only (safest). See [docs/lab/08-GEMY-MOODS-AND-REACTIONS.md](lab/08-GEMY-MOODS-AND-REACTIONS.md).

```powershell
greet-demo.ps1                  # Gemma assist on (default)
greet-demo.ps1 -NoGemmaMood     # keywords only
```

```powershell
# Windows — open it in an interactive window (Ctrl+C to stop):
powershell -ExecutionPolicy Bypass -File greet-demo.ps1
powershell -ExecutionPolicy Bypass -File greet-demo.ps1 -Sensitivity high
powershell -ExecutionPolicy Bypass -File greet-demo.ps1 -NoSpeech   # camera only
powershell -ExecutionPolicy Bypass -File greet-demo.ps1 -NoVision   # mic only
```

#### Run Gemy without a PC (power bank / charger — autostart on boot)

**One-time install** while USB is connected to your PC:

```powershell
powershell -ExecutionPolicy Bypass -File install-gemy-standalone.ps1
```

**Boot autostart is OFF by default** in this repo (`windows/lib/GemyFeatures.ps1`). When enabled via `install-gemy-standalone.ps1`, boot runs **voice-only, keywords-only** (`--no-gemma-mood --no-vision`) for stability. Use the Control Center on a PC for camera + Gemma assist + full intro.

- **Internet is not required** at runtime if speech models are already on the board.
- **USER button** still **starts/stops** Gemy if you want silence.
- Log on the board: `/home/root/gemy.log`
- Disable boot autostart: `install-gemy-standalone.ps1 -NoAutostartOnBoot`

Check services: `adb shell systemctl status gemy-autostart gemy-watcher`

Or directly on the board (needs the venv python for OpenCV + sounddevice):

```bash
/home/root/sl2610-examples/.venv/bin/python3 -u /home/root/greeter.py
# --sensitivity low|medium|high   --gain 400 (if washed out)   --duration 30
# --keywords hello,hi,hey,hiya    --audio-device 0    --no-speech / --no-vision
# --idle-timeout 20   (after this many quiet seconds, force LEDs + buzzer off)
# --fps 12   (vision frame-rate cap; keep it low so the mic gets CPU)
```

> **If it stops reacting to your voice:** run **`cleanup-board.ps1`** or Control Center
> **Stop buzzer & reset board**. The greeter loads speech **before** the camera loop and caps vision at ~5 fps
> (`--fps`). Every phrase should get at least a **neutral** reaction (1 s cooldown). Watch for `[ears] heard:` lines.

First start takes ~10-20 s while the speech model loads; with both on it runs
~35 fps. How it works: vision runs in the main thread (frame differencing for the
wave; a running-average background for the still raised-hand), while speech runs in
a background thread (Silero voice-activity + Moonshine transcription, then a tiny
funny/nice/mean/greeting word-match). A third thread is an idle watchdog. Everything
routes through one shared `react(kind)` dispatcher with a 3 s cooldown, and the LED
+ buzzer parts of each reaction play at the same time. Buzzer/LED/camera/mic are
always released on exit.

> Can Gemma 3 do this from live video? **No.** The board's `gemma-3-270m-it` is
> **text-only**. **Gemma 4 does not run on this board** (2 GB RAM). For NPU vision use bundled
> classify/detect demos. Waving uses OpenCV in `greeter.py`, as here.

### Does the board's Linux have a GUI?

Yes — the image includes a **Wayland desktop** (`weston`) plus Qt/QML demo apps
(`/home/root/demos`). But it's **headless by default**: `weston.service` only
starts when a **physical display** is attached to the board's DPI/MIPI connector
(e.g. the optional Synaptics panel) and the display overlay is enabled in U-boot
(see `coral-boardguide.md`). You **cannot** see the Weston desktop over USB/`adb`
— it renders to the panel, not to your PC.

#### Optional: WebRTC browser stream (on board)

Some images include WebRTC under `/home/root/sl2610-examples/demos/webrtc` (not launched from this repo). Use Synaptics docs or `adb shell` to run signalling on `:8443` and viewer on `:8090` if you need a browser camera stream without Gemy.

### Reboot / power

```bash
reboot           # from the board
# or just unplug/replug power. After a reboot, re-run install-ncm-signed.ps1 on
# Windows and `udhcpc -i usb0` on the board to restore internet.
```

For serial console, U-boot, display overlays, and re-flashing the image, see the
official **`coral-boardguide.md`** in this folder.

---

## Troubleshooting

**`udhcpc` says "no lease, failing"**
The host isn't sharing internet to the NCM adapter. Re-run step 2
(`install-ncm-signed.ps1`), then `udhcpc -i usb0` again.

**Board has IP but no internet (`8.8.8.8` fails)**
ICS likely dropped after a reboot. Re-run step 2.

**Device Manager shows "CDC NCM" with a yellow `!` again**
Re-run `install-ncm-signed.ps1` — it rebinds the `UsbNcm` driver.

**`adb` not found / `adb devices` empty**
Open a new terminal; replug the USB-C cable; run `adb kill-server` then
`adb devices`.

**`gst-plugin-scanner ... libpython` warning when running a demo**
Harmless in headless mode. The model still runs on the NPU.

---

## Quick reference (copy/paste)

```powershell
# Windows: re-arm internet sharing, then connect
powershell -ExecutionPolicy Bypass -File install-ncm-signed.ps1
adb shell
```

```bash
# On the board:
udhcpc -i usb0
ping -c 2 8.8.8.8
cd /home/root/sl2610-examples && source .venv/bin/activate
cd Image_classification
python3 classification.py --model ../models/mbv2.vmfb --image ../samples/cat.jpg --labels labels.json --device torq
```
