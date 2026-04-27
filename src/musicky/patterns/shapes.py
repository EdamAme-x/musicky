"""Shape helpers: turn chord progressions into common musical patterns."""

from __future__ import annotations

from collections.abc import Callable, Iterable

from musicky.core.node import Clip, Node, clip
from musicky.core.timeline import seq
from musicky.primitives.chord import Chord, chord, tx
from musicky.primitives.note import Note
from musicky.primitives.note import pitch as note_pitch

__all__ = ["arp", "hits", "hold", "move", "phrase", "pump"]


def arp(progression: Iterable[Chord], *, interval: float = 0.125) -> Chord:
    """Spread each chord in `progression` into a fast melodic arpeggio.

    The result is a single Chord whose notes are every input chord's
    notes laid out in series with `interval` between them. Pass it to a
    lead instrument like ``saw_lead(clip(arp(...)))``.
    """
    notes: list[Note] = []
    intervals: list[float] = []
    first = True
    for c in progression:
        for n in c.notes:
            notes.append(n)
            if not first:
                intervals.append(interval)
            first = False
        # Always step `interval` between consecutive notes, including
        # across chord boundaries.
    # `intervals` length = len(notes) - 1 by construction.
    return Chord(notes=tuple(notes), intervals=tuple(intervals))


def hold(progression: Iterable[Chord], *, duration: float = 4.0) -> Chord:
    """Lay each chord in `progression` end-to-end, each held for `duration` beats.

    Useful for pads. Each chord's notes get their `duration` set to the
    given value, and chord-to-chord transitions are spaced by the same.
    """
    progression = list(progression)
    notes: list[Note] = []
    intervals: list[float] = []
    for i, c in enumerate(progression):
        # Re-stamp every note's duration so the pad rings for the full bar.
        from dataclasses import replace as _replace

        for n in c.notes:
            notes.append(_replace(n, duration=duration))
        # Inside one chord notes start at the same time; between chords
        # we wait `duration` beats. Pad with 0.0s for in-chord notes,
        # then `duration` for the bridge to the next chord.
        if c.notes:
            intervals.extend([0.0] * (len(c.notes) - 1))
        if i < len(progression) - 1:
            intervals.append(duration)
    return Chord(notes=tuple(notes), intervals=tuple(intervals))


def pump(
    progression: Iterable[Chord],
    *,
    sub: int = 8,
    octaves_below: int = 1,
    duration: float | None = None,
    velocity: int = 110,
) -> Chord:
    """Build an eighth-note (or other subdivision) bassline on chord roots.

    Each chord contributes `sub` repeats of its lowest pitch, dropped by
    `octaves_below` octaves. `duration` defaults to slightly under the
    subdivision so notes do not bleed into each other. The result is a
    melodic Chord ready for a bass instrument.
    """
    spacing = 4.0 / sub  # 4 beats per bar / sub = beat length per hit
    if duration is None:
        duration = spacing * 0.9

    midi_pitches: list[int] = []
    for c in progression:
        if not c.notes:
            continue
        root = min(note_pitch(n) for n in c.notes) - 12 * octaves_below
        midi_pitches.extend([max(0, min(127, root))] * sub)

    return chord(midi_pitches, interval=spacing, duration=duration, velocity=velocity)


def hits(
    fn: Callable[..., Clip],
    *positions: float,
    velocity: int = 100,
    duration: float = 0.25,
) -> list[Clip]:
    """Build a list of drum-element clips at the given beat positions.

    `fn` is one of the helpers from `musicky.sounds.drumkit` (kick,
    snare, closed_hat, ...). All positional args after `fn` are beat
    positions; keyword args set defaults for every produced clip.
    """
    return [fn(at=p, velocity=velocity, duration=duration) for p in positions]


def move(clips: Iterable[Clip], by: float) -> list[Clip]:
    """Shift every clip in the iterable by `by` beats.

    Convenient for placing a groove (a list of Clips) at a section
    offset before passing them to a drum kit.
    """
    from dataclasses import replace as _replace

    return [_replace(c, at=c.at + by) for c in clips]


def phrase(
    instrument: Callable[..., Node],
    chords: Iterable[Chord],
    *,
    transpose: int = 0,
) -> Node:
    """Play `chords` through `instrument`, one after another in time.

    Equivalent to ``seq(instrument(clip(c)) for c in chords)`` with an
    optional `transpose` (in semitones) applied to every chord first.
    Lets a verse/chorus phrase fit on a single line:

        verse  = phrase(square_lead, [HOOK_LOW, HOOK_HIGH, HOOK_LOW])
        chorus = phrase(square_lead, [HOOK_HIGH, HOOK_LIFT], transpose=2)
    """
    materialized = list(chords)
    if transpose:
        materialized = [tx(c, transpose) for c in materialized]
    return seq(*[instrument(clip(c)) for c in materialized])
