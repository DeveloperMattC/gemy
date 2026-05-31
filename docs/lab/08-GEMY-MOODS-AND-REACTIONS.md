# Gemy moods, reactions, and voice pipeline

**For students, instructors, and AI agents.** This is the current behavior of `board/python/greeter.py` and `hat.py` (2026).

---

## One sentence

**Moonshine** hears you → **keywords** pick a mood (fast) → optional **Gemma 3** fills gaps → **hat** plays beeps + LED patterns → unknown or invalid → **neutral**.

---

## All reactions (what you see and hear)

| Mood | When it triggers (examples) | Sound | LEDs |
|------|-----------------------------|-------|------|
| **gemy** | Says the name: "Gemy", "Jemmy" | *Ge-my!* three notes | Mini **rainbow** |
| **greet** | "hello", "hi", wave, hand-up | Friendly double beep | **Rainbow** sweep |
| **funny** | "haha", jokes, knock-knock punchline, chicken joke | Ha-ha-ha + giggle bursts | Rapid **green** flashes + green/blue joy flash |
| **nice** | "thanks", "love you", "awesome" | Happy rising beeps | **Rainbow** + green/blue sparkle |
| **mean** | "stupid", "hate you", "shut up" | Louder sad descending beeps | **Red** slow blinks |
| **sad** | "nobody likes you", "sad news", "lonely" | Quiet whimpers | **Blue** cry flashes |
| **yes** | "yeah", "for sure", "I agree" | One beep | **One green** light beep |
| **no** | "nope", "no way", "not really" | Two beeps | **Two red** light beeps |
| **neutral** | Anything else / Gemma unsure | One soft beep | Gentle **rainbow** |
| **off** | "Gemy turn off", "stop" | Goodbye beeps | Blue fade → exit |

Vision (wave / hand-up) always uses **greet** (rainbow + beep).

---

## How speech is classified (order matters)

```
1. Turn off?        → off
2. Yes?             → yes
3. No?              → no
4. Joke in progress?→ funny (knock-knock / riddle tracker)
5. Name "Gemy"?     → gemy
6. Keywords         → mean, sad, funny, nice, greet
7. Small-talk       → "how are you", "great to hear", etc. → greet / nice (no Gemma)
8. Gemma assist     → only if --gemma-mood and steps 6–7 found nothing
9. Else             → neutral
```

**Gemma never runs before keywords.** That keeps jokes and insults fast and avoids NPU work on clear phrases.

---

## Gemma assist (optional, on by default from PC)

| Flag | Meaning |
|------|---------|
| `--gemma-mood` | Gemma helps when keywords miss (default in `greet-demo.ps1`) |
| `--no-gemma-mood` | Keywords only — safest for debugging freezes |
| `--gemma-mood-serial` | **Disabled** — caused NPU freezes; do not re-enable |

**Stability contract (`gemy_stability.py`) — Gemma must never freeze the board:**

| Rule | Why |
|------|-----|
| **Session heartbeat** | Red LED blinks ~every 1.6 s for the whole run (skipped during hat reactions only) |
| **NPU before listen** | `release_npu()` kills any Gemma worker before `listen_once` |
| **NPU after assist** | `finish_assist()` always kills worker after each attempt (success or fail) |
| **5 s assist cap** | Ears thread never blocks longer; timeout kills worker |
| **When Gemma runs** | ≥4 words or ≥20 chars; not fragments; not during knock-knock; **≥90 s** between assists |
| **listen_once cap** | **60 s** max wait per phrase; then mic reset and listen again |
| **Stuck guard** | `listen_wait` **>45 s** or Gemma/react hang → reset mic + kill Gemma worker |
| Worker logs on **stderr** only | stdout is `READY` / `L|` only (no accidental NPU load “in background”) |

Small-talk ("how are you", "great to hear") and short STT fragments ("Go") → **neutral**, no Gemma.

Invalid Gemma word → **neutral**, no crash (`mood_for_reaction`, `resolve_reaction_kind`).

Boot script uses `--no-gemma-mood` (no Gemma on autostart).

---

## Hardware rules (inviolable)

- Buzzer or any LED **on ≤ 2 seconds** per segment (`hat.MAX_OUTPUT_ON_SEC`).
- Reactions use **`hat.gemy_*()`** helpers with **one GPIO lock** — sound and lights run in sequence (not parallel threads), so rainbows are visible.
- Every reaction ends with `hat.force_all_off()`.

See `.cursor/rules/gemy-hardware-safety.mdc` and `.cursor/rules/coralboard-stability-first.mdc`.

---

## Key files

| File | Role |
|------|------|
| `board/python/greeter.py` | Main app: vision, speech loop, keywords, reactions |
| `board/python/hat.py` | Buzzer, LEDs, `gemy_funny`, `gemy_greet`, … |
| `board/python/gemma_mood.py` | Prompt, `normalize_mood_label`, subprocess worker |
| `board/python/gemma_mood_worker.py` | Isolated Gemma process |
| `windows/demos/greet-demo.ps1` | Push scripts + start greeter |
| `windows/hub/` | Control Center (browser UI) |
| `windows/lib/GemyFeatures.ps1` | Boot autostart flag (default **off**) |

---

## Control Center (Windows)

1. Run `make-shortcut.ps1` or `coralboard-hub.ps1`.
2. Open browser to `http://127.0.0.1:8765/` (port may vary).
3. **Start Gemy — voice** or **with camera**.
4. Wait for **`[ears] listening`** in the PowerShell window.

---

## Extending moods

1. Add keywords in `greeter.py` (`FUNNY`, `NICE`, `MEAN`, `SAD`, `_YES_PHRASES`, …).
2. Add or edit `hat.gemy_*()` for LED/sound pattern.
3. Register in `REACTIONS` and `_LABELS`.
4. Add label to `gemma_mood.VALID_MOODS` and `_MOOD_PROMPT` if Gemma should know it.
5. Push to board: `greet-demo.ps1` or Control Center **Refresh**.

---

## For AI agents continuing this project

**Read first:** `AGENTS.md`, this file, `03-ARCHITECTURE.md`, stability rule in `.cursor/rules/`.

**Do not regress:** serial Gemma NPU mode, parallel buzzer+LED without lock, unvalidated Gemma labels, boot autostart without user intent, removing 2s safety cap.

**Test on board:** `[ears] heard: '...' -> funny` and visible rainbow after a joke; mean → red; sad → blue; yes/no → distinct patterns.
