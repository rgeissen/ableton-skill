---
name: ableton-skill
description: >
  Control Ableton Live directly via the AbletonMCP server. Use this skill whenever the user
  wants to interact with Ableton Live — creating tracks, building beats, composing MIDI,
  loading instruments, controlling playback, mixing, editing devices, browsing the library,
  or any session workflow. Trigger for any request mentioning Ableton, Live, tracks, clips,
  MIDI, beats, drums, instruments, BPM, mix, mute, solo, device, synth, chord, bass, melody,
  scale, or session control — even phrased casually ("make a beat", "add a bass line",
  "solo that track", "turn up the filter"). Always load this skill before any other
  ableton-skill-* skill.
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
| **Compose** | `ableton-skill-compose` | Writing tracks, clips, MIDI notes, generating chords/bass/melody |
| **Sounds** | `ableton-skill-sounds` | Browser search, loading instruments/effects, sample-to-drum-pad kit building, device parameters |
| **Arrange** | `ableton-skill-arrange` | Scene management, song structure, Arrangement timeline, recording, launch quantization, audio export/bounce |
| **Mix** | `ableton-skill-mix` | Track levels, panning, mute/solo, return tracks, sends, EQ/compression |
| **Theory** | `ableton-skill-theory` | Deep music theory — scales, chord types, progression recipes, genre patterns |

For most tasks, load **one stage skill** alongside this base skill. Multi-stage tasks
(e.g. compose + mix) load two. Never load all skills preemptively.

**Vocals** span three stages: **record** the take (mic input chain → `ableton-skill-arrange`),
**tune/warp/chop** the audio clip (→ `ableton-skill-sounds`), and **process** it (EQ/comp/de-ess/
reverb → `ableton-skill-mix`). Load whichever stage the request is about.

---

## Production Workflow (the arc)

Track-building runs through five stages — each maps to a stage skill:

```
1. Basic Beat   → core groove: Chords · Melody · Bass · Drums   (compose)
2. Sound Design → replace / tweak / layer / process the sounds  (sounds)
3. Arrangement  → sections + energy curve, avoid the loop trap  (arrange)
4. Mixing       → EQ resonances → balance → spectrum → glue     (mix)
5. Mastering    → M/S EQ → glue compress → limiter              (mix)
```

**Guiding principles (apply throughout):**
- **Rule of 3 or 4** — lock a strong 8-bar loop from just Chords, Melody, Bass, Drums before adding more.
- **Use a reference track** — import one, map its sections and energy, match it.
- **Limited sound design** — Replace → Tweak → Layer → Process, rather than endless preset hunting.
- **Avoid the 8-bar loop trap** — a loop is not a song; change/evolve an element every 8 bars.
- **Default genre context** — deep/melodic house: 120–128 BPM (125 sweet spot), minor / min7 keys.

---

## Base Tools (always available)

### Session control
| Tool | Purpose | Key params |
|---|---|---|
| `get_session_info` | Tempo, time sig, track/return counts | `include_track_names` (bool) |
| `get_all_tracks_info` | All tracks: name, type, **color**, mute, solo, vol, **is_grouped**, **group_index**, clip/device count | — |
| `get_track_info` | Single track detail — also returns `color`, `is_grouped`, `group_index` | `track_index`, `include_clips`, `include_devices` |
| `get_scale_mode` | Current root note + scale name | — |
| `get_playback_position` | Beat position + is_playing | — |
| `set_tempo` | Change BPM | `tempo` (float) |
| `set_time_signature` | Change meter (4/4, 3/4, …) | `numerator`, `denominator` |
| `start_playback` | Press Play | — |
| `stop_playback` | Press Stop | — |
| `stop_all_clips` | Stop all clips without stopping transport | — |
| `undo` | Undo last action | — |
| `redo` | Redo last undone action | — |
| `tap_tempo` | Set BPM by tapping repeatedly | — |
| `set_metronome` | Toggle click track | `enabled` |
| `set_track_color` | Color-code a track (`#RRGGBB`) — use at any stage | `track_index`, `color` |

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
- **Track grouping** — Group creation is not available via the Live Python API (`create_group_track` does not exist). Use Cmd+G in Ableton to create groups manually. `is_grouped` and `group_index` in track info show the current group hierarchy read from Live.
- `set_track_color` accepts `#RRGGBB` hex strings — common conventions: drums `#FF2200`, bass `#8800FF`, chords `#00AAFF`, lead `#FFCC00`, FX `#008888`
