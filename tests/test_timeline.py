from musicky import chord, clip, length, piano, seq
from musicky.core.render import flatten_voices as flatten


def test_length_of_clip_uses_note_durations() -> None:
    c = clip(chord("C4, E4, G4"))  # block chord, 0.25 dur each
    assert length(c) == 0.25


def test_length_of_instrument_is_max_child_end() -> None:
    node = piano(clip(chord("C4"), at=0), clip(chord("E4"), at=2.0))
    assert length(node) == 2.0 + 0.25


def test_seq_places_children_back_to_back() -> None:
    a = piano(clip(chord("C4, E4, G4")))  # length 0.25
    b = piano(clip(chord("D4")))  # length 0.25
    placed = seq(a, b)
    voices = flatten(placed)
    starts = sorted(v.clip.at for v in voices)
    assert starts[0] == 0.0
    assert starts[1] == 0.25
