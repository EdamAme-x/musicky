"""Random number generator helpers.

All functions in musicky that consume randomness must accept either a `seed`
(int) or a pre-built `random.Random` instance. When neither is provided, the
current wall-clock time is used. This keeps every random-driven operation
reproducible while preserving a sensible default.
"""

from __future__ import annotations

import random
import time

__all__ = ["Rng", "make_rng"]

# Public alias so users do not need to import `random.Random` directly.
Rng = random.Random


def make_rng(seed: int | None = None) -> Rng:
    """Build a Random instance.

    Passing the same integer seed always produces the same sequence, which is
    the property we want for testable composition. When `seed` is None, the
    current time (nanoseconds) is used so successive calls differ.
    """
    if seed is None:
        seed = time.time_ns()
    return random.Random(seed)
