# Gemy / Coralboard — project status & roadmap

**Single place for goals, current state, done work, and what to try next.**  
Update this file when you finish a meaningful chunk of work (see [.cursor/skills/gemy-planning/SKILL.md](../../.cursor/skills/gemy-planning/SKILL.md)).

**Last updated:** 2026-05-31

---

## Goals (north star)

| Goal | Why it matters |
|------|----------------|
| **Stable demo** | Board must not freeze; red heartbeat / `[ears] listening` stay alive |
| **Beep-only honesty** | Only yes/no/moods/off — no fake spoken answers; neutral when unsure |
| **Fast common paths** | Sky quizzes, moon/cheese, math, jokes — **keywords/Q&A**, not Gemma |
| **Safe Gemma assist** | Gemma fills gaps only; background preload; never block ears 90s on first load |
| **Teachable lab** | Code Jam + docs so students can extend moods without breaking NPU rules |
| **Easy recovery** | `recover-board.ps1`, hub “no Gemma” start, clear troubleshooting |

**Non-goals (for now):** spoken TTS answers, new beep patterns without `hat.gemy_*()`, Gemma 4, running Moonshine + Gemma on NPU at once.

---

## What works today (smoke checklist)

After `.\greet-demo.ps1` (or hub **Start Gemy — voice**):

- [ ] `[ears] listening` within ~30s
- [ ] “Hello” → greet (rainbow/beep)
- [ ] “Is the sky green” → **no** (fast, log may show `local Q&A` or keyword path)
- [ ] “Is the sky blue” → **yes**
- [ ] “Is the moon made out of cheese” → **no** (no long Gemma load)
- [ ] Knock-knock / joke → funny (visible rainbow via `gemy_funny`)
- [ ] “Gemy turn off” → exit
- [ ] Session heartbeat ~every 1.6s in logs while idle
- [ ] `.\recover-board.ps1` recovers after a hang

**Stable mode (no Gemma):** hub **Start Gemy — voice, no Gemma** or `.\greet-demo.ps1 -NoGemmaMood`.

---

## Recently completed

| Area | What shipped |
|------|----------------|
| **Stability** | Soft NPU release (`R|`/`P|`), `npu_resident`, background preload, no 90s block on ears |
| **Q&A** | `gemy_qa` + `norm_qa`, sky colors, moon+cheese, `should_skip_gemma_assist` |
| **STT splits** | `gemy_phrase_buffer` (5s merge) |
| **Recovery** | `recover-board.ps1`, cleanup kills `gemma_mood_worker` |
| **Hub** | “Start Gemy — voice, no Gemma (stable)” |
| **Gemma prompts** | Beep-only label picker; incomplete fragments skip Gemma |
| **Tests** | `test_gemy_*` on PC including integration + phrase buffer |
| **Docs/skills** | `LEARNINGS.md`, `gemy-docs` skill, troubleshooting freeze section |

Details: [LEARNINGS.md](LEARNINGS.md) incident log.

---

## Known issues / watch list

| Issue | Status | Notes |
|-------|--------|-------|
| First Gemma preload still takes 1–3 min | Expected | Unclear phrases → neutral until `_model_loaded`; not a freeze |
| STT cuts long questions | Mitigated | Phrase buffer + speak full sentence tip |
| adb drops when board wedges | Ops | USB 15–20s replug + `recover-board.ps1` |
| 2-core CPU: vision vs speech | Ongoing | Default `--fps 5`; use `-NoVision` if mic starved |

---

## Next explorations (prioritized)

Pick **one** board-validated item before adding features.

| Prio | Topic | Outcome | Risk |
|------|--------|---------|------|
| **P0** | Board soak test | 30 min voice: sky, moon, math, jokes, no freeze | Low |
| **P1** | Expand `gemy_qa` facts | More kid quizzes without Gemma | Low |
| **P1** | Phrase buffer tuning | Merge “is the moon” + “made of cheese” reliably on hardware | Low |
| **P2** | Hub “last deploy” hint | Show git date or file versions on refresh | Low |
| **P2** | Code Jam sync | Ensure rounds match `08` + PROJECT-STATUS smoke list | Low |
| **P3** | Deferred Gemma reaction | Apply yes/no *after* preload without second utterance (hard UX) | High |
| **P3** | True listen+Gemma parallel | **Not feasible** on one NPU — do not pursue | — |

**Explored / done (do not redo):** kill worker every assist; 5s Gemma timeout on first load; Gemma on STT fragments; `--gemma-mood-serial`.

---

## Where everything is documented

| Need | File |
|------|------|
| **This roadmap** | `docs/lab/PROJECT-STATUS.md` |
| **Why things broke** | `docs/lab/LEARNINGS.md` |
| **Moods / classification** | `docs/lab/08-GEMY-MOODS-AND-REACTIONS.md` |
| **Fix freezes** | `docs/lab/04-TROUBLESHOOTING.md` |
| **Architecture** | `docs/lab/03-ARCHITECTURE.md` |
| **Students** | `docs/lab/CODE-JAM.md` |
| **Agent entry** | `AGENTS.md` |
| **Cursor: plan & track** | `.cursor/skills/gemy-planning/SKILL.md` |
| **Cursor: update technical docs** | `.cursor/skills/gemy-docs/SKILL.md` |
| **Cursor: run Gemy** | `.cursor/skills/gemy/SKILL.md` |
| **Stability rules** | `.cursor/rules/coralboard-stability-first.mdc` |
| **Planning rule** | `.cursor/rules/gemy-planning-and-docs.mdc` |

---

## Session log (optional, newest first)

Short notes so the next session knows context without reading the whole chat.

### 2026-05-31
- Sky Q&A working on board; moon+cheese froze until `norm_qa` + skip Gemma.
- Backlog: phrase buffer, hub no-Gemma, background preload — implemented same day.
- User asked for planning rules/skills — this file + `gemy-planning`.
