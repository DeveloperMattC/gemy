#!/usr/bin/env python3
"""Always-on [trace] logging for freeze / NPU debugging.

Lines go to stdout (gemy.log when greet-demo uses tee). Disable with GEMY_TRACE=0.
Verbose duplicate lines also go to [diag] when gemy_diag is enabled.
"""
from __future__ import annotations

import os
import threading
import time

_lock = threading.Lock()
_phase = "startup"
_phase_detail = ""
_phase_at = 0.0
_ears_heard_at = 0.0
_listen_wait_since = 0.0


def enabled() -> bool:
    return os.environ.get("GEMY_TRACE", "1").strip().lower() not in (
        "0", "false", "no", "off",
    )


def trace(event: str, detail: str = "") -> None:
    if not enabled():
        return
    ts = time.strftime("%H:%M:%S")
    thr = threading.current_thread().name
    extra = f" {detail}" if detail else ""
    print(f"[trace] {ts} [{thr}] {event}{extra}", flush=True)


def set_phase(phase: str, detail: str = "") -> None:
    """Track where the board is; log only when the phase name changes."""
    global _phase, _phase_detail, _phase_at, _listen_wait_since
    with _lock:
        old = _phase
        _phase = phase
        _phase_detail = detail
        _phase_at = time.time()
        if phase == "listen_wait" and old != "listen_wait":
            _listen_wait_since = _phase_at
        elif phase != "listen_wait":
            _listen_wait_since = 0.0
    if phase != old:
        msg = phase if not detail else f"{phase} ({detail[:80]})"
        trace("phase", msg)


def mark_ears_heard(text: str) -> None:
    global _ears_heard_at
    with _lock:
        _ears_heard_at = time.time()
    trace("ears_heard", text[:80])


def get_phase_age() -> tuple[str, str, float]:
    now = time.time()
    with _lock:
        if not _phase_at:
            return _phase, _phase_detail, -1.0
        return _phase, _phase_detail, now - _phase_at


def listen_wait_elapsed() -> float:
    with _lock:
        if _listen_wait_since <= 0:
            return -1.0
        return time.time() - _listen_wait_since


def npu_snapshot(gemma_mood) -> str:
    if gemma_mood is None:
        return "gemma=off"
    parts = [
        f"state={getattr(gemma_mood, '_state', '?')}",
        f"loaded={int(bool(getattr(gemma_mood, '_model_loaded', False)))}",
        f"npu={int(bool(getattr(gemma_mood, '_npu_resident', False)))}",
        f"prewarm={int(bool(getattr(gemma_mood, '_prewarm_busy', False)))}",
        f"classify={int(bool(getattr(gemma_mood, '_classify_busy', False)))}",
    ]
    proc = getattr(gemma_mood, "_proc", None)
    if proc is not None:
        try:
            parts.append(f"worker={proc.poll()}")
        except Exception:
            parts.append("worker=?")
    cd = getattr(gemma_mood, "_assist_cooldown_until", 0.0)
    if cd > time.time():
        parts.append(f"cooldown={cd - time.time():.0f}s")
    return " ".join(parts)


def greeter_snapshot(greeter) -> str:
    if greeter is None:
        return ""
    try:
        return (
            f"reacting={int(bool(getattr(greeter, '_reacting', False)))} "
            f"cooldown_left={max(0.0, getattr(greeter, 'cooldown', 0) - (time.time() - getattr(greeter, '_last', 0))):.1f}s"
        )
    except Exception:
        return ""


def full_snapshot(gemma_mood=None, greeter=None) -> str:
    phase, detail, ago = get_phase_age()
    parts = [f"phase={phase}"]
    if detail:
        parts.append(f"({detail[:60]})")
    if ago >= 0:
        parts.append(f"phase_ago={ago:.0f}s")
    lw = listen_wait_elapsed()
    if lw >= 0 and phase == "listen_wait":
        parts.append(f"listen_wait={lw:.0f}s")
    with _lock:
        if _ears_heard_at > 0:
            parts.append(f"last_heard={time.time() - _ears_heard_at:.0f}s ago")
    parts.append(npu_snapshot(gemma_mood))
    g = greeter_snapshot(greeter)
    if g:
        parts.append(g)
    return " ".join(parts)


class Span:
    """Timed block; logs start/done with elapsed seconds."""

    def __init__(self, event: str, detail: str = "", gemma_mood=None):
        self.event = event
        self.detail = detail
        self.gemma_mood = gemma_mood
        self._t0 = 0.0

    def __enter__(self):
        self._t0 = time.time()
        extra = self.detail
        if self.gemma_mood is not None:
            snap = npu_snapshot(self.gemma_mood)
            extra = f"{extra} | {snap}" if extra else snap
        trace(f"{self.event}_start", extra)
        return self

    def __exit__(self, exc_type, exc, tb):
        elapsed = time.time() - self._t0
        if exc_type is not None:
            trace(
                f"{self.event}_error",
                f"{elapsed:.2f}s {exc_type.__name__}: {exc}",
            )
            return False
        extra = f"{elapsed:.2f}s"
        if self.gemma_mood is not None:
            extra += f" | {npu_snapshot(self.gemma_mood)}"
        trace(f"{self.event}_done", extra)
        return False


def start_watchdog(
    stop_event,
    gemma_mood=None,
    greeter=None,
    interval_s: float = 30.0,
) -> None:
    """Periodic alive + NPU line — last [trace] before a freeze is the smoking gun."""

    def _loop():
        trace("watchdog_on", f"every {interval_s:.0f}s")
        while not stop_event.wait(interval_s):
            trace("watchdog", full_snapshot(gemma_mood, greeter))

    threading.Thread(target=_loop, name="trace-watchdog", daemon=True).start()
