#!/usr/bin/env python3
"""Integration tests — thin wrapper around black-box classify API."""
from __future__ import annotations

import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import test_support

test_support.install_hat_mock()

import gemy_classify  # noqa: E402
import gemy_qa  # noqa: E402


class TestClassifyIntegration(unittest.TestCase):
  def test_matches_blackbox_contract(self):
    self.assertEqual(gemy_classify.classify_heard("is the sky green"), "no")
    self.assertEqual(gemy_classify.classify_heard("is the sky blue"), "yes")
    self.assertEqual(
        gemy_classify.classify_heard("is the moon made out of cheese"), "no"
    )

  def test_gemma_skip_local_qa(self):
    skip, why = gemy_qa.should_skip_gemma_assist("is the moon made of cheese")
    self.assertTrue(skip)
    self.assertEqual(why, "local_qa")


if __name__ == "__main__":
  unittest.main()
