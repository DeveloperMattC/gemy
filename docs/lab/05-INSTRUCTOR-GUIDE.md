# Instructor guide

## Lab metadata (fill in for submission)

| Field | Value |
|-------|-------|
| **Title** | Coralboard Sensor HAT — Meet Gemy (Multimodal Greeting Robot) |
| **Author** | _[Your name]_ |
| **Organization** | _[Your team / Google program]_ |
| **Duration** | 90–120 minutes |
| **Class size** | 1 board per pair recommended |
| **Prerequisites** | Python basics, PowerShell, USB drivers |

---

## Before class (instructor setup)

### One week prior

- [ ] Flash/verify Coralboard images with `sl2610-examples` + `.venv`
- [ ] Install ADB on all lab PCs (or provide offline Platform Tools zip)
- [ ] Run `install-ncm-signed.ps1` once per PC; document admin UAC process
- [ ] Copy `coralboard-code-lab/` to shared drive or student repos
- [ ] Test one board end-to-end using [01-STUDENT-LAB.md](01-STUDENT-LAB.md)

### Day of class — per bench

- [ ] USB-C data cable (not charge-only)
- [ ] Sensor HAT firmly seated
- [ ] Board boots (~20 s); `adb devices` shows `device`
- [ ] Run `install-ncm-signed.ps1` if internet needed
- [ ] Push `greeter.py` + `hat.py` from `scripts/`
- [ ] Kill stale demos: `adb shell pkill -9 -f wave_detect.py`

---

## Suggested schedule

| Time | Activity | Doc section |
|------|----------|-------------|
| 0:00 | Intro, hardware tour | Student Part 0 |
| 0:15 | ADB + `udhcpc` | Part 1 |
| 0:30 | `hat.py` buzzer/LED/photo | Part 2 |
| 0:45 | Gemma voice demo (mic proof) | Part 3 |
| 1:00 | Deploy `greeter.py`, test reactions | Part 4 |
| 1:25 | Experiments + Q&A | Part 5 |
| 1:35 | Cleanup, retrospective | Part 6 |

---

## Demonstration script (2 min)

1. Launch `greet-demo.ps1` — point at `[ears] listening`.
2. Say **"Gemy"** → signature three-note beep + green-blue-green LEDs.
3. Say **"Hello"** → green + double beep.
4. Say **"That's hilarious haha"** → rainbow + R2D2.
5. Say **"Good robot"** → green/blue + happy beeps.
6. Wave at camera → greet reaction.
7. Ctrl+C → `buzzer off`, `led all off`.

---

## Assessment rubric (suggested)

| Criterion | Points |
|-----------|--------|
| Board connectivity + internet | 15 |
| `hat.py` hardware tests documented | 20 |
| Greeting robot runs with `[ears] on` | 25 |
| ≥4 reaction types demonstrated | 25 |
| Written explanation of GPIO latch OR CPU contention | 15 |

**Bonus:** Extended keyword list or custom reaction pattern.

---

## Common classroom failures

1. **`wave_detect.py` left running** — No voice. Fix: `pkill` + use `greet-demo.ps1`.
2. **Students close terminal but not greeter** — Camera busy. Fix: `fuser /dev/video0`, kill PID.
3. **Buzzer left on** — Teach `gpioset gpiochip0 6=1` emergency.
4. **No `[ears] on` after 30 s** — Speech import failed; check venv path.
5. **ICS blocked by school policy** — Pre-download models on board or use offline mirror.

---

## Differentiation

| Level | Task |
|-------|------|
| Beginner | Follow student lab checklist only |
| Intermediate | Modify `MEAN`/`NICE` lists; tune `--sensitivity` |
| Advanced | Add new `REACTIONS` entry; document in README |

---

## Packaging for Google / external submission

Include in zip or repo:

```
coralboard-code-lab/
  README.md
  docs/*.md
  scripts/*   (all launchers + greeter.py + hat.py)
```

Optional separate zip: `coral-ncm-drv/` and CP210x driver (large; link instead).

Add:

- Link to official Coralboard getting started PDF
- Photo of HAT labeled (mic, camera, LEDs, buzzer)
- 30–60 s screen recording of greeter reactions

---

## Post-lab cleanup command

```powershell
adb shell pkill -9 -f greeter.py
adb shell pkill -9 -f wave_detect.py
adb shell python3 /home/root/hat.py buzzer off
adb shell python3 /home/root/hat.py led all off
```

---

## Contact / support

_[Add your course forum, issue tracker, or email for lab TAs]_
