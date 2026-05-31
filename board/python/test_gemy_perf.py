#!/usr/bin/env python3
"""Performance + memory smoke tests for Gemy hot paths (PC: python test_gemy_perf.py).

Guards regressions: math/classify stay fast; loops do not grow memory without bound.
"""
from __future__ import annotations

import gc
import os
import sys
import time
import tracemalloc
import unittest
from unittest import mock

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import test_support

test_support.install_hat_mock()

import gemy_math  # noqa: E402
import gemy_qa  # noqa: E402
import gemy_stability as stab  # noqa: E402
import greeter  # noqa: E402

# Budgets for 5000 iterations on a typical dev PC (generous for slow CI).
_MATH_ITERS = 5000
_MATH_MAX_TOTAL_S = 0.75
_CLASSIFY_ITERS = 2000
_CLASSIFY_MAX_TOTAL_S = 1.5
_MEMORY_ITERS = 8000
_MEMORY_MAX_GROWTH_BYTES = 8 * 1024 * 1024  # 8 MiB top-line growth

_MATH_SAMPLES = (
    "is one plus one equal to two",
    "is seven times six equal to forty four",
    "is 7 times 6 equal to 42",
    "is eleven plus five equal to sixteen",
    "is eight minus three equal to five",
    "hello there",
    "how are you today",
)


class TestGemyPerf(unittest.TestCase):
    def test_math_try_yes_no_speed(self):
        gemy_math.clear_math_context()
        t0 = time.perf_counter()
        for i in range(_MATH_ITERS):
            gemy_math.try_math_yes_no(_MATH_SAMPLES[i % len(_MATH_SAMPLES)])
        elapsed = time.perf_counter() - t0
        per_us = (elapsed / _MATH_ITERS) * 1e6
        self.assertLess(
            elapsed,
            _MATH_MAX_TOTAL_S,
            f"math too slow: {elapsed:.3f}s total ({per_us:.0f} us/call)",
        )

    def test_classify_utterance_speed(self):
        greet = {"hello", "hi"}
        phrases = _MATH_SAMPLES + (
            "you are stupid", "haha funny", "Gemy turn off",
        )
        t0 = time.perf_counter()
        for i in range(_CLASSIFY_ITERS):
            text = phrases[i % len(phrases)]
            low, words = greeter._words_from_text(text)
            greeter.classify_utterance(text, low, words, greet)
        elapsed = time.perf_counter() - t0
        per_us = (elapsed / _CLASSIFY_ITERS) * 1e6
        self.assertLess(
            elapsed,
            _CLASSIFY_MAX_TOTAL_S,
            f"classify too slow: {elapsed:.3f}s ({per_us:.0f} us/call)",
        )

    def test_ensure_npu_idle_is_fast(self):
        w = __import__("gemma_mood").GemmaMoodSubprocess()
        t0 = time.perf_counter()
        for _ in range(10000):
            stab.ensure_npu_for_ears(w)
        elapsed = time.perf_counter() - t0
        self.assertLess(elapsed, 0.15, f"idle ensure_npu too slow: {elapsed:.3f}s")

    def test_qa_try_answer_speed(self):
        samples = (
            "is the sky blue",
            "is the moon made of cheese",
            "what is the meaning of life",
            "is ten bigger than five",
        )
        t0 = time.perf_counter()
        for i in range(10000):
            gemy_qa.try_answer_yes_no(samples[i % len(samples)])
        elapsed = time.perf_counter() - t0
        self.assertLess(elapsed, 0.8, f"gemy_qa too slow: {elapsed:.3f}s")

    def test_gemma_assist_allowed_speed(self):
        text = "I wonder what you think about the weather today"
        low, words = greeter._words_from_text(text)
        t0 = time.perf_counter()
        for _ in range(10000):
            stab.gemma_assist_allowed(text, low, words)
        elapsed = time.perf_counter() - t0
        self.assertLess(elapsed, 0.5, f"gemma_assist_allowed too slow: {elapsed:.3f}s")

    def test_math_loop_memory_bounded(self):
        gc.collect()
        tracemalloc.start()
        snap_before = tracemalloc.take_snapshot()
        gemy_math.clear_math_context()
        for i in range(_MEMORY_ITERS):
            gemy_math.try_math_yes_no(_MATH_SAMPLES[i % len(_MATH_SAMPLES)])
            if i % 500 == 0:
                gemy_math.clear_math_context()
        gc.collect()
        snap_after = tracemalloc.take_snapshot()
        tracemalloc.stop()
        growth = sum(
            s.size_diff
            for s in snap_after.compare_to(snap_before, "lineno")[:30]
            if s.size_diff > 0
        )
        self.assertLess(
            growth,
            _MEMORY_MAX_GROWTH_BYTES,
            f"math loop grew ~{growth / 1024 / 1024:.2f} MiB",
        )

    def test_classify_loop_memory_bounded(self):
        greet = {"hello", "hi"}
        phrases = _MATH_SAMPLES + ("you are stupid", "haha", "Gemy turn off")
        gc.collect()
        tracemalloc.start()
        snap_before = tracemalloc.take_snapshot()
        for i in range(_MEMORY_ITERS // 2):
            text = phrases[i % len(phrases)]
            low, words = greeter._words_from_text(text)
            greeter.classify_utterance(text, low, words, greet)
        gc.collect()
        snap_after = tracemalloc.take_snapshot()
        tracemalloc.stop()
        growth = sum(
            s.size_diff
            for s in snap_after.compare_to(snap_before, "lineno")[:30]
            if s.size_diff > 0
        )
        self.assertLess(
            growth,
            _MEMORY_MAX_GROWTH_BYTES,
            f"classify loop grew ~{growth / 1024 / 1024:.2f} MiB",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
