#!/usr/bin/env python3
"""On-board liveness smoke: session heartbeat pulses + /proc memory while greeter runs.

Exit 0 = pass, 1 = fail. Run on the Coralboard (or via adb from test-gemy.ps1):

  GEMY_SMOKE_MONITOR=1 /home/root/sl2610-examples/.venv/bin/python3 \\
      /home/root/gemy_heartbeat_smoke.py

  ... --seconds 50 --no-gemma   # keywords-only (stable baseline)
  ... --seconds 90 --with-gemma # optional heavier path
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import threading
import time

PY = os.environ.get("GEMY_PYTHON", "/home/root/sl2610-examples/.venv/bin/python3")
GREETER = "/home/root/greeter.py"
ROOT = "/home/root"

# Session heartbeat ~1.6s; allow gaps during reactions but not a full stall.
PULSE_LINE = re.compile(r"\[stability\]\s+heartbeat pulse\s+(\d+)")
FAIL_MARKERS = (
    "listen_once hung",
    "STUCK ",
    "[ears] stopped:",
    "NPU busy",
    "heartbeat pulse failed",
)


def ok(msg: str) -> None:
    print(f"  OK  {msg}", flush=True)


def fail(msg: str) -> None:
    print(f"  FAIL  {msg}", flush=True)


def read_meminfo() -> dict[str, int]:
    out: dict[str, int] = {}
    try:
        with open("/proc/meminfo", encoding="utf-8") as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 2 and parts[0].endswith(":"):
                    key = parts[0][:-1]
                    try:
                        out[key] = int(parts[1])
                    except ValueError:
                        pass
    except OSError as e:
        fail(f"read meminfo: {e}")
    return out


def read_rss_kb(pid: int) -> int | None:
    path = f"/proc/{pid}/status"
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1])
    except OSError:
        return None
    return None


def _drain_output(stream, box: dict) -> None:
    pulses: list[float] = []
    errors: list[str] = []
    box["pulses"] = pulses
    box["errors"] = errors
    try:
        for raw in stream:
            line = raw.rstrip()
            if line:
                print(f"    | {line}", flush=True)
            for marker in FAIL_MARKERS:
                if marker in line:
                    errors.append(line)
            m = PULSE_LINE.search(line)
            if m:
                pulses.append(time.time())
    except Exception as e:
        errors.append(f"read error: {e}")


def run_greeter_liveness(
    seconds: float,
    with_gemma: bool,
    with_speech: bool,
) -> bool:
    print(f"[liveness] greeter for ~{seconds:.0f}s "
          f"(gemma={with_gemma}, speech={with_speech})", flush=True)
    if not os.path.isfile(GREETER):
        fail(f"missing {GREETER}")
        return False
    if not os.path.isfile(PY):
        fail(f"missing {PY}")
        return False

    greeter_args = [
        PY, "-u", GREETER,
        "--no-vision",
        "--no-intro",
        "--diag",
        "--duration", str(int(seconds) + 8),
    ]
    if not with_gemma:
        greeter_args.append("--no-gemma-mood")
    else:
        greeter_args.append("--gemma-mood")
    if not with_speech:
        greeter_args.append("--no-speech")

    env = {
        **os.environ,
        "GEMY_SMOKE_MONITOR": "1",
        "PYTHONPATH": f"/home/root/sl2610-examples:{ROOT}",
    }
    mem0 = read_meminfo()
    avail0 = mem0.get("MemAvailable", mem0.get("MemFree", 0))
    print(f"  mem start: MemAvailable={avail0} kB", flush=True)

    box: dict = {}
    try:
        proc = subprocess.Popen(
            greeter_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=ROOT,
            env=env,
        )
    except Exception as e:
        fail(f"start greeter: {e}")
        return False

    reader = threading.Thread(
        target=_drain_output, args=(proc.stdout, box), daemon=True)
    reader.start()

    min_avail = avail0
    max_rss: int | None = None
    rss0: int | None = None
    t0 = time.time()
    min_pulses = max(3, int(seconds / 4.0))

    while time.time() - t0 < seconds + 5:
        if proc.poll() is not None:
            break
        mi = read_meminfo()
        avail = mi.get("MemAvailable", mi.get("MemFree", 0))
        min_avail = min(min_avail, avail)
        rss = read_rss_kb(proc.pid)
        if rss is not None:
            if rss0 is None:
                rss0 = rss
            max_rss = rss if max_rss is None else max(max_rss, rss)
        time.sleep(2.0)

    try:
        proc.wait(timeout=25)
    except subprocess.TimeoutExpired:
        fail("greeter did not exit after --duration")
        proc.kill()
        return False

    reader.join(timeout=5.0)
    pulses: list[float] = box.get("pulses", [])
    errors: list[str] = box.get("errors", [])

    print(f"  mem min MemAvailable={min_avail} kB", flush=True)
    if max_rss is not None:
        print(f"  greeter VmRSS max={max_rss} kB (start {rss0} kB)", flush=True)

    if errors:
        for e in errors[:5]:
            fail(e)
        return False

    if proc.returncode not in (0, None):
        fail(f"greeter exit code {proc.returncode}")
        return False

    if len(pulses) < min_pulses:
        fail(f"only {len(pulses)} heartbeat pulses (need >={min_pulses})")
        return False

    # Longest gap between consecutive pulses (react holdoff can skip a few).
    if len(pulses) >= 2:
        gaps = [pulses[i] - pulses[i - 1] for i in range(1, len(pulses))]
        worst = max(gaps)
        if worst > 12.0:
            fail(f"heartbeat gap {worst:.1f}s (>12s — main thread may be blocked)")
            return False
        ok(f"heartbeat pulses={len(pulses)}, worst_gap={worst:.1f}s")

    min_avail_kb = int(os.environ.get("GEMY_MIN_MEM_AVAIL_KB", "12288"))
    if min_avail < min_avail_kb:
        fail(f"MemAvailable dropped to {min_avail} kB (min {min_avail_kb})")
        return False
    ok(f"MemAvailable stayed >= {min_avail} kB")

    max_rss_mb = int(os.environ.get("GEMY_MAX_GREETER_RSS_MB", "512"))
    if max_rss is not None and max_rss > max_rss_mb * 1024:
        fail(f"greeter RSS {max_rss} kB exceeds {max_rss_mb} MiB cap")
        return False
    if max_rss is not None:
        ok(f"greeter RSS peak {max_rss // 1024} MiB")

    ok("liveness run complete")
    return True


def check_stability_imports() -> bool:
    print("[0] stability + diag imports", flush=True)
    cmd = (
        f"import sys; sys.path[:0]=['{ROOT}','/home/root/sl2610-examples']; "
        "import gemy_stability, gemy_diag; "
        "assert hasattr(gemy_diag, 'heartbeat_pulse_count')"
    )
    try:
        subprocess.check_output([PY, "-c", cmd], text=True, stderr=subprocess.STDOUT, timeout=30)
        ok("gemy_stability, gemy_diag")
        return True
    except Exception as e:
        fail(str(e))
        return False


def main() -> int:
    p = argparse.ArgumentParser(description="Gemy heartbeat + memory liveness smoke")
    p.add_argument("--seconds", type=float, default=45.0,
                   help="how long to run greeter (default 45)")
    p.add_argument("--with-gemma", action="store_true",
                   help="enable --gemma-mood (heavier; may skip if no NPU time)")
    p.add_argument("--with-speech", action="store_true",
                   help="enable mic/Moonshine (needs HAT mic; default is no-speech)")
    args = p.parse_args()

    print("Gemy heartbeat + memory smoke (on board)", flush=True)
    results = [
        check_stability_imports(),
        run_greeter_liveness(args.seconds, args.with_gemma, args.with_speech),
    ]
    passed = sum(results)
    total = len(results)
    print(f"\nResult: {passed}/{total} checks passed", flush=True)
    if passed < total:
        print("Tip: run keywords-only first:", flush=True)
        print("  GEMY_SMOKE_MONITOR=1 python3 /home/root/gemy_heartbeat_smoke.py --seconds 45",
              flush=True)
        print("If freezes persist, compare with greet-demo.ps1 -NoGemmaMood", flush=True)
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
