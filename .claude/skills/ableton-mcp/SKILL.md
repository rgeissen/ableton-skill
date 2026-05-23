---
name: ableton-mcp
description: >
  Control Ableton Live directly via the AbletonMCP server. Use this skill whenever the user
  wants to interact with Ableton Live — including creating tracks, building beats or melodies,
  composing MIDI patterns, loading instruments or drum kits, controlling playback, adjusting
  tempo, mixing (volume/pan/mute/solo), editing device parameters, browsing the Live library,
  duplicating or deleting clips and tracks, reading back MIDI notes, generating chords,
  progressions, bass patterns or melodies, or automating any session workflow. Trigger this
  skill for any request mentioning Ableton, Live, tracks, clips, MIDI, beats, drums,
  instruments, BPM, mix, mute, solo, device, synth, chord, bass line, melody, scale, key,
  or session control — even if phrased casually ("make a beat", "add a bass line", "write
  a chord progression in D minor", "solo that track", "turn up the filter", "save the set").
  Always use this skill before attempting to operate Ableton via the browser/keyboard.
compatibility: "Requires AbletonMCP MCP server running as a Remote Script in Ableton Live's MIDI preferences."
---

# Ableton MCP Skill

Control Ableton Live via the AbletonMCP MCP server. The server communicates directly with
Live's Python API — changes are instant and reflected in the session in real time.

> For music theory, scales, chord voicings, genre bass patterns, and melody generation —
> see the [Music Theory Guide](#music-theory-guide) section at the bottom of this document.

---

## First Step: Always Orient Yourself

Before making any changes, call `get_session_info(include_track_names=True)` to understand
the current state (tracks, tempo, time signature). For a quick structured overview of all
tracks, prefer `get_all_tracks_info()` — it returns type, mute, solo, volume, device count,
and clip count for every track in one call. Only call `get_track_info` for tracks you need
to inspect in detail (clips, device names).

**Never assume track indices** — they shift when tracks are added/deleted. Always verify.

---

## Complete Tool Reference

### Session
| Tool | Purpose | Key params |
|---|---|---|
| `get_session_info` | Session overview — tempo, time sig, track/return counts | `include_track_names` (bool) |
| `get_all_tracks_info` | Compact summary of every track (type, mute, solo, vol, device/clip count) | — |
| `set_tempo` | Change BPM | `tempo` (float) |
| `start_playback` | Press Play | — |
| `stop_playback` | Press Stop | — |
| `get_playback_position` | Current beat position + is_playing state | — |
| `get_scale_mode` | Get current root note and scale name from Ableton | — |
| `set_scale_mode` | Set root note, scale name, and/or in-key highlighting | `root_note` (0–11), `scale_name`, `in_key` (bool) |
| `undo` | Undo the last action | — |

### Tracks
| Tool | Purpose | Key params |
|---|---|---|
| `create_midi_track` | Add a new MIDI track | `index` (-1 = end) |
| `create_audio_track` | Add a new audio track | `index` (-1 = end) |
| `get_track_info` | Inspect a single track in detail | `track_index`, `include_clips` (bool), `include_devices` (bool) |
| `set_track_name` | Rename a track | `track_index`, `name` |
| `set_track_mixer` | Set volume and/or pan | `track_index`, `volume` (0.0–1.0), `panning` (-1.0 to 1.0) |
| `set_track_mute` | Mute or unmute | `track_index`, `mute` (bool) |
| `set_track_solo` | Solo or unsolo | `track_index`, `solo` (bool) |
| `delete_track` | Remove a track entirely | `track_index` |

### Clips
| Tool | Purpose | Key params |
|---|---|---|
| `create_clip` | Create empty MIDI clip in a slot | `track_index`, `clip_index`, `length` (beats, default 4.0) |
| `get_clip_notes` | Read back MIDI notes from a clip | `track_index`, `clip_index` |
| `add_notes_to_clip` | Write MIDI notes into a clip (replaces existing) | `track_index`, `clip_index`, `notes[]` |
| `set_clip_name` | Rename a clip | `track_index`, `clip_index`, `name` |
| `duplicate_clip` | Copy a clip to another slot (same or different track) | `track_index`, `clip_index`, `target_clip_index`, `target_track_index?` |
| `delete_clip` | Remove a clip from a slot | `track_index`, `clip_index` |
| `fire_clip` | Launch/trigger a clip | `track_index`, `clip_index` |
| `stop_clip` | Stop a playing clip | `track_index`, `clip_index` |

### Composite (Multi-Step in One Call)
| Tool | Purpose | Key params |
|---|---|---|
| `create_track_with_clip` | Create MIDI track + clip + notes in one call | `track_name`, `notes[]`, `clip_length`, `clip_index`, `clip_name?`, `track_index?` |
| `search_and_load_sound` | Search browser by tags and load onto a track in one call | `track_index`, `tags[]`, `category?`, `result_index?` |

### Devices (Instruments & FX)
| Tool | Purpose | Key params |
|---|---|---|
| `load_instrument_or_effect` | Load any device from browser onto a track | `track_index`, `uri` |
| `load_drum_kit` | Load Drum Rack + kit in one step | `track_index`, `rack_uri`, `kit_path` |
| `get_device_params` | Get parameters of any device (top-level or nested). Returns `contents` map with ready-to-use `chain_path` values when the device is a rack. | `track_index`, `device_index`, `chain_path?`, `return_track_index?`, `is_master?` |
| `set_device_param` | Set a parameter value by index on any device (top-level or nested) | `track_index`, `device_index`, `param_index`, `value`, `chain_path?`, `return_track_index?`, `is_master?` |
| `get_drum_rack_pads` | List loaded drum rack pads: MIDI note, name, mute/solo, chain names | `track_index`, `device_index`, `return_track_index?`, `is_master?` |

### Browser
| Tool | Purpose | Key params |
|---|---|---|
| `get_browser_tree` | List top-level browser categories | `category_type` (all / instruments / sounds / drums / audio_effects / midi_effects) |
| `get_browser_items_at_path` | Drill into a folder — returns immediate children with `path` hints on subfolders | `path`, `item_type` ("all" / "folder" / "loadable") |
| `get_browser_tags` | List tags available in the browser database | `category?`, `prefix?` (filter tag names by prefix) |
| `search_by_tags` | Search browser by tags (AND logic) | `tags[]`, `category?`, `limit?`, `offset?` (for pagination) |
| `load_sound_by_path` | **Preferred load method.** Navigate directly to a browser_path and load onto a track | `track_index`, `browser_path` |

### Music Theory (generate notes — no side effects until passed to clip tools)
| Tool | Purpose | Key params |
|---|---|---|
| `generate_chord` | Generate a single chord as note dicts | `root_note?`, `chord_type`, `voicing`, `octave_shift?`, `scale_name?` |
| `generate_chord_progression` | Generate a diatonic chord progression | `degrees[]`, `root_note?`, `scale_name?`, `bars_per_chord?`, `voicing?` |
| `generate_bass_pattern` | Generate a genre-authentic bass pattern | `root_note?`, `scale_name?`, `style`, `bars?`, `octave?` |
| `generate_melody` | Generate a melodic phrase (step-biased, contour-shaped) | `root_note?`, `scale_name?`, `bars?`, `density?`, `contour?` |
| `humanize_notes` | Add micro-variations to timing, velocity, duration | `notes[]`, `timing_amount?`, `velocity_amount?`, `duration_amount?`, `seed?` |

### Events (observe live state changes)
| Tool | Purpose | Key params |
|---|---|---|
| `subscribe_to_events` | Start listening for Ableton state changes | `event_types[]` (tempo, is_playing, current_song_time, track_count) |
| `get_pending_events` | Drain queued events since last call | — |
| `unsubscribe_from_events` | Stop listening (pass null to unsubscribe all) | `event_types?[]` |

---

## MIDI Note Format

`add_notes_to_clip` expects a list of note objects. **Replaces all existing notes.**
Use `get_clip_notes` first if you need to preserve existing content.

```json
{
  "pitch": 60,          // MIDI note number (60 = C3 in Live's convention)
  "start_time": 0.0,    // Beat position within clip (0.0 = bar 1 beat 1)
  "duration": 0.5,      // Length in beats (0.25=16th, 0.5=8th, 1.0=quarter, 2.0=half)
  "velocity": 100,      // 1–127
  "mute": false
}
```

**MIDI pitch reference (Live: C3 = 60):**
- C3=60, D3=62, E3=64, F3=65, G3=67, A3=69, B3=71
- C4=72, C2=48, C1=36, C5=84
- Sharps: C#=61, D#=63, F#=66, G#=68, A#=70

**Standard GM Drum pitches** (Ableton default kits follow GM):
- 36=Kick, 38=Snare, 42=Closed HH, 46=Open HH
- 49=Crash, 51=Ride, 41=Low Floor Tom, 45=Low Tom, 48=High Tom

---

## Device Parameters Workflow

Every device on every track type (regular, return, master) is reachable. The API uses
**progressive disclosure**: each call tells you exactly what to pass in the next call.

### Track selection (applies to all three device tools)
| Scenario | Params to add |
|---|---|
| Regular track | `track_index=N` (default) |
| Return track A/B/C… | `return_track_index=0/1/2…` |
| Master track | `is_master=True` |

### Step 1 — find the device index
```
get_track_info(track_index, include_devices=True)   →   devices[]: [{index, name, class_name, type}, …]
```

### Step 2 — get top-level parameters (and discover nested devices)
```
get_device_params(track_index, device_index)
```
- Returns `parameters[]` — the device's own knobs (macros for racks).
- If the device is a **Rack**, also returns `contents` with a map of every nested device.
  Each entry includes a `chain_path` list — **copy it unchanged** into the next call.

### Step 3 — drill into a nested device
```
get_device_params(track_index, device_index, chain_path=[…])
```

### Step 4 — set a parameter
```
set_device_param(track_index, device_index, param_index, value, chain_path=[…])
```
`value` is clamped to the param's native min/max automatically.

### chain_path format
```json
{"chain_index": 0, "device_index": 0}                  // Instrument / Effect Rack
{"pad_note": 36, "chain_index": 0, "device_index": 0}  // Drum Rack pad
```
In practice: copy verbatim from the response. Never construct from scratch.

---

## Typical Workflows

### Compose a track with chord progression + bass in one workflow
```
1. get_scale_mode()                         → get current key context from Ableton
2. generate_chord_progression(degrees=[1,5,6,4], root_note="C4", scale_name="major")
   → {notes, clip_length, chord_names}
3. humanize_notes(notes, timing_amount=0.015)
4. create_track_with_clip(track_name="Chords", notes=..., clip_length=4.0)
5. generate_bass_pattern(style="deep_house", root_note="C2")
   → {notes, clip_length}
6. humanize_notes(notes, timing_amount=0.02)
7. create_track_with_clip(track_name="Bass", notes=...)
8. start_playback()
```

### Create a MIDI track with instrument and custom pattern
```
1. get_all_tracks_info()                    → orient, find free slot
2. create_midi_track                        → get new track index
3. set_track_name
4. search_and_load_sound(track_index, tags=["pad", "warm"], category="sounds")
5. generate_melody(root_note="D4", scale_name="dorian", bars=2, contour="arch")
6. humanize_notes(notes, timing_amount=0.02, velocity_amount=8)
7. create_clip(length=clip_length)
8. add_notes_to_clip
9. fire_clip
```

### Build a drum beat
```
1. create_midi_track → set_track_name "Drums"
2. get_browser_tree("drums") → get_browser_items_at_path → find rack_uri + kit_path
3. load_drum_kit
4. create_clip(length=4.0)
5. add_notes_to_clip  ← GM pitches: 36=kick, 38=snare, 42=hihat
6. fire_clip
```

### Find and load a sound by tag
```
1. search_by_tags(tags=["pad", "warm"], category="sounds")
   → returns [{name, type, source, browser_path}, ...]
2. load_sound_by_path(track_index, browser_path)
```
Or use `search_and_load_sound` to do both in one call.

### Monitor playback state in real time
```
1. subscribe_to_events(["tempo", "is_playing", "current_song_time"])
2. [user starts/stops playback or changes tempo in Ableton]
3. get_pending_events()  → [{type:"is_playing", data:{is_playing:true}}, …]
4. unsubscribe_from_events()
```

### Mix a track
```
set_track_mixer(track_index, volume=0.75, panning=-0.3)
set_track_mute(track_index, mute=True)
set_track_solo(track_index, solo=True)
```

### Edit an existing clip non-destructively
```
1. get_clip_notes(track_index, clip_index)    → read current notes
2. modify the notes array
3. add_notes_to_clip(...)                     → write back (full replacement)
```

---

## Notes & Caveats

- **Track indices are 0-based**, do not include return tracks or master — use `return_track_index` / `is_master` for those
- **Clip slot indices are 0-based** (Scene 1 = index 0)
- `add_notes_to_clip` **replaces all notes** — use `get_clip_notes` first to preserve existing content
- `get_track_info` defaults to `include_clips=False, include_devices=False` — pass `True` only when you need that data
- `search_by_tags` reads Ableton's local database directly — Live does not need to be running
- `search_by_tags` uses AND logic — each additional tag narrows results; start with one tag if unsure
- `search_by_tags` returns a `browser_path` — pass it directly to `load_sound_by_path`
- `get_browser_tags(prefix="...")` filters by tag name prefix — use when you know part of the tag
- `delete_track` shifts all subsequent track indices — re-read session info after any deletion
- **Saving sets** is not supported — use Cmd+S in Ableton directly
- `root_note` in `set_scale_mode` is 0–11: C=0, C#=1, D=2 … B=11
- Music theory tools (`generate_*`, `humanize_notes`) have no side effects — they only return note dicts. Always pass the result to `add_notes_to_clip` or `create_track_with_clip` to write it into Ableton.
- Music theory tools auto-resolve root and scale from Ableton's current scale when not specified — set the key in Ableton first for hands-free context
- `get_pending_events` clears the queue on each call — events are not repeated
- Event subscriptions are automatically cleared when the client disconnects

---

## Music Theory

The theory tools (`generate_chord`, `generate_chord_progression`, `generate_bass_pattern`,
`generate_melody`, `humanize_notes`) have expert musical intelligence embedded in them —
scales, diatonic chord qualities, genre bass patterns, and melody contours are all built in.

**Quick reference:**
- All `root_note` / `scale_name` params default to Ableton's current scale (set it in Live's Scale panel)
- Bass styles: `deep_house`, `techno`, `hip_hop`, `funk`, `reggae`, `drum_and_bass`, `afrobeats`, `pop`, `latin`, `jazz`
- Chord voicings: `close`, `open`, `drop2`, `spread`
- Melody contours: `arch` (default), `ascending`, `descending`, `static`, `random`

> For the full theory reference — scale tables, chord types, progression recipes, genre
> bass details, melody parameters, and humanize amounts — invoke the **ableton-mcp-theory** skill.
