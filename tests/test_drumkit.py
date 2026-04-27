"""Tests for individual drum-element helpers."""

import pytest

from musicky import (
    Clip,
    clap,
    closed_hat,
    crash,
    drums,
    hit,
    kick,
    musicky,
    open_hat,
    ride,
    seq,
    snare,
)
from musicky.out.play.midi import render_to_bytes


def test_kick_returns_a_clip() -> None:
    c = kick(at=0)
    assert isinstance(c, Clip)
    assert c.at == 0
    assert len(c.content.notes) == 1


def test_kick_pitch_is_36() -> None:
    """GM Drum Map: Bass Drum 1 is pitch 36."""
    c = kick()
    note = c.content.notes[0]
    # MIDI pitch = (octave + 1) * 12 + semitone
    pitch_classes = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
    midi = (note.octave + 1) * 12 + pitch_classes.index(note.name)
    assert midi == 36


def test_snare_pitch_is_38() -> None:
    note = snare().content.notes[0]
    pitch_classes = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
    midi = (note.octave + 1) * 12 + pitch_classes.index(note.name)
    assert midi == 38


def test_drum_helpers_use_channel_9() -> None:
    for fn in (kick, snare, closed_hat, open_hat, crash, ride, clap):
        note = fn().content.notes[0]
        assert note.channel == 9


def test_at_and_velocity_propagate() -> None:
    c = kick(at=4.0, velocity=80)
    assert c.at == 4.0
    assert c.content.notes[0].velocity == 80


def test_seq_of_drum_helpers_places_them_in_time() -> None:
    pattern = drums(seq(kick(), snare(), kick(), snare()))
    music = musicky(pattern)
    data = render_to_bytes(music)
    # Just check that the MIDI was produced and contains drum note-ons.
    assert data.startswith(b"MThd")
    # Note-on on channel 9 = 0x99
    assert b"\x99\x24" in data  # kick (pitch 36 = 0x24)
    assert b"\x99\x26" in data  # snare (pitch 38 = 0x26)


def test_hit_accepts_arbitrary_pitch() -> None:
    c = hit(pitch=42, at=1.0)  # Closed Hi-Hat
    assert c.at == 1.0
    note = c.content.notes[0]
    assert note.channel == 9


def test_hit_rejects_out_of_range_pitch() -> None:
    with pytest.raises(ValueError, match="drum pitch out of range"):
        hit(pitch=200)
