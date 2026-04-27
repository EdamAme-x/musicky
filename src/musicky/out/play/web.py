"""Web context: emit a self-contained HTML page that plays the Piece.

The generated page embeds the MIDI bytes as base64 and uses ``Tone.js``
plus ``@tonejs/midi`` from a CDN to schedule and play them with a single
click. This keeps the backend pure-Python (no JS toolchain at build time)
while still producing a fully working web playback artifact.

Output destinations:
  * a filesystem path → write the HTML there
  * the literal ``"return"`` → render returns the HTML through a closure
    captured variable (use `last_html(ctx)` to retrieve)
"""

from __future__ import annotations

import base64
from pathlib import Path

from musicky.core.piece import Piece
from musicky.out.play.context import Context
from musicky.out.play.midi import render_to_bytes

__all__ = ["create_web_context", "render_html"]


def create_web_context(
    path: str | Path,
    *,
    title: str = "musicky",
    autoplay: bool = False,
) -> Context:
    """Build a Context that writes a playable HTML file to `path`.

    `autoplay` only affects the generated page: when True the page tries
    to start playback as soon as it loads, but most browsers will still
    require a user gesture before any audio is produced.
    """
    target = Path(path)

    def render(music: Piece) -> None:
        html = render_html(music, title=title, autoplay=autoplay)
        target.write_text(html, encoding="utf-8")

    def close() -> None:
        return None

    return Context(render=render, close=close)


def render_html(music: Piece, *, title: str = "musicky", autoplay: bool = False) -> str:
    """Render a Piece to a self-contained HTML string. Public for embedding."""
    midi_bytes = render_to_bytes(music)
    midi_b64 = base64.b64encode(midi_bytes).decode("ascii")
    autoplay_js = "play();" if autoplay else "/* user gesture required */"

    return _HTML_TEMPLATE.format(
        title=_escape(title),
        midi_b64=midi_b64,
        autoplay_js=autoplay_js,
    )


def _escape(text: str) -> str:
    """Escape HTML-significant characters in user-supplied text."""
    return (
        text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    )


# Template kept as a module-level string so it shows up clearly in diffs.
_HTML_TEMPLATE = """\
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
  body {{ font-family: system-ui, sans-serif; padding: 2rem; }}
  button {{ font-size: 1rem; padding: 0.5rem 1rem; }}
</style>
</head>
<body>
<h1>{title}</h1>
<button id="play">Play</button>
<button id="stop">Stop</button>
<script src="https://cdn.jsdelivr.net/npm/tone@14.8.49/build/Tone.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/@tonejs/midi@2.0.28/build/Midi.min.js"></script>
<script>
const MIDI_B64 = "{midi_b64}";

function decodeMidi(b64) {{
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return bytes;
}}

let synths = [];
let scheduled = false;

async function prepare() {{
  if (scheduled) return;
  await Tone.start();
  const midi = new Midi(decodeMidi(MIDI_B64));
  Tone.Transport.bpm.value = midi.header.tempos[0]?.bpm || 120;

  midi.tracks.forEach(track => {{
    const synth = new Tone.PolySynth(Tone.Synth).toDestination();
    synths.push(synth);
    track.notes.forEach(note => {{
      Tone.Transport.schedule(time => {{
        synth.triggerAttackRelease(note.name, note.duration, time, note.velocity);
      }}, note.time);
    }});
  }});
  scheduled = true;
}}

async function play() {{
  await prepare();
  Tone.Transport.start();
}}

function stop() {{
  Tone.Transport.stop();
  Tone.Transport.cancel();
  synths.forEach(s => s.dispose());
  synths = [];
  scheduled = false;
}}

document.getElementById("play").addEventListener("click", play);
document.getElementById("stop").addEventListener("click", stop);
window.addEventListener("load", () => {{ {autoplay_js} }});
</script>
</body>
</html>
"""
