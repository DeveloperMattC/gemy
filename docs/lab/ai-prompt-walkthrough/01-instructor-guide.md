# Instructor guide — AI prompt walkthrough

Use this when **you** lead the session. Participants follow [02-prompt-journey.md](02-prompt-journey.md) or you project one step at a time.

## Session format

| Style | Best for |
|-------|----------|
| **Live demo + tables paste prompts** | 8–20 people, 1 board on screen |
| **Self-paced with roving help** | 20+ people, 1 board per 2–3 people |
| **Hybrid** | You do Steps 1–3 on screen; they catch up on 4–6 |

## Timing (90 min)

| Min | Step | Your talking point |
|-----|------|-------------------|
| 0–5 | 1 | “AI writes code; you run it and test on hardware.” |
| 5–20 | 2 | “Body first: beep and lights.” |
| 20–30 | 3 | “GUI so anyone can test.” |
| 30–45 | 4 | “Camera **math** sees a wave — **not** Gemma.” ([07-WAVE-VISION-AND-GEMMA.md](../07-WAVE-VISION-AND-GEMMA.md)) |
| 45–65 | 5 | “Ears + personality — this is Gemy.” |
| 65–75 | 6–7 | “One app on Windows; cleanup button.” |
| 75–85 | 8 | Optional: USER button standalone |
| 85–90 | 10 | Show-and-tell |

Add 30 min buffer for Wi‑Fi, driver, or speech model load time on first run.

## Before class

- [ ] Boards flashed with `sl2610-examples` + `.venv`
- [ ] `winget install Google.PlatformTools` on student machines (or USB stick with platform-tools)
- [ ] Run `install-ncm-signed.ps1` once per room PC (admin) or have IT preconfigure NCM
- [ ] Copy entire `gemy-coralboard-lab` repo to shared drive or USB (or have students `git clone`)
- [ ] Print [PROMPTS-ONLY.md](PROMPTS-ONLY.md) or share link
- [ ] Test one board: hub → clean up → Gemy → say “Gemy”
- [ ] Post **emergency buzzer** slide: `adb shell python3 /home/root/hat.py buzzer off`

## What participants need installed

1. **Cursor** (recommended) or VS Code + Copilot  
2. **ADB** in PATH  
3. **gemy-coralboard-lab** folder (repo root)  
4. Coralboard + HAT + USB-C cable  

They do **not** need Python installed on Windows (runs on the board).

## Rules for the room

1. **One prompt at a time** — wait for checkpoint.  
2. **Always Clean up board** before voice (Step 5+).  
3. **Do not run wave-demo and greet-demo together** — wave has no mic and steals the camera.  
4. **Let the AI finish** before clicking Run — but review diffs if curious.  
5. **It's OK to skip to the finished repo** for the demo; the learning is the journey.

## If the repo already has all the code

Say honestly: *“This folder is the answer key. Your job is to **rebuild understanding** with prompts — or extend Gemy with your own moods.”*

Extension prompts for fast groups:

- “Add a **sleepy** mood when I say goodnight.”  
- “Add Italian: when I say ciao, treat as greet.”  
- “Make neutral blink blue twice instead of once.”

## Common failures (quick fixes)

| Symptom | You say | Do |
|---------|---------|-----|
| Voice dead, wave works | “Old wave demo is still running.” | `cleanup-board.ps1` |
| No `[ears] listening` | “Wait 20 seconds for speech model.” | Wait; check internet once |
| Buzzer stuck | “GPIO latched on.” | hat-gui STOP or `buzzer off` |
| AI edited wrong file | “Point it at board/python/” | Paste path in next prompt |
| `adb` not found | “New terminal after winget.” | Reopen PowerShell |

Full prompts: [03-fix-it-prompts.md](03-fix-it-prompts.md)

## Assessment (lightweight)

Participant can explain in one sentence each:

1. What **Gemy** does when you say its name.  
2. Why **cleanup** matters before voice.  
3. One thing the **AI** did vs what **they** did (ran commands, tested hardware).

## Submission angle for Google / jam

Screenshot or 30s video: say “Gemy”, show signature reaction, show hub window, paste final reflection prompt output.
