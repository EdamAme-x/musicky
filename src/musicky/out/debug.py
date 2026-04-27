"""Debugging helpers: serialize any musicky value to JSON.

`dump` is the single entry point. It walks any frozen-dataclass tree
(notes, chords, scales, tracks, pieces) and turns it into a JSON document
either printed to stdout or written to a file. The JSON keeps a ``__type__``
tag on every dataclass so the dump round-trips back to source values
deterministically when needed.
"""

from __future__ import annotations

import json
import sys
from dataclasses import fields, is_dataclass
from pathlib import Path
from typing import Any, Final

__all__ = ["dump", "to_jsonable"]

_STDOUT_SENTINEL: Final[str] = "stdout"

# Field names whose values are callables and therefore not JSON-encodable.
# Listed by name so we drop them even when they are None.
_CALLABLE_FIELDS: Final[frozenset[str]] = frozenset({"apply", "chord_transform"})


def dump(value: Any, dest: str | Path = _STDOUT_SENTINEL) -> None:
    """Serialize a musicky value as pretty JSON.

    `dest` is either the literal ``"stdout"`` (print to standard output) or
    a filesystem path. Anything else is treated as a path. Output is UTF-8
    with two-space indentation; the ordering of keys mirrors the dataclass
    field order so a diff against a previous run is meaningful.
    """
    payload = to_jsonable(value)
    text = json.dumps(payload, ensure_ascii=False, indent=2)

    if isinstance(dest, str) and dest == _STDOUT_SENTINEL:
        sys.stdout.write(text + "\n")
        return

    path = Path(dest)
    path.write_text(text + "\n", encoding="utf-8")


def to_jsonable(value: Any) -> Any:
    """Recursively convert a value into JSON-compatible primitives.

    Frozen dataclasses become ``{"__type__": ClassName, <fields>}`` dicts.
    Tuples and lists become JSON arrays; dicts pass through with values
    converted. Any value not handled explicitly is returned as-is and will
    raise at ``json.dumps`` time if it is not already serializable, which
    is the right behavior — silent fallbacks would mask data bugs.
    """
    if is_dataclass(value) and not isinstance(value, type):
        out: dict[str, Any] = {"__type__": type(value).__name__}
        for f in fields(value):
            attr = getattr(value, f.name)
            # Skip callable-typed fields (Effect.apply, Effect.chord_transform).
            # We detect them by name+type to also drop None values for those
            # fields, so the JSON surface area stays clean either way.
            if f.name in _CALLABLE_FIELDS:
                continue
            out[f.name] = to_jsonable(attr)
        return out

    if isinstance(value, (tuple, list)):
        return [to_jsonable(item) for item in value]

    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}

    return value
