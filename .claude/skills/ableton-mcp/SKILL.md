---
name: ableton-mcp
description: >
  Control Ableton Live directly via the AbletonMCP server. Use this skill whenever the user
  wants to interact with Ableton Live — including creating tracks, building beats or melodies,
  composing MIDI patterns, loading instruments or drum kits, controlling playback, adjusting
  tempo, mixing (volume/pan/mute/solo), editing device parameters, browsing the Live library,
  duplicating or deleting clips and tracks, reading back MIDI notes, or automating any session
  workflow. Trigger this skill for any request mentioning Ableton, Live, tracks, clips, MIDI,
  beats, drums, instruments, BPM, mix, mute, solo, device, synth, or session control — even
  if phrased casually ("make a beat", "add a bass line", "solo that track", "turn up the
  filter", "save the set"). Always use this skill before attempting to operate Ableton via
  the browser/keyboard.
compatibility: "Requires AbletonMCP MCP server running as a Remote Script in Ableton Live's MIDI preferences."
---

# Ableton MCP Skill

Control Ableton Live via the AbletonMCP MCP server. The server communicates directly with
Live's Python API — changes are instant and reflected in the session in real time.

---

## First Step: Always Orient Yourself

Before making any changes, call `get_session_info` to understand the current state:
- How many tracks exist and what type they are
- Current tempo and time signature
- Return track count

Then call `get_track_info` for relevant tracks to inspect clips, devices, volume, mute/solo state.

**Never assume track indices** — they shift when tracks are added/deleted. Always verify.

---

## Complete Tool Reference

### Session
| Tool | Purpose | Key params |
|---|---|---|
| `get_session_info` | Full session overview (tracks, tempo, return tracks, master) | — |
| `set_tempo` | Change BPM | `tempo` (float) |
| `start_playback` | Press Play | — |
| `stop_playback` | Press Stop | — |
| `get_playback_position` | Current beat position + is_playing state | — |
| `get_scale_mode` | Get current root note, root note name, and scale name | — |
| `set_scale_mode` | Set root note, scale name, and/or in-key highlighting | `root_note` (0–11), `scale_name`, `in_key` (bool) |
| `undo` | Undo the last action | — |

### Tracks
| Tool | Purpose | Key params |
|---|---|---|
| `create_midi_track` | Add a new MIDI track | `index` (-1 = end) |
| `create_audio_track` | Add a new audio track | `index` (-1 = end) |
| `get_track_info` | Inspect a track (clips, devices, name, mute/solo, volume) | `track_index` |
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
| `get_browser_tree` | List browser categories/folders | `category_type` (all / instruments / sounds / drums / audio_effects / midi_effects) |
| `get_browser_items_at_path` | Drill into a folder to get loadable URIs | `path` ("category/folder/subfolder") |
| `get_browser_tags` | List all tags available in the browser database | `category` (all / sounds / instruments / drums / audio_effects / midi_effects / max_for_live / plugins / clips / samples / grooves / tunings) |
| `search_by_tags` | Search browser by tags (AND logic — item must have ALL tags) | `tags[]`, `category?`, `limit?` (default 50) |

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
get_track_info(track_index)   →   devices[]: [{index, name, class_name, type}, …]
```

### Step 2 — get top-level parameters (and discover nested devices)
```
get_device_params(track_index, device_index)
```
- Returns `parameters[]` — the device's own knobs (macros for racks).
- If the device is a **Rack**, also returns `contents` with a map of every nested device.
  Each entry includes a `chain_path` list — **copy it unchanged** into the next call.
- `"has_nested_devices": true` on an entry means it is itself a rack; call `get_device_params`
  with its `chain_path` to see another level of `contents`.

### Step 3 — drill into a nested device
```
get_device_params(track_index, device_index, chain_path=[…])
```
Pass the exact `chain_path` from the `contents` entry. Works at any depth.

### Step 4 — set a parameter
```
set_device_param(track_index, device_index, param_index, value, chain_path=[…])
```
Same `chain_path` as the read call. `value` is clamped to the param's native min/max automatically.

### chain_path format
A list of step dicts. Each step navigates one rack layer:
```json
{"chain_index": 0, "device_index": 0}              // Instrument / Effect Rack
{"pad_note": 36, "chain_index": 0, "device_index": 0}  // Drum Rack pad (note 36 = C1)
```
Multiple steps = multiple layers deep. In practice just copy the value from the response.

### Drum Rack: find which pad is which note
```
get_drum_rack_pads(track_index, device_index)
→ [{note: 36, name: "Kick", mute, solo, chains: ["Kick"]}, …]
```
Only loaded pads are returned. Useful when you need to know the note number before
constructing a `chain_path` step manually.

---

## Typical Workflows

### Create a MIDI track with instrument and pattern
```
1. get_session_info                     → note current track count
2. create_midi_track                    → get new track index
3. set_track_name
4. get_browser_tree("instruments")      → find category
5. get_browser_items_at_path            → get URI
6. load_instrument_or_effect
7. create_clip(length=8.0)              → 2-bar clip in slot 0
8. add_notes_to_clip                    → write notes
9. set_clip_name
10. fire_clip
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

### Find and load an instrument by tag
```
1. get_browser_tags(category="instruments")   → see all available tags
2. search_by_tags(tags=["Bass", "Synth"], category="instruments")
   → returns [{name, type, source, tags, browser_path}, ...]
3. get_browser_items_at_path(browser_path)    → get the loadable URI
4. load_instrument_or_effect(track_index, uri)
```

Tag search uses AND logic — results must carry every tag supplied. Start broad (one tag)
and narrow down. Use get_browser_tags first to avoid guessing tag names.
```
set_track_mixer(track_index, volume=0.75, panning=-0.3)  → volume + pan together
set_track_mute(track_index, mute=True)
set_track_solo(track_index, solo=True)
```

### Edit an existing clip non-destructively
```
1. get_clip_notes(track_index, clip_index)    → read current notes
2. modify the notes array in memory
3. add_notes_to_clip(...)                     → write back (full replacement)
```

### Duplicate and vary a pattern
```
duplicate_clip(track_index=0, clip_index=0, target_clip_index=1)
→ copies to slot 1 of same track

get_clip_notes(0, 1)
add_notes_to_clip(0, 1, modified_notes)      → write variation into the copy
```

### Tweak a synth parameter (top-level device)
```
get_device_params(track_index=2, device_index=0)
→ {parameters: [{index:5, name:"Filter Freq", value:1000.0, min:20.0, max:20000.0}, …]}

set_device_param(track_index=2, device_index=0, param_index=5, value=2500.0)
```

### Tweak a parameter inside a Drum Rack pad (e.g. Simpler on the kick)
```
get_device_params(track_index=0, device_index=0)
→ {contents: {type:"drum_rack", drum_pads: [
     {note:36, name:"Kick", chains:[{chain_index:0, devices:[
       {name:"Simpler", chain_path:[{"pad_note":36,"chain_index":0,"device_index":0}]}
     ]}]}, …
   ]}}

get_device_params(track_index=0, device_index=0,
                  chain_path=[{"pad_note":36,"chain_index":0,"device_index":0}])
→ {parameters: [{index:3, name:"Start", value:0.0, min:0.0, max:1.0}, …]}

set_device_param(track_index=0, device_index=0, param_index=3, value=0.1,
                 chain_path=[{"pad_note":36,"chain_index":0,"device_index":0}])
```

### Tweak a parameter on a return track
```
get_device_params(return_track_index=0, device_index=0)   // Return A
set_device_param(return_track_index=0, device_index=0, param_index=2, value=0.5)
```

### Tweak a parameter on the master track
```
get_device_params(is_master=True, device_index=0)
set_device_param(is_master=True, device_index=0, param_index=0, value=0.8)
```

---

## Notes & Caveats

- **Track indices are 0-based**, do not include return tracks or master — use `return_track_index` / `is_master` for those
- **Clip slot indices are 0-based** (Scene 1 = index 0)
- `add_notes_to_clip` **replaces all notes** — use `get_clip_notes` first to preserve existing content
- `duplicate_clip` without `target_track_index` copies within the same track
- `set_device_param` values use the device's native range — always read `get_device_params` first
- `load_drum_kit` requires both `rack_uri` (Drum Rack device URI) AND `kit_path` (preset path)
- `delete_track` shifts all subsequent track indices — re-read session info after any deletion
- **Saving sets** is not supported — the Live Python API exposes no save method on the Song object. Use Cmd+S in Ableton directly.
- `search_by_tags` reads Ableton's local database directly — Live does not need to be running
- `search_by_tags` uses AND logic — each additional tag narrows results; start with one tag if unsure
- `search_by_tags` returns a `browser_path` — pass it to `get_browser_items_at_path` to get the loadable URI
- The MCP server must be running as a Remote Script in Live's MIDI preferences
- `set_scale_mode` params are all optional — pass only what you want to change
- `root_note` is 0–11: C=0, C#=1, D=2, D#=3, E=4, F=5, F#=6, G=7, G#=8, A=9, A#=10, B=11
- Valid `scale_name` values: Major, Minor, Dorian, Phrygian, Lydian, Mixolydian, Locrian, Whole Tone, Minor Pentatonic, Major Pentatonic, Harmonic Minor, Melodic Minor
- `get_device_params` on a rack returns **macros** in `parameters[]` and **nested devices** in `contents` — they are separate
- `chain_path` is a list of step dicts — copy it verbatim from the `contents` response; never construct it from scratch unless you already know the structure
- `get_drum_rack_pads` only returns pads that have something loaded (chains non-empty)
- `drum_pads` in Live are indexed 0–127 by MIDI note number; `pad_note` in a `chain_path` step is that note number
