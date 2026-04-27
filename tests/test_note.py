import pytest

from musicky import from_pitch, is_enharmonic, n, note, pitch


def test_note_parses_sharps_and_octaves() -> None:
    a = note("C5")
    assert a.name == "C"
    assert a.octave == 5
    assert pitch(a) == 72  # C5 = MIDI 72


def test_note_normalizes_flats_to_sharps() -> None:
    assert is_enharmonic(note("Eb4"), note("D#4"))


def test_short_alias_n() -> None:
    assert n("C5") == note("C5")


def test_negative_octave_round_trips() -> None:
    a = note("C-1")
    assert pitch(a) == 0
    assert from_pitch(0).name == "C"
    assert from_pitch(0).octave == -1


def test_invalid_spec_raises() -> None:
    with pytest.raises(ValueError):
        note("H4")
    with pytest.raises(ValueError):
        note("C")
    with pytest.raises(ValueError):
        note("Cx5")


def test_from_pitch_out_of_range() -> None:
    with pytest.raises(ValueError):
        from_pitch(128)


def test_note_accepts_midi_int() -> None:
    """note(60) should equal note('C4')."""
    assert pitch(note(60)) == 60
    assert note(60) == note("C4")


def test_note_int_passes_through_kwargs() -> None:
    n_int = note(60, duration=0.5, velocity=80)
    n_str = note("C4", duration=0.5, velocity=80)
    assert n_int == n_str


def test_note_int_out_of_range() -> None:
    with pytest.raises(ValueError):
        note(200)
