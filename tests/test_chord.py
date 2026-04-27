from musicky import chord, inv, loop, mix, n, notes, pitch, step


def test_chord_from_string() -> None:
    c = chord("C5, E5, G5")
    pitches = [pitch(x) for x in notes(c)]
    assert pitches == [72, 76, 79]


def test_chord_from_iterable_of_notes() -> None:
    c = chord([n("C5"), n("E5"), n("G5")])
    assert len(notes(c)) == 3


def test_chord_from_midi_integers() -> None:
    """MIDI numbers should produce the same chord as the equivalent strings."""
    by_int = chord([60, 64, 67])
    by_str = chord("C4, E4, G4")
    assert pitches(by_int) == pitches(by_str)


def test_chord_mixes_strings_and_integers() -> None:
    mixed = chord(["C4", 64, "G4"])
    assert pitches(mixed) == [60, 64, 67]


def pitches(c: object) -> list[int]:
    """Helper: pull MIDI pitches out of a Chord for comparison."""
    return [pitch(n) for n in notes(c)]  # type: ignore[arg-type]


def test_step_sequences_chords_in_time() -> None:
    a = chord("C5")
    b = chord("D5")
    seq = step(a, b)
    assert len(seq.notes) == 2
    # Bridge interval = duration of the previous chord's last note.
    assert seq.intervals == (a.notes[-1].duration,)


def test_mix_overlays_chords() -> None:
    a = chord("C5, E5")
    b = chord("G5, B5")
    overlaid = mix(a, b)
    assert len(overlaid.notes) == 4
    # A 0.0 join means notes start at the same time.
    assert overlaid.intervals == (0.0, 0.0, 0.0)


def test_loop_repeats() -> None:
    looped = loop(chord("C5"), 4)
    assert len(looped.notes) == 4


def test_loop_zero_returns_empty() -> None:
    looped = loop(chord("C5"), 0)
    assert looped.notes == ()


def test_inversion_lifts_lowest_by_octave() -> None:
    base = chord("C5, E5, G5")
    inverted = inv(base, 1)
    assert pitch(inverted.notes[-1]) == pitch(base.notes[0]) + 12
    assert inverted.notes[0] == base.notes[1]


def test_inversion_negative_drops_highest() -> None:
    base = chord("C5, E5, G5")
    inverted = inv(base, -1)
    assert pitch(inverted.notes[0]) == pitch(base.notes[-1]) - 12
