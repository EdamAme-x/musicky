"""Tests for the LFO/saturation/sidechain effects added for electronic music."""

import math

from musicky import (
    chord,
    clip,
    kick,
    musicky,
    piano,
    saturate,
    saw_lead,
    sidechain,
    sub_bass,
    tr808,
    tremolo,
    vibrato,
    wobble,
)
from musicky.out.synth import sine_engine

SR = 8000


def _render(node: object) -> list[float]:
    return sine_engine(musicky(node), SR)  # type: ignore[arg-type]


def _max_abs(samples: list[float]) -> float:
    return max((abs(s) for s in samples), default=0.0)


# --- vibrato ------------------------------------------------------------------


def test_vibrato_keeps_signal_finite_and_audible() -> None:
    out = _render(vibrato(saw_lead(clip(chord("A4", duration=1.0))), rate=5.0, depth=0.003))
    assert all(math.isfinite(s) for s in out)
    assert _max_abs(out) > 0.0


def test_vibrato_zero_depth_is_passthrough_like() -> None:
    plain = _render(saw_lead(clip(chord("A4", duration=1.0))))
    out = _render(vibrato(saw_lead(clip(chord("A4", duration=1.0))), rate=5.0, depth=0.0))
    # Depth 0 means no time-based detuning; output should be similar shape.
    assert _max_abs(out) > 0.0
    assert abs(_max_abs(out) - _max_abs(plain)) < _max_abs(plain) * 0.5


# --- tremolo ------------------------------------------------------------------


def test_tremolo_modulates_amplitude() -> None:
    plain = _render(saw_lead(clip(chord("A4", duration=1.0))))
    out = _render(tremolo(saw_lead(clip(chord("A4", duration=1.0))), rate=4.0, depth=0.8))
    # Tremolo at depth 0.8 should reduce mid-buffer amplitude noticeably
    # compared to the dry render.
    cut = len(plain) // 4
    plain_window = sum(abs(s) for s in plain[cut : 3 * cut])
    out_window = sum(abs(s) for s in out[cut : 3 * cut])
    assert out_window < plain_window


def test_tremolo_zero_depth_is_passthrough() -> None:
    plain = _render(saw_lead(clip(chord("A4"))))
    out = _render(tremolo(saw_lead(clip(chord("A4"))), rate=4.0, depth=0.0))
    assert plain == out


# --- wobble -------------------------------------------------------------------


def test_wobble_runs_without_blowing_up() -> None:
    out = _render(
        wobble(sub_bass(clip(chord("A2", duration=1.0))), rate=2.0, low=200.0, high=4000.0)
    )
    assert all(math.isfinite(s) for s in out)
    assert _max_abs(out) > 0.0


# --- saturate -----------------------------------------------------------------


def test_saturate_does_not_clip() -> None:
    out = _render(saturate(piano(clip(chord("C4, E4, G4"))), amount=3.0, warmth=0.6))
    assert all(math.isfinite(s) for s in out)
    # Saturation should keep peaks roughly bounded; tanh + warmth term
    # tops out around 1.4 in the worst case.
    assert _max_abs(out) < 1.6


def test_saturate_zero_amount_passes_through() -> None:
    plain = _render(piano(clip(chord("C4"))))
    out = _render(saturate(piano(clip(chord("C4"))), amount=0.0, warmth=0.0))
    # tanh(0 * x) = 0 plus warmth=0 even term = 0 -> pure silence
    assert _max_abs(out) < 1e-6
    # Quick sanity that the dry path itself is not silent.
    assert _max_abs(plain) > 0.0


# --- sidechain ----------------------------------------------------------------


def test_sidechain_ducks_when_source_is_active() -> None:
    """The bass should be quieter at kick onset than between kicks."""
    bass = sub_bass(clip(chord("A1", duration=2.0)))
    kicks = tr808(kick(at=0.0, velocity=120))
    music = musicky(
        sidechain(bass, source=kicks, amount=0.9, attack=0.002, release=0.15),
        bpm=120,
    )
    out = sine_engine(music, SR)

    # Look at the first 50 ms (kick is loudest) vs 400-450 ms (no kick).
    early = out[: int(0.05 * SR)]
    late = out[int(0.4 * SR) : int(0.45 * SR)]
    assert _max_abs(early) < _max_abs(late)


def test_sidechain_amount_zero_is_passthrough() -> None:
    bass = sub_bass(clip(chord("A1", duration=1.0)))
    kicks = tr808(kick(at=0.0, velocity=120))
    plain_music = musicky(bass, bpm=120)
    sc_music = musicky(sidechain(bass, source=kicks, amount=0.0), bpm=120)
    plain = sine_engine(plain_music, SR)
    sc = sine_engine(sc_music, SR)
    assert plain == sc


# --- sub_bass instrument ------------------------------------------------------


def test_sub_bass_renders_low_note() -> None:
    music = musicky(sub_bass(clip(chord("A1", duration=0.5))), bpm=120)
    out = sine_engine(music, SR)
    assert all(math.isfinite(s) for s in out)
    assert _max_abs(out) > 0.0


def test_sub_bass_program_is_synth_bass_2() -> None:
    """sub_bass aliases to GM 39 which is the synth_bass_2 timbre."""
    from musicky.core.render import flatten_voices

    music = musicky(sub_bass(clip(chord("A1"))), bpm=120)
    voices = flatten_voices(music.root)
    assert voices[0].program == 39
    assert voices[0].instrument == "sub_bass"
