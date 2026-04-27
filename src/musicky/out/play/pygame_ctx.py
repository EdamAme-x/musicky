"""pygame mixer context: render to MIDI bytes then play them locally.

This backend uses ``pygame.mixer.music`` to play a temporary MIDI file
generated from the Piece. pygame is loaded lazily so importing
``musicky.out.play`` does not require pygame to be installed; the cost is
paid only when ``create_pygame_context`` is actually called.

Install the optional dependency with::

    pip install musicky[pygame]
"""

from __future__ import annotations

import contextlib
import tempfile
from pathlib import Path
from typing import Any

from musicky.core.piece import Piece
from musicky.out.play.context import Context
from musicky.out.play.midi import render_to_bytes

__all__ = ["create_pygame_context"]


def create_pygame_context(
    *,
    frequency: int = 44100,
    buffer: int = 2048,
    block: bool = True,
) -> Context:
    """Build a Context that plays Pieces through pygame.mixer.

    `frequency` and `buffer` are forwarded to ``pygame.mixer.init``.
    When `block` is True (default), `render` waits for playback to finish
    before returning, which matches the synchronous mental model of
    ``play(music, ctx)``. Set False to fire-and-return.
    """
    pygame = _import_pygame()
    pygame.mixer.init(frequency=frequency, buffer=buffer)

    # We keep one temp file per context and overwrite it on each render so
    # pygame can re-load the same path. The file is removed on `close`.
    with tempfile.NamedTemporaryFile(suffix=".mid", delete=False) as fh:
        tmp = Path(fh.name)

    def render(music: Piece) -> None:
        tmp.write_bytes(render_to_bytes(music))
        pygame.mixer.music.load(str(tmp))
        pygame.mixer.music.play()
        if block:
            while pygame.mixer.music.get_busy():
                pygame.time.wait(50)

    def close() -> None:
        # Idempotent: tolerate double-close from user error.
        with contextlib.suppress(pygame.error):
            pygame.mixer.music.stop()
        with contextlib.suppress(pygame.error):
            pygame.mixer.quit()
        if tmp.exists():
            tmp.unlink()

    return Context(render=render, close=close)


def _import_pygame() -> Any:
    """Import pygame on demand; surface a helpful error when missing."""
    try:
        import pygame  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - exercised via env
        raise ImportError(
            "pygame is required for create_pygame_context(). "
            "Install with: pip install musicky[pygame]",
        ) from exc
    return pygame
