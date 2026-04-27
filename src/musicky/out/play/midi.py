"""MIDI file context: write a Piece to a Standard MIDI File (SMF).

Audio effects in the Node tree are silently ignored when rendering to
MIDI, since SMF has no notion of reverb plug-ins or compressors. The
symbolic effects (humanize, transpose, ...) are honored because they
operate on note data.
"""

from __future__ import annotations

import struct
from collections.abc import Callable
from io import BytesIO
from pathlib import Path

from musicky.core.piece import Piece
from musicky.core.render import Voice, flatten
from musicky.out.play.context import Context
from musicky.primitives.note import PITCH_CLASSES

__all__ = ["create_midi_context", "render_to_bytes"]


def create_midi_context(path: str | Path, *, ticks_per_beat: int = 480) -> Context:
    """Build a Context that writes incoming Pieces to `path` as an SMF."""
    target = Path(path)

    def render(music: Piece) -> None:
        target.write_bytes(render_to_bytes(music, ticks_per_beat=ticks_per_beat))

    def close() -> None:
        return None

    return Context(render=render, close=close)


def render_to_bytes(music: Piece, *, ticks_per_beat: int = 480) -> bytes:
    """Serialize a Piece to SMF bytes.

    `Sample` nodes are skipped: SMF has no way to embed raw audio, so
    file-based samples only show up in audio rendering (`output(...)`).
    """
    flat = flatten(music.root)

    # Group voices by channel so each MIDI track maps to one logical voice.
    by_channel: dict[int, list[Voice]] = {}
    for v in flat:
        if isinstance(v, Voice):
            by_channel.setdefault(v.channel, []).append(v)

    # Format-1 SMF: track 0 carries tempo, the rest carry notes.
    n_tracks = 1 + len(by_channel)
    header = b"MThd" + struct.pack(">IHHH", 6, 1, n_tracks, ticks_per_beat)

    body = bytearray()
    body += _conductor_track(music.bpm)
    for channel, channel_voices in by_channel.items():
        body += _voice_track(channel_voices, channel, ticks_per_beat=ticks_per_beat)

    return bytes(header) + bytes(body)


def _conductor_track(bpm: float) -> bytes:
    """Track 0 carries the tempo so all other tracks share timing.

    SMF Set Tempo encodes microseconds per beat into 3 bytes, so the
    representable range is 1..16777215 µs/beat (≈ 3.58 BPM minimum).
    Negative or zero BPM is meaningless and rejected outright; absurdly
    low BPM is clamped to the SMF maximum so the file stays valid.
    """
    if bpm <= 0:
        raise ValueError(
            f"bpm must be positive, got {bpm}. Typical values are 60-200.",
        )
    micros_per_beat = min(round(60_000_000 / bpm), 0xFFFFFF)
    set_tempo = b"\x00\xff\x51\x03" + micros_per_beat.to_bytes(3, "big")
    end_of_track = b"\x00\xff\x2f\x00"
    return _chunk("MTrk", set_tempo + end_of_track)


def _voice_track(voices: list[Voice], channel: int, *, ticks_per_beat: int) -> bytes:
    """Render every note from `voices` (sharing `channel`) into one MTrk chunk."""
    payload = bytearray()
    program = voices[0].program if voices else 0
    bank = voices[0].bank if voices else 0

    # Bank Select MSB on CC 0, LSB on CC 32, then Program Change.
    # Drum channel 9 still needs Bank Select for kit switching (TR-808 etc.).
    if bank != 0:
        payload += b"\x00" + bytes([0xB0 | channel, 0x00, (bank >> 7) & 0x7F])
        payload += b"\x00" + bytes([0xB0 | channel, 0x20, bank & 0x7F])
    if channel != 9 or bank != 0:
        payload += b"\x00" + bytes([0xC0 | channel, program & 0x7F])

    events: list[tuple[int, bytes]] = []
    for v in voices:
        cursor = v.clip.at
        for i, n in enumerate(v.clip.content.notes):
            on_tick = round(cursor * ticks_per_beat)
            off_tick = on_tick + max(1, round(n.duration * ticks_per_beat))
            midi = max(0, min(127, (n.octave + 1) * 12 + PITCH_CLASSES.index(n.name)))
            velocity = max(0, min(127, n.velocity))
            events.append((on_tick, bytes([0x90 | channel, midi, velocity])))
            events.append((off_tick, bytes([0x80 | channel, midi, 0])))
            if i < len(v.clip.content.intervals):
                cursor += v.clip.content.intervals[i]

    events.sort(key=lambda e: e[0])
    last = 0
    for tick, msg in events:
        delta = tick - last
        last = tick
        payload += _vlq(delta) + msg

    payload += b"\x00\xff\x2f\x00"
    return _chunk("MTrk", bytes(payload))


def _chunk(tag: str, data: bytes) -> bytes:
    return tag.encode("ascii") + struct.pack(">I", len(data)) + data


def _vlq(value: int) -> bytes:
    if value < 0:
        raise ValueError("VLQ cannot encode negative integers")
    buf = BytesIO()
    chunks = [value & 0x7F]
    value >>= 7
    while value:
        chunks.append((value & 0x7F) | 0x80)
        value >>= 7
    for byte in reversed(chunks):
        buf.write(bytes([byte]))
    return buf.getvalue()


_render_signature: Callable[[Piece], None]
