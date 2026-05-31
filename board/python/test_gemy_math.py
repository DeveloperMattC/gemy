#!/usr/bin/env python3
"""Unit tests for gemy_math (run on PC: python test_gemy_math.py)."""
from __future__ import annotations

import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import gemy_math  # noqa: E402


class TestGemyMath(unittest.TestCase):
    def setUp(self):
        gemy_math.clear_math_context()

    def tearDown(self):
        gemy_math.clear_math_context()

    def test_plus_yes_no(self):
        self.assertEqual(
            gemy_math.try_math_yes_no("is one plus one equal to two"), "yes")
        self.assertEqual(
            gemy_math.try_math_yes_no("is one plus one five"), "no")
        self.assertEqual(
            gemy_math.try_math_yes_no("two plus two equals four"), "yes")

    def test_times_and_digits(self):
        self.assertEqual(
            gemy_math.try_math_yes_no("is seven times six equal to forty four"),
            "no",
        )
        self.assertEqual(
            gemy_math.try_math_yes_no("is 7 times 6 equal to 42"), "yes")
        self.assertEqual(
            gemy_math.try_math_yes_no("is five times four twenty"), "yes")
        self.assertEqual(
            gemy_math.try_math_yes_no("is five times four two"), "no")
        self.assertEqual(
            gemy_math.try_math_yes_no("Is 8 plus 13 21."), "yes")
        self.assertEqual(
            gemy_math.try_math_yes_no("Is 8 plus 3 11."), "yes")
        self.assertEqual(
            gemy_math.try_math_yes_no("is 8 plus 3 4"), "no")

    def test_followup(self):
        gemy_math.try_math_yes_no("is seven times six equal to forty four")
        self.assertEqual(
            gemy_math.try_math_yes_no("is it equal to forty two"), "yes")
        self.assertEqual(gemy_math.try_math_yes_no("is it equal to 43"), "no")

    def test_teens_and_add_alias(self):
        self.assertEqual(
            gemy_math.try_math_yes_no("is eleven plus five equal to sixteen"),
            "yes",
        )
        self.assertEqual(
            gemy_math.try_math_yes_no("what is 3 add 4 equal to 7"), "yes")

    def test_minus_and_divide(self):
        self.assertEqual(
            gemy_math.try_math_yes_no("is eight minus three equal to five"),
            "yes",
        )
        self.assertEqual(
            gemy_math.try_math_yes_no("is twelve divided by four equal to three"),
            "yes",
        )

    def test_non_math_returns_none(self):
        self.assertIsNone(gemy_math.try_math_yes_no("hello there"))
        self.assertIsNone(gemy_math.try_math_yes_no("how are you"))

    def test_looks_like_math(self):
        self.assertTrue(gemy_math.looks_like_math_quiz("is 2 plus 2 four"))
        self.assertFalse(gemy_math.looks_like_math_quiz("hello"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
