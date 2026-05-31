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

# Closed vocabulary — must match greeter.REACTIONS + off (see gemy_reactions.py).
VALID_MOODS = frozenset({
    "gemy", "greet", "funny", "nice", "mean", "sad", "yes", "no",
    "neutral", "off",
})

# Single line the model must choose from (deterministic label picker, not chat).
ALLOWED_LABELS_LINE = "gemy greet funny nice mean sad yes no off neutral"

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

# Never valid Gemma output (not in ALLOWED_LABELS_LINE).
_REJECT_LABELS = frozenset({
    "paris", "london", "france", "maybe", "perhaps", "sorry", "because",
    "the", "and", "but", "mood", "label", "answer", "response",
    "happy", "glad", "curious", "confused", "unknown", "think",
})

_PROMPT_HEADER = """You are a strict LABEL PICKER for robot Gemy. You are NOT a chatbot.
Gemy has NO voice. It can ONLY play pre-made beep/LED patterns — one label triggers one pattern.

ALLOWED OUTPUT — exactly ONE word, copied from this list, nothing else:
""" + ALLOWED_LABELS_LINE + """

FORBIDDEN: sentences, explanations, place names, numbers as answers, new moods,
or any word not in the list. Wrong examples (never do this): paris, happy, hello there,
the answer is yes, I think funny, 42, capital.

If nothing fits, output exactly: neutral
When unsure, output exactly: neutral

Beep meanings (pick the closest label only):
- yes = one green beep (agree OR true yes/no quiz)
- no = two red beeps (disagree OR false yes/no quiz)
- neutral = soft beep (cannot answer with beeps only)
- greet = hello / hi
- gemy = they said the robot name
- funny = joke / haha
- nice = thanks / compliment
- mean = insult at Gemy
- sad = sad news / lonely (not insults)
- off = turn off / stop listening
"""

_MOOD_PROMPT = _PROMPT_HEADER + """
Classify what they said (not a quiz — pick mood or yes/no only if clearly stated).

What they said: "{text}"
Label:"""

_MOOD_PROMPT_QUESTION = _PROMPT_HEADER + """
They asked a QUESTION. Gemy cannot speak the answer.
- yes: ONLY true/false question AND answer is true (is the sky blue)
- no: ONLY true/false question AND answer is false
- neutral: what/who/where/why, trivia, math you cannot verify, opinions, stories
  (what is the capital of France -> neutral)
- Do NOT output facts. Do NOT guess yes/no for open questions.

What they asked: "{text}"
Label:"""

_MOOD_PROMPT_MATH = _PROMPT_HEADER + """
They asked a MATH yes/no quiz. Output ONLY: yes, no, or neutral.
- yes: the math check is true
- no: the math check is false
- neutral: not a clear math check or you are unsure
Do NOT output numbers or words like twenty-one — only yes, no, or neutral.

What they asked: "{text}"
Label:"""


def mood_prompt_for(text: str) -> str:
    """Pick strict prompt: math quiz, question, or general."""
    low = text.lower()
    try:
        import gemy_math
        if gemy_math.looks_like_math_quiz(low):
            return _MOOD_PROMPT_MATH
    except ImportError:
        pass
    try:
        import gemy_qa
        if gemy_qa.looks_like_question(low):
            return _MOOD_PROMPT_QUESTION
    except ImportError:
        pass
    return _MOOD_PROMPT


def _strip_label_boilerplate(raw: str) -> str:
    s = str(raw).strip().lower()
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    for prefix in (
        "the label is", "the mood is", "the answer is", "label is", "mood is",
        "answer is", "response is", "i choose", "output", "label", "mood", "answer",
    ):
        if s.startswith(prefix):
            s = s[len(prefix):].strip()
    return s


def _word_to_mood(word: str) -> str | None:
    if not word or word in _REJECT_LABELS:
        return None
    if word in VALID_MOODS:
        return word
    return _MOOD_ALIASES.get(word)


def normalize_mood_label(raw: str) -> str | None:
    """Map raw model text to one allowed label, or None if unknown (caller -> neutral)."""
    if not raw or not str(raw).strip():
        return None
    s = _strip_label_boilerplate(raw)
    if not s:
        return None
    words = re.findall(r"[a-z]+", s)
    if not words:
        return None
    if len(words) == 1:
        return _word_to_mood(words[0])
    # Multi-token output: collect unique moods in order; reject ambiguity.
    found: list[str] = []
    for w in words:
        m = _word_to_mood(w)
        if m and m not in found:
            found.append(m)
    if len(found) == 1:
        return found[0]
    if len(found) > 1:
        # e.g. "yes no" or "funny nice" -> not deterministic
        return "neutral"
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

    def unload(self) -> None:
        """Drop model from RAM/NPU so Moonshine can use the accelerator."""
        with self._lock:
            self._backend = None
        try:
            import gc
            gc.collect()
        except Exception:
            pass

    def classify(self, text: str) -> str | None:
        if not self._backend or not text.strip():
            return None
        safe = text.replace('"', "'").replace("\n", " ")[:240]
        prompt = mood_prompt_for(text).format(text=safe)
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
        self._prewarm_busy = False
        self._prewarm_cancel = threading.Event()
        self._assist_cooldown_until = 0.0
        self._model_loaded = False
        self._npu_resident = False

    @property
    def ready(self) -> bool:
        return self._state == "ready"

    @property
    def loading(self) -> bool:
        return self._state == "loading"

    def warm_worker(self) -> None:
        """Start worker process early (READY fast; model loads on first C| or P|)."""
        if self._state in ("loading", "ready"):
            return
        if self._state == "failed":
            return
        self.start()

    def release_npu(self) -> None:
        """Free NPU for Moonshine; kill worker only if soft release fails."""
        if self._classify_busy:
            self._abort_classify(reason="release_npu_busy")
            return
        if not self.release_npu_soft():
            self._abort_classify(reason="release_npu")

    def finish_assist(self) -> None:
        """End one assist — unload model from NPU but keep worker for faster next check."""
        self._classify_busy = False
        self.release_npu_soft()

    def release_npu_soft(self) -> bool:
        """Unload model in worker (R|); keep process. Returns True if NPU is free."""
        if not self._npu_resident:
            return True
        if not self._proc or self._proc.poll() is not None:
            self._npu_resident = False
            return True
        if self._classify_busy or self._prewarm_busy:
            return False
        ok = self._worker_command("R|", timeout_s=4.0)
        if ok:
            self._npu_resident = False
            return True
        return False

    def start_background_preload(self, timeout_s: float = 120.0) -> None:
        """Load Gemma on NPU in a daemon thread (speech_loop never waits for first load)."""
        self.start_prewarm_background(timeout_s=timeout_s)

    def _trace(self, event: str, detail: str = "") -> None:
        try:
            import gemy_trace
            gemy_trace.trace(event, detail)
        except ImportError:
            pass

    def cancel_prewarm(self, wait_s: float = 3.0) -> bool:
        """Stop background P| preload so Moonshine can use the NPU (avoid killing worker mid-load)."""
        self._trace("prewarm_cancel", f"wait={wait_s:.1f}s")
        self._prewarm_cancel.set()
        deadline = time.time() + max(0.1, float(wait_s))
        while self._prewarm_busy and time.time() < deadline:
            time.sleep(0.05)
        if self._prewarm_busy:
            self._trace("prewarm_cancel_timeout", "abort worker")
            self._abort_classify(reason="cancel_prewarm_timeout")
            return False
        self._trace("prewarm_cancel_ok", "")
        return True

    def start_prewarm_background(self, timeout_s: float = 45.0) -> None:
        """Try to load Gemma on NPU between phrases (listen will cancel via ensure_npu)."""
        if self._prewarm_busy:
            self._trace("prewarm_skip", "already busy")
            return
        self._prewarm_cancel.clear()
        self._trace("prewarm_scheduled", f"timeout={timeout_s:.0f}s")

        def _run():
            if self._prewarm_cancel.is_set():
                self._trace("prewarm_aborted", "cancel before start")
                return
            if self._npu_resident or self._classify_busy:
                self._trace("prewarm_skip", "npu busy or classifying")
                return
            if self._state == "idle":
                self._trace("prewarm_warm_worker", "")
                self.warm_worker()
            if self._prewarm_cancel.is_set():
                return
            if not self._ready.wait(timeout=min(30.0, timeout_s)):
                self._trace("prewarm_fail", "worker not READY in time")
                return
            if self._npu_resident or self._prewarm_cancel.is_set():
                return
            self._prewarm_busy = True
            try:
                # Chunked P| so cancel_prewarm can stop between attempts (full load may retry).
                chunk = min(15.0, float(timeout_s))
                left = float(timeout_s)
                attempt = 0
                while left > 0 and not self._prewarm_cancel.is_set():
                    attempt += 1
                    self._trace("prewarm_P_start", f"attempt={attempt} chunk={chunk:.0f}s left={left:.0f}s")
                    t0 = time.time()
                    if self._worker_command("P|", timeout_s=chunk):
                        self._model_loaded = True
                        self._npu_resident = True
                        self._trace("prewarm_P_ok", f"{time.time() - t0:.1f}s")
                        return
                    self._trace("prewarm_P_chunk_fail", f"{time.time() - t0:.1f}s left={left:.0f}s")
                    left -= chunk
                if self._prewarm_cancel.is_set():
                    self._trace("prewarm_aborted", "cancel during P|")
            finally:
                self._prewarm_busy = False

        threading.Thread(target=_run, name="gemma-prewarm", daemon=True).start()

    def _worker_command(self, cmd: str, timeout_s: float = 4.0) -> bool:
        if not self._proc or self._proc.poll() is not None or not self.ready:
            self._trace("worker_cmd_skip", f"{cmd!r} proc={self._proc!r} ready={self.ready}")
            return False
        self._trace("worker_cmd_start", f"{cmd!r} timeout={timeout_s:.0f}s")
        result: list[bool] = [False]

        def _io():
            try:
                with self._io_lock:
                    self._proc.stdin.write(f"{cmd}\n")
                    self._proc.stdin.flush()
                    deadline = time.time() + timeout_s
                    while time.time() < deadline:
                        raw = self._proc.stdout.readline()
                        if not raw:
                            break
                        line = raw.strip()
                        if line in ("OK", "READY"):
                            result[0] = True
                            return
                        if line.startswith("L|"):
                            return
                        if line == "FAIL":
                            return
            except Exception:
                pass

        th = threading.Thread(target=_io, name="gemma-cmd", daemon=True)
        th.start()
        th.join(timeout=timeout_s + 0.5)
        if th.is_alive():
            self._trace("worker_cmd_hung", f"{cmd!r} >{timeout_s:.0f}s")
            return False
        ok = result[0]
        self._trace("worker_cmd_done", f"{cmd!r} ok={ok}")
        return ok

    def _abort_classify(self, reason: str = "abort") -> None:
        """Kill worker mid-inference or when soft release fails."""
        self._trace("worker_abort", f"reason={reason} state={self._state}")
        try:
            import gemy_diag
            gemy_diag.log("gemma_abort", f"reason={reason} state={self._state}")
        except Exception:
            pass
        self._classify_busy = False
        self._prewarm_busy = False
        self._npu_resident = False
        if self._proc and self._proc.poll() is None:
            try:
                self._proc.kill()
            except Exception:
                pass
        self._proc = None
        self._state = "idle"
        self._ready.clear()
        self._error = None
        try:
            import hat
            hat.force_all_off()
        except Exception:
            pass

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
        t0 = time.time()
        self._trace("classify_C_start", f"timeout={infer_timeout_s:.0f}s text={safe[:40]!r}")
        try:
            t = threading.Thread(target=_do_io, name="gemma-classify", daemon=True)
            t.start()
            t.join(timeout=infer_timeout_s + 0.5)
            if t.is_alive():
                self._trace("classify_C_hung", f">{infer_timeout_s:.0f}s")
                print(
                    f"[gemma] assist timed out ({infer_timeout_s:.0f}s); "
                    "freeing NPU for ears.",
                    flush=True,
                )
                self._abort_classify(reason="classify_timeout")
                self._assist_cooldown_until = time.time() + 20.0
                return None
            if err_box[0]:
                print(f"[gemma] worker classify I/O failed: {err_box[0]}", flush=True)
                self._abort_classify(reason="worker_fail")
                self._assist_cooldown_until = time.time() + 20.0
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
                self._assist_cooldown_until = time.time() + 20.0
                return None
            line = line_box[0] or ""
            if not line.startswith("L|"):
                return None
            label = mood_for_reaction(line[2:].strip())
            self._model_loaded = True
            self._npu_resident = True
            self._trace("classify_C_ok", f"{time.time() - t0:.1f}s label={label!r}")
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
