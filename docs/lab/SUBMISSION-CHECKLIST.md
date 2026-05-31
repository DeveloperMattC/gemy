# Google / workshop submission checklist

Use this when packaging the **gemy-coralboard-lab** repo (especially `docs/lab/`) for review.

## Required artifacts

- [ ] `README.md` — points to Code Jam
- [ ] `docs/lab/CODE-JAM.md` — **primary student path** (rounds + scorecard)
- [ ] `docs/lab/01-STUDENT-LAB.md` — technical track
- [ ] `docs/lab/08-GEMY-MOODS-AND-REACTIONS.md` — current mood/reaction reference
- [ ] `AGENTS.md` — instructions for AI agents
- [ ] `docs/04-TROUBLESHOOTING.md`
- [ ] `docs/05-INSTRUCTOR-GUIDE.md` — filled author/org fields
- [ ] `docs/lab/ai-prompt-walkthrough/` — non-engineer prompt path
- [ ] `board/python/`, `windows/` — source (see repo README)

## Recommended extras

- [ ] Short demo video (MP4) or GIF of reactions (funny rainbow, mean/sad, yes/no)
- [ ] Photo of hardware setup
- [ ] Link to Synaptics Coralboard official documentation
- [ ] One-page PDF export of student lab (optional)

## Not included (reference only)

These remain in the parent `robot/` repo — link or bundle separately if required:

- `coral-ncm-drv/` — signed NCM driver tree
- `CP210x_Universal_Windows_Driver/` — UART driver
- `CORALBOARD-GUIDE.md` — extended operator manual
- Official `coral-boardguide.md` from Synaptics

## Zip command (PowerShell)

```powershell
Compress-Archive -Path "gemy-coralboard-lab" -DestinationPath "coralboard-gemy-lab.zip" -Force
```

## Codelab conversion tips

1. Split `01-STUDENT-LAB.md` into numbered codelab steps (one H2 per step).
2. Add **Duration** and **What you'll learn** at the top of step 1.
3. Embed architecture diagram from `03-ARCHITECTURE.md`.
4. Add **Cleanup** as the final step.
5. Link troubleshooting inline at failure points (voice, buzzer, camera).
