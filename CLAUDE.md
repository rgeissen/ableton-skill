# Ableton MCP — Codebase Guide

## Architecture

Two independent components communicate over a local TCP socket:

```
Claude / MCP Client
      │
      ▼
MCP_Server/server.py          ← FastMCP server (runs outside Ableton)
      │  TCP socket :9877
      ▼
AbletonMCP_Remote_Script/     ← Ableton MIDI Remote Script (runs inside Ableton's Python)
__init__.py
      │
      ▼
Live Python API (Live.*)      ← Ableton's internal API, only accessible from inside Live
```

The remote script is installed in Ableton's MIDI preferences as a Control Surface. It opens a
socket server on port **9877** and accepts JSON commands from the MCP server.

The MCP server can also run in HTTP mode (`--server --port 5006`) for remote clients
(e.g. Uderia on a LAN). DNS rebinding protection is disabled in that mode.

---

## Key Files

| File | Role |
|---|---|
| `MCP_Server/server.py` | All MCP tools. Music theory data tables + helpers. SQLite helpers for tag-based search. |
| `AbletonMCP_Remote_Script/__init__.py` | Command dispatcher + all Live API calls + event subscription system. |
| `pyproject.toml` | Single dependency: `mcp[cli]>=1.3.0`. No other packages needed. |
| `.claude/skills/ableton-skill/SKILL.md` | Main skill — session control, all tool reference, workflows. |
| `.claude/skills/ableton-skill-theory/SKILL.md` | Music theory sub-skill — loaded on demand only. |

---

## Communication Protocol

Commands are JSON sent over TCP. The MCP server calls `ableton.send_command(type, params)` which serialises to:

```json
{ "type": "get_session_info", "params": {} }
```

The remote script responds with:

```json
{ "status": "success", "result": { ... } }
```

State-mutating commands (create track, load device, etc.) are dispatched to Ableton's main thread via `schedule_message(0, fn)` with a `queue.Queue` for the response. Read-only commands run directly on the socket thread.

---

## Adding a New Tool

There are three patterns depending on whether the tool needs Ableton at all:

### Pattern 1 — Read-only Remote Script command
Add an `elif command_type == "..."` branch directly in `_process_command` (in the
read-only dispatch block, alongside `get_session_info`, `get_all_tracks_info`, etc.).
Implement a `_my_command(self, ...)` method. No `schedule_message` needed.

### Pattern 2 — State-mutating Remote Script command
1. Add the command type string to the `command_type in [...]` allow-list in `_process_command`.
2. Add an `elif command_type == "..."` branch inside `main_thread_task`.
3. Implement a `_my_command(self, ...)` method.

### Pattern 3 — Server-only tool (no Remote Script change)
Pure Python in `server.py` only. Used for: composite tools that chain multiple
`send_command` calls (e.g. `create_track_with_clip`), music theory generators
(e.g. `generate_chord_progression`), and DB-only tools (e.g. `search_by_tags`).

```python
@mcp.tool()
def my_tool(ctx: Context, ...) -> str:
    ableton = get_ableton_connection()   # omit if no Live connection needed
    ...
    return json.dumps({...}, indent=2)
```

No package installs needed — stdlib only beyond `mcp[cli]`.

---

## Music Theory Layer (server.py only)

Module-level data tables near the top of `server.py`:

- `NOTE_NAMES` — chromatic pitch class names
- `SCALE_INTERVALS` — 15 scales: semitone offsets from root
- `CHORD_INTERVALS` — 14 chord qualities: semitone offsets from chord root
- `DIATONIC_QUALITY` — degree → chord quality for major and minor
- `BASS_RHYTHM_PATTERNS` — 10 genre keys, each a list of `(beat_offset, semitone_offset, duration, velocity)` tuples

Private helpers (defined before the first `@mcp.tool()`):

- `_note_name_to_midi(note_name)` — `"C4"` → 60
- `_midi_to_note_name(midi)` — 60 → `"C4"`
- `_get_scale_intervals(scale_name)` — looks up `SCALE_INTERVALS`, raises on unknown
- `_build_scale_pitches(root_midi, intervals, octave_range)` — returns sorted list of MIDI pitches
- `_resolve_scale_context(ableton, root_note, scale_name)` — reads Ableton's current scale when args are `None`; returns `(root_midi, intervals, root_str, scale_name_str)`
- `_apply_voicing(pitches, voicing)` — transforms a close-position chord list

Music theory tools are **server-only** (Pattern 3) and have no side effects — they return note dicts that callers pass to `add_notes_to_clip` or `create_track_with_clip`.

---

## Event Subscription System

### Remote Script (`__init__.py`)

Three instance variables on `AbletonMCP`:
```python
self._event_queue = []          # list of {"type", "timestamp", "data"} dicts
self._event_lock = threading.Lock()
self._active_listeners = {}     # event_type str → listener callable
```

Key methods:
- `_make_listener(event_type)` — returns a closure that appends to `_event_queue` under lock
- `_snapshot_for(event_type)` — reads the current Live value for that event type
- `_subscribe_to_events(event_types)` — calls `song.add_<type>_listener(fn)` for each type
- `_get_pending_events()` — drains and returns `_event_queue` under lock
- `_unsubscribe_from_events(event_types)` — removes listeners; `None` = unsubscribe all
- `_unsubscribe_all()` — called automatically in `_handle_client` finally block on disconnect

Supported event types: `tempo`, `is_playing`, `current_song_time`, `track_count`.
All three commands (`subscribe_to_events`, `get_pending_events`, `unsubscribe_from_events`)
are read-only dispatched (no `schedule_message`).

### MCP Server (`server.py`)

Three thin wrapper tools: `subscribe_to_events`, `get_pending_events`, `unsubscribe_from_events`.

---

## Tag-Based Browser Search

`get_browser_tags` and `search_by_tags` bypass the socket entirely and read Ableton's local SQLite database directly:

```
~/Library/Application Support/Ableton/Live Database/Live-files-<version>.db
```

**Key schema facts:**
- `files` table — every browser item. `file_type` is a FourCC integer (`wav-`, `adg-`, `adv-`, `keyw`, etc.).
- `file_type = 1801812343` (`keyw`) — tag nodes. One row per tag name.
- `keywords` table — many-to-many join between files and their tags (`file_id → keyw_id`).
- `ancestors` table — ordered parent chain for each file, used to reconstruct filesystem paths.
- `places` table — maps a file's `place_id` to its pack/library name (e.g. "User Library", "Build and Drop").

**Why not the Live API?** `Live.Browser.BrowserItem` does not expose a `tags` property. Tags only exist in the SQLite DB.

**URI caveat:** `BrowserItem.uri` is generated at runtime by Ableton and is not stored in the DB. Tag search returns a `browser_path` (reconstructed from ancestors) which is passed to `load_sound_by_path` to load the item.

---

## Ableton Live API Constraints

- The `Live` module is only importable inside Ableton's Python runtime — never from the MCP server.
- `BrowserItem` properties: `name`, `uri`, `is_folder`, `is_device`, `is_loadable`, `is_selected`, `children`, `source`. No tags, no metadata.
- `Browser` root properties: `instruments`, `sounds`, `drums`, `audio_effects`, `midi_effects`, `samples`, `clips`, `packs`, `user_library`, `current_project`, `max_for_live`, `plugins`.
- State mutations must run on Ableton's main thread — use `schedule_message(0, fn)`.
- `song.add_<type>_listener` / `song.remove_<type>_listener` work on any thread.

---

## HTTP Server Mode

Run `ableton-skill --server --port 5006` to expose the MCP server over streamable-HTTP
(for remote clients such as Uderia on the same LAN). The host is bound to `0.0.0.0`
and FastMCP's DNS rebinding protection is disabled.

Environment variables `ABLETON_HOST` and `ABLETON_PORT` override the TCP target
(default: `localhost:9877`) — useful when the Remote Script runs on a different machine.

---

## Skills

Six Claude Code skills live in `.claude/skills/`, one per production stage:

| Skill | File | Loaded when |
|---|---|---|
| `ableton-skill` | `ableton-skill/SKILL.md` | Every session — base skill always loaded first |
| `ableton-skill-compose` | `ableton-skill-compose/SKILL.md` | Writing notes, generating music, clip editing |
| `ableton-skill-sounds` | `ableton-skill-sounds/SKILL.md` | Browser search, loading instruments/effects, device params |
| `ableton-skill-arrange` | `ableton-skill-arrange/SKILL.md` | Scenes, song structure, Arrangement timeline, recording |
| `ableton-skill-mix` | `ableton-skill-mix/SKILL.md` | Levels, panning, mute/solo, return tracks, sends, EQ |
| `ableton-skill-theory` | `ableton-skill-theory/SKILL.md` | On demand — deep music theory reference |

Progressive disclosure: the base skill is always loaded (lightweight index). Stage skills
enter context only when the task requires them. Theory is loaded only for deep theory questions.
This keeps the default context footprint small.

## Live API Verified Methods (from Song.pyc strings)

Methods confirmed to exist in Live 12:
- `create_audio_track`, `create_midi_track`, `create_return_track`, `create_scene`
- `delete_scene`, `duplicate_track`, `stop_all_clips`
- `tap_tempo`, `capture_midi`, `redo`, `undo`
- `group_tracks` (read-only list), `ungroup_track`
- `cue_points`, `arrangement_record_arm`, `metronome`, `signature_numerator`, `signature_denominator`
- `current_song_time` (readable and writable)
- `song.add_<type>_listener` / `song.remove_<type>_listener`

**Does NOT exist:** `create_group_track` — group tracks must be created manually with Cmd+G.
