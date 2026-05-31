#!/usr/bin/env python3
"""Minimal text-only Gemma 3 translation (no microphone needed).

Usage:
    python3 gemma_text.py "Text to translate" [Spanish|French]
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.gemma import load_gemma
from gemma_translate.translation import GemmaTranslationService


def main():
    text = sys.argv[1] if len(sys.argv) > 1 else "Hello, how are you today?"
    lang = sys.argv[2] if len(sys.argv) > 2 else "Spanish"

    try:
        from utils.npu import enable_npu_clock
        ok, msg = enable_npu_clock()
        print(f"[NPU] {msg}")
    except Exception as e:
        print(f"[NPU] skipped: {e}")

    print("Loading Gemma 3 270M (Torq/NPU)...")
    backend = load_gemma(use_llama=False, model_path=None, instruct_model=True)
    svc = GemmaTranslationService(backend)

    print(f"\nInput (English): {text}")
    print(f"Target language: {lang}\n")
    result = svc.translate(text, target_language=lang)
    print(f"Translation:     {result.text}")
    try:
        print(f"\n(stats: {result.stats.fmt(verbose=False)})")
    except Exception:
        pass


if __name__ == "__main__":
    main()
