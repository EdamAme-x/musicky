from musicky import degree, prog, s, scale, scale_notes


def test_c_major_scale_notes() -> None:
    notes = [x.name for x in scale_notes(scale("C major"))]
    assert notes == ["C", "D", "E", "F", "G", "A", "B", "C"]


def test_a_minor_scale_notes() -> None:
    notes = [x.name for x in scale_notes(s("A minor"))]
    assert notes == ["A", "B", "C", "D", "E", "F", "G", "A"]


def test_degree_triads() -> None:
    sc = scale("C major")
    one = degree(sc, 1)
    five = degree(sc, 5)
    assert [x.name for x in one.notes] == ["C", "E", "G"]
    assert [x.name for x in five.notes] == ["G", "B", "D"]


def test_degree_seventh() -> None:
    seventh = degree(scale("C major"), 1, size=4)
    assert [x.name for x in seventh.notes] == ["C", "E", "G", "B"]


def test_prog_expands_pattern() -> None:
    prog_chord = prog(scale("C major"), "1,5,6,4")
    assert len(prog_chord.notes) == 12  # 4 triads


def test_scale_high_octave_anchor() -> None:
    """A scale anchored high in the keyboard still enumerates correctly."""
    notes = [x.name for x in scale_notes(scale("C8 major"))]
    assert notes == ["C", "D", "E", "F", "G", "A", "B", "C"]


def test_scale_low_octave_anchor() -> None:
    notes = [x.name for x in scale_notes(scale("C0 major"))]
    assert notes == ["C", "D", "E", "F", "G", "A", "B", "C"]


def test_scale_negative_octave() -> None:
    notes = [x.name for x in scale_notes(scale("C-1 major"))]
    assert notes == ["C", "D", "E", "F", "G", "A", "B", "C"]
