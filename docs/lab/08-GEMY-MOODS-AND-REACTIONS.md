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
| **nice** | "thanks", "love you", "I'm happy" (empathy) | **Woohoo** rising beeps (7 notes, longer each time) | **Green** on every cheer |
| **mean** | "stupid", "hate you", "shut up" | Louder sad descending beeps | **Red** slow blinks |
| **sad** | "I am sad", "I'm tired/sleepy", lonely, bad news | Blue **crying** sobs (7 whimper beeps, two sniffle waves) | **Blue** on every sob |
| **yes** | "yeah", "for sure", "I agree" | One beep | **One green** light beep |
| **no** | "nope", "no way", "not really" | Two beeps | **Two red** light beeps |
| **neutral** | Anything else / Gemma unsure | One soft beep | Gentle **rainbow** |
| **off** | "Gemy turn off", "stop" | Goodbye beeps | Blue fade → exit |

Vision (wave / hand-up) always uses **greet** (rainbow + beep).

---

## How speech is classified (order matters)

```
1. Turn off?        → off
2. Math quiz?       → yes/no (plus/minus/times/divide, follow-up “is it equal to …”)
3. Fact question?   → yes/no (curated facts, comparisons, robot checks — else neutral)
4. Yes?             → yes (not stolen from “is … correct?” questions)
5. No?              → no
6. Joke in progress?→ funny (knock-knock / riddle tracker)
7. Name "Gemy"?     → gemy
8. Keywords         → mean, sad, funny, nice, greet
9. Small-talk       → "how are you", "great to hear", etc. → greet / nice (no Gemma)
10. Gemma assist    → only if not open-ended, not incomplete STT, rate limit OK
11. Else            → neutral (honest “not sure” beep)
```

**Before classify:** split STT lines may merge (`is the moon` + `made of cheese`) via `gemy_phrase_buffer` (5 s window).

**Before Gemma:** open questions → neutral; **incomplete** stubs → neutral; **local Q&A** (sky colors, moon+cheese, `made out of` → `made of`) → yes/no with **no NPU**; `should_skip_gemma_assist()` blocks Gemma if a local answer exists.

**Math examples (no Gemma):** “is one plus one two” → yes; “is 7 times 6 equal to 44” → no; then “is it equal to 42” → yes. Also plus/minus/times/divide, digits, teens (eleven–nineteen), and “what is 3 add 4 equal to 7”.

**Gemma never runs before keywords or math rules.** That keeps jokes, insults, and quizzes fast.

**Beep-only:** Gemy cannot say words or invent buzzer patterns. Open questions ("what is the capital of France") → **neutral**. Gemma is a **label picker** only: it must output exactly one word from `gemy greet funny nice mean sad yes no off neutral` (see `gemma_mood.ALLOWED_LABELS_LINE`). Sentences, facts, or unknown words → **neutral** via `normalize_mood_label()` + `gemy_reactions.gemma_label_to_beep_kind()`. Rule: `.cursor/rules/gemy-beep-only.mdc`.

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
| **NPU before listen** | `ensure_npu_for_ears()` only when model is on NPU (`_npu_resident`) or classify/prewarm busy — idle worker is OK |
| **Warm worker + background preload** | ~2 s after `[ears]`: worker + **`P|`** in daemon thread — **speech never waits** for first load |
| **Assist only if `_model_loaded`** | Until preload done → neutral + log line (no 90s block on ears thread) |
| **NPU after assist** | `finish_assist()` sends **`R|`** (unload model, **keep worker**) — not kill unless release fails |
| **Worker protocol** | `P|` preload, `R|` release, `C|` classify, stdout `READY` / `OK` / `L|` only |
| **Assist timeouts** | After model loaded: up to **12 s** per check; timeout → kill worker + cooldown |
| **When Gemma runs** | ≥3 words or ≥14 chars; not incomplete question; not open trivia; **≥40 s** between assists |
| **listen_once cap** | **60 s** max wait per phrase; then mic reset and listen again |
| **Stuck guard** | `listen_wait` **>45 s** or Gemma **>20 s** (first load **>100 s**) → recover mic + release NPU |
| Worker logs on **stderr** only | stdout is protocol lines only |

Incomplete STT (`is the sky` without `green`) → **neutral**, skip Gemma. See [LEARNINGS.md](LEARNINGS.md).

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
| `board/python/gemy_math.py` | Fast math quizzes (yes/no, no NPU) |
| `board/python/gemy_qa.py` | Safe fact Q&A, `norm_qa`, topic patterns, skip-Gemma guard |
| `board/python/gemy_phrase_buffer.py` | Merge split quiz phrases across listens |
| `board/python/hat.py` | Buzzer, LEDs, `gemy_funny`, `gemy_greet`, … |
| `board/python/gemma_mood.py` | Prompt, `normalize_mood_label`, subprocess worker |
| `board/python/gemma_mood_worker.py` | Isolated Gemma process |
| `board/python/gemy_stability.py` | NPU rules, listen/Gemma timeouts, stuck recovery |
| `windows/demos/greet-demo.ps1` | Push Python files + start greeter |
| `recover-board.ps1` | Emergency: kill greeter + Gemma worker, buzzer/LED off |
| `windows/hub/` | Control Center — **Start Gemy — voice, no Gemma (stable)** |
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
