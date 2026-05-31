#!/usr/bin/env python3
"""Unit tests for Gemy logic (run on PC: python test_gemy_unit.py)."""
from __future__ import annotations

import os
import sys
import time
import unittest
from unittest import mock

# Repo board/python
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

# greeter imports hat (GPIO); mock so tests run on Windows.
_hat_mock = mock.MagicMock()
_hat_mock.MAX_OUTPUT_ON_SEC = 2.0
_hat_mock.start_safety_watchdog = mock.MagicMock()
sys.modules["hat"] = _hat_mock

import gemma_mood  # noqa: E402
import greeter  # noqa: E402


class TestMoodParsing(unittest.TestCase):
    def test_parse_valid(self):
        self.assertEqual(gemma_mood._parse_mood_label("funny"), "funny")
        self.assertEqual(gemma_mood._parse_mood_label("  mean \n"), "mean")
        self.assertEqual(gemma_mood._parse_mood_label("The answer is: nice"), "nice")

    def test_parse_alias(self):
        self.assertEqual(gemma_mood._parse_mood_label("insult"), "mean")
        self.assertEqual(gemma_mood._parse_mood_label("hello"), "greet")

    def test_parse_invalid(self):
        self.assertIsNone(gemma_mood._parse_mood_label(""))
        self.assertIsNone(gemma_mood._parse_mood_label("purple"))
        self.assertIsNone(gemma_mood._parse_mood_label("happy"))
        self.assertIsNone(gemma_mood.mood_for_reaction("neutral"))

    def test_parse_yes_no_sad(self):
        self.assertEqual(gemma_mood.normalize_mood_label("yes"), "yes")
        self.assertEqual(gemma_mood.normalize_mood_label("affirmative"), "yes")
        self.assertEqual(gemma_mood.normalize_mood_label("cry"), "sad")
        self.assertEqual(gemma_mood.mood_for_reaction("  MEAN \n"), "mean")


class TestKeywordClassify(unittest.TestCase):
    def setUp(self):
        self.greet = {"hello", "hi"}

    def _c(self, text):
        low, words = greeter._words_from_text(text)
        return greeter.classify_keywords(low, words, self.greet)

    def test_gemy_name(self):
        self.assertEqual(self._c("hey Gemy"), "gemy")

    def test_greet(self):
        self.assertEqual(self._c("hello there"), "greet")

    def test_funny(self):
        self.assertEqual(self._c("haha that's funny"), "funny")

    def test_mean(self):
        self.assertEqual(self._c("you are stupid"), "mean")

    def test_sad(self):
        self.assertEqual(self._c("nobody likes you"), "sad")
        self.assertEqual(self._c("I have sad news"), "sad")
        self.assertEqual(self._c("you must be so lonely"), "sad")

    def test_mean_before_sad(self):
        self.assertEqual(self._c("I hate you"), "mean")

    def test_yes_no(self):
        self.assertEqual(self._c("yeah"), "yes")
        self.assertEqual(self._c("nope"), "no")
        self.assertEqual(self._c("for sure"), "yes")
        self.assertEqual(self._c("no way"), "no")

    def test_math_quiz(self):
        def u(text):
            low, words = greeter._words_from_text(text)
            return greeter.classify_utterance(text, low, words, self.greet)

        self.assertEqual(u("is one plus one equal to two"), "yes")
        self.assertEqual(u("one plus one is two"), "yes")
        self.assertEqual(u("is one plus one five"), "no")
        self.assertEqual(u("one plus one equal to five"), "no")
        self.assertEqual(greeter._try_math_yes_no(*greeter._words_from_text(
            "two plus two equals four")), "yes")

    def test_resolve_reaction_kind(self):
        self.assertEqual(greeter.resolve_reaction_kind("funny"), "funny")
        self.assertEqual(greeter.resolve_reaction_kind("bogus"), "neutral")
        self.assertEqual(greeter.resolve_reaction_kind(None), "neutral")

    def test_off(self):
        low, words = greeter._words_from_text("Gemy turn off")
        self.assertEqual(
            greeter.classify_utterance("Gemy turn off", low, words, self.greet), "off")

    def test_conversation_without_gemma(self):
        def u(text):
            low, words = greeter._words_from_text(text)
            return greeter.classify_utterance(text, low, words, self.greet)

        self.assertEqual(u("how are you today"), "greet")
        self.assertEqual(u("great to hear"), "nice")
        self.assertEqual(u("good to hear that"), "nice")

    def test_gemma_assist_policy(self):
        import gemy_stability as stab

        low, words = greeter._words_from_text("Go")
        ok, _why = stab.gemma_assist_allowed("Go", low, words)
        self.assertFalse(ok)

        long_text = "I wonder what you think about the weather today"
        low2, words2 = greeter._words_from_text(long_text)
        ok2, _ = stab.gemma_assist_allowed(long_text, low2, words2)
        self.assertTrue(ok2)

    def test_see_phrase_is_greet(self):
        low, words = greeter._words_from_text("Can I see something?")
        self.assertEqual(
            greeter.classify_utterance(
                "Can I see something?", low, words, {"hello", "hi"}
            ),
            "greet",
        )


class TestGreeterIdle(unittest.TestCase):
    def test_no_idle_during_gemma_load(self):
        g = greeter.Greeter(idle_timeout=1.0, startup_grace_s=0.0)

        class FakeMood:
            loading = True

        g.last_activity = time.time() - 60
        g.idle_check(FakeMood())
        _hat_mock.led_off_all.assert_not_called()

    def test_no_idle_during_startup_grace(self):
        g = greeter.Greeter(idle_timeout=1.0, startup_grace_s=300.0)
        g.last_activity = time.time() - 60
        g.idle_check(None)
        _hat_mock.led_off_all.assert_not_called()


class TestGemmaSubprocessProtocol(unittest.TestCase):
    def test_worker_script_exists_in_repo(self):
        worker = os.path.join(_HERE, "gemma_mood_worker.py")
        self.assertTrue(os.path.isfile(worker))

    def test_subprocess_classify_protocol(self):
        """Fake worker mimics gemma_mood_worker OK / L| lines."""
        import subprocess
        import tempfile

        fake = (
            "import sys\n"
            "print('OK', flush=True)\n"
            "for line in sys.stdin:\n"
            "    if line.startswith('C|'):\n"
            "        print('L|funny', flush=True)\n"
        )
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write(fake)
            path = f.name
        try:
            gemma_mood._GEMMA_WORKER = path
            gemma_mood._VENV_PY = sys.executable
            # start() checks isfile(worker) — path is the temp script
            w = gemma_mood.GemmaMoodSubprocess(timeout_s=15.0)
            w.start()
            deadline = time.time() + 10.0
            while w.loading and time.time() < deadline:
                time.sleep(0.1)
            self.assertTrue(w.ready, f"worker not ready: state={w._state} err={w._error}")
            label = w.classify("haha funny")
            self.assertEqual(label, "funny")
            w.stop()
        finally:
            os.unlink(path)
            gemma_mood._GEMMA_WORKER = "/home/root/gemma_mood_worker.py"
            gemma_mood._VENV_PY = "/home/root/sl2610-examples/.venv/bin/python3"


class TestBootScript(unittest.TestCase):
    def test_boot_uses_no_vision(self):
        boot = os.path.join(_HERE, "..", "shell", "gemy-boot.sh")
        with open(boot, encoding="utf-8") as f:
            text = f.read()
        self.assertIn("--no-vision", text)
        self.assertIn("--no-intro", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
