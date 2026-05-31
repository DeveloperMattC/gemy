#!/usr/bin/env python3
"""Black-box tests — heard text in, beep kind out (same contract as live Gemy).

**Contract:** ``gemy_classify.classify_heard()`` is the only classification entry
point under test. It must match what ``greeter.py`` logs as
``[ears] heard: '…' -> kind`` (default: ``use_gemma_assist=False``).

**Not here (see other modules):**
- ``test_gemy_unit.py`` — Gemma label parsing, ``classify_utterance`` slices
- ``test_gemy_empathy.py`` / ``test_gemy_fallback.py`` — module internals
- ``test_gemy_wiring.py`` — REACTIONS ↔ hat handlers

Run: python -m unittest test_gemy_blackbox -v
"""
from __future__ import annotations

import os
import sys
import unittest
from unittest import mock

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import test_support

test_support.install_hat_mock()

import greeter  # noqa: E402
import gemy_classify  # noqa: E402
import gemy_phrase_buffer  # noqa: E402
import gemy_reactions  # noqa: E402

_DEFAULT_GREET = frozenset({"hello", "hi", "hey", "hiya"})


def classify_like_greeter(
    text: str,
    *,
    phrase_buffer: gemy_phrase_buffer.PhraseBuffer | None = None,
    use_gemma_assist: bool = False,
    gemma_mood=None,
    joke_tracker=None,
) -> str:
    """Mirror greeter speech_loop: absorb (optional) then classify_heard (no buffer arg)."""
    buf = phrase_buffer or gemy_phrase_buffer.PhraseBuffer()
    low, words = greeter._words_from_text(text)
    merged_text, low, words, _merged = buf.absorb(text, low, words)
    return gemy_classify.classify_heard(
        merged_text,
        greet_keywords=_DEFAULT_GREET,
        joke_tracker=joke_tracker,
        use_gemma_assist=use_gemma_assist,
        gemma_mood=gemma_mood,
    )


# (heard text, expected kind) — default path: no Gemma, like greet-demo.ps1
BLACKBOX_HEARD_TO_KIND: tuple[tuple[str, str], ...] = (
    # Name & greet
    ("hi gemy", "gemy"),
    ("hey jimmy", "gemy"),
    ("how are you today", "greet"),
    ("hello there", "greet"),
    # Moods
    ("thank you so much", "nice"),
    ("i am so happy", "nice"),
    ("you are stupid", "mean"),
    ("i hate you", "mean"),
    ("i am sad", "sad"),
    ("oh i'm tired", "sad"),
    ("i am a little sleepy", "sad"),
    ("haha that is funny", "funny"),
    # Yes / no & Q&A
    ("yeah sure", "yes"),
    ("nope", "no"),
    ("is the sky blue", "yes"),
    ("is the sky green", "no"),
    ("is the moon made out of cheese", "no"),
    ("do pigs fly", "no"),
    ("is one plus one equal to two", "yes"),
    # Edge / fallback
    ("xyzzy plugh", "neutral"),
    ("", "neutral"),
    # Off
    ("gemy turn off", "off"),
    ("bye gemy", "off"),
    ("stop gemy", "off"),
    ("goodbye gemy", "off"),
    # Math (quiz yes/no)
    ("is five plus five ten", "yes"),
)


class TestBlackBoxClassify(unittest.TestCase):
    """Heard phrase → reaction kind (production contract)."""

    def test_heard_to_kind_table(self):
        for heard, expected in BLACKBOX_HEARD_TO_KIND:
            with self.subTest(heard=heard):
                kind = gemy_classify.classify_heard(heard)
                self.assertEqual(
                    kind, expected,
                    f"classify_heard({heard!r}) -> {kind!r}, want {expected!r}",
                )

    def test_every_kind_is_playable(self):
        for heard, _expected in BLACKBOX_HEARD_TO_KIND:
            kind = gemy_classify.classify_heard(heard)
            self.assertTrue(
                gemy_classify.kind_is_playable(kind),
                f"{heard!r} -> {kind!r} not playable (REACTIONS/hat wiring)",
            )

    def test_unknown_english_gets_valid_kind_not_crash(self):
        for phrase in (
            "the purple elephant danced",
            "quantum flux capacitor",
            "blah",
        ):
            with self.subTest(phrase=phrase):
                kind = gemy_classify.classify_heard(phrase)
                self.assertIn(kind, gemy_reactions.BEEP_REACTIONS)

    def test_phrase_buffer_split_question(self):
        buf = gemy_phrase_buffer.PhraseBuffer()
        k1 = gemy_classify.classify_heard("is the sky", phrase_buffer=buf)
        self.assertEqual(k1, "neutral")
        k2 = gemy_classify.classify_heard("green", phrase_buffer=buf)
        self.assertEqual(k2, "no")

    def test_phrase_buffer_moon_cheese(self):
        buf = gemy_phrase_buffer.PhraseBuffer()
        gemy_classify.classify_heard("is the moon", phrase_buffer=buf)
        kind = gemy_classify.classify_heard(
            "made out of cheese", phrase_buffer=buf
        )
        self.assertEqual(kind, "no")

    def test_phrase_buffer_matches_greeter_absorb_outside(self):
        """Production merges in greeter before classify_heard (buffer not passed in)."""
        buf = gemy_phrase_buffer.PhraseBuffer()
        k1 = classify_like_greeter("is the sky", phrase_buffer=buf)
        self.assertEqual(k1, "neutral")
        k2 = classify_like_greeter("green", phrase_buffer=buf)
        self.assertEqual(k2, "no")

    def test_table_matches_greeter_path(self):
        for heard, expected in BLACKBOX_HEARD_TO_KIND:
            with self.subTest(heard=heard):
                kind = classify_like_greeter(heard)
                self.assertEqual(kind, expected)

    def test_gemma_not_called_by_default(self):
        gemma = mock.MagicMock()
        gemma.ready = True
        gemma._model_loaded = True
        kind = gemy_classify.classify_heard(
            "something utterly unknown xyz",
            use_gemma_assist=False,
            gemma_mood=gemma,
        )
        self.assertEqual(kind, "neutral")
        gemma.classify.assert_not_called()

    def test_gemma_skipped_when_model_not_loaded_even_if_assist_on(self):
        gemma = mock.MagicMock()
        gemma.ready = True
        gemma._model_loaded = False
        gemma._assist_cooldown_until = 0.0
        gemma._classify_busy = False
        kind = gemy_classify.classify_heard(
            "something utterly unknown xyz",
            use_gemma_assist=True,
            gemma_mood=gemma,
        )
        self.assertEqual(kind, "neutral")
        gemma.classify.assert_not_called()


class TestBlackBoxInvariants(unittest.TestCase):
    def test_beep_reactions_match_greeter_reactions(self):
        import greeter
        missing = gemy_reactions.BEEP_REACTIONS - frozenset(greeter.REACTIONS)
        self.assertEqual(
            missing, frozenset(),
            f"REACTIONS missing handlers: {sorted(missing)}",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
