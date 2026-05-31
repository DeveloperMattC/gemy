#!/usr/bin/env python3
"""Shared test setup — mock GPIO hat before importing greeter."""
from __future__ import annotations

import sys
from unittest import mock

_HAT: mock.MagicMock | None = None


def install_hat_mock() -> mock.MagicMock:
    """Call once before ``import greeter`` on PC (no gpiochip / gpioset).

    Returns the singleton mock so tests always patch the same object greeter uses.
    """
    global _HAT
    if _HAT is None:
        _HAT = mock.MagicMock()
        _HAT.MAX_OUTPUT_ON_SEC = 2.0
        _HAT.start_safety_watchdog = mock.MagicMock()
        _HAT.force_all_off = mock.MagicMock()
    sys.modules["hat"] = _HAT
    return _HAT
