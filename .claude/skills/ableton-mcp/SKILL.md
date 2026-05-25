---
name: ableton-mcp
description: >
  Control Ableton Live directly via the AbletonMCP server. Use this skill whenever the user
  wants to interact with Ableton Live — creating tracks, building beats, composing MIDI,
  loading instruments, controlling playback, mixing, editing devices, browsing the library,
  or any session workflow. Trigger for any request mentioning Ableton, Live, tracks, clips,
  MIDI, beats, drums, instruments, BPM, mix, mute, solo, device, synth, chord, bass, melody,
  scale, or session control — even phrased casually ("make a beat", "add a bass line",
  "solo that track", "turn up the filter"). Always load this skill before any other
  ableton-mcp-* skill.
compatibility: "Requires AbletonMCP Remote Script running in Ableton Live's MIDI preferences."
---

# AbletonMCP

Controls Ableton Live via a direct socket connection to the Remote Script. Changes are
instant and reflected in the session in real time.

---

## Always Orient First

```
get_all_tracks_info()      → compact view of every track (name, type, color, mute, solo, volume, clips, devices)
get_session_info()         → tempo, time signature, track count
get_scale_mode()           → current key and scale
get_playback_position()    → beat position + is_playing
```

`get_all_tracks_info` is the default entry point — it returns everything needed to orient
in a single call. Only call `get_track_info` when you need clip or device detail on a
specific track (`include_clips=True` or `include_devices=True`).

**Never assume track indices** — they shift when tracks are added or deleted.

---

## Production Stage Skills

Load the right skill for the task. Each skill is focused and only enters context when needed.

| Stage | Skill | When to invoke |
|---|---|---|
| **Compose** | `ableton-mcp-compose` | Writing tracks, clips, MIDI notes, generating chords/bass/melody, arrangement |
| **Sounds** | `ableton-mcp-sounds` | Browser search, loading instruments/effects, tweaking device parameters |
| **Mix** | `ableton-mcp-mix` | Track levels, panning, mute/solo, EQ/compression, coloring tracks |
| **Theory** | `ableton-mcp-theory` | Deep music theory — scales, chord types, progression recipes, genre patterns |

For most tasks, load **one stage skill** alongside this base skill. Multi-stage tasks
(e.g. compose + mix) load two. Never load all skills preemptively.

---

## Base Tools (always available)

### Session control
| Tool | Purpose | Key params |
|---|---|---|
| `get_session_info` | Tempo, time sig, track/return counts | `include_track_names` (bool) |
| `get_all_tracks_info` | All tracks: name, type, color, mute, solo, vol, grouped, clip/device count | — |
| `get_track_info` | Single track detail | `track_index`, `include_clips`, `include_devices` |
| `get_scale_mode` | Current root note + scale name | — |
| `get_playback_position` | Beat position + is_playing | — |
| `set_tempo` | Change BPM | `tempo` (float) |
| `start_playback` | Press Play | — |
| `stop_playback` | Press Stop | — |
| `undo` | Undo last action | — |

### Events (observe live state changes)
| Tool | Purpose | Key params |
|---|---|---|
| `subscribe_to_events` | Listen for tempo/play/time/track changes | `event_types[]` |
| `get_pending_events` | Drain event queue since last call | — |
| `unsubscribe_from_events` | Stop listening (null = unsubscribe all) | `event_types?[]` |

---

## Notes

- `get_track_info` defaults to `include_clips=False, include_devices=False` — only request what you need
- `add_notes_to_clip` **replaces all notes** — use `get_clip_notes` first to preserve existing content
- Track indices are 0-based and shift when tracks are added/deleted — always re-read after mutations
- Saving sets is not supported via the API — use Cmd+S in Ableton directly
- `search_by_tags` reads Ableton's SQLite database directly — Live does not need to be running
- Event subscriptions auto-clear when the client disconnects
