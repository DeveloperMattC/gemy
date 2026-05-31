#!/usr/bin/env python3
"""Keep Gemy alive: session heartbeat + NPU rules so Gemma never freezes the board."""
from __future__ import annotations

import os
import threading
import time

# Block ears thread for one Gemma assist (seconds). First worker classify loads the
# model on NPU (often 30–180s); 5s timeout used to kill mid-load and wedge the board.
GEMMA_ASSIST_MAX_BLOCK_S = 12.0
GEMMA_FIRST_CLASSIFY_MAX_BLOCK_S = 90.0

# Minimum gap between Gemma assist attempts (worker kept alive; shorter than before).
GEMMA_ASSIST_MIN_INTERVAL_S = 40.0

# Phrase must look like real speech, not a STT fragment.
GEMMA_MIN_WORDS = 3
GEMMA_MIN_CHARS = 14

_STUCK_PHASES = frozenset({
    "listen_wait", "gemma_assist", "gemma_classify",
    "react_greet", "react_funny", "react_nice", "react_mean", "react_sad",
    "react_neutral", "react_gemy", "react_yes", "react_no",
})
# Moonshine+VAD can block a long time; never hold the ears thread forever.
LISTEN_ONCE_MAX_S = 60.0

_STUCK_LISTEN_S = 45.0
_STUCK_GEMMA_S = 20.0
_STUCK_GEMMA_FIRST_LOAD_S = 100.0
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


def npu_held_by_gemma(gemma_mood) -> bool:
    """True only when Gemma is on the NPU (not merely a warm idle worker)."""
    if gemma_mood is None:
        return False
    if getattr(gemma_mood, "_classify_busy", False):
        return True
    if getattr(gemma_mood, "_prewarm_busy", False):
        return True
    if getattr(gemma_mood, "_npu_resident", False):
        return True
    return False


def _trace(event: str, detail: str = "") -> None:
    try:
        import gemy_trace
        gemy_trace.trace(event, detail)
    except ImportError:
        pass


def _npu_line(gemma_mood) -> str:
    try:
        import gemy_trace
        return gemy_trace.npu_snapshot(gemma_mood)
    except ImportError:
        return ""


def ensure_npu_for_ears(gemma_mood) -> bool:
    """Moonshine needs the NPU — unload Gemma model before listen (keep worker if possible).

    Returns True if NPU was freed (slow path).
    """
    if not npu_held_by_gemma(gemma_mood):
        return False
    _trace("ensure_npu_start", _npu_line(gemma_mood))
    if getattr(gemma_mood, "_prewarm_busy", False):
        cancel = getattr(gemma_mood, "cancel_prewarm", None)
        if callable(cancel):
            ok = cancel(wait_s=2.5)
            _trace("ensure_npu_prewarm_cancel", f"ok={ok} {_npu_line(gemma_mood)}")
            print("[stability] NPU released for ears (prewarm cancelled).", flush=True)
            return True
        if hasattr(gemma_mood, "release_npu"):
            gemma_mood.release_npu()
            _trace("ensure_npu_prewarm_kill", _npu_line(gemma_mood))
            print("[stability] NPU released for ears (prewarm stopped).", flush=True)
            return True
    if hasattr(gemma_mood, "release_npu_soft"):
        if gemma_mood.release_npu_soft():
            _trace("ensure_npu_soft_release", _npu_line(gemma_mood))
            print("[stability] NPU released for ears (Gemma unloaded, worker kept).",
                  flush=True)
            return True
    if hasattr(gemma_mood, "release_npu"):
        gemma_mood.release_npu()
        _trace("ensure_npu_hard_release", _npu_line(gemma_mood))
        print("[stability] NPU released for ears (Gemma worker stopped).", flush=True)
        return True
    _trace("ensure_npu_failed", _npu_line(gemma_mood))
    return False


def gemma_assist_timeout_s(gemma_mood=None) -> float:
    """How long the ears thread may wait on one classify (longer on first NPU load)."""
    if gemma_mood is not None and not getattr(gemma_mood, "_model_loaded", False):
        return GEMMA_FIRST_CLASSIFY_MAX_BLOCK_S
    return GEMMA_ASSIST_MAX_BLOCK_S


def finish_gemma_assist(gemma_mood) -> None:
    """Always call after assist — unload model from NPU; react() already cleared GPIO."""
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
            import hat as _hat
        except ImportError:
            return
        hold = _hat.hold_led
        print("[stability] session heartbeat ON (red blink while Gemy runs).", flush=True)
        while not stop_event.wait(interval_s):
            if greeter is not None and getattr(greeter, "_reacting", False):
                continue
            try:
                hold("red", 0.1)
                if gemy_diag is not None:
                    gemy_diag.mark_heartbeat_pulse("session")
                    if os.environ.get("GEMY_SMOKE_MONITOR"):
                        n = gemy_diag.heartbeat_pulse_count()
                        print(f"[stability] heartbeat pulse {n}", flush=True)
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
    time.sleep(0.2)
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
    deadline = time.time() + timeout_s
    t0 = time.time()
    last_progress = t0
    while th.is_alive() and time.time() < deadline:
        remaining = deadline - time.time()
        th.join(timeout=min(1.0, max(0.05, remaining)))
        if stop_event.is_set():
            break
        now = time.time()
        if now - last_progress >= 15.0:
            elapsed = now - t0
            _trace(
                "listen_wait_progress",
                f"{elapsed:.0f}s/{timeout_s:.0f}s {_npu_line(gemma_mood)}",
            )
            print(
                f"[ears] still listening ({elapsed:.0f}s) — speak now "
                f"(or wait; max {timeout_s:.0f}s then mic reset).",
                flush=True,
            )
            last_progress = now
    if th.is_alive():
        _trace("listen_hung", f">{timeout_s:.0f}s {_npu_line(gemma_mood)}")
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
        _trace("listen_error", f"{box['error']!r} {_npu_line(gemma_mood)}")
        raise box["error"]
    elapsed = time.time() - t0
    if box["result"] is not None:
        _trace("listen_once_ok", f"{elapsed:.1f}s")
    return box["result"]


def start_stuck_guard(stop_event, gemma_mood=None, greeter=None, source=None,
                      interval_s: float = 12.0):
    """If ears/Gemma/react stall, recover mic + free NPU."""

    def _loop():
        while not stop_event.wait(interval_s):
            try:
                import gemy_trace
                phase, detail, ago = gemy_trace.get_phase_age()
            except ImportError:
                try:
                    import gemy_diag
                    phase, detail, ago = gemy_diag.get_phase_age()
                except ImportError:
                    continue
            if ago < 0:
                continue
            limit = _STUCK_LISTEN_S
            if phase.startswith("gemma"):
                if gemma_mood is not None and not getattr(
                    gemma_mood, "_model_loaded", False
                ):
                    limit = _STUCK_GEMMA_FIRST_LOAD_S
                else:
                    limit = _STUCK_GEMMA_S
            elif phase.startswith("react_"):
                limit = _STUCK_REACT_S
            elif phase not in _STUCK_PHASES:
                continue
            if ago < limit:
                continue
            snap = ""
            try:
                import gemy_trace
                snap = gemy_trace.full_snapshot(gemma_mood, greeter)
            except ImportError:
                pass
            _trace("stuck_detected", f"{phase!r} {ago:.0f}s {detail} | {snap}")
            print(
                f"[stability] STUCK {phase!r} for {ago:.0f}s ({detail}) — recovering.",
                flush=True,
            )
            if phase == "listen_wait":
                recover_audio_source(source)
            elif phase.startswith("react_") and greeter is not None:
                try:
                    import hat
                    hat.force_all_off()
                except Exception:
                    pass
                abort = getattr(greeter, "abort_reaction", None)
                if callable(abort):
                    abort()
            ensure_npu_for_ears(gemma_mood)
            _trace("stuck_recovered", f"was {phase!r} {ago:.0f}s")
            try:
                import gemy_diag
                gemy_diag.log("stuck_recovery", f"{phase} {ago:.0f}s")
                gemy_diag.set_phase("listen_recovered", f"stuck {phase}")
            except ImportError:
                try:
                    import gemy_trace
                    gemy_trace.set_phase("listen_recovered", f"stuck {phase}")
                except ImportError:
                    pass

    threading.Thread(target=_loop, name="stuck-guard", daemon=True).start()
    print(
        f"[stability] stuck guard ON (listen >{_STUCK_LISTEN_S:.0f}s or "
        f"listen_once >{LISTEN_ONCE_MAX_S:.0f}s recovers).",
        flush=True,
    )
