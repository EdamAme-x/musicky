"""Tests for the composition shortcut helpers in `musicky.patterns`."""

from musicky import (
    Mix,
    arp,
    chord,
    clip,
    grooves,
    hits,
    hold,
    kick,
    move,
    musicky,
    notes,
    piano,
    pump,
    snare,
    tr808,
)
from musicky.core.render import flatten_voices as flatten


def test_arp_concatenates_chords_into_a_melody() -> None:
    progression = [chord("C4, E4, G4"), chord("F4, A4, C5")]
    line = arp(progression, interval=0.25)
    # Each input chord has 3 notes -> total 6, with 5 intervals between.
    assert len(line.notes) == 6
    assert all(iv == 0.25 for iv in line.intervals)


def test_hold_stamps_duration_and_spaces_chords() -> None:
    progression = [chord("C4, E4"), chord("G4, B4")]
    pad = hold(progression, duration=4.0)
    # 2 chords * 2 notes = 4 notes total.
    assert len(pad.notes) == 4
    # Every note's duration is set to the requested value.
    assert all(n.duration == 4.0 for n in pad.notes)


def test_pump_produces_eight_eighths_per_chord() -> None:
    progression = [chord("C4, E4, G4")]
    bass = pump(progression, sub=8)
    # One chord * 8 hits = 8 notes.
    assert len(bass.notes) == 8
    assert all(iv == 0.5 for iv in bass.intervals)


def test_pump_drops_octave_and_uses_root() -> None:
    progression = [chord("C5, E5, G5")]
    bass = pump(progression, sub=4, octaves_below=1)
    # MIDI for C5 is 72; one octave down is 60.
    from musicky import pitch

    assert all(pitch(n) == 60 for n in bass.notes)


def test_hits_builds_a_clip_per_position() -> None:
    clips = hits(kick, 0.0, 1.0, 2.0, 3.0, velocity=110)
    assert len(clips) == 4
    assert [c.at for c in clips] == [0.0, 1.0, 2.0, 3.0]
    assert all(c.content.notes[0].velocity == 110 for c in clips)


def test_move_shifts_a_clip_list() -> None:
    raw = hits(snare, 0.0, 1.0)
    moved = move(raw, by=8.0)
    assert [c.at for c in moved] == [8.0, 9.0]


def test_grooves_full_returns_clips_for_four_bars() -> None:
    pattern = grooves.full(bars=4)
    # Should fit within 16 beats and contain a healthy mix of hits.
    assert all(0 <= c.at < 16.0 for c in pattern)
    assert len(pattern) > 30  # plenty of hits for a busy chorus groove


def test_grooves_intro_only_uses_hi_hats() -> None:
    pattern = grooves.intro(bars=1)
    # Closed hi-hat MIDI pitch is 42 by GM convention.
    assert all(notes(c.content)[0].name == "F#" for c in pattern)


def test_arp_routed_through_a_lead_renders_voices() -> None:
    progression = [chord("C4, E4, G4"), chord("F4, A4, C5")]
    music = musicky(piano(clip(arp(progression, interval=0.125))))
    voices = flatten(music.root)
    assert len(voices) == 1
    assert len(voices[0].clip.content.notes) == 6


def test_grooves_routed_through_drumkit_share_channel() -> None:
    music = musicky(tr808(*move(grooves.full(bars=1), by=0.0)))
    voices = flatten(music.root)
    # All percussion clips end up on channel 9 of the kit.
    assert all(v.channel == 9 for v in voices)


def test_phrase_chains_chords_through_an_instrument() -> None:
    """`phrase(piano, [a, b])` should equal `seq(piano(clip(a)), piano(clip(b)))`."""
    from musicky import phrase, seq

    a = chord("C4, E4, G4")
    b = chord("F4, A4, C5")
    by_phrase = phrase(piano, [a, b])
    by_hand = seq(piano(clip(a)), piano(clip(b)))
    voices_a = sorted(flatten(by_phrase), key=lambda v: v.clip.at)
    voices_b = sorted(flatten(by_hand), key=lambda v: v.clip.at)
    assert [v.clip.at for v in voices_a] == [v.clip.at for v in voices_b]
    assert [v.clip.content for v in voices_a] == [v.clip.content for v in voices_b]


def test_phrase_applies_transpose_in_one_call() -> None:
    """`transpose=2` should shift every chord up by a whole step."""
    from musicky import phrase, pitch

    plain = phrase(piano, [chord("C4"), chord("D4")])
    raised = phrase(piano, [chord("C4"), chord("D4")], transpose=2)
    plain_pitches = [pitch(v.clip.content.notes[0]) for v in flatten(plain)]
    raised_pitches = [pitch(v.clip.content.notes[0]) for v in flatten(raised)]
    assert raised_pitches == [p + 2 for p in plain_pitches]


def test_mix_with_at_offsets_combines_sections() -> None:
    """Sanity check: Mix + at can place sections without overlap."""
    from musicky import at

    section_a = piano(clip(chord("C4")))
    section_b = piano(clip(chord("E4")))
    music = musicky(Mix(children=(at(0.0, section_a), at(4.0, section_b))))
    voices = sorted(flatten(music.root), key=lambda v: v.clip.at)
    assert voices[0].clip.at == 0.0
    assert voices[1].clip.at == 4.0
