from pathlib import Path

from musicky import chord, clip, close, create_web_context, musicky, piano, play
from musicky.out.play.web import render_html


def test_render_html_includes_midi_payload() -> None:
    music = musicky(piano(clip(chord("C4, E4, G4"))), name="hello")
    html = render_html(music, title="hello")
    assert "<title>hello</title>" in html
    assert "MIDI_B64" in html


def test_html_escapes_title() -> None:
    music = musicky(piano(clip(chord("C4"))))
    html = render_html(music, title="<x>&</x>")
    assert "&lt;x&gt;" in html


def test_web_context_writes_file(tmp_path: Path) -> None:
    out = tmp_path / "page.html"
    ctx = create_web_context(out, title="demo")
    play(musicky(piano(clip(chord("C4, E4, G4")))), ctx)
    close(ctx)
    text = out.read_text(encoding="utf-8")
    assert "<!doctype html>" in text
    assert "demo" in text
