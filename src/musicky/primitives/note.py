"""Note primitive: a single pitched event.

A `Note` carries a pitch class (C, C#, ... B), an octave, a duration in beats,
a MIDI velocity (0-127) and an optional MIDI channel. It is fully immutable;
use `dataclasses.replace` (re-exported as `musicky.replace`) to derive a new
note with changed fields.

The pitch class set is canonical (sharps). Flats parsed by `note("Eb4")` are
internally normalized to their sharp equivalent so that equality and MIDI
conversion are total.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "PITCH_CLASSES",
    "Note",
    "from_pitch",
    "is_enharmonic",
    "n",
    "note",
    "pitch",
]

# Sharps-only canonical order. Index in this tuple is the semitone offset
# from C within an octave, which is exactly the value MIDI uses.
PITCH_CLASSES: tuple[str, ...] = (
    "C",
    "C#",
    "D",
    "D#",
    "E",
    "F",
    "F#",
    "G",
    "G#",
    "A",
    "A#",
    "B",
)

# Map of every accepted pitch spelling (sharps and flats) to its canonical
# sharp form. Built once at import time.
_PITCH_LOOKUP: dict[str, str] = {p: p for p in PITCH_CLASSES} | {
    "Db": "C#",
    "Eb": "D#",
    "Fb": "E",
    "Gb": "F#",
    "Ab": "G#",
    "Bb": "A#",
    "Cb": "B",
    # Useful but rare: double accidentals are intentionally not supported.
    "E#": "F",
    "B#": "C",
}


@dataclass(frozen=True, slots=True)
class Note:
    """An immutable note value."""

    name: str  # canonical pitch class (always one of PITCH_CLASSES)
    octave: int  # standard MIDI octave; middle C = C4 = MIDI 60
    duration: float  # length in beats (1.0 = quarter at 4/4)
    velocity: int  # MIDI velocity 0-127
    channel: int | None  # MIDI channel; None means "inherit from track"


def note(
    spec: str | int,
    *,
    duration: float = 0.25,
    velocity: int = 100,
    channel: int | None = None,
) -> Note:
    """Build a Note from ``"C5"`` (preferred) or a MIDI pitch number.

    note("C5")     # human-readable
    note(72)       # same pitch, useful when computed at runtime
    """
    if isinstance(spec, int):
        return from_pitch(spec, duration=duration, velocity=velocity, channel=channel)

    name, octave = _parse_spec(spec)
    return Note(
        name=name,
        octave=octave,
        duration=duration,
        velocity=velocity,
        channel=channel,
    )


def n(spec: str, *, duration: float = 0.25, velocity: int = 100) -> Note:
    """Short alias for `note`. Mirrors musicpy's ``N('C5')`` shorthand."""
    return note(spec, duration=duration, velocity=velocity)


def pitch(value: Note) -> int:
    """Return the absolute MIDI pitch number (0-127) of a Note.

    MIDI defines C-1 as pitch 0 and middle C (C4) as pitch 60, so the
    formula is ``(octave + 1) * 12 + semitone``.
    """
    return (value.octave + 1) * 12 + PITCH_CLASSES.index(value.name)


def from_pitch(
    midi: int,
    *,
    duration: float = 0.25,
    velocity: int = 100,
    channel: int | None = None,
) -> Note:
    """Inverse of `pitch`: build a Note from a MIDI pitch number."""
    if not 0 <= midi <= 127:
        raise ValueError(
            f"MIDI pitch out of range: {midi}. Valid range is 0 (C-1) through 127 (G9).",
        )
    octave, semitone = divmod(midi, 12)
    return Note(
        name=PITCH_CLASSES[semitone],
        octave=octave - 1,
        duration=duration,
        velocity=velocity,
        channel=channel,
    )


def is_enharmonic(a: Note, b: Note) -> bool:
    """True when both notes sound the same (same MIDI pitch)."""
    return pitch(a) == pitch(b)


def _parse_spec(spec: str) -> tuple[str, int]:
    """Split ``"C#5"`` / ``"Eb-1"`` into (canonical name, octave).

    Octave is always the trailing signed integer; the rest is the pitch
    spelling. We do not allow whitespace because the call site uses single
    notes; multi-note parsing belongs in `chord`.
    """
    s = spec.strip()
    # Walk from the right while characters look like part of a signed int.
    i = len(s)
    while i > 0 and (s[i - 1].isdigit() or (s[i - 1] == "-" and i == len(s) - 1)):
        i -= 1
    name_part, octave_part = s[:i], s[i:]
    if not name_part or not octave_part:
        raise ValueError(
            f"invalid note spec: {spec!r}. "
            "Expected format like 'C4', 'C#5', 'Eb3', 'C-1'. "
            "A pitch name (with optional sharp/flat) followed by an octave number is required.",
        )
    canonical = _PITCH_LOOKUP.get(name_part)
    if canonical is None:
        raise ValueError(
            f"unknown pitch class: {name_part!r} in spec {spec!r}. "
            f"Allowed pitches: {sorted(_PITCH_LOOKUP)}.",
        )
    try:
        octave = int(octave_part)
    except ValueError as exc:
        raise ValueError(
            f"invalid octave {octave_part!r} in spec {spec!r}. Expected an integer like 4, -1, 0.",
        ) from exc
    return canonical, octave
