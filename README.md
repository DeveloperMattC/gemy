# Meet Gemy: Voice, Vision & Vibes on the Synaptics Coralboard

**Build a pocket-sized robot that sees you wave, hears its name, laughs at your jokes, and sulks when you're mean — on real edge AI hardware.**

[![Devices](https://img.shields.io/badge/Hardware-Coralboard%20SL2610%20%2B%20Sensor%20HAT-blue)](docs/CORALBOARD-GUIDE.md)
[![Host](https://img.shields.io/badge/Host-Windows%2010%2F11-0078D6)](docs/CORALBOARD-GUIDE.md)
[![Level](https://img.shields.io/badge/Level-Beginner%20%E2%86%92%20Intermediate-green)](docs/lab/01-STUDENT-LAB.md)

---

## What is this?

A **complete code lab** for the [Synaptics Coralboard (SL2610)](https://www.synaptics.com/) with the **Sensor HAT** — camera, microphone, buzzer, and RGB LEDs. You will create **Gemy**, a greeting robot that reacts to:

| You do… | Gemy does… |
|---------|------------|
| Say **“Gemy”** | Signature *Ge-my!* beep + green-blue-green lights |
| Wave or say **hello** | Friendly double beep |
| Say something **funny** | Rainbow + R2D2-style chatter |
| Say something **nice** | Happy beeps + green/blue dance |
| Say something **mean** | Sad beep + red glow |
| Say anything else | One beep + blue “I'm listening” blip |
| Press the board **USER button** | Start/stop Gemy without a laptop (optional) |

Works with **on-device speech** (Moonshine), **OpenCV vision** (no cloud required after setup), and a one-click **Windows Control Center**.

---

## Supported hardware

| Component | Required? | Notes |
|-----------|-----------|--------|
| **Synaptics Coralboard SL2610** | Yes | USB-C to host; Linux on-board |
| **Coralboard Sensor HAT** | Yes | OV5647 camera, PDM mic, buzzer, RGB LEDs |
| **Windows 10/11 PC** | Yes | ADB, PowerShell; admin once for USB internet driver |
| USB-C data cable | Yes | Charge-only cables will not work for ADB |
| Monitor for the board | No | Optional WebRTC stream to your browser |
| Internet on the board | Setup only | For first-time model download; Gemy can run offline later |

Not supported in this lab: other boards, HAT-less setups, macOS/Linux host scripts (Windows-focused).

---

## Who is this for?

- **Developers** who want a guided edge-AI + embedded Linux project with working code  
- **Students & jam participants** following the [AI prompt walkthrough](docs/lab/ai-prompt-walkthrough/) (no manual coding required)  
- **Instructors** submitting a workshop to Google or internal enablement  

---

## Quick start (5 minutes)

```powershell
git clone https://github.com/DeveloperMattC/gemy-coralboard-lab.git
cd gemy-coralboard-lab
winget install Google.PlatformTools   # if needed
powershell -ExecutionPolicy Bypass -File make-shortcut.ps1
```

Plug in the board → open **Coralboard Control Center** → **0. Clean up board** → **3. Gemy** → say **“Gemy”**.

Full guide: [docs/CORALBOARD-GUIDE.md](docs/CORALBOARD-GUIDE.md)

---

## Lab paths

| Track | Start here | Time |
|-------|------------|------|
| **“I don't code” — use AI prompts** | [docs/lab/ai-prompt-walkthrough/](docs/lab/ai-prompt-walkthrough/) | ~90 min |
| **Hands-on technical lab** | [docs/lab/01-STUDENT-LAB.md](docs/lab/01-STUDENT-LAB.md) | ~90–120 min |
| **How it was built** | [docs/lab/02-HOW-WE-CODED-IT.md](docs/lab/02-HOW-WE-CODED-IT.md) | Read |

---

## Repo layout

```
gemy-coralboard-lab/
  board/python/      greeter.py (Gemy), hat.py, gemy-watcher.py
  windows/hub/       Control Center GUI
  windows/demos/     greet-demo, hat-gui, Gemma, WebRTC, …
  windows/setup/     USB internet, cleanup, standalone install
  drivers/ncm/       Windows USB Ethernet driver for the board
  docs/              Guides + lab materials
  *.ps1              Shortcuts from repo root
```

---

## Privacy & sharing

This repository is intended for **public sharing**. It does not include personal machine logs, home directory paths, or account-specific configuration. See [docs/PRIVACY.md](docs/PRIVACY.md).

---

## License

Source code in this repo is provided for education and demonstration. Synaptics Coralboard trademarks and upstream example bundles remain subject to their respective terms. Add a `LICENSE` file before commercial redistribution if required by your organization.
