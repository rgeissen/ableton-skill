# AbletonMCP/init.py
from __future__ import absolute_import, print_function, unicode_literals

from _Framework.ControlSurface import ControlSurface
import socket
import json
import threading
import time
import traceback

# Change queue import for Python 2
try:
    import Queue as queue  # Python 2
except ImportError:
    import queue  # Python 3

# Constants for socket communication
DEFAULT_PORT = 9877
HOST = "localhost"

def create_instance(c_instance):
    """Create and return the AbletonMCP script instance"""
    return AbletonMCP(c_instance)

class AbletonMCP(ControlSurface):
    """AbletonMCP Remote Script for Ableton Live"""
    
    def __init__(self, c_instance):
        """Initialize the control surface"""
        ControlSurface.__init__(self, c_instance)
        self.log_message("AbletonMCP Remote Script initializing...")
        
        # Socket server for communication
        self.server = None
        self.client_threads = []
        self.server_thread = None
        self.running = False
        
        # Cache the song reference for easier access
        self._song = self.song()

        # Event subscription state
        self._event_queue = []
        self._event_lock = threading.Lock()
        self._active_listeners = {}  # event_type -> listener callable

        # Start the socket server
        self.start_server()
        
        self.log_message("AbletonMCP initialized")
        
        # Show a message in Ableton
        self.show_message("AbletonMCP: Listening for commands on port " + str(DEFAULT_PORT))
    
    def disconnect(self):
        """Called when Ableton closes or the control surface is removed"""
        self.log_message("AbletonMCP disconnecting...")
        self.running = False
        
        # Stop the server
        if self.server:
            try:
                self.server.close()
            except:
                pass
        
        # Wait for the server thread to exit
        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(1.0)
            
        # Clean up any client threads
        for client_thread in self.client_threads[:]:
            if client_thread.is_alive():
                # We don't join them as they might be stuck
                self.log_message("Client thread still alive during disconnect")
        
        ControlSurface.disconnect(self)
        self.log_message("AbletonMCP disconnected")
    
    def start_server(self):
        """Start the socket server in a separate thread"""
        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server.bind((HOST, DEFAULT_PORT))
            self.server.listen(5)  # Allow up to 5 pending connections
            
            self.running = True
            self.server_thread = threading.Thread(target=self._server_thread)
            self.server_thread.daemon = True
            self.server_thread.start()
            
            self.log_message("Server started on port " + str(DEFAULT_PORT))
        except Exception as e:
            self.log_message("Error starting server: " + str(e))
            self.show_message("AbletonMCP: Error starting server - " + str(e))
    
    def _server_thread(self):
        """Server thread implementation - handles client connections"""
        try:
            self.log_message("Server thread started")
            # Set a timeout to allow regular checking of running flag
            self.server.settimeout(1.0)
            
            while self.running:
                try:
                    # Accept connections with timeout
                    client, address = self.server.accept()
                    self.log_message("Connection accepted from " + str(address))
                    self.show_message("AbletonMCP: Client connected")
                    
                    # Handle client in a separate thread
                    client_thread = threading.Thread(
                        target=self._handle_client,
                        args=(client,)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                    
                    # Keep track of client threads
                    self.client_threads.append(client_thread)
                    
                    # Clean up finished client threads
                    self.client_threads = [t for t in self.client_threads if t.is_alive()]
                    
                except socket.timeout:
                    # No connection yet, just continue
                    continue
                except Exception as e:
                    if self.running:  # Only log if still running
                        self.log_message("Server accept error: " + str(e))
                    time.sleep(0.5)
            
            self.log_message("Server thread stopped")
        except Exception as e:
            self.log_message("Server thread error: " + str(e))
    
    def _handle_client(self, client):
        """Handle communication with a connected client"""
        self.log_message("Client handler started")
        client.settimeout(None)  # No timeout for client socket
        buffer = ''  # Changed from b'' to '' for Python 2
        
        try:
            while self.running:
                try:
                    # Receive data
                    data = client.recv(8192)
                    
                    if not data:
                        # Client disconnected
                        self.log_message("Client disconnected")
                        break
                    
                    # Accumulate data in buffer with explicit encoding/decoding
                    try:
                        # Python 3: data is bytes, decode to string
                        buffer += data.decode('utf-8')
                    except AttributeError:
                        # Python 2: data is already string
                        buffer += data
                    
                    try:
                        # Try to parse command from buffer
                        command = json.loads(buffer)  # Removed decode('utf-8')
                        buffer = ''  # Clear buffer after successful parse
                        
                        self.log_message("Received command: " + str(command.get("type", "unknown")))
                        
                        # Process the command and get response
                        response = self._process_command(command)
                        
                        # Send the response with explicit encoding
                        try:
                            # Python 3: encode string to bytes
                            client.sendall(json.dumps(response).encode('utf-8'))
                        except AttributeError:
                            # Python 2: string is already bytes
                            client.sendall(json.dumps(response))
                    except ValueError:
                        # Incomplete data, wait for more
                        continue
                        
                except Exception as e:
                    self.log_message("Error handling client data: " + str(e))
                    self.log_message(traceback.format_exc())
                    
                    # Send error response if possible
                    error_response = {
                        "status": "error",
                        "message": str(e)
                    }
                    try:
                        # Python 3: encode string to bytes
                        client.sendall(json.dumps(error_response).encode('utf-8'))
                    except AttributeError:
                        # Python 2: string is already bytes
                        client.sendall(json.dumps(error_response))
                    except:
                        # If we can't send the error, the connection is probably dead
                        break
                    
                    # For serious errors, break the loop
                    if not isinstance(e, ValueError):
                        break
        except Exception as e:
            self.log_message("Error in client handler: " + str(e))
        finally:
            try:
                self._unsubscribe_all()
            except:
                pass
            try:
                client.close()
            except:
                pass
            self.log_message("Client handler stopped")
    
    def _process_command(self, command):
        """Process a command from the client and return a response"""
        command_type = command.get("type", "")
        params = command.get("params", {})
        
        # Initialize response
        response = {
            "status": "success",
            "result": {}
        }
        
        try:
            # Route the command to the appropriate handler
            if command_type == "get_session_info":
                include_track_names = params.get("include_track_names", False)
                response["result"] = self._get_session_info(include_track_names)
            elif command_type == "get_track_info":
                track_index = params.get("track_index", 0)
                include_clips = params.get("include_clips", True)
                include_devices = params.get("include_devices", True)
                response["result"] = self._get_track_info(track_index, include_clips, include_devices)
            elif command_type == "get_all_tracks_info":
                response["result"] = self._get_all_tracks_info()
            # Commands that modify Live's state should be scheduled on the main thread
            elif command_type in ["create_midi_track", "set_track_name",
                                 "create_clip", "add_notes_to_clip", "set_clip_name",
                                 "set_tempo", "fire_clip", "stop_clip",
                                 "start_playback", "stop_playback", "load_browser_item",
                                 "load_browser_item_by_path",
                                 "create_audio_track", "set_track_mixer", "set_track_mute",
                                 "set_track_solo", "duplicate_clip", "delete_clip",
                                 "delete_track", "set_device_param", "undo",
                                 "set_scale_mode", "set_track_color"]:
                # Use a thread-safe approach with a response queue
                response_queue = queue.Queue()
                
                # Define a function to execute on the main thread
                def main_thread_task():
                    try:
                        result = None
                        if command_type == "create_midi_track":
                            index = params.get("index", -1)
                            result = self._create_midi_track(index)
                        elif command_type == "set_track_name":
                            track_index = params.get("track_index", 0)
                            name = params.get("name", "")
                            result = self._set_track_name(track_index, name)
                        elif command_type == "create_clip":
                            track_index = params.get("track_index", 0)
                            clip_index = params.get("clip_index", 0)
                            length = params.get("length", 4.0)
                            result = self._create_clip(track_index, clip_index, length)
                        elif command_type == "add_notes_to_clip":
                            track_index = params.get("track_index", 0)
                            clip_index = params.get("clip_index", 0)
                            notes = params.get("notes", [])
                            result = self._add_notes_to_clip(track_index, clip_index, notes)
                        elif command_type == "set_clip_name":
                            track_index = params.get("track_index", 0)
                            clip_index = params.get("clip_index", 0)
                            name = params.get("name", "")
                            result = self._set_clip_name(track_index, clip_index, name)
                        elif command_type == "set_tempo":
                            tempo = params.get("tempo", 120.0)
                            result = self._set_tempo(tempo)
                        elif command_type == "fire_clip":
                            track_index = params.get("track_index", 0)
                            clip_index = params.get("clip_index", 0)
                            result = self._fire_clip(track_index, clip_index)
                        elif command_type == "stop_clip":
                            track_index = params.get("track_index", 0)
                            clip_index = params.get("clip_index", 0)
                            result = self._stop_clip(track_index, clip_index)
                        elif command_type == "start_playback":
                            result = self._start_playback()
                        elif command_type == "stop_playback":
                            result = self._stop_playback()
                        elif command_type == "load_instrument_or_effect":
                            track_index = params.get("track_index", 0)
                            uri = params.get("uri", "")
                            result = self._load_instrument_or_effect(track_index, uri)
                        elif command_type == "load_browser_item":
                            track_index = params.get("track_index", 0)
                            item_uri = params.get("item_uri", "")
                            result = self._load_browser_item(track_index, item_uri)
                        elif command_type == "load_browser_item_by_path":
                            track_index = params.get("track_index", 0)
                            browser_path = params.get("browser_path", "")
                            result = self._load_browser_item_by_path(track_index, browser_path)
                        elif command_type == "create_audio_track":
                            index = params.get("index", -1)
                            result = self._create_audio_track(index)
                        elif command_type == "set_track_mixer":
                            track_index = params.get("track_index", 0)
                            volume = params.get("volume", None)
                            panning = params.get("panning", None)
                            result = self._set_track_mixer(track_index, volume, panning)
                        elif command_type == "set_track_mute":
                            track_index = params.get("track_index", 0)
                            mute = params.get("mute", False)
                            result = self._set_track_mute(track_index, mute)
                        elif command_type == "set_track_solo":
                            track_index = params.get("track_index", 0)
                            solo = params.get("solo", False)
                            result = self._set_track_solo(track_index, solo)
                        elif command_type == "duplicate_clip":
                            track_index = params.get("track_index", 0)
                            clip_index = params.get("clip_index", 0)
                            target_track_index = params.get("target_track_index", track_index)
                            target_clip_index = params.get("target_clip_index", 0)
                            result = self._duplicate_clip(track_index, clip_index, target_track_index, target_clip_index)
                        elif command_type == "delete_clip":
                            track_index = params.get("track_index", 0)
                            clip_index = params.get("clip_index", 0)
                            result = self._delete_clip(track_index, clip_index)
                        elif command_type == "delete_track":
                            track_index = params.get("track_index", 0)
                            result = self._delete_track(track_index)
                        elif command_type == "set_device_param":
                            track_index = params.get("track_index", 0)
                            device_index = params.get("device_index", 0)
                            param_index = params.get("param_index", 0)
                            value = params.get("value", 0.0)
                            chain_path = params.get("chain_path", None)
                            return_track_index = params.get("return_track_index", None)
                            is_master = params.get("is_master", False)
                            result = self._set_device_param(track_index, device_index, param_index, value, chain_path, return_track_index, is_master)
                        elif command_type == "undo":
                            result = self._undo()
                        elif command_type == "set_scale_mode":
                            root_note = params.get("root_note", None)
                            scale_name = params.get("scale_name", None)
                            in_key = params.get("in_key", None)
                            result = self._set_scale_mode(root_note, scale_name, in_key)
                        elif command_type == "set_track_color":
                            track_index = params.get("track_index", 0)
                            color = params.get("color")
                            result = self._set_track_color(track_index, color)

                        # Put the result in the queue
                        response_queue.put({"status": "success", "result": result})
                    except Exception as e:
                        self.log_message("Error in main thread task: " + str(e))
                        self.log_message(traceback.format_exc())
                        response_queue.put({"status": "error", "message": str(e)})
                
                # Schedule the task to run on the main thread
                try:
                    self.schedule_message(0, main_thread_task)
                except AssertionError:
                    # If we're already on the main thread, execute directly
                    main_thread_task()
                
                # Wait for the response with a timeout
                try:
                    task_response = response_queue.get(timeout=10.0)
                    if task_response.get("status") == "error":
                        response["status"] = "error"
                        response["message"] = task_response.get("message", "Unknown error")
                    else:
                        response["result"] = task_response.get("result", {})
                except queue.Empty:
                    response["status"] = "error"
                    response["message"] = "Timeout waiting for operation to complete"
            elif command_type == "get_browser_item":
                uri = params.get("uri", None)
                path = params.get("path", None)
                response["result"] = self._get_browser_item(uri, path)
            elif command_type == "get_browser_categories":
                category_type = params.get("category_type", "all")
                response["result"] = self._get_browser_categories(category_type)
            elif command_type == "get_browser_items":
                path = params.get("path", "")
                item_type = params.get("item_type", "all")
                response["result"] = self._get_browser_items(path, item_type)
            # Add the new browser commands
            elif command_type == "get_browser_tree":
                category_type = params.get("category_type", "all")
                response["result"] = self.get_browser_tree(category_type)
            elif command_type == "get_browser_items_at_path":
                path = params.get("path", "")
                response["result"] = self.get_browser_items_at_path(path)
            elif command_type == "get_clip_notes":
                track_index = params.get("track_index", 0)
                clip_index = params.get("clip_index", 0)
                response["result"] = self._get_clip_notes(track_index, clip_index)
            elif command_type == "get_device_params":
                track_index = params.get("track_index", 0)
                device_index = params.get("device_index", 0)
                chain_path = params.get("chain_path", None)
                return_track_index = params.get("return_track_index", None)
                is_master = params.get("is_master", False)
                response["result"] = self._get_device_params(track_index, device_index, chain_path, return_track_index, is_master)
            elif command_type == "get_drum_rack_pads":
                track_index = params.get("track_index", 0)
                device_index = params.get("device_index", 0)
                return_track_index = params.get("return_track_index", None)
                is_master = params.get("is_master", False)
                response["result"] = self._get_drum_rack_pads(track_index, device_index, return_track_index, is_master)
            elif command_type == "get_playback_position":
                response["result"] = self._get_playback_position()
            elif command_type == "get_scale_mode":
                response["result"] = self._get_scale_mode()
            elif command_type == "subscribe_to_events":
                event_types = params.get("event_types", [])
                response["result"] = self._subscribe_to_events(event_types)
            elif command_type == "get_pending_events":
                response["result"] = self._get_pending_events()
            elif command_type == "unsubscribe_from_events":
                event_types = params.get("event_types", None)
                response["result"] = self._unsubscribe_from_events(event_types)
            else:
                response["status"] = "error"
                response["message"] = "Unknown command: " + command_type
        except Exception as e:
            self.log_message("Error processing command: " + str(e))
            self.log_message(traceback.format_exc())
            response["status"] = "error"
            response["message"] = str(e)
        
        return response
    
    # Command implementations
    
    def _get_session_info(self, include_track_names=False):
        """Get information about the current session"""
        try:
            result = {
                "tempo": self._song.tempo,
                "signature_numerator": self._song.signature_numerator,
                "signature_denominator": self._song.signature_denominator,
                "track_count": len(self._song.tracks),
                "return_track_count": len(self._song.return_tracks),
                "master_track": {
                    "name": "Master",
                    "volume": self._song.master_track.mixer_device.volume.value,
                    "panning": self._song.master_track.mixer_device.panning.value
                }
            }
            if include_track_names:
                result["track_names"] = [t.name for t in self._song.tracks]
            return result
        except Exception as e:
            self.log_message("Error getting session info: " + str(e))
            raise
    
    def _get_track_info(self, track_index, include_clips=True, include_devices=True):
        """Get information about a track"""
        try:
            if track_index < 0 or track_index >= len(self._song.tracks):
                raise IndexError("Track index out of range")

            track = self._song.tracks[track_index]

            all_tracks = list(self._song.tracks)
            is_grouped = hasattr(track, 'is_grouped') and bool(track.is_grouped)
            group_index = None
            if is_grouped and hasattr(track, 'group_track') and track.group_track in all_tracks:
                group_index = all_tracks.index(track.group_track)

            result = {
                "index": track_index,
                "name": track.name,
                "is_audio_track": track.has_audio_input,
                "is_midi_track": track.has_midi_input,
                "mute": track.mute,
                "solo": track.solo,
                "arm": track.arm,
                "volume": track.mixer_device.volume.value,
                "panning": track.mixer_device.panning.value,
                "color": "#{:06X}".format(track.color) if hasattr(track, 'color') else None,
                "is_grouped": is_grouped,
                "group_index": group_index,
            }

            if include_clips:
                clip_slots = []
                for slot_index, slot in enumerate(track.clip_slots):
                    clip_info = None
                    if slot.has_clip:
                        clip = slot.clip
                        clip_info = {
                            "name": clip.name,
                            "length": clip.length,
                            "is_playing": clip.is_playing,
                            "is_recording": clip.is_recording
                        }
                    clip_slots.append({
                        "index": slot_index,
                        "has_clip": slot.has_clip,
                        "clip": clip_info
                    })
                result["clip_slots"] = clip_slots

            if include_devices:
                devices = []
                for device_index, device in enumerate(track.devices):
                    devices.append({
                        "index": device_index,
                        "name": device.name,
                        "class_name": device.class_name,
                        "type": self._get_device_type(device)
                    })
                result["devices"] = devices

            return result
        except Exception as e:
            self.log_message("Error getting track info: " + str(e))
            raise

    def _get_all_tracks_info(self):
        """Get compact summary of all tracks"""
        try:
            all_tracks = list(self._song.tracks)
            tracks = []
            for i, track in enumerate(all_tracks):
                is_grouped = hasattr(track, 'is_grouped') and bool(track.is_grouped)
                group_index = None
                if is_grouped and hasattr(track, 'group_track') and track.group_track in all_tracks:
                    group_index = all_tracks.index(track.group_track)
                tracks.append({
                    "index": i,
                    "name": track.name,
                    "type": "midi" if track.has_midi_input else "audio",
                    "color": "#{:06X}".format(track.color) if hasattr(track, 'color') else None,
                    "mute": track.mute,
                    "solo": track.solo,
                    "volume": track.mixer_device.volume.value,
                    "is_grouped": is_grouped,
                    "group_index": group_index,
                    "device_count": len(track.devices),
                    "clip_count": sum(1 for s in track.clip_slots if s.has_clip),
                })
            return {"tracks": tracks}
        except Exception as e:
            self.log_message("Error getting all tracks info: " + str(e))
            raise
    
    def _create_midi_track(self, index):
        """Create a new MIDI track at the specified index"""
        try:
            # Create the track
            self._song.create_midi_track(index)
            
            # Get the new track
            new_track_index = len(self._song.tracks) - 1 if index == -1 else index
            new_track = self._song.tracks[new_track_index]
            
            result = {
                "index": new_track_index,
                "name": new_track.name
            }
            return result
        except Exception as e:
            self.log_message("Error creating MIDI track: " + str(e))
            raise
    
    
    def _set_track_name(self, track_index, name):
        """Set the name of a track"""
        try:
            if track_index < 0 or track_index >= len(self._song.tracks):
                raise IndexError("Track index out of range")
            
            # Set the name
            track = self._song.tracks[track_index]
            track.name = name
            
            result = {
                "name": track.name
            }
            return result
        except Exception as e:
            self.log_message("Error setting track name: " + str(e))
            raise
    
    def _create_clip(self, track_index, clip_index, length):
        """Create a new MIDI clip in the specified track and clip slot"""
        try:
            if track_index < 0 or track_index >= len(self._song.tracks):
                raise IndexError("Track index out of range")
            
            track = self._song.tracks[track_index]
            
            if clip_index < 0 or clip_index >= len(track.clip_slots):
                raise IndexError("Clip index out of range")
            
            clip_slot = track.clip_slots[clip_index]
            
            # Check if the clip slot already has a clip
            if clip_slot.has_clip:
                raise Exception("Clip slot already has a clip")
            
            # Create the clip
            clip_slot.create_clip(length)
            
            result = {
                "name": clip_slot.clip.name,
                "length": clip_slot.clip.length
            }
            return result
        except Exception as e:
            self.log_message("Error creating clip: " + str(e))
            raise
    
    def _add_notes_to_clip(self, track_index, clip_index, notes):
        """Add MIDI notes to a clip"""
        try:
            if track_index < 0 or track_index >= len(self._song.tracks):
                raise IndexError("Track index out of range")
            
            track = self._song.tracks[track_index]
            
            if clip_index < 0 or clip_index >= len(track.clip_slots):
                raise IndexError("Clip index out of range")
            
            clip_slot = track.clip_slots[clip_index]
            
            if not clip_slot.has_clip:
                raise Exception("No clip in slot")
            
            clip = clip_slot.clip
            
            # Convert note data to Live's format
            live_notes = []
            for note in notes:
                pitch = note.get("pitch", 60)
                start_time = note.get("start_time", 0.0)
                duration = note.get("duration", 0.25)
                velocity = note.get("velocity", 100)
                mute = note.get("mute", False)
                
                live_notes.append((pitch, start_time, duration, velocity, mute))
            
            # Add the notes
            clip.set_notes(tuple(live_notes))
            
            result = {
                "note_count": len(notes)
            }
            return result
        except Exception as e:
            self.log_message("Error adding notes to clip: " + str(e))
            raise
    
    def _set_clip_name(self, track_index, clip_index, name):
        """Set the name of a clip"""
        try:
            if track_index < 0 or track_index >= len(self._song.tracks):
                raise IndexError("Track index out of range")
            
            track = self._song.tracks[track_index]
            
            if clip_index < 0 or clip_index >= len(track.clip_slots):
                raise IndexError("Clip index out of range")
            
            clip_slot = track.clip_slots[clip_index]
            
            if not clip_slot.has_clip:
                raise Exception("No clip in slot")
            
            clip = clip_slot.clip
            clip.name = name
            
            result = {
                "name": clip.name
            }
            return result
        except Exception as e:
            self.log_message("Error setting clip name: " + str(e))
            raise
    
    def _set_tempo(self, tempo):
        """Set the tempo of the session"""
        try:
            self._song.tempo = tempo
            
            result = {
                "tempo": self._song.tempo
            }
            return result
        except Exception as e:
            self.log_message("Error setting tempo: " + str(e))
            raise
    
    def _fire_clip(self, track_index, clip_index):
        """Fire a clip"""
        try:
            if track_index < 0 or track_index >= len(self._song.tracks):
                raise IndexError("Track index out of range")
            
            track = self._song.tracks[track_index]
            
            if clip_index < 0 or clip_index >= len(track.clip_slots):
                raise IndexError("Clip index out of range")
            
            clip_slot = track.clip_slots[clip_index]
            
            if not clip_slot.has_clip:
                raise Exception("No clip in slot")
            
            clip_slot.fire()
            
            result = {
                "fired": True
            }
            return result
        except Exception as e:
            self.log_message("Error firing clip: " + str(e))
            raise
    
    def _stop_clip(self, track_index, clip_index):
        """Stop a clip"""
        try:
            if track_index < 0 or track_index >= len(self._song.tracks):
                raise IndexError("Track index out of range")
            
            track = self._song.tracks[track_index]
            
            if clip_index < 0 or clip_index >= len(track.clip_slots):
                raise IndexError("Clip index out of range")
            
            clip_slot = track.clip_slots[clip_index]
            
            clip_slot.stop()
            
            result = {
                "stopped": True
            }
            return result
        except Exception as e:
            self.log_message("Error stopping clip: " + str(e))
            raise
    
    
    def _start_playback(self):
        """Start playing the session"""
        try:
            self._song.start_playing()
            
            result = {
                "playing": self._song.is_playing
            }
            return result
        except Exception as e:
            self.log_message("Error starting playback: " + str(e))
            raise
    
    def _stop_playback(self):
        """Stop playing the session"""
        try:
            self._song.stop_playing()
            
            result = {
                "playing": self._song.is_playing
            }
            return result
        except Exception as e:
            self.log_message("Error stopping playback: " + str(e))
            raise
    
    def _get_browser_item(self, uri, path):
        """Get a browser item by URI or path"""
        try:
            # Access the application's browser instance instead of creating a new one
            app = self.application()
            if not app:
                raise RuntimeError("Could not access Live application")
                
            result = {
                "uri": uri,
                "path": path,
                "found": False
            }
            
            # Try to find by URI first if provided
            if uri:
                item = self._find_browser_item_by_uri(app.browser, uri)
                if item:
                    result["found"] = True
                    result["item"] = {
                        "name": item.name,
                        "is_folder": item.is_folder,
                        "is_device": item.is_device,
                        "is_loadable": item.is_loadable,
                        "uri": item.uri
                    }
                    return result
            
            # If URI not provided or not found, try by path
            if path:
                # Parse the path and navigate to the specified item
                path_parts = path.split("/")
                
                # Determine the root based on the first part
                current_item = None
                if path_parts[0].lower() == "nstruments":
                    current_item = app.browser.instruments
                elif path_parts[0].lower() == "sounds":
                    current_item = app.browser.sounds
                elif path_parts[0].lower() == "drums":
                    current_item = app.browser.drums
                elif path_parts[0].lower() == "audio_effects":
                    current_item = app.browser.audio_effects
                elif path_parts[0].lower() == "midi_effects":
                    current_item = app.browser.midi_effects
                else:
                    # Default to instruments if not specified
                    current_item = app.browser.instruments
                    # Don't skip the first part in this case
                    path_parts = ["instruments"] + path_parts
                
                # Navigate through the path
                for i in range(1, len(path_parts)):
                    part = path_parts[i]
                    if not part:  # Skip empty parts
                        continue
                    
                    found = False
                    for child in current_item.children:
                        if child.name.lower() == part.lower():
                            current_item = child
                            found = True
                            break
                    
                    if not found:
                        result["error"] = "Path part '{0}' not found".format(part)
                        return result
                
                # Found the item
                result["found"] = True
                result["item"] = {
                    "name": current_item.name,
                    "is_folder": current_item.is_folder,
                    "is_device": current_item.is_device,
                    "is_loadable": current_item.is_loadable,
                    "uri": current_item.uri
                }
            
            return result
        except Exception as e:
            self.log_message("Error getting browser item: " + str(e))
            self.log_message(traceback.format_exc())
            raise   
    
    
    
    def _load_browser_item(self, track_index, item_uri):
        """Load a browser item onto a track by its URI"""
        try:
            if track_index < 0 or track_index >= len(self._song.tracks):
                raise IndexError("Track index out of range")
            
            track = self._song.tracks[track_index]
            
            # Access the application's browser instance instead of creating a new one
            app = self.application()
            
            # Find the browser item by URI
            item = self._find_browser_item_by_uri(app.browser, item_uri)
            
            if not item:
                raise ValueError("Browser item with URI '{0}' not found".format(item_uri))
            
            # Select the track
            self._song.view.selected_track = track
            
            # Load the item
            app.browser.load_item(item)
            
            result = {
                "loaded": True,
                "item_name": item.name,
                "track_name": track.name,
                "uri": item_uri
            }
            return result
        except Exception as e:
            self.log_message("Error loading browser item: {0}".format(str(e)))
            self.log_message(traceback.format_exc())
            raise
    
    def _load_browser_item_by_path(self, track_index, browser_path):
        """Navigate to an item by browser_path and load it onto a track."""
        try:
            if track_index < 0 or track_index >= len(self._song.tracks):
                raise IndexError("Track index out of range")

            app = self.application()
            if not app:
                raise RuntimeError("Could not access Live application")

            path_parts = [p for p in browser_path.split("/") if p]
            if not path_parts:
                raise ValueError("Invalid browser_path")

            root_category = path_parts[0].lower()
            if not hasattr(app.browser, root_category):
                raise ValueError("Unknown browser category: {0}".format(root_category))

            current_item = getattr(app.browser, root_category)

            for part in path_parts[1:]:
                if not hasattr(current_item, 'children'):
                    raise ValueError("Item has no children at this path level")
                found = None
                for child in current_item.children:
                    if hasattr(child, 'name') and child.name.lower() == part.lower():
                        found = child
                        break
                if found is None:
                    raise ValueError("Path part '{0}' not found".format(part))
                current_item = found

            if not (hasattr(current_item, 'is_loadable') and current_item.is_loadable):
                raise ValueError("Item at '{0}' is not loadable".format(browser_path))

            track = self._song.tracks[track_index]
            self._song.view.selected_track = track
            app.browser.load_item(current_item)

            return {"loaded": True, "item_name": current_item.name}
        except Exception as e:
            self.log_message("Error loading browser item by path: {0}".format(str(e)))
            raise

    def _find_browser_item_by_uri(self, browser_or_item, uri, max_depth=10, current_depth=0):
        """Find a browser item by its URI"""
        try:
            # Check if this is the item we're looking for
            if hasattr(browser_or_item, 'uri') and browser_or_item.uri == uri:
                return browser_or_item
            
            # Stop recursion if we've reached max depth
            if current_depth >= max_depth:
                return None
            
            # Check if this is a browser with root categories
            if hasattr(browser_or_item, 'instruments'):
                # Check all main categories
                categories = [
                    browser_or_item.instruments,
                    browser_or_item.sounds,
                    browser_or_item.drums,
                    browser_or_item.audio_effects,
                    browser_or_item.midi_effects
                ]
                
                for category in categories:
                    item = self._find_browser_item_by_uri(category, uri, max_depth, current_depth + 1)
                    if item:
                        return item
                
                return None
            
            # Check if this item has children
            if hasattr(browser_or_item, 'children') and browser_or_item.children:
                for child in browser_or_item.children:
                    item = self._find_browser_item_by_uri(child, uri, max_depth, current_depth + 1)
                    if item:
                        return item
            
            return None
        except Exception as e:
            self.log_message("Error finding browser item by URI: {0}".format(str(e)))
            return None
    
    # Helper methods
    
    def _get_device_type(self, device):
        """Get the type of a device"""
        try:
            # Simple heuristic - in a real implementation you'd look at the device class
            if device.can_have_drum_pads:
                return "drum_machine"
            elif device.can_have_chains:
                return "rack"
            elif "instrument" in device.class_display_name.lower():
                return "instrument"
            elif "audio_effect" in device.class_name.lower():
                return "audio_effect"
            elif "midi_effect" in device.class_name.lower():
                return "midi_effect"
            else:
                return "unknown"
        except:
            return "unknown"
    
    def _create_audio_track(self, index):
        """Create a new audio track at the specified index"""
        try:
            self._song.create_audio_track(index)
            new_track_index = len(self._song.tracks) - 1 if index == -1 else index
            new_track = self._song.tracks[new_track_index]
            return {"index": new_track_index, "name": new_track.name}
        except Exception as e:
            self.log_message("Error creating audio track: " + str(e))
            raise

    def _set_track_mixer(self, track_index, volume, panning):
        """Set volume and/or panning on a track"""
        try:
            if track_index < 0 or track_index >= len(self._song.tracks):
                raise IndexError("Track index out of range")
            track = self._song.tracks[track_index]
            result = {}
            if volume is not None:
                track.mixer_device.volume.value = max(0.0, min(1.0, volume))
                result["volume"] = track.mixer_device.volume.value
            if panning is not None:
                track.mixer_device.panning.value = max(-1.0, min(1.0, panning))
                result["panning"] = track.mixer_device.panning.value
            return result
        except Exception as e:
            self.log_message("Error setting track mixer: " + str(e))
            raise

    def _set_track_mute(self, track_index, mute):
        """Mute or unmute a track"""
        try:
            if track_index < 0 or track_index >= len(self._song.tracks):
                raise IndexError("Track index out of range")
            track = self._song.tracks[track_index]
            track.mute = mute
            return {"mute": track.mute}
        except Exception as e:
            self.log_message("Error setting track mute: " + str(e))
            raise

    def _set_track_solo(self, track_index, solo):
        """Solo or unsolo a track"""
        try:
            if track_index < 0 or track_index >= len(self._song.tracks):
                raise IndexError("Track index out of range")
            track = self._song.tracks[track_index]
            track.solo = solo
            return {"solo": track.solo}
        except Exception as e:
            self.log_message("Error setting track solo: " + str(e))
            raise

    def _delete_track(self, track_index):
        """Delete a track"""
        try:
            if track_index < 0 or track_index >= len(self._song.tracks):
                raise IndexError("Track index out of range")
            self._song.delete_track(track_index)
            return {"deleted": True}
        except Exception as e:
            self.log_message("Error deleting track: " + str(e))
            raise

    def _duplicate_clip(self, track_index, clip_index, target_track_index, target_clip_index):
        """Duplicate a clip by copying its notes to a new clip in the target slot"""
        try:
            if track_index < 0 or track_index >= len(self._song.tracks):
                raise IndexError("Source track index out of range")
            if target_track_index < 0 or target_track_index >= len(self._song.tracks):
                raise IndexError("Target track index out of range")

            src_track = self._song.tracks[track_index]
            if clip_index < 0 or clip_index >= len(src_track.clip_slots):
                raise IndexError("Source clip index out of range")
            src_slot = src_track.clip_slots[clip_index]
            if not src_slot.has_clip:
                raise Exception("No clip in source slot")
            src_clip = src_slot.clip

            dst_track = self._song.tracks[target_track_index]
            if target_clip_index < 0 or target_clip_index >= len(dst_track.clip_slots):
                raise IndexError("Target clip index out of range")
            dst_slot = dst_track.clip_slots[target_clip_index]
            if dst_slot.has_clip:
                raise Exception("Target slot already has a clip")

            # Read notes from source
            notes = src_clip.get_notes(0, 0, src_clip.length, 128)

            # Create new clip and copy notes
            dst_slot.create_clip(src_clip.length)
            dst_clip = dst_slot.clip
            dst_clip.name = src_clip.name
            if notes:
                dst_clip.set_notes(notes)

            return {"duplicated": True, "note_count": len(notes)}
        except Exception as e:
            self.log_message("Error duplicating clip: " + str(e))
            raise

    def _delete_clip(self, track_index, clip_index):
        """Delete a clip from a clip slot"""
        try:
            if track_index < 0 or track_index >= len(self._song.tracks):
                raise IndexError("Track index out of range")
            track = self._song.tracks[track_index]
            if clip_index < 0 or clip_index >= len(track.clip_slots):
                raise IndexError("Clip index out of range")
            slot = track.clip_slots[clip_index]
            if not slot.has_clip:
                raise Exception("No clip in slot")
            slot.delete_clip()
            return {"deleted": True}
        except Exception as e:
            self.log_message("Error deleting clip: " + str(e))
            raise

    def _get_clip_notes(self, track_index, clip_index):
        """Get all MIDI notes from a clip"""
        try:
            if track_index < 0 or track_index >= len(self._song.tracks):
                raise IndexError("Track index out of range")
            track = self._song.tracks[track_index]
            if clip_index < 0 or clip_index >= len(track.clip_slots):
                raise IndexError("Clip index out of range")
            slot = track.clip_slots[clip_index]
            if not slot.has_clip:
                raise Exception("No clip in slot")
            clip = slot.clip
            notes = clip.get_notes(0, 0, clip.length, 128)
            note_list = [
                {"pitch": n[0], "start_time": n[1], "duration": n[2], "velocity": n[3], "mute": n[4]}
                for n in notes
            ]
            return {"clip_name": clip.name, "length": clip.length, "note_count": len(note_list), "notes": note_list}
        except Exception as e:
            self.log_message("Error getting clip notes: " + str(e))
            raise

    def _resolve_track(self, track_index=0, return_track_index=None, is_master=False):
        """Return the correct track object based on type selector."""
        if is_master:
            return self._song.master_track
        if return_track_index is not None:
            tracks = self._song.return_tracks
            if return_track_index < 0 or return_track_index >= len(tracks):
                raise IndexError("Return track index out of range")
            return tracks[return_track_index]
        tracks = self._song.tracks
        if track_index < 0 or track_index >= len(tracks):
            raise IndexError("Track index out of range")
        return tracks[track_index]

    def _resolve_device(self, track, device_index, chain_path):
        """Walk chain_path steps from a top-level device to the target nested device.

        Each step is a dict with:
          chain_index  (int, required)
          device_index (int, default 0) — which device inside that chain
          pad_note     (int, optional)  — if present, enter a drum rack pad first
        """
        if device_index < 0 or device_index >= len(track.devices):
            raise IndexError("Device index out of range")
        device = track.devices[device_index]
        for step in chain_path:
            pad_note = step.get("pad_note", None)
            chain_idx = step.get("chain_index", 0)
            dev_idx = step.get("device_index", 0)
            if pad_note is not None:
                if not device.can_have_drum_pads:
                    raise ValueError("chain_path step has pad_note but device is not a drum rack")
                pad = device.drum_pads[pad_note]
                if chain_idx >= len(pad.chains):
                    raise IndexError("chain_index {0} out of range for pad {1}".format(chain_idx, pad_note))
                chain = pad.chains[chain_idx]
            else:
                if not device.can_have_chains:
                    raise ValueError("chain_path step has chain_index but device has no chains")
                if chain_idx >= len(device.chains):
                    raise IndexError("chain_index {0} out of range".format(chain_idx))
                chain = device.chains[chain_idx]
            if dev_idx >= len(chain.devices):
                raise IndexError("device_index {0} out of range in chain".format(dev_idx))
            device = chain.devices[dev_idx]
        return device

    def _device_contents_summary(self, device, current_chain_path):
        """Return a progressive-disclosure map of a rack's immediate children.

        Each nested device entry includes a ready-to-use chain_path that can be
        passed directly to get_device_params / set_device_param.
        """
        if device.can_have_drum_pads:
            pads = []
            for pad in device.drum_pads:
                if not pad.chains:
                    continue
                pad_chains = []
                for ci, chain in enumerate(pad.chains):
                    devs = []
                    for di, d in enumerate(chain.devices):
                        next_path = current_chain_path + [{"pad_note": pad.note, "chain_index": ci, "device_index": di}]
                        devs.append({
                            "name": d.name,
                            "class_name": d.class_name,
                            "chain_path": next_path,
                            "has_nested_devices": d.can_have_chains or d.can_have_drum_pads
                        })
                    pad_chains.append({"chain_index": ci, "name": chain.name, "devices": devs})
                pads.append({"note": pad.note, "name": pad.name, "mute": pad.mute, "solo": pad.solo, "chains": pad_chains})
            return {"type": "drum_rack", "drum_pads": pads}
        elif device.can_have_chains:
            chains = []
            for ci, chain in enumerate(device.chains):
                devs = []
                for di, d in enumerate(chain.devices):
                    next_path = current_chain_path + [{"chain_index": ci, "device_index": di}]
                    devs.append({
                        "name": d.name,
                        "class_name": d.class_name,
                        "chain_path": next_path,
                        "has_nested_devices": d.can_have_chains or d.can_have_drum_pads
                    })
                chains.append({"chain_index": ci, "name": chain.name, "devices": devs})
            return {"type": "rack", "chains": chains}
        return None

    def _get_device_params(self, track_index, device_index, chain_path=None, return_track_index=None, is_master=False):
        """Get parameters of any device. chain_path navigates into nested racks at any depth.
        When the resolved device is itself a rack, includes a contents summary with
        ready-to-use chain_path values for each nested device."""
        try:
            track = self._resolve_track(track_index, return_track_index, is_master)
            chain_path = chain_path or []
            device = self._resolve_device(track, device_index, chain_path)
            params = [
                {"index": i, "name": p.name, "value": p.value, "min": p.min, "max": p.max, "is_quantized": p.is_quantized}
                for i, p in enumerate(device.parameters)
            ]
            result = {
                "device_name": device.name,
                "class_name": device.class_name,
                "chain_path": chain_path,
                "param_count": len(params),
                "parameters": params
            }
            contents = self._device_contents_summary(device, chain_path)
            if contents:
                result["contents"] = contents
                result["hint"] = "Pass chain_path from any nested device entry to get its parameters"
            return result
        except Exception as e:
            self.log_message("Error getting device params: " + str(e))
            raise

    def _get_drum_rack_pads(self, track_index, device_index, return_track_index=None, is_master=False):
        """Get drum pad assignments (note, name, mute, solo) for a DrumGroupDevice."""
        try:
            track = self._resolve_track(track_index, return_track_index, is_master)
            if device_index < 0 or device_index >= len(track.devices):
                raise IndexError("Device index out of range")
            device = track.devices[device_index]
            if not device.can_have_drum_pads:
                raise ValueError("Device is not a drum rack")
            pads = []
            for pad in device.drum_pads:
                if pad.chains:
                    chain_names = [c.name for c in pad.chains]
                    pads.append({"note": pad.note, "name": pad.name, "mute": pad.mute, "solo": pad.solo, "chains": chain_names})
            return {"device_name": device.name, "pad_count": len(pads), "pads": pads}
        except Exception as e:
            self.log_message("Error getting drum rack pads: " + str(e))
            raise

    def _set_device_param(self, track_index, device_index, param_index, value, chain_path=None, return_track_index=None, is_master=False):
        """Set a parameter on any device. Accepts the same chain_path as _get_device_params."""
        try:
            track = self._resolve_track(track_index, return_track_index, is_master)
            chain_path = chain_path or []
            device = self._resolve_device(track, device_index, chain_path)
            if param_index < 0 or param_index >= len(device.parameters):
                raise IndexError("Parameter index out of range")
            param = device.parameters[param_index]
            param.value = max(param.min, min(param.max, value))
            return {"param_name": param.name, "value": param.value}
        except Exception as e:
            self.log_message("Error setting device param: " + str(e))
            raise

    def _undo(self):
        """Undo the last action"""
        try:
            self._song.undo()
            return {"success": True}
        except Exception as e:
            self.log_message("Error performing undo: " + str(e))
            raise

    def _get_playback_position(self):
        """Get the current playback position"""
        try:
            return {
                "position_beats": self._song.current_song_time,
                "is_playing": self._song.is_playing
            }
        except Exception as e:
            self.log_message("Error getting playback position: " + str(e))
            raise

    # Note names for converting root_note integer to string
    _NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

    def _get_scale_mode(self):
        """Get the current scale mode settings"""
        try:
            result = {}
            if hasattr(self._song, "root_note"):
                root = int(self._song.root_note)
                result["root_note"] = root
                result["root_note_name"] = self._NOTE_NAMES[root % 12]
            if hasattr(self._song, "scale_name"):
                result["scale_name"] = self._song.scale_name
            if hasattr(self._song, "in_key"):
                result["in_key"] = self._song.in_key
            if not result:
                raise Exception("Scale mode properties not available in this Live version (requires Live 11+)")
            return result
        except Exception as e:
            self.log_message("Error getting scale mode: " + str(e))
            raise

    def _set_track_color(self, track_index, color):
        """Set track color. color is a hex string '#RRGGBB' or an integer."""
        try:
            if track_index < 0 or track_index >= len(self._song.tracks):
                raise IndexError("Track index out of range")
            track = self._song.tracks[track_index]
            if isinstance(color, str):
                color_int = int(color.lstrip('#'), 16)
            else:
                color_int = int(color)
            track.color = color_int
            return {"track_index": track_index, "color": "#{:06X}".format(track.color)}
        except Exception as e:
            self.log_message("Error setting track color: " + str(e))
            raise

    def _set_scale_mode(self, root_note, scale_name, in_key):
        """Set scale mode properties"""
        try:
            result = {}
            if root_note is not None:
                if not hasattr(self._song, "root_note"):
                    raise Exception("root_note not available in this Live version (requires Live 11+)")
                self._song.root_note = max(0, min(11, int(root_note)))
                result["root_note"] = int(self._song.root_note)
                result["root_note_name"] = self._NOTE_NAMES[int(self._song.root_note) % 12]
            if scale_name is not None:
                if not hasattr(self._song, "scale_name"):
                    raise Exception("scale_name not available in this Live version (requires Live 11+)")
                self._song.scale_name = scale_name
                result["scale_name"] = self._song.scale_name
            if in_key is not None:
                if not hasattr(self._song, "in_key"):
                    raise Exception("in_key not available in this Live version (requires Live 11+)")
                self._song.in_key = bool(in_key)
                result["in_key"] = self._song.in_key
            return result
        except Exception as e:
            self.log_message("Error setting scale mode: " + str(e))
            raise

    def get_browser_tree(self, category_type="all"):
        """
        Get a simplified tree of browser categories.
        
        Args:
            category_type: Type of categories to get ('all', 'instruments', 'sounds', etc.)
            
        Returns:
            Dictionary with the browser tree structure
        """
        try:
            # Access the application's browser instance instead of creating a new one
            app = self.application()
            if not app:
                raise RuntimeError("Could not access Live application")
                
            # Check if browser is available
            if not hasattr(app, 'browser') or app.browser is None:
                raise RuntimeError("Browser is not available in the Live application")
            
            result = {
                "type": category_type,
                "categories": [],
            }
            
            # Helper function to process a browser item and its children
            def process_item(item, depth=0):
                if not item:
                    return None
                
                result = {
                    "name": item.name if hasattr(item, 'name') else "Unknown",
                    "is_folder": hasattr(item, 'children') and bool(item.children),
                    "is_device": hasattr(item, 'is_device') and item.is_device,
                    "is_loadable": hasattr(item, 'is_loadable') and item.is_loadable,
                    "uri": item.uri if hasattr(item, 'uri') else None,
                    "children": []
                }
                
                
                return result
            
            # Process based on category type and available attributes
            if (category_type == "all" or category_type == "instruments") and hasattr(app.browser, 'instruments'):
                try:
                    instruments = process_item(app.browser.instruments)
                    if instruments:
                        instruments["name"] = "Instruments"  # Ensure consistent naming
                        result["categories"].append(instruments)
                except Exception as e:
                    self.log_message("Error processing instruments: {0}".format(str(e)))
            
            if (category_type == "all" or category_type == "sounds") and hasattr(app.browser, 'sounds'):
                try:
                    sounds = process_item(app.browser.sounds)
                    if sounds:
                        sounds["name"] = "Sounds"  # Ensure consistent naming
                        result["categories"].append(sounds)
                except Exception as e:
                    self.log_message("Error processing sounds: {0}".format(str(e)))
            
            if (category_type == "all" or category_type == "drums") and hasattr(app.browser, 'drums'):
                try:
                    drums = process_item(app.browser.drums)
                    if drums:
                        drums["name"] = "Drums"  # Ensure consistent naming
                        result["categories"].append(drums)
                except Exception as e:
                    self.log_message("Error processing drums: {0}".format(str(e)))
            
            if (category_type == "all" or category_type == "audio_effects") and hasattr(app.browser, 'audio_effects'):
                try:
                    audio_effects = process_item(app.browser.audio_effects)
                    if audio_effects:
                        audio_effects["name"] = "Audio Effects"  # Ensure consistent naming
                        result["categories"].append(audio_effects)
                except Exception as e:
                    self.log_message("Error processing audio_effects: {0}".format(str(e)))
            
            if (category_type == "all" or category_type == "midi_effects") and hasattr(app.browser, 'midi_effects'):
                try:
                    midi_effects = process_item(app.browser.midi_effects)
                    if midi_effects:
                        midi_effects["name"] = "MIDI Effects"
                        result["categories"].append(midi_effects)
                except Exception as e:
                    self.log_message("Error processing midi_effects: {0}".format(str(e)))
            
            extra_categories = ['samples', 'clips', 'grooves', 'packs', 'user_library', 'max_for_live', 'plugins']
            for attr in extra_categories:
                if category_type == "all" or category_type == attr:
                    if not hasattr(app.browser, attr):
                        continue
                    try:
                        item = getattr(app.browser, attr)
                        category = process_item(item)
                        if category:
                            category["name"] = attr.capitalize()
                            result["categories"].append(category)
                    except Exception as e:
                        self.log_message("Error processing {0}: {1}".format(attr, str(e)))
            
            self.log_message("Browser tree generated for {0} with {1} root categories".format(
                category_type, len(result['categories'])))
            return result
            
        except Exception as e:
            self.log_message("Error getting browser tree: {0}".format(str(e)))
            self.log_message(traceback.format_exc())
            raise
    
    def get_browser_items_at_path(self, path):
        """
        Get browser items at a specific path.
        
        Args:
            path: Path in the format "category/folder/subfolder"
                 where category is one of: instruments, sounds, drums, audio_effects, midi_effects
                 or any other available browser category
                 
        Returns:
            Dictionary with items at the specified path
        """
        try:
            # Access the application's browser instance instead of creating a new one
            app = self.application()
            if not app:
                raise RuntimeError("Could not access Live application")
                
            # Check if browser is available
            if not hasattr(app, 'browser') or app.browser is None:
                raise RuntimeError("Browser is not available in the Live application")
            
            # Parse the path
            path_parts = path.split("/")
            if not path_parts:
                raise ValueError("Invalid path")

            # Determine the root category
            root_category = path_parts[0].lower()
            current_item = None

            known_categories = [
                'instruments', 'sounds', 'drums', 'audio_effects', 'midi_effects',
                'samples', 'clips', 'grooves', 'packs', 'user_library', 'max_for_live', 'plugins'
            ]

            if hasattr(app.browser, root_category):
                current_item = getattr(app.browser, root_category)
            else:
                return {
                    "path": path,
                    "error": "Unknown or unavailable category: {0}".format(root_category),
                    "available_categories": known_categories,
                    "items": []
                }
            
            # Navigate through the path
            for i in range(1, len(path_parts)):
                part = path_parts[i]
                if not part:  # Skip empty parts
                    continue
                
                if not hasattr(current_item, 'children'):
                    return {
                        "path": path,
                        "error": "Item at '{0}' has no children".format('/'.join(path_parts[:i])),
                        "items": []
                    }
                
                found = False
                for child in current_item.children:
                    if hasattr(child, 'name') and child.name.lower() == part.lower():
                        current_item = child
                        found = True
                        break
                
                if not found:
                    return {
                        "path": path,
                        "error": "Path part '{0}' not found".format(part),
                        "items": []
                    }
            
            # Get items at the current path
            items = []
            if hasattr(current_item, 'children'):
                for child in current_item.children:
                    is_folder = hasattr(child, 'children') and bool(child.children)
                    child_name = child.name if hasattr(child, 'name') else "Unknown"
                    item_info = {
                        "name": child_name,
                        "is_folder": is_folder,
                        "is_device": hasattr(child, 'is_device') and child.is_device,
                        "is_loadable": hasattr(child, 'is_loadable') and child.is_loadable,
                        "uri": child.uri if hasattr(child, 'uri') else None
                    }
                    if is_folder:
                        item_info["path"] = path + "/" + child_name
                    items.append(item_info)
            
            result = {
                "path": path,
                "name": current_item.name if hasattr(current_item, 'name') else "Unknown",
                "uri": current_item.uri if hasattr(current_item, 'uri') else None,
                "is_folder": hasattr(current_item, 'children') and bool(current_item.children),
                "is_device": hasattr(current_item, 'is_device') and current_item.is_device,
                "is_loadable": hasattr(current_item, 'is_loadable') and current_item.is_loadable,
                "items": items
            }
            
            self.log_message("Retrieved {0} items at path: {1}".format(len(items), path))
            return result
            
        except Exception as e:
            self.log_message("Error getting browser items at path: {0}".format(str(e)))
            self.log_message(traceback.format_exc())
            raise

    # ---------------------------------------------------------------------------
    # Event Subscription
    # ---------------------------------------------------------------------------

    _SUBSCRIBABLE_EVENTS = {
        "tempo":            "add_tempo_listener",
        "is_playing":       "add_is_playing_listener",
        "current_song_time":"add_current_song_time_listener",
        "track_count":      "add_tracks_listener",
    }
    _UNSUBSCRIBABLE_EVENTS = {
        "tempo":            "remove_tempo_listener",
        "is_playing":       "remove_is_playing_listener",
        "current_song_time":"remove_current_song_time_listener",
        "track_count":      "remove_tracks_listener",
    }

    def _snapshot_for(self, event_type):
        try:
            if event_type == "tempo":
                return {"tempo": self._song.tempo}
            if event_type == "is_playing":
                return {"is_playing": self._song.is_playing}
            if event_type == "current_song_time":
                return {"position": self._song.current_song_time}
            if event_type == "track_count":
                return {"track_count": len(self._song.tracks)}
        except Exception:
            pass
        return {}

    def _make_listener(self, event_type):
        def listener():
            with self._event_lock:
                self._event_queue.append({
                    "type": event_type,
                    "timestamp": time.time(),
                    "data": self._snapshot_for(event_type),
                })
        return listener

    def _subscribe_to_events(self, event_types):
        subscribed = []
        failed = []
        for et in event_types:
            if et in self._active_listeners:
                subscribed.append(et)
                continue
            add_method = self._SUBSCRIBABLE_EVENTS.get(et)
            if not add_method or not hasattr(self._song, add_method):
                failed.append(et)
                continue
            try:
                fn = self._make_listener(et)
                getattr(self._song, add_method)(fn)
                self._active_listeners[et] = fn
                subscribed.append(et)
            except Exception as e:
                self.log_message("Failed to subscribe to {}: {}".format(et, str(e)))
                failed.append(et)
        result = {"subscribed": subscribed}
        if failed:
            result["failed"] = failed
        return result

    def _get_pending_events(self):
        with self._event_lock:
            events = list(self._event_queue)
            self._event_queue = []
        return {"events": events, "count": len(events)}

    def _unsubscribe_from_events(self, event_types=None):
        if event_types is None:
            event_types = list(self._active_listeners.keys())
        unsubscribed = []
        for et in event_types:
            fn = self._active_listeners.pop(et, None)
            if fn is None:
                continue
            remove_method = self._UNSUBSCRIBABLE_EVENTS.get(et)
            if remove_method and hasattr(self._song, remove_method):
                try:
                    getattr(self._song, remove_method)(fn)
                except Exception as e:
                    self.log_message("Error removing listener for {}: {}".format(et, str(e)))
            unsubscribed.append(et)
        return {"unsubscribed": unsubscribed}

    def _unsubscribe_all(self):
        self._unsubscribe_from_events(None)
