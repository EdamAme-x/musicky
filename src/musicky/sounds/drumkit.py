"""Drum-element helpers: shorthand for individual GM percussion notes.

GM Drum Map assigns each percussion sound to a fixed MIDI pitch on
channel 9. Writing those pitches by hand is error-prone (was C2 the
kick or the bass tom?), so this module exposes one helper per common
element. Each helper returns a `Clip` so it slots into the timeline
machinery without ceremony:

    drums(
        seq(
            kick(),
            snare(),
            kick(),
            snare(),
        ),
    )

Helpers accept duration and velocity defaults plus the placement keyword
``at=``, so a busy hi-hat pattern reads without noise:

    closed_hat(at=0, velocity=80)
    closed_hat(at=0.25, velocity=60)
"""

from __future__ import annotations

from musicky.core.node import Clip, clip
from musicky.primitives.chord import Chord
from musicky.primitives.note import Note

__all__ = [
    # bass
    "kick",
    "kick2",
    "side_stick",
    # snare / clap
    "snare",
    "snare2",
    "clap",
    "rim",
    # hat
    "closed_hat",
    "pedal_hat",
    "open_hat",
    # cymbal
    "crash",
    "crash2",
    "ride",
    "ride_bell",
    "splash",
    "china",
    # tom
    "low_tom",
    "low_mid_tom",
    "mid_tom",
    "high_mid_tom",
    "high_tom",
    "low_floor",
    "high_floor",
    # latin / ethnic / hand percussion
    "tambourine",
    "cowbell",
    "vibraslap",
    "low_bongo",
    "high_bongo",
    "mute_conga",
    "open_conga",
    "low_conga",
    "low_timbale",
    "high_timbale",
    "low_agogo",
    "high_agogo",
    "shaker",
    "cabasa",
    "maracas",
    "short_whistle",
    "long_whistle",
    "short_guiro",
    "long_guiro",
    "claves",
    "wood_block_high",
    "wood_block_low",
    "mute_cuica",
    "open_cuica",
    "mute_triangle",
    "open_triangle",
    # generic
    "hit",
]

_PITCH_NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")


def _drum_clip(midi: int, *, at: float, duration: float, velocity: int) -> Clip:
    """Build a single-note clip on channel 9 at the given MIDI pitch."""
    octave, semi = divmod(midi, 12)
    note = Note(
        name=_PITCH_NAMES[semi],
        octave=octave - 1,
        duration=duration,
        velocity=max(0, min(127, velocity)),
        channel=9,
    )
    return clip(Chord(notes=(note,), intervals=()), at=at)


def hit(pitch: int, *, at: float = 0.0, duration: float = 0.25, velocity: int = 100) -> Clip:
    """Play any drum-map MIDI pitch directly.

    Use this when the named helpers do not cover the sound you need
    (some kits expose extra notes outside the GM drum map). For the
    common cases prefer the named helpers like `kick`, `snare`, etc.
    """
    if not 0 <= pitch <= 127:
        raise ValueError(
            f"drum pitch out of range: {pitch}. Valid MIDI pitches are 0-127.",
        )
    return _drum_clip(pitch, at=at, duration=duration, velocity=velocity)


# --- Named helpers ------------------------------------------------------------
# Each helper is a one-line wrapper around _drum_clip with a fixed pitch.
# Defining them explicitly (rather than via globals() loops) keeps mypy
# and IDE auto-completion happy.


def kick(*, at: float = 0.0, duration: float = 0.25, velocity: int = 100) -> Clip:
    """GM Bass Drum 1 (pitch 36). The standard kick."""
    return _drum_clip(36, at=at, duration=duration, velocity=velocity)


def kick2(*, at: float = 0.0, duration: float = 0.25, velocity: int = 100) -> Clip:
    """GM Acoustic Bass Drum (pitch 35). Deeper than `kick`."""
    return _drum_clip(35, at=at, duration=duration, velocity=velocity)


def side_stick(*, at: float = 0.0, duration: float = 0.25, velocity: int = 100) -> Clip:
    """GM Side Stick / Rimshot (pitch 37)."""
    return _drum_clip(37, at=at, duration=duration, velocity=velocity)


def snare(*, at: float = 0.0, duration: float = 0.25, velocity: int = 100) -> Clip:
    """GM Acoustic Snare (pitch 38)."""
    return _drum_clip(38, at=at, duration=duration, velocity=velocity)


def snare2(*, at: float = 0.0, duration: float = 0.25, velocity: int = 100) -> Clip:
    """GM Electric Snare (pitch 40)."""
    return _drum_clip(40, at=at, duration=duration, velocity=velocity)


def clap(*, at: float = 0.0, duration: float = 0.25, velocity: int = 100) -> Clip:
    """GM Hand Clap (pitch 39)."""
    return _drum_clip(39, at=at, duration=duration, velocity=velocity)


def rim(*, at: float = 0.0, duration: float = 0.25, velocity: int = 100) -> Clip:
    """Alias of `side_stick` (GM pitch 37)."""
    return _drum_clip(37, at=at, duration=duration, velocity=velocity)


def closed_hat(*, at: float = 0.0, duration: float = 0.25, velocity: int = 100) -> Clip:
    """GM Closed Hi-Hat (pitch 42)."""
    return _drum_clip(42, at=at, duration=duration, velocity=velocity)


def pedal_hat(*, at: float = 0.0, duration: float = 0.25, velocity: int = 100) -> Clip:
    """GM Pedal Hi-Hat (pitch 44)."""
    return _drum_clip(44, at=at, duration=duration, velocity=velocity)


def open_hat(*, at: float = 0.0, duration: float = 0.25, velocity: int = 100) -> Clip:
    """GM Open Hi-Hat (pitch 46)."""
    return _drum_clip(46, at=at, duration=duration, velocity=velocity)


def crash(*, at: float = 0.0, duration: float = 0.25, velocity: int = 100) -> Clip:
    """GM Crash Cymbal 1 (pitch 49)."""
    return _drum_clip(49, at=at, duration=duration, velocity=velocity)


def crash2(*, at: float = 0.0, duration: float = 0.25, velocity: int = 100) -> Clip:
    """GM Crash Cymbal 2 (pitch 57)."""
    return _drum_clip(57, at=at, duration=duration, velocity=velocity)


def ride(*, at: float = 0.0, duration: float = 0.25, velocity: int = 100) -> Clip:
    """GM Ride Cymbal 1 (pitch 51)."""
    return _drum_clip(51, at=at, duration=duration, velocity=velocity)


def ride_bell(*, at: float = 0.0, duration: float = 0.25, velocity: int = 100) -> Clip:
    """GM Ride Bell (pitch 53)."""
    return _drum_clip(53, at=at, duration=duration, velocity=velocity)


def splash(*, at: float = 0.0, duration: float = 0.25, velocity: int = 100) -> Clip:
    """GM Splash Cymbal (pitch 55)."""
    return _drum_clip(55, at=at, duration=duration, velocity=velocity)


def china(*, at: float = 0.0, duration: float = 0.25, velocity: int = 100) -> Clip:
    """GM Chinese Cymbal (pitch 52)."""
    return _drum_clip(52, at=at, duration=duration, velocity=velocity)


def low_tom(*, at: float = 0.0, duration: float = 0.25, velocity: int = 100) -> Clip:
    """GM Low Tom (pitch 45)."""
    return _drum_clip(45, at=at, duration=duration, velocity=velocity)


def low_mid_tom(*, at: float = 0.0, duration: float = 0.25, velocity: int = 100) -> Clip:
    """GM Low-Mid Tom (pitch 47)."""
    return _drum_clip(47, at=at, duration=duration, velocity=velocity)


def mid_tom(*, at: float = 0.0, duration: float = 0.25, velocity: int = 100) -> Clip:
    """GM Hi-Mid Tom (pitch 48)."""
    return _drum_clip(48, at=at, duration=duration, velocity=velocity)


def high_mid_tom(*, at: float = 0.0, duration: float = 0.25, velocity: int = 100) -> Clip:
    """GM High Tom (pitch 50)."""
    return _drum_clip(50, at=at, duration=duration, velocity=velocity)


def high_tom(*, at: float = 0.0, duration: float = 0.25, velocity: int = 100) -> Clip:
    """Alias of `high_mid_tom` (GM pitch 50)."""
    return _drum_clip(50, at=at, duration=duration, velocity=velocity)


def low_floor(*, at: float = 0.0, duration: float = 0.25, velocity: int = 100) -> Clip:
    """GM Low Floor Tom (pitch 41)."""
    return _drum_clip(41, at=at, duration=duration, velocity=velocity)


def high_floor(*, at: float = 0.0, duration: float = 0.25, velocity: int = 100) -> Clip:
    """GM High Floor Tom (pitch 43)."""
    return _drum_clip(43, at=at, duration=duration, velocity=velocity)


def tambourine(*, at: float = 0.0, duration: float = 0.25, velocity: int = 100) -> Clip:
    """GM Tambourine (pitch 54)."""
    return _drum_clip(54, at=at, duration=duration, velocity=velocity)


def cowbell(*, at: float = 0.0, duration: float = 0.25, velocity: int = 100) -> Clip:
    """GM Cowbell (pitch 56)."""
    return _drum_clip(56, at=at, duration=duration, velocity=velocity)


def vibraslap(*, at: float = 0.0, duration: float = 0.25, velocity: int = 100) -> Clip:
    """GM Vibraslap (pitch 58)."""
    return _drum_clip(58, at=at, duration=duration, velocity=velocity)


def low_bongo(*, at: float = 0.0, duration: float = 0.25, velocity: int = 100) -> Clip:
    """GM Low Bongo (pitch 61)."""
    return _drum_clip(61, at=at, duration=duration, velocity=velocity)


def high_bongo(*, at: float = 0.0, duration: float = 0.25, velocity: int = 100) -> Clip:
    """GM High Bongo (pitch 60)."""
    return _drum_clip(60, at=at, duration=duration, velocity=velocity)


def mute_conga(*, at: float = 0.0, duration: float = 0.25, velocity: int = 100) -> Clip:
    """GM Mute Hi Conga (pitch 62)."""
    return _drum_clip(62, at=at, duration=duration, velocity=velocity)


def open_conga(*, at: float = 0.0, duration: float = 0.25, velocity: int = 100) -> Clip:
    """GM Open Hi Conga (pitch 63)."""
    return _drum_clip(63, at=at, duration=duration, velocity=velocity)


def low_conga(*, at: float = 0.0, duration: float = 0.25, velocity: int = 100) -> Clip:
    """GM Low Conga (pitch 64)."""
    return _drum_clip(64, at=at, duration=duration, velocity=velocity)


def low_timbale(*, at: float = 0.0, duration: float = 0.25, velocity: int = 100) -> Clip:
    """GM Low Timbale (pitch 66)."""
    return _drum_clip(66, at=at, duration=duration, velocity=velocity)


def high_timbale(*, at: float = 0.0, duration: float = 0.25, velocity: int = 100) -> Clip:
    """GM High Timbale (pitch 65)."""
    return _drum_clip(65, at=at, duration=duration, velocity=velocity)


def low_agogo(*, at: float = 0.0, duration: float = 0.25, velocity: int = 100) -> Clip:
    """GM Low Agogo (pitch 68)."""
    return _drum_clip(68, at=at, duration=duration, velocity=velocity)


def high_agogo(*, at: float = 0.0, duration: float = 0.25, velocity: int = 100) -> Clip:
    """GM High Agogo (pitch 67)."""
    return _drum_clip(67, at=at, duration=duration, velocity=velocity)


def shaker(*, at: float = 0.0, duration: float = 0.25, velocity: int = 100) -> Clip:
    """Alias of `maracas` (GM pitch 70).

    GM Drum Map has no dedicated "shaker" slot, so the common name is
    mapped to Maracas. Sounds identical to ``maracas()`` — pick whichever
    name reads better in your code. Some SoundFont kits may have a
    distinct shaker sample on a different note; route there with
    ``hit(pitch=...)`` if needed.
    """
    return _drum_clip(70, at=at, duration=duration, velocity=velocity)


def cabasa(*, at: float = 0.0, duration: float = 0.25, velocity: int = 100) -> Clip:
    """GM Cabasa (pitch 69)."""
    return _drum_clip(69, at=at, duration=duration, velocity=velocity)


def maracas(*, at: float = 0.0, duration: float = 0.25, velocity: int = 100) -> Clip:
    """GM Maracas (pitch 70)."""
    return _drum_clip(70, at=at, duration=duration, velocity=velocity)


def short_whistle(*, at: float = 0.0, duration: float = 0.25, velocity: int = 100) -> Clip:
    """GM Short Whistle (pitch 71)."""
    return _drum_clip(71, at=at, duration=duration, velocity=velocity)


def long_whistle(*, at: float = 0.0, duration: float = 0.25, velocity: int = 100) -> Clip:
    """GM Long Whistle (pitch 72)."""
    return _drum_clip(72, at=at, duration=duration, velocity=velocity)


def short_guiro(*, at: float = 0.0, duration: float = 0.25, velocity: int = 100) -> Clip:
    """GM Short Guiro (pitch 73)."""
    return _drum_clip(73, at=at, duration=duration, velocity=velocity)


def long_guiro(*, at: float = 0.0, duration: float = 0.25, velocity: int = 100) -> Clip:
    """GM Long Guiro (pitch 74)."""
    return _drum_clip(74, at=at, duration=duration, velocity=velocity)


def claves(*, at: float = 0.0, duration: float = 0.25, velocity: int = 100) -> Clip:
    """GM Claves (pitch 75)."""
    return _drum_clip(75, at=at, duration=duration, velocity=velocity)


def wood_block_high(*, at: float = 0.0, duration: float = 0.25, velocity: int = 100) -> Clip:
    """GM Hi Wood Block (pitch 76)."""
    return _drum_clip(76, at=at, duration=duration, velocity=velocity)


def wood_block_low(*, at: float = 0.0, duration: float = 0.25, velocity: int = 100) -> Clip:
    """GM Low Wood Block (pitch 77)."""
    return _drum_clip(77, at=at, duration=duration, velocity=velocity)


def mute_cuica(*, at: float = 0.0, duration: float = 0.25, velocity: int = 100) -> Clip:
    """GM Mute Cuica (pitch 78)."""
    return _drum_clip(78, at=at, duration=duration, velocity=velocity)


def open_cuica(*, at: float = 0.0, duration: float = 0.25, velocity: int = 100) -> Clip:
    """GM Open Cuica (pitch 79)."""
    return _drum_clip(79, at=at, duration=duration, velocity=velocity)


def mute_triangle(*, at: float = 0.0, duration: float = 0.25, velocity: int = 100) -> Clip:
    """GM Mute Triangle (pitch 80)."""
    return _drum_clip(80, at=at, duration=duration, velocity=velocity)


def open_triangle(*, at: float = 0.0, duration: float = 0.25, velocity: int = 100) -> Clip:
    """GM Open Triangle (pitch 81)."""
    return _drum_clip(81, at=at, duration=duration, velocity=velocity)
