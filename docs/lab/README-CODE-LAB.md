# Gemy Code Lab — doc map

Hands-on lab for **Synaptics Coralboard (SL2610) + Sensor HAT** on Windows.

---

## Start here (everyone)

**[PROJECT-STATUS.md](PROJECT-STATUS.md)** — goals, what works today, what we finished, what to try next.

**[CODE-JAM.md](CODE-JAM.md)** — Google Code Jam-style rounds, scorecard, pass/fail checks. ~90 minutes.

---

## Pick your track

| Track | Doc | Best for |
|-------|-----|----------|
| **Code Jam** | [CODE-JAM.md](CODE-JAM.md) | First time, classrooms, vibe coders |
| **AI prompts** | [ai-prompt-walkthrough/](ai-prompt-walkthrough/) | Paste into Cursor; no manual coding |
| **Student lab** | [01-STUDENT-LAB.md](01-STUDENT-LAB.md) | Step-by-step technical path |
| **Instructor** | [05-INSTRUCTOR-GUIDE.md](05-INSTRUCTOR-GUIDE.md) | Schedule, rubric, classroom fixes |

---

## Reference (read when needed)

| Doc | Purpose |
|-----|---------|
| [08-GEMY-MOODS-AND-REACTIONS.md](08-GEMY-MOODS-AND-REACTIONS.md) | Moods, Gemma assist, flags |
| [07-WAVE-VISION-AND-GEMMA.md](07-WAVE-VISION-AND-GEMMA.md) | Wave = OpenCV; Gemma = text only |
| [04-TROUBLESHOOTING.md](04-TROUBLESHOOTING.md) | Buzzer stuck, no ears, camera busy |
| [LEARNINGS.md](LEARNINGS.md) | **Stability lessons** + dated incident log |
| [02-HOW-WE-CODED-IT.md](02-HOW-WE-CODED-IT.md) | Implementation notes |
| [03-ARCHITECTURE.md](03-ARCHITECTURE.md) | Threads and data flow |
| [06-STANDALONE-GEMY.md](06-STANDALONE-GEMY.md) | USER button, no PC |
| [../CORALBOARD-GUIDE.md](../CORALBOARD-GUIDE.md) | Operator guide |

**AI agents:** repo root [AGENTS.md](../../AGENTS.md)

---

## Source code

| Path | Contents |
|------|----------|
| `board/python/` | `greeter.py`, `hat.py`, `gemma_mood*.py` |
| `windows/demos/` | `greet-demo.ps1`, `hat-gui.ps1` |
| `windows/hub/` | Control Center |

Run from repo root: `.\greet-demo.ps1`, `.\coralboard-hub.ps1`
