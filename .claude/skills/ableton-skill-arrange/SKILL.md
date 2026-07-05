---
name: ableton-skill-arrange
description: >
  Arrangement view tools for AbletonMCP. Use this skill for: switching to the Arrangement
  timeline, placing clips at specific bar/beat positions, navigating with cue points,
  working with scenes (create, fire, name, color), arming for recording, building full
  song structures from Session clips, setting launch quantization, and exporting/bouncing
  audio to WAV via real-time resampling capture. Trigger for any request about building a
  full song, intro/verse/chorus/outro structure, arrangement, timeline, scenes, recording,
  "recording to arrangement", recording a vocal or mic take (input routing / channel / monitor),
  exporting/bouncing/rendering audio, or resampling.
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

## Song-Structure Blueprint (electronic / melodic-house)

The canonical section order and its **energy progression** (each section engineered to set up the next):

```
INTRO → BUILD-UP → VERSE → BRIDGE → CHORUS → BREAKDOWN → PRE-DROP → DROP → BUILD-DOWN → OUTRO
 low  →  rising  → mid  → dip   → high  →  low/melodic → rising → peak →  falling  → fade
```

| Section | Role | Typical length | Elements |
|---|---|---|---|
| **Intro** | DJ mix-in; establish pulse | 16–32 bars (ext. mix) | Stripped kick, minimal harmony, no full melody |
| **Build-up** | Ramp energy toward a peak | 8–16 bars | Layer percussion, hint the main theme, add risers/atmosphere |
| **Verse** | Contrast / narrative | 16 bars | Lower energy than chorus, fewer layers |
| **Bridge** | Reset the ear before impact | **≤ 8 bars** | Simplified or **no beat**, sweeps/risers/FX |
| **Chorus / Drop** | Energetic peak, full mix | 16–32 bars | Full instrumentation — all layers in |
| **Breakdown** | Melodic breather (mid-track) | 16–32 bars | Strip the beat, spotlight melody/pads, then progressive build |
| **Build-down** | Controlled release after peak | 8–16 bars | Dissipate energy, thin percussion, reverb/echo |
| **Outro** | Graceful, DJ-friendly exit | 16–32 bars | Fade rhythm/harmony out; **mirror the intro** for mix-out |

**Energy is a curve, not a step.** Automate `Track Volume` / filter cutoff to *ramp within* each
section, then dip hard at section boundaries so the next section hits harder (the "Common Energy"
shape: small climbs → a big breakdown dip → the highest peak at the final drop).

**The 8-bar rule (avoid the "loop trap").** Change *something* every 8 bars — add/remove a layer,
open a filter, drop the kick, introduce a fill. Real melodic-house arrangements evolve each lane
continuously, e.g. (from reference-track deconstruction):
- **Drums:** `Kick` → `Kick + Shakers` → `+ Hats + Clap` → `+ More` … then strip back for breaks
- **Arp/Music:** `Main Arp` → `Main Arp + High` → `Main Arp + Lead` → `NEW ARP` → `Main Arp Fading`
- **Pad + Drone:** present through drops, **absent** through breaks (returns for the next lift)
- **Bass:** in on the drop, out (or high-passed) through the breakdown

**Section-per-scene mapping:** build one Session scene per section (name + color-code by energy),
then record them to the Arrangement in order (see workflow below). Place a **cue point** at each
boundary for fast navigation.

---

## Transitions & Movement

The glue between sections — the details that make an arrangement feel professional:

| Technique | How | When |
|---|---|---|
| **HP-filter the kick** | Automate a high-pass up over 1–2 bars, drop it on the downbeat | Last bars before a drop/section change |
| **No-Kick (NK) bar** | Mute/remove the kick for 1–2 bars | Right before the beat re-enters — creates lift |
| **Risers / sweeps** | White-noise riser, reverse cymbal/sample on a return | Into any high-energy section |
| **Filter open for movement** | Open a low-pass right **before** and **between** changes | Continuously, for life |
| **Impact + tail** | Crash/impact on the downbeat + reverb tail from the previous section | On the boundary itself |
| **FX marker every boundary** | An FX hit/sweep sits on *every* section change | All transitions |
| **Held string / vox sample** | Sustains across the gap so the mix never fully drops out | Break → drop |

**Send-effect reverb tiers** (route tracks to returns by depth — see `ableton-skill-mix`):
- **Short reverb** → drums (room glue)   • **Medium** → plucks, ambience, FX
- **Long reverb** → piano, swell pads, drone   • **Delay** → plucks / melodic stabs

**Reference-track workflow:** import a reference track onto an audio track, mark its section
boundaries with cue points, read its energy shape, and match your section lengths + element
density to it. This is the fastest route to a pro arrangement.

---

## DJ-Ready Structure & Energy (from *Secrets of Dance Music Production*)

- **Loop first, song second** — perfect a killer 4- or 8-bar loop (drums, bass, key parts), *then* expand it into sections. Drop any layer that doesn't add to sound, groove, or tone.
- **Eight is the magic number** — put changes/turnarounds at **8, 16, or 32 bars**. Deviating (e.g. a 2½-bar turnaround) breaks dancefloor momentum; occasional 12-bar switches add flexibility.
- **DJ intro & outro** — give **8/16/32 bars** of stripped beats (kick + hat + one percussive element) at the start and end for cueing/mixing, plus an identifiable sound announcing the track proper.
- **3 momentum rules building into a drop:** ① filters **open** · ② pitches **rise** · ③ ambient **space increases** (reverb/delay sends up). **Reverse all three at the drop** (filters close, pitch resets, FX cut) for maximum impact.
- **Breakdown** — withdraw the rhythm/bass, build from quiet (or silence) to epic. To keep the backbone while easing energy, **low-cut the kick** (removes weight, keeps the click).
- **Fix the mix in the arrangement** — a crowded mix is usually an arrangement problem: mute non-essentials (each part eats headroom + frequency), or transpose/re-voice a clashing part rather than only EQ'ing.

### Transition FX toolkit (extends *Transitions & Movement* above)

- **Ambient bus build** — raise a part's reverb/delay **send** as the track nears a turnaround (builds tension, pushes the part back), then snap the send back at the new section for impact.
- **"The bomb" (impact)** — a long-decay 808 kick + a long reverb (decay ~10 s, pre-delay ~6 ms, low-cut ~410 Hz) + a high-shelf boost (~+8 dB from 670 Hz) placed at the *start* of a breakdown.
- **Full-mix FX** — automate a **high-pass filter on the master** (classic DJ move: pull the low end out, bring it back), optionally a delay after it. Use curves, not straight lines.
- **Don't underestimate silence** — an extra **bar of silence** (or a hard filter dip) before the drop creates more drama than adding another FX layer.
- **Fills** — at the end of 8/16-bar cycles: drum rolls, `Beat Repeat`, reversed backing, filtered noise sweeps.

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
| `set_launch_quantization` | Global clip/scene launch quantization | `quantization` |

**Launch quantization** controls *when* a fired clip or scene actually starts. `set_launch_quantization("1 bar")`
snaps every launch to the next downbeat (tight, musical); `"none"` fires immediately so multiple
clips launch perfectly together. Values: `none · 8 bars · 4 bars · 2 bars · 1 bar · 1/2 · 1/4 · 1/8 · 1/16 · 1/32`
(plus triplets `1/2t`…`1/8t`). Use `"none"` when firing several tracks in one go for a clean simultaneous start.

---

## Recording a Vocal / Live Take (mic input)

Record a real mic (or any external input) into a Session slot. Discover the routing first, then wire the chain:

| Tool | Purpose | Key params |
|---|---|---|
| `get_track_io` | Read arm/monitor + **available input routing types & channels** | `track_index` |
| `set_track_input_routing` | Pick the input **type** (`"Ext. In"` for a mic) | `track_index`, `routing_name` |
| `set_track_input_channel` | Pick the input **channel** (mono `"1"`/`"2"`, or list them) | `track_index`, `channel?` |
| `set_track_monitor` | Monitoring: **0 = In** (hear yourself), 1 = Auto, 2 = Off | `track_index`, `state` |
| `set_track_arm` | Arm the track | `track_index`, `arm` |
| `fire_clip_slot` | Fire an **empty** slot on an armed track → starts recording | `track_index`, `clip_index` |

**Vocal record chain:**
```
create_audio_track()
get_track_io(track)                         → find "Ext. In" + the mic's channel
set_track_input_routing(track, "Ext. In")
set_track_input_channel(track, "1")         → mono mic on input 1
set_track_monitor(track, 0)                 → In, so the singer hears themselves
set_track_arm(track, True)
set_metronome(enabled=True)                 → click for timing (optional)
fire_clip_slot(track, slot)                 → recording starts
# ... performance ...
stop_playback()                             → (or fire the slot again to stop + play)
get_clip_file_path(track, slot)             → the recorded WAV
```
Record at a healthy level but leave **12–15 dB headroom** on peaks. After the take, **tune/warp** it with `set_audio_clip_properties` (see `ableton-skill-sounds`) and **process** it (EQ → comp → de-ess → reverb) via `ableton-skill-mix`. Comp multiple takes across scenes; keep the same mic position between takes.

---

## Export & Resampling Capture

Ableton's API has **no offline render-to-disk**, so bouncing audio is a *real-time* capture:
the transport plays and a hidden track records the master bus via **Resampling**. These tools
each take as long as the material plays.

| Tool | Purpose | Key params |
|---|---|---|
| `export_audio` | Bounce the playing Session to a WAV (one scene) | `bars` (default 16), `scene_index` |
| `export_tutorial` | Capture multiple scenes back-to-back into **one** continuous WAV | `scene_bars[]`, `content_tracks[]`, `scene_start?` |
| `get_clip_file_path` | Read the WAV path of a recorded audio clip | `track_index`, `clip_index?` |
| `fire_clip_slot` | Fire a slot directly — works on **empty** slots (starts recording on an armed track) | `track_index`, `clip_index?` |
| `set_track_input_routing` | Route a track's input (e.g. `"Resampling"` = master bus) | `track_index`, `routing_name` |
| `set_track_monitor` | Monitor state: 0 In · 1 Auto · 2 Off | `track_index`, `state` |

**Bounce a loop to WAV** — `export_audio` does the whole capture chain for you (creates a
Resampling track, monitor Off, arms, relaunches the scene, records, reads the file path):
```
export_audio(bars=16, scene_index=0)
→ {"recording": {"file_path": ".../Samples/Recorded/….wav"}}
```
Launch quantization can offset the start by up to a bar — capture a couple extra bars for a clean loop.
The WAV lands in the set's `Samples/Recorded/` folder.

**Multi-scene continuous capture** — `export_tutorial` records several scenes seamlessly into
one WAV and returns absolute `segment_start_seconds` per scene (offsets into that file):
```
export_tutorial(scene_bars=[4,4,4,8], content_tracks=[2,3,4,5], scene_start=0)
→ {"recording": {...}, "segment_start_seconds": [0.0, 8.0, 16.0, 24.0]}
```
`content_tracks` are the *backing* tracks to play through the capture (not the capture track);
they are fired per-boundary off the live transport so a scene launch never interrupts recording.
Mute any live/student track first so it stays out of the backing.

**Manual resampling** (fine control) — if you need custom routing, do it by hand:
```
create_audio_track() → set_track_input_routing(N, "Resampling") → set_track_monitor(N, 2) → set_track_arm(N, True)
set_launch_quantization("none")
fire_clip_slot(track_index=N)        # arms recording into the slot
fire_scene(index=0)                  # play the material
# ...wait the material's length, then...
stop_playback()
get_clip_file_path(track_index=N)    # → recorded WAV path
```

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
