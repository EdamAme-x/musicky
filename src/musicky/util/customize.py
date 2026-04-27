"""`custom`: bind keyword arguments to a function once, reuse it many times.

When the same effect is invoked repeatedly with non-default knobs, passing
those knobs at every call site is noisy. `custom` returns a new callable
with those keywords pre-bound. The bound keywords can still be overridden
at call time, just like `functools.partial`.

The wrapper preserves ``__name__``, ``__doc__`` and ``__wrapped__`` so
introspection (help, IDE tooltips, error tracebacks) keeps pointing at the
original function. This is what `functools.partial` does *not* do, which
is the only reason this module exists.
"""

from __future__ import annotations

import functools
from collections.abc import Callable
from typing import Any, ParamSpec, TypeVar

__all__ = ["custom"]

_P = ParamSpec("_P")
_R = TypeVar("_R")


def custom(fn: Callable[_P, _R], **bound: Any) -> Callable[..., _R]:
    """Return a callable equal to `fn` with `bound` keywords pre-applied.

    Example::

        my_noise = custom(noise, interval=0.5, velocity=80)
        my_noise(scale("C major"), length=16, seed=1)

    Call-site arguments win over bound ones, so users can override any
    pre-bound keyword as needed::

        my_noise(scale("C major"), length=16, interval=0.25, seed=1)
    """

    @functools.wraps(fn)
    def wrapper(*args: object, **kwargs: object) -> _R:
        # Caller's kwargs override bound defaults.
        merged = {**bound, **kwargs}
        return fn(*args, **merged)  # type: ignore[arg-type]

    # Augment the docstring so users discover what was pre-bound when they
    # call help() on the resulting function.
    if bound:
        bound_repr = ", ".join(f"{k}={v!r}" for k, v in bound.items())
        original_doc = wrapper.__doc__ or ""
        wrapper.__doc__ = f"{original_doc}\n\n[custom] pre-bound keywords: {bound_repr}".strip()

    return wrapper
