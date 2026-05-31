# Prompt journey — build Gemy step by step

**How to use:** Paste each prompt into Cursor. Run the **Try it** command. Pass the checkpoint before the next step.

**Jam map:** [../CODE-JAM.md](../CODE-JAM.md)

---

## Step 1 — Plug in (Round 0)

**Say:** "We teach a robot named Gemy to hear and react — AI writes the code."

### Prompt 1A

```
I'm in the Gemy Code Jam with a Coralboard SL2610 + Sensor HAT. Read README.md and docs/lab/CODE-JAM.md. Give me a 5-bullet summary in plain English.
```

### Prompt 1B

```
Help me verify ADB. Exact PowerShell from repo root. What does success look like?
```

**Try it:**

```powershell
adb devices
powershell -ExecutionPolicy Bypass -File make-shortcut.ps1
```

**Pass:** `device` in adb list; Control Center opens in browser.

---

## Step 2 — Body language (Round 1)

**Say:** "First the robot body — beeps and colors."

### Prompt 2A

```
Explain board/python/hat.py for beginners: buzzer, RGB LEDs, rainbow, photo. How do I test via adb push and adb shell commands from repo root?
```

**Try it:**

```powershell
adb push board\python\hat.py /home/root/hat.py
adb shell python3 /home/root/hat.py beep
adb shell python3 /home/root/hat.py rainbow
```

Or: Control Center → **HAT test panel** → Beep, Rainbow, STOP.

**Pass:** Beep heard; rainbow seen; buzzer stops on STOP.

---

## Step 3 — HAT buttons (optional)

### Prompt 3A

```
How do I open hat-gui.ps1 from this repo? What buttons should I click to test beep and STOP?
```

**Try it:**

```powershell
powershell -ExecutionPolicy Bypass -File hat-gui.ps1
```

**Pass:** Window opens; STOP silences buzzer.

---

## Step 4 — Gemy hears you (Round 2)

**Say:** "Ears use Moonshine on the mic. Moods use keyword lists first — Gemma only helps when unclear."

### Prompt 4A

```
Explain board/python/greeter.py for the Code Jam: speech, moods, how to start with greet-demo.ps1 or Control Center. What line means ready? What should I say to test?
```

**Try it:**

```powershell
powershell -ExecutionPolicy Bypass -File cleanup-board.ps1
powershell -ExecutionPolicy Bypass -File greet-demo.ps1
```

Wait for `[ears] listening`. Say **Gemy**, **hello**, **haha that's funny**.

**Pass:** Log shows `[ears] heard:` and board reacts.

---

## Step 5 — Eyes (Round 3)

**Say:** "Waves use camera math (OpenCV), not Gemma."

### Prompt 5A

```
How do I start Gemy with camera + voice from Control Center or greet-demo.ps1? How does wave and hand-up detection work in greeter.py? One paragraph, no jargon.
```

**Try it:** Control Center → **Start Gemy — camera + voice**. Wave, then say **hello**.

**Pass:** Wave triggers greet; voice still works.

Read: [../07-WAVE-VISION-AND-GEMMA.md](../07-WAVE-VISION-AND-GEMMA.md)

---

## Step 6 — Full vibes (Round 4)

**Say:** "Every mood — mean is red, sad is blue."

### Prompt 6A

```
Walk me through the CODE-JAM Round 4 test script: insult, sad phrase, yes, no, joke, turn off. What should I see for each?
```

**Try it:** Say each line from [../CODE-JAM.md](../CODE-JAM.md) Round 4 table.

**Pass:** 5+ moods; cleanup when done.

---

## Step 7 — Control Center (host demo)

### Prompt 7A

```
What does coralboard-hub.ps1 / Control Center do? List the main buttons and when to use cleanup-board.ps1.
```

**Try it:**

```powershell
powershell -ExecutionPolicy Bypass -File coralboard-hub.ps1
```

**Pass:** Start Gemy from browser; cleanup works.

---

## Step 8 — Bonus: your phrase

### Prompt 8A

```
Add one new keyword to greeter.py so Gemy reacts when I say "you rock". Minimal change. Tell me push + restart steps.
```

**Pass:** Custom phrase works after restart.

---

## Step 9 — Final demo

1. Cleanup → **Start Gemy — camera + voice**  
2. **Gemy** → **You are awesome** → **Haha funny** → **wave**  
3. Cleanup  

### Prompt 9 — reflection

```
I finished the Gemy Code Jam as a non-engineer. Write 3 sentences for my submission: what I built, one thing I learned, one surprise. No jargon.
```

---

**Stuck?** [03-fix-it-prompts.md](03-fix-it-prompts.md) · **Details:** [../02-HOW-WE-CODED-IT.md](../02-HOW-WE-CODED-IT.md)
