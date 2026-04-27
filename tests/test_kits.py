"""Tests for drum-kit constructors and Bank Select MIDI emission."""

from musicky import (
    chord,
    clip,
    drums,
    house_kit,
    jazz_kit,
    lofi_kit,
    musicky,
    standard_kit,
    tr808,
    tr909,
)
from musicky.out.play.midi import render_to_bytes


def test_kits_route_to_drums_channel() -> None:
    """Every kit produces an Instrument whose name is 'drums'."""
    for kit in (drums, tr808, tr909, jazz_kit, lofi_kit, house_kit, standard_kit):
        node = kit(clip(chord("C2")))
        assert node.name == "drums"


def test_kit_banks_differ() -> None:
    assert drums(clip(chord("C2"))).bank == 0
    assert tr808(clip(chord("C2"))).bank == 25
    assert tr909(clip(chord("C2"))).bank == 26
    assert jazz_kit(clip(chord("C2"))).bank == 32
    assert lofi_kit(clip(chord("C2"))).bank == 49


def test_midi_emits_bank_select_for_non_default_kit() -> None:
    """Bank != 0 must produce CC 0 (MSB) and CC 32 (LSB) on the channel."""
    music = musicky(tr808(clip(chord("C2"))))
    data = render_to_bytes(music)
    # Bank Select MSB on channel 9 is byte 0xB9, controller 0x00.
    assert b"\xb9\x00\x00" in data  # MSB byte
    assert b"\xb9\x20\x19" in data  # LSB = 25 = 0x19


def test_midi_default_kit_does_not_emit_bank_select() -> None:
    """Default kit (bank 0) should not emit Bank Select on channel 9."""
    music = musicky(drums(clip(chord("C2"))))
    data = render_to_bytes(music)
    # No Bank Select MSB on channel 9 with non-zero value
    assert b"\xb9\x00\x00" not in data
