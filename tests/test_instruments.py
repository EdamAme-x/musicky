"""Tests for the GM instrument library and dynamic sound() factory."""

import pytest

from musicky import (
    GM_PROGRAMS,
    Instrument,
    acoustic_grand,
    bass,
    chord,
    clip,
    distortion_guitar,
    finger_bass,
    guitar,
    nylon_guitar,
    piano,
    sitar,
    sound,
    tr808,
)


def test_gm_programs_table_has_128_entries() -> None:
    # Strict subset check: every distinct program 0-127 should be reachable.
    programs = set(GM_PROGRAMS.values())
    assert programs == set(range(128))


def test_acoustic_grand_program_is_zero() -> None:
    node = acoustic_grand(clip(chord("C4")))
    assert isinstance(node, Instrument)
    assert node.program == 0


def test_distortion_guitar_program() -> None:
    assert distortion_guitar(clip(chord("E2"))).program == 30


def test_sitar_program() -> None:
    assert sitar(clip(chord("C4"))).program == 104


def test_short_aliases_match_canonical() -> None:
    """`piano` should be the same maker as `acoustic_grand`."""
    assert piano is acoustic_grand
    assert guitar is nylon_guitar
    assert bass is finger_bass


def test_sound_by_name() -> None:
    node = sound("harpsichord", clip(chord("C4")))
    assert node.program == 6


def test_sound_by_program_number() -> None:
    node = sound(40, clip(chord("C4")))
    assert node.program == 40
    assert node.name == "program_40"


def test_sound_unknown_name_raises() -> None:
    with pytest.raises(ValueError, match="unknown instrument name"):
        sound("not_a_thing", clip(chord("C4")))


def test_sound_program_out_of_range() -> None:
    with pytest.raises(ValueError, match="GM program out of range"):
        sound(200, clip(chord("C4")))


def test_tr808_routes_to_drums_with_bank() -> None:
    """Drum kits keep the literal name 'drums' for routing, but carry a bank."""
    node = tr808(clip(chord("C2")))
    assert node.name == "drums"
    assert node.bank == 25
