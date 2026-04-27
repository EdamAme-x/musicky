"""Signal-flow nodes: the core data model.

Every musicky composition is a tree of `Node` values. Leaves are `Clip`s
that carry actual musical material; interior nodes are `Instrument`,
`Effect` and `Mix` that describe how the children combine on the way to
the speakers. The renderer walks this tree to produce MIDI or audio.

The whole tree is immutable. Constructors live as free functions next to
each Node subclass — `clip(...)`, `piano(...)`, `reverb(...)`, etc. —
so user code reads as a direct picture of the signal flow:

    reverb(
        piano(
            clip(verse, at=0),
            clip(chorus, at=16),
        ),
        amount=0.3,
    )

is exactly "a piano part with two regions, sent through reverb".
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from musicky.primitives.chord import Chord

__all__ = [
    "AudioFn",
    "ChordFn",
    "Clip",
    "Effect",
    "Instrument",
    "Mix",
    "Node",
    "Sample",
    "clip",
    "sample",
]

# An audio effect transforms one mono PCM buffer into another, given the
# sample rate and the piece's BPM (so time-based parameters like
# Automation curves can be evaluated against the beat grid).
# A symbolic effect rewrites Chord data before synthesis.
AudioFn = Callable[[list[float], int, float], list[float]]
ChordFn = Callable[[Chord], Chord]


@dataclass(frozen=True, slots=True)
class Clip:
    """A piece of musical content placed at a specific time.

    `content` is a `Chord` (which can hold one or many notes with their
    own internal timing). `at` is the start position in beats, measured
    from the origin of the enclosing piece.
    """

    content: Chord
    at: float


@dataclass(frozen=True, slots=True)
class Instrument:
    """An audio source that gives its children a sound.

    `name` is a human label ("piano", "bass", "tr808", ...). `program`
    is the General MIDI program number (0-127). `bank` selects an
    extended bank for synths that support more than 128 instruments
    (GS/XG/SoundFont kits); the default 0 means "stay on GM Bank 0".
    """

    name: str
    program: int
    bank: int
    children: tuple[Node, ...]


@dataclass(frozen=True, slots=True)
class Effect:
    """A transform applied to everything below it in the tree.

    `kind` and `params` exist for debugging and JSON serialization, so
    ``dump(music)`` can show what effects are wired up. The actual work
    is done by the optional callables stored alongside; the renderer
    invokes whichever ones are present.

      * `apply` — audio: ``(samples, sample_rate) -> samples``
      * `chord_transform` — symbolic: ``Chord -> Chord``
      * `transpose_offset` — special-case symbolic effect (semitones)

    A node with everything ``None`` / 0 acts as a pass-through; that is
    what `master(...)` returns. User code can build custom effects by
    constructing an `Effect` directly with their own `apply` callable —
    no registration is required.

    Function fields are excluded from equality so two effects with the
    same `kind` and `params` compare equal regardless of closure
    identity. This makes tests and JSON-roundtrip checks tractable.
    """

    kind: str
    params: dict[str, Any]
    children: tuple[Node, ...]
    apply: AudioFn | None = field(default=None, compare=False)
    chord_transform: ChordFn | None = field(default=None, compare=False)
    transpose_offset: int = 0


@dataclass(frozen=True, slots=True)
class Sample:
    """An external audio file placed on the timeline.

    `path` points to a wav/mp3/ogg/flac on disk. `at` is the start
    position in beats. `volume` is a linear gain factor (1.0 leaves
    the sample unchanged), and `speed` resamples the audio (1.0 is
    original; values above 1 play faster and higher-pitched, below 1
    slower and lower).

    MIDI export ignores Sample nodes because the SMF format has no
    way to embed raw audio. Audio output (`output(...)`) mixes the
    sample directly into the rendered buffer.
    """

    path: str
    at: float
    volume: float
    speed: float


@dataclass(frozen=True, slots=True)
class Mix:
    """A bare grouping node that mixes its children with no extra logic.

    `Mix` is what `musicky(...)` produces internally and what `seq(...)`
    returns after computing time offsets. Users rarely construct it by
    hand.
    """

    children: tuple[Node, ...]


Node = Clip | Instrument | Effect | Mix | Sample


def clip(content: Chord, at: float = 0.0) -> Clip:
    """Build a Clip. `at` defaults to 0 because most clips start at the top."""
    return Clip(content=content, at=at)


def sample(path: str, *, at: float = 0.0, volume: float = 1.0, speed: float = 1.0) -> Sample:
    """Drop an external audio file onto the timeline.

        sample("vocal_chop.wav", at=8.0, volume=0.7)

    Supports wav directly via the standard library; mp3/ogg/flac are
    decoded through ffmpeg, which must be on PATH for those formats.
    """
    return Sample(path=path, at=at, volume=volume, speed=speed)
