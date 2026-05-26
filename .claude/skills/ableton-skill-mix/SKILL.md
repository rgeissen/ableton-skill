---
name: ableton-skill-mix
description: >
  Mixing tools for AbletonMCP. Use this skill for: setting track volume and pan, muting or
  soloing tracks, coloring tracks for session navigation, adjusting EQ or dynamics devices,
  working with return tracks and master track effects, balancing levels across tracks.
  Trigger for any request about mixing, levels, panning, EQ, compression, volume balancing,
  mute, solo, or sound enhancement at the mix stage.
compatibility: "Requires ableton-skill skill loaded. Part of the AbletonMCP skill suite."
---

# Mix — Levels, Color & Effects

This skill covers the **Mixing** stage. Use `get_all_tracks_info()` from the base skill
first — it returns volume, mute, solo, and color for every track in one call.

---

## Track Mixer

| Tool | Purpose | Key params |
|---|---|---|
| `set_track_mixer` | Volume + pan in one call | `track_index`, `volume` (0.0–1.0), `panning` (-1.0 to 1.0) |
| `set_track_mute` | Mute / unmute | `track_index`, `mute` (bool) |
| `set_track_solo` | Solo / unsolo | `track_index`, `solo` (bool) |
| `set_track_color` | Color-code for session navigation | `track_index`, `color` (#RRGGBB) |

### Return Tracks & Sends

| Tool | Purpose | Key params |
|---|---|---|
| `get_return_tracks` | List return tracks (volume, pan, mute) | — |
| `create_return_track` | Add a new return track | — |
| `set_send_level` | Set send amount from track to return | `track_index`, `return_track_index`, `value` (0.0–1.0) |

**Send level reference:** 0.0 = off, 0.5 = −6 dB, 1.0 = unity (maximum send).

**Typical reverb/delay setup:**
```
create_return_track()                          → return A
# Load reverb via ableton-skill-sounds
set_send_level(track_index=2, return_track_index=0, value=0.3)  → 30% of track 2 → reverb A
```

**Volume reference:**
- 0.0 = silence, 0.85 = unity gain (0 dB), 1.0 = +6 dB
- Typical mix starting point: kicks 0.85–0.9, bass 0.75–0.85, pads 0.5–0.65, leads 0.6–0.75

**Color conventions for session navigation:**

| Role | Suggested color |
|---|---|
| Kick / Drums | `#FF2200` red |
| Bass | `#8800FF` purple |
| Chords / Pads | `#00AAFF` blue |
| Melody / Lead | `#FFCC00` yellow |
| Percussion | `#FF8800` orange |
| FX / Atmosphere | `#008888` teal |
| Vocals | `#FF44AA` pink |
| Bus / Reference | `#888888` grey |

---

## Effects & Device Parameters

Device parameters work identically in Mixing — same progressive disclosure pattern as Sound Design.
The difference is context: at mix stage you're adjusting EQ, compression, saturation, reverb, delay.

### Track selection
| Target | Params |
|---|---|
| Regular track | `track_index=N` |
| Return track A/B… | `return_track_index=0/1…` |
| Master track | `is_master=True` |

### Read → Set
```
get_device_params(track_index, device_index)
→ parameters[]: [{index, name, value, min, max}]

set_device_param(track_index, device_index, param_index, value)
```
Always read first — values use the device's native range.

### Common mixing tasks

**EQ Eight — cut low end on a pad:**
```
get_device_params(track_index=3, device_index=1)
→ find "Frequency 1" and "Active 1" params
set_device_param(track_index=3, device_index=1, param_index=..., value=...)
```

**Compressor on bass — adjust threshold and ratio:**
```
get_device_params(track_index=1, device_index=1)
→ [{name:"Threshold", ...}, {name:"Ratio", ...}]
set_device_param(...)
```

**Reverb send on return track A:**
```
get_device_params(return_track_index=0, device_index=0)
set_device_param(return_track_index=0, device_index=0, param_index=N, value=0.6)
```

**Master track limiter:**
```
get_device_params(is_master=True, device_index=0)
set_device_param(is_master=True, device_index=0, param_index=N, value=0.0)
```

---

## Typical Mix Workflow

```
# 1. Survey the session
get_all_tracks_info()
→ [{index, name, volume, mute, solo, color, ...}]

# 2. Rough balance — set levels
set_track_mixer(track_index=0, volume=0.85)   # kick
set_track_mixer(track_index=1, volume=0.78)   # bass
set_track_mixer(track_index=2, volume=0.60)   # chords
set_track_mixer(track_index=3, volume=0.65)   # lead

# 3. Color-code for navigation
set_track_color(0, "#FF2200")  # drums
set_track_color(1, "#8800FF")  # bass
set_track_color(2, "#00AAFF")  # chords
set_track_color(3, "#FFCC00")  # lead

# 4. Inspect and tweak devices
get_track_info(track_index=1, include_devices=True)  → device list
get_device_params(track_index=1, device_index=1)     → compressor params
set_device_param(track_index=1, device_index=1, param_index=2, value=-18.0)

# 5. Solo to check in isolation
set_track_solo(track_index=1, solo=True)
# ... listen ...
set_track_solo(track_index=1, solo=False)
```
