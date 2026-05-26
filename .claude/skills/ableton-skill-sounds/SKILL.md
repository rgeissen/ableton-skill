---
name: ableton-skill-sounds
description: >
  Sound design and instrument loading tools for AbletonMCP. Use this skill for: browsing
  Ableton's library, searching sounds by tag, loading instruments or effects onto tracks,
  loading drum kits, reading and tweaking device parameters (synths, samplers, effects,
  racks). Trigger for any request about finding a sound, loading a preset, tweaking a synth
  parameter, adjusting a filter, setting up an effect chain, or drilling into a device rack.
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
| `get_browser_tags` | Discover available tags | `category?`, `prefix?` |
| `get_browser_tree` | Top-level browser categories | `category_type` |
| `get_browser_items_at_path` | Drill into a folder | `path`, `item_type` (all/folder/loadable) |

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
