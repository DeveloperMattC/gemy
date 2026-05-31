#!/usr/bin/env python3
import unittest

import gemy_fallback
from gemy_reactions import BEEP_REACTIONS


class TestFallback(unittest.TestCase):
    def test_always_valid(self):
        for text in ("", "blah blah", "is the sky blue", "purple elephant"):
            low = text.lower()
            words = set(low.split())
            k = gemy_fallback.closest_beep_kind(low, words)
            self.assertIn(k, BEEP_REACTIONS)

    def test_sleepy_via_empathy(self):
        k = gemy_fallback.closest_beep_kind("i am sleepy", {"i", "am", "sleepy"})
        self.assertEqual(k, "sad")

    def test_random_gibberish_neutral(self):
        k = gemy_fallback.closest_beep_kind("xyzzy plugh", {"xyzzy", "plugh"})
        self.assertEqual(k, "neutral")

    def test_finalize_none(self):
        self.assertEqual(
            gemy_fallback.finalize_beep_kind(None, "hello there", {"hello", "there"}),
            "greet",
        )


if __name__ == "__main__":
    unittest.main()
