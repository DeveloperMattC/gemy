#!/usr/bin/env python3
"""Last-resort local mood — every utterance maps to a beep without Gemma/NPU.

Used when keywords, math, Q&A, and empathy do not match. Picks the closest
reaction by word/phrase score, else neutral.
"""
from __future__ import annotations

from gemy_reactions import BEEP_REACTIONS

# Tie-break order (stronger moods first when scores equal).
_MOOD_PRIORITY = (
    "mean", "sad", "funny", "nice", "greet", "gemy", "yes", "no", "neutral",
)

_MEAN_W = frozenset({
    "stupid", "dumb", "hate", "idiot", "moron", "ugly", "suck", "worst", "mean",
    "rude", "nasty", "pathetic", "worthless", "jerk", "loser", "garbage", "trash",
})
_SAD_W = frozenset({
    "sad", "unhappy", "upset", "lonely", "alone", "crying", "hurt", "miss",
    "worried", "anxious", "stressed", "gloomy", "sick", "tired", "bad", "sorry",
})
_FUNNY_W = frozenset({
    "funny", "joke", "jokes", "haha", "lol", "laugh", "laughing", "hilarious",
    "silly", "goofy", "knock", "humor", "comedy",
})
_NICE_W = frozenset({
    "good", "great", "nice", "love", "thanks", "thank", "awesome", "cool", "best",
    "wonderful", "happy", "sweet", "kind", "pretty", "beautiful", "yay",
})
_GREET_W = frozenset({"hello", "hi", "hey", "hiya", "howdy", "morning", "evening"})
_GEMY_W = frozenset({"gemy", "gemi", "jemmy", "jimmy"})
_YES_W = frozenset({"yes", "yeah", "yep", "yup", "sure", "correct", "right", "true"})
_NO_W = frozenset({"no", "nope", "nah", "wrong", "false", "never"})

_MOOD_SIGNALS: tuple[tuple[str, frozenset, tuple[str, ...]], ...] = (
    ("mean", _MEAN_W, ("shut up", "hate you", "you suck", "go away", "leave me alone")),
    ("sad", _SAD_W, ("feel bad", "so sad", "bad news", "feel down", "miss you")),
    ("funny", _FUNNY_W, ("tell a joke", "knock knock", "so funny", "ha ha")),
    ("nice", _NICE_W, ("thank you", "love you", "good job", "well done")),
    ("greet", _GREET_W, ("how are you", "whats up", "good morning")),
    ("gemy", _GEMY_W, ()),
    ("yes", _YES_W, ("of course", "for sure", "uh huh")),
    ("no", _NO_W, ("no way", "not really", "absolutely not")),
)


def _score_moods(low: str, words: set[str]) -> dict[str, int]:
    scores: dict[str, int] = {}
    for kind, wset, phrases in _MOOD_SIGNALS:
        if kind not in BEEP_REACTIONS:
            continue
        s = len(words & wset)
        for p in phrases:
            if p in low:
                s += 2
        if s > 0:
            scores[kind] = s
    return scores


def closest_beep_kind(low: str, words: set[str] | None = None) -> str:
    """Always returns a valid beep kind (never None). Prefer neutral when unsure."""
    words = words or set()
    n = low.strip()
    if not n:
        return "neutral"

    try:
        import gemy_empathy
        em = gemy_empathy.try_empathy_mood(n, words)
        if em:
            return em
    except ImportError:
        pass

    try:
        import gemy_reactions
        if gemy_reactions.looks_like_open_ended_question(n):
            return "neutral"
    except ImportError:
        pass

    scores = _score_moods(n, words)
    if not scores:
        return "neutral"

    best = max(scores.values())
    tied = [k for k, v in scores.items() if v == best]
    for kind in _MOOD_PRIORITY:
        if kind in tied:
            print(
                f"[ears] closest mood -> {kind} (score {best}, no exact keyword match)",
                flush=True,
            )
            return kind
    return "neutral"


def finalize_beep_kind(kind: str | None, low: str, words: set[str] | None = None) -> str:
    """Map any classify result to a beep kind; None becomes closest or neutral."""
    if kind and kind in BEEP_REACTIONS:
        return kind
    if kind == "off":
        return "off"
    return closest_beep_kind(low, words or set())
