#!/usr/bin/env python3
"""Canonical beep/LED reactions — the only patterns Gemy may play.

Gemy has no speech and no new buzzer sequences. Every heard phrase maps to
one of these kinds (or neutral). Gemma assist only picks from this set.
"""
from __future__ import annotations

import re

# Wired in greeter.REACTIONS + hat.gemy_*() — do not add kinds without hat support.
BEEP_REACTIONS = frozenset({
    "gemy", "greet", "funny", "nice", "mean", "sad", "yes", "no", "neutral",
})

# Turn-off is handled in the speech loop (not in REACTIONS dict).
KIND_OFF = "off"

_ALL_KINDS = BEEP_REACTIONS | {KIND_OFF}

_RE_OPEN_WH = re.compile(
    r"\b(what|who|where|when|which)\s+(?:is|are|was|were)\b",
)
_RE_WHY = re.compile(r"\bwhy\b")


def looks_like_open_ended_question(low: str) -> bool:
    """Questions that cannot be answered with yes/no beeps (e.g. capital of France)."""
    try:
        import gemy_qa
        if not gemy_qa.looks_like_question(low):
            return False
    except ImportError:
        n = low.strip().lower()
        if not n:
            return False
    else:
        n = low.strip().lower()
    if _RE_OPEN_WH.search(n):
        return True
    if _RE_WHY.search(n):
        return True
    if "how old" in n or "how tall" in n or "how much" in n:
        return True
    if "tell me about" in n or "what do you think" in n:
        return True
    return False


def is_valid_beep_kind(kind: str | None) -> bool:
    return bool(kind and kind in _ALL_KINDS)


def gemma_label_to_beep_kind(raw: str | None, low: str = "") -> str | None:
    """Map Gemma text to a beep kind, or None (-> neutral). Never invent patterns."""
    from gemma_mood import mood_for_reaction

    label = mood_for_reaction(raw or "")
    if not label:
        return None
    if label == KIND_OFF:
        return KIND_OFF
    if label not in BEEP_REACTIONS:
        print(f"[gemy] beep filter: {label!r} not a reaction -> neutral", flush=True)
        return None
    if label in ("yes", "no") and looks_like_open_ended_question(low):
        print(
            f"[gemy] beep filter: yes/no not valid for open question -> neutral",
            flush=True,
        )
        return None
    return label


def resolve_beep_kind(kind: str | None) -> str:
    """Final gate before react(): unknown -> neutral (never KeyError)."""
    if not kind or kind == "neutral":
        return "neutral"
    if kind in BEEP_REACTIONS or kind == KIND_OFF:
        return kind
    print(f"[gemy] unknown reaction {kind!r} -> neutral", flush=True)
    return "neutral"
