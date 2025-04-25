import time # For potential delays or timing later
import traceback # For error logging

# --- Placeholder Imports (We'll refine these paths later) ---
# Assume these modules/classes exist based on our structure plan
try:
    from ..config.manager import ConfigManager # To load bindings/settings
    from ..detectors.voice_detector import VoiceDetector
    from ..detectors.facial_detector import FacialDetector # Assuming this exists or will exist
    # Import other detectors (HandDetector, etc.) here later
    from ..actions.registry import get_action_function # To get the function for an action ID
except ImportError:
    # Handle potential import errors if running engine parts standalone during dev
    print("WARN: Could not perform relative imports in engine.py. Ensure structure is correct or adjust paths if testing.")
    # Define dummy classes/functions for basic structure testing if needed
    class ConfigManager:
        def load_config(self): return {'bindings': [], 'settings': {}}
        def get_bindings(self): return []
        def get_setting(self, key, default=None): return default
    class VoiceDetector:
        def __init__(self, **kwargs): print("Dummy VoiceDetector created")
        def start(self): pass
        def stop(self): pass
    class FacialDetector:
         def __init__(self, **kwargs): print("Dummy FacialDetector created")
         def start(self): pass
         def stop(self): pass
    def get_action_function(action_id): return lambda: print(f"Dummy action called for: {action_id}")


class Engine:
    """
    The core engine that manages detectors, loads configuration,
    handles events, and executes corresponding actions.
    """
    def __init__(self, config_path="config.json"): # Default config file name
        print("--- Engine Initializing ---")
        self.config_manager = ConfigManager(config_path)
        self.detectors = {} # Dictionary to hold active detectors {detector_type: instance}
        self.bindings = {} # Dictionary to store loaded bindings for quick lookup
        self.is_running = False

        self._load_configuration()
        self._initialize_actions() # Currently just checks registry access
        self._initialize_detectors()
        print("--- Engine Initialized ---")

    def _load_configuration(self):
        """Loads bindings and settings from the config manager."""
        print("Engine: Loading configuration...")
        try:
            config_data = self.config_manager.load_config()
            # Process bindings into a more efficient lookup structure if needed
            # For now, just store the raw list/dict from config manager
            self.bindings = self.config_manager.get_bindings() # Assumes get_bindings() returns the structure we need
            # Store settings if needed (e.g., thresholds for detectors)
            self.settings = config_data.get('settings', {})
            print(f"Engine: Loaded {len(self.bindings)} bindings.")
            # print(f"Engine: Loaded settings: {self.settings}") # Optional: Log settings
        except Exception as e:
            print(f"ERROR: Failed to load configuration: {e}")
            self.bindings = [] # Use empty bindings on error
            self.settings = {}

    def _initialize_actions(self):
        """Initializes access to the action registry."""
        # Currently, we just need the function, no complex setup needed here.
        # We verify that the import worked by checking the function type.
        if not callable(get_action_function):
             print("ERROR: Action registry function 'get_action_function' not available!")
        else:
            print("Engine: Action registry access initialized.")


    def _initialize_detectors(self):
        """Creates and initializes detector instances based on configuration."""
        print("Engine: Initializing detectors...")
        self.detectors = {} # Clear any previous detectors

        # --- Voice Detector Initialization ---
        # Extract trigger words needed for voice detector from bindings
        voice_trigger_words = set()
        for binding in self.bindings:
            if binding.get("trigger_type") == "voice":
                trigger = binding.get("trigger_event")
                if trigger: # Ensure trigger_event is not empty/None
                    voice_trigger_words.add(str(trigger).lower())

        if voice_trigger_words: # Only initialize if there are voice bindings
            try:
                print(f"Engine: Initializing VoiceDetector for triggers: {list(voice_trigger_words)}")
                # Get specific settings for the voice detector if they exist
                voice_settings = self.settings.get('voice_detector', {})
                self.detectors['voice'] = VoiceDetector(
                    trigger_words=list(voice_trigger_words), # Pass the required trigger words
                    event_handler=self.handle_event, # Pass the engine's handler method!
                    energy_threshold=voice_settings.get('energy_threshold', DEFAULT_ENERGY_THRESHOLD), # Allow config override
                    pause_threshold=voice_settings.get('pause_threshold', DEFAULT_PAUSE_THRESHOLD),   # Allow config override
                    # device_index=voice_settings.get('device_index', None) # Future: Allow config override
                )
            except Exception as e:
                 print(f"ERROR: Failed to initialize VoiceDetector: {e}")
                 traceback.print_exc()
        else:
            print("Engine: No voice bindings found, VoiceDetector not initialized.")


        # --- Facial Detector Initialization (Example Structure) ---
        # Check if any bindings use the 'face' trigger type
        facial_triggers_needed = any(b.get("trigger_type") == "face" for b in self.bindings)

        if facial_triggers_needed:
            try:
                print("Engine: Initializing FacialDetector...")
                # Get specific settings for the facial detector if they exist
                facial_settings = self.settings.get('facial_detector', {})
                self.detectors['face'] = FacialDetector(
                     # Pass settings from config if needed (e.g., thresholds, camera index)
                     # ear_threshold=facial_settings.get('ear_threshold', 0.20),
                     # mar_threshold=facial_settings.get('mar_threshold', 0.35),
                     # camera_index=facial_settings.get('camera_index', 0),
                     event_handler=self.handle_event # Pass the engine's handler method!
                )
            except Exception as e:
                 print(f"ERROR: Failed to initialize FacialDetector: {e}")
                 traceback.print_exc()
        else:
             print("Engine: No facial bindings found, FacialDetector not initialized.")

        # --- Initialize other detectors (Hand, etc.) similarly ---

        print(f"Engine: Initialized active detectors: {list(self.detectors.keys())}")


    def handle_event(self, detector_type, event_data):
        """
        Callback method for detectors. Receives events and triggers actions based on bindings.
        Args:
            detector_type (str): The type of detector sending the event (e.g., "voice", "face").
            event_data (any): The specific event data (e.g., "next", "LEFT_WINK").
        """
        if not self.is_running:
             # print(f"DEBUG: Event received while engine stopped: {detector_type} - {event_data}")
             return # Don't process events if detection isn't active

        print(f"Engine: Event received - Type: '{detector_type}', Data: '{event_data}'")

        # Convert event data to the format expected in bindings (usually lowercase string)
        event_key = str(event_data).lower()

        # --- Find Matching Binding ---
        action_id_to_execute = None
        for binding in self.bindings:
            # Check if binding matches the received event type and data
            if binding.get("trigger_type") == detector_type and \
               binding.get("trigger_event", "").lower() == event_key:
                action_id_to_execute = binding.get("action_id")
                print(f"Engine: Found binding - Event '{event_key}' triggers Action ID '{action_id_to_execute}'")
                break # Found the first matching binding, stop searching

        # --- Execute Action ---
        if action_id_to_execute:
            action_func = get_action_function(action_id_to_execute)
            if action_func:
                try:
                    print(f"Engine: Executing action for ID '{action_id_to_execute}'...")
                    action_func() # Call the action function
                except Exception as e:
                    print(f"ERROR: Failed to execute action '{action_id_to_execute}': {e}")
                    traceback.print_exc()
            else:
                print(f"WARN: Action ID '{action_id_to_execute}' found in binding but not in action registry!")
        # else: # Optional: Log if an event was received but had no binding
            # print(f"Engine: No action bound to event: {detector_type} - {event_key}")


    def start(self):
        """Starts all initialized detectors."""
        if self.is_running:
            print("Engine: Already running.")
            return
        print("--- Engine Starting Detectors ---")
        self.is_running = True # Set running flag BEFORE starting detectors
        start_success_count = 0
        for detector_type, detector_instance in self.detectors.items():
            try:
                detector_instance.start()
                start_success_count += 1
            except Exception as e:
                print(f"ERROR: Failed to start detector '{detector_type}': {e}")
                traceback.print_exc()
        if start_success_count == len(self.detectors):
             print("Engine: All detectors started successfully.")
        else:
             print(f"WARN: Started {start_success_count}/{len(self.detectors)} detectors.")


    def stop(self):
        """Stops all initialized detectors."""
        if not self.is_running:
             print("Engine: Already stopped.")
             return
        print("--- Engine Stopping Detectors ---")
        self.is_running = False # Set running flag AFTER stopping detectors ideally, or before is ok too
        stop_success_count = 0
        for detector_type, detector_instance in self.detectors.items():
            try:
                detector_instance.stop()
                stop_success_count += 1
            except Exception as e:
                print(f"ERROR: Failed to stop detector '{detector_type}': {e}")
                traceback.print_exc()
        if stop_success_count == len(self.detectors):
             print("Engine: All detectors stopped successfully.")
        else:
             print(f"WARN: Stopped {stop_success_count}/{len(self.detectors)} detectors.")


    def reload_configuration(self):
        """Stops detectors, reloads config, and restarts detectors."""
        print("--- Engine Reloading Configuration ---")
        self.stop()
        # Add a small delay to ensure threads fully stop if needed
        # time.sleep(0.1)
        self._load_configuration()
        self._initialize_detectors() # Re-create detectors with new config/triggers
        self.start()
        print("--- Engine Reload Complete ---")


# --- Example Usage (for testing engine logic standalone - remove later) ---
if __name__ == '__main__':
    print("--- Running Engine Directly (Basic Test) ---")

    # Create dummy config file for testing
    import json
    dummy_config = {
        "bindings": [
            {"trigger_type": "voice", "trigger_event": "next", "action_id": "PRESS_DOWN"},
            {"trigger_type": "voice", "trigger_event": "go", "action_id": "PRESS_RIGHT"},
            {"trigger_type": "face", "trigger_event": "LEFT_WINK", "action_id": "PRESS_LEFT"} # Example face binding
        ],
        "settings": {
            "voice_detector": {"pause_threshold": 0.45},
            "facial_detector": {} # Placeholder
        }
    }
    config_filename = "test_engine_config.json"
    with open(config_filename, 'w') as f:
        json.dump(dummy_config, f, indent=4)

    # Dummy Config Manager for testing
    class TestConfigManager:
         def __init__(self, path): self.path = path
         def load_config(self):
             with open(self.path, 'r') as f: return json.load(f)
         def get_bindings(self): return self.load_config().get('bindings', [])
         def get_setting(self, key, default=None): return self.load_config().get('settings', {}).get(key, default)

    # Monkey-patch ConfigManager for the test
    import sys
    # This assumes engine.py is in accessicommand/core
    sys.modules['accessicommand.config.manager'].ConfigManager = TestConfigManager
    # Re-import to use the patched version (may not be strictly necessary depending on import timing)
    # from accessicommand.config.manager import ConfigManager

    # Create the engine using the test config
    engine = Engine(config_path=config_filename)

    # Start the engine (starts dummy detectors)
    engine.start()

    print("\nEngine running with dummy detectors.")
    print("Simulating events (call engine.handle_event manually):")
    print("  engine.handle_event('voice', 'go')")
    print("  engine.handle_event('face', 'LEFT_WINK')")
    print("  engine.handle_event('voice', 'unknown')")

    # Keep alive for manual testing via console or just exit
    try:
        input("Press Enter to stop engine and exit...")
    except KeyboardInterrupt:
        pass
    finally:
        engine.stop()
        # Clean up dummy file
        import os
        try: os.remove(config_filename)
        except OSError: pass
        print("--- Engine Test Finished ---")