"""Render a Node tree to flat events and to PCM samples.

The renderer has no knowledge of specific effects. It just walks the tree
and invokes the callables that effect nodes carry on themselves:

  * ``effect.transpose_offset`` shifts pitch during the symbolic pass.
  * ``effect.chord_transform`` rewrites Chord data during the symbolic pass.
  * ``effect.apply`` processes audio buffers during synthesis.

Adding a new effect therefore requires no change here — the user (or
``musicky.effects.fx``) only writes a constructor that produces an
`Effect` with the right callables.

Two passes:

1. ``flatten(node)`` walks the tree, applying symbolic effects to chord
   data and computing each clip's start time, instrument program and
   audio-effect chain. Returns one ``Voice`` per clip.

2. ``synthesize(voices, ...)`` turns those voices into a mono PCM
   buffer. Each clip is rendered with the supplied waveform engine,
   then the audio chain is applied scope by scope: voices that share a
   chain prefix form a sub-bus.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace

from musicky.core.node import (
    AudioFn,
    ChordFn,
    Clip,
    Effect,
    Instrument,
    Mix,
    Node,
    Sample,
)
from musicky.primitives.chord import Chord
from musicky.primitives.note import PITCH_CLASSES, Note

__all__ = [
    "FlatNode",
    "SampledVoice",
    "Voice",
    "flatten",
    "flatten_voices",
    "render_audio",
    "synthesize",
]

# Each chain link is just the audio function the renderer should apply.
# Two voices sharing a common chain prefix end up in the same sub-bus.
AudioFxChain = tuple[AudioFn, ...]


@dataclass(frozen=True, slots=True)
class Voice:
    """A clip with its instrument and audio-effect chain, ready to render."""

    clip: Clip
    program: int
    bank: int  # MIDI bank (Bank Select MSB); 0 means GM Bank 0
    channel: int  # MIDI channel; 9 is reserved for percussion
    audio_fx: AudioFxChain  # outermost first: chain[0] wraps everything below
    instrument: str = ""  # human label of the source Instrument node


@dataclass(frozen=True, slots=True)
class SampledVoice:
    """An external audio sample with its placement and effect chain.

    Mirrors `Voice` but for `Sample` nodes: the renderer loads the file,
    pastes it onto the timeline at `sample.at`, then routes the result
    through the same `audio_fx` chain as ordinary voices.
    """

    sample: Sample
    audio_fx: AudioFxChain


# A flat traversal entry can be either a synth voice or an audio sample.
FlatNode = Voice | SampledVoice


# --- Pass 1: flatten ----------------------------------------------------------


def flatten_voices(root: Node) -> list[Voice]:
    """Convenience: `flatten(root)` narrowed to synth voices only.

    Tests and any caller that does not care about Sample placement can
    use this to avoid type-narrowing every time.
    """
    return [v for v in flatten(root) if isinstance(v, Voice)]


def flatten(root: Node) -> list[FlatNode]:
    """Traverse the tree, applying symbolic effects on the way down.

    Returns a flat list mixing synth voices and sample nodes; the
    synthesis pass handles each kind separately but routes them through
    the same audio-effect chain.
    """
    # `assigned` maps an instrument's identity (name + program + bank)
    # to the MIDI channel it has been given. Re-using the same channel
    # for multiple occurrences of the same instrument is what lets users
    # write e.g. ``seq(saw_lead(...), saw_lead(...), ...)`` without
    # exhausting the 16-channel limit. Channel 9 is reserved for
    # percussion by the GM convention.
    assigned: dict[tuple[str, int, int], int] = {}
    next_channel = [0]
    state = _State()
    return _walk(root, state, assigned, next_channel)


@dataclass(frozen=True, slots=True)
class _State:
    """Context handed down during traversal.

    Tracks the active instrument (program/channel) and the audio-fx
    chain accumulated from outermost ancestors. Symbolic transforms are
    applied immediately as we descend, so they do not need storage here
    beyond the merged callable.
    """

    program: int = 0
    bank: int = 0
    channel: int | None = None
    audio_fx: AudioFxChain = ()
    transpose_offset: int = 0
    chord_transform: ChordFn | None = None
    instrument: str = ""


def _walk(
    node: Node,
    st: _State,
    assigned: dict[tuple[str, int, int], int],
    next_channel: list[int],
) -> list[FlatNode]:
    if isinstance(node, Sample):
        return [SampledVoice(sample=node, audio_fx=st.audio_fx)]

    if isinstance(node, Clip):
        chord_value = node.content
        if st.chord_transform is not None:
            chord_value = st.chord_transform(chord_value)
        if st.transpose_offset:
            chord_value = _transpose_chord(chord_value, st.transpose_offset)
        return [
            Voice(
                clip=replace(node, content=chord_value),
                program=st.program,
                bank=st.bank,
                channel=_resolve_channel(st),
                audio_fx=st.audio_fx,
                instrument=st.instrument,
            ),
        ]

    if isinstance(node, Instrument):
        is_drum = node.name == "drums"
        if is_drum:
            channel = 9
        else:
            key = (node.name, node.program, node.bank)
            if key in assigned:
                # Same instrument reused — share its channel so we do
                # not waste one of the 16 MIDI slots.
                channel = assigned[key]
            else:
                channel = next_channel[0] if next_channel[0] != 9 else next_channel[0] + 1
                if channel > 15:
                    # MIDI channels are 4 bits (0-15). Channel 9 is
                    # reserved for percussion, leaving 15 slots for
                    # distinct melodic instruments.
                    raise ValueError(
                        "too many distinct instruments in this piece. "
                        "MIDI supports 16 channels total, with channel "
                        "9 reserved for percussion. That leaves 15 "
                        "melodic instrument slots; flatten() saw a "
                        "16th distinct (name, program, bank) combo and "
                        "would otherwise emit invalid MIDI bytes. "
                        "Reuse the same instrument helper across clips "
                        "instead of giving each one its own.",
                    )
                next_channel[0] = channel + 1
                assigned[key] = channel
        new_state = replace(
            st,
            program=node.program,
            bank=node.bank,
            channel=channel,
            instrument=node.name,
        )
        out: list[FlatNode] = []
        for child in node.children:
            out.extend(_walk(child, new_state, assigned, next_channel))
        return out

    if isinstance(node, Mix):
        out = []
        for child in node.children:
            out.extend(_walk(child, st, assigned, next_channel))
        return out

    if isinstance(node, Effect):
        return _walk_effect(node, st, assigned, next_channel)

    raise TypeError(
        f"unknown node type: {type(node).__name__}. "
        "Expected one of Clip, Instrument, Effect, Mix. "
        "If you wrote a custom node class, update the renderer accordingly.",
    )


def _walk_effect(
    node: Effect,
    st: _State,
    assigned: dict[tuple[str, int, int], int],
    next_channel: list[int],
) -> list[FlatNode]:
    """Apply an Effect's symbolic / audio contributions to the traversal state.

    Both symbolic and audio effects follow the same natural-reading
    convention: the **innermost** effect (closest to the clip) runs
    first, the outermost runs last. Source-code-wise that means
    ``reverb(humanize(piano(...)))`` produces audio that humanizes the
    chord first, synthesizes, then sends through reverb — which is what
    a DAW would do with a serial chain.

    Audio side: the chain stores outer→inner (append on descent), and
    the synthesis pass peels from the inner end. Symbolic side: we
    compose so existing transforms (outer ancestors) run *after* the
    incoming one (inner) when the leaf clip is reached.
    """
    new_state = st

    # Transposition is purely additive so the order doesn't matter.
    if node.transpose_offset:
        new_state = replace(
            new_state,
            transpose_offset=new_state.transpose_offset + node.transpose_offset,
        )

    # Symbolic compose: incoming transform runs FIRST (it is the inner
    # one, closest to the clip), then any outer transforms accumulated
    # earlier from ancestors.
    if node.chord_transform is not None:
        new_state = replace(
            new_state,
            chord_transform=_compose(node.chord_transform, new_state.chord_transform),
        )

    # Audio effects extend the chain so descendants accumulate them.
    # Append rather than prepend so ``audio_fx[0]`` is OUTERMOST and
    # ``audio_fx[-1]`` is innermost; the synthesis pass peels from the
    # innermost end first.
    if node.apply is not None:
        new_state = replace(new_state, audio_fx=(*new_state.audio_fx, node.apply))

    out: list[FlatNode] = []
    for child in node.children:
        out.extend(_walk(child, new_state, assigned, next_channel))
    return out


def _resolve_channel(st: _State) -> int:
    """Pick a channel; default to 0 when no instrument has been seen."""
    if st.channel is not None:
        return st.channel
    return 0


def _compose(first: ChordFn, then: ChordFn | None) -> ChordFn:
    """Return ``then ∘ first``: apply `first` first, then `then`.

    Used by `_walk_effect` to put the innermost (incoming) symbolic
    effect ahead of any outer ones already accumulated. Passing ``None``
    for `then` is a convenience for the very first composition.
    """
    if then is None:
        return first
    return lambda c: then(first(c))


def _transpose_chord(c: Chord, semitones: int) -> Chord:
    """Symbolic transpose: shift every note's pitch by `semitones`."""
    if semitones == 0:
        return c
    new_notes = []
    for n in c.notes:
        midi = (n.octave + 1) * 12 + PITCH_CLASSES.index(n.name) + semitones
        midi = max(0, min(127, midi))
        octave, semi = divmod(midi, 12)
        new_notes.append(
            Note(
                name=PITCH_CLASSES[semi],
                octave=octave - 1,
                duration=n.duration,
                velocity=n.velocity,
                channel=n.channel,
            ),
        )
    return Chord(notes=tuple(new_notes), intervals=c.intervals)


# --- Pass 2: synthesize --------------------------------------------------------


WaveFn = Callable[[float], float]


def synthesize(
    voices: list[FlatNode],
    *,
    sample_rate: int,
    bpm: float,
    waveform: WaveFn,
) -> list[float]:
    """Render the flattened nodes into a mono float buffer in [-1, 1]."""
    if not voices:
        return [0.0]

    spb = 60.0 / bpm

    # Sample nodes need their on-disk audio loaded so we can size the
    # output buffer correctly and mix the samples in.
    sample_buffers: dict[int, list[float]] = {}
    for i, v in enumerate(voices):
        if isinstance(v, SampledVoice):
            sample_buffers[i] = _load_sample(v.sample, sample_rate)

    total_seconds = 0.0
    for i, v in enumerate(voices):
        if isinstance(v, Voice):
            total_seconds = max(total_seconds, _voice_seconds(v, spb))
        else:
            samples_len = len(sample_buffers[i])
            end_seconds = v.sample.at * spb + samples_len / sample_rate
            total_seconds = max(total_seconds, end_seconds)
    total_samples = max(1, round(total_seconds * sample_rate))

    raw_buffers: list[list[float]] = []
    for i, v in enumerate(voices):
        if isinstance(v, Voice):
            raw_buffers.append(
                _render_clip_samples(v, sample_rate, spb, total_samples, waveform),
            )
        else:
            raw_buffers.append(
                _render_sample(v, sample_buffers[i], sample_rate, spb, total_samples),
            )
    return _apply_chains(voices, raw_buffers, sample_rate, bpm)


def _load_sample(s: Sample, sample_rate: int) -> list[float]:
    """Decode `s.path` to mono float samples at `sample_rate`.

    Wav files go through the standard library directly. Other formats
    (mp3/ogg/flac) are converted by ffmpeg into a temp wav first; if
    ffmpeg is missing the call raises with a clear message.
    """
    import shutil
    import struct
    import subprocess
    import tempfile
    import wave
    from pathlib import Path

    src = Path(s.path)
    if not src.exists():
        raise FileNotFoundError(f"sample file not found: {src}")

    suffix = src.suffix.lower().lstrip(".")
    wav_path = src
    cleanup: Path | None = None
    if suffix != "wav":
        if shutil.which("ffmpeg") is None:
            raise RuntimeError(
                f"reading {suffix!r} samples requires ffmpeg on PATH. "
                "Install ffmpeg or convert the file to wav first.",
            )
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as fh:
            wav_path = Path(fh.name)
        cleanup = wav_path
        result = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-loglevel",
                "error",
                "-i",
                str(src),
                "-ac",
                "1",
                "-ar",
                str(sample_rate),
                str(wav_path),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            wav_path.unlink(missing_ok=True)
            raise RuntimeError(
                f"ffmpeg failed to decode {src}:\n{result.stderr.strip()}",
            )

    try:
        with wave.open(str(wav_path), "rb") as w:
            channels = w.getnchannels()
            width = w.getsampwidth()
            in_rate = w.getframerate()
            frames = w.readframes(w.getnframes())
    finally:
        if cleanup is not None:
            cleanup.unlink(missing_ok=True)

    if width == 1:
        # 8-bit unsigned PCM
        raw = [(b - 128) / 128.0 for b in frames]
    elif width == 2:
        count = len(frames) // 2
        raw = [v / 32768.0 for v in struct.unpack(f"<{count}h", frames)]
    elif width == 3:
        # 24-bit packed; rebuild signed 24 then normalize.
        raw = []
        for j in range(0, len(frames), 3):
            b0, b1, b2 = frames[j], frames[j + 1], frames[j + 2]
            v = b0 | (b1 << 8) | (b2 << 16)
            if v & 0x800000:
                v -= 0x1000000
            raw.append(v / 8388608.0)
    elif width == 4:
        count = len(frames) // 4
        raw = [v / 2147483648.0 for v in struct.unpack(f"<{count}i", frames)]
    else:
        raise RuntimeError(f"unsupported wav sample width: {width * 8} bits")

    # Down-mix to mono if needed.
    if channels > 1:
        mono: list[float] = []
        for j in range(0, len(raw), channels):
            mono.append(sum(raw[j : j + channels]) / channels)
        raw = mono

    # Resample to the engine sample rate using simple linear interpolation.
    if in_rate != sample_rate:
        ratio = in_rate / sample_rate
        out_len = int(len(raw) / ratio)
        resampled = [0.0] * out_len
        for j in range(out_len):
            src_pos = j * ratio
            base = int(src_pos)
            frac = src_pos - base
            if base + 1 < len(raw):
                resampled[j] = raw[base] * (1.0 - frac) + raw[base + 1] * frac
            elif base < len(raw):
                resampled[j] = raw[base]
        raw = resampled

    return raw


def _render_sample(
    v: SampledVoice,
    audio: list[float],
    sample_rate: int,
    spb: float,
    total_samples: int,
) -> list[float]:
    """Place `audio` onto a fresh buffer at v.sample.at, scaled by volume.

    `speed` resamples the audio (linear interpolation) so 0.5 plays half
    speed (one octave down) and 2.0 plays double speed (one octave up).
    """
    out = [0.0] * total_samples
    if not audio:
        return out

    start = round(v.sample.at * spb * sample_rate)
    if start >= total_samples:
        return out

    speed = max(0.0001, v.sample.speed)
    volume = v.sample.volume

    if speed == 1.0:
        end = min(start + len(audio), total_samples)
        for i in range(max(0, start), end):
            out[i] = audio[i - start] * volume
        return out

    # Linear-interpolated resampling: source position advances by `speed`
    # each output sample.
    src_pos = 0.0
    for i in range(max(0, start), total_samples):
        if src_pos >= len(audio) - 1:
            break
        base = int(src_pos)
        frac = src_pos - base
        out[i] = (audio[base] * (1.0 - frac) + audio[base + 1] * frac) * volume
        src_pos += speed
    return out


def _voice_seconds(v: Voice, spb: float) -> float:
    cursor = v.clip.at
    end_beat = v.clip.at
    notes = v.clip.content.notes
    intervals = v.clip.content.intervals
    for i, n in enumerate(notes):
        end_beat = max(end_beat, cursor + n.duration)
        if i < len(intervals):
            cursor += intervals[i]
    # Add a small tail so reverb/delay have room to ring out.
    return end_beat * spb + 0.5


def _render_clip_samples(
    v: Voice,
    sample_rate: int,
    spb: float,
    total_samples: int,
    waveform: WaveFn,
) -> list[float]:
    """Synthesize a single voice's clip at its placed time."""
    out = [0.0] * total_samples
    cursor = v.clip.at
    notes = v.clip.content.notes
    intervals = v.clip.content.intervals
    profile = _adsr_for(v.instrument)

    for i, n in enumerate(notes):
        midi = (n.octave + 1) * 12 + PITCH_CLASSES.index(n.name)
        freq = 440.0 * (2.0 ** ((midi - 69) / 12.0))
        amp = max(0, min(127, n.velocity)) / 127.0 * 0.6
        start = round(cursor * spb * sample_rate)
        length = max(1, round(n.duration * spb * sample_rate))
        _render_tone(out, start, length, freq, amp, sample_rate, waveform, profile)
        if i < len(intervals):
            cursor += intervals[i]

    return out


# ADSR profile: attack / decay / sustain-level / release in seconds (or unitless
# for sustain). Different sound families want very different shapes.
@dataclass(frozen=True, slots=True)
class _ADSR:
    attack: float  # seconds to reach full level
    decay: float  # seconds to drop from full to sustain level
    sustain: float  # 0..1, level held during the note
    release: float  # seconds to fade out after note-off

    # `pitch_decay` adds a quick downward pitch sweep at the start of the
    # note (a tenth of a semitone or so) which gives drum-like attacks
    # noticeably more punch. 0 disables it.
    pitch_decay_amount: float = 0.0
    pitch_decay_time: float = 0.01


# Curated profiles tuned by ear for the in-Python additive engine. They
# do not pretend to model real instruments — they just give each role
# the kind of envelope shape that makes a track feel alive.
_ADSR_PROFILES: dict[str, _ADSR] = {
    # Snappy lead synths — hit fast, short sustain so each note speaks.
    "square_lead": _ADSR(0.005, 0.05, 0.7, 0.08),
    "saw_lead": _ADSR(0.005, 0.06, 0.7, 0.10),
    "calliope_lead": _ADSR(0.01, 0.06, 0.7, 0.12),
    "chiff_lead": _ADSR(0.005, 0.05, 0.6, 0.10),
    "charang_lead": _ADSR(0.005, 0.05, 0.7, 0.10),
    "voice_lead": _ADSR(0.02, 0.10, 0.8, 0.20),
    "fifths_lead": _ADSR(0.01, 0.08, 0.7, 0.12),
    "bass_lead": _ADSR(0.005, 0.05, 0.6, 0.10),
    # Pads — slow open, slow close, full sustain to wash everything.
    "new_age_pad": _ADSR(0.40, 0.30, 0.85, 0.80),
    "warm_pad": _ADSR(0.50, 0.40, 0.90, 1.00),
    "polysynth_pad": _ADSR(0.30, 0.30, 0.85, 0.70),
    "choir_pad": _ADSR(0.45, 0.35, 0.90, 0.90),
    "bowed_pad": _ADSR(0.40, 0.30, 0.85, 0.80),
    "metallic_pad": _ADSR(0.20, 0.20, 0.80, 0.60),
    "halo_pad": _ADSR(0.40, 0.30, 0.85, 0.80),
    "sweep_pad": _ADSR(0.50, 0.40, 0.85, 0.90),
    # Bass — pluck attack, fast decay, tight body, almost no release.
    "synth_bass_1": _ADSR(0.003, 0.08, 0.6, 0.05),
    "synth_bass_2": _ADSR(0.003, 0.10, 0.6, 0.06),
    # Sub-bass: instant attack, near-full sustain, slow release. The
    # whole point is to feel the low end ringing through.
    "sub_bass": _ADSR(0.001, 0.05, 0.95, 0.20),
    "finger_bass": _ADSR(0.005, 0.10, 0.5, 0.08),
    "pick_bass": _ADSR(0.003, 0.08, 0.5, 0.06),
    "slap_bass_1": _ADSR(0.002, 0.05, 0.4, 0.04),
    "slap_bass_2": _ADSR(0.002, 0.05, 0.4, 0.04),
    "fretless_bass": _ADSR(0.01, 0.15, 0.6, 0.12),
    "acoustic_bass": _ADSR(0.005, 0.15, 0.5, 0.10),
    # Pianos — fast attack, long decay, no sustain plateau (decay to 0).
    "acoustic_grand": _ADSR(0.003, 1.50, 0.0, 0.30),
    "bright_piano": _ADSR(0.003, 1.20, 0.0, 0.25),
    "electric_piano_1": _ADSR(0.005, 0.80, 0.3, 0.30),
    "electric_piano_2": _ADSR(0.005, 0.80, 0.3, 0.30),
    "harpsichord": _ADSR(0.002, 0.50, 0.0, 0.10),
    "clavinet": _ADSR(0.002, 0.30, 0.0, 0.08),
    # Drums — instant attack, tiny decay, no sustain, quick release.
    # Pitch decay adds the characteristic "thump → boom" of a kick.
    "drums": _ADSR(0.001, 0.05, 0.0, 0.05, pitch_decay_amount=0.5, pitch_decay_time=0.02),
}

# A safe default for instruments without a curated profile.
_DEFAULT_ADSR = _ADSR(attack=0.01, decay=0.10, sustain=0.7, release=0.15)


def _adsr_for(instrument_name: str) -> _ADSR:
    """Return the ADSR envelope tuned for a given instrument label."""
    return _ADSR_PROFILES.get(instrument_name, _DEFAULT_ADSR)


def _render_tone(
    buffer: list[float],
    start: int,
    length: int,
    freq: float,
    amp: float,
    sample_rate: int,
    waveform: WaveFn,
    profile: _ADSR,
) -> None:
    """Render one tone shaped by an ADSR profile.

    `length` is the note-on duration in samples; the release tail
    extends past it. The whole envelope is clamped against the buffer
    so writing past the end is impossible.
    """
    import math

    if length <= 0 or amp <= 0:
        return

    attack_n = max(1, int(profile.attack * sample_rate))
    decay_n = max(1, int(profile.decay * sample_rate))
    release_n = max(1, int(profile.release * sample_rate))
    sustain = max(0.0, min(1.0, profile.sustain))
    total = length + release_n

    # Optional pitch sweep at the attack — gives drums their snap.
    pd_amount = profile.pitch_decay_amount
    pd_samples = max(1, int(profile.pitch_decay_time * sample_rate))

    two_pi = 2.0 * math.pi
    base_step = two_pi * freq / sample_rate
    end = min(start + total, len(buffer))
    if start >= end:
        return

    phase = 0.0
    # Pre-roll: walk to the actual write position so phase is correct
    # even when `start` is before the buffer.
    skip = max(0, -start)
    for _ in range(skip):
        if pd_amount > 0 and _ < pd_samples:
            sweep = 1.0 + pd_amount * (1.0 - _ / pd_samples)
        else:
            sweep = 1.0
        phase += base_step * sweep

    for i in range(max(0, start), end):
        local = i - start
        # Envelope: attack -> decay -> sustain (until note off) -> release
        if local < attack_n:
            env = local / attack_n
        elif local < attack_n + decay_n:
            t = (local - attack_n) / decay_n
            env = 1.0 + (sustain - 1.0) * t
        elif local < length:
            env = sustain
        else:
            t = (local - length) / release_n
            env = sustain * max(0.0, 1.0 - t)

        # Pitch decay during the very start of the note.
        if pd_amount > 0 and local < pd_samples:
            sweep = 1.0 + pd_amount * (1.0 - local / pd_samples)
        else:
            sweep = 1.0
        phase += base_step * sweep
        buffer[i] += amp * env * waveform(phase)


def _apply_chains(
    voices: Sequence[FlatNode],
    buffers: list[list[float]],
    sample_rate: int,
    bpm: float,
) -> list[float]:
    """Walk audio-fx chains scope by scope, summing as we go.

    Algorithm: at every step, group the current entries by their full
    remaining chain. Entries that share the entire chain mix into one
    bus (so two voices both wrapped in the *same* outer reverb meet
    here). Then the deepest chain has its innermost effect (the right
    end, since chains store outer→inner) applied. After peeling one
    layer, the loop repeats — and because we re-group on every pass,
    voices that originally had different inner depths but a shared
    outer wrapper finally meet on that wrapper exactly once.

    `id()` keys each callable by identity so two distinct closures that
    happen to look alike never collapse into one bus by accident.
    """

    def key(chain: AudioFxChain) -> tuple[int, ...]:
        return tuple(id(fn) for fn in chain)

    # Initial entries: one per voice (so different voices that share the
    # full chain still mix correctly via the first regroup pass).
    entries: list[tuple[AudioFxChain, list[float]]] = list(
        zip([v.audio_fx for v in voices], buffers, strict=True),
    )

    while True:
        # Re-group on the current chain so any pair of entries that just
        # became identical (e.g., after peeling an inner reverb) gets
        # merged into a single bus before the next layer is applied.
        groups: dict[tuple[int, ...], tuple[AudioFxChain, list[list[float]]]] = {}
        for chain, buf in entries:
            k = key(chain)
            if k in groups:
                groups[k][1].append(buf)
            else:
                groups[k] = (chain, [buf])
        entries = [(chain, _mix_buffers(bufs)) for chain, bufs in groups.values()]

        # Done when nothing has any chain left to peel.
        max_len = max((len(chain) for chain, _ in entries), default=0)
        if max_len == 0:
            break

        # Peel the innermost effect of the deepest chain. Doing one peel
        # per iteration keeps the regroup step above honest.
        idx = max(range(len(entries)), key=lambda i: len(entries[i][0]))
        chain, bus = entries[idx]
        bus = chain[-1](bus, sample_rate, bpm)
        entries[idx] = (chain[:-1], bus)

    return _mix_buffers([bus for _, bus in entries])


def _mix_buffers(buffers: list[list[float]]) -> list[float]:
    if not buffers:
        return [0.0]
    length = max(len(b) for b in buffers)
    out = [0.0] * length
    for b in buffers:
        for i, v in enumerate(b):
            out[i] += v
    return out


# --- Public convenience -------------------------------------------------------


def render_audio(
    root: Node,
    *,
    bpm: float,
    sample_rate: int,
    waveform: WaveFn,
) -> list[float]:
    """Render a Node tree directly to a mono PCM buffer."""
    voices = flatten(root)
    return synthesize(voices, sample_rate=sample_rate, bpm=bpm, waveform=waveform)
