"""Instrument node constructors for every General MIDI program.

The General MIDI Level 1 specification defines 128 instrument programs
(0-127), grouped into 16 families of 8 sounds each. Every program is
exposed here as a single function that returns an `Instrument` node.

Why 128 functions and not a single `instrument(name, ...)` factory?
Because IDE auto-completion and a flat namespace are far more pleasant
to compose with than memorizing strings. For dynamic dispatch, see
`sound(spec, *children)` which accepts either a name or an integer.

Aliases at the bottom of the file map short familiar names (``piano``,
``guitar``, ``bass``, ``synth``, ``strings``) onto the most common
choice within each family, so casual users never have to scroll through
all 128 names.
"""

from __future__ import annotations

from collections.abc import Callable

from musicky.core.node import Instrument, Node

__all__ = [
    "GM_PROGRAMS",
    "sound",
    # Piano family (0-7)
    "acoustic_grand",
    "bright_piano",
    "electric_grand",
    "honkytonk",
    "electric_piano_1",
    "electric_piano_2",
    "harpsichord",
    "clavinet",
    # Chromatic Percussion family (8-15)
    "celesta",
    "glockenspiel",
    "music_box",
    "vibraphone",
    "marimba",
    "xylophone",
    "tubular_bells",
    "dulcimer",
    # Organ family (16-23)
    "drawbar_organ",
    "percussive_organ",
    "rock_organ",
    "church_organ",
    "reed_organ",
    "accordion",
    "harmonica",
    "tango_accordion",
    # Guitar family (24-31)
    "nylon_guitar",
    "steel_guitar",
    "jazz_guitar",
    "clean_guitar",
    "muted_guitar",
    "overdrive_guitar",
    "distortion_guitar",
    "guitar_harmonics",
    # Bass family (32-39)
    "acoustic_bass",
    "finger_bass",
    "pick_bass",
    "fretless_bass",
    "slap_bass_1",
    "slap_bass_2",
    "synth_bass_1",
    "synth_bass_2",
    # Strings family (40-47)
    "violin",
    "viola",
    "cello",
    "contrabass",
    "tremolo_strings",
    "pizzicato_strings",
    "orchestral_harp",
    "timpani",
    # Ensemble family (48-55)
    "string_ensemble_1",
    "string_ensemble_2",
    "synth_strings_1",
    "synth_strings_2",
    "choir_aahs",
    "voice_oohs",
    "synth_voice",
    "orchestra_hit",
    # Brass family (56-63)
    "trumpet",
    "trombone",
    "tuba",
    "muted_trumpet",
    "french_horn",
    "brass_section",
    "synth_brass_1",
    "synth_brass_2",
    # Reed family (64-71)
    "soprano_sax",
    "alto_sax",
    "tenor_sax",
    "baritone_sax",
    "oboe",
    "english_horn",
    "bassoon",
    "clarinet",
    # Pipe family (72-79)
    "piccolo",
    "flute",
    "recorder",
    "pan_flute",
    "blown_bottle",
    "shakuhachi",
    "whistle",
    "ocarina",
    # Synth Lead family (80-87)
    "square_lead",
    "saw_lead",
    "calliope_lead",
    "chiff_lead",
    "charang_lead",
    "voice_lead",
    "fifths_lead",
    "bass_lead",
    # Synth Pad family (88-95)
    "new_age_pad",
    "warm_pad",
    "polysynth_pad",
    "choir_pad",
    "bowed_pad",
    "metallic_pad",
    "halo_pad",
    "sweep_pad",
    # Synth Effects family (96-103)
    "rain_fx",
    "soundtrack_fx",
    "crystal_fx",
    "atmosphere_fx",
    "brightness_fx",
    "goblins_fx",
    "echoes_fx",
    "scifi_fx",
    # Ethnic family (104-111)
    "sitar",
    "banjo",
    "shamisen",
    "koto",
    "kalimba",
    "bagpipe",
    "fiddle",
    "shanai",
    # Percussive family (112-119)
    "tinkle_bell",
    "agogo",
    "steel_drums",
    "woodblock",
    "taiko_drum",
    "melodic_tom",
    "synth_drum",
    "reverse_cymbal",
    # Sound Effects family (120-127)
    "guitar_fret_noise",
    "breath_noise",
    "seashore",
    "bird_tweet",
    "telephone_ring",
    "helicopter",
    "applause",
    "gunshot",
    # Short aliases for the most-used members
    "piano",
    "guitar",
    "bass",
    "synth",
    "strings",
    "organ",
    "harp",
    "lead",
    "pad",
    "sax",
    "sub_bass",
]


def _mk(name: str, program: int, bank: int = 0) -> Callable[..., Instrument]:
    """Return a factory function that builds Instrument nodes.

    Each call to ``_mk`` produces a new closure capturing `name`,
    `program` and `bank`. The closure walks straight into ``Instrument``
    when invoked, which keeps the public namespace consistent with the
    library's no-classes-only-functions rule.
    """

    def make(*children: Node) -> Instrument:
        return Instrument(name=name, program=program, bank=bank, children=children)

    make.__name__ = name
    make.__qualname__ = f"musicky.sounds.instruments.{name}"
    make.__doc__ = (
        f"GM program {program}"
        + (f" (bank {bank})" if bank else "")
        + f" — returns an Instrument named {name!r}."
    )
    return make


# Piano family ----------------------------------------------------------------
acoustic_grand = _mk("acoustic_grand", 0)
bright_piano = _mk("bright_piano", 1)
electric_grand = _mk("electric_grand", 2)
honkytonk = _mk("honkytonk", 3)
electric_piano_1 = _mk("electric_piano_1", 4)
electric_piano_2 = _mk("electric_piano_2", 5)
harpsichord = _mk("harpsichord", 6)
clavinet = _mk("clavinet", 7)

# Chromatic Percussion --------------------------------------------------------
celesta = _mk("celesta", 8)
glockenspiel = _mk("glockenspiel", 9)
music_box = _mk("music_box", 10)
vibraphone = _mk("vibraphone", 11)
marimba = _mk("marimba", 12)
xylophone = _mk("xylophone", 13)
tubular_bells = _mk("tubular_bells", 14)
dulcimer = _mk("dulcimer", 15)

# Organ -----------------------------------------------------------------------
drawbar_organ = _mk("drawbar_organ", 16)
percussive_organ = _mk("percussive_organ", 17)
rock_organ = _mk("rock_organ", 18)
church_organ = _mk("church_organ", 19)
reed_organ = _mk("reed_organ", 20)
accordion = _mk("accordion", 21)
harmonica = _mk("harmonica", 22)
tango_accordion = _mk("tango_accordion", 23)

# Guitar ----------------------------------------------------------------------
nylon_guitar = _mk("nylon_guitar", 24)
steel_guitar = _mk("steel_guitar", 25)
jazz_guitar = _mk("jazz_guitar", 26)
clean_guitar = _mk("clean_guitar", 27)
muted_guitar = _mk("muted_guitar", 28)
overdrive_guitar = _mk("overdrive_guitar", 29)
distortion_guitar = _mk("distortion_guitar", 30)
guitar_harmonics = _mk("guitar_harmonics", 31)

# Bass ------------------------------------------------------------------------
acoustic_bass = _mk("acoustic_bass", 32)
finger_bass = _mk("finger_bass", 33)
pick_bass = _mk("pick_bass", 34)
fretless_bass = _mk("fretless_bass", 35)
slap_bass_1 = _mk("slap_bass_1", 36)
slap_bass_2 = _mk("slap_bass_2", 37)
synth_bass_1 = _mk("synth_bass_1", 38)
synth_bass_2 = _mk("synth_bass_2", 39)

# Strings ---------------------------------------------------------------------
violin = _mk("violin", 40)
viola = _mk("viola", 41)
cello = _mk("cello", 42)
contrabass = _mk("contrabass", 43)
tremolo_strings = _mk("tremolo_strings", 44)
pizzicato_strings = _mk("pizzicato_strings", 45)
orchestral_harp = _mk("orchestral_harp", 46)
timpani = _mk("timpani", 47)

# Ensemble --------------------------------------------------------------------
string_ensemble_1 = _mk("string_ensemble_1", 48)
string_ensemble_2 = _mk("string_ensemble_2", 49)
synth_strings_1 = _mk("synth_strings_1", 50)
synth_strings_2 = _mk("synth_strings_2", 51)
choir_aahs = _mk("choir_aahs", 52)
voice_oohs = _mk("voice_oohs", 53)
synth_voice = _mk("synth_voice", 54)
orchestra_hit = _mk("orchestra_hit", 55)

# Brass -----------------------------------------------------------------------
trumpet = _mk("trumpet", 56)
trombone = _mk("trombone", 57)
tuba = _mk("tuba", 58)
muted_trumpet = _mk("muted_trumpet", 59)
french_horn = _mk("french_horn", 60)
brass_section = _mk("brass_section", 61)
synth_brass_1 = _mk("synth_brass_1", 62)
synth_brass_2 = _mk("synth_brass_2", 63)

# Reed ------------------------------------------------------------------------
soprano_sax = _mk("soprano_sax", 64)
alto_sax = _mk("alto_sax", 65)
tenor_sax = _mk("tenor_sax", 66)
baritone_sax = _mk("baritone_sax", 67)
oboe = _mk("oboe", 68)
english_horn = _mk("english_horn", 69)
bassoon = _mk("bassoon", 70)
clarinet = _mk("clarinet", 71)

# Pipe ------------------------------------------------------------------------
piccolo = _mk("piccolo", 72)
flute = _mk("flute", 73)
recorder = _mk("recorder", 74)
pan_flute = _mk("pan_flute", 75)
blown_bottle = _mk("blown_bottle", 76)
shakuhachi = _mk("shakuhachi", 77)
whistle = _mk("whistle", 78)
ocarina = _mk("ocarina", 79)

# Synth Lead ------------------------------------------------------------------
square_lead = _mk("square_lead", 80)
saw_lead = _mk("saw_lead", 81)
calliope_lead = _mk("calliope_lead", 82)
chiff_lead = _mk("chiff_lead", 83)
charang_lead = _mk("charang_lead", 84)
voice_lead = _mk("voice_lead", 85)
fifths_lead = _mk("fifths_lead", 86)
bass_lead = _mk("bass_lead", 87)

# Synth Pad -------------------------------------------------------------------
new_age_pad = _mk("new_age_pad", 88)
warm_pad = _mk("warm_pad", 89)
polysynth_pad = _mk("polysynth_pad", 90)
choir_pad = _mk("choir_pad", 91)
bowed_pad = _mk("bowed_pad", 92)
metallic_pad = _mk("metallic_pad", 93)
halo_pad = _mk("halo_pad", 94)
sweep_pad = _mk("sweep_pad", 95)

# Synth Effects ---------------------------------------------------------------
rain_fx = _mk("rain_fx", 96)
soundtrack_fx = _mk("soundtrack_fx", 97)
crystal_fx = _mk("crystal_fx", 98)
atmosphere_fx = _mk("atmosphere_fx", 99)
brightness_fx = _mk("brightness_fx", 100)
goblins_fx = _mk("goblins_fx", 101)
echoes_fx = _mk("echoes_fx", 102)
scifi_fx = _mk("scifi_fx", 103)

# Ethnic ----------------------------------------------------------------------
sitar = _mk("sitar", 104)
banjo = _mk("banjo", 105)
shamisen = _mk("shamisen", 106)
koto = _mk("koto", 107)
kalimba = _mk("kalimba", 108)
bagpipe = _mk("bagpipe", 109)
fiddle = _mk("fiddle", 110)
shanai = _mk("shanai", 111)

# Percussive ------------------------------------------------------------------
tinkle_bell = _mk("tinkle_bell", 112)
agogo = _mk("agogo", 113)
steel_drums = _mk("steel_drums", 114)
woodblock = _mk("woodblock", 115)
taiko_drum = _mk("taiko_drum", 116)
melodic_tom = _mk("melodic_tom", 117)
synth_drum = _mk("synth_drum", 118)
reverse_cymbal = _mk("reverse_cymbal", 119)

# Sound Effects ---------------------------------------------------------------
guitar_fret_noise = _mk("guitar_fret_noise", 120)
breath_noise = _mk("breath_noise", 121)
seashore = _mk("seashore", 122)
bird_tweet = _mk("bird_tweet", 123)
telephone_ring = _mk("telephone_ring", 124)
helicopter = _mk("helicopter", 125)
applause = _mk("applause", 126)
gunshot = _mk("gunshot", 127)


# --- Short aliases ------------------------------------------------------------
# These pick the most familiar member of each family so casual users can
# write `piano(...)` without remembering it is `acoustic_grand`. They are
# *the same* maker objects so equality and identity are preserved.

piano = acoustic_grand
guitar = nylon_guitar
bass = finger_bass
synth = square_lead
strings = string_ensemble_1
organ = drawbar_organ
harp = orchestral_harp
lead = square_lead
pad = new_age_pad
sax = alto_sax
# Sub-bass alias: synth_bass_2 has the most low-end body in GM. Pair it
# with the `sub_bass` ADSR profile in render.py for fat club-style lows.
sub_bass = _mk("sub_bass", 39)


# --- Lookup table for `sound()` ----------------------------------------------

# Built directly from the GM Level 1 specification. Aliases like
# `piano` -> `acoustic_grand` are resolved by also storing the alias
# names so `sound("piano")` works without surprise.
_GM_NAMES: tuple[str, ...] = (
    "acoustic_grand",
    "bright_piano",
    "electric_grand",
    "honkytonk",
    "electric_piano_1",
    "electric_piano_2",
    "harpsichord",
    "clavinet",
    "celesta",
    "glockenspiel",
    "music_box",
    "vibraphone",
    "marimba",
    "xylophone",
    "tubular_bells",
    "dulcimer",
    "drawbar_organ",
    "percussive_organ",
    "rock_organ",
    "church_organ",
    "reed_organ",
    "accordion",
    "harmonica",
    "tango_accordion",
    "nylon_guitar",
    "steel_guitar",
    "jazz_guitar",
    "clean_guitar",
    "muted_guitar",
    "overdrive_guitar",
    "distortion_guitar",
    "guitar_harmonics",
    "acoustic_bass",
    "finger_bass",
    "pick_bass",
    "fretless_bass",
    "slap_bass_1",
    "slap_bass_2",
    "synth_bass_1",
    "synth_bass_2",
    "violin",
    "viola",
    "cello",
    "contrabass",
    "tremolo_strings",
    "pizzicato_strings",
    "orchestral_harp",
    "timpani",
    "string_ensemble_1",
    "string_ensemble_2",
    "synth_strings_1",
    "synth_strings_2",
    "choir_aahs",
    "voice_oohs",
    "synth_voice",
    "orchestra_hit",
    "trumpet",
    "trombone",
    "tuba",
    "muted_trumpet",
    "french_horn",
    "brass_section",
    "synth_brass_1",
    "synth_brass_2",
    "soprano_sax",
    "alto_sax",
    "tenor_sax",
    "baritone_sax",
    "oboe",
    "english_horn",
    "bassoon",
    "clarinet",
    "piccolo",
    "flute",
    "recorder",
    "pan_flute",
    "blown_bottle",
    "shakuhachi",
    "whistle",
    "ocarina",
    "square_lead",
    "saw_lead",
    "calliope_lead",
    "chiff_lead",
    "charang_lead",
    "voice_lead",
    "fifths_lead",
    "bass_lead",
    "new_age_pad",
    "warm_pad",
    "polysynth_pad",
    "choir_pad",
    "bowed_pad",
    "metallic_pad",
    "halo_pad",
    "sweep_pad",
    "rain_fx",
    "soundtrack_fx",
    "crystal_fx",
    "atmosphere_fx",
    "brightness_fx",
    "goblins_fx",
    "echoes_fx",
    "scifi_fx",
    "sitar",
    "banjo",
    "shamisen",
    "koto",
    "kalimba",
    "bagpipe",
    "fiddle",
    "shanai",
    "tinkle_bell",
    "agogo",
    "steel_drums",
    "woodblock",
    "taiko_drum",
    "melodic_tom",
    "synth_drum",
    "reverse_cymbal",
    "guitar_fret_noise",
    "breath_noise",
    "seashore",
    "bird_tweet",
    "telephone_ring",
    "helicopter",
    "applause",
    "gunshot",
)

# Map every GM name (and its short alias) to its GM program number.
GM_PROGRAMS: dict[str, int] = {name: i for i, name in enumerate(_GM_NAMES)} | {
    "piano": 0,
    "guitar": 24,
    "bass": 33,
    "synth": 80,
    "strings": 48,
    "organ": 16,
    "harp": 46,
    "lead": 80,
    "pad": 88,
    "sax": 65,
    "sub_bass": 39,
}


def sound(spec: str | int, *children: Node, bank: int = 0) -> Instrument:
    """Build an Instrument by name or by GM program number.

    `spec` may be a string ("acoustic_grand", "808", any registered name)
    or an integer (0-127, used as the program directly). `bank` selects an
    extended bank for SoundFont kits.
    """
    if isinstance(spec, int):
        if not 0 <= spec <= 127:
            raise ValueError(
                f"GM program out of range: {spec}. Valid programs are 0-127.",
            )
        return Instrument(name=f"program_{spec}", program=spec, bank=bank, children=children)

    program = GM_PROGRAMS.get(spec)
    if program is None:
        raise ValueError(
            f"unknown instrument name: {spec!r}. "
            "Pass an integer GM program (0-127), or use one of the "
            f"{len(GM_PROGRAMS)} predefined names. "
            "See musicky.sounds.instruments.GM_PROGRAMS for the full list.",
        )
    return Instrument(name=spec, program=program, bank=bank, children=children)
