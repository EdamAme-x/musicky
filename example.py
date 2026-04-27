"""Dogfooding example: a backing track for a example-style song.
"""

from pathlib import Path

from musicky import (
    Mix,
    acoustic_grand,
    at,
    chord,
    clean_guitar,
    clip,
    create_midi_context,
    drums,
    eq,
    finger_bass,
    gain,
    grooves,
    hold,
    humanize,
    limiter,
    master,
    move,
    musicky,
    normalize,
    output,
    phrase,
    play,
    pump,
    reverb,
    string_ensemble_1,
)

# --- Layout -------------------------------------------------------------------

BPM = 168
SECTION = 16.0  # 4 bars * 4 beats

INTRO = 0 * SECTION
VERSE_A = 1 * SECTION
VERSE_B = 2 * SECTION
CHORUS = 3 * SECTION
INTERLUDE = 4 * SECTION
VERSE_A2 = 5 * SECTION
VERSE_B2 = 6 * SECTION
CHORUS2 = 7 * SECTION
OUTRO = 8 * SECTION

# --- Harmonic content ---------------------------------------------------------
# A-minor / C-major shared progression. The A-section uses i-VI-III-VII
# (Am - F - C - G), the staple of fast vocaloid pop. The B-section adds a
# ii-V cadence to push toward the chorus.

PROG_A = [
    chord("A3, C4, E4, G4"),  # Am7
    chord("F3, A3, C4, E4"),  # Fmaj7
    chord("C4, E4, G4, B4"),  # Cmaj7
    chord("G3, B3, D4, F4"),  # G7
]

PROG_B = [
    chord("D3, F3, A3, C4"),  # Dm7
    chord("G3, B3, D4, F4"),  # G7
    chord("C4, E4, G4, B4"),  # Cmaj7
    chord("A3, C4, E4, G4"),  # Am7
]

PROG_CHORUS = PROG_A  # the chorus reuses the i-VI-III-VII shape


# --- Pattern helpers ----------------------------------------------------------


def piano_eighths(progression):
    """Repeat each chord across one bar as 8th-note hits.

    The result drives the rhythm section without filling the mid-range
    the way a sustained pad would, leaving room for a vocal on top.
    """
    return [
        chord(
            [n.name + str(n.octave) for n in c.notes] * 2,
            interval=0.5,
            duration=0.45,
        )
        for c in progression
    ]


def guitar_arpeggio(progression):
    """Lay each chord as a 16th-note up-arp across one bar."""
    return [
        chord(
            [n.name + str(n.octave) for n in c.notes] * 2,
            interval=0.25,
            duration=0.22,
        )
        for c in progression
    ]


# --- Piano: the rhythmic engine ----------------------------------------------

piano_part = humanize(
    Mix(
        children=(
            at(INTRO, phrase(acoustic_grand, piano_eighths(PROG_A))),
            at(VERSE_A, phrase(acoustic_grand, piano_eighths(PROG_A))),
            at(VERSE_B, phrase(acoustic_grand, piano_eighths(PROG_B))),
            at(CHORUS, phrase(acoustic_grand, piano_eighths(PROG_CHORUS))),
            at(INTERLUDE, phrase(acoustic_grand, piano_eighths(PROG_A))),
            at(VERSE_A2, phrase(acoustic_grand, piano_eighths(PROG_A))),
            at(VERSE_B2, phrase(acoustic_grand, piano_eighths(PROG_B))),
            at(CHORUS2, phrase(acoustic_grand, piano_eighths(PROG_CHORUS))),
            at(OUTRO, phrase(acoustic_grand, piano_eighths(PROG_A[:2]))),
        )
    ),
    timing=0.005,
    velocity=4,
    seed=11,
)

# --- Clean guitar: arpeggio strums on B-section, choruses, and interlude -----

guitar_part = humanize(
    Mix(
        children=(
            at(VERSE_B, phrase(clean_guitar, guitar_arpeggio(PROG_B))),
            at(CHORUS, phrase(clean_guitar, guitar_arpeggio(PROG_CHORUS))),
            at(INTERLUDE, phrase(clean_guitar, guitar_arpeggio(PROG_A))),
            at(VERSE_B2, phrase(clean_guitar, guitar_arpeggio(PROG_B))),
            at(CHORUS2, phrase(clean_guitar, guitar_arpeggio(PROG_CHORUS))),
        )
    ),
    timing=0.004,
    velocity=4,
    seed=23,
)

# --- Bass: 8th-note roots from each chord ------------------------------------

bass_part = Mix(
    children=(
        at(VERSE_A, finger_bass(clip(pump(PROG_A)))),
        at(VERSE_B, finger_bass(clip(pump(PROG_B)))),
        at(CHORUS, finger_bass(clip(pump(PROG_CHORUS)))),
        at(INTERLUDE, finger_bass(clip(pump(PROG_A)))),
        at(VERSE_A2, finger_bass(clip(pump(PROG_A)))),
        at(VERSE_B2, finger_bass(clip(pump(PROG_B)))),
        at(CHORUS2, finger_bass(clip(pump(PROG_CHORUS)))),
        at(OUTRO, finger_bass(clip(pump(PROG_A[:2])))),
    )
)

# --- Strings: sweeten the choruses only --------------------------------------

strings_part = Mix(
    children=(
        at(CHORUS, string_ensemble_1(clip(hold(PROG_CHORUS, duration=4.0)))),
        at(CHORUS2, string_ensemble_1(clip(hold(PROG_CHORUS, duration=4.0)))),
    )
)

# --- Drums: layered grooves per section --------------------------------------

drum_clips: list = []
drum_clips += move(grooves.intro(), INTRO)
drum_clips += move(grooves.sparse(), VERSE_A)
drum_clips += move(grooves.sparse(), VERSE_B)
drum_clips += move(grooves.full(), CHORUS)
drum_clips += move(grooves.break_(), INTERLUDE)
drum_clips += move(grooves.sparse(), VERSE_A2)
drum_clips += move(grooves.sparse(), VERSE_B2)
drum_clips += move(grooves.full(), CHORUS2)
drum_clips += move(grooves.outro(), OUTRO)
drum_part = drums(*drum_clips)

# --- Mix tree -----------------------------------------------------------------
# Piano and guitar take a small mid cut so the vocal range stays open.
# Strings live in a deep reverb and well below the rhythm section. No
# distortion / saturation / sidechain — the band is doing the work.

music = musicky(
    master(
        normalize(),
        limiter(threshold=-1.0),
        # Piano: the rhythmic anchor. Light reverb plus a small mid cut.
        eq(reverb(piano_part, amount=0.18, decay=1.5), mid=-2.0),
        # Guitar: tiny reverb, sits behind the piano.
        reverb(guitar_part, amount=0.15, decay=1.2),
        # Bass: low-shelf bump for body, otherwise dry.
        eq(bass_part, low=2.0),
        # Strings: airy, far back in the mix.
        gain(reverb(strings_part, amount=0.5, decay=2.5), db=-6.0),
        # Drums: forward and dry.
        drum_part,
    ),
    bpm=BPM,
    name="example",
)

# --- Render -------------------------------------------------------------------

if __name__ == "__main__":
    here = Path(__file__).parent
    midi_path = here / "example.mid"
    wav_path = here / "example.wav"

    play(music, create_midi_context(midi_path))
    print(f"wrote {midi_path} ({midi_path.stat().st_size} bytes)")

    output(music, wav_path)
    print(f"wrote {wav_path} ({wav_path.stat().st_size} bytes)")
