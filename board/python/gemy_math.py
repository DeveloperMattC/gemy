#!/usr/bin/env python3
"""Fast keyword math quizzes for Gemy (yes/no reactions, no Gemma/NPU).

Handles spoken and digit operands, plus/times/minus/divide, and follow-ups
like "is it equal to forty two" after a prior quiz.
"""
from __future__ import annotations

import re

# Spoken operands 0-19 (+ homophones). "to"/"too" handled in token lookup.
_NUM_WORD: dict[str, int | None] = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19,
    "too": 2, "to": None, "for": 4,
}

_TENS_MAP = {
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}

# Common STT phrases (substring match) — checked only when quiz-like.
_MATH_YES_SNIPPETS = (
    "one plus one is two", "one plus one equal two", "one plus one equals two",
    "one plus one equal to two", "1 plus 1 is 2", "1 plus 1 equals 2",
    "two plus two is four", "two plus two equals four", "two plus two equal four",
    "is one plus one two", "is one plus one equal to two",
    "does one plus one equal two", "one and one is two",
)
_MATH_NO_SNIPPETS = (
    "one plus one is five", "one plus one equal five", "one plus one equals five",
    "one plus one equal to five", "is one plus one five", "one plus one five",
    "two plus two is five", "one plus one is three",
)

_Q_PREFIX = r"(?:(?:is|does|are|can|what(?:'s| is)|whats)\s+)?"
_EQ_TAIL = r"(?:equal(?:s)?(?:\s+to)?|is|are|make(?:s)?)\s+(.+?)\s*$"

_RE_MATH_FOLLOWUP = re.compile(
    r"(?:is\s+)?(?:it|that|the answer)\s+"
    r"(?:(?:equal(?:s)?(?:\s+to)?)|is)\s+(.+?)\s*$",
)
_RE_MATH_FOLLOWUP_SHORT = re.compile(
    r"^(?:is\s+)?(?:it|that)\s+(.+?)\s*$",
)

# Digit tail first: "is 8 plus 13 21" (Moonshine often drops "equal to").
_RE_DIGIT_PLUS_TAIL = re.compile(
    r"(?:is|does|are|can|what(?:'s| is)|whats)\s+(\d+)\s+plus\s+(\d+)\s+(\d+)\s*$"
)
_RE_DIGIT_TIMES_TAIL = re.compile(
    r"(?:is|does|are|can|what(?:'s| is)|whats)\s+(\d+)\s+times\s+(\d+)\s+(\d+)\s*$"
)

# (pattern, op) — first match wins; explicit equals forms after digit tails.
_BIN_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(_Q_PREFIX + r"(\w+)\s+plus\s+(\w+)\s+" + _EQ_TAIL), "+"),
    (re.compile(_Q_PREFIX + r"(\w+)\s+(?:add|and)\s+(\w+)\s+" + _EQ_TAIL), "+"),
    (re.compile(_Q_PREFIX + r"(\w+)\s+times\s+(\w+)\s+" + _EQ_TAIL), "*"),
    (re.compile(
        _Q_PREFIX + r"(\w+)\s+(?:multiplied by|multiply)\s+(\w+)\s+" + _EQ_TAIL
    ), "*"),
    (re.compile(_Q_PREFIX + r"(\w+)\s+minus\s+(\w+)\s+" + _EQ_TAIL), "-"),
    (re.compile(
        _Q_PREFIX + r"(\w+)\s+(?:take away)\s+(\w+)\s+" + _EQ_TAIL
    ), "-"),
    (re.compile(
        _Q_PREFIX + r"(\w+)\s+(?:divided by|over)\s+(\w+)\s+" + _EQ_TAIL
    ), "/"),
    (re.compile(
        r"(?:is|does|are|can|what(?:'s| is)|whats)\s+(\w+)\s+plus\s+(\w+)\s+(.+?)\s*$"
    ), "+"),
    (re.compile(
        r"(?:is|does|are|can|what(?:'s| is)|whats)\s+(\w+)\s+times\s+(\w+)\s+(.+?)\s*$"
    ), "*"),
    (re.compile(
        r"(?:is|does|are|can|what(?:'s| is)|whats)\s+(\w+)\s+minus\s+(\w+)\s+(.+?)\s*$"
    ), "-"),
    (re.compile(
        r"(?:is|does|are|can|what(?:'s| is)|whats)\s+(\w+)\s+"
        r"(?:divided by|over)\s+(\w+)\s+(.+?)\s*$"
    ), "/"),
)

_MATH_HINTS = (
    " plus ", " times ", " multiplied by", " multiply ",
    " minus ", " divided by", " add ", " take away ", " over ",
)

_math_last_answer: int | None = None


def clear_math_context() -> None:
    global _math_last_answer
    _math_last_answer = None


def _remember_math_answer(a: int, b: int, op: str) -> None:
    global _math_last_answer
    if op == "+":
        _math_last_answer = a + b
    elif op == "*":
        _math_last_answer = a * b
    elif op == "-":
        _math_last_answer = a - b
    elif op == "/":
        _math_last_answer = a // b if b else None


def _eval_math_triple(a: int | None, b: int | None, c: int | None, op: str) -> str | None:
    if a is None or b is None or c is None:
        return None
    _remember_math_answer(a, b, op)
    if op == "+":
        return "yes" if (a + b) == c else "no"
    if op == "*":
        return "yes" if (a * b) == c else "no"
    if op == "-":
        return "yes" if (a - b) == c else "no"
    if op == "/":
        if b == 0:
            return None
        return "yes" if (a // b) == c else "no"
    return None


def _token_to_int(tok: str) -> int | None:
    if not tok:
        return None
    if tok.isdigit():
        return int(tok)
    return _NUM_WORD.get(tok)  # type: ignore[return-value]


def _parse_spoken_number(phrase: str) -> int | None:
    """Parse '42', 'seven', 'forty two', or 'twelve'."""
    if not phrase:
        return None
    p = phrase.strip().lower()
    p = re.sub(r"[^\w\s]", "", p)
    if not p:
        return None
    if p.isdigit():
        return int(p)
    one = _token_to_int(p)
    if one is not None:
        return one
    if p in _TENS_MAP:
        return _TENS_MAP[p]
    parts = p.split()
    if len(parts) != 2:
        return None
    tens_w, ones_w = parts
    if tens_w not in _TENS_MAP:
        return None
    ones = _token_to_int(ones_w)
    if ones is None or ones < 0 or ones > 9:
        return None
    return _TENS_MAP[tens_w] + ones


def _parse_math_match(m: re.Match[str], op: str) -> str | None:
    a = _token_to_int(m.group(1))
    b = _token_to_int(m.group(2))
    c = _parse_spoken_number(m.group(3))
    return _eval_math_triple(a, b, c, op)


def _try_digit_tail(n: str) -> str | None:
    for pat, op in ((_RE_DIGIT_PLUS_TAIL, "+"), (_RE_DIGIT_TIMES_TAIL, "*")):
        m = pat.search(n)
        if m:
            ans = _parse_math_match(m, op)
            if ans:
                return ans
    return None


def _norm_math(low: str) -> str:
    """Normalize heard text for math patterns (greeter passes lowered text)."""
    n = low.lower().replace("-", " ").replace("'", "")
    n = re.sub(r"[^\w\s]", " ", n)
    n = re.sub(r"\s+", " ", n).strip()
    return n


def _try_math_followup(n: str) -> str | None:
    global _math_last_answer
    if _math_last_answer is None:
        return None
    for pat in (_RE_MATH_FOLLOWUP, _RE_MATH_FOLLOWUP_SHORT):
        m = pat.search(n)
        if not m:
            continue
        c = _parse_spoken_number(m.group(1))
        if c is not None:
            return "yes" if c == _math_last_answer else "no"
    return None


def _has_math_hint(n: str) -> bool:
    padded = f" {n} "
    return any(h in padded for h in _MATH_HINTS) or any(ch.isdigit() for ch in n)


def looks_like_math_quiz(low: str) -> bool:
    """True when the phrase looks like an arithmetic quiz."""
    n = _norm_math(low)
    if _has_math_hint(n):
        return True
    if _math_last_answer is not None and re.search(
            r"\b(it|that|the answer)\b", n):
        return True
    return False


# Public aliases for gemy_qa comparisons.
parse_operand = _token_to_int
parse_spoken_number = _parse_spoken_number


def try_math_yes_no(
    low: str, words: set[str] | None = None, n: str | None = None,
) -> str | None:
    """Simple +/-/*// quizzes -> yes/no without calling Gemma. words unused (compat)."""
    del words
    n = n if n is not None else _norm_math(low)
    follow = _try_math_followup(n)
    if follow:
        return follow
    if not _has_math_hint(n):
        return None
    for snippet in _MATH_NO_SNIPPETS:
        if snippet in n:
            return "no"
    for snippet in _MATH_YES_SNIPPETS:
        if snippet in n:
            return "yes"
    ans = _try_digit_tail(n)
    if ans:
        return ans
    for pat, op in _BIN_PATTERNS:
        m = pat.search(n)
        if not m:
            continue
        ans = _parse_math_match(m, op)
        if ans:
            return ans
    return None
