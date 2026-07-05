# AbletonMCP Skill Pack — Claude Desktop install

Six skills that teach Claude how to produce music in Ableton Live via the AbletonMCP server,
with deep dance-music production knowledge (drums, synthesis, bass, sampling, theory, mixing,
mastering, arrangement, and vocals).

| Zip | Skill | Loads when |
|---|---|---|
| `ableton-skill.zip` | **ableton-skill** (base) | Always — session control, orientation, routing to the others |
| `ableton-skill-compose.zip` | compose | Writing beats, clips, chords, bass, melody |
| `ableton-skill-sounds.zip` | sounds | Browser, instruments/effects, device params, audio-clip / vocal editing |
| `ableton-skill-arrange.zip` | arrange | Scenes, song structure, timeline, recording (incl. vocal takes), export |
| `ableton-skill-mix.zip` | mix | Levels, EQ, compression, sends, mastering |
| `ableton-skill-theory.zip` | theory | Scales, chords, progressions, harmony |

`ableton-skill-pack-all.zip` is just a convenience bundle of all six zips — **you still upload each
skill's own zip individually** (Claude Desktop imports one skill per upload).

---

## Two halves — you need BOTH

1. **These skills** = the knowledge + workflows (uploaded to Claude Desktop, below).
2. **The AbletonMCP MCP server** = the actual tools (`get_all_tracks_info`, `create_midi_track`,
   `set_audio_clip_properties`, …) that the skills call. Without the server connected, the skills
   have nothing to drive Ableton with.

### Step 1 — Connect the AbletonMCP server (once)
In Claude Desktop: **Settings → Developer → Edit Config** → open `claude_desktop_config.json` and add:

```json
{
  "mcpServers": {
    "ableton-skill": {
      "command": "uvx",
      "args": ["ableton-skill"]
    }
  }
}
```

Then restart Claude Desktop. (This is the same config from the repo README. Requires `uv`/`uvx`
installed. Run only one instance of the server — not Cursor and Desktop at once.)

### Step 2 — Run the Remote Script in Ableton
Install the AbletonMCP Remote Script as a Control Surface in **Ableton → Preferences →
Link/Tempo/MIDI**, and keep Ableton open. (See the repo README for the one-time install; after any
Remote Script change run `./deploy_remote_script.sh` and restart Ableton.)

### Step 3 — Enable Code execution in Claude Desktop
Custom skills require it: **Settings → Capabilities → enable Code execution**
(Team/Enterprise: an owner enables it in Organization settings → Skills).

### Step 4 — Upload the skills
For **each** of the six zips:
**Customize → Skills → “+” → Create skill → Upload a skill →** choose the `.zip`.

Recommended order: upload **`ableton-skill.zip` (base) first**, then the five stage skills. Skills
are private to your account. The folder name inside each zip already matches the skill name (a
requirement) — upload the zips as-is, don't re-zip their contents.

---

## Verify it works
Open a new chat and try: *“What tracks are in my Ableton session?”* Claude should load the base
`ableton-skill`, call `get_all_tracks_info`, and report your tracks. Then try *“make a deep house
beat”* or *“tune this vocal clip to the key”*.

## Notes
- If Claude answers about Ableton but never actually changes anything, the **skills loaded but the
  MCP server isn't connected** — recheck Step 1/2.
- If upload fails with “missing SKILL.md” or “folder name doesn’t match”, re-download the zip from
  `skill-pack/` and upload it unmodified.
- Rebuild these zips after editing the source skills with: `./build_desktop_pack.sh`.
