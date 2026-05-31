#!/usr/bin/env python3
"""Gemma 3 mood classification for Gemy (text in -> one mood label out).

Loads in a background thread by default so greeter.py can start listening immediately.

HARDWARE: This module returns mood labels only. Never drive buzzer/LEDs here.
All output goes through greeter.py -> hat.py (max 2s ON per segment).
"""
from __future__ import annotations

import os
import re
import subprocess
import threading
import time

_GEMMA_WORKER = "/home/root/gemma_mood_worker.py"
_VENV_PY = "/home/root/sl2610-examples/.venv/bin/python3"

# Labels greeter.py can react to (neutral = no Gemma override when returned alone).
VALID_MOODS = frozenset({
    "gemy", "greet", "funny", "nice", "mean", "sad", "yes", "no",
    "neutral", "off",
})

_MOOD_ALIASES = {
    "insult": "mean", "rude": "mean", "negative": "mean", "angry": "mean",
    "mad": "mean", "bully": "mean", "bullying": "mean",
    "joke": "funny", "humor": "funny", "humour": "funny", "laugh": "funny",
    "laughing": "funny", "hilarious": "funny", "comedy": "funny",
    "compliment": "nice", "positive": "nice", "kind": "nice", "thanks": "nice",
    "thank": "nice", "grateful": "nice", "praise": "nice",
    "hello": "greet", "greeting": "greet", "hi": "greet", "hey": "greet",
    "howdy": "greet",
    "name": "gemy", "robot": "gemy",
    "cry": "sad", "crying": "sad", "upset": "sad", "lonely": "sad",
    "depressed": "sad", "hurt": "sad", "grief": "sad", "sorrow": "sad",
    "affirmative": "yes", "agree": "yes", "correct": "yes", "true": "yes",
    "deny": "no", "disagree": "no", "incorrect": "no", "false": "no",
    "stop": "off", "shutdown": "off", "sleep": "off", "goodbye": "off",
    "bye": "off", "quit": "off", "exit": "off",
}

_MOOD_PROMPT = """You classify what a person said to a small robot named Gemy.
Reply with EXACTLY ONE WORD from this list only:
gemy, greet, funny, nice, mean, sad, yes, no, off, neutral

Rules:
- gemy: they say the robot's name (Gemy, Gemi, Jemmy) without asking to stop
- greet: hello, hi, hey, good morning
- funny: jokes, punchlines, haha, lol, knock-knock
- nice: compliments, thanks, love, you're awesome, kindness
- mean: insults, hate, rude, shut up, stupid, go away (angry at the robot)
- sad: lonely, rejection, bad news, crying, nobody likes you, leaving forever
- yes: agreeing (yes, yeah, sure, correct, I agree) OR true quiz answers (one plus one is two)
- no: disagreeing (no, nope, nah, wrong) OR false quiz answers (one plus one is five)
- off: turn off, stop listening, go to sleep, Gemy turn off, power down
- neutral: unclear or small talk that fits none of the above

Output ONLY one word from the list. No punctuation or explanation.

What they said: "{text}"
One word:"""


def normalize_mood_label(raw: str) -> str | None:
    """Map raw model text to a valid mood id, or None if unknown / empty."""
    if not raw or not str(raw).strip():
        return None
    for word in re.findall(r"[a-z]+", str(raw).lower()):
        if word in VALID_MOODS:
            return word
        if word in _MOOD_ALIASES:
            return _MOOD_ALIASES[word]
    return None


def mood_for_reaction(raw: str) -> str | None:
    """Safe label for greeter reactions: unknown or neutral -> None (use neutral)."""
    label = normalize_mood_label(raw)
    if not label or label == "neutral":
        return None
    if label not in VALID_MOODS:
        print(f"[gemma] unknown mood {label!r} -> neutral", flush=True)
        return None
    return label


def _parse_mood_label(raw: str) -> str | None:
    return mood_for_reaction(raw)


def _gemma_progress(msg: str) -> None:
    """Worker uses stdout only for READY / L| lines; logs go to stderr."""
    import sys
    if os.environ.get("GEMMA_WORKER"):
        print(msg, file=sys.stderr, flush=True)
    else:
        print(msg, flush=True)


class GemmaMoodClassifier:
    """Thread-safe wrapper around GemmaBackend for mood labels."""

    def __init__(self):
        self._backend = None
        self._lock = threading.Lock()

    @property
    def ready(self) -> bool:
        return self._backend is not None

    def load(self) -> None:
        try:
            from utils.npu import enable_npu_clock
            ok, msg = enable_npu_clock()
            _gemma_progress(f"[gemma] NPU: {msg}")
        except Exception as e:
            _gemma_progress(f"[gemma] NPU clock skipped: {e}")

        from utils.gemma import load_gemma

        _gemma_progress(
            "[gemma] loading Gemma 3 270M on NPU (first time can take 1-3 min)...")
        t0 = time.time()
        self._backend = load_gemma(
            use_llama=False, model_path=None, instruct_model=True
        )
        _gemma_progress(f"[gemma] mood model ready ({time.time() - t0:.1f}s).")

    def classify(self, text: str) -> str | None:
        if not self._backend or not text.strip():
            return None
        safe = text.replace('"', "'").replace("\n", " ")[:240]
        prompt = _MOOD_PROMPT.format(text=safe)
        t0 = time.time()
        raw = ""
        try:
            with self._lock:
                for partial in self._backend.stream_response(prompt):
                    raw = str(partial)
        except Exception as e:
            _gemma_progress(f"[gemma] mood inference failed: {e}")
            return None
        elapsed = time.time() - t0
        label = mood_for_reaction(raw)
        if label:
            _gemma_progress(f"[gemma] mood={label} ({elapsed:.1f}s) raw={raw!r}")
        else:
            unk = normalize_mood_label(raw)
            if unk == "neutral":
                _gemma_progress(f"[gemma] mood=neutral ({elapsed:.1f}s)")
            else:
                _gemma_progress(
                    f"[gemma] unknown/unparsed mood ({elapsed:.1f}s) raw={raw!r} -> neutral")
        return label


class GemmaMoodLoader:
    """Load Gemma in the background; classify when ready (keywords until then)."""

    def __init__(self):
        self._classifier = None
        self._lock = threading.Lock()
        self._state = "idle"  # idle | loading | ready | failed
        self._error = None
        self._thread = None
        self._started = 0.0
        self._timeout_s = 120.0
        self._last_progress = 0.0

    @property
    def ready(self) -> bool:
        return self._state == "ready" and self._classifier is not None

    @property
    def loading(self) -> bool:
        return self._state == "loading"

    def start_background(self, timeout_s: float = 120.0) -> "GemmaMoodLoader":
        if self._state == "loading":
            return self
        self._timeout_s = timeout_s
        self._state = "loading"
        self._started = time.time()
        self._last_progress = self._started
        self._thread = threading.Thread(target=self._load_worker, name="gemma-load",
                                        daemon=True)
        self._thread.start()
        return self

    def _progress(self):
        now = time.time()
        if now - self._last_progress < 10.0:
            return
        self._last_progress = now
        elapsed = int(now - self._started)
        print(f"[gemma] still loading ({elapsed}s)... wave/voice use keywords for now.",
              flush=True)

    def _load_worker(self):
        try:
            try:
                import os
                os.nice(10)
            except Exception:
                pass
            classifier = GemmaMoodClassifier()
            classifier.load()
            with self._lock:
                self._classifier = classifier
                self._state = "ready"
            print("[gemma] mood online — Gemma 3 will classify funny/mean/nice.", flush=True)
        except Exception as e:
            with self._lock:
                self._state = "failed"
                self._error = str(e)
            print(f"[gemma] mood load failed ({e}); keywords only.", flush=True)

    def classify(self, text: str) -> str | None:
        if self._state == "loading":
            if time.time() - self._started > self._timeout_s:
                with self._lock:
                    if self._state == "loading":
                        self._state = "failed"
                        self._error = "timeout"
                print("[gemma] mood load timed out; using keywords (reload greeter to retry).",
                      flush=True)
            else:
                self._progress()
        if not self.ready or self._classifier is None:
            return None
        return self._classifier.classify(text)


class GemmaMoodSubprocess:
    """Gemma in a child process so greeter stays responsive while listening."""

    def __init__(self, timeout_s: float = 180.0):
        self._timeout_s = timeout_s
        self._state = "idle"  # idle | loading | ready | failed
        self._error = None
        self._started = 0.0
        self._proc = None
        self._io_lock = threading.Lock()
        self._ready = threading.Event()
        self._stderr_thread = None
        self._classify_busy = False
        self._assist_cooldown_until = 0.0

    @property
    def ready(self) -> bool:
        return self._state == "ready"

    @property
    def loading(self) -> bool:
        return self._state == "loading"

    def release_npu(self) -> None:
        """Stop worker so Moonshine can use the NPU (SL2610 has one shared accelerator)."""
        self._abort_classify(reason="release_npu")

    def finish_assist(self) -> None:
        """End one assist attempt; always release NPU before the next listen."""
        self._abort_classify(reason="finish_assist")

    def _abort_classify(self, reason: str = "abort") -> None:
        """Kill worker mid-inference so Moonshine can use the NPU again."""
        try:
            import gemy_diag
            gemy_diag.log("gemma_abort", f"reason={reason} state={self._state}")
        except Exception:
            pass
        self._classify_busy = False
        if self._proc and self._proc.poll() is None:
            try:
                self._proc.kill()
            except Exception:
                pass
        self._proc = None
        self._state = "idle"
        self._ready.clear()
        self._error = None

    def acquire_npu(self, wait: bool = True) -> bool:
        """Start worker and wait until Gemma is loaded on the NPU."""
        if self._state == "ready":
            return True
        if self._state != "loading":
            self.start()
        if not wait:
            return False
        return self._ready.wait(timeout=self._timeout_s)

    def start(self) -> "GemmaMoodSubprocess":
        if self._state == "loading":
            return self
        if not os.path.isfile(_GEMMA_WORKER):
            print(f"[gemma] missing {_GEMMA_WORKER}; keywords only.", flush=True)
            self._state = "failed"
            return self
        py = _VENV_PY if os.path.isfile(_VENV_PY) else "python3"
        self._state = "loading"
        self._started = time.time()
        print("[gemma] starting mood worker (loads on first assist only)...",
              flush=True)
        work_cwd = "/home/root" if os.path.isdir("/home/root") else os.path.dirname(
            os.path.abspath(_GEMMA_WORKER))
        try:
            self._proc = subprocess.Popen(
                [py, "-u", _GEMMA_WORKER],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                cwd=work_cwd,
                env={
                    **os.environ,
                    "PYTHONPATH": "/home/root/sl2610-examples:/home/root",
                    "GEMMA_WORKER": "1",
                },
            )
        except Exception as e:
            self._state = "failed"
            self._error = str(e)
            print(f"[gemma] could not start worker ({e}); keywords only.", flush=True)
            return self

        self._stderr_thread = threading.Thread(
            target=self._drain_stderr, name="gemma-worker-err", daemon=True)
        self._stderr_thread.start()
        threading.Thread(
            target=self._wait_ready, name="gemma-worker-wait", daemon=True).start()
        return self

    def _drain_stderr(self):
        try:
            for line in self._proc.stderr:
                line = line.rstrip()
                if line:
                    print(line, flush=True)
        except Exception:
            pass

    def _wait_ready(self):
        try:
            while self._proc and self._proc.poll() is None:
                if time.time() - self._started > self._timeout_s:
                    self._fail("timeout waiting for worker")
                    return
                line = None
                try:
                    import select
                    ready, _, _ = select.select([self._proc.stdout], [], [], 2.0)
                    if ready:
                        line = self._proc.stdout.readline()
                except Exception:
                    line = self._proc.stdout.readline()
                if not line:
                    continue
                line = line.strip()
                if line in ("OK", "READY"):
                    self._state = "ready"
                    self._ready.set()
                    try:
                        import gemy_diag
                        gemy_diag.log("gemma_worker", f"line={line}")
                    except Exception:
                        pass
                    if line == "OK":
                        print("[gemma] mood model loaded in worker.", flush=True)
                    else:
                        print("[gemma] mood worker ready - keywords first; Gemma on unclear.",
                              flush=True)
                    return
                if line == "FAIL":
                    self._fail("worker reported FAIL")
                    return
            code = self._proc.poll() if self._proc else -1
            if self._state == "loading":
                self._fail(f"worker exited ({code})")
        except Exception as e:
            self._fail(str(e))

    def _fail(self, msg: str):
        self._state = "failed"
        self._error = msg
        try:
            import gemy_diag
            gemy_diag.log("gemma_fail", msg)
        except Exception:
            pass
        print(f"[gemma] mood load failed ({msg}); keywords only.", flush=True)
        try:
            if self._proc and self._proc.poll() is None:
                self._proc.kill()
        except Exception:
            pass

    def classify(self, text: str, infer_timeout_s: float = 90.0) -> str | None:
        try:
            return self._classify_impl(text, infer_timeout_s)
        except Exception as e:
            print(f"[gemma] classify error ({e}); neutral.", flush=True)
            return None

    def _classify_impl(self, text: str, infer_timeout_s: float = 90.0) -> str | None:
        if time.time() < self._assist_cooldown_until:
            return None
        if self._classify_busy:
            return None
        if self._state == "loading":
            if time.time() - self._started > self._timeout_s:
                self._fail("timeout")
            return None
        if not self.ready or not self._proc or self._proc.poll() is not None:
            return None
        if not text.strip():
            return None
        safe = text.replace("\n", " ").replace("|", " ")[:240]
        line_box: list[str | None] = [None]
        err_box: list[str | None] = [None]
        junk_box: list[str] = []

        def _do_io():
            deadline = time.time() + infer_timeout_s
            try:
                with self._io_lock:
                    self._proc.stdin.write(f"C|{safe}\n")
                    self._proc.stdin.flush()
                    while time.time() < deadline:
                        raw = self._proc.stdout.readline()
                        if not raw:
                            break
                        line = raw.strip()
                        if not line:
                            continue
                        if line.startswith("L|"):
                            line_box[0] = line
                            return
                        if line == "FAIL":
                            err_box[0] = "FAIL"
                            return
                        junk_box.append(line)
            except Exception as e:
                err_box[0] = str(e)

        self._classify_busy = True
        try:
            t = threading.Thread(target=_do_io, name="gemma-classify", daemon=True)
            t.start()
            t.join(timeout=infer_timeout_s + 0.5)
            if t.is_alive():
                print(
                    f"[gemma] assist timed out ({infer_timeout_s:.0f}s); "
                    "freeing NPU for ears.",
                    flush=True,
                )
                self._abort_classify(reason="classify_timeout")
                self._assist_cooldown_until = time.time() + 45.0
                return None
            if err_box[0]:
                print(f"[gemma] worker classify I/O failed: {err_box[0]}", flush=True)
                self._abort_classify(reason="worker_fail")
                self._assist_cooldown_until = time.time() + 45.0
                return None
            if junk_box:
                print(
                    f"[gemma] worker sent {len(junk_box)} non-protocol line(s) on stdout; "
                    "killing worker to free NPU.",
                    flush=True,
                )
                for j in junk_box[:3]:
                    print(f"[gemma]   junk: {j[:100]}", flush=True)
                try:
                    import gemy_diag
                    gemy_diag.log("gemma_classify", f"junk_stdout={junk_box[0]!r}")
                except Exception:
                    pass
                self._abort_classify(reason="junk_stdout")
                self._assist_cooldown_until = time.time() + 45.0
                return None
            line = line_box[0] or ""
            if not line.startswith("L|"):
                return None
            label = mood_for_reaction(line[2:].strip())
            try:
                import gemy_diag
                gemy_diag.log("gemma_classify", f"label={label!r}")
            except Exception:
                pass
            return label
        finally:
            self._classify_busy = False

    def stop(self):
        try:
            if self._proc and self._proc.poll() is None:
                self._proc.kill()
        except Exception:
            pass


def load_gemma_before_speech(on_progress=None):
    """Load Gemma on the main thread before Moonshine (not recommended on SL2610)."""
    print("[gemma] loading before speech (in-process)...", flush=True)
    t0 = time.time()
    try:
        from utils.npu import enable_npu_clock
        ok, msg = enable_npu_clock()
        print(f"[gemma] NPU: {msg}", flush=True)
    except Exception as e:
        print(f"[gemma] NPU clock skipped: {e}", flush=True)
    try:
        classifier = GemmaMoodClassifier()
        if on_progress:
            on_progress()
        classifier.load()
        print(f"[gemma] mood ready ({time.time() - t0:.1f}s).", flush=True)
        return classifier
    except Exception as e:
        print(f"[gemma] mood load failed ({e}); keywords only.", flush=True)
        return None


def create_gemma_mood_loader(timeout_s: float = 120.0) -> GemmaMoodLoader:
    """Return a loader that is not started yet (greeter starts it after [ears] on)."""
    loader = GemmaMoodLoader()
    loader._timeout_s = timeout_s
    return loader


def start_gemma_mood_background(timeout_s: float = 120.0) -> GemmaMoodLoader:
    print("[gemma] mood will load in background (do not wait — listen for [ears] on).",
          flush=True)
    return GemmaMoodLoader().start_background(timeout_s)
