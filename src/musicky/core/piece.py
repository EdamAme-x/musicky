"""Piece type and the top-level `musicky(...)` constructor.

A `Piece` is a tiny wrapper that pairs a Node tree with global metadata
(tempo and an optional name). All structural information — instruments,
effects, timing — lives inside the tree itself.
"""

from __future__ import annotations

from dataclasses import dataclass

from musicky.core.node import Mix, Node

__all__ = ["Piece", "musicky"]


@dataclass(frozen=True, slots=True)
class Piece:
    """A complete composition: a signal-flow tree plus tempo and label."""

    root: Node
    bpm: float
    name: str | None


def musicky(*children: Node, bpm: float = 120.0, name: str | None = None) -> Piece:
    """Build a Piece from any number of top-level Node children.

    Multiple children are wrapped in a `Mix` so they play simultaneously,
    which matches DAW intuition: each top-level child is a separate
    track. With a single child the wrapping is harmless.
    """
    root = children[0] if len(children) == 1 else Mix(children=children)
    return Piece(root=root, bpm=bpm, name=name)
