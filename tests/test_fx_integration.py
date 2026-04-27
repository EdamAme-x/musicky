"""Integration tests: every audio effect must produce non-trivial output.

These exist as a regression net so a future refactor of the renderer or
of `effects.fx` cannot silently break a single effect. Each test passes
a piece through one effect and checks that the result is finite,
non-empty, and audibly distinct from the dry rendering for parameter
values that should affect the signal.
"""

import math

from musicky import (
    Effect,
    chord,
    chorus,
    clip,
    compressor,
    delay,
    distortion,
    eq,
    highpass,
    limiter,
    lowpass,
    musicky,
    normalize,
    piano,
    reverb,
)
from musicky.out.synth import sine_engine

SR = 8000


def _render(node: Effect | object) -> list[float]:
    return sine_engine(musicky(node), SR)  # type: ignore[arg-type]


def _all_finite(samples: list[float]) -> bool:
    return all(math.isfinite(s) for s in samples)


def _max_abs(samples: list[float]) -> float:
    return max((abs(s) for s in samples), default=0.0)


def test_swing_changes_intervals() -> None:
    """`swing` should perturb interval data on note-by-note clips."""
    from musicky import swing
    from musicky.core.render import flatten_voices as flatten

    melody = chord("C4, D4, E4, F4", interval=0.25)
    voices = flatten(swing(piano(clip(melody)), amount=0.05))
    intervals = voices[0].clip.content.intervals
    # First interval is even-indexed (i=0), so it shifts up by amount.
    assert intervals[0] > 0.25
    # Second is odd-indexed (i=1), so it shifts down.
    assert intervals[1] < 0.25


def test_arpeggiate_spreads_block_chord_in_time() -> None:
    from musicky import arpeggiate
    from musicky.core.render import flatten_voices as flatten

    block = chord("C4, E4, G4")  # interval=0 by default
    voices = flatten(arpeggiate(piano(clip(block)), interval=0.1))
    assert all(iv == 0.1 for iv in voices[0].clip.content.intervals)


def test_lowpass_attenuates_a_high_tone() -> None:
    """A 1 kHz lowpass should reduce the level of higher pitches."""
    plain = _render(piano(clip(chord("C7"))))  # 2093 Hz, well above cutoff
    filtered = _render(lowpass(piano(clip(chord("C7"))), cutoff=500.0))
    assert _all_finite(filtered)
    assert _max_abs(filtered) < _max_abs(plain) * 0.9


def test_highpass_attenuates_a_low_tone() -> None:
    plain = _render(piano(clip(chord("C2"))))  # ~65 Hz, below cutoff
    filtered = _render(highpass(piano(clip(chord("C2"))), cutoff=2000.0))
    assert _all_finite(filtered)
    assert _max_abs(filtered) < _max_abs(plain) * 0.9


def test_eq_unity_when_all_zero() -> None:
    """An EQ with all bands at 0 dB must reproduce the input within rounding."""
    plain = _render(piano(clip(chord("C4"))))
    eqd = _render(eq(piano(clip(chord("C4"))), low=0, mid=0, high=0))
    # Allow some numerical slack (band-split filters introduce tiny drift).
    assert max(abs(a - b) for a, b in zip(plain, eqd, strict=True)) < 0.05


def test_eq_high_boost_increases_output() -> None:
    plain = _render(piano(clip(chord("C7"))))
    boosted = _render(eq(piano(clip(chord("C7"))), high=12.0))
    assert _all_finite(boosted)
    assert _max_abs(boosted) > _max_abs(plain)


def test_compressor_reduces_peak() -> None:
    plain = _render(piano(clip(chord("C4, E4, G4, C5"))))
    crushed = _render(
        compressor(piano(clip(chord("C4, E4, G4, C5"))), threshold=-20, ratio=8.0),
    )
    assert _all_finite(crushed)
    # The compressor should not increase the peak; it usually lowers it.
    assert _max_abs(crushed) <= _max_abs(plain) + 1e-6


def test_distortion_clips_within_unity() -> None:
    out = _render(distortion(piano(clip(chord("C4"))), drive=10.0, mix=1.0))
    assert _all_finite(out)
    # tanh saturates around ±1; the mix=1 path must not exceed that.
    assert _max_abs(out) <= 1.0 + 1e-6


def test_distortion_mix_zero_is_dry() -> None:
    plain = _render(piano(clip(chord("C4"))))
    out = _render(distortion(piano(clip(chord("C4"))), drive=10.0, mix=0.0))
    assert all(abs(a - b) < 1e-9 for a, b in zip(plain, out, strict=True))


def test_delay_adds_audible_echo() -> None:
    out = _render(delay(piano(clip(chord("C4"))), time=0.05, feedback=0.5, mix=0.5))
    assert _all_finite(out)
    # An echo means the signal extends past the original note region;
    # the first 100 ms should still have energy.
    tail_energy = sum(abs(s) for s in out[int(0.1 * SR) : int(0.3 * SR)])
    assert tail_energy > 0.5


def test_chorus_runs_without_error() -> None:
    """Chorus mostly modulates phase; we just confirm finiteness and shape."""
    out = _render(chorus(piano(clip(chord("C4"))), rate=2.0, depth=0.005, mix=0.7))
    assert _all_finite(out)
    assert len(out) > 0
    assert _max_abs(out) > 0.0


def test_normalize_brings_peak_to_target() -> None:
    out = _render(normalize(piano(clip(chord("C4"))), peak=0.5))
    assert _all_finite(out)
    # Normalize is the last fx in this single-effect chain, so the
    # output peak should be very close to the requested level.
    assert abs(_max_abs(out) - 0.5) < 1e-6


def test_limiter_caps_to_threshold() -> None:
    """A -3 dB limiter must keep all samples below ~0.708."""
    out = _render(limiter(piano(clip(chord("C4, E4, G4"))), threshold=-3.0))
    ceiling = 10 ** (-3.0 / 20.0)
    assert _all_finite(out)
    assert _max_abs(out) <= ceiling + 1e-6


def test_reverb_decay_extends_tail() -> None:
    """Longer decay means more energy late in the buffer."""
    short = _render(reverb(piano(clip(chord("C4"))), amount=1.0, decay=0.2))
    long_ = _render(reverb(piano(clip(chord("C4"))), amount=1.0, decay=2.0))
    # Compare the trailing 25% of each render.
    cut = int(0.75 * len(short))
    short_tail = sum(abs(s) for s in short[cut:])
    long_tail = sum(abs(s) for s in long_[cut:])
    assert long_tail > short_tail
