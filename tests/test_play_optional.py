"""Smoke tests for optional backends."""

import importlib.util

import pytest

from musicky import chord, clip, create_native_context, create_pygame_context, musicky, piano


@pytest.mark.skipif(
    importlib.util.find_spec("pygame") is None,
    reason="pygame is not installed",
)
def test_pygame_context_constructs() -> None:
    pytest.importorskip("pygame")
    import os

    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    ctx = create_pygame_context(block=False)
    music = musicky(piano(clip(chord("C4"))))
    try:
        ctx.render(music)
    finally:
        ctx.close()


@pytest.mark.skipif(
    importlib.util.find_spec("fluidsynth") is None,
    reason="pyfluidsynth is not installed",
)
def test_native_context_requires_soundfont() -> None:
    pytest.importorskip("fluidsynth")
    with pytest.raises((OSError, RuntimeError, ValueError)):
        create_native_context("/nonexistent.sf2")
