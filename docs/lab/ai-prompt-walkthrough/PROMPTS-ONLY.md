# Prompts only — print-friendly

Copy each block into Cursor or ChatGPT. Run the matching command your instructor gives you.

---

**1A — Orient**

```
I'm in the Gemy Code Jam (github.com/DeveloperMattC/gemy) with a Coralboard SL2610 + Sensor HAT. Read README.md and docs/lab/CODE-JAM.md. Give me a 5-bullet summary in plain English.
```

**1B — ADB check**

```
Help me verify ADB from repo root. Exact PowerShell commands and what success looks like. Board plugged in via USB-C.
```

---

**2A — Test hat.py**

```
Explain board/python/hat.py for beginners. How do I test beep, rainbow, and STOP via adb push and adb shell from repo root?
```

**2B — HAT GUI**

```
How do I open hat-gui.ps1 from this repo? What buttons test beep and STOP?
```

---

**3A — Start Gemy**

```
Explain board/python/greeter.py: speech, moods, math quizzes (plus/times), how to start with greet-demo.ps1 or Control Center. What line means ready? What should I say to test?
```

---

**4A — Camera + wave**

```
How do I start Gemy with camera + voice from Control Center? How does wave detection work in greeter.py vision_loop? One paragraph — OpenCV only, not Gemma.
```

---

**5A — Full vibes**

```
Walk me through CODE-JAM Round 4: insult, sad, yes, no, joke, math (7 times 6), turn off. What hardware for each?
```

---

**6A — Control Center**

```
What does coralboard-hub.ps1 / Control Center do? List main buttons and when to use cleanup-board.ps1.
```

---

**7A — Cleanup**

```
Give me one PowerShell command from repo root to run cleanup-board.ps1 and explain what it kills.
```

---

**8A — Bonus keyword**

```
Add keyword "you rock" -> nice mood in greeter.py (minimal diff). Push + restart steps.
```

---

**10 — Reflection**

```
I finished the Gemy Code Jam. Write 3 sentences for my submission: what I built, one thing I learned, one surprise. No jargon.
```

---

**Fix voice**

```
Gemy: no [ears] heard after wave worked. Diagnose stale greeter, camera busy, NPU/Gemma freeze. Point me to cleanup-board.ps1 and -NoGemmaMood. Read docs/lab/04-TROUBLESHOOTING.md.
```

**Fix buzzer stuck**

```
HAT buzzer stuck on. adb commands: hat.py buzzer off and gpioset gpiochip0 6=1. One sentence why (GPIO latch).
```

**Fix math**

```
Gemy should answer math quizzes: plus and times, yes/no, follow-up "is it equal to 42". Explain _try_math_yes_no in greeter.py.
```
