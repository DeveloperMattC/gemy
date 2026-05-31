# Gemy lab learnings

**For humans and agents.** Dated incidents are below; the **summary** is the stable “what we learned” from the 2026 freeze work.

Canonical how-to: [04-TROUBLESHOOTING.md](04-TROUBLESHOOTING.md) (recovery), [08-GEMY-MOODS-AND-REACTIONS.md](08-GEMY-MOODS-AND-REACTIONS.md) (behavior). **Roadmap / done / next:** [PROJECT-STATUS.md](PROJECT-STATUS.md). Agents: [gemy-docs](../../.cursor/skills/gemy-docs/SKILL.md), [gemy-planning](../../.cursor/skills/gemy-planning/SKILL.md).

---

## Summary — what we learned (2026)

### One NPU, two hungry models

The SL2610 has **one NPU**. **Moonshine** needs it while listening; **Gemma 3** needs it while classifying. They cannot run together. Any design that loads Gemma during listen or leaves Gemma on the NPU while the mic is active will freeze or fail.

### `READY` is not “model loaded”

The mood worker prints **`READY`** as soon as the process starts. The **first** `C|…` classify can still take **1–3 minutes** to load Gemma on the NPU. The ears thread blocks during that load (up to **90 s**, then neutral). That is not always a dead board — check whether **session heartbeat** lines still print every ~1.6 s.

### Killing the worker every phrase was catastrophic

Old behavior: `finish_assist()` **killed** the worker after every assist → full reload next time. Fix: worker protocol **`R|`** unloads the model but **keeps the process**; **`P|`** optional preload between phrases.

### “NPU busy” must mean model on NPU

An idle worker process must **not** count as holding the NPU. Only **`_npu_resident`** or **`_classify_busy`** should block Moonshine / trigger `ensure_npu_for_ears()`.

### Keywords before Gemma (always)

Math, fact Q&A, sky-color patterns, and **incomplete-question detection** avoid Gemma entirely. Gemma is a **label picker** for beeps only — not a chatbot. Open trivia and STT **fragments** → **neutral**, not a multi-minute NPU load.

### STT often cuts questions short

Real log: user said “is the sky green”; board heard **`Is the sky`**. That must **not** start Gemma. User should speak the **full** sentence; code treats `is the sky` / `is the <noun>` stubs as incomplete.

### Frozen board recovery

When the user cannot talk and adb dies (`error: closed`, empty `adb devices`):

1. **Unplug USB-C 15–20 s**, replug.
2. `adb devices` → must show `grinn-astra-2619-coral`.
3. **`.\recover-board.ps1`** (fast cleanup; kills greeter + **gemma_mood_worker**).
4. Restart **`.\greet-demo.ps1 -NoGemmaMood`** until stable, then full deploy.

### Red LED / buzzer stuck

GPIO can **latch ON** if a process dies mid-beep. Recovery: `gpioset gpiochip0 6=1`, `hat.py force-off`, or cleanup script. Hat safety watchdog caps ON time at **2 s** when Python is still running.

### Backlog implementation status

| Item | Status | Notes |
|------|--------|--------|
| **Phrase buffer** | **Done** | `gemy_phrase_buffer.py` — e.g. `is the sky` + `green` within 5s |
| **More keyword QA** | **Done** | `norm_qa`, topic patterns, extra `_FACT_*`, `should_skip_gemma_assist` |
| **Hub “no Gemma” start** | **Done** | Control Center → **Start Gemy — voice, no Gemma (stable)** |
| **Async Gemma (no freeze)** | **Done (pragmatic)** | Background `start_background_preload()`; ears **never** wait for first NPU load; assist only if `_model_loaded` |
| **True parallel listen + Gemma** | **Not possible** | One NPU — cannot transcribe while Gemma runs |

**Async Gemma** here means: preload runs in a **daemon thread** after `[ears] listening`; unclear phrases get **neutral immediately** until load finishes, not a 90s blocked `speech_loop`.

---

## Incident log (newest first)

### 2026-05-31 — “Moon made of cheese” froze (STT wording)

- **Symptom:** Sky Q&A worked; “is the moon made **out of** cheese” hung on first Gemma load.
- **Cause:** Fact list had `made of` only; STT often says `made out of`. No topic fallback → Gemma on NPU.
- **Fix:** `norm_qa()`, snippet + regex moon+cheese, `should_skip_gemma_assist`, phrase buffer for split lines.
- **Files:** `gemy_qa.py`, `gemy_phrase_buffer.py`, `greeter.py`

### 2026-05-31 — adb dropped; board unreachable

- **Symptom:** Gemy frozen; user cannot talk; `adb devices` empty after hang.
- **Cause:** Long Gemma load / NPU wedge; USB adb connection lost.
- **Fix:** Physical USB cycle; `recover-board.ps1`; restart with `-NoGemmaMood`; push latest `gemy_qa` + greeter + gemma worker.
- **Files:** `recover-board.ps1`, `windows/setup/cleanup-board.ps1`

### 2026-05-31 — STT heard only "Is the sky" → Gemma load freeze

- **Symptom:** User asked "is the sky green"; log shows `text='Is the sky'` then `first mood check` / NPU load; board feels frozen 1–3 min.
- **Cause:** Moonshine cut the phrase short; incomplete stub still triggered Gemma assist (full model load) instead of neutral.
- **Fix:** `gemy_qa.looks_like_incomplete_yes_no_question()`; greeter skips Gemma → neutral. Full phrase still hits keyword QA (`is the sky green` → no).
- **Files:** `gemy_qa.py`, `greeter.py`

### 2026-05-31 — Gemma worker killed every assist (slow + freezes)

- **Symptom:** First unclear phrase OK; later phrases hang or red LED stuck; logs show `classify_timeout` at 5s while worker still loading on NPU.
- **Cause:** Worker prints `READY` before model load; greeter waited 5s then **killed** the worker on `finish_assist`, forcing 1–3 min reload. Any running worker was treated as “NPU busy” before every listen.
- **Fix:** Worker protocol `R|` (unload model, keep process), `P|` (preload); `finish_assist` soft-release; `npu_held_by_gemma` only when `_npu_resident` or classify busy; longer first-classify timeout.
- **Files:** `gemma_mood.py`, `gemma_mood_worker.py`, `gemy_stability.py`, `greeter.py`

### 2026-05-31 — “Is the sky orange” / blue sky quizzes

- **Symptom:** Freeze or long wait; STT garble (“Use the sky blue”).
- **Cause:** No keyword QA for wrong sky colors; everything hit Gemma on a cold or dying worker.
- **Fix:** `gemy_qa` facts + `_RE_SKY_COLOR`; prefer keywords before Gemma.
- **Files:** `gemy_qa.py`, `greeter.py`
