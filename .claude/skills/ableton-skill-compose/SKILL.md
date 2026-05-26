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
| `add_notes_to_clip` | Write notes (replaces all) | `track_index`, `clip_index`, `notes[]` |
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
Pitch 60 = C3 in Live. `add_notes_to_clip` **replaces** all notes — use `get_clip_notes` first to preserve.

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
