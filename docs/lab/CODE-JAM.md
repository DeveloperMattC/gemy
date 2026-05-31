# Gemy Code Jam — Coralboard edition

**Build a robot that hears you, sees you wave, and reacts with beeps and rainbows.**

| | |
|---|---|
| **Time** | ~90 minutes (or 60 min fast track) |
| **Gear** | Windows laptop + Coralboard + Sensor HAT + USB-C cable |
| **Skill level** | Zero to vibe coder — no Python required if you use AI |
| **Repo** | [github.com/DeveloperMattC/gemy](https://github.com/DeveloperMattC/gemy) |

---

## How this jam works

Like a **Google Code Jam**, you solve **rounds** in order. Each round has:

1. **Goal** — what “done” looks like  
2. **Do this** — one command or one button  
3. **Test** — say or do something; board must react  
4. **Pass** — checkbox before you advance  

**Two tracks** (pick one):

| Track | You | Start at |
|-------|-----|----------|
| **A — Vibe coder** | Paste AI prompts, click buttons | [Round 0](#round-0--plug-in-5-min) then [AI prompts](ai-prompt-walkthrough/02-prompt-journey.md) |
| **B — Hands-on** | Run commands yourself | [Round 0](#round-0--plug-in-5-min) through [Round 4](#round-4--full-vibes-20-min) below |

Both tracks end with the same demo: **Gemy listens, waves work, moods light up.**

---

## Scorecard (100 points)

Print this. Check boxes as you go.

| Round | Points | Pass when |
|-------|--------|-----------|
| [0 — Plug in](#round-0--plug-in-5-min) | 10 | Control Center shows board connected |
| [1 — Body](#round-1--body-language-15-min) | 20 | Beep + green LED + photo |
| [2 — Ears](#round-2--ears-20-min) | 30 | `[ears] listening` + Gemy reacts to your voice |
| [3 — Eyes](#round-3--eyes-15-min) | 20 | Wave or hand-up triggers greet |
| [4 — Vibes](#round-4--full-vibes-20-min) | 20 | 5+ moods tested (joke, mean, sad, yes, no) |
| **Bonus** | +10 | Custom phrase or mood via AI |

---

## Round 0 — Plug in (5 min)

### Goal

Laptop talks to the board. One dashboard controls everything.

### Do this

```powershell
git clone https://github.com/DeveloperMattC/gemy.git
cd gemy
winget install Google.PlatformTools
powershell -ExecutionPolicy Bypass -File make-shortcut.ps1
```

1. Plug **USB-C** into the Coralboard (data port on the main board).  
2. Wait ~20 seconds for boot.  
3. Open **Gemy Control Center** (desktop shortcut or `.\coralboard-hub.ps1`).  
4. Browser opens at `http://127.0.0.1:8765/` — leave the PowerShell window open.

### Test

Click **Refresh**. Status should show the board connected (not “waiting for device”).

### Pass

- [ ] `adb devices` shows `device`  
- [ ] Control Center loads in the browser  

**Stuck?** [04-TROUBLESHOOTING.md](04-TROUBLESHOOTING.md) — ADB section. Instructor: run `install-ncm-signed.ps1` once (admin) if the board needs internet.

---

## Round 1 — Body language (15 min)

### Goal

Make the buzzer beep and the LEDs change color — the robot’s “body.”

### Do this

**Easy path:** Control Center → **HAT test panel** → click **Beep**, **Green on**, **Rainbow**, **STOP**.

**Command path:**

```powershell
adb push board\python\hat.py /home/root/hat.py
adb shell python3 /home/root/hat.py beep
adb shell python3 /home/root/hat.py led green on
adb shell python3 /home/root/hat.py rainbow
adb shell python3 /home/root/hat.py led all off
```

### Test

| You do | Board does |
|--------|------------|
| Beep | One short sound, then silence |
| Green on | Green LED lights up |
| Rainbow | Colors cycle |
| STOP / `buzzer off` | Buzzer definitely off |

Optional: **Take photo** in HAT panel, or:

```powershell
adb pull /home/root/hat_photo.jpg .
```

### Pass

- [ ] Heard a beep  
- [ ] Saw LED colors  
- [ ] Buzzer stops when you hit STOP  

**Vibe coder prompt:**

```
I'm in the Gemy Code Jam. Help me test board/python/hat.py on my Coralboard via adb — beep, green LED, rainbow, then all off. Give exact PowerShell commands from the repo root.
```

---

## Round 2 — Ears (20 min)

### Goal

Gemy **hears** you and reacts. This is the main event.

### Do this

1. Control Center → **Stop buzzer & reset board** (clears old demos).  
2. Click **Start Gemy — voice** (recommended first time).  
3. Watch the PowerShell window (~15–20 s for speech model load).

### Test

Wait for this line:

```text
[ears] listening (moods: ...)
```

Then say:

| Say | Expect in log | Hardware |
|-----|-----------------|----------|
| **"Gemy"** | `-> gemy` | Name beep + mini rainbow |
| **"Hello"** | `-> greet` | Friendly beep |
| **"Haha that's funny"** | `-> funny` | Silly beeps + rainbow |
| **"Thank you"** | `-> nice` | Happy beeps |

### Pass

- [ ] Saw `[ears] listening`  
- [ ] Terminal shows `[ears] heard: ...`  
- [ ] Board beeped/LED within ~3 s  

**Fast debug:** `.\greet-demo.ps1 -NoGemmaMood` (keywords only, no NPU Gemma).

**Stuck?** Run cleanup again. See [04-TROUBLESHOOTING.md](04-TROUBLESHOOTING.md).

---

## Round 3 — Eyes (15 min)

### Goal

Gemy **sees** a wave or raised hand (camera math — not Gemma).

### Do this

1. **Stop** the voice-only session (Ctrl+C in PowerShell, or cleanup).  
2. Control Center → **Start Gemy — camera + voice**.  
3. Stand where the HAT camera can see you.

### Test

| You do | Board does |
|--------|------------|
| Wave side to side ~2 s | Greet reaction (beep + lights) |
| Hold hand up in upper half of frame ~1 s | Greet reaction |

Log may show `[vision] wave` or `[vision] hand-up`.

### Pass

- [ ] Wave triggered a reaction  
- [ ] Voice still works after a wave (`[ears] heard:` still appears)  

**Remember:** Waving uses **OpenCV**, not Gemma. Gemma 3 on this board is text-only mood assist. [07-WAVE-VISION-AND-GEMMA.md](07-WAVE-VISION-AND-GEMMA.md)

---

## Round 4 — Full vibes (20 min)

### Goal

Hit every mood. Understand the personality table.

### Test script (read aloud to the room)

Say each line. Tick when the board matches:

| # | Say | Mood | Look for |
|---|-----|------|----------|
| 1 | "Gemy" | gemy | Name ack |
| 2 | "You are stupid" | mean | **Red** blinks |
| 3 | "Nobody likes you" | sad | **Blue** cries |
| 4 | "Yeah for sure" | yes | **One green** beep |
| 5 | "No way" | no | **Two red** beeps |
| 6 | Chicken joke + punchline | funny | Rainbow + chatter |
| 7 | "Gemy turn off" | off | Goodbye, exits |

Full reference: [08-GEMY-MOODS-AND-REACTIONS.md](08-GEMY-MOODS-AND-REACTIONS.md)

### Pass

- [ ] At least **5 different moods** observed  
- [ ] **Mean** = red, **sad** = blue (not swapped)  
- [ ] Cleanup: Ctrl+C, then **Stop buzzer & reset board**  

---

## Bonus round — Make it yours (+10)

### Goal

Change Gemy without fear.

### Vibe coder prompts (pick one)

**Add a keyword:**

```
In board/python/greeter.py, add "you rock" to the NICE keyword list so Gemy reacts nice when I say it. Keep changes minimal. Tell me how to push and restart.
```

**Add a custom reaction word:**

```
Add keyword "pizza" -> funny mood in greeter.py (minimal diff). Push with greet-demo.ps1 flow.
```

### Test

Push + restart Gemy. Say your new phrase. Board reacts.

### Pass

- [ ] Your custom phrase triggers a mood  

---

## Final demo (2 min)

Perform for a neighbor or the room:

1. **Start Gemy — camera + voice**  
2. Say **"Gemy"**  
3. Say **"That is hilarious"**  
4. Say **"You are awesome"**  
5. **Wave**  
6. **Stop buzzer & reset board**  

You finished the jam.

---

## What's in the box (reminder)

| Piece | Role |
|-------|------|
| **Coralboard** | The computer (2 GB RAM, NPU, runs Linux) |
| **Sensor HAT** | Camera, mic, buzzer, RGB LEDs — **not** a second computer |

Gemma **4** does not run on this board (too big; stack is Gemma **3 270M** for optional mood assist). Keywords handle most phrases.

---

## Where to go next

| Doc | When |
|-----|------|
| [ai-prompt-walkthrough/](ai-prompt-walkthrough/) | Build the same thing by pasting AI prompts |
| [01-STUDENT-LAB.md](01-STUDENT-LAB.md) | Deeper technical steps |
| [04-TROUBLESHOOTING.md](04-TROUBLESHOOTING.md) | Something broke |
| [05-INSTRUCTOR-GUIDE.md](05-INSTRUCTOR-GUIDE.md) | Hosting a class |
| [CORALBOARD-GUIDE.md](../CORALBOARD-GUIDE.md) | Day-to-day operator cheat sheet |

---

## Submission blurb (copy for your portfolio)

> I completed the Gemy Code Jam on the Synaptics Coralboard: USB setup, HAT hardware, on-device speech (Moonshine), OpenCV wave detection, and a multi-mood reaction robot — beeps, rainbows, red mean, blue sad — all from a Windows laptop and one USB cable.
