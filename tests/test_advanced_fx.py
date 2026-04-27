"""Tests for the post-dogfooding additions: gain, duck, sample, ADSR, automation."""

import math
import struct
import wave
from pathlib import Path

from musicky import (
    Sample,
    auto,
    chord,
    clip,
    duck,
    gain,
    kick,
    lowpass,
    master,
    musicky,
    piano,
    sample,
    saw_lead,
    tr808,
)
from musicky.core.render import flatten, flatten_voices
from musicky.out.synth import sine_engine

SR = 8000


def _render(node: object) -> list[float]:
    return sine_engine(musicky(node), SR)  # type: ignore[arg-type]


def _max_abs(samples: list[float]) -> float:
    return max((abs(s) for s in samples), default=0.0)


# --- gain ---------------------------------------------------------------------


def test_gain_zero_db_is_passthrough() -> None:
    plain = _render(piano(clip(chord("C4"))))
    same = _render(gain(piano(clip(chord("C4"))), db=0.0))
    assert plain == same


def test_gain_six_db_doubles_amplitude() -> None:
    plain_peak = _max_abs(_render(piano(clip(chord("C4")))))
    boosted_peak = _max_abs(_render(gain(piano(clip(chord("C4"))), db=6.0)))
    # +6 dB is roughly a 2x amplitude increase.
    assert 1.7 < boosted_peak / plain_peak < 2.3


def test_gain_accepts_automation() -> None:
    """Automated gain should not crash and must produce finite samples."""
    fade = auto([(0.0, -60.0), (1.0, 0.0)])
    out = _render(gain(piano(clip(chord("C4"))), db=fade))
    assert all(math.isfinite(s) for s in out)


# --- duck ---------------------------------------------------------------------


def test_duck_reduces_overall_level() -> None:
    """A periodic duck should lower the energy of a sustained signal."""
    sustained_chord = chord("C4, E4, G4")
    plain = _render(piano(clip(sustained_chord)))
    ducked = _render(duck(piano(clip(sustained_chord)), by=0.7, rate=2.0))
    plain_energy = sum(abs(s) for s in plain)
    ducked_energy = sum(abs(s) for s in ducked)
    assert ducked_energy < plain_energy


def test_duck_zero_amount_is_passthrough() -> None:
    plain = _render(piano(clip(chord("C4"))))
    same = _render(duck(piano(clip(chord("C4"))), by=0.0))
    assert plain == same


# --- sample -------------------------------------------------------------------


def _write_test_wav(path: Path, frequency: float = 440.0, seconds: float = 0.2) -> None:
    """Synthesize a tiny sine-wave wav so we have a real sample to load."""
    sr = 22050
    n = int(sr * seconds)
    pcm = bytearray()
    for i in range(n):
        v = math.sin(2 * math.pi * frequency * i / sr) * 0.5
        pcm += struct.pack("<h", int(v * 32767))
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(bytes(pcm))


def test_sample_returns_sample_node() -> None:
    s = sample("test.wav", at=2.0, volume=0.5, speed=0.75)
    assert isinstance(s, Sample)
    assert s.at == 2.0
    assert s.volume == 0.5
    assert s.speed == 0.75


def test_sample_loads_and_mixes_into_output(tmp_path: Path) -> None:
    wav = tmp_path / "tone.wav"
    _write_test_wav(wav, frequency=880.0)
    music = musicky(sample(str(wav), at=0.0, volume=0.8), bpm=120)
    out = sine_engine(music, SR)
    # Should produce a non-silent buffer because the sample contributes.
    assert _max_abs(out) > 0.1


def test_sample_volume_zero_is_silent(tmp_path: Path) -> None:
    wav = tmp_path / "tone.wav"
    _write_test_wav(wav)
    music = musicky(sample(str(wav), at=0.0, volume=0.0), bpm=120)
    out = sine_engine(music, SR)
    assert _max_abs(out) < 1e-6


def test_sample_can_be_wrapped_in_effect(tmp_path: Path) -> None:
    """Samples should pass through the audio_fx chain like a Voice."""
    wav = tmp_path / "tone.wav"
    _write_test_wav(wav)
    music = musicky(lowpass(sample(str(wav)), cutoff=200.0), bpm=120)
    out = sine_engine(music, SR)
    assert all(math.isfinite(s) for s in out)


def test_sample_missing_file_raises(tmp_path: Path) -> None:
    import pytest

    music = musicky(sample(str(tmp_path / "nope.wav")), bpm=120)
    with pytest.raises(FileNotFoundError):
        sine_engine(music, SR)


# --- ADSR profile coverage ----------------------------------------------------


def test_drum_profile_gives_short_envelope() -> None:
    """A kick should fade to silence well inside one second."""
    music = musicky(tr808(kick(at=0.0, velocity=120)), bpm=120)
    out = sine_engine(music, SR)
    # By 0.5 s the kick must already be quiet.
    half_sec = SR // 2
    if len(out) > half_sec:
        late = out[half_sec : half_sec + 100]
        early = out[:100]
        assert _max_abs(late) < _max_abs(early)


def test_pad_profile_holds_longer_than_lead_profile() -> None:
    """Same note on a pad should ring longer than on a lead."""
    pad_music = musicky(_pad_voice(), bpm=120)  # type: ignore[arg-type]
    lead_music = musicky(_lead_voice(), bpm=120)  # type: ignore[arg-type]
    pad_out = sine_engine(pad_music, SR)
    lead_out = sine_engine(lead_music, SR)
    # 0.4 s after note start the pad still has energy, the lead is mostly
    # released — compare the trailing energy of identical-length renders.
    cut = int(0.5 * SR)
    if cut < len(pad_out) and cut < len(lead_out):
        pad_tail = sum(abs(s) for s in pad_out[cut:])
        lead_tail = sum(abs(s) for s in lead_out[cut:])
        assert pad_tail >= lead_tail


def _pad_voice() -> object:
    from musicky import warm_pad

    return warm_pad(clip(chord("C4", duration=1.0)))


def _lead_voice() -> object:
    return saw_lead(clip(chord("C4", duration=1.0)))


# --- Sample is excluded from MIDI export -------------------------------------


def test_sample_node_is_skipped_in_midi(tmp_path: Path) -> None:
    """SMF cannot embed audio, so Sample nodes should not appear there."""
    wav = tmp_path / "tone.wav"
    _write_test_wav(wav)
    music = musicky(sample(str(wav)), piano(clip(chord("C4"))), bpm=120)
    from musicky.out.play.midi import render_to_bytes

    data = render_to_bytes(music)
    # Should be a normal MIDI file, just with the piano voice.
    assert data.startswith(b"MThd")
    # Conductor + 1 piano track.
    assert data.count(b"MTrk") == 2


def test_flatten_voices_filters_out_samples(tmp_path: Path) -> None:
    """`flatten_voices` should omit SampledVoice entries."""
    wav = tmp_path / "tone.wav"
    _write_test_wav(wav)
    music = musicky(sample(str(wav)), piano(clip(chord("C4"))), bpm=120)
    all_flat = flatten(music.root)
    voices_only = flatten_voices(music.root)
    assert len(all_flat) == 2
    assert len(voices_only) == 1


# --- Master nesting still works ----------------------------------------------


def test_master_with_all_new_effects() -> None:
    """A realistic mix tree using gain + duck + automation should render."""
    music = musicky(
        master(
            gain(
                lowpass(
                    piano(clip(chord("C4, E4, G4"))),
                    cutoff=auto([(0.0, 500.0), (2.0, 4000.0)]),
                ),
                db=-1.0,
            ),
            duck(
                tr808(kick(at=0.0)),
                by=0.5,
                rate=2.0,
            ),
        ),
        bpm=120,
    )
    out = sine_engine(music, SR)
    assert all(math.isfinite(s) for s in out)
