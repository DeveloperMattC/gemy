# Agent instructions — Gemy Coralboard lab

**Start here** when continuing work on this repo. **Code Jam (humans):** [docs/lab/CODE-JAM.md](docs/lab/CODE-JAM.md). Lab index: [docs/lab/README-CODE-LAB.md](docs/lab/README-CODE-LAB.md). **Moods & reactions (canonical):** [docs/lab/08-GEMY-MOODS-AND-REACTIONS.md](docs/lab/08-GEMY-MOODS-AND-REACTIONS.md).

---

## Always apply first

1. **Stability** — [.cursor/rules/coralboard-stability-first.mdc](.cursor/rules/coralboard-stability-first.mdc)  
2. **Hardware** — [.cursor/rules/gemy-hardware-safety.mdc](.cursor/rules/gemy-hardware-safety.mdc)  

When editing Gemy code or Windows launchers, Cursor also loads:

3. **Gemy patterns** — [.cursor/rules/gemy-development.mdc](.cursor/rules/gemy-development.mdc) (mistake log, moods, classification order)  
4. **PowerShell/hub** — [.cursor/rules/gemy-windows-scripts.mdc](.cursor/rules/gemy-windows-scripts.mdc)  

**Skills:** [.cursor/skills/gemy/SKILL.md](.cursor/skills/gemy/SKILL.md) (Gemy), [.cursor/skills/coralboard/SKILL.md](.cursor/skills/coralboard/SKILL.md) (USB/adb/HAT).

---

## What Gemy is today

| Piece | Location | Notes |
|-------|----------|--------|
| Main app | `board/python/greeter.py` | Vision + speech + mood dispatch |
| HAT driver | `board/python/hat.py` | `gemy_funny` (rainbow+joke), `gemy_mean`, `gemy_sad`, … |
| Gemma moods | `board/python/gemma_mood.py`, `gemma_mood_worker.py` | Assist only; invalid label → neutral |
| PC launcher | `windows/demos/greet-demo.ps1` | Default **`--gemma-mood`**; `-NoGemmaMood` for keywords-only |
| Control Center | `windows/hub/` | Web UI → `greet-demo.ps1`; port ~8765 |
| Boot autostart | `board/shell/gemy-boot.sh`, `GemyFeatures.ps1` | **Off by default**; boot uses `--no-gemma-mood --no-vision` |

**Moods:** `gemy`, `greet`, `funny`, `nice`, `mean`, `sad`, `yes`, `no`, `neutral`, `off`.

**Classification:** keywords + math → optional Gemma assist → `resolve_reaction_kind()` (unknown → neutral).

**Stack:** Python on board; PowerShell + browser Control Center on Windows. **Gemma 3 270M** only (not Gemma 4 on this hardware).

---

## Do not regress

- `--gemma-mood-serial` or per-phrase NPU Gemma reload (freezes).
- Parallel `r2d2` + `rainbow` in separate threads (GPIO lock hides rainbow).
- Gemma on main thread before `[ears] listening`.
- Raw Gemma labels into `react()` without `mood_for_reaction` / `resolve_reaction_kind`.
- Removing 2s watchdog or `MAX_OUTPUT_ON_SEC`.
- Re-enabling boot autostart in `greet-demo.ps1` without `GemyFeatures.ps1` check.
- Hub demos that hold camera without cleanup.

---

## Quick commands

```powershell
.\greet-demo.ps1                    # push + start (Gemma assist on)
.\greet-demo.ps1 -NoGemmaMood       # keywords only — debug freezes
.\greet-demo.ps1 -NoVision          # voice only
.\cleanup-board.ps1
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
| [docs/CORALBOARD-GUIDE.md](docs/CORALBOARD-GUIDE.md) | Operator guide |
