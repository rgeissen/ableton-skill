---
name: ableton-skill-compose
description: >
  Composition and arrangement tools for AbletonMCP. Use this skill for: creating MIDI or
  audio tracks, writing clips and notes, generating chords/progressions/bass lines/melodies,
  humanizing patterns, arranging clips (duplicate, delete, fire, stop), naming and coloring
  tracks, setting scale/tempo. Trigger for any request about writing music, building a beat,
  creating a pattern, composing a progression, or structuring an arrangement.
compatibility: "Requires ableton-skill skill loaded. Part of the AbletonMCP skill suite."
---

# Compose — Tracks, Clips & Music Generation

This skill covers the **Basic Beat** and **Arrangement** stages. Orient yourself first with
`get_all_tracks_info()` from the base skill, then use the tools below.

> For deep music theory — scales, chord recipes, genre bass details, melody parameters —
> invoke the **ableton-skill-theory** skill.

---

## Song-Building Foundations

**Rule of 3 or 4 — build the core idea from just 4 elements:** **Chords · Melody · Bass · Drums.**
Get these locked as an 8-bar loop before adding anything else. Limited palette = faster decisions.

**The layering framework** — each musical role is itself a stack of layers, not a single sound:
- **Harmony** = main chord/pad + a *rhythm layer* (pluck) + an *arp layer* — split across low/high instruments
- **Melody** = lead + a *swell layer* + a *rhythm layer* (pluck) — again low/high
- **Bass** = aligned to the harmony/melody rhythm (locks the groove)
- Plus **Ambience** (sample/texture), **Drums**, and a **Drone** (great as a track starter)

**Genre defaults (deep / melodic house, Anjunadeep style):** 120–128 BPM (**125** is the sweet
spot) · minor or **minor-7th** chords · four-on-the-floor kick · claps/snares on beats 2 & 4 ·
off-beat hats, 1/16 hats for energy · sub bass sitting *between* the kicks. Set the key with
`set_scale_mode` so every `generate_*` call inherits it.

**Chord progressions that work** (full rules in `ableton-skill-theory`):
- **Magic chords:** degrees **1 · 4 · 5 · 6** — hard to go wrong
- **Resolve** with a cadence: **5→1** or **4→1**; leave it **hanging** with a half-cadence (any→5, 1→4)
- **Parallel harmony** — transpose a whole chord *shape* up/down by a fixed interval for that
  "alien", emotional melodic-house sound (voice-leading rules deliberately ignored)

**Drum programming:** strong beats = 1 & 3, weak = 2 & 4, off-beat = the "and" between beats.
Add life with **velocity**, **note length**, **polyrhythm**, and **swing (on weak beats only)**.
Use quiet **ghost notes** for bounce. ADSR: sustain is a *level*, the rest are *times* — release is
rarely used on drums; lowering sustain thins the body while keeping the transient punchy.

---

## Melody & Phrase Construction

A memorable melody isn't random notes — build it from a **motif** and develop it (this is what
`generate_melody` seeds; take its output and shape it further):

**Motif** = a short, memorable cell (2–5 notes). Restate it, then **develop** it — pick from:
`repetition · transposition · sequence · variation · fragmentation · interval-change · rhythm-change ·
inversion · retrograde · augmentation (longer) · diminution (shorter) · extension · truncation`.
Repetition-with-variation is what makes a hook stick.

**Phrase = a musical sentence.** Pair two into **call & response**:
- **Antecedent** ("question") — ends on a **half cadence** (hangs, unresolved)
- **Consequent** ("answer") — ends on an **authentic cadence** (resolves home)

Practically: `generate_melody(..., bars=2, contour="ascending")` for the antecedent, then a second
2-bar phrase `contour="descending"` ending on a chord tone for the consequent. Combine → a complete
4-bar melody. (This mirrors the A/B "call, then call-and-response" arrangement idea in `ableton-skill-arrange`.)

**Chord–melody relationship:** land **chord tones** on strong beats (stable), pass through
**non-chord tones** on weak beats (tension) — the melody breathes with the harmony.

---

## Groove & Feel

Beyond straight 16ths — the feel choices that give a beat its character:

- **Swing / shuffle** — delay the off-beat 8ths (long-short) instead of even. Apply via `humanize_notes`
  timing or Live's groove pool; swing lives on the **weak** beats. Shuffle = a stronger triplet swing.
- **Syncopation** — deliberately accent the off-beats / "&"s so the groove pushes and pulls against the
  pulse. The engine of funk, house, and most electronic grooves.
- **Triplets** — divide the beat into 3 (vs. straight 2/4) for rolls, fills, and a rounder feel.
- **Compound meter (6/8, 12/8)** — the beat itself divides in 3; `set_time_signature(6, 8)` for a
  lilting, rolling groove.
- **Harmonic rhythm** — how *often* chords change (1 per bar = spacious, 2 per bar = driving). Slowing
  it under a busy melody, or speeding it in a build, controls energy independently of the notes.

**Reharmonization** — to vary a repeated 8-bar loop without touching the melody, change the chords
underneath it (swap within a functional area, or add a secondary dominant — see `ableton-skill-theory`).
A key weapon against the "8-bar loop trap".

---

## Beat Programming (numeric, from *Secrets of Dance Music Production*)

**The grid:** 16 steps = 1 bar (4/4). Four-to-the-floor kick on steps **1, 5, 9, 13**; hats on the off-beat 8ths; claps/snares on beats 2 & 4. Downbeat = 1, upbeat = 4, off-beats = 2 & 4 and the "&"s.

**Genre tempo:** chillout 75–100 · **house/techno 120–128** · trance 130–145 · D&B 150–180 · hardcore 180+.

**Velocity for groove:** keep the **kick velocity constant** (esp. four-to-floor); keep snare/clap mostly constant; vary hats & percussion freely. Off-beats ~**50 %** velocity for an organic feel. Map **velocity → LP cutoff** so quiet hits are also duller = depth. (A longer note *sounds* louder — map length → velocity for a dynamics illusion.)

**Swing % by genre** (delays every 2nd 16th; 50 % = straight): house **60–65** · deep house **55–60** · techno **50–65** (often manual per-element) · garage/2-step **55–65** · dubstep **50–70** · trance **55–70** · chillout **50–75**. Multi-swing (hats 54 % while a wonky perc 66 %) = vibe; classic disco = a swung bass over a straight 4/4. In Ableton, apply via the **Groove Pool**.

**Placement feel:** a hit *before* the beat = urgent; *after* = lazy. Nudge snares/claps a few ms off-grid, and stagger the kick & snare so their transients don't collide (de-mask).

---

## Bass Lines — Archetypes & Programming

Pick an archetype for the genre, then keep it simple (modulated basslines rarely exceed **3 notes** and nearly always resolve to the root):

| Archetype | Genre | Character |
|---|---|---|
| **Off-beat** | disco, synth-pop, trance | notes *between* each kick — driving pulse, supplies the root |
| **Root rhythm** | house | sticks to root, freed from the off-beat for rhythmic interest |
| **Noodle** | funk, disco (Chic) | busy, skips octaves, returns to root; needs subtle glide, works over simple beats |
| **Bass as lead** | D&B, dubstep, EDM | the melodic star; spans subs + upper octaves |
| **Ostinato** | jacking house | one repeating groove under shifting elements |
| **Modulated** | Reese, dubstep wobble | 2–3 notes, LFO/env on cutoff & wavetable |
| **No bass** | some techno | a long-sustain 808 does the low-frequency work |

**Programming:** start with the chord root; add the 5th or major/minor 3rd as stepping stones; use **passing notes** (outside the chord) for fluid, jazzy movement. A bass note can *change the chord* above a static triad (root/3rd/5th under one pad), or move under a progression without changing it. Keep it **monophonic**, and always mind the **kick+bass relationship** (see `ableton-skill-mix` — write notes between the kicks, sub = sine/triangle, keep it mono).

---

## Track Management

| Tool | Purpose | Key params |
|---|---|---|
| `create_midi_track` | New MIDI track | `index` (-1 = end) |
| `create_audio_track` | New audio track | `index` (-1 = end) |
| `set_track_name` | Rename a track | `track_index`, `name` |
| `set_track_color` | Color-code a track | `track_index`, `color` (#RRGGBB) |
| `duplicate_track` | Clone track with devices + clips | `track_index` |
| `set_track_arm` | Arm/disarm for recording | `track_index`, `arm` |
| `delete_track` | Remove a track | `track_index` |

**Color conventions** — consistent coloring makes sessions navigable at a glance:

| Role | Suggested color |
|---|---|
| Kick / Drums | `#FF2200` red |
| Bass | `#8800FF` purple |
| Chords / Pads | `#00AAFF` blue |
| Melody / Lead | `#FFCC00` yellow |
| Percussion / Perc | `#FF8800` orange |
| FX / Atmosphere | `#008888` teal |
| Vocals | `#FF44AA` pink |
| Reference / Bus | `#888888` grey |

---

## Clip Editing

| Tool | Purpose | Key params |
|---|---|---|
| `create_clip` | Empty MIDI clip in a slot | `track_index`, `clip_index`, `length` (beats) |
| `add_notes_to_clip` | Write notes (**replaces** by default; `replace=False` appends) | `track_index`, `clip_index`, `notes[]`, `replace?` |
| `get_clip_notes` | Read existing notes | `track_index`, `clip_index` |
| `remove_notes_from_clip` | Delete notes by pitch/time range | `track_index`, `clip_index`, `from_pitch?`, `pitch_span?`, `from_time?`, `time_span?` |
| `set_clip_name` | Name a clip | `track_index`, `clip_index`, `name` |
| `set_clip_color` | Color-code a clip | `track_index`, `clip_index`, `color` (#RRGGBB) |
| `set_clip_loop` | Set loop region | `track_index`, `clip_index`, `looping?`, `loop_start?`, `loop_end?` |
| `duplicate_clip` | Copy to another slot | `track_index`, `clip_index`, `target_clip_index`, `target_track_index?` |
| `delete_clip` | Remove a clip | `track_index`, `clip_index` |
| `fire_clip` | Launch a clip | `track_index`, `clip_index` |
| `stop_clip` | Stop a playing clip | `track_index`, `clip_index` |
| `create_track_with_clip` | Track + clip + notes in one call | `track_name`, `notes[]`, `clip_length`, `clip_name?` |

**Note format:**
```json
{"pitch": 60, "start_time": 0.0, "duration": 0.5, "velocity": 100, "mute": false}
```
Pitch 60 = C3 in Live. `add_notes_to_clip` **replaces** the clip's notes by default (clears first, then writes) — pass `replace=False` to append. To edit existing content, `get_clip_notes` → modify → write back.

---

## Music Generation

All tools return note dicts with **no side effects**. Pass `notes` to `add_notes_to_clip`
or `create_track_with_clip` to write into Live. Always `humanize_notes` last.

| Tool | Purpose | Key params |
|---|---|---|
| `generate_chord` | Single chord | `root_note?`, `chord_type`, `voicing`, `scale_name?` |
| `generate_chord_progression` | Diatonic progression | `degrees[]`, `root_note?`, `scale_name?`, `bars_per_chord?`, `voicing?` |
| `generate_bass_pattern` | Genre bass line | `root_note?`, `scale_name?`, `style`, `bars?`, `octave?` |
| `generate_melody` | Melodic phrase | `root_note?`, `scale_name?`, `bars?`, `density?`, `contour?` |
| `humanize_notes` | Human-feel micro-variation | `notes[]`, `timing_amount?`, `velocity_amount?`, `seed?` |

**Scale & key:** all `root_note` / `scale_name` params are optional — tools auto-read Ableton's
current scale when omitted. Set the key in Live's Scale panel for hands-free context.

**Bass styles:** `deep_house` `techno` `hip_hop` `funk` `reggae` `drum_and_bass` `afrobeats` `pop` `latin` `jazz`

**Contours:** `arch` (default) `ascending` `descending` `static` `random`

---

## Scale & Tempo

| Tool | Purpose | Key params |
|---|---|---|
| `set_scale_mode` | Set key/scale in Live | `root_note` (0–11), `scale_name`, `in_key` (bool) |
| `set_tempo` | Change BPM | `tempo` (float) |

---

## Typical Compose Workflow

```
# 1. Start with key context
get_scale_mode()   → root=9 (A), scale="minor"

# 2. Chord progression
generate_chord_progression(degrees=[1,6,3,7], root_note="A3", scale_name="minor", bars_per_chord=1)
humanize_notes(notes, timing_amount=0.02, velocity_amount=10)
create_track_with_clip(track_name="Chords", notes=..., clip_length=4.0)
set_track_color(track_index=N, color="#00AAFF")

# 3. Bass
generate_bass_pattern(style="deep_house", root_note="A2", bars=4)
humanize_notes(notes, timing_amount=0.01, velocity_amount=6)
create_track_with_clip(track_name="Bass", notes=..., clip_length=16.0)
set_track_color(track_index=N, color="#8800FF")

# 4. Melody
generate_melody(root_note="A4", scale_name="minor", bars=2, contour="arch")
humanize_notes(notes, timing_amount=0.025, velocity_amount=12)
create_track_with_clip(track_name="Lead", notes=..., clip_length=8.0)
set_track_color(track_index=N, color="#FFCC00")

# 5. Vary: duplicate clip → edit notes → write back
duplicate_clip(track_index=N, clip_index=0, target_clip_index=1)
get_clip_notes(N, 1) → modify → add_notes_to_clip(N, 1, modified)
```
