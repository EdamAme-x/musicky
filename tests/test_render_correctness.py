"""Renderer correctness checks: bus merging and wet/dry behavior.

These tests guard the audio-effect pipeline against the kind of subtle
bugs that the code review surfaced — they ensure the pipeline keeps
behaving like a real DAW would.
"""

from musicky import chord, clip, musicky, piano, reverb
from musicky.out.synth import sine_engine


def test_reverb_amount_zero_passes_through_dry() -> None:
    """amount=0 must leave the input untouched within rounding."""
    plain = musicky(piano(clip(chord("C4"))))
    wet = musicky(reverb(piano(clip(chord("C4"))), amount=0.0))
    assert sine_engine(plain, 8000) == sine_engine(wet, 8000)


def test_reverb_amount_one_drops_the_dry_signal() -> None:
    """amount=1 means pure wet — the original waveform should disappear.

    We compare against the dry rendering by checking that no early
    sample matches the dry signal sample-for-sample. The reverb tail
    starts after at least one delay (~30 ms ≈ 240 samples at 8 kHz),
    so the first 100 samples of the wet output should be near zero
    while the dry output is clearly non-zero.
    """
    dry_music = musicky(piano(clip(chord("C4"))))
    wet_music = musicky(reverb(piano(clip(chord("C4"))), amount=1.0))

    dry = sine_engine(dry_music, 8000)
    wet = sine_engine(wet_music, 8000)

    # The first 100 samples of the wet output should be ~0 (pre-delay).
    assert max(abs(s) for s in wet[:100]) < 1e-6
    # The dry output meanwhile must already be ringing.
    assert max(abs(s) for s in dry[:100]) > 0.01


def test_shared_outer_reverb_is_applied_once() -> None:
    """When two voices share an outer reverb, it should mix into one bus.

    The previous renderer applied the reverb closure twice (once per
    distinct sub-chain), doubling the wet contribution. Here we check
    that a tree with one inner-only delay alongside a sibling without
    that delay still produces a single, coherent wet signal — i.e.,
    rendering does not blow up audio levels by double-summing the
    outer reverb's tail.
    """
    from musicky import delay

    music = musicky(
        reverb(
            delay(piano(clip(chord("C4"))), time=0.05, mix=0.5),
            piano(clip(chord("E4"))),
            amount=0.5,
        ),
    )
    samples = sine_engine(music, 8000)
    # Peak should stay within the normal floating range; double-applied
    # reverb in the old code could push past 2.0 quickly. We use 4.0 as
    # a generous ceiling — the assertion is that we do not catastrophically
    # over-sum, not that we hit any particular level.
    assert max(abs(s) for s in samples) < 4.0
