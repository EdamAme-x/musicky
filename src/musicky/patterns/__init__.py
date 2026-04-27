"""Composition shortcuts for common building blocks.

Most pieces have the same handful of repeating shapes — a chord
progression spread as an arpeggio, a pad that holds each chord for a
bar, a bass that pumps eighth-notes on the chord root, a drum groove
laid out across four bars. Writing those by hand for every track is
busywork, so they live here as small reusable functions.

These return raw `Chord` / `Clip` / `list[Clip]` values, not Nodes, so
they slot into whatever instrument or effect chain the user wants.
"""

from musicky.patterns import grooves
from musicky.patterns.shapes import arp, hits, hold, move, phrase, pump

__all__ = ["arp", "grooves", "hits", "hold", "move", "phrase", "pump"]
