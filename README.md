# Gemy Code Jam — Coralboard SL2610

**90-minute hands-on jam:** plug in a Coralboard, open Control Center, and build a robot that **hears**, **sees waves**, and **reacts with vibes** (beeps + rainbow / red / blue).

**Stack:** Python on the board (`greeter.py`, `hat.py`); PowerShell + browser UI on Windows (`windows/hub/`). Speech uses **Moonshine** STT; moods use **keyword rules first**, optional **Gemma 3 270M** assist — not Gemma 4 (too large for this board).

[![Hardware](https://img.shields.io/badge/Hardware-Coralboard%20%2B%20Sensor%20HAT-blue)](docs/CORALBOARD-GUIDE.md)
[![Host](https://img.shields.io/badge/Host-Windows%2010%2F11-0078D6)](docs/CORALBOARD-GUIDE.md)
[![Jam](https://img.shields.io/badge/Start-CODE--JAM-green)](docs/lab/CODE-JAM.md)

**Demo video:** [Watch Gemy on Coralboard (Google Photos)](https://photos.google.com/share/AF1QipMbPbwXUzknBdhTQ45QUKH_kgF2tNoz5nDwCJDY639jZIquuocTetWdLV-zYc-Jpw?key=U3JZTWpfUi1adk1BeDI4dE1vZjY0UkZXVHg1aHNB) — public shared album: LED and buzzer reactions, laughing, yes/no answers, and greetings.

---

## Start here

**New to the board?** Open the jam guide (rounds, scorecard, pass/fail checks):

**[docs/lab/CODE-JAM.md](docs/lab/CODE-JAM.md)**

| Track | Who | Time |
|-------|-----|------|
| **Code Jam rounds** | Everyone | ~90 min |
| **AI prompts (no coding)** | Vibe coders + Cursor | [ai-prompt-walkthrough](docs/lab/ai-prompt-walkthrough/) |
| **Deep dive** | Engineers | [01-STUDENT-LAB.md](docs/lab/01-STUDENT-LAB.md) |

---

## 5-minute setup

```powershell
git clone https://github.com/DeveloperMattC/gemy.git
cd gemy
winget install Google.PlatformTools
powershell -ExecutionPolicy Bypass -File make-shortcut.ps1
```

Plug in USB-C → open **Gemy Control Center** → **Start Gemy — voice** → wait for **`[ears] listening`** → say **"Gemy"**.

---

## What Gemy does

| You… | Gemy… |
|------|--------|
| Say **"Gemy"** | Name beep + mini rainbow |
| Say **hello** / **wave** | Friendly greet |
| **Joke** / **haha** | Silly beeps + rainbow |
| Something **nice** | Happy beeps + sparkle |
| Something **mean** | Red blinks |
| Something **sad** | Blue cries |
| **Yes** / **no** / **math quiz** | 1 green / 2 red beeps / yes-no for plus & times |
| **"Gemy turn off"** | Goodbye |

Details: [docs/lab/08-GEMY-MOODS-AND-REACTIONS.md](docs/lab/08-GEMY-MOODS-AND-REACTIONS.md)

---

## Repo layout

```
board/python/     greeter.py, hat.py, gemma_mood*.py, gemy_stability.py
windows/hub/      Control Center (browser UI, PowerShell server)
windows/demos/    greet-demo.ps1, hat-gui.ps1
docs/lab/         CODE-JAM.md + lab docs
```

Operator cheat sheet: [docs/CORALBOARD-GUIDE.md](docs/CORALBOARD-GUIDE.md)

---

## License

Educational use. Follow Synaptics / upstream example licenses when redistributing. [docs/PRIVACY.md](docs/PRIVACY.md)
