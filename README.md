# Ableton Skill — Ableton Live Integration for Claude
[![smithery badge](https://smithery.ai/badge/@ahujasid/ableton-skill)](https://smithery.ai/server/@ahujasid/ableton-skill)

Ableton Skill connects Ableton Live to Claude AI, allowing Claude to directly interact with and control Ableton Live. This integration enables prompt-assisted music production — from writing the first beat to building a full arrangement.

### Join the Community

Give feedback, get inspired, and build on top of Ableton Skill: [Discord](https://discord.gg/3ZrMyGKnaU). Made by [Siddharth](https://x.com/sidahuj)

## Features

- **Two-way synchronization**: Claude both controls Ableton *and* listens to it — subscribe to live state changes (tempo, playback, track edits) so Claude always knows what's happening in your session without you having to describe it. This means Claude can react to what you do manually, pick up context automatically, and give suggestions that reflect the actual current state of the project.
- **Music theory intelligence**: Generate chords, progressions, bass lines, and melodies from genre and scale context — no manual note entry required
- **Track manipulation**: Create, modify, and manipulate MIDI and audio tracks
- **Instrument and effect selection**: Search Ableton's library by tag or name and load sounds directly onto tracks
- **Clip creation**: Write, edit, and humanize MIDI clips with full note control
- **Scene and arrangement**: Manage session scenes, build song sections, and record into the Arrangement timeline
- **Mixing**: Set levels, panning, mute/solo, sends, and adjust device parameters

## How It Works

Two components communicate over a local TCP socket:

```
Claude (via MCP client)
      │
      ▼
MCP_Server/server.py          ← runs outside Ableton, exposes all tools
      │  TCP :9877
      ▼
AbletonMCP_Remote_Script/     ← Ableton MIDI Remote Script, calls Live Python API
__init__.py
```

### Skill Architecture — Progressive Disclosure

When using Claude Code or the Claude desktop app, Ableton Skill loads specialized skills depending on what you're doing. This keeps context lean — only the relevant guidance enters the conversation.

| Stage | Skill | Loaded when |
|---|---|---|
| Session control | `ableton-skill` | Always — base orientation and transport |
| Compose | `ableton-skill-compose` | Writing beats, clips, chords, bass, melody |
| Sounds | `ableton-skill-sounds` | Browsing library, loading instruments/effects, tweaking device parameters |
| Arrange | `ableton-skill-arrange` | Scene management, song structure, Arrangement timeline |
| Mix | `ableton-skill-mix` | Levels, panning, sends, EQ, compression |
| Theory | `ableton-skill-theory` | Deep music theory — scales, chord recipes, genre patterns |

For most tasks Claude loads one stage skill alongside the base. Multi-stage tasks (e.g. compose + mix) load two. The theory skill loads only when you ask a deep theory question.

## Installation

### Installing via Smithery

To install Ableton Live Integration for Claude Desktop automatically via [Smithery](https://smithery.ai/server/@ahujasid/ableton-skill):

```bash
npx -y @smithery/cli install @ahujasid/ableton-skill --client claude
```

### Prerequisites

- Ableton Live 10 or newer
- Python 3.8 or newer
- [uv package manager](https://astral.sh/uv)

If you're on Mac, please install uv as:
```
brew install uv
```

Otherwise, install from [uv's official website][https://docs.astral.sh/uv/getting-started/installation/]

⚠️ Do not proceed before installing UV

### Claude for Desktop Integration

[Follow along with the setup instructions video](https://youtu.be/iJWJqyVuPS8)

1. Go to Claude > Settings > Developer > Edit Config > claude_desktop_config.json to include the following:

```json
{
    "mcpServers": {
        "ableton-skill": {
            "command": "uvx",
            "args": [
                "ableton-skill"
            ]
        }
    }
}
```

### Cursor Integration

Run ableton-skill without installing it permanently through uvx. Go to Cursor Settings > MCP and paste this as a command:

```
uvx ableton-skill
```

⚠️ Only run one instance of the MCP server (either on Cursor or Claude Desktop), not both

### Installing the Ableton Remote Script

[Follow along with the setup instructions video](https://youtu.be/iJWJqyVuPS8)

1. Download the `AbletonMCP_Remote_Script/__init__.py` file from this repo

2. Copy the folder to Ableton's MIDI Remote Scripts directory. Different OS and versions have different locations. **One of these should work, you might have to look**:

   **For macOS:**
   - Method 1: Go to Applications > Right-click on Ableton Live app → Show Package Contents → Navigate to:
     `Contents/App-Resources/MIDI Remote Scripts/`
   - Method 2: If it's not there in the first method, use the direct path (replace XX with your version number):
     `/Users/[Username]/Library/Preferences/Ableton/Live XX/User Remote Scripts`
   
   **For Windows:**
   - Method 1:
     C:\Users\[Username]\AppData\Roaming\Ableton\Live x.x.x\Preferences\User Remote Scripts 
   - Method 2:
     `C:\ProgramData\Ableton\Live XX\Resources\MIDI Remote Scripts\`
   - Method 3:
     `C:\Program Files\Ableton\Live XX\Resources\MIDI Remote Scripts\`
   *Note: Replace XX with your Ableton version number (e.g., 10, 11, 12)*

4. Create a folder called 'AbletonMCP' in the Remote Scripts directory and paste the downloaded '\_\_init\_\_.py' file

3. Launch Ableton Live

4. Go to Settings/Preferences → Link, Tempo & MIDI

5. In the Control Surface dropdown, select "AbletonMCP"

6. Set Input and Output to "None"

## Usage

### Starting the Connection

1. Ensure the Ableton Remote Script is loaded in Ableton Live
2. Make sure the MCP server is configured in Claude Desktop or Cursor
3. The connection should be established automatically when you interact with Claude

### Using with Claude

Once the config file has been set on Claude, and the remote script is running in Ableton, you will see a hammer icon with tools for Ableton Skill.

## Capabilities

**Session & Transport**
- Get session info, track list, scale mode, playback position
- Set tempo, time signature, metronome; tap tempo; undo/redo
- Start/stop playback, stop all clips

**Compose**
- Create MIDI and audio tracks; duplicate, color, arm, delete
- Create clips, write/edit MIDI notes (`add_notes_to_clip` **replaces by default**, `replace=False` to append), set clip loop, color, name
- Generate chords, progressions, bass lines, melodies with music theory built in
- Humanize patterns for a natural feel

**Sounds**
- Search Ableton's library by tag (`search_by_tags`) — works without Live running
- Load instruments, effects, drum kits; place samples on specific drum-rack pads; browse the user library
- Read and set any device parameter including nested racks and Drum Rack pads
- Edit audio clips — warp mode, pitch/transpose, gain (`set_audio_clip_properties`) for tuning vocals, pitching chops, and time-stretch feel

**Arrange**
- Create, name, color, and fire scenes
- Switch to the Arrangement timeline; move the playhead; list arrangement clips
- Arm arrangement recording; capture recently played MIDI; set launch quantization
- Export/bounce audio to WAV via real-time resampling (single scene or multi-scene)
- Read cue point markers

**Mix**
- Set track volume, panning, mute, solo
- Create return tracks; set send levels from any track to any return
- Adjust EQ, compression, or any device parameter on regular, return, and master tracks

**Vocals** (spans record → edit → process)
- Record a mic/live take: discover I/O (`get_track_io`), route input (`set_track_input_routing` / `set_track_input_channel`), monitor, arm, and record into a slot
- Tune/warp/gain the recorded clip (`set_audio_clip_properties` — Complex Pro for natural vocals)
- Process it with the mixing device tools (EQ, compression, de-essing, reverb sends)

**Events**
- Subscribe to live state changes: tempo, playback, song time, track count
- Poll for queued events with `get_pending_events`

## Example Commands

**Beat building**
- "Create a Metro Boomin style hip-hop beat" 
- "Create an 80s synthwave track" [Demo](https://youtu.be/VH9g66e42XA)
- "Load a 808 drum rack and write a trap pattern"

**Composition**
- "Add a deep house bass line in A minor"
- "Generate a ii–V–I chord progression in G major and humanize it"
- "Write an arching 2-bar melody over the chords"

**Sound design**
- "Find a warm pad sound and load it onto track 2"
- "Turn up the filter cutoff on the synth on track 3"
- "Add reverb and adjust the decay time"

**Arrangement**
- "Create scenes for Intro, Verse, Chorus, and Outro"
- "Switch to Arrangement view and record each scene in sequence"
- "Create a return track and add 30% reverb send from the lead"

**Session management**
- "Set the tempo to 128 BPM and switch to 4/4"
- "Mute all tracks except the drums"
- "Color-code all tracks by role"


## Troubleshooting

- **Connection issues**: Make sure the Ableton Remote Script is loaded, and the MCP server is configured on Claude
- **Timeout errors**: Try simplifying your requests or breaking them into smaller steps
- **Stale Remote Script** (`Unknown command: …` errors, or new behavior missing — e.g. MIDI notes *stacking* instead of replacing): Ableton loads the Remote Script copy from **inside the app bundle**, which can lag the repo. Run `./deploy_remote_script.sh` (copies the script into every installed Ableton app and clears bytecode), then restart Ableton or reselect the AbletonMCP control surface in Preferences → Link/Tempo/MIDI.
- **Have you tried turning it off and on again?**: If you're still having connection errors, try restarting both Claude and Ableton Live

## Technical Details

### Communication Protocol

Commands are sent as JSON over TCP (`localhost:9877`):

```json
{ "type": "create_midi_track", "params": { "index": -1 } }
{ "status": "success", "result": { "name": "1-MIDI", "index": 0 } }
```

State-mutating commands are dispatched to Ableton's main thread via `schedule_message`. Read-only commands run directly on the socket thread.

### Notes & Limitations

- **Save manually**: saving `.als` sets is not exposed by the Live API — use Cmd+S in Ableton
- **Group tracks**: `create_group_track` does not exist in the Live Python API; use Cmd+G in Ableton to group tracks manually
- **Arrangement clips**: `get_arrangement_clips` requires Live 11 or newer
- **Tag search**: `search_by_tags` reads Ableton's local SQLite database directly — Live does not need to be running for this call
- Always save your work before extensive experimentation

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Disclaimer

This is a third-party integration and not made by Ableton.
