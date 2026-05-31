# Instructor guide — Gemy Code Jam

## Metadata

| Field | Value |
|-------|-------|
| **Title** | Gemy Code Jam — Coralboard SL2610 |
| **Duration** | 60 min (fast) / 90 min (full) / 120 min (with bonus) |
| **Class size** | 1 board per pair |
| **Student doc** | [CODE-JAM.md](CODE-JAM.md) |
| **AI track** | [ai-prompt-walkthrough/](ai-prompt-walkthrough/) |

---

## Before class

- [ ] ADB on lab PCs (`winget install Google.PlatformTools`)
- [ ] Run `install-ncm-signed.ps1` once per PC (admin) if internet needed
- [ ] Test one board: `make-shortcut.ps1` → Control Center → Start Gemy — voice
- [ ] Clone [gemy-coralboard-lab](https://github.com/DeveloperMattC/gemy-coralboard-lab) to shared drive

---

## Schedule (90 min)

| Time | Activity | Doc |
|------|----------|-----|
| 0:00 | Welcome, what's in the box, jam rules | CODE-JAM intro |
| 0:10 | Round 0 — plug in, Control Center | Round 0 |
| 0:25 | Round 1 — HAT panel beeps/LEDs | Round 1 |
| 0:45 | Round 2 — Start Gemy, voice test | Round 2 |
| 1:00 | Round 3 — camera + wave | Round 3 |
| 1:15 | Round 4 — full mood script | Round 4 |
| 1:25 | Final demos + cleanup | Final demo |
| 1:30 | Optional bonus: custom keyword | Bonus |

**Fast track (60 min):** Skip HAT CLI commands; use Control Center only. Skip bonus.

---

## 2-minute stage demo

1. Control Center → cleanup → **Start Gemy — camera + voice**
2. **"Gemy"** → **"That's hilarious"** → **"Good robot"** → **wave**
3. Cleanup

---

## Rubric (matches scorecard)

| Criterion | Points |
|-----------|--------|
| Board connected in Control Center | 10 |
| HAT beep + LED | 20 |
| `[ears] listening` + 3 voice moods | 30 |
| Wave or hand-up | 20 |
| 5 moods including mean/sad/yes/no | 20 |
| Bonus: custom keyword | +10 |

---

## Common failures

| Problem | Fix |
|---------|-----|
| No `[ears] listening` | Wait 20 s; `-NoGemmaMood`; cleanup + restart |
| Camera busy | `cleanup-board.ps1` |
| Buzzer stuck | HAT STOP or cleanup |
| Freeze / no red heartbeat | `-NoGemmaMood`; kill greeter via cleanup |
| Old greeter running | cleanup before every start |

Full list: [04-TROUBLESHOOTING.md](04-TROUBLESHOOTING.md)

---

## Talking points

- **HAT ≠ second computer** — peripherals only
- **Wave ≠ Gemma** — OpenCV motion; Gemma is optional text mood assist
- **Gemma 4 ≠ on this board** — Gemma 3 270M max; keywords do most work
- **Cleanup before every voice demo** — classroom habit

---

## AI jam hosts

Participants use [02-prompt-journey.md](ai-prompt-walkthrough/02-prompt-journey.md).  
Print [PROMPTS-ONLY.md](ai-prompt-walkthrough/PROMPTS-ONLY.md) as handout.

Keep one **working board on projector**; students follow on laptops.
