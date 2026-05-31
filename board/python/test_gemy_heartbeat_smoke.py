#!/usr/bin/env python3
"""PC tests for gemy_heartbeat_smoke helpers (no adb required)."""
from __future__ import annotations

import os
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import gemy_heartbeat_smoke as hb  # noqa: E402
import gemy_diag  # noqa: E402


class TestHeartbeatSmokeHelpers(unittest.TestCase):
    def test_pulse_regex(self):
        m = hb.PULSE_LINE.search("[stability] heartbeat pulse 7")
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), "7")

    def test_read_meminfo(self):
        with tempfile.NamedTemporaryFile("w", delete=False) as f:
            f.write("MemTotal:       2048000 kB\n")
            f.write("MemAvailable:    512000 kB\n")
            path = f.name
        try:
            orig = hb.read_meminfo
            def fake():
                out = {}
                with open(path, encoding="utf-8") as mf:
                    for line in mf:
                        parts = line.split()
                        if len(parts) >= 2 and parts[0].endswith(":"):
                            out[parts[0][:-1]] = int(parts[1])
                return out
            hb.read_meminfo = fake
            mi = hb.read_meminfo()
            self.assertEqual(mi["MemAvailable"], 512000)
        finally:
            hb.read_meminfo = orig
            os.unlink(path)

    def test_fail_markers_detect_stuck(self):
        line = "[stability] STUCK 'listen_wait' for 120s"
        self.assertTrue(any(m in line for m in hb.FAIL_MARKERS))

    def test_diag_pulse_count(self):
        gemy_diag._heartbeat_pulses = 0
        gemy_diag.mark_heartbeat_pulse("test")
        self.assertEqual(gemy_diag.heartbeat_pulse_count(), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
