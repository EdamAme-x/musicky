"""Output: rendering engines, file output, debug dump, playback contexts."""

from musicky.out.debug import dump, to_jsonable
from musicky.out.output import output, render_wav_bytes
from musicky.out.play import (
    Context,
    close,
    create_midi_context,
    create_native_context,
    create_pygame_context,
    create_web_context,
    play,
)
from musicky.out.synth import (
    Engine,
    additive_engine,
    fluidsynth_engine,
    resolve_engine,
    saw_engine,
    sine_engine,
    square_engine,
    triangle_engine,
)

__all__ = [
    "Context",
    "Engine",
    "additive_engine",
    "close",
    "create_midi_context",
    "create_native_context",
    "create_pygame_context",
    "create_web_context",
    "dump",
    "fluidsynth_engine",
    "output",
    "play",
    "render_wav_bytes",
    "resolve_engine",
    "saw_engine",
    "sine_engine",
    "square_engine",
    "to_jsonable",
    "triangle_engine",
]
