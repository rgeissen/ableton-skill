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
            "set_device_param", "undo", "save_set", "set_scale_mode"
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


# Core Tool endpoints

@mcp.tool()
def get_session_info(ctx: Context) -> str:
    """Get detailed information about the current Ableton session"""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_session_info")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting session info from Ableton: {str(e)}")
        return f"Error getting session info: {str(e)}"

@mcp.tool()
def get_track_info(ctx: Context, track_index: int) -> str:
    """
    Get detailed information about a specific track in Ableton.
    
    Parameters:
    - track_index: The index of the track to get information about
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_track_info", {"track_index": track_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting track info from Ableton: {str(e)}")
        return f"Error getting track info: {str(e)}"

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
def get_browser_items_at_path(ctx: Context, path: str) -> str:
    """
    Get browser items at a specific path in Ableton's browser.
    
    Parameters:
    - path: Path in the format "category/folder/subfolder"
            where category is one of the available browser categories in Ableton
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_browser_items_at_path", {
            "path": path
        })
        
        # Check if there was an error with available categories
        if "error" in result and "available_categories" in result:
            error = result.get("error", "")
            available_cats = result.get("available_categories", [])
            return (f"Error: {error}\n"
                   f"Available browser categories: {', '.join(available_cats)}")
        
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
def get_browser_tags(ctx: Context, category: str = "all") -> str:
    """
    Return all tag names available in Ableton's browser, read directly from
    Ableton's local database (Ableton does not need to be running).

    Parameters:
    - category: Filter to tags used in a specific browser section.
                One of: all (default), sounds, instruments, drums, audio_effects,
                midi_effects, max_for_live, plugins, clips, samples, grooves, tunings
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

    Each result includes name, type, source, and a browser_path you can pass
    to get_browser_items_at_path to obtain a live URI for loading.
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
            LIMIT ?
        """, tags + [_KEYW_TYPE] + cat_params + [n, limit]).fetchall()

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
            "hint":       "Pass the parent folder of browser_path to get_browser_items_at_path to get a live URI",
            "results":    results,
        }, indent=2)

    except Exception as e:
        logger.error(f"Error searching by tags: {e}")
        return f"Error searching by tags: {e}"


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
        mcp.run("streamable-http")
    else:
        logging.basicConfig(level=logging.INFO, stream=sys.stderr)
        mcp.run()

if __name__ == "__main__":
    main()