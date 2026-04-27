"""Synthesis engines: turn a Piece into mono float samples.

Each engine is a function ``(Piece, sample_rate) -> list[float]``. The
engine picks the basic waveform; effect processing and clip layout are
handled uniformly by `musicky.core.render`.

Built-in engines:
  * ``sine``    — pure sine wave (default)
  * ``triangle``— triangle wave
  * ``square``  — square wave
  * ``saw``     — sawtooth wave
  * ``additive``— sine plus weighted harmonics
  * ``fluidsynth``— SoundFont-based renderer (requires pyfluidsynth + .sf2)

A user can also pass any callable matching ``Engine`` to ``output(...)``.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from typing import Any

from musicky.core.node import Clip
from musicky.core.piece import Piece
from musicky.core.render import Voice, flatten, synthesize
from musicky.primitives.note import PITCH_CLASSES

__all__ = [
    "Engine",
    "additive_engine",
    "fluidsynth_engine",
    "resolve_engine",
    "saw_engine",
    "sine_engine",
    "square_engine",
    "triangle_engine",
]

Engine = Callable[[Piece, int], list[float]]


def resolve_engine(
    engine: str | Engine,
    *,
    soundfont: str | None = None,
    harmonics: tuple[float, ...] = (1.0, 0.5, 0.25, 0.125),
) -> Engine:
    """Translate a user-supplied engine spec into a concrete callable."""
    if callable(engine):
        return engine

    if engine == "sine":
        return sine_engine
    if engine == "triangle":
        return triangle_engine
    if engine == "square":
        return square_engine
    if engine == "saw":
        return saw_engine
    if engine == "additive":
        return lambda music, sr: additive_engine(music, sr, harmonics=harmonics)
    if engine == "fluidsynth":
        # No explicit soundfont? Fall back to the auto-resolved default
        # so the simplest call site — output(music, "song.wav") — just
        # works on the first run.
        if soundfont is None:
            from musicky.sf import default_soundfont

            sf_path = str(default_soundfont())
        else:
            sf_path = soundfont
        return lambda music, sr: fluidsynth_engine(music, sr, soundfont=sf_path)

    raise ValueError(
        f"unknown engine {engine!r}. "
        "Built-in engines: 'sine', 'triangle', 'square', 'saw', 'additive', "
        "'fluidsynth'. You can also pass any callable matching "
        "(Piece, sample_rate) -> list[float] as a custom engine.",
    )


def sine_engine(music: Piece, sample_rate: int) -> list[float]:
    """Pure sine wave: cleanest, no aliasing, but flute-like."""
    return _render(music, sample_rate, _sine_wave)


def triangle_engine(music: Piece, sample_rate: int) -> list[float]:
    """Triangle wave: warm, low harmonic content."""
    return _render(music, sample_rate, _triangle_wave)


def square_engine(music: Piece, sample_rate: int) -> list[float]:
    """Square wave: chiptune character."""
    return _render(music, sample_rate, _square_wave)


def saw_engine(music: Piece, sample_rate: int) -> list[float]:
    """Sawtooth wave: bright synth-lead character."""
    return _render(music, sample_rate, _saw_wave)


def additive_engine(
    music: Piece,
    sample_rate: int,
    *,
    harmonics: tuple[float, ...] = (1.0, 0.5, 0.25, 0.125),
) -> list[float]:
    """Sine plus weighted harmonics (fundamental at index 1)."""
    norm = sum(abs(w) for w in harmonics) or 1.0

    def waveform(phase: float, _h: tuple[float, ...] = harmonics, _n: float = norm) -> float:
        s = 0.0
        for i, weight in enumerate(_h, start=1):
            s += weight * math.sin(i * phase)
        return s / _n

    return _render(music, sample_rate, waveform)


def fluidsynth_engine(
    music: Piece,
    sample_rate: int,
    *,
    soundfont: str,
) -> list[float]:
    """Render via pyfluidsynth using a SoundFont.

    Audio effects from the Node tree (reverb, eq, lowpass, ...) ARE
    honored: voices that share an audio-fx chain are rendered together
    into one bus, then the bus is sent through the chain just like the
    in-Python engines do. This means ``reverb(piano(clip(...)))`` works
    the same way regardless of which engine the user picked.

    `Sample` nodes are dropped: fluidsynth cannot mix in pre-recorded
    audio. Users who need that should fall back to a built-in waveform
    engine where Sample mixing is performed in pure Python.
    """
    from musicky.core.render import _apply_chains  # internal but stable

    voices = [v for v in flatten(music.root) if isinstance(v, Voice)]
    if not voices:
        return [0.0]

    spb = 60.0 / music.bpm
    total_seconds = max(
        (_voice_seconds(v.clip, spb) for v in voices),
        default=0.0,
    )
    total_samples = max(1, round((total_seconds + 0.5) * sample_rate))

    # Group voices by their audio_fx chain identity so the synth runs
    # once per bus and the chain is applied once per bus afterwards.
    groups: dict[tuple[int, ...], list[Voice]] = {}
    for v in voices:
        key = tuple(id(fn) for fn in v.audio_fx)
        groups.setdefault(key, []).append(v)

    bus_voices: list[Voice] = []
    bus_buffers: list[list[float]] = []
    for grouped in groups.values():
        bus_buffers.append(
            _render_voices_with_fluidsynth(
                grouped,
                soundfont,
                sample_rate,
                spb,
                total_samples,
            ),
        )
        # All voices in the group share audio_fx, so picking the first
        # one is enough for `_apply_chains` to read the chain off of.
        bus_voices.append(grouped[0])

    return _apply_chains(bus_voices, bus_buffers, sample_rate, music.bpm)


def _render_voices_with_fluidsynth(
    voices: list[Voice],
    soundfont: str,
    sample_rate: int,
    spb: float,
    total_samples: int,
) -> list[float]:
    """Run a group of voices through a fresh fluidsynth instance.

    Each call gets its own Synth so program_select state does not leak
    between buses. The events from every voice in the group are merged
    onto a single timeline and rendered into one mono buffer.
    """
    fluidsynth = _import_fluidsynth()
    fs = fluidsynth.Synth(samplerate=float(sample_rate))
    sfid = fs.sfload(soundfont)
    if sfid == -1:
        # fluidsynth signals failure with -1 instead of raising. Turn
        # that into a clear error so users do not silently get a dead
        # buffer when the SoundFont path is wrong.
        fs.delete()
        raise FileNotFoundError(
            f"fluidsynth could not load SoundFont {soundfont!r}. "
            "Check that the file exists and is a valid .sf2/.sf3.",
        )

    events: list[tuple[int, str, int, int, int]] = []
    for v in voices:
        # Pass v.bank so SoundFont kits keyed by bank (TR-808 etc.)
        # play correctly under fluidsynth, matching the MIDI backend.
        fs.program_select(v.channel, sfid, v.bank, v.program)
        cursor = v.clip.at
        for i, n in enumerate(v.clip.content.notes):
            on = round(cursor * spb * sample_rate)
            off = on + round(n.duration * spb * sample_rate)
            midi = max(0, min(127, (n.octave + 1) * 12 + PITCH_CLASSES.index(n.name)))
            velocity = max(0, min(127, n.velocity))
            events.append((on, "on", v.channel, midi, velocity))
            events.append((off, "off", v.channel, midi, 0))
            if i < len(v.clip.content.intervals):
                cursor += v.clip.content.intervals[i]

    events.sort(key=lambda e: e[0])

    out = [0.0] * total_samples
    cursor_sample = 0
    for ev_sample, kind, channel, pitch, velocity in events:
        if ev_sample > cursor_sample:
            chunk = fs.get_samples(ev_sample - cursor_sample)
            _accumulate_int16(out, chunk, cursor_sample)
            cursor_sample = ev_sample
        if kind == "on":
            fs.noteon(channel, pitch, velocity)
        else:
            fs.noteoff(channel, pitch)
    if cursor_sample < total_samples:
        chunk = fs.get_samples(total_samples - cursor_sample)
        _accumulate_int16(out, chunk, cursor_sample)

    fs.delete()
    return out


# --- helpers ------------------------------------------------------------------


def _render(music: Piece, sample_rate: int, waveform: Callable[[float], float]) -> list[float]:
    voices = flatten(music.root)
    return synthesize(
        voices,
        sample_rate=sample_rate,
        bpm=music.bpm,
        waveform=waveform,
    )


def _voice_seconds(clip: Clip, spb: float) -> float:
    end = clip.at
    cursor = clip.at
    notes = clip.content.notes
    intervals = clip.content.intervals
    for i, n in enumerate(notes):
        end = max(end, cursor + n.duration)
        if i < len(intervals):
            cursor += intervals[i]
    return end * spb


def _sine_wave(phase: float) -> float:
    return math.sin(phase)


def _triangle_wave(phase: float) -> float:
    t = (phase / (2.0 * math.pi)) % 1.0
    return 4.0 * abs(t - 0.5) - 1.0


def _square_wave(phase: float) -> float:
    return 1.0 if math.sin(phase) >= 0 else -1.0


def _saw_wave(phase: float) -> float:
    t = (phase / (2.0 * math.pi)) % 1.0
    return 2.0 * t - 1.0


def _import_fluidsynth() -> Any:
    try:
        import fluidsynth  # type: ignore[import-untyped]
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "pyfluidsynth is part of the core dependencies of musicky. "
            "If it is missing, reinstall with `pip install musicky`. "
            "You also need the underlying libfluidsynth library: "
            "`apt install libfluidsynth3` on Debian/Ubuntu, "
            "`brew install fluid-synth` on macOS.",
        ) from exc
    return fluidsynth


def _accumulate_int16(out: list[float], chunk: Any, start: int) -> None:
    n_pairs = len(chunk) // 2
    for i in range(n_pairs):
        idx = start + i
        if idx >= len(out):
            break
        left = chunk[2 * i] / 32768.0
        right = chunk[2 * i + 1] / 32768.0
        out[idx] += (left + right) * 0.5
