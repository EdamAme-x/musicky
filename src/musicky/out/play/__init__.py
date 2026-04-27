"""Playback layer: render a Piece through a Context.

A `Context` is a pure data record that bundles two callables: a `render`
function that takes a `Piece` and produces output, and a `close` function
that releases any resources the context acquired.

The `play` entry point is intentionally trivial — it forwards to
``ctx.render(music)``. The split exists so users can write the same call
site against any backend (MIDI file, pygame mixer, native synth, web
bundle) and swap them by changing the context constructor.
"""

from musicky.out.play.context import Context, close, play
from musicky.out.play.midi import create_midi_context
from musicky.out.play.native import create_native_context
from musicky.out.play.pygame_ctx import create_pygame_context
from musicky.out.play.web import create_web_context

__all__ = [
    "Context",
    "close",
    "create_midi_context",
    "create_native_context",
    "create_pygame_context",
    "create_web_context",
    "play",
]
