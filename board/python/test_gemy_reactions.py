#!/usr/bin/env python3
"""Tests for beep-only reaction policy (PC: python test_gemy_reactions.py)."""
from __future__ import annotations

import os
import sys
import unittest
from unittest import mock

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import test_support

test_support.install_hat_mock()

import gemy_reactions  # noqa: E402


class TestBeepOnly(unittest.TestCase):
    def test_open_ended_capital(self):
        self.assertTrue(
            gemy_reactions.looks_like_open_ended_question(
                "what is the capital of france"
            )
        )

    def test_yes_no_question_not_open(self):
        self.assertFalse(
            gemy_reactions.looks_like_open_ended_question("is the sky blue")
        )

    def test_gemma_yes_blocked_for_open(self):
        self.assertIsNone(
            gemy_reactions.gemma_label_to_beep_kind(
                "yes", "what is the capital of france"
            )
        )

    def test_gemma_funny_allowed(self):
        self.assertEqual(
            gemy_reactions.gemma_label_to_beep_kind("funny", "haha that is funny"),
            "funny",
        )

    def test_resolve_unknown(self):
        self.assertEqual(gemy_reactions.resolve_beep_kind("purple"), "neutral")
        self.assertEqual(gemy_reactions.resolve_beep_kind(None), "neutral")

    def test_resolve_yes(self):
        self.assertEqual(gemy_reactions.resolve_beep_kind("yes"), "yes")


if __name__ == "__main__":
    unittest.main(verbosity=2)
