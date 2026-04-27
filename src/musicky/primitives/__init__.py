"""Primitive layer: pure-functional building blocks for musical data.

The primitive types (Note, Chord, Scale) carry the actual musical
content. Higher-level structure — clips, instruments, effects, the
piece itself — lives one level up in the package, where the Node tree
is assembled.
"""

from dataclasses import replace

from musicky.primitives.chord import (
    Chord,
    chord,
    inv,
    loop,
    mix,
    notes,
    octave,
    step,
    tx,
)
from musicky.primitives.note import (
    PITCH_CLASSES,
    Note,
    from_pitch,
    is_enharmonic,
    n,
    note,
    pitch,
)
from musicky.primitives.scale import (
    SCALE_INTERVALS,
    Scale,
    degree,
    prog,
    s,
    scale,
    scale_notes,
)

__all__ = [
    "replace",
    # note
    "Note",
    "PITCH_CLASSES",
    "from_pitch",
    "is_enharmonic",
    "n",
    "note",
    "pitch",
    # chord
    "Chord",
    "chord",
    "inv",
    "loop",
    "mix",
    "notes",
    "octave",
    "step",
    "tx",
    # scale
    "SCALE_INTERVALS",
    "Scale",
    "degree",
    "prog",
    "s",
    "scale",
    "scale_notes",
]
