#!/usr/bin/env python3
"""Phase logging for Gemy — copy [diag] lines when the board freezes or heartbeat stops."""
from __future__ import annotations

import threading
import time

_enabled = False
_lock = threading.Lock()
_phase = "startup"
_phase_detail = ""
_phase_at = 0.0
_ears_heard_at = 0.0
_heartbeat_pulses = 0
_heartbeat_last_at = 0.0


def set_enabled(on: bool) -> None:
    global _enabled
    _enabled = bool(on)
    if on:
        log("diag", "verbose logging ON (grep [diag] in log)")


def enabled() -> bool:
    return _enabled


def log(phase: str, detail: str = "") -> None:
    if not _enabled:
        return
    ts = time.strftime("%H:%M:%S")
    thr = threading.current_thread().name
    extra = f" {detail}" if detail else ""
    print(f"[diag] {ts} [{thr}] {phase}{extra}", flush=True)


def set_phase(phase: str, detail: str = "") -> None:
    """Remember where we are (printed again on watchdog if stuck)."""
    global _phase, _phase_detail, _phase_at
    with _lock:
        _phase = phase
        _phase_detail = detail
        _phase_at = time.time()
    log(phase, detail)


def mark_ears_heard(text: str) -> None:
    global _ears_heard_at
    with _lock:
        _ears_heard_at = time.time()
    log("ears_heard", text[:80])


def mark_heartbeat_pulse(source: str) -> None:
    global _heartbeat_pulses, _heartbeat_last_at
    with _lock:
        _heartbeat_pulses += 1
        _heartbeat_last_at = time.time()
    log("heartbeat", source)


def get_phase_age() -> tuple[str, str, float]:
    """Current phase, detail, seconds since last phase change (-1 if unknown)."""
    now = time.time()
    with _lock:
        if not _phase_at:
            return _phase, _phase_detail, -1.0
        return _phase, _phase_detail, now - _phase_at


def snapshot(gemma_mood=None, greeter=None) -> str:
    """One-line status for periodic watchdog."""
    now = time.time()
    with _lock:
        phase = _phase
        detail = _phase_detail
        phase_ago = now - _phase_at if _phase_at else -1
        heard_ago = now - _ears_heard_at if _ears_heard_at else -1
        hb_ago = now - _heartbeat_last_at if _heartbeat_last_at else -1
        hb_n = _heartbeat_pulses
    parts = [f"phase={phase}"]
    if detail:
        parts.append(f"({detail})")
    parts.append(f"phase_ago={phase_ago:.0f}s")
    if heard_ago >= 0:
        parts.append(f"last_heard={heard_ago:.0f}s")
    parts.append(f"hb_pulses={hb_n}")
    if hb_ago >= 0:
        parts.append(f"last_hb={hb_ago:.0f}s")
    if greeter is not None:
        try:
            reacting = getattr(greeter, "_reacting", False)
            idle = getattr(greeter, "_idle", False)
            parts.append(f"reacting={reacting}")
            parts.append(f"idle_flag={idle}")
        except Exception:
            pass
    if gemma_mood is not None:
        parts.append(f"gemma={_gemma_status(gemma_mood)}")
    return " ".join(parts)


def _gemma_status(gemma_mood) -> str:
    st = getattr(gemma_mood, "_state", "?")
    busy = getattr(gemma_mood, "_classify_busy", False)
    cd = getattr(gemma_mood, "_assist_cooldown_until", 0.0)
    proc = getattr(gemma_mood, "_proc", None)
    poll = proc.poll() if proc else None
    extra = []
    if busy:
        extra.append("classify_busy")
    if cd > time.time():
        extra.append(f"cooldown={cd - time.time():.0f}s")
    if poll is not None:
        extra.append(f"worker_exit={poll}")
    if extra:
        return f"{st} ({', '.join(extra)})"
    return str(st)


class Span:
    """Log start/done with elapsed time; updates phase on enter."""

    def __init__(self, phase: str, detail: str = ""):
        self.phase = phase
        self.detail = detail
        self._t0 = 0.0

    def __enter__(self):
        self._t0 = time.time()
        set_phase(self.phase, self.detail)
        return self

    def __exit__(self, exc_type, exc, tb):
        elapsed = time.time() - self._t0
        if exc_type is not None:
            log(f"{self.phase}_error", f"{elapsed:.2f}s {exc_type.__name__}: {exc}")
            set_phase(f"{self.phase}_error", str(exc)[:120])
            return False
        log(f"{self.phase}_done", f"{elapsed:.2f}s")
        set_phase("idle" if self.phase.startswith("listen") else f"after_{self.phase}")
        return False


def start_watchdog(stop_event, gemma_mood=None, greeter=None, interval_s: float = 20.0):
    """Periodic alive line — last [diag] before freeze is the smoking gun."""

    def _loop():
        while not stop_event.wait(interval_s):
            log("watchdog", snapshot(gemma_mood, greeter))

    t = threading.Thread(target=_loop, name="diag-watchdog", daemon=True)
    t.start()
    log("watchdog", f"every {interval_s:.0f}s")
    return t
