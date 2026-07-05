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

## The 4 Golden Rules of a Great Mix

Genre-independent (from *The Secrets of Dance Music Production*). Judge every mix decision against these:

1. **Fills the frequency spectrum — with clarity.** Content from 30 Hz to 18–20 kHz, each element in its own range without piling up into mush.
2. **Dynamic — "no loud without soft".** Impacts hit hardest after calm. Shape energy at every level: transient, beat (hits vs gaps), and arrangement.
3. **Width and depth, but works in mono.** Push a sound *back* by lowering volume + softening its transient + rolling off highs + adding reverb. Kick & bass low and **central**; pads panned wide.
4. **Living / evolving — but ≤ 2–3 parts changing at once.** The ear can only track so much. Club < radio for rate of change, but never static across 64 bars.

Dance mixes are **context-specific**: club = big low end, less mid/high; radio = even spread + upper-mid activity. **Always check in mono** — never push pivotal parts far from centre.

---

## Mixing Method & Order

Work **in combination**, from the most important element outward (kick/bass first). Order of operations:

1. **Initial balance** — faders first; relative volume beats any process. Set the dominant elements (kick+bass, or lead) *first*, build the rest quieter around them. Avoid the "race to the top" (set levels too low rather than high). **Mix backwards from the loudest section (the drop) to keep headroom.**
2. **EQ the resonances** — sweep EQ Eight to find and tame each instrument's harsh/boomy peaks (1–3 dB cuts, gentle Q).
3. **EQ-bracket / top-and-tail** — high/low-cut each part to its useful band (see the frequency chart below): frees headroom + adds clarity. Use 12–18 dB/oct, sweep until the timbre changes, back off. Don't low-cut *everything* (brittle mix).
4. **Balance the frequency spectrum** — give the kick (50–100 Hz) and bass their own bands so nothing clashes.
5. **Glue the drums** — bus-compress or a short room reverb send so the kit sounds like one unit.

**Concrete level targets:** kick peaks ~**−15 to −12 dB**; individual channels ~**−15 to −18 dBFS**; master at **0 dBFS / unity**. **Never let any channel, insert, bus, or the master exceed 0 dBFS** — digital just clips (and clipping sounds bad). Fix mix problems in the **arrangement** first (mute non-essentials, re-voice clashing synths) before reaching for EQ.

**Sidechain compression** (the house "pump"): key a Compressor on the bass/pad tracks from the kick
so they duck on every kick hit. In Ableton, trigger from a **muted 4/4 kick track** (Impulse), Detection = **Peak**, and **sync the release to tempo** (at 120 BPM a 1/16 = **125 ms**) — this pumps even in breakdowns where no audible kick plays. Put the comp's **sidechain HPF ~145 Hz** (up to 250 Hz on a bus) so only the low end triggers it.

**Mono the low end:** put a `Utility` on the bass with **Width = 0** (or `EQ Eight` → Mid/Side, cut
Sides below ~100–150 Hz) so sub frequencies stay centred and phase-solid. Keep kick & bass **dry** (no reverb). Check the whole mix in mono.

---

## Mixing Reference (dance music)

### EQ — "what goes where" (fundamentals & fix zones, Hz)

| Element | Low / weight | Body / knock | Presence / bite | Air / sizzle |
|---|---|---|---|---|
| **Kick** | 20–60 (808 peak 40–60) | 60–80 weight · 120–600 knock | 1–4 k click | 3–8 k crack |
| **Snare** | roll < 70–100 | 120–350 body/balls | ~1 k crack (cut harsh 1–4.5 k) | 6–8 k snap · 10 k air |
| **Hi-hats** | roll < 250–300 | 1–3 k body | 5–8 k sibilance (de-ess) | 8–11 k sparkle |
| **Bass** | 50–120 power | 250 fat · 600–700 growl | 700 – 1.2 k def | harmonics to 8 k |
| **Sub** | 16–60 (mono!) | — | — | — |
| **Lead** | 60 Hz–8 k overall; check overlap with bass | | | |
| **Pads** | warmth 200–400 | presence 1.2 k | (mix low + top-and-tail) | |
| **Keys** | full to 80 | presence 2.4–4 k | roll lows | |
| **Vocal** | roll < 80 | 200–700 body · 1 k nasal(cut) | 4–6 k presence | 11–12 k air (+1–2 dB) |

**EQ rules:** cuts sound more natural than boosts · **cut narrow, boost wide** · narrow-Q boost + sweep = "search & destroy" a resonance, then cut it.

### Compressor starting points (per source)

| Source | GR | Ratio | Attack | Release | Notes |
|---|---|---|---|---|---|
| Kick | 2–8 dB | 2:1–4:1 | 2–20 ms | ~0.6 ms fast | attack sets punch vs weight |
| Snare | 2–8 dB | 3:1–5:1 | 0.5–120 ms | 5–180 ms | slow attack = more transient |
| Bass | 3–6 dB | 3:1–8:1 | 0–30 ms | 0.5–2 s | busier line → lower ratio |
| Vocal (up-front) | 2–6 dB | 2:1–5:1 | 10–25 ms | auto / 100–250 ms | too-fast attack clips word starts |
| Bus glue | 2–5 dB | 1.1:1–2:1 | 0.1 ms | Auto | slow-ish attack keeps punch |
| Bus pump | 4–10 dB | 5:1–10:1 | 0.1–0.3 ms | Auto (to tempo) | audible pumping |
| Parallel smash | 15–20 dB | 10:1–∞ | 0.5–20 ms | Auto | blend 10–30 % under dry |

Character: **VCA/Glue** = transparent glue · **Optical (LA-2A)** = musical vocals/bass · **FET (1176)** = aggressive kick/snare/parallel · two comps in series (lower ratios) beat one pushed hard.

### Kick + bass (the make-or-break relationship)

Both share the low end — keep both **dry, central, focused**, and choose **complementary** peaks (808 at 60 Hz → pick a bass peaking ~80 Hz). Three models:
- **Low bass / upper kick** (D&B): bass fills subsonics, tight kick punches higher.
- **Low kick / upper bass**: 808 owns the sub; roll bass low end to ~80 Hz (Q 0.30), bass peaks 75–125 Hz.
- **Side-by-side**: find the kick fundamental (e.g. 61 Hz) → **cut the bass 3 dB there** + small boost around it; add kick→bass sidechain (2:1, 1 ms attack, 125 ms release, 2–3 dB); low-cut bass 48 dB/oct at 60 Hz.

**Best fix is arrangement:** write bass notes to fall *between* the kick hits, and shorten the bass release so it doesn't run into the next kick.

### Ambient sends (reverb / delay)

Use **no more than 3–4** total — one **short** + one **long** reverb on returns, feed tracks in varying amounts. Keep leads/kick/bass dry (or early-reflections only). **EQ-bracket the returns** (roll lows + highs) so ambience stays out of the kick/bass zone. Longer **pre-delay** (synced to tempo) and longer **tail** = further back. Pan a return opposite its dry signal. Delay: sync to tempo, feedback 20–40 %, EQ the return; trick = 1/8 + infinite feedback + automate the delay volume down.

### Common problems → fixes

| Symptom | Fix |
|---|---|
| **Harsh (2–5 k)** | bracket offenders; wide **1–2 dB dip at 3–5 kHz** on the music bus |
| **Muddy low end** | analyser; roll to 30–40 Hz; **tune the kick** so its fundamental dodges the bass; sidechain kick→bass |
| **Bass no punch** | don't cut too high; gently inflate **50–70 Hz** (Pultec-style) |
| **Flat / lifeless** | too much compression — reduce ratio/GR (a comp should hit 0 GR a few times per bar); build energy via arrangement + automation |
| **Too much ambience** | mute each FX return in turn; halve return levels; bracket returns |
| **D&B masking** | transient-shape everything; cut reverb/delay tails |

### Vocal chain (order)

Level-automate first (consistent level before FX) → **EQ** (HP 80–120 Hz, to ~300 Hz in a busy mix; cut 150–400 boxy, 1–1.5 k nasal, 2.5–6 k ring; boost wide 200–600 warmth, 2.5–6 k presence, 8–10 k air +1–2 dB) → **Compressor** (2:1–4:1, 3–5 dB GR, attack 10–25 ms; add a 2nd comp or limiter for spikes) → **De-esser** (3–8 kHz; male 3–6 k, female 4–10 k; last in chain) → **reverb/delay sends** (plate, pre-delay synced, roll the return < 100 Hz and > 5 kHz; de-ess *before* a bright reverb). Doubles pan ±19→±63; harmonies at 3rds/5ths lower in level. Keep chorus/widening off the lead (mono), on harmonies only.

---

## Mastering Chain (master track)

Applied on the **master** (`get_device_params(is_master=True, ...)`), in order:

1. **Corrective EQ** — search-and-destroy problem frequencies (mud 150–400 Hz cut ≤ 3 dB, etc.).
2. **Sweetening EQ** — cut narrow, boost wide & gentle. Typical moves: +1 dB @ 5.5 kHz (Q 2) for bite, +1.4 dB @ 40 Hz for warmth, air shelf 8–12 kHz, low-cut ~20 Hz.
3. **Glue Compressor** — attack ~0.3, release ~0.8, ratio 2–4:1, ~2–4 dB GR, makeup to match. **Two comps in series (lower thresholds) beat one pushed hard** for loudness.
4. **Mid/Side EQ** — **mono below ~100 Hz** (keeps bass powerful & centred); lift the **Sides +~25 %** above 100 Hz to widen.
5. **Limiter** (last) — ceiling **−0.3 dB**, raise gain for **~2–3 dB** reduction, release Auto, lookahead ~3 ms.

**Targets:** aim for **~−10 dB RMS** (−9 to −10 headroom is a respected range). Don't chase the loudness war — over-limiting rounds off transients (loses kick punch / snare crack) and *reduces* dancefloor energy; streaming normalises anyway. Deliver the master as **24-bit / 44.1 kHz WAV** (the source for all formats); mp3 ≥ 320 kbps for Beatport; dither to 16-bit for CD.

**Dance master edit:** mastering hypes the breakdown so the drop can lose impact — automate the master volume **down ~20 dB across the breakdown**, back to full at the drop, and cut **one bar of silence** before the drop (let reverb tails bleed) for a doubly-powerful hit.

---

## Reference: tempo → delay time & frequency bands

**Delay time (ms) = `60000 / BPM` for a 1/4 note.** Halve per division: 1/8 = 30000/BPM, 1/16 = 15000/BPM. Triplet × 2/3, dotted × 1.5.

| BPM | 1/4 | 1/8 | 1/16 |
|---|---|---|---|
| 120 | 500 | 250 | 125 |
| 124 | 484 | 242 | 121 |
| 125 | 480 | 240 | 120 |
| 128 | 469 | 234 | 117 |

**Frequency bands:** Sub **20–60** · Bass **60–250** · Mids **250–2 k** · High-mids **2–6 k** · Highs **6–20 k**. Zones: 20–40 pressure · 40–60 weight · 60–100 solidity · 100–260 warmth · 400–600 body/wood · 600–1 k crunch · 1–2 k definition · 2–4 k presence · 4–10 k clarity · 10–20 k air. (Middle C = 261.6 Hz, A = 440 Hz. Never put bass below **E1 = 41 Hz**.)

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
