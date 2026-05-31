#!/usr/bin/env python3
"""Phrase buffer tests."""
from __future__ import annotations

import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import gemy_phrase_buffer  # noqa: E402
import gemy_qa  # noqa: E402


class TestPhraseBuffer(unittest.TestCase):
    def test_merge_moon_cheese(self):
        buf = gemy_phrase_buffer.PhraseBuffer()
        t1, l1, w1, m1 = buf.absorb("Is the moon", "is the moon", {"is", "the", "moon"})
        self.assertFalse(m1)
        t2, l2, w2, m2 = buf.absorb(
            "made of cheese", "made of cheese", {"made", "of", "cheese"}
        )
        self.assertTrue(m2)
        self.assertEqual(gemy_qa.try_answer_yes_no(l2, w2), "no")


if __name__ == "__main__":
    unittest.main()
