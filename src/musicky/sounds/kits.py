"""Drum-kit node constructors.

A drum kit is just an `Instrument` pinned to MIDI channel 9 with a
specific bank number. SoundFonts and hardware GS/XG synths use the bank
number to switch between kits while the program stays at 0.

The bank numbers below match the Roland GS / SC-88 conventions which
are what most General-purpose SoundFonts (FluidR3, GeneralUser GS, etc.)
ship with. Some banks are commonly extended by individual SoundFont
authors and may be empty in stock GM-only synths — in that case the
synth simply falls back to the standard kit.

`drums(...)` is the bank-0 default kit. Every other helper hard-codes a
specific bank so call sites stay descriptive (`tr808(...)` reads better
than `Instrument("drums", 0, 25, ...)`).
"""

from __future__ import annotations

from collections.abc import Callable

from musicky.core.node import Instrument, Node

__all__ = [
    # standard
    "drums",
    "standard_kit",
    # GS/XG variations
    "room_kit",
    "power_kit",
    "rock_kit",
    "electronic_kit",
    "tr808",
    "tr909",
    "dance_kit",
    "techno_kit",
    "hiphop_kit",
    "jungle_kit",
    "house_kit",
    "trap_kit",
    "analog_kit",
    "jazz_kit",
    "brush_kit",
    "orchestra_kit",
    "ethnic_kit",
    "latin_kit",
    "taiko_kit",
    "lofi_kit",
    "garage_kit",
    "industrial_kit",
    "tribal_kit",
    "sfx_kit",
]


def _kit(name: str, bank: int) -> Callable[..., Instrument]:
    """Build a closure that produces a drums-channel Instrument.

    The Instrument's ``name`` is always ``"drums"`` (this is the literal
    the renderer checks to route to MIDI channel 9). The kit's
    user-facing identity travels in ``bank``, which the synth uses to
    pick the right SoundFont preset.
    """

    def make(*children: Node) -> Instrument:
        return Instrument(name="drums", program=0, bank=bank, children=children)

    make.__name__ = name
    make.__qualname__ = f"musicky.sounds.kits.{name}"
    make.__doc__ = f"Drum kit {name!r} (GS/XG bank {bank}). Routes to MIDI channel 9."
    return make


# Standard --------------------------------------------------------------------
drums = _kit("drums", 0)
standard_kit = _kit("standard_kit", 0)

# GS variations ---------------------------------------------------------------
room_kit = _kit("room_kit", 8)
power_kit = _kit("power_kit", 16)
rock_kit = _kit("rock_kit", 16)  # alias of power_kit
electronic_kit = _kit("electronic_kit", 24)
tr808 = _kit("tr808", 25)
tr909 = _kit("tr909", 26)
dance_kit = _kit("dance_kit", 26)  # alias of tr909
techno_kit = _kit("techno_kit", 27)
hiphop_kit = _kit("hiphop_kit", 28)
jungle_kit = _kit("jungle_kit", 29)
house_kit = _kit("house_kit", 30)
trap_kit = _kit("trap_kit", 31)
analog_kit = _kit("analog_kit", 25)  # alias of tr808
jazz_kit = _kit("jazz_kit", 32)
brush_kit = _kit("brush_kit", 40)
orchestra_kit = _kit("orchestra_kit", 48)
ethnic_kit = _kit("ethnic_kit", 42)
latin_kit = _kit("latin_kit", 41)
taiko_kit = _kit("taiko_kit", 43)
lofi_kit = _kit("lofi_kit", 49)
garage_kit = _kit("garage_kit", 50)
industrial_kit = _kit("industrial_kit", 51)
tribal_kit = _kit("tribal_kit", 52)
sfx_kit = _kit("sfx_kit", 56)
