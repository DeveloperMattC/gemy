# Architecture

## System context

```mermaid
flowchart LR
  subgraph Host["Windows PC"]
    HUB[Control Center browser UI]
    GREET[greet-demo.ps1]
    ADB[adb]
    ICS[USB NCM + ICS]
  end

  subgraph Board["Coralboard Linux"]
  direction TB
    GREETER[greeter.py]
    HAT[hat.py]
    SPEECH[utils/speech.py]
    VENV[.venv OpenCV Moonshine]
    HW["HAT: cam mic LED buzzer"]
  end

  HUB --> GREET
  GREET --> ADB
  ADB --> GREETER
  ICS --> Board
  GREETER --> HAT
  GREETER --> SPEECH
  HAT --> HW
  SPEECH --> HW
  VENV --> GREETER
```

---

## `greeter.py` internal architecture

```mermaid
flowchart TB
  subgraph MainThread["Main thread"]
    CAM[Open camera + exposure]
    VIS[Vision loop capped at 8 fps]
    WAVE[Wave: motion reversals]
    HAND[Hand-up: background FG]
  end

  subgraph EarsThread["ears thread"]
    VAD[Silero VAD segments]
    STT[Moonshine transcribe]
    KW[classify_utterance keywords math]
    GEM[try_gemma_mood_assist optional]
    RES[resolve_reaction_kind]
  end

  subgraph IdleThread["idle thread"]
    IDLE[idle_check every 2s]
  end

  subgraph Dispatcher["Greeter.react"]
    COOL[cooldown lock]
    RX[REACTIONS gemy greet funny nice mean sad yes no neutral]
  end

  CAM --> VIS
  VIS --> WAVE
  VIS --> HAND
  WAVE --> Dispatcher
  HAND --> Dispatcher
  VAD --> STT --> CLS --> Dispatcher
  Dispatcher --> HAT[hat.py]
  IDLE --> HAT
  RX --> HAT
```

---

## Data flow: speech path

```
PDM microphone (HAT)
    → ALSA (klamath-asoc hw:0,0)
    → sounddevice InputStream
    → SileroSpeechSegmenter (utterance boundaries)
    → MoonshineTranscriber (text string)
    → classify_utterance (keywords, yes/no, math, jokes)
    → optional gemma_mood worker (if --gemma-mood and unclear)
    → resolve_reaction_kind → gemy|greet|funny|nice|mean|sad|yes|no|neutral
    → Greeter.react(kind)
    → hat.gemy_funny / gemy_greet / gemy_mean / … (one GPIO lock each)
```

**NPU (one accelerator):** Moonshine uses the NPU during `listen_once`. Gemma loads/runs only **between** listens. Worker `R|` unloads the model before the next listen; `READY` does **not** mean the model is loaded yet. See [LEARNINGS.md](LEARNINGS.md).

**Note:** Default ALSA device works in testing (`device=None`). Device `0` is the hardware capture device; both showed signal in RMS probes.

---

## Data flow: vision path

> **Not Gemma 3.** Camera vision is OpenCV only. Gemma 3 is text-in/text-out for `gemma_translate/` demos. See [07-WAVE-VISION-AND-GEMMA.md](07-WAVE-VISION-AND-GEMMA.md).

```
/dev/video0 (OV5647)
    → OpenCV VideoCapture
    → resize 320×240
    → gray + blur
    → |frame - prev|  → motion mask → wave logic
    → background model → upper-frame FG → hand-up logic
    → Greeter.greet() on wave or hand-up
```

Vision triggers always use reaction **`greet`** (double beep + green).

## Data flow: Gemma 3 translation (separate demo)

```
HAT mic (or typed text)
    → Moonshine STT (voice demo only)
    → gemma_translate/GemmaTranslationService  ← prompts live on board
    → Gemma 3 270M (NPU)
    → translated text (no HAT beep/LED reaction)
```

Run on the board from `/home/root/sl2610-examples/gemma_translate/` — **not** used by `greeter.py`.

---

## Resource ownership

| Resource | Owner | Conflict if |
|----------|-------|-------------|
| `/dev/video0` | One `greeter.py` (vision thread) | Duplicate greeter or stale demo |
| GPIO buzzer line | Last `gpioset` | Stuck ON if not driven HIGH |
| ALSA capture | One `InputStream` | Rare duplicate if two speech apps run |
| CPU (2 cores) | Vision + STT compete | High `--fps` breaks speech |

---

## Reaction state machine (conceptual)

```mermaid
stateDiagram-v2
  [*] --> Idle
  Idle --> GemyName: say Gemy
  Idle --> Greet: wave / hand-up / hello
  GemyName --> Cooldown: signature hello
  Idle --> Funny: haha lol funny
  Idle --> Nice: good love thanks
  Idle --> Mean: stupid hate
  Idle --> Neutral: other speech
  Greet --> Cooldown
  Funny --> Cooldown
  Nice --> Cooldown
  Mean --> Cooldown
  Neutral --> Cooldown
  Cooldown --> Idle: 3s elapsed
  Idle --> ForceOff: 20s no activity
  ForceOff --> Idle
```

---

## Deployment layout on board

```
/home/root/
  greeter.py
  hat.py
  gemma_mood.py
  gemma_mood_worker.py
  gemy_stability.py
  gemy_diag.py
  gemy.log
  sl2610-examples/
    .venv/bin/python3
    utils/speech.py
    gemma_translate/   # optional Synaptics demos
```

---

## Security and scope notes (for reviewers)

- Lab assumes **trusted local USB** access (`adb` as root on board).
- No cloud API required after models are cached on board.
- ICS shares host internet; instructors should disclose network routing to students.
- Sentiment lexicons are intentionally naive — not suitable for production moderation.
