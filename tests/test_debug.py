import json
from pathlib import Path

import pytest

from musicky import chord, clip, dump, musicky, note, piano, reverb, to_jsonable


def test_to_jsonable_note() -> None:
    payload = to_jsonable(note("C5"))
    assert payload == {
        "__type__": "Note",
        "name": "C",
        "octave": 5,
        "duration": 0.25,
        "velocity": 100,
        "channel": None,
    }


def test_to_jsonable_chord_recurses() -> None:
    payload = to_jsonable(chord("C5, E5"))
    assert payload["__type__"] == "Chord"
    assert len(payload["notes"]) == 2
    assert payload["notes"][0]["__type__"] == "Note"
    assert payload["intervals"] == [0.0]


def test_to_jsonable_node_tree() -> None:
    music = musicky(
        reverb(piano(clip(chord("C4, E4, G4"), at=0)), amount=0.3),
        bpm=110,
        name="hi",
    )
    payload = to_jsonable(music)
    assert payload["__type__"] == "Piece"
    assert payload["bpm"] == 110
    assert payload["root"]["__type__"] == "Effect"
    assert payload["root"]["kind"] == "reverb"


def test_dump_to_stdout(capsys: pytest.CaptureFixture[str]) -> None:
    dump(note("C5"))
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed["__type__"] == "Note"


def test_dump_to_file(tmp_path: Path) -> None:
    path = tmp_path / "out.json"
    music = musicky(piano(clip(chord("C4, E4, G4"))), name="demo")
    dump(music, path)
    parsed = json.loads(path.read_text(encoding="utf-8"))
    assert parsed["name"] == "demo"


def test_empty_chord_serializes() -> None:
    payload = to_jsonable(chord([]))
    assert payload == {"__type__": "Chord", "notes": [], "intervals": []}


def test_effect_omits_callable_fields() -> None:
    """Effect.apply / Effect.chord_transform are dropped from JSON."""
    payload = to_jsonable(reverb(piano(clip(chord("C4"))), amount=0.2))
    assert payload["__type__"] == "Effect"
    assert payload["kind"] == "reverb"
    # The closures must not appear in the serialized form.
    assert "apply" not in payload
    assert "chord_transform" not in payload
    # Params still show up, so the dump is informative.
    assert payload["params"]["amount"] == 0.2
