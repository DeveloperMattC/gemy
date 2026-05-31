#!/usr/bin/env python3
"""Unit tests for gemy_qa (run on PC: python test_gemy_qa.py)."""
from __future__ import annotations

import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from unittest import mock

import test_support

test_support.install_hat_mock()

import gemy_qa  # noqa: E402


class TestGemyQa(unittest.TestCase):
    def test_fact_yes(self):
        self.assertEqual(gemy_qa.try_answer_yes_no("is the sky blue"), "yes")
        self.assertEqual(gemy_qa.try_answer_yes_no("is the sky orange"), "no")

    def test_sky_color_pattern(self):
        self.assertEqual(gemy_qa.try_answer_yes_no("is the sky blue"), "yes")
        self.assertEqual(gemy_qa.try_answer_yes_no("is the sky orange"), "no")
        self.assertEqual(gemy_qa.try_answer_yes_no("is the sky green"), "no")

    def test_incomplete_question_skips_gemma(self):
        self.assertTrue(gemy_qa.looks_like_incomplete_yes_no_question("is the sky"))
        self.assertFalse(gemy_qa.looks_like_incomplete_yes_no_question("is the sky green"))
        self.assertFalse(gemy_qa.looks_like_incomplete_yes_no_question("is the sky blue"))

    def test_moon_cheese_made_out_of(self):
        self.assertEqual(
            gemy_qa.try_answer_yes_no("is the moon made out of cheese"), "no")
        self.assertEqual(
            gemy_qa.try_answer_yes_no("is the moon made of cheese"), "no")

    def test_should_skip_gemma_moon_cheese(self):
        skip, why = gemy_qa.should_skip_gemma_assist("is the moon made out of cheese")
        self.assertTrue(skip)
        self.assertEqual(why, "local_qa")
        self.assertEqual(gemy_qa.try_answer_yes_no("is water wet"), "yes")

    def test_fact_no(self):
        self.assertEqual(
            gemy_qa.try_answer_yes_no("is the moon made of cheese"), "no")
        self.assertEqual(gemy_qa.try_answer_yes_no("do cats bark"), "no")

    def test_robot(self):
        self.assertEqual(gemy_qa.try_answer_yes_no("can you hear me"), "yes")
        self.assertEqual(gemy_qa.try_answer_yes_no("can you fly"), "no")

    def test_compare(self):
        self.assertEqual(
            gemy_qa.try_answer_yes_no("is ten bigger than five"), "yes")
        self.assertEqual(
            gemy_qa.try_answer_yes_no("is three greater than nine"), "no")

    def test_even_odd(self):
        self.assertEqual(
            gemy_qa.try_answer_yes_no("is four an even number"), "yes")
        self.assertEqual(
            gemy_qa.try_answer_yes_no("is five an odd number"), "yes")

    def test_unknown_returns_none(self):
        self.assertIsNone(
            gemy_qa.try_answer_yes_no("what is the meaning of life"))
        self.assertIsNone(gemy_qa.try_answer_yes_no("yeah"))
        self.assertIsNone(gemy_qa.try_answer_yes_no("hello"))

    def test_looks_like_question(self):
        self.assertTrue(gemy_qa.looks_like_question("is the sky blue"))
        self.assertTrue(gemy_qa.looks_like_question("how are you"))
        self.assertFalse(gemy_qa.looks_like_question("thank you"))


class TestGreeterQuestionGuard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, _HERE)
        import greeter as g  # noqa: E402

        cls.greeter = g

    def test_correct_in_question_not_plain_yes(self):
        low, words = self.greeter._words_from_text("is that answer correct")
        self.assertFalse(self.greeter._is_yes(low, words))

    def test_classify_fact_before_keywords(self):
        low, words = self.greeter._words_from_text("is the sky blue")
        kind = self.greeter.classify_utterance(
            "is the sky blue", low, words, {"hello"})
        self.assertEqual(kind, "yes")


if __name__ == "__main__":
    unittest.main(verbosity=2)
