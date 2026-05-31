#!/usr/bin/env python3
"""Stability tests: heartbeat, NPU release, listen timeouts, stuck recovery.

Run on PC: python test_gemy_stability.py
Guards against Coralboard freezes (Gemma holding NPU, hung listen, dead heartbeat).
"""
from __future__ import annotations

import os
import sys
import threading
import time
import unittest
from unittest import mock

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import test_support

_hat_mock = test_support.install_hat_mock()

import gemy_diag  # noqa: E402
import gemy_math  # noqa: E402
import gemy_stability as stab  # noqa: E402
import gemma_mood  # noqa: E402
import greeter  # noqa: E402


class TestStabilityConstants(unittest.TestCase):
    def test_gemma_block_shorter_than_worker_default(self):
        """Ears thread must not wait on Gemma as long as the worker infer cap."""
        self.assertLessEqual(stab.GEMMA_ASSIST_MAX_BLOCK_S, 20.0)
        self.assertGreater(stab.GEMMA_FIRST_CLASSIFY_MAX_BLOCK_S, stab.GEMMA_ASSIST_MAX_BLOCK_S)
        self.assertGreater(stab.GEMMA_ASSIST_MIN_INTERVAL_S, 30.0)

    def test_first_classify_timeout_longer(self):
        w = gemma_mood.GemmaMoodSubprocess()
        self.assertEqual(stab.gemma_assist_timeout_s(w), stab.GEMMA_FIRST_CLASSIFY_MAX_BLOCK_S)
        w._model_loaded = True
        self.assertEqual(stab.gemma_assist_timeout_s(w), stab.GEMMA_ASSIST_MAX_BLOCK_S)

    def test_listen_cap_bounded(self):
        self.assertLessEqual(stab._STUCK_LISTEN_S, stab.LISTEN_ONCE_MAX_S)
        self.assertLess(stab._STUCK_GEMMA_S, stab._STUCK_LISTEN_S)


class TestNpuRelease(unittest.TestCase):
    def test_npu_not_held_when_idle(self):
        w = gemma_mood.GemmaMoodSubprocess()
        self.assertFalse(stab.npu_held_by_gemma(w))
        self.assertFalse(stab.ensure_npu_for_ears(w))

    def test_ensure_npu_aborts_when_classify_busy(self):
        proc = mock.MagicMock()
        proc.poll.return_value = None
        w = gemma_mood.GemmaMoodSubprocess()
        w._proc = proc
        w._state = "ready"
        w._classify_busy = True
        w._npu_resident = True
        stab.ensure_npu_for_ears(w)
        self.assertIsNone(w._proc)
        self.assertEqual(w._state, "idle")
        self.assertFalse(w._classify_busy)
        proc.kill.assert_called()

    def test_ensure_npu_soft_unload_keeps_worker(self):
        w = gemma_mood.GemmaMoodSubprocess()
        w._proc = mock.MagicMock()
        w._proc.poll.return_value = None
        w._state = "ready"
        w._npu_resident = True
        with mock.patch.object(w, "release_npu_soft", return_value=True) as rel:
            stab.ensure_npu_for_ears(w)
        rel.assert_called_once()
        self.assertIsNotNone(w._proc)

    def test_finish_assist_keeps_worker(self):
        w = gemma_mood.GemmaMoodSubprocess()
        w._proc = mock.MagicMock()
        w._proc.poll.return_value = None
        w._state = "ready"
        w._npu_resident = True
        before = stab.seconds_since_last_gemma_assist()
        with mock.patch.object(w, "release_npu_soft", return_value=True) as rel:
            stab.finish_gemma_assist(w)
        rel.assert_called_once()
        after = stab.seconds_since_last_gemma_assist()
        self.assertLess(after, before)
        self.assertIsNotNone(w._proc)

    def test_npu_resident_only_when_model_loaded(self):
        w = gemma_mood.GemmaMoodSubprocess()
        w._proc = mock.MagicMock()
        w._proc.poll.return_value = None
        w._state = "ready"
        self.assertFalse(stab.npu_held_by_gemma(w))
        w._npu_resident = True
        self.assertTrue(stab.npu_held_by_gemma(w))

    def test_gemma_assist_rate_limit(self):
        stab.record_gemma_assist_attempt()
        ok, why = stab.gemma_assist_allowed(
            "this is a long enough phrase for gemma assist",
            "this is a long enough phrase for gemma assist",
            set("this is a long enough phrase for gemma assist".split()),
        )
        self.assertFalse(ok)
        self.assertIn("rate limit", why)


class TestListenOnceTimed(unittest.TestCase):
    def test_hung_listen_returns_none_and_recover(self):
        def slow_listen(stop_event=None):
            time.sleep(30)

        recognizer = mock.MagicMock()
        recognizer.listen_once = slow_listen
        source = mock.MagicMock()
        t0 = time.perf_counter()
        out = stab.listen_once_timed(
            recognizer, source, threading.Event(), gemma_mood=None, timeout_s=0.25
        )
        elapsed = time.perf_counter() - t0
        self.assertIsNone(out)
        self.assertLess(elapsed, 2.0)
        source.stop.assert_called()

    def test_fast_listen_returns_result(self):
        class R:
            text = "hello"

        recognizer = mock.MagicMock()
        recognizer.listen_once = lambda stop_event=None: R()
        out = stab.listen_once_timed(
            recognizer, mock.MagicMock(), threading.Event(), timeout_s=2.0
        )
        self.assertEqual(out.text, "hello")


class TestSmokeMonitorPulse(unittest.TestCase):
    def test_monitor_prints_pulse_line(self):
        hat = mock.MagicMock()
        stop = threading.Event()
        with mock.patch.dict(sys.modules, {"hat": hat}):
            with mock.patch.dict(os.environ, {"GEMY_SMOKE_MONITOR": "1"}):
                import gemy_diag as gd
                gd._heartbeat_pulses = 0
                stab.start_session_heartbeat(stop, None, interval_s=0.05)
                time.sleep(0.25)
                stop.set()
                time.sleep(0.1)
        self.assertGreaterEqual(gd.heartbeat_pulse_count(), 1)


class TestSessionHeartbeat(unittest.TestCase):
    def _run_heartbeat(self, greeter, seconds=0.35, interval=0.05):
        hat = mock.MagicMock()
        stop = threading.Event()
        with mock.patch.dict(sys.modules, {"hat": hat}):
            stab.start_session_heartbeat(stop, greeter, interval_s=interval)
            time.sleep(seconds)
            stop.set()
            time.sleep(interval * 2)
        return hat

    def test_heartbeat_pulses_when_idle(self):
        g = greeter.Greeter()
        g._reacting = False
        hat = self._run_heartbeat(g)
        self.assertGreaterEqual(hat.hold_led.call_count, 2)
        hat.hold_led.assert_called_with("red", 0.1)
        self.assertGreaterEqual(gemy_diag._heartbeat_pulses, 1)

    def test_heartbeat_skips_during_reaction(self):
        greeter_obj = greeter.Greeter()
        greeter_obj._reacting = True
        hat = self._run_heartbeat(greeter_obj, seconds=0.3)
        hat.hold_led.assert_not_called()

    def test_heartbeat_thread_is_daemon(self):
        hat = mock.MagicMock()
        stop = threading.Event()
        with mock.patch.dict(sys.modules, {"hat": hat}):
            stab.start_session_heartbeat(stop, greeter.Greeter(), interval_s=0.1)
            time.sleep(0.05)
            threads = [t for t in threading.enumerate() if t.name == "session-heartbeat"]
            self.assertEqual(len(threads), 1)
            self.assertTrue(threads[0].daemon)
            stop.set()


class TestStuckGuard(unittest.TestCase):
    def test_stuck_listen_wait_recovers_mic(self):
        source = mock.MagicMock()
        gemma = gemma_mood.GemmaMoodSubprocess()
        stop = threading.Event()
        with mock.patch(
            "gemy_trace.get_phase_age",
            return_value=("listen_wait", "test", 120.0),
        ):
            stab.start_stuck_guard(
                stop, gemma_mood=gemma, source=source, interval_s=0.05
            )
            time.sleep(0.2)
            stop.set()
            time.sleep(0.1)
        source.stop.assert_called()

    def test_stuck_gemma_releases_npu(self):
        w = gemma_mood.GemmaMoodSubprocess()
        w._model_loaded = True
        w._npu_resident = True
        w._proc = mock.MagicMock()
        w._proc.poll.return_value = None
        w._state = "ready"
        stop = threading.Event()
        def _soft():
            w._npu_resident = False
            return True

        with mock.patch(
            "gemy_trace.get_phase_age",
            return_value=("gemma_assist", "x", 60.0),
        ):
            with mock.patch.object(w, "release_npu_soft", side_effect=_soft) as rel:
                stab.start_stuck_guard(stop, gemma_mood=w, interval_s=0.05)
                time.sleep(0.25)
                stop.set()
                time.sleep(0.1)
            rel.assert_called()
        self.assertFalse(w._npu_resident)


class TestGreeterStability(unittest.TestCase):
    def setUp(self):
        _hat_mock.reset_mock()
        gemy_diag._heartbeat_pulses = 0
        gemy_diag._heartbeat_last_at = 0.0

    def test_abort_reaction_clears_lock(self):
        g = greeter.Greeter()
        g._reacting = True
        g.abort_reaction()
        self.assertFalse(g._reacting)

    def test_react_always_force_all_off_on_error(self):
        g = greeter.Greeter(cooldown=0)
        bad = mock.Mock(side_effect=RuntimeError("led fail"))
        orig = greeter.REACTIONS.get("neutral")
        greeter.REACTIONS["neutral"] = bad
        try:
            g.react("neutral", "test")
        finally:
            if orig is not None:
                greeter.REACTIONS["neutral"] = orig
            else:
                greeter.REACTIONS.pop("neutral", None)
        _hat_mock.force_all_off.assert_called()
        self.assertFalse(g._reacting)

    def test_try_gemma_assist_finishes_on_classify_error(self):
        gemma = mock.MagicMock()
        gemma.ready = True
        gemma._classify_busy = False
        gemma._assist_cooldown_until = 0.0
        gemma._state = "ready"
        gemma.classify.side_effect = RuntimeError("npu oom")
        text = "I wonder what you think about the weather today"
        low, words = greeter._words_from_text(text)
        out = greeter.try_gemma_mood_assist(text, gemma, low=low, words=words)
        self.assertIsNone(out)
        gemma.classify.assert_called_once()
        gemma.finish_assist.assert_called_once()

    def test_init_gemma_serial_disabled(self):
        args = argparse_namespace(gemma_mood=True, gemma_mood_serial=True)
        out = greeter.init_gemma_mood(args, greeter.Greeter(), threading.Event())
        self.assertIsNone(out)

    def test_unparsed_math_may_call_gemma(self):
        """Unparsed math is not blocked from Gemma assist (yes/no only)."""
        low, words = greeter._words_from_text("is ninety nine plus one equal to fifty")
        self.assertTrue(gemy_math.looks_like_math_quiz(low))
        out = greeter._maybe_gemma_assist(
            "is ninety nine plus one equal to fifty",
            low, words, mock.MagicMock(), None, True,
        )
        self.assertIsNone(out)


def argparse_namespace(**kwargs):
    return type("NS", (), kwargs)()


class TestGemmaSubprocessAbort(unittest.TestCase):
    def test_release_clears_busy_and_proc(self):
        w = gemma_mood.GemmaMoodSubprocess()
        w._proc = mock.MagicMock()
        w._proc.poll.return_value = None
        w._classify_busy = True
        w._state = "ready"
        w.release_npu()
        self.assertFalse(w._classify_busy)
        self.assertIsNone(w._proc)
        self.assertEqual(w._state, "idle")


if __name__ == "__main__":
    unittest.main(verbosity=2)
