# Agent instructions — Gemy Coralboard lab

**Start here** when continuing work on this repo.

| Read first | Purpose |
|------------|---------|
| [docs/lab/PROJECT-STATUS.md](docs/lab/PROJECT-STATUS.md) | **Goals, done, next steps, smoke checklist** |
| [docs/lab/08-GEMY-MOODS-AND-REACTIONS.md](docs/lab/08-GEMY-MOODS-AND-REACTIONS.md) | Moods & reactions (technical canon) |
| [docs/lab/LEARNINGS.md](docs/lab/LEARNINGS.md) | Why freezes happened |

**Code Jam:** [docs/lab/CODE-JAM.md](docs/lab/CODE-JAM.md). **Lab index:** [docs/lab/README-CODE-LAB.md](docs/lab/README-CODE-LAB.md).

---

## Always apply first

1. **Stability** — [.cursor/rules/coralboard-stability-first.mdc](.cursor/rules/coralboard-stability-first.mdc)  
2. **Hardware** — [.cursor/rules/gemy-hardware-safety.mdc](.cursor/rules/gemy-hardware-safety.mdc)  

When editing Gemy code or Windows launchers, Cursor also loads:

3. **Planning & docs** — [.cursor/rules/gemy-planning-and-docs.mdc](.cursor/rules/gemy-planning-and-docs.mdc) (goals, roadmap, session updates)
4. **Gemy patterns** — [.cursor/rules/gemy-development.mdc](.cursor/rules/gemy-development.mdc) (mistake log, moods, classification order)
5. **Beep-only** — [.cursor/rules/gemy-beep-only.mdc](.cursor/rules/gemy-beep-only.mdc) (no speech; neutral when no beep fits)
6. **PowerShell/hub** — [.cursor/rules/gemy-windows-scripts.mdc](.cursor/rules/gemy-windows-scripts.mdc)  

**Skills:** [gemy-planning](.cursor/skills/gemy-planning/SKILL.md) (goals/roadmap/status), [gemy-docs](.cursor/skills/gemy-docs/SKILL.md) (technical docs), [gemy](.cursor/skills/gemy/SKILL.md) (runtime), [coralboard](.cursor/skills/coralboard/SKILL.md) (USB/adb/HAT).

**Planning rule:** [.cursor/rules/gemy-planning-and-docs.mdc](.cursor/rules/gemy-planning-and-docs.mdc) (always on).

---

## What Gemy is today

| Piece | Location | Notes |
|-------|----------|--------|
| Main app | `board/python/greeter.py` | Vision + speech + mood dispatch |
| HAT driver | `board/python/hat.py` | `gemy_funny` (rainbow+joke), `gemy_mean`, `gemy_sad`, … |
| Gemma moods | `board/python/gemma_mood.py`, `gemma_mood_worker.py` | Assist only; invalid label → neutral |
| PC launcher | `windows/demos/greet-demo.ps1` | Default **local moods only** (no NPU); `-GemmaMoodAssist` experimental |
| Control Center | `windows/hub/` | Web UI → `greet-demo.ps1`; port ~8765 |
| Boot autostart | `board/shell/gemy-boot.sh`, `GemyFeatures.ps1` | **Off by default**; boot uses `--no-gemma-mood --no-vision` |

**Moods:** `gemy`, `greet`, `funny`, `nice`, `mean`, `sad`, `yes`, `no`, `neutral`, `off`.

**Classification:** keywords + math → optional Gemma assist → `resolve_reaction_kind()` (unknown → neutral).

**Stack:** Python on board; PowerShell + browser Control Center on Windows. **Gemma 3 270M** only (not Gemma 4 on this hardware).

---

## Lessons from freeze debugging (2026)

- **One NPU** — Moonshine (listen) and Gemma (classify) never together; `READY` ≠ model loaded.
- **Soft release** — `finish_assist()` uses worker `R|` (keep process); do not kill worker every phrase.
- **STT fragments** — `is the sky` without a color → neutral, no Gemma (`looks_like_incomplete_yes_no_question`).
- **Sky quizzes** — keyword Q&A first (`is the sky green` → no).
- **Recovery** — USB cycle if adb empty; `.\recover-board.ps1`; then `-NoGemmaMood` until stable.

Full write-up: [docs/lab/LEARNINGS.md](docs/lab/LEARNINGS.md).

---

## Do not regress

- `--gemma-mood-serial` or per-phrase NPU Gemma reload (freezes).
- Killing Gemma worker on every `finish_assist` (forces 1–3 min reload).
- Treating idle worker process as “NPU busy” before every listen.
- Gemma assist on incomplete questions (`is the sky` with no color).
- Parallel `r2d2` + `rainbow` in separate threads (GPIO lock hides rainbow).
- Gemma on main thread before `[ears] listening`.
- Raw Gemma labels into `react()` without `mood_for_reaction` / `resolve_reaction_kind`.
- Removing 2s watchdog or `MAX_OUTPUT_ON_SEC`.
- Re-enabling boot autostart in `greet-demo.ps1` without `GemyFeatures.ps1` check.
- Hub demos that hold camera without cleanup.

---

## Quick commands

```powershell
.\greet-demo.ps1                    # push + start (local moods, no NPU)
.\greet-demo.ps1 -GemmaMoodAssist    # experimental Gemma on neutral only
.\greet-demo.ps1 -NoVision          # voice only
.\recover-board.ps1                 # emergency: unfreeze + kill Gemma worker
.\cleanup-board.ps1                 # full cleanup (slower)
.\windows\hub\coralboard-hub.ps1    # Control Center
```

On board, success line: **`[ears] listening (moods: …)`**.

---

## Doc map (update these when behavior changes)

| Doc | Audience |
|-----|----------|
| [docs/lab/CODE-JAM.md](docs/lab/CODE-JAM.md) | **Primary student path** (Code Jam rounds) |
| [docs/lab/08-GEMY-MOODS-AND-REACTIONS.md](docs/lab/08-GEMY-MOODS-AND-REACTIONS.md) | Moods, Gemma, reactions — **source of truth** |
| [docs/lab/01-STUDENT-LAB.md](docs/lab/01-STUDENT-LAB.md) | Technical student steps |
| [docs/lab/02-HOW-WE-CODED-IT.md](docs/lab/02-HOW-WE-CODED-IT.md) | Implementation |
| [docs/lab/03-ARCHITECTURE.md](docs/lab/03-ARCHITECTURE.md) | Diagrams |
| [docs/lab/04-TROUBLESHOOTING.md](docs/lab/04-TROUBLESHOOTING.md) | Fixes |
| [docs/lab/LEARNINGS.md](docs/lab/LEARNINGS.md) | Dated incident notes (append-only) |
| [docs/lab/PROJECT-STATUS.md](docs/lab/PROJECT-STATUS.md) | **Goals, roadmap, done, next** |
| [docs/CORALBOARD-GUIDE.md](docs/CORALBOARD-GUIDE.md) | Operator guide |
