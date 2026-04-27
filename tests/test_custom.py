from musicky import Node, chord, clip, custom, humanize, piano, reverb


def _chord_node() -> Node:
    """Helper: build a tiny Node tree to feed effect constructors."""
    return piano(clip(chord("C4")))


def test_custom_binds_keyword_default() -> None:
    soft_reverb = custom(reverb, amount=0.1)
    a = soft_reverb(_chord_node())
    b = reverb(_chord_node(), amount=0.1)
    assert a == b


def test_custom_call_site_overrides_bound_kwarg() -> None:
    soft_reverb = custom(reverb, amount=0.1)
    overridden = soft_reverb(_chord_node(), amount=0.5)
    direct = reverb(_chord_node(), amount=0.5)
    assert overridden == direct


def test_custom_preserves_name_and_doc() -> None:
    custom_humanize = custom(humanize, timing=0.04)
    assert custom_humanize.__name__ == "humanize"
    assert custom_humanize.__doc__ is not None
    assert "pre-bound keywords" in custom_humanize.__doc__


def test_custom_wraps_pointer() -> None:
    custom_humanize = custom(humanize, timing=0.04)
    assert custom_humanize.__wrapped__ is humanize  # type: ignore[attr-defined]
