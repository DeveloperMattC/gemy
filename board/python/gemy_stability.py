#!/usr/bin/env python3
"""Keep Gemy alive: session heartbeat + NPU rules so Gemma never freezes the board."""
from __future__ import annotations

import threading
import time

# Hard cap on blocking the ears thread for one Gemma assist (seconds).
GEMMA_ASSIST_MAX_BLOCK_S = 5.0

# Minimum gap between Gemma assist attempts (NPU + worker churn).
GEMMA_ASSIST_MIN_INTERVAL_S = 90.0

# Phrase must look like real speech, not a STT fragment.
GEMMA_MIN_WORDS = 4
GEMMA_MIN_CHARS = 20

_STUCK_PHASES = frozenset({
    "listen_wait", "gemma_assist", "gemma_classify",
    "react_greet", "react_funny", "react_nice", "react_mean", "react_sad",
    "react_neutral", "react_gemy", "react_yes", "react_no",
})
# Moonshine+VAD can block a long time; never hold the ears thread forever.
LISTEN_ONCE_MAX_S = 60.0

_STUCK_LISTEN_S = 45.0
_STUCK_GEMMA_S = 12.0
_STUCK_REACT_S = 18.0

_last_gemma_assist_at = 0.0
_last_gemma_lock = threading.Lock()


def _now() -> float:
    return time.time()


def record_gemma_assist_attempt() -> None:
    global _last_gemma_assist_at
    with _last_gemma_lock:
        _last_gemma_assist_at = _now()


def seconds_since_last_gemma_assist() -> float:
    with _last_gemma_lock:
        if _last_gemma_assist_at <= 0:
            return 1e9
        return _now() - _last_gemma_assist_at


def ensure_npu_for_ears(gemma_mood) -> None:
    """Moonshine needs the NPU — never leave a Gemma worker running before listen."""
    if gemma_mood is None:
        return
    if hasattr(gemma_mood, "release_npu"):
        busy = getattr(gemma_mood, "_classify_busy", False)
        proc = getattr(gemma_mood, "_proc", None)
        if proc is not None or busy:
            gemma_mood.release_npu()
            print("[stability] NPU released for ears (Gemma worker stopped).", flush=True)


def finish_gemma_assist(gemma_mood) -> None:
    """Always call after assist — do not keep Gemma on the NPU between phrases."""
    if gemma_mood is None:
        return
    record_gemma_assist_attempt()
    if hasattr(gemma_mood, "finish_assist"):
        gemma_mood.finish_assist()
    elif hasattr(gemma_mood, "release_npu"):
        gemma_mood.release_npu()


def gemma_assist_allowed(text, low, words, joke_tracker=None) -> tuple[bool, str]:
    """When False, use neutral without touching the NPU."""
    stripped = low.strip()
    if len(stripped) < 4:
        return False, "too short"
    if len(words) <= 1 and len(stripped) < 6:
        return False, "fragment"
    if len(words) < GEMMA_MIN_WORDS and len(stripped) < GEMMA_MIN_CHARS:
        return False, f"need {GEMMA_MIN_WORDS}+ words or {GEMMA_MIN_CHARS}+ chars"
    if joke_tracker is not None and getattr(joke_tracker, "active", False):
        return False, "joke in progress"
    gap = seconds_since_last_gemma_assist()
    if gap < GEMMA_ASSIST_MIN_INTERVAL_S:
        return False, f"rate limit ({GEMMA_ASSIST_MIN_INTERVAL_S - gap:.0f}s left)"
    return True, ""


def start_session_heartbeat(stop_event, greeter, interval_s: float = 1.6):
    """Red LED pulse for whole session — proves the board is not frozen."""

    def _loop():
        try:
            import gemy_diag
        except ImportError:
            gemy_diag = None
        try:
            import hat
        except ImportError:
            return
        print("[stability] session heartbeat ON (red blink while Gemy runs).", flush=True)
        while not stop_event.wait(interval_s):
            if greeter is not None and getattr(greeter, "_reacting", False):
                continue
            try:
                hat.hold_led("red", 0.1)
                if gemy_diag is not None:
                    gemy_diag.mark_heartbeat_pulse("session")
                if greeter is not None:
                    greeter.touch()
            except Exception as e:
                print(f"[stability] heartbeat pulse failed: {e}", flush=True)

    threading.Thread(target=_loop, name="session-heartbeat", daemon=True).start()


def recover_audio_source(source) -> None:
    """Try to unblock a hung listen_once by resetting the mic stream."""
    if source is None:
        return
    for meth in ("stop", "close", "reset"):
        fn = getattr(source, meth, None)
        if callable(fn):
            try:
                fn()
                print(f"[stability] audio source.{meth}()", flush=True)
            except Exception as e:
                print(f"[stability] audio {meth} failed: {e}", flush=True)
    time.sleep(0.35)
    for meth in ("start", "open", "resume"):
        fn = getattr(source, meth, None)
        if callable(fn):
            try:
                fn()
                print(f"[stability] audio source.{meth}() OK", flush=True)
                return
            except Exception as e:
                print(f"[stability] audio {meth} failed: {e}", flush=True)


def listen_once_timed(recognizer, source, stop_event, gemma_mood=None,
                      timeout_s: float | None = None):
    """Run listen_once in a thread; reset mic if it blocks too long."""
    timeout_s = timeout_s if timeout_s is not None else LISTEN_ONCE_MAX_S
    box: dict = {"result": None, "error": None}

    def _run():
        try:
            box["result"] = recognizer.listen_once(stop_event=stop_event)
        except Exception as e:
            box["error"] = e

    th = threading.Thread(target=_run, name="listen-once", daemon=True)
    th.start()
    th.join(timeout=timeout_s)
    if th.is_alive():
        print(
            f"[stability] listen_once hung >{timeout_s:.0f}s — resetting mic, continuing.",
            flush=True,
        )
        ensure_npu_for_ears(gemma_mood)
        recover_audio_source(source)
        try:
            import gemy_diag
            gemy_diag.log("listen_timeout", f">{timeout_s:.0f}s")
            gemy_diag.set_phase("listen_recovered", "timeout")
        except ImportError:
            pass
        return None
    if box["error"] is not None:
        raise box["error"]
    return box["result"]


def start_stuck_guard(stop_event, gemma_mood=None, greeter=None, source=None,
                      interval_s: float = 12.0):
    """If ears/Gemma/react stall, recover mic + free NPU."""

    def _loop():
        try:
            import gemy_diag
        except ImportError:
            return
        while not stop_event.wait(interval_s):
            phase, detail, ago = gemy_diag.get_phase_age()
            if ago < 0:
                continue
            limit = _STUCK_LISTEN_S
            if phase.startswith("gemma"):
                limit = _STUCK_GEMMA_S
            elif phase.startswith("react_"):
                limit = _STUCK_REACT_S
            elif phase not in _STUCK_PHASES:
                continue
            if ago < limit:
                continue
            print(
                f"[stability] STUCK {phase!r} for {ago:.0f}s ({detail}) — recovering.",
                flush=True,
            )
            if phase == "listen_wait":
                recover_audio_source(source)
            ensure_npu_for_ears(gemma_mood)
            gemy_diag.log("stuck_recovery", f"{phase} {ago:.0f}s")
            gemy_diag.set_phase("listen_recovered", f"stuck {phase}")

    threading.Thread(target=_loop, name="stuck-guard", daemon=True).start()
    print(
        f"[stability] stuck guard ON (listen >{_STUCK_LISTEN_S:.0f}s or "
        f"listen_once >{LISTEN_ONCE_MAX_S:.0f}s recovers).",
        flush=True,
    )
