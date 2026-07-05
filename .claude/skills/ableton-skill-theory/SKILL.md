---
name: ableton-skill-theory
description: >
  Music theory reference and generation guide for the AbletonMCP server. Use this skill when
  you need detailed guidance on: scale names and intervals, chord types and voicings, diatonic
  progression recipes, genre-specific bass pattern styles, melody generation parameters, or
  humanization amounts. Also use it when the user asks about music theory in the context of
  Ableton (e.g. "what chords work in D dorian?", "what's a good bass style for techno?",
  "how do I write a jazz ii-V-I?"). This skill complements the ableton-skill skill — it covers
  the musical intelligence behind the generate_* and humanize_notes tools.
compatibility: "Companion to the ableton-skill skill. Requires ableton-skill to be active."
---

# AbletonMCP — Music Theory Guide

This skill covers the musical intelligence embedded in the AbletonMCP theory tools.
All `generate_*` and `humanize_notes` tools return note dicts with **no side effects** —
always pass the result to `add_notes_to_clip` or `create_track_with_clip` to write into Ableton.

---

## When to Use Which Tool

| Goal | Tool |
|---|---|
| One chord to place in a clip | `generate_chord` |
| A full progression (I-V-vi-IV, ii-V-I, etc.) | `generate_chord_progression` |
| A bass line that fits a genre | `generate_bass_pattern` |
| A melody phrase for a lead, pad, or arp | `generate_melody` |
| Make any pattern feel human | `humanize_notes` — apply last, before writing to clip |

---

## Scale Reference

All theory tools accept `scale_name` (case-insensitive, spaces or underscores OK).
When `root_note` and `scale_name` are omitted, tools read Ableton's current scale automatically —
set the key in Live's Scale panel first for hands-free context.

| `scale_name` | Intervals | Character |
|---|---|---|
| `major` | 0-2-4-5-7-9-11 | Bright, resolved |
| `minor` | 0-2-3-5-7-8-10 | Natural minor — melancholic |
| `dorian` | 0-2-3-5-7-9-10 | Minor with raised 6th — funky, jazzy |
| `phrygian` | 0-1-3-5-7-8-10 | Minor with ♭2 — dark, Spanish, metal |
| `lydian` | 0-2-4-6-7-9-11 | Major with ♯4 — dreamy, cinematic |
| `mixolydian` | 0-2-4-5-7-9-10 | Major with ♭7 — bluesy, rock, gospel |
| `locrian` | 0-1-3-5-6-8-10 | Diminished feel — very dark, unstable |
| `harmonic_minor` | 0-2-3-5-7-8-11 | Raised 7th — classical, dramatic |
| `melodic_minor` | 0-2-3-5-7-9-11 | Raised 6+7 — jazz, modern |
| `pentatonic_major` | 0-2-4-7-9 | 5-note major — folk, country, simple solos |
| `pentatonic_minor` | 0-3-5-7-10 | 5-note minor — rock, blues, riffs |
| `blues` | 0-3-5-6-7-10 | Pentatonic minor + ♭5 — blues, soul, R&B |
| `whole_tone` | 0-2-4-6-8-10 | All whole steps — impressionistic, floaty |
| `diminished` | 0-2-3-5-6-8-9-11 | Alternating half/whole — tense, jazz |
| `chromatic` | 0-1-2…11 | All 12 tones — atonal, free |

---

## Chord Types and Voicings

### `chord_type` values

| Type | Intervals | Feel |
|---|---|---|
| `maj` | 0-4-7 | Bright, stable |
| `min` | 0-3-7 | Sad, stable |
| `dim` | 0-3-6 | Tense, unstable |
| `aug` | 0-4-8 | Dreamy, unresolved |
| `maj7` | 0-4-7-11 | Warm, sophisticated |
| `min7` | 0-3-7-10 | Melancholic, smooth |
| `dom7` | 0-4-7-10 | Bluesy, tense (wants to resolve to I) |
| `dim7` | 0-3-6-9 | Dramatic, fully symmetric |
| `half_dim7` | 0-3-6-10 | Jazz minor ii chord |
| `sus2` | 0-2-7 | Open, ambiguous |
| `sus4` | 0-5-7 | Suspended, resolves naturally |
| `add9` | 0-4-7-14 | Modern, airy |
| `maj9` | 0-4-7-11-14 | Rich, R&B/neo-soul |
| `min9` | 0-3-7-10-14 | Lush, melancholic |

### `voicing` options

| Voicing | Effect | Best for |
|---|---|---|
| `close` | Stacked intervals as-is | Piano, synth stabs |
| `open` | Alternate notes raised an octave | Guitar-style, spacious |
| `drop2` | 2nd-highest note dropped an octave | Full-bodied, orchestral |
| `spread` | Each note raised by one more octave | Cinematic pads, wide |

---

## Diatonic Chord Progressions

`generate_chord_progression(degrees=[...])` auto-assigns chord quality from the scale.

**In major:** I=maj, II=min, III=min, IV=maj, V=maj, VI=min, VII=dim
**In minor:** I=min, II=dim, III=maj, IV=min, V=min, VI=maj, VII=maj

### Proven progression recipes

| Name | Degrees | Genre |
|---|---|---|
| Pop anthem | `[1, 5, 6, 4]` | Pop, rock |
| Minor pop | `[1, 6, 3, 7]` | Indie, singer-songwriter |
| Jazz ii–V–I | `[2, 5, 1]` | Jazz (works in major or minor) |
| Blues turnaround | `[1, 4, 1, 5, 4, 1]` | Blues |
| 12-bar blues | `[1,1,1,1, 4,4,1,1, 5,4,1,5]` (1 bar each) | Blues, rock'n'roll |
| Andalusian cadence | `[1, 7, 6, 5]` (phrygian) | Flamenco, dark electronic |
| Epic/cinematic | `[1, 6, 4, 5]` | Trailer, film |
| Pachelbel | `[1, 5, 6, 3, 4, 1, 4, 5]` | Classical, baroque-inspired |
| Modal vamp | `[1, 2]` (dorian/mixolydian) | Jazz, lounge, groove |
| Minor ii–V–i | `[2, 5, 1]` (harmonic_minor) | Jazz minor, bossa |
| Coltrane changes | `[1, 3, 6, 4, ...]` | Advanced jazz |

**Tip:** `bars_per_chord=2.0` gives each chord 2 bars — good for slow ballads. `bars_per_chord=0.5` makes a rapid 2-chord-per-bar vamp.

### Named dance-track progressions (all minor key, degrees)

Real reference progressions (from *Secrets of Dance Music Production*) — feed straight to `generate_chord_progression(degrees=[...], scale_name="minor")`:

| Track | Degrees |
|---|---|
| Avicii — *Levels* | `[1, 3, 7, 6]` |
| Nicky Romero — *Like Home* | `[1, 7, 3, 6]` |
| Swedish House Mafia — *Don't You Worry Child* | `[7, 1, 6, 6]` |
| Disclosure — *You & Me* | `[4, 7, 1, 1]` |
| Burial — *Archangel* | `[6, 5, 4, 4]` |
| Black Box — *Ride On Time* | `[1, 3, 6, 7]` |
| Daft Punk — *Around The World* | `[5, 6, 1, 1]` |

Surefire floor-fillers: **`vi–I`** and **`IV–V–I`**. Resolution usually lands on the tonic — *delaying, denying, or surprising* it (deceptive cadence, out-of-key stab) is more powerful than always resolving.

### Chord development for dance genres

- **maj7** (root, +4, +7, +11) — deep/disco house, jazzy. **min7** (root, +3, +7, +10) — dark techno/dub stabs. **9ths** are easier than 7ths (same added note over major or minor). **min9** — dark reverbed techno. **sus2/sus4** (drop the 3rd) — unresolved tension. **add9/add2** (no 7th) — dark, oppressive (techno/D&B).
- **Sampled-triad-in-key rule:** a chord *shape* transposed across the keys only stays in key on **I, IV, V** roots (9th chords only on **I & IV**). Breaking this deliberately gives the classic **out-of-key old-school stab** flavour — often desirable, not wrong.

---

## Cadences, Substitutions & Borrowing

The practical rule-set for writing progressions that resolve — or that hang, endlessly, for a loop.

**Magic chords: `1 · 4 · 5 · 6`.** These four degrees carry most electronic/pop harmony.

### Harmonic function — the engine (T · SD · D)

Every diatonic chord belongs to one of three **functional areas**. Harmony is the motion
*between* areas — this is *why* the substitution groups below work (each area's chords are
interchangeable):

| Area | Chords (degrees) | Feeling |
|---|---|---|
| **Tonic (T)** | **1 · 3 · 6** | Home, rest, resolved |
| **Subdominant (SD)** | **2 · 4** | Departure, motion away (pre-dominant) |
| **Dominant (D)** | **5 · 7** | Tension, wants to resolve to T |

The two fundamental motions: **T → D → T** (simplest tension/release) and the full
**T → SD → D → T** (departure → build → tension → home). Every classic progression is a
decoration of these — e.g. `1 6 4 5` = T–T–SD–D, `1 4 5 1` = T–SD–D–T.

### Cadences — how a phrase lands (Book 3 taxonomy)

| Cadence | Motion | Effect |
|---|---|---|
| **Perfect Authentic (PAC)** | `5 → 1`, both root position, melody ends on 1 | Strongest resolution — full stop |
| **Imperfect Authentic (IAC)** | `5 → 1` but inverted or melody not on 1 | Softer landing |
| **Leading-tone IAC** | `7° → 1` | Gentle authentic resolution |
| **Plagal** | `4 → 1` | "Amen", warm resolution |
| **Half** | `any → 5` | Hangs, unresolved — *ideal for loops* |
| **Deceptive** | `5 → 6` | Sets up 1, resolves to 6 instead — surprise, keeps energy going |
| **SD → D** | e.g. `4 → 5` | Builds tension into a following resolution |

**Rules for sweet progressions:** ① nearly always end on a cadence · ② start on any degree, but
**1 is always safe** · ③ put anything in the middle · ④–⑥ substitute freely (below) · ⑦ borrow the
same degree from any mode sharing the tonic.

**Half-cadences (suspenseful / *endless* — ideal for looping club tracks):** end on **any → 5**,
`1 → 4`, or `5 → 4`. The progression **must start on `1`** so the loop's return home resolves the
suspense. A **deceptive** `5 → 6` is another great loop engine — it denies the resolution every pass.

**In-scale substitutions** — swap any degree for its functional cousin (same area, shared notes):
| Swap group | Interchangeable degrees |
|---|---|
| Tonic family | **1 ↔ 3 ↔ 6** (treat a 3 as "really a 1 or 6") |
| Subdominant | **2 ↔ 4** (treat a 2 as "really a 4") |
| Dominant | **5 ↔ 7** (treat a 7 as "really a 5") |

**Borrowing & modal interchange** — take a chord from *outside* the current scale:
- **Chord borrowing / modulation:** pull a degree from the **parallel** scale (same tonic, e.g. C major → C minor). When a borrowed chord plays, use *that mode's* scale tones for the melody over it.
- **Mediant substitution:** major/minor chords a mediant / sub-mediant (a third) away.
- **Neo-Riemannian:** chords that are physically close (share notes) regardless of any scale.
- In Scaler these map to **Modulation**, **Mediant**, and **Neo-Riemannian** modes.

**Advanced tension (jazz / reharmonization):**
- **Secondary dominant** — borrow the *dominant of a non-tonic chord* to tonicise it. A `dom7` a
  fifth above the target (written `V/x`), e.g. before the `2` chord play `V/2` (its own V7). Adds a
  strong pull to any degree, not just the tonic.
- **Tritone substitution** — replace a `dom7` (V7) with the dom7 a **tritone** (6 semitones) away;
  they share the same guide-tones, so it resolves the same way with a chromatic bassline.
- **Reharmonization** — keep the melody, change the chords under it (swap within an area, add a
  secondary dominant, or reharmonise the whole phrase). The fastest way to vary a repeated section.

**Chord extensions & alterations** (colour beyond triads — several already in the `chord_type` table):
- **add** (add9), **7ths**, **extended** 9 / 11 / 13 (stack more thirds), **sus** (2/4 replacing the 3rd),
  **omit** (drop the 5th or root for space), **alterations** (♯5/♭5/♯9/♭9 for bite).
- **Slash chords / inversions** — put a non-root chord tone in the bass (`C/E`, `C/G`) for smoother
  bass movement and voice-leading between chords.

**Chord-quality shortcuts:** diminished = 5th a semitone **down** · augmented = 5th a semitone **up**
· suspended = replace the 3rd with a 4th (or 2nd) · relative minor = **3 semitones down** from the major.

**Parallel harmony (melodic-house signature):** transpose an entire chord *shape* up/down by a fixed
interval so every note moves the same amount. Ignores voice-leading — gives that "alien", emotive
Anjunadeep colour, and is trivial to program (one shape, shifted).

---

## Genre Bass Patterns

`generate_bass_pattern(style=...)` produces genre-authentic rhythm, pitch movement, and velocity curves.

| Style | Rhythmic character | Root movement |
|---|---|---|
| `deep_house` | Root pulse + ghost sub on the off-beat | Root dominant, occasional -12 sub |
| `techno` | Relentless 8th-note grid | Pure root, machine-like |
| `hip_hop` | Heavy slow notes, chromatic slide | Root + ♭5 movement |
| `funk` | Tight 16th-note groove | Root, 5th, 4th — lots of movement |
| `reggae` | Skank on beats 2 and 4 | Root only, very sparse |
| `drum_and_bass` | Fast pickup + dramatic sub drop | Root + -12 sub |
| `afrobeats` | Syncopated with anticipations | Root, 4th, 5th ornaments |
| `pop` | Simple quarter-note roots | Clear, supportive |
| `latin` | Tumbao feel — anticipations | Syncopated with passing tones |
| `jazz` | Walking-style | Root + passing tones via 4th/5th/chromatic |

**Pro tip:** Run `bars=2` or `bars=4` for a longer loop. Bass patterns tile perfectly — the same pattern repeats across all bars.

---

## Melody Generation

`generate_melody` uses a step-biased random walk: 60% step (1–2 scale degrees), 25% leap (3–4), 15% rest.

### `density` options

| Density | Grid | Fill % | Feel |
|---|---|---|---|
| `sparse` | 8th-note | 50% | Airy, spacious — good for pads |
| `medium` | 8th-note | 70% | Natural, singable |
| `dense` | 16th-note | 80% | Busy, ornamental |

### `contour` options

| Contour | Shape | Use |
|---|---|---|
| `arch` | Rises to midpoint, falls back | Most musical default — question + answer |
| `ascending` | Generally moves upward | Build-up, tension |
| `descending` | Generally moves downward | Resolution, comedown |
| `static` | Stays within 3 scale steps of root | Vamp, ostinato, riff |
| `random` | No directional bias | Atonal feel, experimental |

**Tips:**
- `start_degree=5` opens on the 5th scale degree — gives a "question phrase" that wants to resolve
- `octave_range=2` spans two octaves for more drama; use with `contour="arch"` for a climactic arc
- Generate two 2-bar phrases with different contours (`arch` then `descending`) and combine for a complete 4-bar melody

---

## Humanize Recommendations

Apply `humanize_notes` last, just before passing notes to `add_notes_to_clip` or `create_track_with_clip`. Use `seed` for reproducible results while iterating.

| Context | `timing_amount` | `velocity_amount` | `duration_amount` |
|---|---|---|---|
| Tight electronic (techno, house) | 0.005–0.015 | 5–8 | 0.01–0.03 |
| Natural feel (pop, jazz, soul) | 0.02–0.04 | 10–15 | 0.03–0.06 |
| Very loose (funk, hip-hop, reggae) | 0.03–0.06 | 12–20 | 0.05–0.10 |
| Drum patterns | 0.01–0.025 | 8–12 | 0.01–0.02 |
| Orchestral/cinematic | 0.02–0.05 | 8–18 | 0.05–0.12 |

---

## End-to-End Composition Example

```
# 1. Get the key context from Ableton
get_scale_mode()
→ {root_note: 9, root_note_name: "A", scale_name: "Minor"}

# 2. Chord progression (A minor, i–VI–III–VII)
generate_chord_progression(degrees=[1,6,3,7], root_note="A3", scale_name="minor",
                            bars_per_chord=1.0, voicing="open")
→ {notes: [...], clip_length: 4.0, chord_names: ["Amin", "Fmaj", "Cmaj", "Gmaj"]}

humanize_notes(notes, timing_amount=0.02, velocity_amount=10)
create_track_with_clip(track_name="Chords", notes=..., clip_length=4.0)

# 3. Bass pattern (deep house feel rooted on A)
generate_bass_pattern(style="deep_house", root_note="A2", scale_name="minor", bars=4)
→ {notes: [...], clip_length: 16.0}

humanize_notes(notes, timing_amount=0.01, velocity_amount=6)
create_track_with_clip(track_name="Bass", notes=..., clip_length=16.0)

# 4. Melody (arch contour over 2 bars)
generate_melody(root_note="A4", scale_name="minor", bars=2,
                density="medium", contour="arch", octave_range=1)
→ {notes: [...], clip_length: 8.0}

humanize_notes(notes, timing_amount=0.025, velocity_amount=12)
create_track_with_clip(track_name="Lead", notes=..., clip_length=8.0)

# 5. Play it
start_playback()
```
