# ableton_mcp_server.py
from mcp.server.fastmcp import FastMCP, Context
import socket
import json
import logging
import sqlite3
import glob
import os
from dataclasses import dataclass
from contextlib import asynccontextmanager
from typing import AsyncIterator, Dict, Any, List, Optional, Union

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AbletonMCPServer")

# ---------------------------------------------------------------------------
# Music Theory Data Tables
# ---------------------------------------------------------------------------

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

SCALE_INTERVALS: Dict[str, List[int]] = {
    "major":            [0, 2, 4, 5, 7, 9, 11],
    "minor":            [0, 2, 3, 5, 7, 8, 10],
    "dorian":           [0, 2, 3, 5, 7, 9, 10],
    "phrygian":         [0, 1, 3, 5, 7, 8, 10],
    "lydian":           [0, 2, 4, 6, 7, 9, 11],
    "mixolydian":       [0, 2, 4, 5, 7, 9, 10],
    "locrian":          [0, 1, 3, 5, 6, 8, 10],
    "harmonic_minor":   [0, 2, 3, 5, 7, 8, 11],
    "melodic_minor":    [0, 2, 3, 5, 7, 9, 11],
    "pentatonic_major": [0, 2, 4, 7, 9],
    "pentatonic_minor": [0, 3, 5, 7, 10],
    "blues":            [0, 3, 5, 6, 7, 10],
    "whole_tone":       [0, 2, 4, 6, 8, 10],
    "diminished":       [0, 2, 3, 5, 6, 8, 9, 11],
    "chromatic":        list(range(12)),
}

CHORD_INTERVALS: Dict[str, List[int]] = {
    "maj":       [0, 4, 7],
    "min":       [0, 3, 7],
    "dim":       [0, 3, 6],
    "aug":       [0, 4, 8],
    "maj7":      [0, 4, 7, 11],
    "min7":      [0, 3, 7, 10],
    "dom7":      [0, 4, 7, 10],
    "dim7":      [0, 3, 6, 9],
    "half_dim7": [0, 3, 6, 10],
    "sus2":      [0, 2, 7],
    "sus4":      [0, 5, 7],
    "add9":      [0, 4, 7, 14],
    "maj9":      [0, 4, 7, 11, 14],
    "min9":      [0, 3, 7, 10, 14],
}

# Diatonic degree (1–7) → chord quality for major and minor scales
DIATONIC_QUALITY: Dict[str, Dict[int, str]] = {
    "major": {1: "maj", 2: "min", 3: "min", 4: "maj", 5: "maj", 6: "min", 7: "dim"},
    "minor": {1: "min", 2: "dim", 3: "maj", 4: "min", 5: "min", 6: "maj", 7: "maj"},
}

# Genre bass patterns: (beat_offset, semitone_offset_from_root, duration_beats, velocity)
BASS_RHYTHM_PATTERNS: Dict[str, List[tuple]] = {
    "deep_house": [
        (0.0,  0,   0.25, 100), (0.5,   0,  0.25,  80),
        (1.0,  0,   0.5,   95), (2.0,   0,  0.25, 100),
        (2.75, -12, 0.25,  70), (3.0,   0,  0.5,   90),
    ],
    "techno": [
        (0.0,  0, 0.125, 110), (0.5,  0, 0.125,  90),
        (1.0,  0, 0.125, 105), (1.5,  0, 0.125,  85),
        (2.0,  0, 0.125, 110), (2.5,  0, 0.125,  90),
        (3.0,  0, 0.125, 105), (3.5,  0, 0.125,  85),
    ],
    "hip_hop": [
        (0.0, 0,  0.5, 100), (1.5,  0,  0.25, 85),
        (2.0, -5, 0.5,  95), (3.5,  0,  0.25, 80),
    ],
    "funk": [
        (0.0,  0,  0.125, 110), (0.25, 0,  0.125,  75),
        (0.5,  7,  0.125,  90), (1.0,  0,  0.25,  100),
        (1.5, -5,  0.125,  80), (2.0,  0,  0.125, 110),
        (2.5,  5,  0.125,  85), (3.0,  0,  0.5,    95),
        (3.5,  7,  0.125,  75),
    ],
    "reggae": [
        (1.0, 0, 0.5, 95), (3.0, 0, 0.5, 90), (3.75, 0, 0.25, 75),
    ],
    "drum_and_bass": [
        (0.0,  0,   0.25, 110), (0.75,   0, 0.125,  80),
        (1.0,  0,   0.25, 100), (1.5,  -12, 0.125,  70),
        (2.0,  0,   0.25, 110), (3.0,    0, 0.5,    95),
    ],
    "afrobeats": [
        (0.0, 0, 0.25, 100), (0.5, 5, 0.25,  85),
        (1.0, 0, 0.5,   95), (2.0, 7, 0.25,  90),
        (2.5, 0, 0.25,  80), (3.0, 0, 0.5,  100),
    ],
    "pop": [
        (0.0, 0, 0.5, 95), (1.0, 0, 0.5, 90),
        (2.0, 0, 0.5, 95), (3.0, 0, 0.5, 90),
    ],
    "latin": [
        (0.0, 0, 0.25, 105), (0.75, 7,  0.25,  85),
        (1.0, 0, 0.5,   95), (2.0,  5,  0.25,  90),
        (2.5, 0, 0.25,  80), (3.0,  0,  0.5,  100),
        (3.5, 7, 0.125, 75),
    ],
    "jazz": [
        (0.0, 0,  0.5, 90), (1.0, 7,  0.25, 75),
        (1.5, 5,  0.25, 70), (2.0, 0,  0.5,  85),
        (3.0, -5, 0.5,  80), (3.5, 0,  0.25, 65),
    ],
}

@dataclass
class AbletonConnection:
    host: str
    port: int
    sock: socket.socket = None
    
    def connect(self) -> bool:
        """Connect to the Ableton Remote Script socket server"""
        if self.sock:
            return True
            
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            logger.info(f"Connected to Ableton at {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Ableton: {str(e)}")
            self.sock = None
            return False
    
    def disconnect(self):
        """Disconnect from the Ableton Remote Script"""
        if self.sock:
            try:
                self.sock.close()
            except Exception as e:
                logger.error(f"Error disconnecting from Ableton: {str(e)}")
            finally:
                self.sock = None

    def receive_full_response(self, sock, buffer_size=8192):
        """Receive the complete response, potentially in multiple chunks"""
        chunks = []
        sock.settimeout(15.0)  # Increased timeout for operations that might take longer
        
        try:
            while True:
                try:
                    chunk = sock.recv(buffer_size)
                    if not chunk:
                        if not chunks:
                            raise Exception("Connection closed before receiving any data")
                        break
                    
                    chunks.append(chunk)
                    
                    # Check if we've received a complete JSON object
                    try:
                        data = b''.join(chunks)
                        json.loads(data.decode('utf-8'))
                        logger.info(f"Received complete response ({len(data)} bytes)")
                        return data
                    except json.JSONDecodeError:
                        # Incomplete JSON, continue receiving
                        continue
                except socket.timeout:
                    logger.warning("Socket timeout during chunked receive")
                    break
                except (ConnectionError, BrokenPipeError, ConnectionResetError) as e:
                    logger.error(f"Socket connection error during receive: {str(e)}")
                    raise
        except Exception as e:
            logger.error(f"Error during receive: {str(e)}")
            raise
            
        # If we get here, we either timed out or broke out of the loop
        if chunks:
            data = b''.join(chunks)
            logger.info(f"Returning data after receive completion ({len(data)} bytes)")
            try:
                json.loads(data.decode('utf-8'))
                return data
            except json.JSONDecodeError:
                raise Exception("Incomplete JSON response received")
        else:
            raise Exception("No data received")

    def send_command(self, command_type: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send a command to Ableton and return the response"""
        if not self.sock and not self.connect():
            raise ConnectionError("Not connected to Ableton")
        
        command = {
            "type": command_type,
            "params": params or {}
        }
        
        # Check if this is a state-modifying command
        is_modifying_command = command_type in [
            "create_midi_track", "create_audio_track", "set_track_name",
            "create_clip", "add_notes_to_clip", "set_clip_name",
            "set_tempo", "fire_clip", "stop_clip", "set_device_parameter",
            "start_playback", "stop_playback", "load_instrument_or_effect",
            "set_track_mixer", "set_track_mute", "set_track_solo",
            "duplicate_clip", "delete_clip", "delete_track",
            "set_device_param", "undo", "save_set", "set_scale_mode",
            "set_track_input_routing", "set_track_monitor", "fire_clip_slot",
            "start_synced_capture"
        ]
        
        try:
            logger.info(f"Sending command: {command_type} with params: {params}")
            
            # Send the command
            self.sock.sendall(json.dumps(command).encode('utf-8'))
            logger.info(f"Command sent, waiting for response...")
            
            # For state-modifying commands, add a small delay to give Ableton time to process
            if is_modifying_command:
                import time
                time.sleep(0.1)  # 100ms delay
            
            # Set timeout based on command type
            timeout = 15.0 if is_modifying_command else 10.0
            self.sock.settimeout(timeout)
            
            # Receive the response
            response_data = self.receive_full_response(self.sock)
            logger.info(f"Received {len(response_data)} bytes of data")
            
            # Parse the response
            response = json.loads(response_data.decode('utf-8'))
            logger.info(f"Response parsed, status: {response.get('status', 'unknown')}")
            
            if response.get("status") == "error":
                logger.error(f"Ableton error: {response.get('message')}")
                raise Exception(response.get("message", "Unknown error from Ableton"))
            
            # For state-modifying commands, add another small delay after receiving response
            if is_modifying_command:
                import time
                time.sleep(0.1)  # 100ms delay
            
            return response.get("result", {})
        except socket.timeout:
            logger.error("Socket timeout while waiting for response from Ableton")
            self.sock = None
            raise Exception("Timeout waiting for Ableton response")
        except (ConnectionError, BrokenPipeError, ConnectionResetError) as e:
            logger.error(f"Socket connection error: {str(e)}")
            self.sock = None
            raise Exception(f"Connection to Ableton lost: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response from Ableton: {str(e)}")
            if 'response_data' in locals() and response_data:
                logger.error(f"Raw response (first 200 bytes): {response_data[:200]}")
            self.sock = None
            raise Exception(f"Invalid response from Ableton: {str(e)}")
        except Exception as e:
            logger.error(f"Error communicating with Ableton: {str(e)}")
            self.sock = None
            raise Exception(f"Communication error with Ableton: {str(e)}")

@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[Dict[str, Any]]:
    """Manage server startup and shutdown lifecycle"""
    try:
        logger.info("AbletonMCP server starting up")
        
        try:
            ableton = get_ableton_connection()
            logger.info("Successfully connected to Ableton on startup")
        except Exception as e:
            logger.warning(f"Could not connect to Ableton on startup: {str(e)}")
            logger.warning("Make sure the Ableton Remote Script is running")
        
        yield {}
    finally:
        global _ableton_connection
        if _ableton_connection:
            logger.info("Disconnecting from Ableton on shutdown")
            _ableton_connection.disconnect()
            _ableton_connection = None
        logger.info("AbletonMCP server shut down")

# Create the MCP server with lifespan support
mcp = FastMCP(
    "AbletonMCP",
    lifespan=server_lifespan
)

# Global connection for resources
_ableton_connection = None

def get_ableton_connection():
    """Get or create a persistent Ableton connection"""
    global _ableton_connection
    
    if _ableton_connection is not None:
        try:
            # Test the connection with a simple ping
            # We'll try to send an empty message, which should fail if the connection is dead
            # but won't affect Ableton if it's alive
            _ableton_connection.sock.settimeout(1.0)
            _ableton_connection.sock.sendall(b'')
            return _ableton_connection
        except Exception as e:
            logger.warning(f"Existing connection is no longer valid: {str(e)}")
            try:
                _ableton_connection.disconnect()
            except:
                pass
            _ableton_connection = None
    
    # Connection doesn't exist or is invalid, create a new one
    if _ableton_connection is None:
        # Try to connect up to 3 times with a short delay between attempts
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                logger.info(f"Connecting to Ableton (attempt {attempt}/{max_attempts})...")
                _ableton_connection = AbletonConnection(
                    host=os.environ.get("ABLETON_HOST", "localhost"),
                    port=int(os.environ.get("ABLETON_PORT", "9877")),
                )
                if _ableton_connection.connect():
                    logger.info("Created new persistent connection to Ableton")
                    
                    # Validate connection with a simple command
                    try:
                        # Get session info as a test
                        _ableton_connection.send_command("get_session_info")
                        logger.info("Connection validated successfully")
                        return _ableton_connection
                    except Exception as e:
                        logger.error(f"Connection validation failed: {str(e)}")
                        _ableton_connection.disconnect()
                        _ableton_connection = None
                        # Continue to next attempt
                else:
                    _ableton_connection = None
            except Exception as e:
                logger.error(f"Connection attempt {attempt} failed: {str(e)}")
                if _ableton_connection:
                    _ableton_connection.disconnect()
                    _ableton_connection = None
            
            # Wait before trying again, but only if we have more attempts left
            if attempt < max_attempts:
                import time
                time.sleep(1.0)
        
        # If we get here, all connection attempts failed
        if _ableton_connection is None:
            logger.error("Failed to connect to Ableton after multiple attempts")
            raise Exception("Could not connect to Ableton. Make sure the Remote Script is running.")
    
    return _ableton_connection


# ---------------------------------------------------------------------------
# Music Theory Helpers
# ---------------------------------------------------------------------------

def _note_name_to_midi(note_name: str) -> int:
    """Convert 'C4' → 60, 'A#3' → 58, 'Bb3' → 58."""
    note_name = note_name.strip()
    if len(note_name) < 2:
        raise ValueError(f"Invalid note: {note_name!r}")
    if len(note_name) > 1 and note_name[1] in ("#", "b"):
        pitch_str, octave_str = note_name[:2], note_name[2:]
    else:
        pitch_str, octave_str = note_name[:1], note_name[1:]
    pitch_str = pitch_str.upper()
    enharmonics = {"CB": "B", "DB": "C#", "EB": "D#", "FB": "E", "GB": "F#",
                   "AB": "G#", "BB": "A#"}
    pitch_str = enharmonics.get(pitch_str, pitch_str)
    if pitch_str not in NOTE_NAMES:
        raise ValueError(f"Unknown pitch class: {pitch_str!r}. Use C, C#, D, D#, E, F, F#, G, G#, A, A#, B")
    octave = int(octave_str)
    return NOTE_NAMES.index(pitch_str) + (octave + 1) * 12


def _midi_to_note_name(midi: int) -> str:
    return f"{NOTE_NAMES[midi % 12]}{(midi // 12) - 1}"


def _get_scale_intervals(scale_name: str) -> List[int]:
    key = scale_name.lower().replace(" ", "_").replace("-", "_")
    if key not in SCALE_INTERVALS:
        raise ValueError(f"Unknown scale '{scale_name}'. Valid: {sorted(SCALE_INTERVALS)}")
    return SCALE_INTERVALS[key]


def _build_scale_pitches(root_midi: int, intervals: List[int], octave_range: int = 2) -> List[int]:
    """Return MIDI pitches for all scale notes across octave_range octaves, ascending."""
    pitches = []
    for oct_shift in range(octave_range):
        for iv in intervals:
            p = root_midi + oct_shift * 12 + iv
            if 0 <= p <= 127:
                pitches.append(p)
    return sorted(set(pitches))


def _resolve_scale_context(ableton, root_note: Optional[str], scale_name: Optional[str]) -> tuple:
    """Return (root_midi, intervals, root_note_str, scale_name_str).
    Falls back to Ableton's current scale when args are None."""
    if root_note is None or scale_name is None:
        try:
            live_scale = ableton.send_command("get_scale_mode")
            if root_note is None:
                # root_note from Live API is 0–11; build octave 3 note name
                live_root = live_scale.get("root_note", 0)
                root_note = f"{NOTE_NAMES[live_root % 12]}3"
            if scale_name is None:
                raw = live_scale.get("scale_name", "major")
                scale_name = raw.lower().replace(" ", "_")
        except Exception:
            root_note = root_note or "C3"
            scale_name = scale_name or "major"
    root_midi = _note_name_to_midi(root_note)
    intervals = _get_scale_intervals(scale_name)
    return root_midi, intervals, root_note, scale_name


def _apply_voicing(pitches: List[int], voicing: str) -> List[int]:
    """Revoice a close-position chord (ascending pitches)."""
    p = sorted(pitches)
    if voicing == "close":
        return p
    if voicing == "open":
        return sorted(p[i] + (12 if i % 2 == 0 and i > 0 else 0) for i, _ in enumerate(p))
    if voicing == "drop2" and len(p) >= 3:
        second_highest = sorted(p)[-2]
        return sorted([x if x != second_highest else second_highest - 12 for x in p])
    if voicing == "spread":
        return sorted(p[i] + i * 12 for i in range(len(p)))
    return p  # unknown voicing → close


# Core Tool endpoints

@mcp.tool()
def get_session_info(ctx: Context, include_track_names: bool = False) -> str:
    """
    Get information about the current Ableton session.

    Parameters:
    - include_track_names: When True, include a 'track_names' list with every track name in order (default: False).
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_session_info", {"include_track_names": include_track_names})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting session info from Ableton: {str(e)}")
        return f"Error getting session info: {str(e)}"

@mcp.tool()
def get_track_info(ctx: Context, track_index: int, include_clips: bool = False, include_devices: bool = False) -> str:
    """
    Get information about a specific track in Ableton.

    Parameters:
    - track_index:     The index of the track to get information about.
    - include_clips:   When True, include the 'clip_slots' array (default: False).
    - include_devices: When True, include the 'devices' array (default: False).
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_track_info", {
            "track_index": track_index,
            "include_clips": include_clips,
            "include_devices": include_devices,
        })
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting track info from Ableton: {str(e)}")
        return f"Error getting track info: {str(e)}"

@mcp.tool()
def get_all_tracks_info(ctx: Context) -> str:
    """
    Get a compact summary of all tracks in the session in one call.
    Returns index, name, type, mute, solo, volume, device_count, and clip_count for each track.
    Use get_track_info with include_clips/include_devices for full details on a specific track.
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_all_tracks_info")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting all tracks info from Ableton: {str(e)}")
        return f"Error getting all tracks info: {str(e)}"

@mcp.tool()
def create_midi_track(ctx: Context, index: int = -1) -> str:
    """
    Create a new MIDI track in the Ableton session.
    
    Parameters:
    - index: The index to insert the track at (-1 = end of list)
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("create_midi_track", {"index": index})
        return f"Created new MIDI track: {result.get('name', 'unknown')}"
    except Exception as e:
        logger.error(f"Error creating MIDI track: {str(e)}")
        return f"Error creating MIDI track: {str(e)}"


@mcp.tool()
def set_track_name(ctx: Context, track_index: int, name: str) -> str:
    """
    Set the name of a track.
    
    Parameters:
    - track_index: The index of the track to rename
    - name: The new name for the track
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_track_name", {"track_index": track_index, "name": name})
        return f"Renamed track to: {result.get('name', name)}"
    except Exception as e:
        logger.error(f"Error setting track name: {str(e)}")
        return f"Error setting track name: {str(e)}"

@mcp.tool()
def create_clip(ctx: Context, track_index: int, clip_index: int, length: float = 4.0) -> str:
    """
    Create a new MIDI clip in the specified track and clip slot.
    
    Parameters:
    - track_index: The index of the track to create the clip in
    - clip_index: The index of the clip slot to create the clip in
    - length: The length of the clip in beats (default: 4.0)
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("create_clip", {
            "track_index": track_index, 
            "clip_index": clip_index, 
            "length": length
        })
        return f"Created new clip at track {track_index}, slot {clip_index} with length {length} beats"
    except Exception as e:
        logger.error(f"Error creating clip: {str(e)}")
        return f"Error creating clip: {str(e)}"

@mcp.tool()
def add_notes_to_clip(
    ctx: Context, 
    track_index: int, 
    clip_index: int, 
    notes: List[Dict[str, Union[int, float, bool]]]
) -> str:
    """
    Add MIDI notes to a clip.
    
    Parameters:
    - track_index: The index of the track containing the clip
    - clip_index: The index of the clip slot containing the clip
    - notes: List of note dictionaries, each with pitch, start_time, duration, velocity, and mute
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("add_notes_to_clip", {
            "track_index": track_index,
            "clip_index": clip_index,
            "notes": notes
        })
        return f"Added {len(notes)} notes to clip at track {track_index}, slot {clip_index}"
    except Exception as e:
        logger.error(f"Error adding notes to clip: {str(e)}")
        return f"Error adding notes to clip: {str(e)}"

@mcp.tool()
def set_clip_name(ctx: Context, track_index: int, clip_index: int, name: str) -> str:
    """
    Set the name of a clip.
    
    Parameters:
    - track_index: The index of the track containing the clip
    - clip_index: The index of the clip slot containing the clip
    - name: The new name for the clip
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_clip_name", {
            "track_index": track_index,
            "clip_index": clip_index,
            "name": name
        })
        return f"Renamed clip at track {track_index}, slot {clip_index} to '{name}'"
    except Exception as e:
        logger.error(f"Error setting clip name: {str(e)}")
        return f"Error setting clip name: {str(e)}"

@mcp.tool()
def set_tempo(ctx: Context, tempo: float) -> str:
    """
    Set the tempo of the Ableton session.
    
    Parameters:
    - tempo: The new tempo in BPM
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_tempo", {"tempo": tempo})
        return f"Set tempo to {tempo} BPM"
    except Exception as e:
        logger.error(f"Error setting tempo: {str(e)}")
        return f"Error setting tempo: {str(e)}"


@mcp.tool()
def load_instrument_or_effect(ctx: Context, track_index: int, uri: str) -> str:
    """
    Load an instrument or effect onto a track using its URI.
    
    Parameters:
    - track_index: The index of the track to load the instrument on
    - uri: The URI of the instrument or effect to load (e.g., 'query:Synths#Instrument%20Rack:Bass:FileId_5116')
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("load_browser_item", {
            "track_index": track_index,
            "item_uri": uri
        })
        
        # Check if the instrument was loaded successfully
        if result.get("loaded", False):
            new_devices = result.get("new_devices", [])
            if new_devices:
                return f"Loaded instrument with URI '{uri}' on track {track_index}. New devices: {', '.join(new_devices)}"
            else:
                devices = result.get("devices_after", [])
                return f"Loaded instrument with URI '{uri}' on track {track_index}. Devices on track: {', '.join(devices)}"
        else:
            return f"Failed to load instrument with URI '{uri}'"
    except Exception as e:
        logger.error(f"Error loading instrument by URI: {str(e)}")
        return f"Error loading instrument by URI: {str(e)}"

@mcp.tool()
def fire_clip(ctx: Context, track_index: int, clip_index: int) -> str:
    """
    Start playing a clip.
    
    Parameters:
    - track_index: The index of the track containing the clip
    - clip_index: The index of the clip slot containing the clip
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("fire_clip", {
            "track_index": track_index,
            "clip_index": clip_index
        })
        return f"Started playing clip at track {track_index}, slot {clip_index}"
    except Exception as e:
        logger.error(f"Error firing clip: {str(e)}")
        return f"Error firing clip: {str(e)}"

@mcp.tool()
def stop_clip(ctx: Context, track_index: int, clip_index: int) -> str:
    """
    Stop playing a clip.
    
    Parameters:
    - track_index: The index of the track containing the clip
    - clip_index: The index of the clip slot containing the clip
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("stop_clip", {
            "track_index": track_index,
            "clip_index": clip_index
        })
        return f"Stopped clip at track {track_index}, slot {clip_index}"
    except Exception as e:
        logger.error(f"Error stopping clip: {str(e)}")
        return f"Error stopping clip: {str(e)}"

@mcp.tool()
def start_playback(ctx: Context) -> str:
    """Start playing the Ableton session."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("start_playback")
        return "Started playback"
    except Exception as e:
        logger.error(f"Error starting playback: {str(e)}")
        return f"Error starting playback: {str(e)}"

@mcp.tool()
def stop_playback(ctx: Context) -> str:
    """Stop playing the Ableton session."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("stop_playback")
        return "Stopped playback"
    except Exception as e:
        logger.error(f"Error stopping playback: {str(e)}")
        return f"Error stopping playback: {str(e)}"

@mcp.tool()
def get_browser_tree(ctx: Context, category_type: str = "all") -> str:
    """
    Get a hierarchical tree of browser categories from Ableton.
    
    Parameters:
    - category_type: Type of categories to get ('all', 'instruments', 'sounds', 'drums', 'audio_effects', 'midi_effects')
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_browser_tree", {
            "category_type": category_type
        })
        
        # Check if we got any categories
        if "available_categories" in result and len(result.get("categories", [])) == 0:
            available_cats = result.get("available_categories", [])
            return (f"No categories found for '{category_type}'. "
                   f"Available browser categories: {', '.join(available_cats)}")
        
        # Format the tree in a more readable way
        total_folders = result.get("total_folders", 0)
        formatted_output = f"Browser tree for '{category_type}' (showing {total_folders} folders):\n\n"
        
        def format_tree(item, indent=0):
            output = ""
            if item:
                prefix = "  " * indent
                name = item.get("name", "Unknown")
                path = item.get("path", "")
                has_more = item.get("has_more", False)
                
                # Add this item
                output += f"{prefix}• {name}"
                if path:
                    output += f" (path: {path})"
                if has_more:
                    output += " [...]"
                output += "\n"
                
                # Add children
                for child in item.get("children", []):
                    output += format_tree(child, indent + 1)
            return output
        
        # Format each category
        for category in result.get("categories", []):
            formatted_output += format_tree(category)
            formatted_output += "\n"
        
        return formatted_output
    except Exception as e:
        error_msg = str(e)
        if "Browser is not available" in error_msg:
            logger.error(f"Browser is not available in Ableton: {error_msg}")
            return f"Error: The Ableton browser is not available. Make sure Ableton Live is fully loaded and try again."
        elif "Could not access Live application" in error_msg:
            logger.error(f"Could not access Live application: {error_msg}")
            return f"Error: Could not access the Ableton Live application. Make sure Ableton Live is running and the Remote Script is loaded."
        else:
            logger.error(f"Error getting browser tree: {error_msg}")
            return f"Error getting browser tree: {error_msg}"

@mcp.tool()
def get_browser_items_at_path(ctx: Context, path: str, item_type: str = "all") -> str:
    """
    Get browser items at a specific path in Ableton's browser.

    Parameters:
    - path:      Path in the format "category/folder/subfolder"
                 where category is one of the available browser categories in Ableton.
    - item_type: Filter items by type. One of:
                   "all"      — return all items (default)
                   "folder"   — return only folders
                   "loadable" — return only loadable items
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_browser_items_at_path", {"path": path})

        if "error" in result and "available_categories" in result:
            error = result.get("error", "")
            available_cats = result.get("available_categories", [])
            return (f"Error: {error}\n"
                   f"Available browser categories: {', '.join(available_cats)}")

        if item_type != "all" and "items" in result:
            if item_type == "folder":
                result["items"] = [i for i in result["items"] if i.get("is_folder")]
            elif item_type == "loadable":
                result["items"] = [i for i in result["items"] if i.get("is_loadable")]
            else:
                return f"Error: invalid item_type '{item_type}'. Must be one of: all, folder, loadable"

        return json.dumps(result, indent=2)
    except Exception as e:
        error_msg = str(e)
        if "Browser is not available" in error_msg:
            logger.error(f"Browser is not available in Ableton: {error_msg}")
            return f"Error: The Ableton browser is not available. Make sure Ableton Live is fully loaded and try again."
        elif "Could not access Live application" in error_msg:
            logger.error(f"Could not access Live application: {error_msg}")
            return f"Error: Could not access the Ableton Live application. Make sure Ableton Live is running and the Remote Script is loaded."
        elif "Unknown or unavailable category" in error_msg:
            logger.error(f"Invalid browser category: {error_msg}")
            return f"Error: {error_msg}. Please check the available categories using get_browser_tree."
        elif "Path part" in error_msg and "not found" in error_msg:
            logger.error(f"Path not found: {error_msg}")
            return f"Error: {error_msg}. Please check the path and try again."
        else:
            logger.error(f"Error getting browser items at path: {error_msg}")
            return f"Error getting browser items at path: {error_msg}"

@mcp.tool()
def load_sound_by_path(ctx: Context, track_index: int, browser_path: str) -> str:
    """
    Load a sound directly onto a track using its browser_path (as returned by search_by_tags).
    Navigates to the item and loads it in one step — no intermediate URI lookup needed.

    Parameters:
    - track_index:   The index of the track to load onto
    - browser_path:  Full path as returned by search_by_tags
                     (e.g. "packs/Analog Brass & Winds/Pads/Deep Space")
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("load_browser_item_by_path", {
            "track_index": track_index,
            "browser_path": browser_path
        })
        if result.get("loaded"):
            return f"Loaded '{result.get('item_name')}' on track {track_index}"
        return f"Could not load item at '{browser_path}'"
    except Exception as e:
        logger.error(f"Error loading sound by path: {str(e)}")
        return f"Error loading sound by path: {str(e)}"


@mcp.tool()
def browse_user_library(ctx: Context, folder: str = "", max_items: int = 200) -> str:
    """
    Browse the User Library directly via the Live browser API and return loadable items
    with their browser_path. Use this instead of search_by_tags when looking for
    user-created or user-saved presets that may not appear in the SQLite tag database.

    Parameters:
    - folder:     Optional subfolder path to restrict the search, relative to User Library
                  (e.g. "Presets/Instruments/Operator"). Leave empty to browse everything.
    - max_items:  Maximum number of loadable items to return (default 200).

    Returns a list of items, each with name and browser_path.
    Pass browser_path directly to load_sound_by_path to load the item onto a track.
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("browse_user_library", {
            "folder": folder or None,
            "max_items": max_items,
        })
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error browsing user library: {str(e)}")
        return f"Error browsing user library: {str(e)}"


@mcp.tool()
def load_drum_kit(ctx: Context, track_index: int, rack_uri: str, kit_path: str) -> str:
    """
    Load a drum rack and then load a specific drum kit into it.
    
    Parameters:
    - track_index: The index of the track to load on
    - rack_uri: The URI of the drum rack to load (e.g., 'Drums/Drum Rack')
    - kit_path: Path to the drum kit inside the browser (e.g., 'drums/acoustic/kit1')
    """
    try:
        ableton = get_ableton_connection()
        
        # Step 1: Load the drum rack
        result = ableton.send_command("load_browser_item", {
            "track_index": track_index,
            "item_uri": rack_uri
        })
        
        if not result.get("loaded", False):
            return f"Failed to load drum rack with URI '{rack_uri}'"
        
        # Step 2: Get the drum kit items at the specified path
        kit_result = ableton.send_command("get_browser_items_at_path", {
            "path": kit_path
        })
        
        if "error" in kit_result:
            return f"Loaded drum rack but failed to find drum kit: {kit_result.get('error')}"
        
        # Step 3: Find a loadable drum kit
        kit_items = kit_result.get("items", [])
        loadable_kits = [item for item in kit_items if item.get("is_loadable", False)]
        
        if not loadable_kits:
            return f"Loaded drum rack but no loadable drum kits found at '{kit_path}'"
        
        # Step 4: Load the first loadable kit
        kit_uri = loadable_kits[0].get("uri")
        load_result = ableton.send_command("load_browser_item", {
            "track_index": track_index,
            "item_uri": kit_uri
        })
        
        return f"Loaded drum rack and kit '{loadable_kits[0].get('name')}' on track {track_index}"
    except Exception as e:
        logger.error(f"Error loading drum kit: {str(e)}")
        return f"Error loading drum kit: {str(e)}"

@mcp.tool()
def create_audio_track(ctx: Context, index: int = -1) -> str:
    """
    Create a new audio track in the Ableton session.

    Parameters:
    - index: The index to insert the track at (-1 = end of list)
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("create_audio_track", {"index": index})
        return f"Created new audio track: {result.get('name', 'unknown')}"
    except Exception as e:
        logger.error(f"Error creating audio track: {str(e)}")
        return f"Error creating audio track: {str(e)}"


@mcp.tool()
def set_track_mixer(ctx: Context, track_index: int, volume: float = None, panning: float = None) -> str:
    """
    Set the volume and/or panning of a track.

    Parameters:
    - track_index: The index of the track
    - volume: Volume level 0.0–1.0 (None = no change)
    - panning: Pan position -1.0 (left) to 1.0 (right) (None = no change)
    """
    try:
        ableton = get_ableton_connection()
        params = {"track_index": track_index}
        if volume is not None:
            params["volume"] = volume
        if panning is not None:
            params["panning"] = panning
        result = ableton.send_command("set_track_mixer", params)
        parts = []
        if "volume" in result:
            parts.append(f"volume={result['volume']:.3f}")
        if "panning" in result:
            parts.append(f"panning={result['panning']:.3f}")
        return f"Track {track_index} mixer updated: {', '.join(parts)}"
    except Exception as e:
        logger.error(f"Error setting track mixer: {str(e)}")
        return f"Error setting track mixer: {str(e)}"


@mcp.tool()
def set_track_mute(ctx: Context, track_index: int, mute: bool) -> str:
    """
    Mute or unmute a track.

    Parameters:
    - track_index: The index of the track
    - mute: True to mute, False to unmute
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_track_mute", {"track_index": track_index, "mute": mute})
        state = "muted" if result.get("mute") else "unmuted"
        return f"Track {track_index} {state}"
    except Exception as e:
        logger.error(f"Error setting track mute: {str(e)}")
        return f"Error setting track mute: {str(e)}"


@mcp.tool()
def set_track_solo(ctx: Context, track_index: int, solo: bool) -> str:
    """
    Solo or unsolo a track.

    Parameters:
    - track_index: The index of the track
    - solo: True to solo, False to unsolo
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_track_solo", {"track_index": track_index, "solo": solo})
        state = "soloed" if result.get("solo") else "unsoloed"
        return f"Track {track_index} {state}"
    except Exception as e:
        logger.error(f"Error setting track solo: {str(e)}")
        return f"Error setting track solo: {str(e)}"


@mcp.tool()
def set_track_color(ctx: Context, track_index: int, color: str) -> str:
    """
    Set the color of a track.

    Parameters:
    - track_index: The index of the track.
    - color:       Hex color string in '#RRGGBB' format, e.g. '#FF6600' for orange.

    Common production color conventions:
    - Drums/percussion: #FF0000 (red) or #FF6600 (orange)
    - Bass: #8800FF (purple) or #0000FF (blue)
    - Chords/harmony: #00AA00 (green) or #00AAFF (cyan)
    - Melody/lead: #FFFF00 (yellow) or #FF00FF (pink)
    - FX/atmosphere: #888888 (grey) or #00FFFF (cyan)
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_track_color", {"track_index": track_index, "color": color})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error setting track color: {str(e)}")
        return f"Error setting track color: {str(e)}"


@mcp.tool()
def delete_track(ctx: Context, track_index: int) -> str:
    """
    Delete a track from the session.

    Parameters:
    - track_index: The index of the track to delete
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("delete_track", {"track_index": track_index})
        return f"Deleted track at index {track_index}"
    except Exception as e:
        logger.error(f"Error deleting track: {str(e)}")
        return f"Error deleting track: {str(e)}"


@mcp.tool()
def duplicate_clip(ctx: Context, track_index: int, clip_index: int, target_clip_index: int, target_track_index: int = None) -> str:
    """
    Duplicate a clip to another clip slot.

    Parameters:
    - track_index: Source track index
    - clip_index: Source clip slot index
    - target_clip_index: Destination clip slot index
    - target_track_index: Destination track index (defaults to same track)
    """
    try:
        ableton = get_ableton_connection()
        params = {
            "track_index": track_index,
            "clip_index": clip_index,
            "target_clip_index": target_clip_index,
            "target_track_index": target_track_index if target_track_index is not None else track_index
        }
        result = ableton.send_command("duplicate_clip", params)
        dest_track = target_track_index if target_track_index is not None else track_index
        return f"Duplicated clip from track {track_index}, slot {clip_index} to track {dest_track}, slot {target_clip_index}"
    except Exception as e:
        logger.error(f"Error duplicating clip: {str(e)}")
        return f"Error duplicating clip: {str(e)}"


@mcp.tool()
def delete_clip(ctx: Context, track_index: int, clip_index: int) -> str:
    """
    Delete a clip from a clip slot.

    Parameters:
    - track_index: The index of the track containing the clip
    - clip_index: The index of the clip slot
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("delete_clip", {"track_index": track_index, "clip_index": clip_index})
        return f"Deleted clip at track {track_index}, slot {clip_index}"
    except Exception as e:
        logger.error(f"Error deleting clip: {str(e)}")
        return f"Error deleting clip: {str(e)}"


@mcp.tool()
def get_clip_notes(ctx: Context, track_index: int, clip_index: int) -> str:
    """
    Get all MIDI notes from a clip.

    Parameters:
    - track_index: The index of the track containing the clip
    - clip_index: The index of the clip slot
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_clip_notes", {"track_index": track_index, "clip_index": clip_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting clip notes: {str(e)}")
        return f"Error getting clip notes: {str(e)}"


@mcp.tool()
def get_device_params(
    ctx: Context,
    track_index: int = 0,
    device_index: int = 0,
    chain_path: Optional[list] = None,
    return_track_index: Optional[int] = None,
    is_master: bool = False,
) -> str:
    """
    Get parameters of any device — regular tracks, return tracks, or the master track —
    including devices nested at any depth inside racks and drum racks.

    Progressive disclosure: call with only track/device indices to get that device's
    own parameters plus a 'contents' map of its nested devices. Each nested device entry
    includes a ready-to-use 'chain_path' — pass it unchanged in the next call to drill in.

    chain_path format — a list of steps, each a dict:
      {"chain_index": N, "device_index": N}             — for Instrument/Effect Racks
      {"pad_note": N, "chain_index": N, "device_index": N} — for Drum Rack pads

    Track selection (mutually exclusive, is_master takes priority):
    - track_index: regular track (default)
    - return_track_index: return track A=0, B=1, …
    - is_master: True for the master track
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_device_params", {
            "track_index": track_index,
            "device_index": device_index,
            "chain_path": chain_path,
            "return_track_index": return_track_index,
            "is_master": is_master,
        })
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting device params: {str(e)}")
        return f"Error getting device params: {str(e)}"


@mcp.tool()
def get_drum_rack_pads(
    ctx: Context,
    track_index: int = 0,
    device_index: int = 0,
    return_track_index: Optional[int] = None,
    is_master: bool = False,
) -> str:
    """
    Get drum pad assignments for a Drum Rack — note number, pad name, mute/solo state,
    and the chain names of loaded pads. Only loaded pads (those with chains) are returned.

    Track selection (mutually exclusive, is_master takes priority):
    - track_index: regular track (default)
    - return_track_index: return track A=0, B=1, …
    - is_master: True for the master track
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_drum_rack_pads", {
            "track_index": track_index,
            "device_index": device_index,
            "return_track_index": return_track_index,
            "is_master": is_master,
        })
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting drum rack pads: {str(e)}")
        return f"Error getting drum rack pads: {str(e)}"


@mcp.tool()
def set_device_param(
    ctx: Context,
    track_index: int = 0,
    device_index: int = 0,
    param_index: int = 0,
    value: float = 0.0,
    chain_path: Optional[list] = None,
    return_track_index: Optional[int] = None,
    is_master: bool = False,
) -> str:
    """
    Set a parameter on any device. Accepts the same chain_path and track-selection
    arguments as get_device_params — copy the chain_path from that response unchanged.

    Track selection (mutually exclusive, is_master takes priority):
    - track_index: regular track (default)
    - return_track_index: return track A=0, B=1, …
    - is_master: True for the master track
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_device_param", {
            "track_index": track_index,
            "device_index": device_index,
            "param_index": param_index,
            "value": value,
            "chain_path": chain_path,
            "return_track_index": return_track_index,
            "is_master": is_master,
        })
        return f"Set '{result.get('param_name', f'param {param_index}')}' to {result.get('value', value):.4f}"
    except Exception as e:
        logger.error(f"Error setting device param: {str(e)}")
        return f"Error setting device param: {str(e)}"


@mcp.tool()
def undo(ctx: Context) -> str:
    """Undo the last action in Ableton."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("undo")
        return "Undo successful"
    except Exception as e:
        logger.error(f"Error performing undo: {str(e)}")
        return f"Error performing undo: {str(e)}"


@mcp.tool()
def get_playback_position(ctx: Context) -> str:
    """Get the current playback position in beats."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_playback_position")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting playback position: {str(e)}")
        return f"Error getting playback position: {str(e)}"


@mcp.tool()
def get_scale_mode(ctx: Context) -> str:
    """Get the current scale mode settings (root note, scale name, and in-key state)."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_scale_mode")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting scale mode: {str(e)}")
        return f"Error getting scale mode: {str(e)}"


@mcp.tool()
def set_scale_mode(
    ctx: Context,
    root_note: int = None,
    scale_name: str = None,
    in_key: bool = None
) -> str:
    """
    Set the scale mode for the Ableton session.

    Parameters:
    - root_note: Root note as MIDI semitone 0–11 (0=C, 1=C#, 2=D, 3=D#, 4=E, 5=F,
                 6=F#, 7=G, 8=G#, 9=A, 10=A#, 11=B). None = no change.
    - scale_name: Name of the scale, e.g. 'Major', 'Minor', 'Dorian', 'Phrygian',
                  'Lydian', 'Mixolydian', 'Locrian', 'Whole Tone', 'Minor Pentatonic',
                  'Major Pentatonic', 'Harmonic Minor', 'Melodic Minor'. None = no change.
    - in_key: True to enable in-key highlighting, False to disable. None = no change.
    """
    try:
        ableton = get_ableton_connection()
        params = {}
        if root_note is not None:
            params["root_note"] = root_note
        if scale_name is not None:
            params["scale_name"] = scale_name
        if in_key is not None:
            params["in_key"] = in_key
        result = ableton.send_command("set_scale_mode", params)
        parts = []
        if "root_note_name" in result:
            parts.append(f"root={result['root_note_name']}")
        if "scale_name" in result:
            parts.append(f"scale={result['scale_name']}")
        if "in_key" in result:
            parts.append(f"in_key={result['in_key']}")
        return f"Scale mode updated: {', '.join(parts)}"
    except Exception as e:
        logger.error(f"Error setting scale mode: {str(e)}")
        return f"Error setting scale mode: {str(e)}"


# ---------------------------------------------------------------------------
# Tag-based browser search (reads Ableton's SQLite DB directly)
# ---------------------------------------------------------------------------

_KEYW_TYPE = 1801812343  # FourCC 'keyw' — tag nodes in the files table


def _get_ableton_db() -> str:
    pattern = os.path.expanduser(
        "~/Library/Application Support/Ableton/Live Database/Live-files-*.db"
    )
    dbs = sorted(glob.glob(pattern), reverse=True)
    if not dbs:
        raise FileNotFoundError(
            "No Ableton Live database found. Make sure Ableton has been opened at least once."
        )
    return dbs[0]


def _category_filter(category: str) -> tuple:
    """Return (sql_fragment, params) to restrict by browser category."""
    c = category.lower().replace(" ", "_").replace("-", "_")
    ADG = 1633969965   # .adg rack
    ADV = 1633973805   # .adv preset
    AMP = 1634562093   # .amp audio-effect preset
    ALC = 1634493229   # .alc clip / M4L device
    ALS = 1634497325   # .als live set
    AGR = 1634169389   # .agr groove
    SCL = 1935895597   # .scl tuning
    WAV = 2002875949
    AIF = 1634297446
    FLC = 1718378851
    MP3 = 1836069677
    REX = 1919252525
    PLG = 1886156135   # AU/VST plugin
    VSP = 1987277936   # VST preset
    VSB = 1987277922
    VS3 = 1987277875

    if c in ("all", ""):
        return "", []
    if c in ("sounds", "instruments"):
        return ("(f.file_type = ? OR (f.file_type = ? AND f.device_type = 1))",
                [ADV, ADG])
    if c == "drums":
        return ("(f.file_type = ? AND f.device_id LIKE ?)",
                [ADG, "%DrumGroup%"])
    if c in ("audio_effects", "audio_effect"):
        return ("((f.file_type = ? AND f.device_type = 2) OR f.file_type = ?)",
                [ADG, AMP])
    if c in ("midi_effects", "midi_effect"):
        return ("(f.file_type = ? AND f.device_type = 4)",
                [ADG])
    if c in ("max_for_live", "m4l"):
        return ("(f.file_type = ?)", [ALC])
    if c in ("plugins", "plug_ins"):
        return ("(f.file_type IN (?,?,?,?))", [PLG, VSP, VSB, VS3])
    if c == "clips":
        return ("(f.file_type IN (?,?))", [ALC, ALS])
    if c == "samples":
        return ("(f.file_type IN (?,?,?,?,?))", [WAV, AIF, FLC, MP3, REX])
    if c == "grooves":
        return ("(f.file_type = ?)", [AGR])
    if c == "tunings":
        return ("(f.file_type = ?)", [SCL])
    raise ValueError(
        f"Unknown category '{category}'. Valid values: all, sounds, instruments, "
        "drums, audio_effects, midi_effects, max_for_live, plugins, clips, samples, grooves, tunings"
    )


def _human_type(file_type: int, device_id: str) -> str:
    if file_type == 1633973805: return "preset"
    if file_type == 1633969965:
        if device_id and "DrumGroup"  in device_id: return "drum_rack"
        if device_id and "audiofx"   in device_id: return "audio_effect_rack"
        if device_id and "midifx"    in device_id: return "midi_effect_rack"
        return "instrument_rack"
    if file_type in (2002875949, 1634297446, 1718378851, 1836069677, 1919252525):
        return "sample"
    if file_type == 1634493229: return "clip_or_m4l"
    if file_type == 1634497325: return "live_set"
    if file_type == 1634169389: return "groove"
    if file_type == 1935895597: return "tuning"
    if file_type in (1987277936, 1886156135, 1987277922, 1987277875): return "plugin"
    return "unknown"


def _reconstruct_browser_path(conn, file_id: int) -> str:
    """Build a browser-navigable path string from the ancestor chain."""
    place_row = conn.execute("""
        SELECT p.file_id, p.name
        FROM places p
        JOIN files f ON f.place_id = p.file_id
        WHERE f.file_id = ?
    """, (file_id,)).fetchone()

    ancestors = conn.execute("""
        SELECT f.file_id, f.name
        FROM files f
        JOIN ancestors a ON f.file_id = a.ancestor_id
        WHERE a.file_id = ?
        ORDER BY a.ancestor_id
    """, (file_id,)).fetchall()

    file_name = conn.execute(
        "SELECT name FROM files WHERE file_id = ?", (file_id,)
    ).fetchone()[0]

    if not place_row:
        return file_name

    place_file_id, place_name = place_row
    place_idx = next(
        (i for i, (aid, _) in enumerate(ancestors) if aid == place_file_id), None
    )
    relative = [name for _, name in ancestors[place_idx + 1:]] if place_idx is not None else []
    root = "user_library" if place_name == "User Library" else f"packs/{place_name}"
    return "/".join([root] + relative + [file_name])


@mcp.tool()
def get_browser_tags(ctx: Context, category: str = "all", prefix: str = "") -> str:
    """
    Return tag names available in Ableton's browser, read directly from
    Ableton's local database (Ableton does not need to be running).

    Parameters:
    - category: Filter to tags used in a specific browser section.
                One of: all (default), sounds, instruments, drums, audio_effects,
                midi_effects, max_for_live, plugins, clips, samples, grooves, tunings
    - prefix:   If non-empty, only return tags whose name starts with this string
                (case-insensitive). Default: "" (no filter).
    """
    try:
        db_path = _get_ableton_db()
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)

        cat_sql, cat_params = _category_filter(category)

        if cat_sql:
            rows = conn.execute(f"""
                SELECT DISTINCT tag.name
                FROM files tag
                JOIN keywords k  ON k.keyw_id  = tag.file_id
                JOIN files f     ON k.file_id   = f.file_id
                WHERE tag.file_type = ?
                  AND {cat_sql}
                ORDER BY tag.name
            """, [_KEYW_TYPE] + cat_params).fetchall()
        else:
            rows = conn.execute(
                "SELECT name FROM files WHERE file_type = ? ORDER BY name",
                (_KEYW_TYPE,)
            ).fetchall()

        conn.close()
        tags = [r[0] for r in rows]
        if prefix:
            prefix_lower = prefix.lower()
            tags = [t for t in tags if t.lower().startswith(prefix_lower)]
        return json.dumps({"category": category, "count": len(tags), "tags": tags}, indent=2)

    except Exception as e:
        logger.error(f"Error getting browser tags: {e}")
        return f"Error getting browser tags: {e}"


@mcp.tool()
def search_by_tags(
    ctx: Context,
    tags: List[str],
    category: str = "all",
    limit: int = 50,
    offset: int = 0,
) -> str:
    """
    Search Ableton's browser for content matching ALL supplied tags.
    Reads directly from Ableton's local database — Ableton does not need to be running.

    Parameters:
    - tags:     One or more tag names (AND logic — results must carry every tag).
                Use get_browser_tags to discover available tags.
    - category: Restrict results to a browser section.
                One of: all (default), sounds, instruments, drums, audio_effects,
                midi_effects, max_for_live, plugins, clips, samples, grooves, tunings
    - limit:    Maximum number of results to return (default 50).
    - offset:   Number of results to skip before returning (default 0). Use with limit for pagination.

    Each result includes name, type, source, and a browser_path you can pass
    to load_sound_by_path to load it directly onto a track.
    """
    try:
        if not tags:
            return "Error: provide at least one tag"

        db_path = _get_ableton_db()
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)

        cat_sql, cat_params = _category_filter(category)
        n = len(tags)
        tag_placeholders = ",".join("?" * n)

        cat_clause = f"AND {cat_sql}" if cat_sql else ""

        rows = conn.execute(f"""
            SELECT f.file_id, f.name, f.file_type, f.device_id,
                   p.name AS source
            FROM files f
            JOIN keywords k   ON k.file_id  = f.file_id
            JOIN files tag    ON tag.file_id = k.keyw_id
            LEFT JOIN places pl ON f.place_id = pl.file_id
            LEFT JOIN files p   ON pl.file_id = p.file_id
            WHERE tag.name IN ({tag_placeholders})
              AND tag.file_type = ?
              {cat_clause}
            GROUP BY f.file_id
            HAVING COUNT(DISTINCT tag.name) = ?
            LIMIT ? OFFSET ?
        """, tags + [_KEYW_TYPE] + cat_params + [n, limit, offset]).fetchall()

        results = []
        for file_id, name, file_type, device_id, source in rows:
            browser_path = _reconstruct_browser_path(conn, file_id)

            results.append({
                "name":         name,
                "type":         _human_type(file_type, device_id or ""),
                "source":       source or "unknown",
                "browser_path": browser_path,
            })

        conn.close()
        return json.dumps({
            "query_tags": tags,
            "category":   category,
            "count":      len(results),
            "offset":     offset,
            "hint":       "Pass browser_path directly to load_sound_by_path to load onto a track",
            "results":    results,
        }, indent=2)

    except Exception as e:
        logger.error(f"Error searching by tags: {e}")
        return f"Error searching by tags: {e}"


@mcp.tool()
def create_track_with_clip(
    ctx: Context,
    track_name: str,
    notes: List[Dict],
    clip_length: float = 4.0,
    clip_index: int = 0,
    clip_name: Optional[str] = None,
    track_index: int = -1,
) -> str:
    """
    Create a named MIDI track, create a clip, and add notes in one call.
    Replaces the common 4-step workflow: create_midi_track → set_track_name → create_clip → add_notes_to_clip.

    Parameters:
    - track_name:   Name for the new track.
    - notes:        List of note objects ({pitch, start_time, duration, velocity, mute}).
    - clip_length:  Length of the clip in beats (default 4.0).
    - clip_index:   Clip slot index to create the clip in (default 0).
    - clip_name:    Optional name for the clip. Defaults to track_name if not provided.
    - track_index:  Where to insert the track (-1 = end, default).
    """
    try:
        ableton = get_ableton_connection()

        track_result = ableton.send_command("create_midi_track", {"index": track_index})
        new_track_index = track_result.get("index", track_index)

        ableton.send_command("set_track_name", {"track_index": new_track_index, "name": track_name})
        ableton.send_command("create_clip", {"track_index": new_track_index, "clip_index": clip_index, "length": clip_length})
        ableton.send_command("add_notes_to_clip", {"track_index": new_track_index, "clip_index": clip_index, "notes": notes})

        if clip_name or track_name:
            ableton.send_command("set_clip_name", {
                "track_index": new_track_index,
                "clip_index": clip_index,
                "name": clip_name or track_name,
            })

        return json.dumps({
            "track_index": new_track_index,
            "track_name": track_name,
            "clip_index": clip_index,
            "clip_length": clip_length,
            "note_count": len(notes),
        }, indent=2)
    except Exception as e:
        logger.error(f"Error creating track with clip: {str(e)}")
        return f"Error creating track with clip: {str(e)}"


@mcp.tool()
def search_and_load_sound(
    ctx: Context,
    track_index: int,
    tags: List[str],
    category: str = "all",
    result_index: int = 0,
) -> str:
    """
    Search for a sound by tags and load it onto a track in one call.
    Replaces the common 2-step workflow: search_by_tags → load_sound_by_path.

    Parameters:
    - track_index:   The index of the track to load onto.
    - tags:          One or more tag names (AND logic — item must have ALL tags).
    - category:      Restrict search to a browser section (default: "all").
    - result_index:  Which result to load (0 = first match, default).
    """
    try:
        ableton = get_ableton_connection()

        db_path = _get_ableton_db()
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)

        cat_sql, cat_params = _category_filter(category)
        n = len(tags)
        tag_placeholders = ",".join("?" * n)
        cat_clause = f"AND {cat_sql}" if cat_sql else ""

        rows = conn.execute(f"""
            SELECT f.file_id, f.name
            FROM files f
            JOIN keywords k   ON k.file_id  = f.file_id
            JOIN files tag    ON tag.file_id = k.keyw_id
            WHERE tag.name IN ({tag_placeholders})
              AND tag.file_type = ?
              {cat_clause}
            GROUP BY f.file_id
            HAVING COUNT(DISTINCT tag.name) = ?
            LIMIT ? OFFSET ?
        """, tags + [_KEYW_TYPE] + cat_params + [n, 1, result_index]).fetchall()

        if not rows:
            conn.close()
            return f"No results found for tags {tags} (category: {category}, result_index: {result_index})"

        file_id, name = rows[0]
        browser_path = _reconstruct_browser_path(conn, file_id)
        conn.close()

        result = ableton.send_command("load_browser_item_by_path", {
            "track_index": track_index,
            "browser_path": browser_path,
        })

        if result.get("loaded"):
            return json.dumps({
                "loaded": result.get("item_name", name),
                "track_index": track_index,
                "browser_path": browser_path,
            }, indent=2)
        return f"Found '{name}' but could not load it from '{browser_path}'"
    except Exception as e:
        logger.error(f"Error in search_and_load_sound: {str(e)}")
        return f"Error in search_and_load_sound: {str(e)}"


# ---------------------------------------------------------------------------
# Event Subscription Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def subscribe_to_events(ctx: Context, event_types: List[str]) -> str:
    """
    Subscribe to live Ableton state-change events. Poll get_pending_events to receive them.

    Supported event types: tempo, is_playing, current_song_time, track_count.

    Parameters:
    - event_types: List of event type strings to subscribe to.

    Returns which event types were successfully subscribed.
    Use get_pending_events periodically to drain the event queue.
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("subscribe_to_events", {"event_types": event_types})
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error subscribing to events: {e}"


@mcp.tool()
def get_pending_events(ctx: Context) -> str:
    """
    Drain and return all queued Ableton events since the last call.

    Call this periodically while Ableton is playing to receive state changes
    (tempo edits, play/stop, song position updates, track additions/removals).
    Each call clears the queue — events are not repeated on subsequent calls.

    Returns {"events": [...], "count": int}. Each event has "type", "timestamp", and "data".
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_pending_events")
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error getting pending events: {e}"


@mcp.tool()
def unsubscribe_from_events(ctx: Context, event_types: Optional[List[str]] = None) -> str:
    """
    Unsubscribe from Ableton events and stop receiving them.

    Parameters:
    - event_types: List of event type strings to unsubscribe from.
                   Pass null / omit to unsubscribe from all active subscriptions.

    Returns the list of event types that were unsubscribed.
    """
    try:
        ableton = get_ableton_connection()
        params = {"event_types": event_types} if event_types is not None else {}
        result = ableton.send_command("unsubscribe_from_events", params)
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error unsubscribing from events: {e}"


# ---------------------------------------------------------------------------
# Music Theory Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def generate_chord(
    ctx: Context,
    root_note: Optional[str] = None,
    chord_type: str = "maj",
    voicing: str = "close",
    octave_shift: int = 0,
    scale_name: Optional[str] = None,
    velocity: int = 90,
    duration: float = 1.0,
    start_time: float = 0.0,
) -> str:
    """
    Generate a chord as a list of MIDI note dicts ready to pass to add_notes_to_clip or create_track_with_clip.

    When root_note or scale_name is not supplied, the tool reads Ableton's current scale setting.

    Parameters:
    - root_note:    Root note string like "C4", "F#3", "Bb2". Default: Ableton's current scale root.
    - chord_type:   Chord quality. One of: maj, min, dim, aug, maj7, min7, dom7, dim7, half_dim7,
                    sus2, sus4, add9, maj9, min9. Default: "maj".
    - voicing:      Note layout. "close" (stacked), "open" (wide), "drop2", "spread". Default: "close".
    - octave_shift: Transpose the whole chord up/down by N octaves. Default: 0.
    - scale_name:   Scale context for display/validation. Default: Ableton's current scale.
    - velocity:     MIDI velocity 1–127. Default: 90.
    - duration:     Note duration in beats. Default: 1.0.
    - start_time:   Clip position in beats. Default: 0.0.

    Returns a dict with "notes" (pass to add_notes_to_clip), "chord_name", and "root".
    """
    try:
        ableton = get_ableton_connection()
        root_midi, intervals, root_str, scale_str = _resolve_scale_context(ableton, root_note, scale_name)

        if chord_type not in CHORD_INTERVALS:
            return f"Error: unknown chord_type '{chord_type}'. Valid: {sorted(CHORD_INTERVALS)}"

        raw_pitches = [root_midi + iv + octave_shift * 12 for iv in CHORD_INTERVALS[chord_type]]
        raw_pitches = [max(0, min(127, p)) for p in raw_pitches]
        voiced = _apply_voicing(raw_pitches, voicing)

        notes = [{"pitch": p, "start_time": start_time, "duration": duration,
                  "velocity": velocity, "mute": False} for p in voiced]

        return json.dumps({
            "notes": notes,
            "chord_name": f"{NOTE_NAMES[root_midi % 12]}{chord_type}",
            "root": root_str,
            "voicing": voicing,
            "hint": "Pass 'notes' to add_notes_to_clip or create_track_with_clip",
        }, indent=2)
    except Exception as e:
        return f"Error generating chord: {e}"


@mcp.tool()
def generate_chord_progression(
    ctx: Context,
    degrees: List[int],
    root_note: Optional[str] = None,
    scale_name: Optional[str] = None,
    bars_per_chord: float = 1.0,
    voicing: str = "close",
    velocity: int = 90,
    octave: int = 4,
) -> str:
    """
    Generate a diatonic chord progression as MIDI notes, ready for create_track_with_clip.

    Degrees are scale degrees 1–7. Chord qualities are automatically derived from the scale
    (e.g. degree 5 in major = dominant/maj, degree 2 in minor = diminished).

    Parameters:
    - degrees:        List of scale degrees, e.g. [1, 4, 5, 1] or [1, 6, 4, 5].
    - root_note:      Root note string like "C4". Default: Ableton's current scale root.
    - scale_name:     Scale name. Default: Ableton's current scale.
    - bars_per_chord: Duration of each chord in bars (beats when 4/4). Default: 1.0 bar = 4 beats.
    - voicing:        Note layout. "close" | "open" | "drop2" | "spread". Default: "close".
    - velocity:       MIDI velocity 1–127. Default: 90.
    - octave:         Root octave for the chords. Default: 4.

    Returns "notes" (all chords combined), "clip_length", "chord_names", and scale context.
    """
    try:
        ableton = get_ableton_connection()
        # Use given octave for the root, override what _resolve_scale_context returns
        root_for_resolve = f"{root_note}" if root_note else None
        _, intervals, root_str, scale_str = _resolve_scale_context(ableton, root_for_resolve, scale_name)

        # Re-derive root at the requested octave
        root_pitch_class = NOTE_NAMES.index(root_str[:-1]) if root_str[-1].isdigit() else \
                           NOTE_NAMES.index(root_str[:-2] if root_str[-2] in ("#", "b") else root_str[:-1])
        root_midi = root_pitch_class + (octave + 1) * 12

        beats_per_chord = bars_per_chord * 4.0
        all_notes = []
        chord_names = []
        quality_map = DIATONIC_QUALITY.get(scale_str, DIATONIC_QUALITY["major"])

        for i, degree in enumerate(degrees):
            if degree < 1 or degree > len(intervals):
                return f"Error: degree {degree} out of range for scale '{scale_str}' (1–{len(intervals)})"
            chord_root = root_midi + intervals[degree - 1]
            quality = quality_map.get(degree, "maj")
            raw_pitches = [chord_root + iv for iv in CHORD_INTERVALS[quality]]
            raw_pitches = [max(0, min(127, p)) for p in raw_pitches]
            voiced = _apply_voicing(raw_pitches, voicing)
            t_start = i * beats_per_chord
            for p in voiced:
                all_notes.append({"pitch": p, "start_time": t_start,
                                  "duration": beats_per_chord * 0.9,
                                  "velocity": velocity, "mute": False})
            chord_names.append(f"{NOTE_NAMES[chord_root % 12]}{quality}")

        clip_length = len(degrees) * beats_per_chord
        return json.dumps({
            "notes": all_notes,
            "clip_length": clip_length,
            "chord_names": chord_names,
            "root": root_str,
            "scale": scale_str,
            "hint": "Pass 'notes' and 'clip_length' to create_track_with_clip",
        }, indent=2)
    except Exception as e:
        return f"Error generating chord progression: {e}"


@mcp.tool()
def generate_bass_pattern(
    ctx: Context,
    root_note: Optional[str] = None,
    scale_name: Optional[str] = None,
    style: str = "deep_house",
    bars: int = 1,
    octave: int = 2,
) -> str:
    """
    Generate a genre-authentic bass pattern as MIDI notes, ready for create_track_with_clip.

    Each style encodes expert-crafted rhythm, pitch movement, and velocity curves. The root
    note anchors all pitches; pitch offsets in the pattern are semitone movements from the root.

    Parameters:
    - root_note:  Root note string like "A2". Default: Ableton's current scale root (at octave 2).
    - scale_name: Scale for validation/context. Default: Ableton's current scale.
    - style:      Genre pattern. One of: deep_house, techno, hip_hop, funk, reggae,
                  drum_and_bass, afrobeats, pop, latin, jazz. Default: "deep_house".
    - bars:       Number of bars to generate (pattern repeats). Default: 1.
    - octave:     Root octave. Default: 2 (sub-bass register).

    Returns "notes", "clip_length", "style", and scale context.
    """
    try:
        if style not in BASS_RHYTHM_PATTERNS:
            return f"Error: unknown style '{style}'. Valid: {sorted(BASS_RHYTHM_PATTERNS)}"

        ableton = get_ableton_connection()
        _, intervals, root_str, scale_str = _resolve_scale_context(ableton, root_note, scale_name)

        # Build root at target octave
        root_pc = _note_name_to_midi(root_str) % 12
        root_midi = root_pc + (octave + 1) * 12

        # Build scale pitch set for snapping
        scale_pitches = set()
        for oct_shift in range(-1, 3):
            for iv in intervals:
                p = root_midi + oct_shift * 12 + iv
                if 0 <= p <= 127:
                    scale_pitches.add(p)

        pattern = BASS_RHYTHM_PATTERNS[style]
        beats_per_bar = 4.0
        notes = []
        for bar in range(bars):
            bar_offset = bar * beats_per_bar
            for (beat_off, semitone_off, dur, vel) in pattern:
                raw_pitch = root_midi + semitone_off
                # Snap to nearest scale pitch
                if scale_pitches:
                    raw_pitch = min(scale_pitches, key=lambda p: abs(p - raw_pitch))
                raw_pitch = max(0, min(127, raw_pitch))
                notes.append({
                    "pitch": raw_pitch,
                    "start_time": bar_offset + beat_off,
                    "duration": dur,
                    "velocity": min(127, max(1, vel)),
                    "mute": False,
                })

        clip_length = bars * beats_per_bar
        return json.dumps({
            "notes": notes,
            "clip_length": clip_length,
            "style": style,
            "root": root_str,
            "scale": scale_str,
            "hint": "Pass 'notes' and 'clip_length' to create_track_with_clip",
        }, indent=2)
    except Exception as e:
        return f"Error generating bass pattern: {e}"


@mcp.tool()
def generate_melody(
    ctx: Context,
    root_note: Optional[str] = None,
    scale_name: Optional[str] = None,
    bars: int = 2,
    density: str = "medium",
    contour: str = "arch",
    octave_range: int = 1,
    start_degree: int = 1,
    velocity_min: int = 70,
    velocity_max: int = 100,
) -> str:
    """
    Generate a melodic phrase using a musically-aware algorithm.

    Motion is step-biased (60% step, 25% leap, 15% rest). Contour shapes the pitch tendency
    across the phrase. The result sounds intentional, not random.

    Parameters:
    - root_note:    Root note string like "D4". Default: Ableton's current scale root.
    - scale_name:   Scale name. Default: Ableton's current scale.
    - bars:         Length in bars. Default: 2.
    - density:      Note density. "sparse" (8th grid, 50% fill), "medium" (8th grid, 70%),
                    "dense" (16th grid, 80%). Default: "medium".
    - contour:      Melodic shape. "arch" (rise then fall), "ascending", "descending",
                    "static" (stays near start), "random". Default: "arch".
    - octave_range: How many octaves the melody can span. Default: 1.
    - start_degree: Scale degree to begin on (1=root). Default: 1.
    - velocity_min: Minimum note velocity. Default: 70.
    - velocity_max: Maximum note velocity. Default: 100.

    Returns "notes", "clip_length", "scale", "root".
    """
    import random as _random

    try:
        ableton = get_ableton_connection()
        _, intervals, root_str, scale_str = _resolve_scale_context(ableton, root_note, scale_name)
        root_midi = _note_name_to_midi(root_str)

        # Build scale pitch pool
        pitches = _build_scale_pitches(root_midi, intervals, octave_range + 1)
        # Trim to a comfortable melodic range (root to root + octave_range octaves)
        pitches = [p for p in pitches if root_midi <= p <= root_midi + octave_range * 12]
        if not pitches:
            pitches = [root_midi]

        # Grid and fill settings
        density_settings = {
            "sparse": (0.5,  0.5),
            "medium": (0.5,  0.7),
            "dense":  (0.25, 0.8),
        }
        grid_size, fill_prob = density_settings.get(density, (0.5, 0.7))

        clip_length = bars * 4.0
        total_slots = int(clip_length / grid_size)

        # Starting pitch
        start_idx = min(start_degree - 1, len(pitches) - 1)
        current_idx = start_idx

        notes = []
        for slot in range(total_slots):
            t = slot * grid_size
            progress = t / clip_length  # 0→1 across the phrase

            # Contour bias: preferred direction
            if contour == "arch":
                bias = 1 if progress < 0.5 else -1
            elif contour == "ascending":
                bias = 1
            elif contour == "descending":
                bias = -1
            elif contour == "static":
                bias = 0
            else:
                bias = 0

            # Decide motion type: step, leap, or rest
            roll = _random.random()
            if roll < 0.15:
                continue  # rest

            if roll < 0.40:
                # Leap: 3–4 scale steps
                step = _random.choice([3, 4]) * (bias if bias != 0 else _random.choice([-1, 1]))
            else:
                # Step: 1–2 scale steps
                step = _random.choice([1, 2]) * (bias if bias != 0 else _random.choice([-1, 1]))

            current_idx = max(0, min(len(pitches) - 1, current_idx + step))

            # Fill probability gate
            if _random.random() > fill_prob:
                continue

            vel = _random.randint(velocity_min, velocity_max)
            notes.append({
                "pitch": pitches[current_idx],
                "start_time": t,
                "duration": grid_size * _random.choice([1, 1, 2]),  # vary duration
                "velocity": vel,
                "mute": False,
            })

        return json.dumps({
            "notes": notes,
            "clip_length": clip_length,
            "scale": scale_str,
            "root": root_str,
            "hint": "Pass 'notes' and 'clip_length' to create_track_with_clip",
        }, indent=2)
    except Exception as e:
        return f"Error generating melody: {e}"


@mcp.tool()
def humanize_notes(
    ctx: Context,
    notes: List[Dict],
    timing_amount: float = 0.02,
    velocity_amount: int = 10,
    duration_amount: float = 0.05,
    seed: Optional[int] = None,
) -> str:
    """
    Apply subtle human-feel variations to a list of MIDI notes.

    Adds small random offsets to timing, velocity, and duration to break the mechanical
    feel of programmatic patterns. Use after generate_chord_progression, generate_bass_pattern,
    or generate_melody before passing notes to add_notes_to_clip.

    Parameters:
    - notes:            List of note dicts (pitch, start_time, duration, velocity, mute).
    - timing_amount:    Max timing shift in beats (±). Default: 0.02 (~5ms at 120 BPM).
    - velocity_amount:  Max velocity variation (±). Default: 10.
    - duration_amount:  Max duration variation (±). Default: 0.05 beats.
    - seed:             Optional integer seed for reproducibility.

    Returns {"notes": [...]} — pass directly to add_notes_to_clip or create_track_with_clip.
    """
    import random as _random
    if seed is not None:
        _random.seed(seed)

    try:
        humanized = []
        for note in notes:
            n = dict(note)
            n["start_time"] = max(0.0, n.get("start_time", 0.0) + _random.uniform(-timing_amount, timing_amount))
            n["duration"]   = max(0.01, n.get("duration", 0.25) + _random.uniform(-duration_amount, duration_amount))
            n["velocity"]   = max(1, min(127, n.get("velocity", 80) + _random.randint(-velocity_amount, velocity_amount)))
            humanized.append(n)
        return json.dumps({"notes": humanized}, indent=2)
    except Exception as e:
        return f"Error humanizing notes: {e}"


# =============================================================================
# Transport extras
# =============================================================================

@mcp.tool()
def redo(ctx: Context) -> str:
    """Redo the last undone action."""
    try:
        ableton = get_ableton_connection()
        ableton.send_command("redo")
        return "Redo applied"
    except Exception as e:
        logger.error(f"Error in redo: {str(e)}")
        return f"Error in redo: {str(e)}"


@mcp.tool()
def tap_tempo(ctx: Context) -> str:
    """Send a tap-tempo pulse. Call repeatedly in rhythm to set BPM by tapping."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("tap_tempo")
        return f"Tap registered. Current tempo: {result.get('tempo', '?')} BPM"
    except Exception as e:
        logger.error(f"Error tapping tempo: {str(e)}")
        return f"Error tapping tempo: {str(e)}"


@mcp.tool()
def capture_midi(ctx: Context) -> str:
    """Trigger Live's MIDI Capture to recover recently played notes on the armed track."""
    try:
        ableton = get_ableton_connection()
        ableton.send_command("capture_midi")
        return "MIDI captured"
    except Exception as e:
        logger.error(f"Error capturing MIDI: {str(e)}")
        return f"Error capturing MIDI: {str(e)}"


@mcp.tool()
def set_time_signature(ctx: Context, numerator: int = None, denominator: int = None) -> str:
    """
    Change the session time signature.

    Parameters:
    - numerator: Beats per bar (e.g. 3, 4, 5, 6, 7)
    - denominator: Beat unit (2, 4, 8, 16)
    """
    try:
        ableton = get_ableton_connection()
        params = {}
        if numerator is not None:
            params["numerator"] = numerator
        if denominator is not None:
            params["denominator"] = denominator
        result = ableton.send_command("set_time_signature", params)
        return f"Time signature: {result['numerator']}/{result['denominator']}"
    except Exception as e:
        logger.error(f"Error setting time signature: {str(e)}")
        return f"Error setting time signature: {str(e)}"


@mcp.tool()
def set_metronome(ctx: Context, enabled: bool) -> str:
    """
    Enable or disable the metronome click.

    Parameters:
    - enabled: True to enable, False to disable
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_metronome", {"enabled": enabled})
        state = "on" if result.get("metronome") else "off"
        return f"Metronome {state}"
    except Exception as e:
        logger.error(f"Error setting metronome: {str(e)}")
        return f"Error setting metronome: {str(e)}"


@mcp.tool()
def set_arrangement_record(ctx: Context, record: bool) -> str:
    """
    Arm or disarm arrangement recording.

    Parameters:
    - record: True to arm arrangement record, False to disarm
    """
    try:
        ableton = get_ableton_connection()
        ableton.send_command("set_arrangement_record", {"record": record})
        return f"Arrangement record {'armed' if record else 'disarmed'}"
    except Exception as e:
        logger.error(f"Error setting arrangement record: {str(e)}")
        return f"Error setting arrangement record: {str(e)}"


@mcp.tool()
def get_current_song_time(ctx: Context) -> str:
    """Get the current playhead position in beats."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_current_song_time")
        return f"Current song time: {result['current_song_time']:.3f} beats"
    except Exception as e:
        logger.error(f"Error getting song time: {str(e)}")
        return f"Error getting song time: {str(e)}"


@mcp.tool()
def set_current_song_time(ctx: Context, time: float) -> str:
    """
    Jump the playhead to a beat position in the Arrangement.

    Parameters:
    - time: Position in beats from the start (≥ 0). E.g. 8.0 = bar 3 in 4/4.
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_current_song_time", {"time": time})
        return f"Playhead moved to {result['current_song_time']:.3f} beats"
    except Exception as e:
        logger.error(f"Error setting song time: {str(e)}")
        return f"Error setting song time: {str(e)}"


# =============================================================================
# Scenes
# =============================================================================

@mcp.tool()
def get_scenes(ctx: Context) -> str:
    """List all scenes in the session with name, color, and tempo."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_scenes")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting scenes: {str(e)}")
        return f"Error getting scenes: {str(e)}"


@mcp.tool()
def create_scene(ctx: Context, index: int = -1) -> str:
    """
    Add a new empty scene.

    Parameters:
    - index: Position to insert the scene (-1 = append at end)
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("create_scene", {"index": index})
        return f"Created scene at index {result['index']} (name: '{result['name']}')"
    except Exception as e:
        logger.error(f"Error creating scene: {str(e)}")
        return f"Error creating scene: {str(e)}"


@mcp.tool()
def delete_scene(ctx: Context, index: int) -> str:
    """
    Delete a scene.

    Parameters:
    - index: The scene index to delete
    """
    try:
        ableton = get_ableton_connection()
        ableton.send_command("delete_scene", {"index": index})
        return f"Deleted scene {index}"
    except Exception as e:
        logger.error(f"Error deleting scene: {str(e)}")
        return f"Error deleting scene: {str(e)}"


@mcp.tool()
def fire_scene(ctx: Context, index: int) -> str:
    """
    Launch all clips in a scene.

    Parameters:
    - index: The scene index to fire
    """
    try:
        ableton = get_ableton_connection()
        ableton.send_command("fire_scene", {"index": index})
        return f"Scene {index} fired"
    except Exception as e:
        logger.error(f"Error firing scene: {str(e)}")
        return f"Error firing scene: {str(e)}"


@mcp.tool()
def set_scene_name(ctx: Context, index: int, name: str) -> str:
    """
    Rename a scene.

    Parameters:
    - index: Scene index
    - name: New name for the scene
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_scene_name", {"index": index, "name": name})
        return f"Scene {index} renamed to '{result['name']}'"
    except Exception as e:
        logger.error(f"Error setting scene name: {str(e)}")
        return f"Error setting scene name: {str(e)}"


@mcp.tool()
def set_scene_color(ctx: Context, index: int, color: str) -> str:
    """
    Set the color of a scene.

    Parameters:
    - index: Scene index
    - color: Hex color string e.g. '#FF2200'
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_scene_color", {"index": index, "color": color})
        return f"Scene {index} color set to {result['color']}"
    except Exception as e:
        logger.error(f"Error setting scene color: {str(e)}")
        return f"Error setting scene color: {str(e)}"


@mcp.tool()
def stop_all_clips(ctx: Context) -> str:
    """Stop all currently playing clips in all tracks."""
    try:
        ableton = get_ableton_connection()
        ableton.send_command("stop_all_clips")
        return "All clips stopped"
    except Exception as e:
        logger.error(f"Error stopping all clips: {str(e)}")
        return f"Error stopping all clips: {str(e)}"


# =============================================================================
# Return tracks & sends
# =============================================================================

@mcp.tool()
def get_return_tracks(ctx: Context) -> str:
    """List all return tracks with name, color, volume, and panning."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_return_tracks")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting return tracks: {str(e)}")
        return f"Error getting return tracks: {str(e)}"


@mcp.tool()
def create_return_track(ctx: Context) -> str:
    """Add a new return track (appended at the end of the return track list)."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("create_return_track")
        return f"Return track created at index {result['return_track_index']} (total: {result['return_track_count']})"
    except Exception as e:
        logger.error(f"Error creating return track: {str(e)}")
        return f"Error creating return track: {str(e)}"


@mcp.tool()
def set_send_level(ctx: Context, track_index: int, return_track_index: int, value: float) -> str:
    """
    Set the send level from a track to a return track.

    Parameters:
    - track_index: Source track index
    - return_track_index: Return track index (0 = A, 1 = B, …)
    - value: Send level 0.0–1.0
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_send_level", {
            "track_index": track_index,
            "return_track_index": return_track_index,
            "value": value,
        })
        return f"Track {track_index} send to return {return_track_index}: {result['value']:.3f}"
    except Exception as e:
        logger.error(f"Error setting send level: {str(e)}")
        return f"Error setting send level: {str(e)}"


# =============================================================================
# Track extras
# =============================================================================

@mcp.tool()
def set_track_arm(ctx: Context, track_index: int, arm: bool) -> str:
    """
    Arm or disarm a track for recording.

    Parameters:
    - track_index: Track index
    - arm: True to arm, False to disarm
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_track_arm", {"track_index": track_index, "arm": arm})
        return f"Track {track_index} {'armed' if result['arm'] else 'disarmed'}"
    except Exception as e:
        logger.error(f"Error setting track arm: {str(e)}")
        return f"Error setting track arm: {str(e)}"


@mcp.tool()
def duplicate_track(ctx: Context, track_index: int) -> str:
    """
    Duplicate a track including all its devices and clips. The copy appears at track_index + 1.

    Parameters:
    - track_index: Source track index
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("duplicate_track", {"track_index": track_index})
        return f"Track {track_index} duplicated → new track at {result['new_track_index']} (total: {result['track_count']})"
    except Exception as e:
        logger.error(f"Error duplicating track: {str(e)}")
        return f"Error duplicating track: {str(e)}"


# =============================================================================
# Clip extras
# =============================================================================

@mcp.tool()
def remove_notes_from_clip(
    ctx: Context,
    track_index: int,
    clip_index: int,
    from_pitch: int = 0,
    pitch_span: int = 128,
    from_time: float = 0.0,
    time_span: float = None,
) -> str:
    """
    Remove a range of notes from a MIDI clip.

    Parameters:
    - track_index: Track index
    - clip_index: Clip slot index
    - from_pitch: Lowest MIDI pitch to remove (0–127)
    - pitch_span: Number of pitches covered (default 128 = all)
    - from_time: Start time in beats
    - time_span: Duration in beats to clear (None = entire clip)
    """
    try:
        ableton = get_ableton_connection()
        params: dict = {
            "track_index": track_index,
            "clip_index": clip_index,
            "from_pitch": from_pitch,
            "pitch_span": pitch_span,
            "from_time": from_time,
        }
        if time_span is not None:
            params["time_span"] = time_span
        ableton.send_command("remove_notes_from_clip", params)
        return f"Notes removed from clip {clip_index} on track {track_index}"
    except Exception as e:
        logger.error(f"Error removing notes: {str(e)}")
        return f"Error removing notes: {str(e)}"


@mcp.tool()
def set_clip_loop(
    ctx: Context,
    track_index: int,
    clip_index: int,
    looping: bool = None,
    loop_start: float = None,
    loop_end: float = None,
) -> str:
    """
    Set loop properties on a clip.

    Parameters:
    - track_index: Track index
    - clip_index: Clip slot index
    - looping: True to enable looping, False to disable (None = no change)
    - loop_start: Loop start in beats (None = no change)
    - loop_end: Loop end in beats (None = no change)
    """
    try:
        ableton = get_ableton_connection()
        params: dict = {"track_index": track_index, "clip_index": clip_index}
        if looping is not None:
            params["looping"] = looping
        if loop_start is not None:
            params["loop_start"] = loop_start
        if loop_end is not None:
            params["loop_end"] = loop_end
        result = ableton.send_command("set_clip_loop", params)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error setting clip loop: {str(e)}")
        return f"Error setting clip loop: {str(e)}"


@mcp.tool()
def set_clip_color(ctx: Context, track_index: int, clip_index: int, color: str) -> str:
    """
    Set the color of a clip.

    Parameters:
    - track_index: Track index
    - clip_index: Clip slot index
    - color: Hex color string e.g. '#FF2200'
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_clip_color", {
            "track_index": track_index,
            "clip_index": clip_index,
            "color": color,
        })
        return f"Clip {clip_index} on track {track_index} color set to {result['color']}"
    except Exception as e:
        logger.error(f"Error setting clip color: {str(e)}")
        return f"Error setting clip color: {str(e)}"


# =============================================================================
# Arrangement
# =============================================================================

@mcp.tool()
def switch_to_arrangement_view(ctx: Context) -> str:
    """Switch Ableton's main window to the Arrangement (timeline) view."""
    try:
        ableton = get_ableton_connection()
        ableton.send_command("switch_to_arrangement_view")
        return "Switched to Arrangement view"
    except Exception as e:
        logger.error(f"Error switching view: {str(e)}")
        return f"Error switching view: {str(e)}"


@mcp.tool()
def get_arrangement_clips(ctx: Context, track_index: int) -> str:
    """
    List all clips placed in the Arrangement timeline for a track.

    Parameters:
    - track_index: Track index to inspect
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_arrangement_clips", {"track_index": track_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting arrangement clips: {str(e)}")
        return f"Error getting arrangement clips: {str(e)}"


@mcp.tool()
def get_cue_points(ctx: Context) -> str:
    """List all cue points (markers) in the Arrangement with their names and beat positions."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_cue_points")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting cue points: {str(e)}")
        return f"Error getting cue points: {str(e)}"


# =============================================================================
# Audio capture / export (real-time resampling)
# =============================================================================

@mcp.tool()
def set_track_input_routing(ctx: Context, track_index: int, routing_name: str = "Resampling") -> str:
    """
    Set a track's INPUT routing by display name (e.g. "Resampling" to capture the master output).
    If the requested routing isn't found, returns the list of available routing names.

    Parameters:
    - track_index:  the track to route
    - routing_name: input routing display name (default "Resampling")
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_track_input_routing", {
            "track_index": track_index, "routing_name": routing_name})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error setting input routing: {str(e)}")
        return f"Error setting input routing: {str(e)}"


@mcp.tool()
def set_track_monitor(ctx: Context, track_index: int, state: int = 2) -> str:
    """
    Set a track's monitoring state: 0 = In, 1 = Auto, 2 = Off.
    Use Off (2) on a Resampling capture track so it doesn't feed back while recording.
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_track_monitor", {
            "track_index": track_index, "state": state})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error setting monitor: {str(e)}")
        return f"Error setting monitor: {str(e)}"


@mcp.tool()
def fire_clip_slot(ctx: Context, track_index: int, clip_index: int = 0) -> str:
    """
    Fire a clip SLOT directly (unlike fire_clip, this works on EMPTY slots).
    On an armed track, firing an empty slot starts recording into it — used to trigger a resampling capture.
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("fire_clip_slot", {
            "track_index": track_index, "clip_index": clip_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error firing clip slot: {str(e)}")
        return f"Error firing clip slot: {str(e)}"


@mcp.tool()
def get_clip_file_path(ctx: Context, track_index: int, clip_index: int = 0) -> str:
    """
    Return the sample file path of a recorded audio clip on a track
    (checks the session clip slot first, then the latest arrangement clip).
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_clip_file_path", {
            "track_index": track_index, "clip_index": clip_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting clip file path: {str(e)}")
        return f"Error getting clip file path: {str(e)}"


@mcp.tool()
def export_audio(ctx: Context, bars: int = 16, scene_index: int = 0) -> str:
    """
    Capture the currently-playing Session audio to a WAV via real-time RESAMPLING, and return the recorded file path.

    Ableton's API has no render-to-disk, so this is a real-time capture — it takes `bars` worth of time
    at the current tempo. It:
      1. creates an audio track, routes its input to "Resampling" (the master bus), sets monitoring Off, arms it;
      2. (re)launches scene `scene_index` and records into the capture track's clip slot;
      3. waits the loop duration, stops, and reads the recorded clip's file_path.

    Parameters:
    - bars:        number of 4/4 bars to capture (default 16)
    - scene_index: the Session scene/row to play + record into (default 0)

    Note: requires the AbletonMCP Remote Script to expose set_track_input_routing / set_track_monitor.
    If this errors with an unknown-command message, reload the control surface in Live's Link/MIDI prefs
    (or restart Live). The WAV lands in the Live set's Samples/Recorded folder; its path is in `recording.file_path`.
    Launch quantization may offset the capture start by up to a bar; capture a couple extra bars if you need a clean loop.
    """
    import time
    try:
        ableton = get_ableton_connection()
        info = ableton.send_command("get_session_info")
        bpm = float(info.get("tempo", 120.0))
        seconds = bars * (60.0 / bpm) * 4.0

        cap = ableton.send_command("create_audio_track", {"index": -1})
        cap_idx = cap.get("index")

        routing = ableton.send_command("set_track_input_routing", {
            "track_index": cap_idx, "routing_name": "Resampling"})
        if not routing.get("set"):
            return ("Could not set 'Resampling' input on the capture track. "
                    "Available input routings: " + json.dumps(routing.get("available", [])))

        ableton.send_command("set_track_monitor", {"track_index": cap_idx, "state": 2})
        ableton.send_command("set_track_arm", {"track_index": cap_idx, "arm": True})
        ableton.send_command("set_track_name", {"track_index": cap_idx, "name": "GC Export"})

        # Fire the content scene AND the empty armed capture slot in the SAME Live tick, so they
        # quantize to the identical launch boundary → the recording's bar 1 == the content's bar 1.
        ableton.send_command("start_synced_capture", {
            "content_scene_index": scene_index,
            "capture_track_index": cap_idx,
            "capture_slot_index": scene_index})

        bar_len = (60.0 / bpm) * 4.0
        # Record the full loop + a 2-bar buffer so launch-quantization latency never clips the end.
        time.sleep(seconds + bar_len * 2 + 0.5)

        ableton.send_command("stop_all_clips")
        ableton.send_command("set_track_arm", {"track_index": cap_idx, "arm": False})
        time.sleep(0.5)  # let Live finalize / flush the recorded sample to disk

        # Trim the recording to an exact, bar-aligned loop (start is aligned to content bar 1).
        try:
            ableton.send_command("set_clip_loop", {
                "track_index": cap_idx, "clip_index": scene_index,
                "looping": True, "loop_start": 0.0, "loop_end": float(bars) * 4.0})
        except Exception:
            pass

        fp = ableton.send_command("get_clip_file_path", {
            "track_index": cap_idx, "clip_index": scene_index})

        return json.dumps({
            "capture_track_index": cap_idx,
            "bars": bars, "tempo": bpm, "captured_seconds": round(seconds, 1),
            "recording": fp,
        }, indent=2)
    except Exception as e:
        logger.error(f"Error exporting audio: {str(e)}")
        return f"Error exporting audio: {str(e)}"


# Main execution
def main():
    import argparse
    import sys
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", action="store_true", help="Run as HTTP server instead of stdio")
    parser.add_argument("--port", type=int, default=5006, help="HTTP server port (default: 5006)")
    args = parser.parse_args()

    if args.server:
        mcp.settings.host = "0.0.0.0"
        mcp.settings.port = args.port
        mcp.settings.transport_security.enable_dns_rebinding_protection = False
        mcp.run("streamable-http")
    else:
        logging.basicConfig(level=logging.INFO, stream=sys.stderr)
        mcp.run()

if __name__ == "__main__":
    main()