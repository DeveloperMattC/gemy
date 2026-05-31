#!/usr/bin/env python3
"""Safe keyword Q&A for Gemy — yes/no beeps only when we are confident.

No Gemma, no web, no eval. Unknown questions return None (greeter -> neutral or Gemma).
"""
from __future__ import annotations

import re

from gemy_math import parse_operand, parse_spoken_number

# Substring facts (normalized lowercase). Only high-confidence kid/lab facts.
_FACT_YES = (
    "is the sky blue",
    "is the ocean salty",
    "is water wet",
    "is ice cold",
    "is fire hot",
    "is snow cold",
    "is the sun hot",
    "is the sun a star",
    "is earth a planet",
    "do birds fly",
    "do fish swim",
    "do bees make honey",
    "do plants need water",
    "do humans need air",
    "do we breathe oxygen",
    "is two an even number",
    "is ten greater than five",
    "is five bigger than three",
    "are there seven days in a week",
    "are there twelve months in a year",
    "are there sixty seconds in a minute",
    "is a minute longer than a second",
    "is a triangle a shape",
    "is a square a shape",
    "do triangles have three sides",
    "do squares have four sides",
    "is python a programming language",
    "can robots beep",
    "can you hear me",
    "can you listen",
    "are you a robot",
    "are you gemy",
    "is gemy a robot",
    "do robots have leds",
    "is coralboard a computer board",
    "is the moon in the sky",
    "does the earth go around the sun",
    "does the moon orbit earth",
    "is rain water",
    "is steam hot",
    "is boiling water hot",
    "do magnets attract metal",
    "is steel a metal",
    "is gold a metal",
    "are penguins birds",
    "are spiders arachnids",
    "do dogs bark",
    "do cats meow",
    "is red a color",
    "is blue a color",
    "is zero less than one",
    "is one less than two",
)

_FACT_NO = (
    "is the moon made of cheese",
    "is the moon made out of cheese",
    "is the sun a planet",
    "is the earth flat",
    "is ice hot",
    "is fire cold",
    "do cats bark",
    "do dogs meow",
    "do fish fly",
    "can humans breathe underwater without help",
    "is two plus two five",
    "is ten less than five",
    "is five smaller than three",
    "are there ten days in a week",
    "are there twenty months in a year",
    "do triangles have four sides",
    "do squares have three sides",
    "is the sky green",
    "is the sky orange",
    "is the sky red",
    "is the sky purple",
    "is the sky yellow",
    "is grass blue",
    "is snow hot",
    "do rocks float in water usually",
    "can robots eat food",
    "do robots need sleep like humans",
    "is gemy a human",
    "are you a human",
    "is water dry",
    "is sand a liquid",
    "does the sun orbit the earth",
    "is the moon the sun",
    "are whales fish",
    "are bats birds",
    "is the ocean made of lemonade",
    "do pigs fly",
    "can fish walk on land",
    "is snow made of fire",
    "is the sun cold",
    "do snakes have legs",
    "is wood a metal",
    "can you swim in the desert",
)

# Gemy / lab directed (still yes/no beeps).
_ROBOT_YES = (
    "can you hear me",
    "can you listen to me",
    "are you listening",
    "are you there",
    "are you awake",
    "are you on",
    "are you a robot",
    "are you gemy",
    "do you have a buzzer",
    "do you have lights",
    "do you have leds",
)

_ROBOT_NO = (
    "can you fly",
    "can you walk",
    "can you run",
    "do you have legs",
    "do you have arms",
    "can you speak words",
    "can you talk like a person",
)


def _longest_first(items: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(sorted(items, key=len, reverse=True))


_FACT_NO_SORTED = _longest_first(_FACT_NO)
_FACT_YES_SORTED = _longest_first(_FACT_YES)
_ROBOT_NO_SORTED = _longest_first(_ROBOT_NO)
_ROBOT_YES_SORTED = _longest_first(_ROBOT_YES)

_QUESTION_START = re.compile(
    r"^(?:is|are|was|were|am|do|does|did|can|could|will|would|should|has|have|had)\b"
)
_WH_WORD = re.compile(
    r"\b(what|who|when|where|why|how|which|whether)\b"
)

_RE_COMPARE = re.compile(
    r"\b(?:is|are)\s+(\w+)\s+"
    r"(bigger|larger|greater|more|smaller|less|fewer|shorter|taller|longer)\s+"
    r"(?:than\s+)?(\w+)\b"
)
_RE_SKY_COLOR = re.compile(
    r"\bis the sky\s+"
    r"(blue|orange|red|green|purple|yellow|pink|black|white|grey|gray)\b"
)


def _norm(low: str) -> str:
    n = low.replace("-", " ").replace("'", "").replace("?", " ")
    return re.sub(r"\s+", " ", n).strip()


def norm_qa(low: str) -> str:
    """Normalize for fact matching (STT variants like 'made out of')."""
    n = _norm(low)
    n = re.sub(r"\bmade out of\b", "made of", n)
    n = re.sub(r"\bout of\b", "of", n)
    n = re.sub(r"\bthe the\b", "the", n)
    return n.strip()


# Topic patterns when substring facts miss (moon+cheese, flat earth, …).
_TOPIC_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bmoon\b.*\bcheese\b|\bcheese\b.*\bmoon\b"), "no"),
    (re.compile(r"\bthe sun\b.*\b(?:a\s+)?planet\b"), "no"),
    (re.compile(r"\bthe moon\b.*\b(?:a\s+)?planet\b"), "no"),
    (re.compile(r"\bearth\b.*\bflat\b|\bflat\b.*\bearth\b"), "no"),
    (re.compile(r"\bsun\b.*\borbit\b.*\bearth\b|\bearth\b.*\borbit\b.*\bsun\b"), "no"),
    (re.compile(r"\bwhales?\b.*\bfish\b|\bfish\b.*\bwhales?\b"), "no"),
    (re.compile(r"\bcats?\b.*\bbark\b|\bdogs?\b.*\bmeow\b"), "no"),
    (re.compile(r"\bpigs?\b.*\bfly\b|\bfly\b.*\bpigs?\b"), "no"),
    (re.compile(r"\bocean\b.*\blemonade\b|\blemonade\b.*\bocean\b"), "no"),
    (re.compile(r"\bsnakes?\b.*\blegs?\b|\blegs?\b.*\bsnakes?\b"), "no"),
)


def _looks_factual_check(n: str) -> bool:
    """Question or "is/are/do/can …" check — not a plain affirmation like "yeah"."""
    if looks_like_question(n):
        return True
    if n.startswith(("is it ", "is that ", "does that ", "are they ")):
        return True
    return bool(re.search(r"\b(is|are|do|does|can|could)\b", n))


def looks_like_question(low: str) -> bool:
    """Heard phrase is probably a question (for Gemma prompt + affirmation guard)."""
    n = _norm(low)
    if not n:
        return False
    if _QUESTION_START.search(n):
        return True
    if _WH_WORD.search(n):
        return True
    return False


def _try_topic_patterns(n: str) -> str | None:
    for pat, ans in _TOPIC_PATTERNS:
        if pat.search(n):
            return ans
    return None


def try_local_yes_no(low: str, words: set[str] | None = None) -> str | None:
    """All fast paths: facts, patterns, compare — no Gemma."""
    n = norm_qa(low)
    if not n or not _looks_factual_check(n):
        return None
    for fn in (_try_compare, _try_sky_color, _try_even_odd, _try_fact_snippets, _try_topic_patterns):
        ans = fn(n)
        if ans:
            return ans
    return None


def should_skip_gemma_assist(low: str) -> tuple[bool, str]:
    """True when Gemma must not run (local answer, incomplete, or known topic)."""
    if try_local_yes_no(low):
        return True, "local_qa"
    if looks_like_incomplete_yes_no_question(low):
        return True, "incomplete"
    try:
        import gemy_empathy
        if gemy_empathy.try_empathy_mood(low) or gemy_empathy.looks_like_personal_share(low):
            return True, "empathy"
    except ImportError:
        pass
    return False, ""


def looks_like_incomplete_yes_no_question(low: str) -> bool:
    """STT fragment — not safe to load Gemma (e.g. 'is the sky' without 'green')."""
    n = norm_qa(low)
    if not n or not _looks_factual_check(n):
        return False
    for fn in (_try_sky_color, _try_compare, _try_even_odd, _try_fact_snippets):
        if fn(n):
            return False
    if re.search(r"\b(the|a|an)\s*$", n):
        return True
    if re.match(r"^is the sky\s*$", n):
        return True
    if re.match(r"^(?:is|are)\s+the\s+\w+\s*$", n):
        return True
    if re.search(r"\b(?:made|made of|composed of)\s*$", n):
        return True
    if re.match(r"^is the moon\s*$", n):
        return True
    if _QUESTION_START.match(n) and len(n.split()) <= 2:
        return True
    return False


def _try_compare(n: str) -> str | None:
    m = _RE_COMPARE.search(n)
    if not m:
        return None
    a = parse_operand(m.group(1))
    b = parse_operand(m.group(3))
    if a is None or b is None:
        return None
    rel = m.group(2)
    if rel in ("bigger", "larger", "greater", "more", "taller", "longer"):
        return "yes" if a > b else "no"
    if rel in ("smaller", "less", "fewer", "shorter"):
        return "yes" if a < b else "no"
    return None


def _try_sky_color(n: str) -> str | None:
    m = _RE_SKY_COLOR.search(n)
    if not m:
        return None
    return "yes" if m.group(1) == "blue" else "no"


def _try_even_odd(n: str) -> str | None:
    m = re.search(r"\bis\s+(\w+)\s+(?:an?\s+)?(even|odd)\s+number\b", n)
    if not m:
        return None
    v = parse_operand(m.group(1))
    if v is None or v < 0:
        return None
    even = (v % 2) == 0
    if m.group(2) == "even":
        return "yes" if even else "no"
    return "yes" if not even else "no"


def _try_fact_snippets(n: str) -> str | None:
    for snippet in _FACT_NO_SORTED:
        if snippet in n:
            return "no"
    for snippet in _FACT_YES_SORTED:
        if snippet in n:
            return "yes"
    for snippet in _ROBOT_NO_SORTED:
        if snippet in n:
            return "no"
    for snippet in _ROBOT_YES_SORTED:
        if snippet in n:
            return "yes"
    return None


def try_answer_yes_no(
    low: str, words: set[str] | None = None, n: str | None = None,
) -> str | None:
    """Return yes/no only when confident; else None (-> neutral or Gemma assist)."""
    del words
    if n is not None:
        return try_local_yes_no(n) if _looks_factual_check(n) else None
    return try_local_yes_no(low)
