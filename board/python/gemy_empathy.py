#!/usr/bin/env python3
"""Fast empathy moods for personal feelings — no Gemma, no NPU.

Maps sharing how the human feels to nice (happy cheer) or sad (gentle cry) beeps.
Tired / sleepy / worn out -> sad; happy / excited -> nice.
"""
from __future__ import annotations

import re

try:
    import gemy_qa
except ImportError:
    gemy_qa = None

# Happy / warm (green woohoo) — positive share only.
_EMPATHY_NICE_PHRASES = (
    "feeling good", "feel good", "feeling great", "feel great",
    "so happy", "really happy", "pretty happy", "feeling happy", "feel happy",
    "excited", "thrilled", "pumped",
)

# Gentle sad (blue cry) — low energy, hurt, tired, hard day.
_EMPATHY_SAD_PHRASES = (
    "sleepy", "so sleepy", "little sleepy", "pretty sleepy", "really sleepy",
    "im sleepy", "i am sleepy", "i'm sleepy", "feel sleepy", "feeling sleepy",
    "am tired", "im tired", "i am tired", "i'm tired", "so tired", "really tired",
    "pretty tired", "little tired", "very tired", "feel tired", "feeling tired",
    "exhausted", "worn out", "wore out", "need sleep", "need a nap", "need to sleep",
    "going to bed", "going to sleep", "time for bed", "time to sleep",
    "long day", "hard day", "rough day", "tough day",
    "yawning", "yawn",
    "feeling down", "feel down", "feeling low", "feel low",
    "not feeling well", "dont feel well", "do not feel well",
    "feeling awful", "feel awful", "feeling horrible", "feel horrible",
    "feeling bad", "feel bad", "not good", "not great",
    "im upset", "i am upset", "i'm upset", "feeling upset", "feel upset",
    "im worried", "i am worried", "feeling worried", "so worried",
    "stressed out", "feeling stressed", "overwhelmed", "anxious",
    "feeling sick", "feel sick", "dont feel good", "do not feel good",
    "had a bad day", "bad day today", "worst day",
)

_EMPATHY_NICE_WORDS = frozenset({
    "excited", "thrilled", "pumped", "happy", "happiness", "joyful", "cheerful",
})

_EMPATHY_SAD_WORDS = frozenset({
    "sleepy", "sleepiness", "tired", "tiredness", "exhausted", "exhaustion",
    "yawn", "yawning", "nap", "napping", "snooze", "drowsy", "weary",
    "worried", "anxious", "stressed", "overwhelmed", "miserable",
    "depressed", "gloomy", "heartbroken", "devastated",
})

# "I am / I'm / I feel …" personal share (not a quiz question).
_RE_PERSONAL = re.compile(
    r"\b(?:i am|i'm|im|i feel|i'm feeling|im feeling|feeling|feel)\b",
)


def looks_like_personal_share(low: str) -> bool:
    """Human sharing how they feel (not asking Gemy a fact question)."""
    n = low.strip()
    if not n:
        return False
    if gemy_qa is not None and gemy_qa.looks_like_question(n):
        return False
    if _RE_PERSONAL.search(n):
        return True
    for p in _EMPATHY_NICE_PHRASES + _EMPATHY_SAD_PHRASES:
        if p in n:
            return True
    return False


def try_empathy_mood(low: str, words: set[str] | None = None) -> str | None:
    """Return nice or sad for feelings; None if no match."""
    words = words or set()
    n = low.strip()
    if not n:
        return None
    if gemy_qa is not None and gemy_qa.looks_like_question(n):
        return None

    for p in _EMPATHY_SAD_PHRASES:
        if p in n:
            return "sad"
    if words & _EMPATHY_SAD_WORDS:
        return "sad"

    for p in _EMPATHY_NICE_PHRASES:
        if p in n:
            return "nice"
    if words & _EMPATHY_NICE_WORDS:
        return "nice"

    return None
