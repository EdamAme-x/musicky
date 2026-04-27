# musicky

バイブで音楽を作るための Python ライブラリ。READMEがそのままドキュメントです。

## Installation

Currently distributed via git only:

```bash
pip install git+https://github.com/EdamAme-x/musicky.git
```

Or pull the repo and use [uv](https://github.com/astral-sh/uv) for development:

```bash
git clone https://github.com/EdamAme-x/musicky.git
cd musicky
uv sync --extra dev
```

You also need the `libfluidsynth` shared library since the default
audio engine renders through real SoundFont samples:

- Debian / Ubuntu: `apt install libfluidsynth3`
- macOS: `brew install fluid-synth`
- Windows: ship with the FluidSynth installer or use Chocolatey

The first call to `output(music, "song.wav")` automatically downloads a
~50 MB free SoundFont (MuseScore's MS Basic) into `~/.cache/musicky/`.
Set `MUSICKY_SOUNDFONT=/path/to/your.sf2` to use your own instead.

## The shape of a musicky piece

Everything is a function call, and the call tree IS the signal flow. A
DAW screenshot translates almost line-for-line:

```python
from musicky import (
    musicky, clip, chord, scale, prog,
    piano, bass, guitar, drums, strings,
    reverb, lowpass, eq, limiter, normalize, master,
    seq, play, output, dump,
    create_midi_context,
)

verse        = chord("C5, E5, G5, C6")
chorus_chord = prog(scale("C major"), "1,5,6,4")

music = musicky(
    master(
        normalize(),
        limiter(threshold=-0.5),

        reverb(
            piano(
                clip(verse, at=0),
                clip(chorus_chord, at=4),
                clip(verse, at=8),
            ),
            amount=0.3,
        ),

        lowpass(
            bass(clip(chord("C2, G2, A2, F2", interval=1.0), at=0)),
            cutoff=400,
        ),

        drums(clip(chord("C2, C2, G2, C2", interval=1.0), at=0)),
    ),
    bpm=110,
    name="hello",
)

dump(music)                                     # pretty JSON to stdout
play(music, create_midi_context("./song.mid"))  # write SMF
output(music, "./song.wav")                     # real instruments via SoundFont
```

Read the tree like a wiring diagram: each `reverb(...)` etc. wraps
whatever is inside. `master(...)` is just a visual marker for the final
chain — it has no effect of its own.

A larger, fully arranged demo lives in [`example.py`](./example.py)
— a vocaloid-style backing track in A minor. Run it to produce
`example.mid` and `example.wav`.

## The pieces

### Primitives — pure musical data

```python
note("C5")                          # a single note (also: Eb4, F#-1, ...)
note(60)                            # by MIDI pitch
chord("C5, E5, G5")                 # a block chord
chord("C5, E5, G5", interval=0.25)  # an arpeggio (interval > 0)
chord([60, 64, 67])                 # MIDI numbers also work
scale("C major")                    # a scale
prog(scale("C major"), "1,5,6,4")   # I-V-vi-IV progression
tx(chord("C4, E4, G4"), 7)          # transpose +7 semitones
octave(chord("C4, E4, G4"), -1)     # drop one octave
```

### Clips — content placed on the timeline

```python
clip(content)             # at = 0 (default)
clip(content, at=4)       # starts at beat 4
sample("hit.wav", at=8)   # external audio file dropped onto the timeline
```

### Instruments — every General MIDI program is a function

All 128 GM instruments are individual functions. Short aliases pick
the most familiar member of each family:

```python
piano(*children)            # alias of acoustic_grand (GM 0)
guitar(*children)           # alias of nylon_guitar (GM 24)
bass(*children)             # alias of finger_bass (GM 33)
synth(*children)            # alias of square_lead (GM 80)
strings(*children)          # alias of string_ensemble_1 (GM 48)
sax(*children)              # alias of alto_sax (GM 65)
sub_bass(*children)         # synth_bass_2 with a sub-friendly ADSR
```

The full set of 128 programs (`acoustic_grand`, `bright_piano`,
`distortion_guitar`, `slap_bass_1`, `synth_strings_1`, `square_lead`,
`warm_pad`, `kalimba`, `taiko_drum`, `gunshot` …) is available as
direct imports. For dynamic dispatch use `sound`:

```python
sound("harpsichord", clip(...))    # by name
sound(40, clip(...))               # by GM program number
sound("808", clip(...), bank=25)   # bank for SoundFont kits
```

### Drum kits — 25+ kits, all on channel 9

```python
drums(*children)            # standard kit
tr808(*children)            # Roland TR-808 emulation
tr909(*children)
electronic_kit, dance_kit, techno_kit, hiphop_kit, jungle_kit,
house_kit, trap_kit, analog_kit,
jazz_kit, brush_kit, orchestra_kit,
ethnic_kit, latin_kit, taiko_kit,
lofi_kit, garage_kit, industrial_kit, tribal_kit,
room_kit, power_kit, rock_kit, sfx_kit,
```

### Drum elements — write beats with named hits

```python
drums(
    seq(
        kick(at=0),
        closed_hat(at=0.5, velocity=70),
        snare(at=1),
        closed_hat(at=1.5, velocity=70),
    ),
)
```

Available helpers:

```python
kick, kick2, side_stick, snare, snare2, clap, rim,
closed_hat, pedal_hat, open_hat,
crash, crash2, ride, ride_bell, splash, china,
low_tom, low_mid_tom, mid_tom, high_mid_tom, high_tom, low_floor, high_floor,
tambourine, cowbell, vibraslap,
low_bongo, high_bongo,
mute_conga, open_conga, low_conga,
low_timbale, high_timbale,
low_agogo, high_agogo,
shaker, cabasa, maracas,
short_whistle, long_whistle, short_guiro, long_guiro,
claves, wood_block_high, wood_block_low,
mute_cuica, open_cuica, mute_triangle, open_triangle,
hit(pitch=42, at=0),     # any drum-map MIDI pitch
```

### Effects — wrap children to transform them

Symbolic (operates on chord data before synthesis):

```python
humanize(...,   timing=0.02, velocity=8, seed=42)
quantize(...,   grid=0.25)
transpose(...,  semitones=2)
swing(...,      amount=0.1)
arpeggiate(..., interval=0.125)
```

Audio (operates on PCM samples after synthesis):

```python
reverb(...,     amount=0.3, decay=1.5)
lowpass(...,    cutoff=1000)            # cutoff also accepts auto(...)
highpass(...,   cutoff=200)
eq(...,         low=0, mid=0, high=0)   # dB on each band
compressor(..., threshold=-12, ratio=4)
distortion(..., drive=2.0, mix=1.0)
delay(...,      time=0.25, feedback=0.4, mix=0.3)
chorus(...,     rate=1.5, depth=0.005, mix=0.5)
normalize(...,  peak=0.95)
limiter(...,    threshold=-0.5)

# Movement / character
vibrato(...,    rate=5.0, depth=0.005)
tremolo(...,    rate=5.0, depth=0.5)
wobble(...,     rate=2.0, low=200, high=4000)
saturate(...,   amount=1.5, warmth=0.5)
gain(...,       db=0.0)                 # also accepts auto(...)
duck(...,       by=0.6, rate=2.0)       # periodic side-chain duck
sidechain(...,  source=kick_pattern, amount=0.7)
```

### Patterns — composition shortcuts

```python
arp(progression, interval=0.125)        # spread chords as fast arpeggios
hold(progression, duration=4.0)         # hold each chord for N beats (pads)
pump(progression, sub=8)                # 8th-note bassline on chord roots
phrase(piano, [a, b, c], transpose=2)   # play chords in sequence on an instrument
hits(kick, 0.0, 1.0, 2.0, 3.0)          # drum positions to clip list
move(clips, by=8.0)                     # shift a clip list in time
grooves.full(bars=4)                    # 4-on-the-floor with snare on 2&4
grooves.sparse(bars=4)                  # verse-friendly groove
grooves.intro(bars=4)                   # hi-hats only
grooves.break_(bars=4)                  # crash + claps
grooves.outro(bars=2)                   # half-time fadeout
```

### Time helpers

```python
seq(a, b, c)            # play in sequence (auto-shifts by length)
at(beats, node)          # place a node at an absolute beat
shift(node, by=4.0)      # move every clip below by N beats
length(node)             # total length in beats
```

### Audio output (wav / mp3 / ogg / flac)

```python
output(music, "song.wav")                          # default: SoundFont (fluidsynth)
output(music, "song.wav", engine="sine")           # built-in waveform engines
output(music, "song.wav", engine="triangle")
output(music, "song.wav", engine="square")
output(music, "song.wav", engine="saw")
output(music, "song.wav", engine="additive",
       harmonics=(1.0, 0.5, 0.25, 0.125))

# Custom SoundFont
output(music, "song.wav", soundfont="./MyKit.sf2")

# mp3/ogg/flac require ffmpeg on PATH
output(music, "song.mp3")
```

### Reusable presets with `custom`

```python
from musicky import custom, reverb

soft_reverb = custom(reverb, amount=0.1)

music = musicky(
    soft_reverb(piano(clip(a))),
    soft_reverb(bass(clip(b)), amount=0.2),  # call-site overrides win
    bpm=110,
)
```

The wrapper keeps the original function's name and docstring, so
`help()` and IDE tooltips still work.

### Automation — values that change over time

```python
from musicky import auto, lowpass

sweep = auto([(0, 200.0), (16, 8000.0)])   # filter sweep across 16 beats
lowpass(piano_part, cutoff=sweep)
```

`auto(...)` accepts a list of `(beat, value)` control points and
linearly interpolates between them. Currently usable on `lowpass`,
`highpass`, and `gain` parameters.

## Inspecting a piece

```python
from musicky import dump

dump(music)                # pretty JSON to stdout
dump(music, "music.json")  # to file
```

Every dataclass is tagged with `__type__` so the JSON is unambiguous.

## Development

```bash
git clone https://github.com/EdamAme-x/musicky.git
cd musicky
uv sync --extra dev

uv run pytest
uv run ruff check .
uv run ruff format .
uv run mypy

uv run python example.py   # renders example.mid + example.wav
```

## License

MIT
