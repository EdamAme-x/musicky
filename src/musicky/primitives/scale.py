"""Scale primitive: an ordered set of pitch intervals from a tonic.

A `Scale` is defined by its tonic note plus an interval pattern (semitone
steps between consecutive scale degrees). The pattern always sums to 12 for
diatonic scales but the type does not enforce this, so users can build
exotic scales freely.

The functions here let you enumerate scale notes, pull a chord built on a
given scale degree (`degree`), and turn a numeric figured-bass-style string
into a chord progression (`prog`).
"""

from __future__ import annotations

from dataclasses import dataclass

from musicky.primitives.chord import Chord, chord
from musicky.primitives.note import (
    PITCH_CLASSES,
    Note,
    from_pitch,
)
from musicky.primitives.note import (
    note as mk_note,
)
from musicky.primitives.note import (
    pitch as note_pitch,
)

__all__ = [
    "SCALE_INTERVALS",
    "Scale",
    "degree",
    "prog",
    "s",
    "scale",
    "scale_notes",
]

# Common interval patterns. Values are semitone steps starting from the
# tonic. The list does not include the closing octave (12) because it is
# implied; this matches how musicpy presents scales.
SCALE_INTERVALS: dict[str, tuple[int, ...]] = {
    "major": (2, 2, 1, 2, 2, 2, 1),
    "minor": (2, 1, 2, 2, 1, 2, 2),  # natural minor
    "harmonic_minor": (2, 1, 2, 2, 1, 3, 1),
    "melodic_minor": (2, 1, 2, 2, 2, 2, 1),
    "dorian": (2, 1, 2, 2, 2, 1, 2),
    "phrygian": (1, 2, 2, 2, 1, 2, 2),
    "lydian": (2, 2, 2, 1, 2, 2, 1),
    "mixolydian": (2, 2, 1, 2, 2, 1, 2),
    "locrian": (1, 2, 2, 1, 2, 2, 2),
    "pentatonic": (2, 2, 3, 2, 3),
    "blues": (3, 2, 1, 1, 3, 2),
    "chromatic": (1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1),
}


@dataclass(frozen=True, slots=True)
class Scale:
    """An immutable scale value."""

    tonic: Note  # the root note (octave matters: it anchors `scale_notes`)
    intervals: tuple[int, ...]  # semitone steps between consecutive degrees
    name: str | None  # optional human-readable label for debugging


def scale(spec: str, mode: str = "major") -> Scale:
    """Build a Scale from ``"C major"`` or ``("C5", "minor")`` style input.

    `spec` accepts either ``"<pitch> <mode>"`` (one space) or just a pitch
    name (in which case `mode` argument is used). When no octave is given
    the scale is anchored at octave 4 — a sensible middle of the keyboard.
    """
    parts = spec.strip().split()
    if len(parts) == 2:
        pitch_part, mode = parts
    elif len(parts) == 1:
        pitch_part = parts[0]
    else:
        raise ValueError(f"invalid scale spec: {spec!r}")

    # Allow tonic without octave: default to 4.
    if pitch_part[-1].isdigit() or (len(pitch_part) > 1 and pitch_part[-2:].lstrip("-").isdigit()):
        tonic = mk_note(pitch_part)
    else:
        tonic = mk_note(f"{pitch_part}4")

    intervals = SCALE_INTERVALS.get(mode)
    if intervals is None:
        raise ValueError(f"unknown scale mode: {mode!r}")
    return Scale(tonic=tonic, intervals=intervals, name=mode)


def s(spec: str, mode: str = "major") -> Scale:
    """Short alias for `scale`. Mirrors musicpy's ``S('C major')``."""
    return scale(spec, mode)


def scale_notes(value: Scale) -> tuple[Note, ...]:
    """Enumerate the notes of a scale across one octave starting at the tonic."""
    out = [value.tonic]
    cursor = note_pitch(value.tonic)
    for step_size in value.intervals:
        cursor += step_size
        out.append(
            from_pitch(
                cursor,
                duration=value.tonic.duration,
                velocity=value.tonic.velocity,
                channel=value.tonic.channel,
            ),
        )
    return tuple(out)


def degree(
    value: Scale,
    n: int,
    *,
    size: int = 3,
    duration: float = 0.25,
    velocity: int = 100,
) -> Chord:
    """Return the chord built on the `n`-th degree of a scale.

    `n` is 1-indexed (so ``degree(s, 1)`` is the tonic chord). `size` is
    the number of stacked thirds: 3 → triad, 4 → seventh chord. Notes are
    drawn from `scale_notes` and wrapped to higher octaves once the
    in-octave list is exhausted.
    """
    if n < 1:
        raise ValueError("degree number must be >= 1")
    if size < 1:
        raise ValueError("chord size must be >= 1")

    base = scale_notes(value)  # length = len(intervals) + 1, last == tonic + octave
    pool_pitches = [note_pitch(x) for x in base[:-1]]  # drop duplicated octave
    if not pool_pitches:
        raise ValueError("scale has no notes")

    chord_pitches: list[int] = []
    pool_len = len(pool_pitches)
    for i in range(size):
        # Stacked thirds: indices 0, 2, 4, ... within the scale, with octave wrap.
        idx = (n - 1) + i * 2
        octave_shift, in_pool = divmod(idx, pool_len)
        chord_pitches.append(pool_pitches[in_pool] + 12 * octave_shift)

    derived = [
        from_pitch(p, duration=duration, velocity=velocity, channel=value.tonic.channel)
        for p in chord_pitches
    ]
    return chord(derived, interval=0.0, duration=duration, velocity=velocity)


def prog(
    value: Scale,
    pattern: str | tuple[int, ...],
    *,
    size: int = 3,
    duration: float = 1.0,
    velocity: int = 100,
) -> Chord:
    """Build a chord progression from a numeric pattern.

    ``prog(s, "1,5,6,4")`` expands to triads on degrees I, V, vi, IV. The
    pattern can also be passed as a tuple ``(1, 5, 6, 4)`` for callers
    composing it programmatically. Result is a single Chord whose
    sub-chords are sequenced via `step`.
    """
    from musicky.primitives.chord import step  # local import: avoids cycle at import time

    if isinstance(pattern, str):
        numbers = tuple(int(p) for p in pattern.split(",") if p.strip())
    else:
        numbers = pattern

    return step(
        *(degree(value, n, size=size, duration=duration, velocity=velocity) for n in numbers),
    )


_ = PITCH_CLASSES
