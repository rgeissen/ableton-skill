---
name: ableton-skill-sounds
description: >
  Sound design and instrument loading tools for AbletonMCP. Use this skill for: browsing
  Ableton's library, searching sounds by tag, loading instruments or effects onto tracks,
  loading drum kits, placing individual samples onto specific drum-rack pads (building a
  one-shot kit), browsing user-saved presets, reading and tweaking device parameters (synths,
  samplers, effects, racks), and editing audio clips — warp mode, pitch/transpose, gain — for
  tuning vocals, pitching chops, and time-stretch feel. Trigger for any request about finding a
  sound, loading a preset, building a drum kit from samples, tweaking a synth parameter, adjusting
  a filter, setting up an effect chain, drilling into a device rack, tuning or warping a
  vocal/audio clip, or making vocal chops.
compatibility: "Requires ableton-skill skill loaded. Part of the AbletonMCP skill suite."
---

# Sounds — Browser, Instruments & Device Parameters

This skill covers the **Sound Design** stage. Before loading devices, orient with
`get_all_tracks_info()` from the base skill to confirm track indices.

---

## Browser & Loading

| Tool | Purpose | Key params |
|---|---|---|
| `search_by_tags` | **Start here.** Find sounds by tag (AND logic) | `tags[]`, `category?`, `limit?`, `offset?` |
| `search_and_load_sound` | Search + load in one call | `track_index`, `tags[]`, `category?`, `result_index?` |
| `load_sound_by_path` | Load directly from a known browser_path | `track_index`, `browser_path` |
| `load_instrument_or_effect` | Load any device by URI | `track_index`, `uri` |
| `load_drum_kit` | Load Drum Rack + kit together | `track_index`, `rack_uri`, `kit_path` |
| `load_sample_to_drum_pad` | Load a sample onto a **specific** drum pad (by MIDI note) | `track_index`, `pad_note`, `browser_path`, `device_index?` |
| `browse_user_library` | List user presets not in the tag DB | `folder?`, `max_items?` |
| `get_browser_tags` | Discover available tags | `category?`, `prefix?` |
| `get_browser_tree` | Top-level browser categories | `category_type` |
| `get_browser_items_at_path` | Drill into a folder | `path`, `item_type` (all/folder/loadable) |

**User-saved presets** — `search_by_tags` only sees Ableton's SQLite tag database, which
often misses user-created/saved presets. When a preset isn't found by tag, use
`browse_user_library(folder="Presets/Instruments/Operator")` — it walks the live browser and
returns `browser_path`s you pass straight to `load_sound_by_path`.

**Browser categories:** `all` `sounds` `instruments` `drums` `audio_effects` `midi_effects`
`max_for_live` `plugins` `clips` `samples` `grooves` `tunings`

**Preferred workflow — tag search:**
```
search_by_tags(tags=["bass", "warm"], category="sounds")
→ [{name, type, source, browser_path}, ...]
load_sound_by_path(track_index, browser_path)
```
Start with one tag, narrow with two. `browser_path` from search results goes directly to
`load_sound_by_path` — never call `get_browser_items_at_path` just to get a URI from a search result.

**Drum kit workflow:**
```
get_browser_tree("drums") → get_browser_items_at_path(path) → find rack_uri + kit_path
load_drum_kit(track_index, rack_uri, kit_path)
```

**Build a one-shot kit from individual samples** — `load_sound_by_path` only loads onto the
currently-*selected* pad, so it can't place samples deterministically. Use
`load_sample_to_drum_pad`, which selects the target pad first:
```
load_instrument_or_effect(track_index, uri="…/Drum Rack")   # empty rack first
load_sample_to_drum_pad(track_index, pad_note=36, browser_path=".../Kicks/kick.wav")
load_sample_to_drum_pad(track_index, pad_note=38, browser_path=".../Claps/clap.wav")
load_sample_to_drum_pad(track_index, pad_note=42, browser_path=".../Hats/closed.wav")
load_sample_to_drum_pad(track_index, pad_note=46, browser_path=".../Hats/open.wav")
```
Standard General-MIDI pad map: kick 36, snare/clap 38, closed-hat 42, open-hat 46, ride 51.
`browser_path`'s first segment is a browser category (e.g. `user_library/…`); segments are
name-matched, so parentheses in pack folder names are fine. `device_index=-1` (default)
targets the first drum rack on the track.

---

## Device Parameters

Every device on regular, return, and master tracks is reachable via progressive disclosure.

### Track selection
| Target | Params |
|---|---|
| Regular track | `track_index=N` |
| Return track A/B… | `return_track_index=0/1…` |
| Master track | `is_master=True` |

### Read → Drill → Set

```
# Step 1: find device index
get_track_info(track_index, include_devices=True)
→ devices[]: [{index, name, class_name, type}]

# Step 2: read parameters (and discover nested devices in racks)
get_device_params(track_index, device_index)
→ parameters[]: [{index, name, value, min, max}]
→ contents: {type, ...}  ← only if device is a Rack

# Step 3: drill into rack chain (copy chain_path verbatim)
get_device_params(track_index, device_index, chain_path=[...])

# Step 4: set a parameter
set_device_param(track_index, device_index, param_index, value, chain_path?)
```

Value is clamped to the native min/max automatically. Always read first.

### Drum Rack pads
```
get_drum_rack_pads(track_index, device_index)
→ [{note:36, name:"Kick", chains:[...]}]

# Edit a parameter inside a pad (e.g. Simpler attack on Kick):
get_device_params(track_index, device_index,
                  chain_path=[{"pad_note":36,"chain_index":0,"device_index":0}])
set_device_param(..., chain_path=[{"pad_note":36,"chain_index":0,"device_index":0}])
```
`chain_path` is a list — copy it verbatim from the `contents` response.

### chain_path format
```json
{"chain_index": 0, "device_index": 0}                  // Instrument / Effect Rack layer
{"pad_note": 36, "chain_index": 0, "device_index": 0}  // Drum Rack pad layer
```

---

## Common Sound Design Tasks

### Tweak a synth filter
```
get_device_params(track_index=2, device_index=0)
→ [{index:5, name:"Filter Freq", value:1000, min:20, max:20000}]
set_device_param(track_index=2, device_index=0, param_index=5, value=3500)
```

### Adjust reverb on a return track
```
get_device_params(return_track_index=0, device_index=0)
set_device_param(return_track_index=0, device_index=0, param_index=2, value=0.6)
```

### Set a macro on an Instrument Rack
```
get_device_params(track_index=1, device_index=0)
→ {parameters: [{index:0, name:"Macro 1 - Cutoff", ...}], contents: {...}}
set_device_param(track_index=1, device_index=0, param_index=0, value=0.7)
```

---

## Genre Sound-Design Recipes (deep / melodic house — Anjunadeep style)

The whole palette below is achievable with **Ableton stock devices** — `Analog`, `Operator`,
`Wavetable`, `Drum Rack`, and stock effects. Load the device (or a factory preset near the target),
then `get_device_params` → `set_device_param` to shape it. Search presets with `search_by_tags`
or `browse_user_library`; the preset names below are good search seeds.

### Instruments by role
| Role | Best stock synth | Shape it toward… | Preset seeds |
|---|---|---|---|
| **Sub bass** | Operator (sine + subtle FM) / Wavetable | Pure sine low octave, tight envelope, mono | *Sine Sub, FM Sub Bass, Basic Sub* |
| **Warm bass** | Analog | 2 detuned saws (few cents), slow filter-env attack (no click) | *Sub Bass, Fat Sub, Smooth Bass* |
| **Lush pad** | Analog / Wavetable | Detuned saws, **attack 2–3 s / release 5–10 s**, chorus, slow (<1 Hz) LFO→cutoff | *Warm Pad, Atmospheric Pad, Cloud Pad, Drone* |
| **Lead** | Analog / Wavetable | Saw/square, fast attack, vibrato LFO (5–7 Hz, 1–2 st), light unison | *Saw Lead, Bright Lead, Evolving Lead* |
| **Arp** | Operator + **Arpeggiator** MIDI FX | Simple wave, short gate, 1/16 rate | *Plucky Lead, Arpeggiated Synth* |

### MIDI effects (before the instrument)
- **Arpeggiator** — turns held chords into evolving lines. Styles Up / Down / Up-Down / Random;
  rate 1/8–1/16; short **Gate** = percussive arp, long = sustained; add **Velocity Random** for feel.
- **Chord** — trigger full chords from one note (Shift +4 = 3rd, +7 = 5th, +11 = maj7). Stack before
  the Arpeggiator for arpeggiated chords.

### Depth & space (stock effects on returns — see `ableton-skill-mix` for tiers)
| Effect | Setting for this genre |
|---|---|
| **Reverb** | Long decay 2–5 s + pre-delay 20–50 ms on pads/atmos; "Shimmer"/octave-up for sparkle |
| **Delay** / Ping Pong | Tempo-synced (1/4, 1/8, dotted), feedback 20–40 %, ping-pong for width |
| **Chorus / Ensemble** | Subtle — Rate 0.2–0.8 Hz, Depth 1–3 ms, 20–40 % wet — widens pads/leads |
| **Phaser** | Gentle, slow LFO 0.1–0.5 Hz — subtle motion on pads (use sparingly) |

### Drums (Drum Rack layering)
Layer for punch: kick = **sub layer + transient layer**; claps/snares = 2+ stacked samples.
Base on 909/808 kits, then layer **organic percussion** (shaker, rim, ride) for the deep-house groove.
Use `load_sample_to_drum_pad` to place each one-shot on its pad; velocity layers + ghost notes for feel.

### Warm-analog principle (recreating Diva-style tones with stock)
Warmth = **detuned oscillators** (a few cents apart for beating) + a **gentle low-pass with slow
filter-envelope** + a touch of **Saturator**/Chorus. This one recipe underlies most Analog bass,
pad, and lead patches above.

---

## Synthesis Fundamentals (from *Secrets of Dance Music Production*)

**Waveform → use:** Sine = pure → sub, stacks, FX · Triangle = near-pure → soft sub/pad · Square/pulse = odd harmonics → hollow bass, reeds; **PWM** (LFO → pulse width) = shimmer/movement · Saw = all harmonics → leads, pads, aggressive bass · Supersaw = detuned-saw stack → big EDM leads · Noise = risers/falls, grit on pads/keys.

**Oscillator moves:** detune a 2nd osc a few cents = thickness; add a sub-osc 1–2 octaves down; **unison/spread** on pads & leads; osc **sync + detune** = metallic/aggressive.

**Filter:** low-pass is the start of ~99 % of bass. Cutoff = −3 dB point; high **resonance** self-oscillates (303 scream). Slopes: **12 dB gentle, 24 dB steep**. Key-tracking raises cutoff with pitch.

**ADSR by role:** pad/string = **long attack + long release + high sustain** (swell) · punchy bass/arp = **short attack, medium decay/sustain** so the transient bursts through · use a **filter envelope** for per-note movement. **LFO** < 20 Hz, sync to tempo (16th vibrato, 4-bar sweep); note-on retrigger locks it to the groove.

**Synthesis types:** FM (sine operators) = bells/metallic → **Operator** · Wavetable = evolving, modulate WT-position → **Wavetable** · additive = organ drawbars · granular/physical-modelling = textures.

### Patch recipes
- **Lead:** detune multi-osc across octaves (or supersaw stack) + a little noise for bite; fast attack/release keeps it forward; modulate by velocity/keytrack/mod-wheel. Loves tape delay + reverb after.
- **Arp:** shorter env than a lead (instant attack, short D/S/R); route velocity or keynote → cutoff; automate filter open + sustain up to build pressure before a drop.
- **Pad:** saw/square (warm) or triangle (cold), long attack + release, LP cutoff pulled back till it recedes + small resonance, EQ off the lows, a 2nd osc an octave up/down; movement via slow LFO → cutoff.
- **FX riser/fall:** to *raise* energy — open filters, raise pitch, speed up modulation (reverse for falls). Long FX: decay/sustain 100 %, draw a 1/4/8/16-bar MIDI note; layer a 1-bar fill + 16-bar rise + 32-bar reverse whoosh; sidechain sustained FX to the kick.

---

## Drum Synthesis & Layering

**Synthesise a kick:** sine osc + amp env ~300 ms (zero attack, short release); **pitch envelope** sweeping ~E4 (330 Hz) → E1 (41 Hz); add a "thump" at E3 (165 Hz), 10–60 ms, for body. (Trance kick opens higher, ~E6.) **Snare** = that kick template + a **noise osc** for snap. **Hat** = filtered white noise, amp sustain 0, decay ~50 ms, high-pass to kill lows + resonance for bite.

**Layering (do it with intent):**
- Time-shift layers to gel as one hit, or stagger for a wider feel.
- **PHASE is critical** — layered kicks cancel low end if their transients fire in opposite directions; zoom the waveforms, and **flip one sample's polarity** if they don't start the same way. Re-check after *any* start-time change.
- EQ so each layer owns a band; **choke/mute group** so an open hat is cut by the next closed hat. Bus all layers to one drum group for glue, then **bounce to a single sample**.
- Velocity multisample: map louder hits to brighter samples, quiet hits to duller ones, for organic variation.

---

## Sampling & Resampling

**Warp modes (Ableton):** try every mode per source — **Complex Pro** for vocals/tonal, **Texture** for atmospheric/metallic, a transient-preserving mode for drums. Vocal pitch-up without chipmunk = Complex Pro + Transpose; pull **Formants → 0** to *get* the chipmunk effect; in Texture, **Flux → 0** = more solid. Extreme stretch = artefacts (worst when slowing down) — solo to check.

**Chopping breaks (amen etc.):** slice at transients → retrigger/reorder/repitch. Rule: warp so every **kick lands on the beat**, leave the swing in the spaces. **Convert to New MIDI Track** to study a break's velocity/timing and reuse the groove.

**Zero crossings:** set all sample start/end/loop points at zero crossings (or add short fades) to avoid clicks.

**Resampling & lo-fi:** stack processing by **Freeze → Flatten → drag the audio onto a new Sampler** and process again (effectively infinite). Old-school lo-fi = **Redux** bit/sample-rate reduction (12-bit = Linn/MPC chunk, SP-1200 ≈ 26 kHz/8-bit) + a touch of saturation before the reduction; bounce, reload, repitch.

**Vocal chops (Sampler):** set Vol < Vel = 0 %, route **Velocity → Sample Offset**, then draw rhythmic MIDI with varied velocities to scrub the start point — instant percussive chops.

---

## Audio-Clip Editing & Vocal Tuning

Recorded/imported **audio clips** (vocals, samples, loops) have their own warp/pitch/gain — the controls for tuning a vocal, choosing a time-stretch feel, and gain-staging. Read first, then set:

| Tool | Purpose | Key params |
|---|---|---|
| `get_audio_clip_properties` | Read warp / pitch / gain of an audio clip | `track_index`, `clip_index` |
| `set_audio_clip_properties` | Set any of them (only what you pass changes) | `warp_mode?`, `warping?`, `pitch_coarse?`, `pitch_fine?`, `gain?` |

**Warp modes** (`warp_mode`, by name — setting it turns Warp on):

| Mode | Best for |
|---|---|
| **Complex Pro** | **vocals** & tonal material — keeps formants natural when stretched |
| Complex | full mixes / busy audio |
| Tones · Texture | monophonic tonal / pads & atmospheres |
| Re-Pitch | ties pitch to tempo — tape / chipmunk / "alien" effect |
| Beats | drums & rhythmic loops (transient-preserving) |

- **Tune a vocal into key:** `set_audio_clip_properties(warp_mode="Complex Pro", pitch_coarse=<semitones>, pitch_fine=<cents>)`. `pitch_coarse` −48…+48 st, `pitch_fine` −49…+49 ct.
- **Chipmunk / alien vocal:** `warp_mode="Re-Pitch"` (pitch follows the stretch), or pitch a Complex-Pro clip up ±12.
- **Gain-stage:** `gain` is **0.0–1.0 and non-linear** (~0.4 ≈ 0 dB unity, ~0.6 ≈ +8 dB) — read `gain_display` in the result for the real dB.
- For rhythmic **vocal chops**, prep pitch/warp here, then use the Sampler velocity→Sample-Offset trick above.
