#!/usr/bin/env python3
"""On-board smoke test for Gemy stack. Exit 0 = pass, 1 = fail.

  /home/root/sl2610-examples/.venv/bin/python3 /home/root/gemy_smoke_test.py
  /home/root/sl2610-examples/.venv/bin/python3 /home/root/gemy_smoke_test.py --quick
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time

PY = "/home/root/sl2610-examples/.venv/bin/python3"
ROOT = "/home/root"
EXAMPLES = "/home/root/sl2610-examples"
WORKER = f"{ROOT}/gemma_mood_worker.py"
GREETER = f"{ROOT}/greeter.py"
GEMMA_TIMEOUT = int(os.environ.get("GEMY_GEMMA_TIMEOUT", "200"))


def ok(msg: str) -> None:
    print(f"  OK  {msg}", flush=True)


def fail(msg: str) -> None:
    print(f"  FAIL  {msg}", flush=True)


def check_files() -> bool:
    print("[1] Required files on board", flush=True)
    good = True
    for path in (GREETER, f"{ROOT}/hat.py", f"{ROOT}/gemma_mood.py", WORKER, PY):
        if os.path.isfile(path):
            ok(path)
        else:
            fail(f"missing {path}")
            good = False
    return good


def check_imports() -> bool:
    print("[2] Python imports", flush=True)
    cmd = (
        f"import sys; sys.path[:0]=['{ROOT}','{EXAMPLES}']; "
        "import greeter, gemma_mood, hat; print('imports')"
    )
    try:
        out = subprocess.check_output([PY, "-c", cmd], text=True, stderr=subprocess.STDOUT, timeout=60)
        if "imports" in out:
            ok("greeter, gemma_mood, hat")
            return True
    except Exception as e:
        fail(str(e))
    return False


def check_hat_force_off() -> bool:
    print("[3] HAT force-off", flush=True)
    try:
        subprocess.run(
            ["python3", f"{ROOT}/hat.py", "force-off"],
            timeout=15, check=False, capture_output=True,
        )
        ok("hat.py force-off")
        return True
    except Exception as e:
        fail(str(e))
        return False


def check_gemma_worker(quick: bool) -> bool:
    if quick:
        print("[4] Gemma worker (skipped --quick)", flush=True)
        return True
    print(f"[4] Gemma worker (timeout {GEMMA_TIMEOUT}s)", flush=True)
    if not os.path.isfile(WORKER):
        fail("worker missing")
        return False
    env = {**os.environ, "PYTHONPATH": f"{EXAMPLES}:{ROOT}"}
    try:
        proc = subprocess.Popen(
            [PY, "-u", WORKER],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            cwd=ROOT,
            env=env,
        )
    except Exception as e:
        fail(f"start worker: {e}")
        return False

    import threading

    def _drain_stderr():
        try:
            for line in proc.stderr:
                line = line.rstrip()
                if line:
                    print(f"    worker stderr: {line}", flush=True)
        except Exception:
            pass

    threading.Thread(target=_drain_stderr, daemon=True).start()

    t0 = time.time()
    ready = False
    try:
        while time.time() - t0 < GEMMA_TIMEOUT:
            if proc.poll() is not None:
                fail(f"worker exited early code={proc.returncode}")
                return False
            line = proc.stdout.readline()
            if not line:
                time.sleep(0.2)
                continue
            line = line.strip()
            print(f"    worker stdout: {line!r}", flush=True)
            if line == "OK":
                ready = True
                break
            if line == "FAIL":
                fail("worker printed FAIL")
                return False
        if not ready:
            fail("timeout waiting for OK")
            proc.kill()
            return False
        ok("worker ready")

        proc.stdin.write("C|you are so funny haha\n")
        proc.stdin.flush()
        label_line = proc.stdout.readline().strip()
        print(f"    classify: {label_line!r}", flush=True)
        if not label_line.startswith("L|"):
            fail(f"bad classify line: {label_line!r}")
            return False
        label = label_line[2:].strip()
        if label not in ("funny", "nice", "neutral", "greet", ""):
            fail(f"unexpected label {label!r}")
            return False
        ok(f"classify returned {label!r}")
        return True
    finally:
        try:
            proc.kill()
        except Exception:
            pass


def check_greeter_help() -> bool:
    print("[5] greeter.py --help", flush=True)
    try:
        out = subprocess.check_output(
            [PY, GREETER, "--help"], text=True, stderr=subprocess.STDOUT, timeout=30)
        if "--no-vision" in out and "--no-gemma-mood" in out:
            ok("argparse")
            return True
        fail("help missing expected flags")
    except Exception as e:
        fail(str(e))
    return False


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--quick", action="store_true", help="skip Gemma NPU load")
    args = p.parse_args()

    print("Gemy smoke test on board", flush=True)
    results = [
        check_files(),
        check_imports(),
        check_hat_force_off(),
        check_gemma_worker(args.quick),
        check_greeter_help(),
    ]
    passed = sum(results)
    total = len(results)
    print(f"\nResult: {passed}/{total} checks passed", flush=True)
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
