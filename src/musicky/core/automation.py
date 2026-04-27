"""Automation: parameters that change over time.

`auto([(beat, value), ...])` builds a piecewise-linear curve evaluated at
arbitrary beat positions. Effect parameters that accept ``float |
Automation`` can be animated by passing one of these instead of a scalar.

The renderer evaluates an Automation by linearly interpolating between
the surrounding control points; before the first point it holds the
first value, after the last point it holds the last value. This matches
how DAWs draw automation lanes.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["Automation", "auto", "evaluate"]


@dataclass(frozen=True, slots=True)
class Automation:
    """A time-varying parameter expressed as ordered control points.

    `points` are ``(beat, value)`` pairs sorted by beat. We do not enforce
    sortedness in the type but `auto(...)` always produces sorted data,
    so callers should construct via that helper.
    """

    points: tuple[tuple[float, float], ...]


def auto(points: list[tuple[float, float]] | tuple[tuple[float, float], ...]) -> Automation:
    """Build an Automation from a list of ``(beat, value)`` pairs."""
    if not points:
        raise ValueError(
            "auto() requires at least one (beat, value) point. "
            "Example: auto([(0, 0.0), (4, 1.0), (8, 0.0)]) for a fade-in/out.",
        )
    sorted_points = tuple(sorted(points, key=lambda p: p[0]))
    return Automation(points=sorted_points)


def evaluate(curve: Automation | float, at_beat: float) -> float:
    """Sample the parameter at `at_beat`. Scalars pass through.

    A bare float is accepted so call sites can write
    ``evaluate(param, beat)`` without checking the type first.
    """
    if isinstance(curve, (int, float)):
        return float(curve)

    points = curve.points
    if not points:
        return 0.0
    if at_beat <= points[0][0]:
        return points[0][1]
    if at_beat >= points[-1][0]:
        return points[-1][1]

    # Linear search is fine; control points lists are tiny in practice.
    for i in range(1, len(points)):
        b1, v1 = points[i]
        if at_beat <= b1:
            b0, v0 = points[i - 1]
            t = (at_beat - b0) / (b1 - b0) if b1 > b0 else 0.0
            return v0 + (v1 - v0) * t
    return points[-1][1]
