#!/usr/bin/env python3
"""Isolated Gemma 3 mood worker (separate process from greeter.py).

Greeter uses keyword moods first; this process loads Gemma on the NPU only when
needed (first classify or P|preload). Moonshine STT runs in greeter and owns the
NPU while listening.

Protocol (stdout / stdin line-based):
  stderr  progress logs
  stdout  READY           worker alive (no model loaded yet)
  stdout  OK              preload or release done
  stdin   P|              preload model on NPU (optional warm-up)
  stdin   R|              unload model, free NPU (keep process alive)
  stdin   C|<utterance>   classify (loads model on first request if needed)
  stdout  L|<mood|empty>  one mood label or empty
"""
from __future__ import annotations

import os
import sys

os.environ["GEMMA_WORKER"] = "1"

sys.path.insert(0, "/home/root/sl2610-examples")
sys.path.insert(0, "/home/root")

from gemma_mood import GemmaMoodClassifier  # noqa: E402


def _log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def _load_classifier(classifier):
    if classifier is None:
        _log("[gemma-worker] loading Gemma 3 on NPU (first check, can take 1-3 min)...")
        classifier = GemmaMoodClassifier()
        classifier.load()
        _log("[gemma-worker] model ready")
    return classifier


def _release_classifier(classifier):
    if classifier is not None:
        try:
            classifier.unload()
        except Exception as e:
            _log(f"[gemma-worker] unload: {e}")
    return None


def main() -> int:
    try:
        _log("[gemma-worker] ready (Gemma loads on first mood check)")
        print("READY", flush=True)
        classifier = None
        for raw in sys.stdin:
            line = raw.strip()
            if not line:
                continue
            if line.startswith("R|"):
                classifier = _release_classifier(classifier)
                print("OK", flush=True)
                continue
            if line.startswith("P|"):
                classifier = _load_classifier(classifier)
                print("OK", flush=True)
                continue
            if not line.startswith("C|"):
                _log(f"[gemma-worker] ignore: {line!r}")
                continue
            text = line[2:]
            classifier = _load_classifier(classifier)
            label = classifier.classify(text) or ""
            print(f"L|{label}", flush=True)
    except Exception as e:
        _log(f"[gemma-worker] fatal: {e}")
        print("FAIL", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
