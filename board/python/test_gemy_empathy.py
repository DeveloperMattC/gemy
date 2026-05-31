#!/usr/bin/env python3
"""Tests for gemy_empathy — feelings without Gemma."""
import unittest

import gemy_empathy


class TestEmpathy(unittest.TestCase):
    def test_tired_sad(self):
        self.assertEqual(
            gemy_empathy.try_empathy_mood("i am a little sleepy right now"),
            "sad",
        )
        self.assertEqual(gemy_empathy.try_empathy_mood("im so tired"), "sad")
        self.assertEqual(gemy_empathy.try_empathy_mood("oh i'm tired"), "sad")

    def test_happy_nice(self):
        self.assertEqual(gemy_empathy.try_empathy_mood("i am so happy"), "nice")

    def test_sad_feelings(self):
        self.assertEqual(gemy_empathy.try_empathy_mood("i am feeling down"), "sad")
        self.assertEqual(gemy_empathy.try_empathy_mood("i feel awful today"), "sad")

    def test_questions_not_empathy(self):
        self.assertIsNone(gemy_empathy.try_empathy_mood("is the sky blue"))

    def test_personal_share(self):
        self.assertTrue(gemy_empathy.looks_like_personal_share("i am a little sleepy"))


if __name__ == "__main__":
    unittest.main()
