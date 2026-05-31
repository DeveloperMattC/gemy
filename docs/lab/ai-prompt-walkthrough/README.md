# Build Gemy with AI — zero-code Coralboard lab (SL2610 + Sensor HAT)

**For students, jam hosts, and curious devs:** paste prompts, run demos, and end with a robot that sees, hears, and reacts — no Python required.

This folder is a **script you can read aloud** while participants **copy prompts into an AI assistant** (Cursor, ChatGPT, Copilot, etc.). No one needs to write code by hand.

The finished project already exists in this repo (`board/python/greeter.py`, etc.). This walkthrough **re-creates the same journey** so a code jam or classroom feels like magic, step by step.

## Who this is for

| Role | Read this |
|------|-----------|
| **Participants** (no coding background) | [00-for-participants.md](00-for-participants.md) then follow [02-prompt-journey.md](02-prompt-journey.md) |
| **Instructor / jam host** | [01-instructor-guide.md](01-instructor-guide.md) + [PROMPTS-ONLY.md](PROMPTS-ONLY.md) for a printable handout |
| **Stuck on AI or hardware** | [03-fix-it-prompts.md](03-fix-it-prompts.md) |

## How a session works (90–120 min)

1. Everyone clones **[gemy-coralboard-lab](https://github.com/DeveloperMattC/gemy-coralboard-lab)** and opens that folder in Cursor (or similar).
2. You plug in a Coralboard + Sensor HAT per table (or demo one board on a projector).
3. For each step in **02-prompt-journey.md**, participants paste the prompt, let the AI edit files, then run the **Try it** command you announce.
4. By the end they have **Gemy**: wave, voice, moods, and a Control Center button.

## Files in this folder

| File | Purpose |
|------|---------|
| [00-for-participants.md](00-for-participants.md) | Plain-English setup (what to install, what the board is) |
| [01-instructor-guide.md](01-instructor-guide.md) | Timing, talking points, checkpoints, common mistakes |
| [02-prompt-journey.md](02-prompt-journey.md) | **Main lab** — numbered steps with prompts + “try it” commands |
| [03-fix-it-prompts.md](03-fix-it-prompts.md) | Extra prompts when voice fails, buzzer stuck, etc. |
| [PROMPTS-ONLY.md](PROMPTS-ONLY.md) | All prompts in one list (print or PDF) |

## Relationship to the technical lab

- Hands-on technical steps: [../01-STUDENT-LAB.md](../01-STUDENT-LAB.md)
- How the code works: [../02-HOW-WE-CODED-IT.md](../02-HOW-WE-CODED-IT.md)
- This folder: **same outcome**, taught through **AI pair-programming** instead of reading Python.

## Tip for hosts

Keep one **working board** on stage. Run **0. Clean up board** in the Control Center before every voice demo. Say **“Gemy”** clearly — the board loves its name.
