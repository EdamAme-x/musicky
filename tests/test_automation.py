import pytest

from musicky import auto
from musicky.core.automation import evaluate


def test_auto_sorts_points() -> None:
    a = auto([(4.0, 1.0), (0.0, 0.0), (8.0, 0.5)])
    assert a.points == ((0.0, 0.0), (4.0, 1.0), (8.0, 0.5))


def test_evaluate_holds_first_value_before_first_point() -> None:
    a = auto([(2.0, 0.5), (4.0, 1.0)])
    assert evaluate(a, 0.0) == 0.5


def test_evaluate_holds_last_value_after_last_point() -> None:
    a = auto([(0.0, 0.0), (4.0, 1.0)])
    assert evaluate(a, 100.0) == 1.0


def test_evaluate_interpolates_linearly() -> None:
    a = auto([(0.0, 0.0), (4.0, 1.0)])
    assert evaluate(a, 2.0) == 0.5


def test_evaluate_passes_through_scalars() -> None:
    assert evaluate(0.7, 5.0) == 0.7


def test_auto_requires_at_least_one_point() -> None:
    with pytest.raises(ValueError):
        auto([])


def test_auto_with_single_point_holds_value() -> None:
    """A single control point becomes a constant curve at that value."""
    a = auto([(2.0, 0.7)])
    assert evaluate(a, 0.0) == 0.7
    assert evaluate(a, 2.0) == 0.7
    assert evaluate(a, 100.0) == 0.7


def test_auto_duplicate_beat_picks_one_value() -> None:
    """Two points at the same beat: sample-at-beat picks the held value.

    With identical beats and different values, evaluate() at that exact
    beat returns one of them (whichever wins the sort tie). The
    important contract is that evaluation does not crash and the curve
    is monotonic in time.
    """
    a = auto([(2.0, 0.0), (2.0, 1.0)])
    # Both points share beat=2.0. The held value at that beat must be
    # one of the two control values; evaluate() should not raise.
    val = evaluate(a, 2.0)
    assert val in (0.0, 1.0)
    # Sampling slightly before the duplicate point still works.
    assert evaluate(a, 1.5) in (0.0, 1.0)


def test_auto_three_point_curve_interpolates_each_segment() -> None:
    """A multi-segment curve interpolates linearly between successive points."""
    a = auto([(0.0, 0.0), (4.0, 1.0), (8.0, 0.0)])
    assert evaluate(a, 2.0) == 0.5  # halfway up
    assert evaluate(a, 6.0) == 0.5  # halfway down
