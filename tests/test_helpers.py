"""Tests for the small composition helpers added during dogfooding."""

from musicky import (
    at,
    chord,
    clip,
    length,
    musicky,
    octave,
    piano,
    pitch,
    seq,
    shift,
    tx,
)
from musicky.core.render import flatten_voices as flatten


def test_shift_moves_clip_in_time() -> None:
    node = shift(piano(clip(chord("C4"), at=0.0)), by=4.0)
    voices = flatten(node)
    assert voices[0].clip.at == 4.0


def test_shift_recurses_through_effects_and_mix() -> None:
    from musicky import reverb
    from musicky.core.node import Mix

    inner = Mix(children=(piano(clip(chord("C4"), at=0.0)),))
    outer = reverb(inner, amount=0.3)
    moved = shift(outer, by=2.0)
    voices = flatten(moved)
    assert all(v.clip.at == 2.0 for v in voices)


def test_at_places_node_at_absolute_position() -> None:
    """`at(n, node)` aligns the earliest clip with beat n."""
    src = piano(clip(chord("C4"), at=1.0), clip(chord("E4"), at=3.0))
    placed = at(10.0, src)
    voices = sorted(flatten(placed), key=lambda v: v.clip.at)
    assert voices[0].clip.at == 10.0
    # Relative spacing is preserved.
    assert voices[1].clip.at == 12.0


def test_seq_uses_length_to_chain() -> None:
    """seq + length must agree so cascaded sections do not overlap."""
    a = piano(clip(chord("C4, E4, G4")))  # length 0.25
    b = piano(clip(chord("D4")))  # length 0.25
    placed = seq(a, b)
    voices = sorted(flatten(placed), key=lambda v: v.clip.at)
    assert voices[0].clip.at == 0.0
    assert voices[-1].clip.at == length(a)


def test_tx_shifts_pitches_by_semitones() -> None:
    raised = tx(chord("C4, E4, G4"), 7)
    assert [pitch(n) for n in raised.notes] == [67, 71, 74]


def test_tx_clamps_to_midi_range() -> None:
    raised = tx(chord("G9"), 12)  # G9 is already at MIDI 127
    assert pitch(raised.notes[0]) == 127


def test_octave_is_tx_by_twelve() -> None:
    assert octave(chord("C4, E4, G4"), 1) == tx(chord("C4, E4, G4"), 12)
    assert octave(chord("C4, E4, G4"), -1) == tx(chord("C4, E4, G4"), -12)


def test_musicky_uses_helpers_together() -> None:
    """A small piece using shift + tx + seq should render without errors."""
    verse = piano(clip(chord("C4, E4, G4")))
    chorus = piano(clip(tx(chord("C4, E4, G4"), 5)))  # up a fourth
    full = seq(verse, chorus, shift(verse, by=0.0))
    music = musicky(full, bpm=120)
    voices = flatten(music.root)
    assert len(voices) == 3
    # All on a single piano channel since we reused the same helper.
    assert {v.channel for v in voices} == {0}
