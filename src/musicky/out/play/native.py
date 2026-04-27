"""Native context: send MIDI events to a local fluidsynth instance.

This backend uses ``pyfluidsynth`` to drive a soft synth in-process. It
needs both the Python binding and the underlying ``libfluidsynth`` shared
library plus a SoundFont (.sf2) file. Install with::

    pip install musicky[native]

The default behavior plays note-by-note in real time using time.sleep,
which keeps the implementation simple and dependency-free beyond the
synth itself.
"""

from __future__ import annotations

import contextlib
import time
from typing import Any

from musicky.core.piece import Piece
from musicky.core.render import Voice, flatten
from musicky.out.play.context import Context
from musicky.primitives.note import PITCH_CLASSES

__all__ = ["create_native_context"]


def create_native_context(
    soundfont: str,
    *,
    driver: str | None = None,
    gain: float = 0.5,
    block: bool = True,
) -> Context:
    """Build a Context that plays Pieces through fluidsynth.

    `soundfont` is the path to an .sf2 file. `driver` selects the audio
    backend (e.g. ``"alsa"``, ``"coreaudio"``, ``"dsound"``); the default
    asks fluidsynth to pick one. `block` mirrors the pygame context: when
    True (default) `render` waits for playback to finish.
    """
    fluidsynth = _import_fluidsynth()

    fs = fluidsynth.Synth(gain=gain)
    fs.start(driver=driver) if driver else fs.start()
    sfid = fs.sfload(soundfont)
    if sfid == -1:
        # fluidsynth's binding signals failure with -1 instead of raising.
        # Surface a clear FileNotFoundError so callers see the problem
        # right away rather than silently producing dead audio later.
        raise FileNotFoundError(
            f"fluidsynth could not load SoundFont {soundfont!r}. "
            "Check that the file exists and is a valid .sf2/.sf3.",
        )

    def render(music: Piece) -> None:
        # Flatten the Node tree to a list of voices, then play each one
        # in sequence. Polyphony across voices is approximated rather
        # than actual; for a more faithful playback render to MIDI and
        # use a sequencer that respects the timeline.
        seconds_per_beat = 60.0 / music.bpm
        total_wait = 0.0

        for v in flatten(music.root):
            # Sample nodes are not playable through fluidsynth's
            # program-select path; rendering through `output(...)` is
            # the place to mix file-based audio in.
            if not isinstance(v, Voice):
                continue
            # Pass v.bank so kits like tr808 select the right SoundFont
            # preset, matching what MIDI export would emit.
            fs.program_select(v.channel, sfid, v.bank, v.program)
            cursor_beats = v.clip.at
            for i, note_value in enumerate(v.clip.content.notes):
                midi_pitch = (note_value.octave + 1) * 12 + PITCH_CLASSES.index(note_value.name)
                midi_pitch = max(0, min(127, midi_pitch))
                velocity = max(0, min(127, note_value.velocity))

                fs.noteon(v.channel, midi_pitch, velocity)
                hold = note_value.duration * seconds_per_beat
                if block:
                    time.sleep(hold)
                fs.noteoff(v.channel, midi_pitch)
                total_wait += hold

                if i < len(v.clip.content.intervals):
                    gap = v.clip.content.intervals[i] * seconds_per_beat
                    if block:
                        time.sleep(gap)
                    cursor_beats += v.clip.content.intervals[i]

        if not block:
            # Best-effort: keep the synth alive long enough to drain.
            time.sleep(total_wait)

    def close() -> None:
        # Best-effort cleanup; the underlying C library may already be torn down.
        with contextlib.suppress(Exception):
            fs.delete()

    return Context(render=render, close=close)


def _import_fluidsynth() -> Any:
    """Lazy import; raise an actionable error if pyfluidsynth is missing."""
    try:
        import fluidsynth  # type: ignore[import-untyped]
    except ImportError as exc:  # pragma: no cover - exercised via env
        raise ImportError(
            "pyfluidsynth is required for create_native_context(). "
            "It is part of the core dependencies of musicky; "
            "reinstall with `pip install musicky` if it went missing.",
        ) from exc
    return fluidsynth
