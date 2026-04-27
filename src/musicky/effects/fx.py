"""Effect node constructors.

Each constructor builds an `Effect` with its implementation captured as a
closure on the node itself. The renderer invokes ``effect.apply`` (audio)
or ``effect.chord_transform`` (symbolic) directly, with no registry.

This means a custom effect requires no plumbing — the user just writes a
constructor that returns an `Effect` with their own callable:

    def bitcrush(*children: Node, depth: int = 8) -> Effect:
        def apply(samples: list[float], sr: int, _bpm: float) -> list[float]:
            steps = 2 ** depth
            return [round(s * steps) / steps for s in samples]
        return Effect(
            kind="bitcrush", params={"depth": depth},
            children=children, apply=apply,
        )

`master(...)` is a special pass-through: no `apply`, no `chord_transform`,
no `transpose_offset`. The renderer treats it as a transparent group.
"""

from __future__ import annotations

import math
from dataclasses import replace

from musicky._rng import make_rng
from musicky.core.automation import Automation, evaluate
from musicky.core.node import Effect, Node
from musicky.primitives.chord import Chord

__all__ = [
    # symbolic
    "arpeggiate",
    "humanize",
    "quantize",
    "swing",
    "transpose",
    # audio
    "chorus",
    "compressor",
    "delay",
    "distortion",
    "duck",
    "eq",
    "gain",
    "highpass",
    "limiter",
    "lowpass",
    "normalize",
    "reverb",
    "saturate",
    "sidechain",
    "tremolo",
    "vibrato",
    "wobble",
    # grouping
    "master",
]


# --- Symbolic (Chord -> Chord) ------------------------------------------------


def humanize(
    *children: Node,
    timing: float = 0.02,
    velocity: int = 8,
    seed: int | None = None,
) -> Effect:
    """Add small random jitter to timing and velocity (seeded for reproducibility)."""

    def transform(c: Chord) -> Chord:
        r = make_rng(seed)
        new_intervals = tuple(max(0.0, iv + r.uniform(-timing, timing)) for iv in c.intervals)
        new_notes = tuple(
            replace(n, velocity=max(0, min(127, n.velocity + r.randint(-velocity, velocity))))
            for n in c.notes
        )
        return Chord(notes=new_notes, intervals=new_intervals)

    return Effect(
        kind="humanize",
        params={"timing": timing, "velocity": velocity, "seed": seed},
        children=children,
        chord_transform=transform,
    )


def quantize(*children: Node, grid: float = 0.25) -> Effect:
    """Snap note onsets to a grid (in beats). 0.25 = 16th notes at 4/4."""
    if grid <= 0:
        raise ValueError(
            f"quantize grid must be positive, got {grid}. "
            "Typical values: 0.25 (16th), 0.5 (8th), 1.0 (quarter).",
        )

    def transform(c: Chord) -> Chord:
        new_intervals = tuple(round(iv / grid) * grid for iv in c.intervals)
        return Chord(notes=c.notes, intervals=new_intervals)

    return Effect(
        kind="quantize",
        params={"grid": grid},
        children=children,
        chord_transform=transform,
    )


def transpose(*children: Node, semitones: int = 0) -> Effect:
    """Shift every pitch in the children by `semitones` half-steps."""
    return Effect(
        kind="transpose",
        params={"semitones": semitones},
        children=children,
        transpose_offset=semitones,
    )


def swing(*children: Node, amount: float = 0.1) -> Effect:
    """Push every off-beat note slightly later. `amount` is fraction of a beat."""

    def transform(c: Chord) -> Chord:
        shifted: list[float] = []
        for i, iv in enumerate(c.intervals):
            shifted.append(iv + amount if i % 2 == 0 else max(0.0, iv - amount))
        return Chord(notes=c.notes, intervals=tuple(shifted))

    return Effect(
        kind="swing",
        params={"amount": amount},
        children=children,
        chord_transform=transform,
    )


def arpeggiate(*children: Node, interval: float = 0.125) -> Effect:
    """Spread block chords into rising arpeggios with `interval` between notes."""

    def transform(c: Chord) -> Chord:
        if not c.notes:
            return c
        new_intervals = tuple([interval] * (len(c.notes) - 1))
        return Chord(notes=c.notes, intervals=new_intervals)

    return Effect(
        kind="arpeggiate",
        params={"interval": interval},
        children=children,
        chord_transform=transform,
    )


# --- Audio (samples -> samples) -----------------------------------------------


def reverb(*children: Node, amount: float = 0.3, decay: float = 1.5) -> Effect:
    """Simple feedback-delay reverb.

    `amount` is true wet/dry: 0 returns the dry signal unchanged, 1
    returns reverb tail only, intermediate values cross-fade. `decay`
    controls how long the tail rings (in seconds).
    """

    def apply(samples: list[float], sr: int, _bpm: float) -> list[float]:
        if amount <= 0:
            return samples
        delays = [int(sr * t) for t in (0.0297, 0.0371, 0.0411, 0.0437)]
        feedback = max(0.0, min(0.95, 0.7 ** (1.0 / max(0.1, decay))))

        # Build the wet signal as the sum of feedback echoes only. We
        # accumulate into a fresh buffer and read past samples through
        # the original `samples`, so the wet path never contains the
        # dry signal — that lets `amount` mean true wet/dry.
        wet = [0.0] * len(samples)
        for d in delays:
            if d <= 0 or d >= len(samples):
                continue
            gain = feedback
            offset = d
            # Multiple taps per delay line emulate exponential decay.
            while offset < len(samples) and gain > 1e-4:
                for i in range(offset, len(samples)):
                    wet[i] += samples[i - offset] * gain
                offset += d
                gain *= feedback
        return [(1.0 - amount) * s + amount * w for s, w in zip(samples, wet, strict=True)]

    return Effect(
        kind="reverb",
        params={"amount": amount, "decay": decay},
        children=children,
        apply=apply,
    )


def lowpass(
    *children: Node,
    cutoff: float | Automation = 1000.0,
    resonance: float = 0.7,
) -> Effect:
    """One-pole lowpass at `cutoff` Hz.

    `cutoff` may be an `Automation` curve, in which case the filter's
    cutoff sweeps over time — useful for filter-builds and drops.
    """

    def apply(samples: list[float], sr: int, bpm: float) -> list[float]:
        return _onepole_lp_auto(samples, sr, bpm, cutoff)

    return Effect(
        kind="lowpass",
        params={"cutoff": cutoff, "resonance": resonance},
        children=children,
        apply=apply,
    )


def highpass(
    *children: Node,
    cutoff: float | Automation = 200.0,
    resonance: float = 0.7,
) -> Effect:
    """One-pole highpass at `cutoff` Hz.

    `cutoff` may be an `Automation` curve to sweep over time.
    """

    def apply(samples: list[float], sr: int, bpm: float) -> list[float]:
        return _onepole_hp_auto(samples, sr, bpm, cutoff)

    return Effect(
        kind="highpass",
        params={"cutoff": cutoff, "resonance": resonance},
        children=children,
        apply=apply,
    )


def eq(*children: Node, low: float = 0.0, mid: float = 0.0, high: float = 0.0) -> Effect:
    """Three-band shelving EQ. Values are dB gains on each band."""

    def apply(samples: list[float], sr: int, _bpm: float) -> list[float]:
        low_g = _db_to_lin(low)
        mid_g = _db_to_lin(mid)
        high_g = _db_to_lin(high)
        # Crude split: lowpass < 250 Hz, highpass > 4 kHz, the rest is mid.
        low_band = _onepole_lp(samples, sr, 250.0)
        high_band = _onepole_hp(samples, sr, 4000.0)
        mid_band = [s - lo - hi for s, lo, hi in zip(samples, low_band, high_band, strict=True)]
        return [
            low_g * lo + mid_g * mi + high_g * hi
            for lo, mi, hi in zip(low_band, mid_band, high_band, strict=True)
        ]

    return Effect(
        kind="eq",
        params={"low": low, "mid": mid, "high": high},
        children=children,
        apply=apply,
    )


def compressor(
    *children: Node,
    threshold: float = -12.0,
    ratio: float = 4.0,
    attack: float = 0.005,
    release: float = 0.05,
) -> Effect:
    """Static-gain compressor. `threshold` in dBFS; `attack`/`release` in seconds."""

    def apply(samples: list[float], sr: int, _bpm: float) -> list[float]:
        thr = _db_to_lin(threshold)
        r = max(1.0, ratio)
        atk = max(1, int(attack * sr))
        rel = max(1, int(release * sr))
        out = [0.0] * len(samples)
        env = 0.0
        for i, s in enumerate(samples):
            target = abs(s)
            coeff = 1.0 / atk if target > env else 1.0 / rel
            env += (target - env) * coeff
            if env > thr:
                over = env / thr
                gain = 1.0 / (over ** (1.0 - 1.0 / r))
            else:
                gain = 1.0
            out[i] = s * gain
        return out

    return Effect(
        kind="compressor",
        params={"threshold": threshold, "ratio": ratio, "attack": attack, "release": release},
        children=children,
        apply=apply,
    )


def distortion(*children: Node, drive: float = 2.0, mix: float = 1.0) -> Effect:
    """Soft-clipping distortion via tanh."""

    def apply(samples: list[float], _sr: int, _bpm: float) -> list[float]:
        d = max(0.0, drive)
        m = max(0.0, min(1.0, mix))
        return [(1.0 - m) * s + m * math.tanh(d * s) for s in samples]

    return Effect(
        kind="distortion",
        params={"drive": drive, "mix": mix},
        children=children,
        apply=apply,
    )


def delay(
    *children: Node,
    time: float = 0.25,
    feedback: float = 0.4,
    mix: float = 0.3,
) -> Effect:
    """Simple feedback delay line. `time` in seconds."""

    def apply(samples: list[float], sr: int, _bpm: float) -> list[float]:
        t = max(0.0, time)
        fb = max(0.0, min(0.95, feedback))
        m = max(0.0, min(1.0, mix))
        d = max(1, int(t * sr))
        out = list(samples)
        for i in range(d, len(out)):
            out[i] += out[i - d] * fb
        return [(1.0 - m) * s + m * o for s, o in zip(samples, out, strict=True)]

    return Effect(
        kind="delay",
        params={"time": time, "feedback": feedback, "mix": mix},
        children=children,
        apply=apply,
    )


def chorus(*children: Node, rate: float = 1.5, depth: float = 0.005, mix: float = 0.5) -> Effect:
    """Pitch-modulated chorus via a slowly-modulated delay line."""

    def apply(samples: list[float], sr: int, _bpm: float) -> list[float]:
        r = max(0.01, rate)
        d_seconds = max(0.0, depth)
        m = max(0.0, min(1.0, mix))
        base_delay = int(0.02 * sr)
        depth_samples = int(d_seconds * sr)
        out = list(samples)
        for i in range(len(samples)):
            offset = base_delay + int(depth_samples * math.sin(2.0 * math.pi * r * i / sr))
            idx = i - offset
            if 0 <= idx < len(samples):
                out[i] = (1.0 - m) * samples[i] + m * samples[idx]
        return out

    return Effect(
        kind="chorus",
        params={"rate": rate, "depth": depth, "mix": mix},
        children=children,
        apply=apply,
    )


def normalize(*children: Node, peak: float = 0.95) -> Effect:
    """Scale the children so the loudest sample matches `peak` (0-1)."""

    def apply(samples: list[float], _sr: int, _bpm: float) -> list[float]:
        p = max(0.01, min(1.0, peak))
        current = max((abs(s) for s in samples), default=0.0)
        if current <= 0:
            return samples
        scale = p / current
        return [s * scale for s in samples]

    return Effect(
        kind="normalize",
        params={"peak": peak},
        children=children,
        apply=apply,
    )


def limiter(*children: Node, threshold: float = -0.5, release: float = 0.05) -> Effect:
    """Brick-wall limiter at `threshold` dBFS."""

    def apply(samples: list[float], _sr: int, _bpm: float) -> list[float]:
        ceiling = _db_to_lin(threshold)
        out: list[float] = []
        for s in samples:
            if abs(s) > ceiling:
                out.append(ceiling if s > 0 else -ceiling)
            else:
                out.append(s)
        return out

    return Effect(
        kind="limiter",
        params={"threshold": threshold, "release": release},
        children=children,
        apply=apply,
    )


def gain(*children: Node, db: float | Automation = 0.0) -> Effect:
    """Static (or animated) gain change in decibels.

    Positive ``db`` makes the children louder, negative quieter. Pass an
    ``Automation`` curve to sweep gain over time (e.g. for fades).
    """

    def apply(samples: list[float], sr: int, bpm: float) -> list[float]:
        if isinstance(db, (int, float)):
            factor = _db_to_lin(float(db))
            if factor == 1.0:
                return samples
            return [s * factor for s in samples]
        # Automation: evaluate per-sample at the matching beat position.
        spb = 60.0 / max(1.0, bpm)
        out = [0.0] * len(samples)
        for i, s in enumerate(samples):
            beat = (i / sr) / spb
            out[i] = s * _db_to_lin(evaluate(db, beat))
        return out

    return Effect(
        kind="gain",
        params={"db": db},
        children=children,
        apply=apply,
    )


def duck(
    *children: Node,
    by: float = 0.6,
    attack: float = 0.005,
    release: float = 0.18,
    rate: float = 2.0,
) -> Effect:
    """Pumping side-chain compression effect (no external source needed).

    Mimics the classic kick-driven sidechain duck by carving a periodic
    volume dip into the children at ``rate`` Hz. ``by`` is how deep the
    dip goes (0..1, where 0.6 cuts to 40%). ``attack`` is how fast the
    dip drops, ``release`` how fast it recovers — both in seconds.

    This intentionally does not look at any other Node so it stays a
    pure audio effect; the rate matches a four-on-the-floor kick at
    typical dance tempos. Set ``rate`` to ``bpm/60`` for an exact lock.
    """

    def apply(samples: list[float], sr: int, _bpm: float) -> list[float]:
        if by <= 0:
            return samples
        period = max(1, int(sr / max(0.01, rate)))
        atk_n = max(1, int(attack * sr))
        rel_n = max(1, int(release * sr))
        depth = max(0.0, min(1.0, by))

        # Build one period of the duck envelope, then tile it.
        env_period = [1.0] * period
        for i in range(period):
            if i < atk_n:
                # 1.0 -> (1 - depth) along the attack
                env_period[i] = 1.0 - depth * (i / atk_n)
            elif i < atk_n + rel_n:
                # back up to 1.0 along the release
                t = (i - atk_n) / rel_n
                env_period[i] = (1.0 - depth) + depth * t
            else:
                env_period[i] = 1.0

        return [s * env_period[i % period] for i, s in enumerate(samples)]

    return Effect(
        kind="duck",
        params={"by": by, "attack": attack, "release": release, "rate": rate},
        children=children,
        apply=apply,
    )


# --- Grouping -----------------------------------------------------------------


def master(*children: Node) -> Effect:
    """A no-op group. Useful as a visual marker for the final chain."""
    return Effect(kind="master", params={}, children=children)


# --- Internal helpers ---------------------------------------------------------


def _db_to_lin(db: float) -> float:
    """Convert a dB gain to a linear scale factor."""
    return float(10.0 ** (db / 20.0))


def _onepole_lp(samples: list[float], sr: int, cutoff: float) -> list[float]:
    """One-pole lowpass shared by `lowpass` and `eq`."""
    rc = 1.0 / (2.0 * math.pi * cutoff)
    dt = 1.0 / sr
    alpha = dt / (rc + dt)
    out = [0.0] * len(samples)
    prev = 0.0
    for i, s in enumerate(samples):
        prev = prev + alpha * (s - prev)
        out[i] = prev
    return out


def _onepole_hp(samples: list[float], sr: int, cutoff: float) -> list[float]:
    """One-pole highpass shared by `highpass` and `eq`."""
    rc = 1.0 / (2.0 * math.pi * cutoff)
    dt = 1.0 / sr
    alpha = rc / (rc + dt)
    out = [0.0] * len(samples)
    prev_s = 0.0
    prev_o = 0.0
    for i, s in enumerate(samples):
        prev_o = alpha * (prev_o + s - prev_s)
        prev_s = s
        out[i] = prev_o
    return out


def _onepole_lp_auto(
    samples: list[float],
    sr: int,
    bpm: float,
    cutoff: float | Automation,
) -> list[float]:
    """One-pole lowpass with optional Automation on the cutoff frequency."""
    if not isinstance(cutoff, Automation):
        return _onepole_lp(samples, sr, float(cutoff))
    spb = 60.0 / max(1.0, bpm)
    dt = 1.0 / sr
    out = [0.0] * len(samples)
    prev = 0.0
    for i, s in enumerate(samples):
        beat = (i * dt) / spb
        cf = max(1.0, evaluate(cutoff, beat))
        rc = 1.0 / (2.0 * math.pi * cf)
        alpha = dt / (rc + dt)
        prev = prev + alpha * (s - prev)
        out[i] = prev
    return out


def _onepole_hp_auto(
    samples: list[float],
    sr: int,
    bpm: float,
    cutoff: float | Automation,
) -> list[float]:
    """One-pole highpass with optional Automation on the cutoff."""
    if not isinstance(cutoff, Automation):
        return _onepole_hp(samples, sr, float(cutoff))
    spb = 60.0 / max(1.0, bpm)
    dt = 1.0 / sr
    out = [0.0] * len(samples)
    prev_s = 0.0
    prev_o = 0.0
    for i, s in enumerate(samples):
        beat = (i * dt) / spb
        cf = max(1.0, evaluate(cutoff, beat))
        rc = 1.0 / (2.0 * math.pi * cf)
        alpha = rc / (rc + dt)
        prev_o = alpha * (prev_o + s - prev_s)
        prev_s = s
        out[i] = prev_o
    return out


# --- LFO-driven movement ------------------------------------------------------


def vibrato(*children: Node, rate: float = 5.0, depth: float = 0.005) -> Effect:
    """Pitch wobble via fractional-delay LFO.

    `rate` is the LFO frequency in Hz, `depth` is in seconds (typical
    values 0.001-0.01 = a few cents to about a quartertone).
    """

    def apply(samples: list[float], sr: int, _bpm: float) -> list[float]:
        d = max(0.0, depth)
        max_off = max(1, int(d * sr) + 1)
        out = [0.0] * len(samples)
        for i, _s in enumerate(samples):
            lfo = math.sin(2.0 * math.pi * rate * i / sr)
            offset = lfo * d * sr
            src = i - max_off + offset
            base = int(src)
            frac = src - base
            if 0 <= base < len(samples) - 1:
                out[i] = samples[base] * (1.0 - frac) + samples[base + 1] * frac
            elif 0 <= base < len(samples):
                out[i] = samples[base]
        return out

    return Effect(
        kind="vibrato",
        params={"rate": rate, "depth": depth},
        children=children,
        apply=apply,
    )


def tremolo(*children: Node, rate: float = 5.0, depth: float = 0.5) -> Effect:
    """Volume LFO. `depth` 0..1 (0 leaves the signal alone, 1 full duck)."""

    def apply(samples: list[float], sr: int, _bpm: float) -> list[float]:
        d = max(0.0, min(1.0, depth))
        out = [0.0] * len(samples)
        for i, s in enumerate(samples):
            lfo = math.sin(2.0 * math.pi * rate * i / sr)
            # Map LFO from [-1,1] to [1-d, 1].
            env = 1.0 - d * (0.5 - 0.5 * lfo)
            out[i] = s * env
        return out

    return Effect(
        kind="tremolo",
        params={"rate": rate, "depth": depth},
        children=children,
        apply=apply,
    )


def wobble(
    *children: Node,
    rate: float = 2.0,
    low: float = 200.0,
    high: float = 4000.0,
) -> Effect:
    """Lowpass cutoff swept by a triangle LFO between `low` and `high` Hz.

    The classic "wub" of dub/dubstep basses. The LFO uses a triangle
    rather than sine so the sweep feels more linear.
    """

    def apply(samples: list[float], sr: int, _bpm: float) -> list[float]:
        out = [0.0] * len(samples)
        prev = 0.0
        dt = 1.0 / sr
        for i, s in enumerate(samples):
            phase = (rate * i / sr) % 1.0
            tri = 1.0 - abs(2.0 * phase - 1.0)  # 0..1..0
            cf = low + (high - low) * tri
            rc = 1.0 / (2.0 * math.pi * cf)
            alpha = dt / (rc + dt)
            prev = prev + alpha * (s - prev)
            out[i] = prev
        return out

    return Effect(
        kind="wobble",
        params={"rate": rate, "low": low, "high": high},
        children=children,
        apply=apply,
    )


# --- Saturation ---------------------------------------------------------------


def saturate(*children: Node, amount: float = 1.5, warmth: float = 0.5) -> Effect:
    """Soft tube/tape saturation.

    `amount` boosts the input before a gentle tanh curve so harmonics
    bloom on the loud parts; `warmth` (0..1) blends in a slight even-
    harmonic emphasis that thickens bass without changing pitch.
    """

    def apply(samples: list[float], _sr: int, _bpm: float) -> list[float]:
        a = max(0.0, amount)
        w = max(0.0, min(1.0, warmth))
        out: list[float] = []
        for s in samples:
            driven = math.tanh(a * s)
            even = w * driven * driven * (1.0 if s >= 0 else -1.0)
            out.append(driven + 0.4 * even)
        return out

    return Effect(
        kind="saturate",
        params={"amount": amount, "warmth": warmth},
        children=children,
        apply=apply,
    )


# --- Signal-driven sidechain --------------------------------------------------


def sidechain(
    *children: Node,
    source: Node,
    amount: float = 0.7,
    attack: float = 0.005,
    release: float = 0.18,
    threshold: float = 0.05,
) -> Effect:
    """Duck `children` whenever `source` produces signal (true sidechain).

    The renderer runs `source` through the sine engine to detect its
    envelope, then ducks the children's samples by up to `amount` (0..1)
    whenever the source envelope exceeds `threshold`. This is what makes
    a kick "punch through" a bass in club music.

    Note: the source is rendered with the sine engine internally so
    its envelope is shape-accurate even though the user never hears it.
    """
    from musicky.core.piece import musicky as _musicky
    from musicky.out.synth import sine_engine

    # Pre-render the source once, lazily on first apply call so the
    # bpm/sr come from the current rendering pass.
    cache: dict[tuple[int, float], list[float]] = {}

    def env_of(sr: int, bpm: float) -> list[float]:
        key = (sr, bpm)
        if key in cache:
            return cache[key]
        rendered = sine_engine(_musicky(source, bpm=bpm), sr)
        # Crude envelope follower: rectify + onepole smoother.
        atk_n = max(1, int(attack * sr))
        rel_n = max(1, int(release * sr))
        env = [0.0] * len(rendered)
        e = 0.0
        for i, s in enumerate(rendered):
            target = abs(s)
            coeff = 1.0 / atk_n if target > e else 1.0 / rel_n
            e += (target - e) * coeff
            env[i] = e
        cache[key] = env
        return env

    def apply(samples: list[float], sr: int, bpm: float) -> list[float]:
        if amount <= 0:
            return samples
        env = env_of(sr, bpm)
        peak = max(env, default=0.0) or 1.0
        out = [0.0] * len(samples)
        for i, s in enumerate(samples):
            level = env[i] / peak if i < len(env) else 0.0
            # Above threshold -> linearly duck up to `amount`.
            duck_amt = max(0.0, min(1.0, (level - threshold) / max(1e-6, 1.0 - threshold)))
            gain_factor = 1.0 - amount * duck_amt
            out[i] = s * gain_factor
        return out

    return Effect(
        kind="sidechain",
        params={
            "amount": amount,
            "attack": attack,
            "release": release,
            "threshold": threshold,
        },
        children=children,
        apply=apply,
    )
