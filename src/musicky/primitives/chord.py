"""Chord primitive: an ordered set of notes with timing relationships.

A `Chord` is the workhorse container for any non-trivial musical material.
It carries a tuple of `Note` values plus an `intervals` tuple describing the
gap (in beats) between successive note onsets. With ``interval == 0`` the
adjacent notes start simultaneously (true chord), with ``interval > 0`` they
form a melodic line.

Pure functions in this module take chords and return new chords; nothing is
mutated. Combinators include `step` (sequence in time), `mix` (overlay) and
`loop` (repetition). `inv` performs musical inversion.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, replace

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
    "Chord",
    "chord",
    "inv",
    "loop",
    "mix",
    "notes",
    "octave",
    "step",
    "tx",
]


@dataclass(frozen=True, slots=True)
class Chord:
    """An immutable ordered collection of notes.

    `intervals[i]` is the time gap (in beats) between ``notes[i]`` and
    ``notes[i+1]`` onsets. Length always equals ``len(notes) - 1`` (or 0 for
    an empty chord). Storing intervals rather than absolute onsets keeps
    sequencing (`step`) cheap: just concatenate.
    """

    notes: tuple[Note, ...]
    intervals: tuple[float, ...]


def chord(
    spec: str | Iterable[Note | str | int],
    *,
    interval: float = 0.0,
    duration: float = 0.25,
    velocity: int = 100,
) -> Chord:
    """Build a Chord.

    `spec` may be:
      * a comma-separated string ``"C5, E5, G5"``
      * an iterable of `Note` objects
      * an iterable of pitch strings ``["C5", "E5", "G5"]``
      * an iterable of MIDI pitch numbers ``[72, 76, 79]`` (for code
        that computes pitches at runtime)

    `interval` is applied uniformly between successive notes. Use 0 for
    a block chord, or a positive value for an arpeggio / melodic line.
    """
    parsed: list[Note] = []
    if isinstance(spec, str):
        # Split on comma; ignore stray whitespace. Empty fragments raise.
        for piece in (p.strip() for p in spec.split(",") if p.strip()):
            parsed.append(mk_note(piece, duration=duration, velocity=velocity))
    else:
        for item in spec:
            if isinstance(item, Note):
                parsed.append(item)
            else:
                # Both str and int route through `note()`, which accepts each.
                parsed.append(mk_note(item, duration=duration, velocity=velocity))

    intervals = tuple([interval] * max(0, len(parsed) - 1))
    return Chord(notes=tuple(parsed), intervals=intervals)


def notes(value: Chord) -> tuple[Note, ...]:
    """Return the notes of a chord. Provided for symmetry with `pitch`."""
    return value.notes


def step(*chords: Chord) -> Chord:
    """Place chords one after another in time.

    The bridging interval between two chords is the duration of the last
    note of the left-hand chord. This is the intuitive default: "play A,
    then play B once A has finished its final note." Callers wanting a
    different gap can insert a rest or splice intervals manually.
    """
    if not chords:
        return Chord(notes=(), intervals=())

    out_notes: list[Note] = []
    out_intervals: list[float] = []
    for i, c in enumerate(chords):
        if i > 0:
            # Bridge to this chord using the previous chord's last note duration.
            prev = chords[i - 1]
            bridge = prev.notes[-1].duration if prev.notes else 0.0
            out_intervals.append(bridge)
        out_notes.extend(c.notes)
        out_intervals.extend(c.intervals)

    # When the final chord has no internal intervals, drop the trailing
    # bridge slot we may have appended above.
    if len(out_intervals) > max(0, len(out_notes) - 1):
        out_intervals = out_intervals[: len(out_notes) - 1]

    return Chord(notes=tuple(out_notes), intervals=tuple(out_intervals))


def mix(*chords: Chord) -> Chord:
    """Overlay chords so that all of them start at the same time.

    The result starts every input chord at offset 0 and lets each one
    proceed under its own intervals. This implementation is intentionally
    simple: it concatenates the note tuples and inserts ``0.0`` between
    chords so adjacent groups onset together. Use `step` for sequencing.
    """
    if not chords:
        return Chord(notes=(), intervals=())

    out_notes: list[Note] = []
    out_intervals: list[float] = []
    for i, c in enumerate(chords):
        if i > 0:
            out_intervals.append(0.0)  # next group starts at the same time
        out_notes.extend(c.notes)
        out_intervals.extend(c.intervals)

    if len(out_intervals) > max(0, len(out_notes) - 1):
        out_intervals = out_intervals[: len(out_notes) - 1]

    return Chord(notes=tuple(out_notes), intervals=tuple(out_intervals))


def loop(value: Chord, times: int) -> Chord:
    """Repeat a chord `times` times sequentially.

    Equivalent to ``step(value, value, ..., value)`` but spelled to match
    the user's intent. ``times <= 0`` returns an empty chord.
    """
    if times <= 0:
        return Chord(notes=(), intervals=())
    return step(*([value] * times))


def inv(value: Chord, n: int = 1) -> Chord:
    """Invert a chord `n` times.

    Each inversion lifts the lowest remaining note by one octave so it
    becomes the highest. Negative `n` performs the opposite move (drop the
    highest by an octave). The intervals tuple is preserved because we
    only swap pitch classes/octaves, not timing.

    MIDI pitches are clamped to the legal range 0-127. A chord whose top
    note is already at the ceiling (G9) can still be inverted; the
    raised note simply stays at 127. Likewise for negative inversions
    bumping into 0.
    """
    if not value.notes:
        return value

    lifted = list(value.notes)
    for _ in range(abs(n)):
        if n > 0:
            head, *rest = lifted
            shifted = from_pitch(
                max(0, min(127, note_pitch(head) + 12)),
                duration=head.duration,
                velocity=head.velocity,
                channel=head.channel,
            )
            lifted = [*rest, shifted]
        else:
            *rest, tail = lifted
            shifted = from_pitch(
                max(0, min(127, note_pitch(tail) - 12)),
                duration=tail.duration,
                velocity=tail.velocity,
                channel=tail.channel,
            )
            lifted = [shifted, *rest]

    return replace(value, notes=tuple(lifted))


def tx(value: Chord, semitones: int) -> Chord:
    """Transpose every note in `value` by `semitones` half-steps.

    Pitches are clamped to the legal MIDI range so a chord near the
    ceiling does not raise; the saturating notes simply stop rising.
    """
    if semitones == 0:
        return value
    new_notes = tuple(
        from_pitch(
            max(0, min(127, note_pitch(n) + semitones)),
            duration=n.duration,
            velocity=n.velocity,
            channel=n.channel,
        )
        for n in value.notes
    )
    return replace(value, notes=new_notes)


def octave(value: Chord, n: int = 1) -> Chord:
    """Move every note `n` octaves (positive = up, negative = down)."""
    return tx(value, 12 * n)


# Re-export `replace` is handled by the package __init__; we only use the
# pitch-class tuple here to keep the import surface tight.
_ = PITCH_CLASSES
