# accessicommand/core/engine.py
import sys
import os
import traceback
import time

# --- DEBUG Prints (Optional: Can be removed for cleaner output) ---
print(f"--- Debug Info from engine.py ---")
print(f"Current Working Directory: {os.getcwd()}")
print("Python sys.path:")
for p in sys.path: print(f"  - {p}")
print("---------------------------------")
# --- END DEBUG ---


# --- Use ABSOLUTE Imports ---
try:
    print("Attempting absolute imports...")
    from accessicommand.config.manager import ConfigManager
    print(" -> Imported ConfigManager OK")
    from accessicommand.detectors.voice_detector import VoiceDetector
    print(" -> Imported VoiceDetector OK")
    # --- Import REAL Facial Detector ---
    from accessicommand.detectors.facial_detector import FacialDetector # This should now succeed
    print(" -> Imported FacialDetector OK")
    # ---------------------------------
    from accessicommand.actions.registry import get_action_function, ACTION_REGISTRY
    print(" -> Imported Action Registry OK")
    _imports_ok = True
    print("Absolute imports successful.")
except ImportError as e:
    print(f"ERROR: Could not perform absolute imports in engine.py: {e}")
    print("       Make sure all modules exist and __init__.py files are correct.")
    _imports_ok = False
    sys.exit(1)


# --- Engine Default Constants ---
# Voice Defaults
DEFAULT_VOICE_PAUSE_THRESHOLD = 0.4
DEFAULT_VOICE_ENERGY_THRESHOLD = 350
# Facial Defaults (Match those in facial_detector.py)
DEFAULT_CAMERA_INDEX = 0
DEFAULT_EAR_THRESHOLD = 0.20
DEFAULT_MAR_THRESHOLD = 0.35
DEFAULT_ERR_THRESHOLD = 1.34
DEFAULT_BOTH_EYES_CLOSED_FRAMES = 2
DEFAULT_HEAD_TILT_LEFT_MIN = -100
DEFAULT_HEAD_TILT_LEFT_MAX = -160
DEFAULT_HEAD_TILT_RIGHT_MIN = 100
DEFAULT_HEAD_TILT_RIGHT_MAX = 160
DEFAULT_CONSEC_FRAMES_MOUTH = 3
DEFAULT_CONSEC_FRAMES_EYEBROW = 3
DEFAULT_CONSEC_FRAMES_HEAD_TILT = 3
DEFAULT_BLINK_COOLDOWN = 0.3


class Engine:
    """ Core engine managing detectors, config, events, and actions. """
    def __init__(self, config_path="config.json"):
        print("--- Engine Initializing ---")
        self.config_manager = ConfigManager(config_path)
        self.detectors = {}
        self.bindings = []
        self.settings = {}
        self.is_running = False
        self._load_configuration()
        self._initialize_actions()
        # --- Initialize Detectors (Calls the updated method below) ---
        self._initialize_detectors()
        print("--- Engine Initialized ---")

    def _load_configuration(self):
        """ Loads config using ConfigManager. """
        print(f"Engine: Loading configuration from '{self.config_manager.config_path}'...")
        try:
            self.config_data = self.config_manager.get_config()
            self.bindings = self.config_manager.get_bindings()
            self.settings = self.config_manager.get_settings()
            print(f"Engine: Loaded {len(self.bindings)} bindings.")
        except Exception as e:
            print(f"ERROR: Failed to load configuration: {e}"); traceback.print_exc()
            self.bindings = []; self.settings = {}

    def _initialize_actions(self):
        """ Verifies action registry access. """
        if not callable(get_action_function): print("ERROR: get_action_function not available!")
        else: print(f"Engine: Action registry OK ({len(ACTION_REGISTRY)} actions).")

    def _initialize_detectors(self):
        """ Creates detector instances based on config bindings and settings. """
        print("Engine: Initializing detectors...")
        self.detectors = {} # Reset detectors

        # --- Voice Detector Initialization ---
        voice_trigger_words = set(str(b.get("trigger_event")).lower() for b in self.bindings if b.get("trigger_type") == "voice" and b.get("trigger_event"))
        if voice_trigger_words:
            try:
                print(f"Engine: Initializing VoiceDetector...")
                voice_settings = self.settings.get('voice_detector', {})
                self.detectors['voice'] = VoiceDetector(
                    trigger_words=list(voice_trigger_words),
                    event_handler=self.handle_event,
                    energy_threshold=voice_settings.get('energy_threshold', DEFAULT_VOICE_ENERGY_THRESHOLD),
                    pause_threshold=voice_settings.get('pause_threshold', DEFAULT_VOICE_PAUSE_THRESHOLD),
                )
            except Exception as e: print(f"ERROR: Init VoiceDetector failed: {e}"); traceback.print_exc()
        else: print("Engine: No voice bindings found.")

        # --- Facial Detector Initialization (UPDATED) ---
        facial_triggers_needed = any(b.get("trigger_type") == "face" for b in self.bindings)
        if facial_triggers_needed:
            # Check if the real FacialDetector class was imported successfully
            if 'FacialDetector' in globals() and _imports_ok:
                try:
                    print("Engine: Initializing FacialDetector...")
                    # Get the 'facial_detector' settings dict from loaded config, or empty dict if missing
                    facial_settings = self.settings.get('facial_detector', {})

                    # --- Pass ALL relevant settings from config to FacialDetector ---
                    # The FacialDetector __init__ will use its own defaults if a key is missing here
                    self.detectors['face'] = FacialDetector(
                        event_handler=self.handle_event, # Pass the engine's handler

                        # Pass settings found in config, otherwise FacialDetector uses its defaults
                        camera_index=facial_settings.get('camera_index', DEFAULT_CAMERA_INDEX),
                        ear_threshold=facial_settings.get('ear_threshold', DEFAULT_EAR_THRESHOLD),
                        mar_threshold=facial_settings.get('mar_threshold', DEFAULT_MAR_THRESHOLD),
                        err_threshold=facial_settings.get('err_threshold', DEFAULT_ERR_THRESHOLD),
                        both_eyes_closed_frames=facial_settings.get('both_eyes_closed_frames', DEFAULT_BOTH_EYES_CLOSED_FRAMES),
                        head_tilt_left_min=facial_settings.get('head_tilt_left_min', DEFAULT_HEAD_TILT_LEFT_MIN),
                        head_tilt_left_max=facial_settings.get('head_tilt_left_max', DEFAULT_HEAD_TILT_LEFT_MAX),
                        head_tilt_right_min=facial_settings.get('head_tilt_right_min', DEFAULT_HEAD_TILT_RIGHT_MIN),
                        head_tilt_right_max=facial_settings.get('head_tilt_right_max', DEFAULT_HEAD_TILT_RIGHT_MAX),
                        consec_frames_mouth=facial_settings.get('consec_frames_mouth', DEFAULT_CONSEC_FRAMES_MOUTH),
                        consec_frames_eyebrow=facial_settings.get('consec_frames_eyebrow', DEFAULT_CONSEC_FRAMES_EYEBROW),
                        consec_frames_head_tilt=facial_settings.get('consec_frames_head_tilt', DEFAULT_CONSEC_FRAMES_HEAD_TILT),
                        blink_cooldown=facial_settings.get('blink_cooldown', DEFAULT_BLINK_COOLDOWN),
                        show_video=facial_settings.get('show_video', False) # Allow config to enable debug video
                    )
                except Exception as e:
                     print(f"ERROR: Failed to initialize FacialDetector: {e}")
                     traceback.print_exc()
            else:
                # This path should ideally not be reached if imports are correct
                print("ERROR: FacialDetector class not available despite bindings needing it.")
        else:
             print("Engine: No facial bindings found, FacialDetector not initialized.")

        print(f"Engine: Initialized active detectors: {list(self.detectors.keys())}")


    def handle_event(self, detector_type, event_data):
        """ Handles events from detectors and triggers actions based on config bindings. """
        if not self.is_running: return

        print(f"Engine: Event received - Type: '{detector_type}', Data: '{event_data}'")
        event_key = str(event_data).lower() # Lowercase event name for matching
        action_id_to_execute = None

        # Find matching binding
        for binding in self.bindings:
            # Match type and lowercase trigger_event from config
            if binding.get("trigger_type") == detector_type and \
               str(binding.get("trigger_event", "")).lower() == event_key:
                action_id_to_execute = binding.get("action_id")
                if action_id_to_execute:
                    print(f"Engine: Found binding -> Action ID '{action_id_to_execute}'")
                    break
                else:
                    print(f"WARN: Binding found for '{event_key}', but 'action_id' missing.")

        # Execute action
        if action_id_to_execute:
            action_func = get_action_function(action_id_to_execute) # Get func from registry
            if action_func:
                try:
                    print(f"Engine: Executing action '{action_id_to_execute}'...")
                    action_func() # Execute the action
                except Exception as e:
                    print(f"ERROR: executing action '{action_id_to_execute}': {e}")
                    traceback.print_exc()
            else:
                print(f"WARN: Action ID '{action_id_to_execute}' (from config) not found in action registry!")


    def start(self):
        """ Starts all initialized detectors. """
        if self.is_running: print("Engine: Already running."); return
        print("--- Engine Starting Detectors ---"); self.is_running = True
        if not self.detectors: print("Engine: No detectors to start."); return
        start_count = 0
        for dtype, det_instance in self.detectors.items():
            try:
                print(f"Engine: Starting {dtype} detector..."); det_instance.start(); start_count += 1
            except Exception as e: print(f"ERROR: Start {dtype} detector failed: {e}"); traceback.print_exc()
        print(f"Engine: Started {start_count}/{len(self.detectors)} detectors.")

    def stop(self):
        """ Stops all initialized detectors. """
        if not self.detectors and not self.is_running: print("Engine: Already stopped/no detectors."); return
        if not self.is_running and self.detectors: print("Engine: Was not marked as running, attempting stop...");
        elif not self.is_running: print("Engine: Already stopped."); return

        print("--- Engine Stopping Detectors ---"); self.is_running = False
        stop_count = 0
        for dtype, det_instance in self.detectors.items():
            try:
                if callable(getattr(det_instance, "stop", None)):
                    print(f"Engine: Stopping {dtype} detector..."); det_instance.stop(); stop_count += 1
                else: print(f"WARN: Detector '{dtype}' has no stop() method.")
            except Exception as e: print(f"ERROR: Stop {dtype} detector failed: {e}"); traceback.print_exc()
        print(f"Engine: Stopped {stop_count}/{len(self.detectors)} detectors.")

    def reload_configuration(self):
        """ Reloads configuration and restarts detectors. """
        print("--- Engine Reloading Configuration ---"); self.stop()
        # time.sleep(0.2) # Optional delay
        self._load_configuration(); self._initialize_detectors(); self.start()
        print("--- Engine Reload Complete ---")

# --- Integration Test Block ---
if __name__ == '__main__':
    if not _imports_ok: print("Exiting due to import errors."); sys.exit(1)
    print("--- Running Engine Directly (Integration Test) ---")

    current_script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_script_dir))
    config_file_path = os.path.join(project_root, "config.json")
    print(f"Using config file: {config_file_path}")
    if not os.path.exists(config_file_path): print(f"ERROR: Config file not found!"); sys.exit(1)

    # Create the Engine - it will now initialize both detectors if bindings exist
    engine = Engine(config_path=config_file_path)
    engine.start() # This starts both detector threads

    if not engine.detectors: print("\nWARN: No detectors initialized. Check config.")
    else: print(f"\nEngine running with detectors: {list(engine.detectors.keys())}")
    print("Perform configured actions (voice/face). Press Ctrl+C to stop.")

    try:
        while True: time.sleep(1) # Keep alive
    except KeyboardInterrupt: print("\nCtrl+C detected. Stopping engine...")
    except Exception as main_e: print(f"\nERROR in main test loop: {main_e}"); traceback.print_exc()
    finally: engine.stop(); print("--- Engine Test Finished ---")