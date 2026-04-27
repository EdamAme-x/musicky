from pathlib import Path

from musicky import (
    Context,
    bass,
    chord,
    clip,
    close,
    create_midi_context,
    musicky,
    piano,
    play,
)
from musicky.out.play.midi import render_to_bytes


def test_render_to_bytes_starts_with_mthd() -> None:
    music = musicky(piano(clip(chord("C4, E4, G4"))), name="t")
    data = render_to_bytes(music)
    assert data.startswith(b"MThd")


def test_render_to_bytes_has_one_track_per_voice() -> None:
    music = musicky(
        piano(clip(chord("C4"))),
        bass(clip(chord("C2"))),
    )
    data = render_to_bytes(music)
    # 1 conductor + 2 voices on different channels
    assert data.count(b"MTrk") == 3


def test_midi_context_writes_file(tmp_path: Path) -> None:
    out = tmp_path / "song.mid"
    ctx = create_midi_context(out)
    music = musicky(piano(clip(chord("C4, E4, G4"))))
    play(music, ctx)
    close(ctx)

    assert out.exists()
    assert out.read_bytes().startswith(b"MThd")


def test_midi_context_overwrites_on_second_render(tmp_path: Path) -> None:
    out = tmp_path / "song.mid"
    ctx = create_midi_context(out)
    play(musicky(piano(clip(chord("C4")))), ctx)
    first_size = out.stat().st_size
    play(musicky(piano(clip(chord("C4, E4, G4, B4")))), ctx)
    second_size = out.stat().st_size
    assert second_size > first_size


def test_context_is_dataclass() -> None:
    ctx = create_midi_context("/tmp/dummy.mid")
    assert isinstance(ctx, Context)
