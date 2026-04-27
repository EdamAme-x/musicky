"""Tests for symbolic and audio effect propagation through the renderer."""

from musicky import (
    chord,
    clip,
    humanize,
    musicky,
    piano,
    quantize,
    reverb,
    transpose,
)
from musicky.core.render import flatten_voices as flatten


def test_master_is_pass_through() -> None:
    """`master(...)` should not affect the audio_fx chain."""
    from musicky import master

    plain = piano(clip(chord("C4")))
    wrapped = master(piano(clip(chord("C4"))))
    a_voices = flatten(plain)
    b_voices = flatten(wrapped)
    assert a_voices[0].audio_fx == b_voices[0].audio_fx == ()


def test_transpose_is_symbolic_and_shifts_pitch() -> None:
    node = transpose(piano(clip(chord("C4"))), semitones=2)
    voices = flatten(node)
    note = voices[0].clip.content.notes[0]
    assert note.name == "D"


def test_humanize_is_seeded_and_reproducible() -> None:
    a = flatten(humanize(piano(clip(chord("C4, E4, G4"))), seed=42))
    b = flatten(humanize(piano(clip(chord("C4, E4, G4"))), seed=42))
    assert a[0].clip.content == b[0].clip.content


def test_quantize_snaps_intervals_to_grid() -> None:
    weird = chord("C4, E4, G4", interval=0.18)
    grid = 0.25
    voices = flatten(quantize(piano(clip(weird)), grid=grid))
    for iv in voices[0].clip.content.intervals:
        assert iv % grid == 0.0


def test_reverb_appears_in_audio_fx_chain() -> None:
    voices = flatten(reverb(piano(clip(chord("C4"))), amount=0.5))
    # The chain stores the audio callable directly; we just check it is there.
    assert len(voices[0].audio_fx) == 1
    assert callable(voices[0].audio_fx[0])


def test_audio_fx_render_produces_sound() -> None:
    """A reverb-wrapped piece should still produce non-empty audio."""
    music = musicky(reverb(piano(clip(chord("C4, E4, G4"))), amount=0.3), bpm=120)
    from musicky.out.synth import sine_engine

    samples = sine_engine(music, 8000)
    assert any(abs(s) > 0.01 for s in samples)


def test_user_defined_audio_effect_runs() -> None:
    """Users can build a brand-new effect with no registry plumbing.

    We construct a custom `Effect` whose `apply` is a closure that flips
    the sign of every sample. The renderer should pick this up directly
    via `effect.apply`, with no changes to the library.
    """
    from musicky import Effect
    from musicky.out.synth import sine_engine

    def invert(*children: object) -> Effect:
        def apply(samples: list[float], _sr: int, _bpm: float) -> list[float]:
            return [-s for s in samples]

        return Effect(
            kind="invert",
            params={},
            children=tuple(children),  # type: ignore[arg-type]
            apply=apply,
        )

    plain_music = musicky(piano(clip(chord("C4"))), bpm=120)
    inverted_music = musicky(invert(piano(clip(chord("C4")))), bpm=120)

    plain = sine_engine(plain_music, 8000)
    inverted = sine_engine(inverted_music, 8000)
    # The inverted run should be the negation of the plain one (modulo
    # the ring-out tail being silent on both).
    nonzero = [(p, q) for p, q in zip(plain, inverted, strict=True) if abs(p) > 0.001]
    assert nonzero  # at least some non-trivial samples
    assert all(abs(p + q) < 1e-9 for p, q in nonzero)


def test_symbolic_effects_apply_innermost_first() -> None:
    """Inner symbolic effect should run first, outer last.

    With ``transpose(quantize(piano(clip)), semitones=12)``, quantize
    runs before transpose conceptually, but transpose is purely
    additive on pitch so we test the order via two stacked
    chord_transforms whose order matters: a `humanize` set to a fixed
    seed followed by a velocity-doubling effect should NOT match the
    reverse order if the order is honored.
    """
    from dataclasses import replace as _replace

    from musicky import Effect
    from musicky.core.render import flatten_voices as flatten
    from musicky.primitives.chord import Chord

    def boost(*children: object) -> Effect:
        def transform(c: Chord) -> Chord:
            return Chord(
                notes=tuple(_replace(n, velocity=min(127, n.velocity + 20)) for n in c.notes),
                intervals=c.intervals,
            )

        return Effect(
            kind="boost",
            params={},
            children=tuple(children),  # type: ignore[arg-type]
            chord_transform=transform,
        )

    def cap(*children: object) -> Effect:
        def transform(c: Chord) -> Chord:
            return Chord(
                notes=tuple(_replace(n, velocity=min(80, n.velocity)) for n in c.notes),
                intervals=c.intervals,
            )

        return Effect(
            kind="cap",
            params={},
            children=tuple(children),  # type: ignore[arg-type]
            chord_transform=transform,
        )

    # boost(cap(... v=100)) -> cap(100)=80 -> boost(80)=100  (final v=100)
    inner_cap_then_boost = flatten(boost(cap(piano(clip(chord("C4", velocity=100))))))
    assert inner_cap_then_boost[0].clip.content.notes[0].velocity == 100

    # cap(boost(... v=100)) -> boost(100)=120(clamped 127) -> cap(127)=80 (final v=80)
    inner_boost_then_cap = flatten(cap(boost(piano(clip(chord("C4", velocity=100))))))
    assert inner_boost_then_cap[0].clip.content.notes[0].velocity == 80


def test_user_defined_symbolic_effect_runs() -> None:
    """A user-supplied chord_transform also runs without registration."""
    from musicky import Effect
    from musicky.core.render import flatten_voices as flatten
    from musicky.primitives.chord import Chord

    def double_velocity(*children: object) -> Effect:
        def transform(c: Chord) -> Chord:
            from dataclasses import replace as _replace

            return Chord(
                notes=tuple(_replace(n, velocity=min(127, n.velocity * 2)) for n in c.notes),
                intervals=c.intervals,
            )

        return Effect(
            kind="double_velocity",
            params={},
            children=tuple(children),  # type: ignore[arg-type]
            chord_transform=transform,
        )

    voices = flatten(double_velocity(piano(clip(chord("C4, E4", velocity=50)))))
    assert all(n.velocity == 100 for n in voices[0].clip.content.notes)
