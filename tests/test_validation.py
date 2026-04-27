"""Boundary-case tests added during the post-review hardening pass.

Every test here corresponds to a specific defect that the code reviewer
flagged in the audit. Keeping them as a separate module makes the
intent obvious and lets future contributors find the regression suite
in one place.
"""

import pytest

from musicky import (
    chord,
    clip,
    inv,
    musicky,
    piano,
    pitch,
    quantize,
    sound,
    tr808,
)
from musicky.out.play.midi import render_to_bytes


def test_low_bpm_does_not_overflow_smf_tempo() -> None:
    """SMF tempo bytes are 3 bytes wide; a 1 BPM piece must clamp, not crash."""
    music = musicky(piano(clip(chord("C4"))), bpm=1.0)
    data = render_to_bytes(music)
    # Should still produce a valid header.
    assert data.startswith(b"MThd")


def test_zero_bpm_rejected() -> None:
    music = musicky(piano(clip(chord("C4"))), bpm=0.0)
    with pytest.raises(ValueError, match="bpm must be positive"):
        render_to_bytes(music)


def test_negative_bpm_rejected() -> None:
    music = musicky(piano(clip(chord("C4"))), bpm=-60.0)
    with pytest.raises(ValueError, match="bpm must be positive"):
        render_to_bytes(music)


def test_too_many_distinct_instruments_raises() -> None:
    """16 distinct melodic instruments should error out (only 15 channels free)."""
    from musicky import sound
    from musicky.core.node import Mix
    from musicky.core.render import flatten_voices as flatten

    # Use 16 distinct GM programs so each one demands its own channel.
    voices = [sound(i, clip(chord(f"C{(i % 7) + 1}"))) for i in range(16)]
    music = musicky(Mix(children=tuple(voices)))
    with pytest.raises(ValueError, match="too many distinct instruments"):
        flatten(music.root)


def test_same_instrument_repeated_shares_channel() -> None:
    """Reusing the same instrument helper across clips reuses the channel."""
    from musicky.core.node import Mix
    from musicky.core.render import flatten_voices as flatten

    music = musicky(
        Mix(children=tuple(piano(clip(chord(f"C{i}"))) for i in range(8))),
    )
    voices = flatten(music.root)
    channels = {v.channel for v in voices}
    # All eight piano clips collapse onto one MIDI channel.
    assert channels == {0}


def test_quantize_grid_zero_rejected() -> None:
    with pytest.raises(ValueError, match="grid must be positive"):
        quantize(piano(clip(chord("C4"))), grid=0)


def test_quantize_grid_negative_rejected() -> None:
    with pytest.raises(ValueError, match="grid must be positive"):
        quantize(piano(clip(chord("C4"))), grid=-0.5)


def test_inv_near_top_of_midi_range_does_not_crash() -> None:
    """A near-ceiling chord inverted up must not raise.

    Before the fix, ``from_pitch(128)`` would propagate up out of inv().
    """
    top = chord("F9, G9")  # both within 0-127 (G9 = 127)
    inverted = inv(top, 1)
    # Lifted note is clamped at the MIDI ceiling.
    assert pitch(inverted.notes[-1]) == 127


def test_inv_at_bottom_of_midi_range_does_not_crash() -> None:
    """A near-floor chord inverted down must not raise."""
    bottom = chord("C-1, D-1")
    inverted = inv(bottom, -1)
    # Lowered note is clamped at MIDI 0.
    assert pitch(inverted.notes[0]) == 0


def test_tr808_routes_via_bank_25() -> None:
    """Drum-kit bank actually flows through the MIDI bytes."""
    music = musicky(tr808(clip(chord("C2"))))
    data = render_to_bytes(music)
    # Bank Select MSB = 0, LSB = 25 on channel 9 (status byte 0xB9).
    assert b"\xb9\x00\x00" in data
    assert b"\xb9\x20\x19" in data  # 0x19 = 25


def test_sound_short_alias_resolves_to_correct_program() -> None:
    """`sound("piano")` must hit GM 0 even now that the lookup is hand-built."""
    node = sound("piano", clip(chord("C4")))
    assert node.program == 0


def test_sound_alias_table_has_full_gm_set() -> None:
    """The hand-built GM_PROGRAMS table covers all 128 programs at minimum."""
    from musicky import GM_PROGRAMS

    programs = set(GM_PROGRAMS.values())
    assert programs == set(range(128))
