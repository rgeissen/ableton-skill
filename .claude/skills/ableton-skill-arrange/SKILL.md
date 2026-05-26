---
name: ableton-skill-arrange
description: >
  Arrangement view tools for AbletonMCP. Use this skill for: switching to the Arrangement
  timeline, placing clips at specific bar/beat positions, navigating with cue points,
  working with scenes (create, fire, name, color), arming for recording, building full
  song structures from Session clips. Trigger for any request about building a full song,
  intro/verse/chorus/outro structure, arrangement, timeline, scenes, recording, or
  "recording to arrangement".
compatibility: "Requires ableton-skill skill loaded. Part of the AbletonMCP skill suite."
---

# Arrange — Song Structure & Timeline

This skill covers Session scene management and Arrangement view timeline workflow.
Load it alongside the base `ableton-skill` skill.

---

## Scene Management (Session View)

Scenes are the rows in Session View — each row contains one clip slot per track.
Firing a scene launches all clips in that row simultaneously.

| Tool | Purpose | Key params |
|---|---|---|
| `get_scenes` | List all scenes (name, color, tempo) | — |
| `create_scene` | Add a new empty scene | `index` (-1 = append) |
| `delete_scene` | Remove a scene | `index` |
| `fire_scene` | Launch all clips in a scene | `index` |
| `set_scene_name` | Rename a scene | `index`, `name` |
| `set_scene_color` | Color-code a scene | `index`, `color` (#RRGGBB) |
| `stop_all_clips` | Stop all playing clips | — |

**Scene naming convention for song sections:**
- Intro, Verse A, Chorus, Break, Drop, Buildup, Outro
- Color-code by energy: low `#004488` → high `#FF2200`

---

## Arrangement Timeline

| Tool | Purpose | Key params |
|---|---|---|
| `switch_to_arrangement_view` | Switch main window to Arranger | — |
| `get_current_song_time` | Read playhead position in beats | — |
| `set_current_song_time` | Jump playhead to a beat position | `time` (beats) |
| `get_arrangement_clips` | List clips on a track's timeline | `track_index` |
| `get_cue_points` | List all cue point markers | — |
| `set_arrangement_record` | Arm arrangement recording | `record` (bool) |

**Beat position reference (4/4, 1 bar = 4 beats):**
```
Bar 1  = beat 0.0
Bar 5  = beat 16.0
Bar 9  = beat 32.0
Bar 17 = beat 64.0
```

---

## Transport & Recording

| Tool | Purpose | Key params |
|---|---|---|
| `set_track_arm` | Arm a track for recording | `track_index`, `arm` |
| `capture_midi` | Recover recently played MIDI | — |
| `set_arrangement_record` | Arm arrangement record | `record` |
| `redo` | Redo last undone action | — |
| `set_time_signature` | Change meter (e.g. 3/4, 6/8) | `numerator`, `denominator` |
| `set_metronome` | Toggle click track | `enabled` |
| `tap_tempo` | Set BPM by tapping | — |
| `duplicate_track` | Clone track with devices + clips | `track_index` |

---

## Typical Arrangement Workflow

```
# 1. Build clips in Session View first (use ableton-skill-compose)
get_all_tracks_info()   → confirm track indices

# 2. Set up scenes for sections
create_scene(index=-1)  → append "Intro"
set_scene_name(index=0, name="Intro")
create_scene(index=-1)  → append "Verse"
set_scene_name(index=1, name="Verse")
create_scene(index=-1)  → append "Chorus")
set_scene_name(index=2, name="Chorus")

# 3. Create and color clips per section (ableton-skill-compose)

# 4. Switch to Arrangement, set playhead, record sections
switch_to_arrangement_view()
set_current_song_time(time=0.0)         → bar 1
set_arrangement_record(record=True)
fire_scene(index=0)                     → records Intro into arrangement
# ... let it play, then ...
set_current_song_time(time=16.0)        → bar 5
fire_scene(index=1)                     → records Verse

# 5. Check what's on the timeline
get_arrangement_clips(track_index=0)    → list clips on track 0
get_cue_points()                        → list markers
```

---

## Notes

- `get_arrangement_clips` requires Live 11 / 12 — `track.arrangement_clips` must exist
- `capture_midi` recovers notes from the recent past on the **armed** track — arm first
- `set_current_song_time` positions the **playhead**, not the loop region
- Scenes do not have a built-in length — clip lengths determine how long the scene plays
- `stop_all_clips` is the fastest way to silence everything without stopping transport
