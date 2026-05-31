#!/usr/bin/env python3
"""Hardware wiring audit — every beep kind must reach a hat handler."""
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

HAT_FN = {
    "gemy": "gemy_name_ack",
    "greet": "gemy_greet",
    "funny": "gemy_funny",
    "nice": "gemy_nice",
    "mean": "gemy_mean",
    "sad": "gemy_sad",
    "yes": "gemy_yes",
    "no": "gemy_no",
    "neutral": "gemy_neutral",
}


class TestHatWiring(unittest.TestCase):
    def test_reactions_dict_matches_beep_set(self):
        import greeter
        self.assertEqual(
            frozenset(greeter.REACTIONS), gemy_reactions.BEEP_REACTIONS
        )

    def test_hat_exports_handlers(self):
        import hat
        for kind, fn_name in HAT_FN.items():
            self.assertTrue(hasattr(hat, fn_name), kind)

    def test_react_chain_calls_hat(self):
        import greeter
        for kind, hat_fn in HAT_FN.items():
            with self.subTest(kind=kind):
                with mock.patch.object(greeter.hat, hat_fn, mock.MagicMock()) as m:
                    greeter.REACTIONS[kind]()
                    m.assert_called_once()


if __name__ == "__main__":
    unittest.main(verbosity=2)
