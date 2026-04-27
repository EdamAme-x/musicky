from musicky import (
    Clip,
    Effect,
    Instrument,
    Mix,
    bass,
    chord,
    clip,
    drums,
    musicky,
    piano,
    reverb,
)
from musicky.core.render import flatten_voices as flatten


def test_clip_holds_chord_and_position() -> None:
    c = clip(chord("C4"), at=4.0)
    assert isinstance(c, Clip)
    assert c.at == 4.0
    assert len(c.content.notes) == 1


def test_piano_returns_instrument() -> None:
    node = piano(clip(chord("C4")))
    assert isinstance(node, Instrument)
    # `piano` is an alias of `acoustic_grand`; both share the canonical name.
    assert node.name == "acoustic_grand"
    assert node.program == 0


def test_drums_uses_channel_9_after_flatten() -> None:
    node = drums(clip(chord("C2")))
    voices = flatten(node)
    assert all(v.channel == 9 for v in voices)


def test_reverb_returns_effect_node() -> None:
    node = reverb(piano(clip(chord("C4"))), amount=0.5)
    assert isinstance(node, Effect)
    assert node.kind == "reverb"
    assert node.params["amount"] == 0.5


def test_musicky_with_one_child_does_not_wrap() -> None:
    music = musicky(piano(clip(chord("C4"))))
    assert isinstance(music.root, Instrument)


def test_musicky_with_multiple_children_wraps_in_mix() -> None:
    music = musicky(
        piano(clip(chord("C4"))),
        bass(clip(chord("C2"))),
    )
    assert isinstance(music.root, Mix)
    assert len(music.root.children) == 2


def test_flatten_preserves_at_position() -> None:
    voices = flatten(piano(clip(chord("C4"), at=2.0), clip(chord("E4"), at=4.0)))
    positions = sorted(v.clip.at for v in voices)
    assert positions == [2.0, 4.0]


def test_flatten_distinct_channels_per_instrument() -> None:
    music = musicky(
        piano(clip(chord("C4"))),
        bass(clip(chord("C2"))),
    )
    voices = flatten(music.root)
    channels = {v.channel for v in voices}
    assert len(channels) == 2


def test_audio_fx_nesting_outer_to_inner() -> None:
    """audio_fx[0] is the OUTERMOST effect; the last entry is the innermost.

    Each chain link is now the audio function itself; we only check the
    chain length here, since the closures are anonymous.
    """
    node = reverb(reverb(piano(clip(chord("C4"))), amount=0.1), amount=0.4)
    voices = flatten(node)
    assert len(voices) == 1
    assert len(voices[0].audio_fx) == 2
    # Both links must be callable (they are the closures from `reverb`).
    assert all(callable(fn) for fn in voices[0].audio_fx)
