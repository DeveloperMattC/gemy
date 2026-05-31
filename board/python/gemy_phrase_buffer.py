#!/usr/bin/env python3
"""Merge split STT utterances into one question (e.g. 'is the moon' + 'made of cheese')."""
from __future__ import annotations

import re
import time

try:
    import gemy_qa
except ImportError:
    gemy_qa = None

# Seconds to wait for the rest of a split question.
MERGE_TTL_S = 5.0

_CONTINUATION_START = re.compile(
    r"^(?:of|out of|from|made|made of|made out of|or|and)\b",
    re.I,
)


def _is_continuation(low: str) -> bool:
    n = low.strip().lower()
    if not n:
        return False
    if _CONTINUATION_START.search(n):
        return True
    # Short tail without a new question starter ("green", "made of cheese").
    if gemy_qa is not None and gemy_qa.looks_like_question(n):
        return False
    return len(n.split()) <= 5


def _wants_merge_prefix(low: str) -> bool:
    if gemy_qa is None:
        return False
    if gemy_qa.looks_like_incomplete_yes_no_question(low):
        return True
    n = low.strip().lower()
    return bool(re.search(r"\b(?:made|made of|made out of|composed of)\s*$", n))


class PhraseBuffer:
    """Hold a question prefix until the next phrase completes it."""

    def __init__(self, ttl_s: float = MERGE_TTL_S):
        self._ttl_s = ttl_s
        self._text = ""
        self._low = ""
        self._words: set[str] = set()
        self._at = 0.0

    def clear(self) -> None:
        self._text = ""
        self._low = ""
        self._words = set()
        self._at = 0.0

    def absorb(self, text: str, low: str, words: set[str]) -> tuple[str, str, set[str], bool]:
        """Return (text, low, words, was_merged)."""
        now = time.time()
        if self._text and (now - self._at) > self._ttl_s:
            self.clear()

        if self._text and _is_continuation(low):
            merged_text = f"{self._text} {text}".strip()
            merged_low = f"{self._low} {low}".strip()
            merged_words = set(self._words) | set(words)
            self.clear()
            return merged_text, merged_low, merged_words, True

        if _wants_merge_prefix(low):
            self._text = text.strip()
            self._low = low.strip()
            self._words = set(words)
            self._at = now

        return text.strip(), low.strip(), words, False
