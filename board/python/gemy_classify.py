#!/usr/bin/env python3
"""Public speech classification API (black-box contract for tests and greeter).

Input: heard text (as STT would return).
Output: final beep kind (always a valid reaction or ``off``).

No GPIO, no Gemma/NPU unless ``use_gemma_assist=True``.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import gemy_fallback
import gemy_reactions

if TYPE_CHECKING:
    from greeter import KnockKnockTracker

DEFAULT_GREET_KEYWORDS = frozenset({"hello", "hi", "hey", "hiya"})


def classify_heard(
    text: str,
    *,
    greet_keywords: set[str] | frozenset[str] | None = None,
    phrase_buffer=None,
    joke_tracker: "KnockKnockTracker | None" = None,
    use_gemma_assist: bool = False,
    gemma_mood=None,
) -> str:
    """Full ears-path classification: phrase merge → keywords → optional Gemma → finalize.

    This is what ``[ears] heard: '…' -> kind`` uses (default: local only, no NPU).
    """
    from greeter import (
        _maybe_gemma_assist,
        _words_from_text,
        classify_utterance,
        resolve_reaction_kind,
    )

    greet = set(greet_keywords or DEFAULT_GREET_KEYWORDS)
    stripped = (text or "").strip()
    if not stripped:
        return "neutral"

    low, words = _words_from_text(stripped)
    if phrase_buffer is not None:
        stripped, low, words, _merged = phrase_buffer.absorb(stripped, low, words)
        text = stripped

    kind = classify_utterance(
        stripped, low, words, greet, joke_tracker=joke_tracker, gemma_mood=None
    )
    if (
        use_gemma_assist
        and kind not in ("off",)
        and (kind is None or kind == "neutral")
        and gemma_mood is not None
        and getattr(gemma_mood, "_model_loaded", False)
    ):
        gemma_kind = _maybe_gemma_assist(
            text, low, words, gemma_mood, joke_tracker, True
        )
        if gemma_kind:
            kind = gemma_kind
    return gemy_fallback.finalize_beep_kind(
        resolve_reaction_kind(kind), low, words
    )


def kind_is_playable(kind: str) -> bool:
    """True if greeter can dispatch a reaction (or shutdown for off)."""
    if kind == "off":
        return True
    if kind not in gemy_reactions.BEEP_REACTIONS:
        return False
    from greeter import REACTIONS
    return kind in REACTIONS
