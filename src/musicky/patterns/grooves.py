"""Drum-groove templates.

Each function returns a list of `Clip` objects covering `bars` bars of
percussion, starting at beat 0. Wrap the result in a drum kit to play:

    drums(*grooves.full(bars=4))

The styles are intentionally generic — nudge them up or down with
`velocity` for dynamics, or splice them together via `seq` of drum kits
with different patterns.
"""

from __future__ import annotations

from musicky.core.node import Clip
from musicky.sounds.drumkit import (
    clap,
    closed_hat,
    crash,
    kick,
    open_hat,
    snare,
)

__all__ = ["break_", "full", "intro", "outro", "sparse"]

BAR = 4.0  # 4 beats per bar


def full(*, bars: int = 4, velocity: int = 100) -> list[Clip]:
    """Driving four-on-the-floor groove with snare on 2 & 4 and 8th hats."""
    out: list[Clip] = []
    for bar in range(bars):
        b = bar * BAR
        for beat in range(4):
            out.append(kick(at=b + beat, velocity=velocity + 15))
        out.append(snare(at=b + 1.0, velocity=velocity))
        out.append(snare(at=b + 3.0, velocity=velocity))
        out.append(clap(at=b + 1.0, velocity=velocity - 20))
        out.append(clap(at=b + 3.0, velocity=velocity - 20))
        for half in range(8):
            out.append(closed_hat(at=b + 0.5 * half, velocity=velocity - 30))
        out.append(open_hat(at=b + 3.5, velocity=velocity - 12))
    return out


def sparse(*, bars: int = 4, velocity: int = 100) -> list[Clip]:
    """Verse-friendly: kick on 1 + 3, snare on 2 + 4, off-beat hats only."""
    out: list[Clip] = []
    for bar in range(bars):
        b = bar * BAR
        out.append(kick(at=b + 0, velocity=velocity + 10))
        out.append(kick(at=b + 2, velocity=velocity + 5))
        out.append(snare(at=b + 1.0, velocity=velocity - 5))
        out.append(snare(at=b + 3.0, velocity=velocity - 5))
        for half in range(1, 8, 2):
            out.append(closed_hat(at=b + 0.5 * half, velocity=velocity - 40))
    return out


def intro(*, bars: int = 4, velocity: int = 70) -> list[Clip]:
    """Hi-hats only — softens the start before the rhythm enters."""
    return [
        closed_hat(at=bar * BAR + 0.5 * half, velocity=velocity)
        for bar in range(bars)
        for half in range(8)
    ]


def break_(*, bars: int = 4, velocity: int = 100) -> list[Clip]:
    """A single crash on the downbeat plus claps that lead into the next bar."""
    out: list[Clip] = [crash(at=0.0, velocity=velocity + 10)]
    for bar in range(bars):
        out.append(clap(at=bar * BAR + 3.5, velocity=velocity - 15))
    return out


def outro(*, bars: int = 2, velocity: int = 90) -> list[Clip]:
    """Half-time fadeout: kicks on 1 + 3, snares on 2 + 4, decreasing velocity."""
    out: list[Clip] = []
    for bar in range(bars):
        b = bar * BAR
        vel = max(20, velocity - bar * 20)
        out.append(kick(at=b + 0, velocity=vel))
        out.append(kick(at=b + 2, velocity=vel - 5))
        out.append(snare(at=b + 1.0, velocity=vel - 10))
        out.append(snare(at=b + 3.0, velocity=vel - 10))
    return out
