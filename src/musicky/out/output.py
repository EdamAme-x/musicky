"""Audio file output: render a Piece to wav/mp3/ogg/flac.

`output(music, path)` renders the Node tree into a mono WAV using the
chosen synthesis engine, then (for non-wav formats) shells out to
``ffmpeg`` for encoding. WAV is produced via the standard library's
``wave`` module.
"""

from __future__ import annotations

import shutil
import struct
import subprocess
import tempfile
import wave
from io import BytesIO
from pathlib import Path
from typing import Final

from musicky.core.piece import Piece
from musicky.out.synth import Engine, resolve_engine

__all__ = ["output", "render_wav_bytes"]

_SUPPORTED_FORMATS: Final[frozenset[str]] = frozenset({"wav", "mp3", "ogg", "flac"})


def output(
    music: Piece,
    path: str | Path,
    *,
    format: str | None = None,
    engine: str | Engine = "fluidsynth",
    soundfont: str | None = None,
    harmonics: tuple[float, ...] = (1.0, 0.5, 0.25, 0.125),
    sample_rate: int = 44100,
) -> None:
    """Render `music` to an audio file.

    Defaults to the SoundFont-based ``"fluidsynth"`` engine, which gives
    real instrument sounds. The first call downloads a small SoundFont
    (~33 MB) into ``~/.cache/musicky``; set the ``MUSICKY_SOUNDFONT``
    environment variable to point at your own .sf2/.sf3 to skip that.

    The output format is taken from the file extension unless `format`
    is passed explicitly. `harmonics` is consumed only by the additive
    engine.
    """
    target = Path(path)
    fmt = (format or target.suffix.lstrip(".")).lower()
    if fmt not in _SUPPORTED_FORMATS:
        raise ValueError(
            f"unsupported output format {fmt!r}. "
            f"Supported formats: {sorted(_SUPPORTED_FORMATS)}. "
            "The format is taken from the file extension; pass format= to override.",
        )

    wav_bytes = render_wav_bytes(
        music,
        engine=engine,
        soundfont=soundfont,
        harmonics=harmonics,
        sample_rate=sample_rate,
    )

    if fmt == "wav":
        target.write_bytes(wav_bytes)
        return

    if shutil.which("ffmpeg") is None:
        raise RuntimeError(
            f"ffmpeg is required to write {fmt!r} but was not found on PATH.\n"
            f"  - Install ffmpeg (https://ffmpeg.org/download.html)\n"
            f"  - Or use wav output: output(music, 'out.wav')",
        )

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as fh:
        fh.write(wav_bytes)
        tmp_wav = Path(fh.name)
    try:
        result = subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp_wav), str(target)],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"ffmpeg failed to encode {fmt!r}:\n{result.stderr.strip()}",
            )
    finally:
        tmp_wav.unlink(missing_ok=True)


def render_wav_bytes(
    music: Piece,
    *,
    engine: str | Engine = "fluidsynth",
    soundfont: str | None = None,
    harmonics: tuple[float, ...] = (1.0, 0.5, 0.25, 0.125),
    sample_rate: int = 44100,
) -> bytes:
    """Synthesize the Piece into raw WAV (PCM16, mono) bytes.

    Same defaults as `output()`: ``"fluidsynth"`` with an auto-resolved
    SoundFont. Pass `engine="sine"` (or any other built-in name) to use
    the in-Python waveform engines instead.
    """
    fn = resolve_engine(engine, soundfont=soundfont, harmonics=harmonics)
    samples = fn(music, sample_rate)

    peak = max((abs(v) for v in samples), default=0.0)
    scale = 0.9 / peak if peak > 1.0 else 1.0
    pcm = bytearray()
    for v in samples:
        clamped = max(-1.0, min(1.0, v * scale))
        pcm += struct.pack("<h", int(clamped * 32767))

    buf = BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(bytes(pcm))
    return buf.getvalue()
