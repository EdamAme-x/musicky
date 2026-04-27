"""Time-axis helpers for Node trees.

`seq(*children)` is the natural counterpart to bare `Mix`: it places its
children one after another in time, computing each one's start position
from the lengths of the children before it. This means users can write
``seq(piano(clip(a)), piano(clip(b)))`` and trust the renderer to put
``b`` right after ``a`` finishes.

Implementing this requires inspecting how long each subtree lasts in
beats. `length(node)` walks the tree and returns the maximum end-time
among all clips below it.
"""

from __future__ import annotations

from dataclasses import replace

from musicky.core.node import Clip, Effect, Instrument, Mix, Node, Sample

__all__ = ["at", "length", "seq", "shift"]


def length(node: Node) -> float:
    """Return the total duration of `node` in beats.

    The duration is the latest clip end-time across the subtree.
    Symbolic effects do not change durations measurably (humanize jitter
    is small and bounded), so we ignore them. Audio effects also do not
    change beat-time so they are transparent here.
    """
    if isinstance(node, Clip):
        end = node.at
        cursor = node.at
        notes = node.content.notes
        intervals = node.content.intervals
        for i, n in enumerate(notes):
            end = max(end, cursor + n.duration)
            if i < len(intervals):
                cursor += intervals[i]
        return end

    if isinstance(node, Sample):
        # We do not know the audio file's exact length without decoding;
        # treat its `at` as a lower bound for downstream sequencing.
        return node.at

    if isinstance(node, (Instrument, Effect, Mix)):
        if not node.children:
            return 0.0
        return max(length(c) for c in node.children)

    raise TypeError(
        f"unknown node type: {type(node).__name__}. "
        "Expected one of Clip, Instrument, Effect, Mix, Sample.",
    )


def seq(*children: Node) -> Mix:
    """Place `children` one after another in time.

    Each child is shifted by the cumulative length of all previous
    children. The resulting node is a `Mix` so the rest of the renderer
    sees the children played simultaneously from the offsets we set.
    """
    cursor = 0.0
    placed: list[Node] = []
    for child in children:
        placed.append(_shift(child, cursor))
        cursor += length(child)
    return Mix(children=tuple(placed))


def shift(node: Node, by: float) -> Node:
    """Return a copy of `node` with every Clip below it offset by `by` beats.

    Useful for placing a sub-tree at a specific point on the global
    timeline without manually walking its clips. `seq()` uses this
    internally to chain its children, but it is also handy for arranging
    sections explicitly:

        verse_at_bar_4 = shift(verse, by=16.0)
    """
    if by == 0:
        return node

    if isinstance(node, (Clip, Sample)):
        return replace(node, at=node.at + by)
    if isinstance(node, Instrument):
        return replace(node, children=tuple(shift(c, by) for c in node.children))
    if isinstance(node, Effect):
        return replace(node, children=tuple(shift(c, by) for c in node.children))
    if isinstance(node, Mix):
        return replace(node, children=tuple(shift(c, by) for c in node.children))
    raise TypeError(
        f"unknown node type: {type(node).__name__}. "
        "Expected one of Clip, Instrument, Effect, Mix, Sample.",
    )


def at(beats: float, node: Node) -> Node:
    """Place `node` so its earliest clip starts at `beats` on the timeline.

    Equivalent to ``shift(node, beats - earliest_at(node))``. Reads more
    naturally for explicit section layouts:

        Mix(at(0,    intro),
            at(16,   verse),
            at(32,   chorus))
    """
    earliest = _earliest(node)
    return shift(node, beats - earliest)


def _earliest(node: Node) -> float:
    """Return the smallest `at` of any leaf below `node` (0 if there are none)."""
    if isinstance(node, (Clip, Sample)):
        return node.at
    if isinstance(node, (Instrument, Effect, Mix)):
        if not node.children:
            return 0.0
        return min(_earliest(c) for c in node.children)
    raise TypeError(
        f"unknown node type: {type(node).__name__}. "
        "Expected one of Clip, Instrument, Effect, Mix, Sample.",
    )


# Internal alias kept for backward compatibility with the previous _shift
# name. Removed from __all__; new code should use `shift`.
_shift = shift
