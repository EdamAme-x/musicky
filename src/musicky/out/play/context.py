"""Context type and the `play` / `close` entry points.

`Context` is a frozen dataclass that holds two functions: how to render a
Piece, and how to release backend resources. Backend modules construct a
`Context` from closures so that no class is involved in the public API.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from musicky.core.piece import Piece

__all__ = ["Context", "close", "play"]


@dataclass(frozen=True, slots=True)
class Context:
    """A playback target.

    `render(music)` must perform the backend-specific work — emit a MIDI
    file, push to a synthesiser, build an HTML bundle, etc. `close()` is
    called by `close(ctx)` and should be idempotent so that double-close
    in user code is safe.
    """

    render: Callable[[Piece], None]
    close: Callable[[], None]


def play(music: Piece, ctx: Context) -> None:
    """Render `music` through `ctx`. Pure dispatch; no logic of its own."""
    ctx.render(music)


def close(ctx: Context) -> None:
    """Tear down a context. Equivalent to ``ctx.close()`` but reads better
    as the inverse of `play` at call sites that look like::

        ctx = create_pygame_context()
        try:
            play(music, ctx)
        finally:
            close(ctx)
    """
    ctx.close()
