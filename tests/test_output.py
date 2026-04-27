from pathlib import Path

import pytest

from musicky import bass, chord, clip, musicky, output, piano
from musicky.out.output import render_wav_bytes


def test_render_wav_bytes_starts_with_riff() -> None:
    music = musicky(piano(clip(chord("C4, E4, G4"))))
    data = render_wav_bytes(music, sample_rate=8000)
    assert data[:4] == b"RIFF"
    assert data[8:12] == b"WAVE"


def test_output_writes_wav_file(tmp_path: Path) -> None:
    out = tmp_path / "song.wav"
    music = musicky(piano(clip(chord("C4, E4, G4"))), bass(clip(chord("C2"))))
    output(music, out, sample_rate=8000)
    assert out.exists()
    assert out.read_bytes()[:4] == b"RIFF"


def test_output_unsupported_format_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unsupported"):
        output(musicky(piano(clip(chord("C4")))), tmp_path / "out.xyz")


def test_output_format_override(tmp_path: Path) -> None:
    out = tmp_path / "song.dat"
    output(musicky(piano(clip(chord("C4")))), out, format="wav", sample_rate=8000)
    assert out.read_bytes()[:4] == b"RIFF"


def test_output_engine_triangle(tmp_path: Path) -> None:
    out = tmp_path / "tri.wav"
    output(musicky(piano(clip(chord("C4, E4, G4")))), out, engine="triangle", sample_rate=8000)
    assert out.read_bytes()[:4] == b"RIFF"


def test_output_engine_unknown_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unknown engine"):
        output(
            musicky(piano(clip(chord("C4")))),
            tmp_path / "out.wav",
            engine="zither",
            sample_rate=8000,
        )


def test_output_engine_fluidsynth_uses_env_soundfont(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """`engine="fluidsynth"` resolves the SoundFont automatically.

    With ``MUSICKY_SOUNDFONT`` pointing at a missing file we expect a
    clear `RuntimeError` rather than the old `ValueError("soundfont")`
    (the old API required passing soundfont= explicitly; the new one
    falls back to ``default_soundfont()``).
    """
    monkeypatch.setenv("MUSICKY_SOUNDFONT", str(tmp_path / "missing.sf2"))
    with pytest.raises(RuntimeError, match="MUSICKY_SOUNDFONT"):
        output(
            musicky(piano(clip(chord("C4")))),
            tmp_path / "out.wav",
            engine="fluidsynth",
            sample_rate=8000,
        )


def test_output_engine_callable(tmp_path: Path) -> None:
    def silent_engine(_music: object, _sr: int) -> list[float]:
        return [0.0] * 100

    out = tmp_path / "silent.wav"
    output(musicky(piano(clip(chord("C4")))), out, engine=silent_engine, sample_rate=8000)
    assert out.read_bytes()[:4] == b"RIFF"


def test_output_mp3_without_ffmpeg(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import shutil as real_shutil

    monkeypatch.setattr(real_shutil, "which", lambda _name: None)
    with pytest.raises(RuntimeError, match="ffmpeg"):
        output(musicky(piano(clip(chord("C4")))), tmp_path / "out.mp3", sample_rate=8000)
