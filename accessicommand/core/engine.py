# accessicommand/core/engine.py
import sys
import os
import traceback
import time
import threading
import cv2
import mediapipe as mp

# Initialize MediaPipe drawing utilities
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles
mp_hands = mp.solutions.hands
mp_face_mesh = mp.solutions.face_mesh

# Absolute Imports
try:
    from accessicommand.config.manager import ConfigManager
    from accessicommand.detectors.voice_detector import VoiceDetector
    from accessicommand.detectors.facial_detector import FacialDetector
    from accessicommand.detectors.hand_detector import HandDetector
    from accessicommand.actions.registry import get_action_function, ACTION_REGISTRY
    _imports_ok = True
except ImportError as e: print(f"ERROR: Import failed: {e}"); sys.exit(1)

# Engine Default Constants
DEFAULT_VOICE_PAUSE_THRESHOLD = 0.4; DEFAULT_VOICE_ENERGY_THRESHOLD = 350
DEFAULT_CAMERA_INDEX = 0; DEFAULT_EAR_THRESHOLD = 0.20; DEFAULT_MAR_THRESHOLD = 0.35
DEFAULT_ERR_THRESHOLD = 1.34; DEFAULT_BOTH_EYES_CLOSED_FRAMES = 2
DEFAULT_HEAD_TILT_LEFT_MIN = -100; DEFAULT_HEAD_TILT_LEFT_MAX = -160
DEFAULT_HEAD_TILT_RIGHT_MIN = 100; DEFAULT_HEAD_TILT_RIGHT_MAX = 160
DEFAULT_CONSEC_FRAMES_MOUTH = 3; DEFAULT_CONSEC_FRAMES_EYEBROW = 3
DEFAULT_CONSEC_FRAMES_HEAD_TILT = 2; DEFAULT_BLINK_COOLDOWN = 0.3
DEFAULT_CONSEC_FRAMES_BLINK = 2
DEFAULT_HAND_CAMERA_INDEX = 0; DEFAULT_MAX_HANDS = 1
DEFAULT_DETECTION_CONFIDENCE = 0.7; DEFAULT_TRACKING_CONFIDENCE = 0.5
DEFAULT_CONSEC_FRAMES_FOR_GESTURE = 5
DEFAULT_SHOW_FACE_VIDEO = False; DEFAULT_SHOW_HAND_VIDEO = False

class Engine:
    """ Core engine managing detectors, config, events, and actions. """
    def __init__(self, config_path="config.json"):
        print("--- Engine Initializing ---")
        self.config_manager = ConfigManager(config_path)
        self.detectors = {}
        self.bindings = []
        self.settings = {}
        self.is_running = False
        self.main_loop_thread = None
        self.capture_devices = {}
        self.visual_detectors_by_cam = {}
        self.show_combined_video = False
        self.vis_settings = {}

        self._load_configuration()
        self._initialize_actions()
        self._initialize_detectors()
        print("--- Engine Initialized ---")

    def _load_configuration(self):
        print(f"Engine: Loading configuration from '{self.config_manager.config_path}'...")
        try:
            self.config_data = self.config_manager.get_config()
            self.bindings = self.config_manager.get_bindings()
            self.settings = self.config_manager.get_settings()
            facial_settings = self.settings.get('facial_detector', {})
            hand_settings = self.settings.get('hand_detector', {})
            self.vis_settings['show_face'] = facial_settings.get('show_video', DEFAULT_SHOW_FACE_VIDEO)
            self.vis_settings['show_hand'] = hand_settings.get('show_video', DEFAULT_SHOW_HAND_VIDEO)
            self.show_combined_video = self.vis_settings['show_face'] or self.vis_settings['show_hand']
            print(f"Engine: Loaded {len(self.bindings)} bindings.")
        except Exception as e:
            print(f"ERROR loading config: {e}"); traceback.print_exc()
            self.bindings=[]; self.settings={}

    def _initialize_actions(self):
        if not callable(get_action_function):
            print("ERROR: get_action_function unavailable!")
        else:
            print(f"Engine: Action registry OK ({len(ACTION_REGISTRY)} actions).")

    def _initialize_detectors(self):
        print("Engine: Initializing detectors...")
        self.detectors = {}
        self.visual_detectors_by_cam = {}

        # Voice Detector
        voice_triggers_needed = any(b.get("trigger_type") == "voice" for b in self.bindings)
        if voice_triggers_needed:
            try:
                print("Engine: Initializing VoiceDetector...")
                voice_settings = self.settings.get('voice_detector', {})
                self.detectors['voice'] = VoiceDetector(
                    trigger_words=list(set(str(b.get("trigger_event")).lower() for b in self.bindings if b.get("trigger_type") == "voice" and b.get("trigger_event"))),
                    event_handler=self.handle_event,
                    energy_threshold=voice_settings.get('energy_threshold', DEFAULT_VOICE_ENERGY_THRESHOLD),
                    pause_threshold=voice_settings.get('pause_threshold', DEFAULT_VOICE_PAUSE_THRESHOLD),
                )
            except Exception as e: print(f"ERROR init VoiceDetector failed: {e}"); traceback.print_exc()
        else: print("Engine: No voice bindings found.")

        # Visual Detectors
        visual_detector_configs = {
            'face': {'class': FacialDetector, 'settings_key': 'facial_detector', 'defaults': {
                'ear_threshold': DEFAULT_EAR_THRESHOLD, 'mar_threshold': DEFAULT_MAR_THRESHOLD,
                'err_threshold': DEFAULT_ERR_THRESHOLD, 'both_eyes_closed_frames': DEFAULT_BOTH_EYES_CLOSED_FRAMES,
                'head_tilt_left_min': DEFAULT_HEAD_TILT_LEFT_MIN, 'head_tilt_left_max': DEFAULT_HEAD_TILT_LEFT_MAX,
                'head_tilt_right_min': DEFAULT_HEAD_TILT_RIGHT_MIN, 'head_tilt_right_max': DEFAULT_HEAD_TILT_RIGHT_MAX,
                'consec_frames_blink': DEFAULT_CONSEC_FRAMES_BLINK,
                'consec_frames_mouth': DEFAULT_CONSEC_FRAMES_MOUTH,
                'consec_frames_eyebrow': DEFAULT_CONSEC_FRAMES_EYEBROW, 'consec_frames_head_tilt': DEFAULT_CONSEC_FRAMES_HEAD_TILT,
                'blink_cooldown': DEFAULT_BLINK_COOLDOWN
            }},
            'hand': {'class': HandDetector, 'settings_key': 'hand_detector', 'defaults': {
                'max_num_hands': DEFAULT_MAX_HANDS,
                'min_detection_confidence': DEFAULT_DETECTION_CONFIDENCE, 'min_tracking_confidence': DEFAULT_TRACKING_CONFIDENCE,
                'consec_frames_for_gesture': DEFAULT_CONSEC_FRAMES_FOR_GESTURE
            }}
        }
        default_face_cam_idx = DEFAULT_CAMERA_INDEX
        default_hand_cam_idx = DEFAULT_HAND_CAMERA_INDEX

        for det_type, config_info in visual_detector_configs.items():
            needs_init = any(b.get("trigger_type") == det_type for b in self.bindings)
            if needs_init:
                DetectorClass = config_info['class']
                if DetectorClass is None or not _imports_ok:
                    print(f"WARN: Cannot initialize {det_type} detector - class missing or import failed.")
                    continue

                try:
                    print(f"Engine: Initializing {DetectorClass.__name__}...")
                    settings = self.settings.get(config_info['settings_key'], {})
                    init_kwargs = config_info['defaults'].copy()
                    default_cam = default_face_cam_idx if det_type == 'face' else default_hand_cam_idx
                    cam_index = settings.get('camera_index', default_cam)
                    for key in list(init_kwargs.keys()):
                        if key in settings:
                            init_kwargs[key] = settings[key]
                    # Ensure these args expected by Engine but not Detector are removed
                    init_kwargs.pop('camera_index', None)
                    init_kwargs.pop('show_video', None)

                    detector_instance = DetectorClass(event_handler=self.handle_event, **init_kwargs)
                    self.detectors[det_type] = detector_instance

                    if cam_index not in self.visual_detectors_by_cam:
                        self.visual_detectors_by_cam[cam_index] = []
                    self.visual_detectors_by_cam[cam_index].append(detector_instance)
                    print(f"   - Added {DetectorClass.__name__} to camera index {cam_index}")

                except Exception as e: print(f"ERROR: Init {DetectorClass.__name__} failed: {e}"); traceback.print_exc()
            else:
                print(f"Engine: No {det_type} bindings found, {config_info['class'].__name__} not initialized.")

        print(f"Engine: Initialized active detectors: {list(self.detectors.keys())}")
        print(f"Engine: Camera mapping: { {k: [d.__class__.__name__ for d in v] for k, v in self.visual_detectors_by_cam.items()} }")

    def handle_event(self, detector_type, event_data):
        if not self.is_running: return
        print(f"Engine: Event received - Type: '{detector_type}', Data: '{event_data}'")
        event_key = str(event_data).lower(); action_id_to_execute = None
        for binding in self.bindings:
            if binding.get("trigger_type") == detector_type and str(binding.get("trigger_event", "")).lower() == event_key:
                action_id_to_execute = binding.get("action_id")
                if action_id_to_execute: print(f"Engine: Found binding -> Action ID '{action_id_to_execute}'"); break
                else: print(f"WARN: Binding found for '{event_key}', but 'action_id' missing.")
        if action_id_to_execute:
            action_func = get_action_function(action_id_to_execute)
            if action_func:
                try: print(f"Engine: Executing action '{action_id_to_execute}'..."); action_func()
                except Exception as e: print(f"ERROR: executing action '{action_id_to_execute}': {e}"); traceback.print_exc()
            else: print(f"WARN: Action ID '{action_id_to_execute}' not in registry!")

    def _run_main_loop(self):
        print("Engine: Starting main processing loop...")
        active_captures = {}
        try:
            for cam_index in self.visual_detectors_by_cam.keys():
                print(f"Engine: Initializing camera {cam_index}...")
                cap = cv2.VideoCapture(cam_index); time.sleep(0.5)
                if not cap.isOpened(): print(f"ERROR: Cannot open camera {cam_index}!"); continue
                active_captures[cam_index] = cap; print(f"Engine: Camera {cam_index} opened.")
            if not active_captures: print("ERROR: No cameras opened."); self.is_running = False; return

            frame_width, frame_height = {}, {}

            while self.is_running:
                frames = {}; timestamps = {}

                # Read frames
                for cam_index, cap in active_captures.items():
                    if not cap.isOpened(): frames[cam_index]=None; continue
                    ret, frame = cap.read()
                    if not ret: print(f"WARN: Frame grab fail cam {cam_index}."); frames[cam_index]=None; continue
                    if cam_index not in frame_width: frame_height[cam_index], frame_width[cam_index], _ = frame.shape
                    frames[cam_index] = frame; timestamps[cam_index] = time.time()

                # Process frames
                vis_results = {}
                for cam_index, frame in frames.items():
                    if frame is None: continue
                    frame_flipped = cv2.flip(frame, 1)
                    rgb_frame = cv2.cvtColor(frame_flipped, cv2.COLOR_BGR2RGB)
                    vis_results[cam_index] = {}
                    for detector in self.visual_detectors_by_cam.get(cam_index, []):
                        detector_type = next((k for k, v in self.detectors.items() if v == detector), None)
                        if detector_type and detector.is_active:
                            try:
                                vis_data = detector.process_frame(rgb_frame, timestamps[cam_index])
                                if vis_data: vis_results[cam_index][detector_type] = vis_data
                            except Exception as process_e: print(f"ERROR: Processing frame with {detector_type} failed: {process_e}"); traceback.print_exc()

 # Visualization
                if self.show_combined_video:
                    # ... (keep the setup code for display_frame etc.) ...
                    display_frame = None; display_cam_index = next(iter(active_captures.keys()), None)
                    if display_cam_index is not None and frames.get(display_cam_index) is not None:
                        display_frame = cv2.flip(frames[display_cam_index].copy(), 1) # Use flipped frame
                        h, w, _ = display_frame.shape

                        # Draw Face Results
                        if self.vis_settings.get('show_face') and 'face' in vis_results.get(display_cam_index, {}):
                            face_vis = vis_results[display_cam_index]['face']
                            # --- Use the landmark_object returned by the detector ---
                            landmark_drawing_object = face_vis.get('landmark_object')
                            if landmark_drawing_object: # Check if the object exists
                                mp_drawing.draw_landmarks(
                                    image=display_frame,
                                    landmark_list=landmark_drawing_object, # Pass the correct object
                                    connections=mp_face_mesh.FACEMESH_CONTOURS,
                                    landmark_drawing_spec=None,
                                    connection_drawing_spec=mp_drawing_styles.get_default_face_mesh_contours_style()
                                )
                            # ------------------------------------------------------
                            # Display text using states and values dictionaries
                            if face_vis: # Ensure face_vis itself is not None
                                f_states = face_vis.get('states', {}); f_vals = face_vis.get('values', {})
                                # Use .get() for values too, providing default if key missing
                                text = f"F|T:{f_vals.get('head_tilt_angle', 0.0):.0f} M:{f_vals.get('mar', 0.0):.2f} E:{f_vals.get('avg_err', 0.0):.2f}"
                                cv2.putText(display_frame, text, (10, h-40), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
                                f_active = [k.split('_')[0] for k,v in f_states.items() if v]; state_text = "Face: "+(",".join(f_active) if f_active else "None")
                                cv2.putText(display_frame, state_text, (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

                        # Draw Hand Results (keep as is, HandDetector returns correct format)
                        if self.vis_settings.get('show_hand') and 'hand' in vis_results.get(display_cam_index, {}):
                            hand_vis = vis_results[display_cam_index]['hand']
                            if hand_vis:
                                mp_drawing.draw_landmarks(image=display_frame, landmark_list=hand_vis,
                                     connections=mp_hands.HAND_CONNECTIONS, landmark_drawing_spec=None,
                                     connection_drawing_spec=mp_drawing_styles.get_default_hand_connections_style())
                            hand_det = self.detectors.get('hand')
                            if hand_det: stable_hand = hand_det._current_stable_gesture; cv2.putText(display_frame, f"Hand: {stable_hand}", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

                        # ... (keep the imshow, waitKey, except blocks as they were) ...
                        try: cv2.imshow('AccessiCommand Output', display_frame)
                        except cv2.error as cv_err: print(f"WARN: imshow error: {cv_err}"); self.show_combined_video = False

                    try: # Handle waitKey safely
                        key = cv2.waitKey(1) & 0xFF
                        if key == ord('q'): self.is_running = False; break
                    except cv2.error as key_err: print(f"WARN: waitKey error: {key_err}"); self.show_combined_video = False

                else: # if not self.show_combined_video
                    time.sleep(0.01) # Prevent CPU hog if no video shown

        except Exception as loop_e: print(f"ERROR in Engine main loop: {loop_e}"); traceback.print_exc()
        finally:
             print("Engine: Exiting main processing loop...");
             for cam_index, cap in active_captures.items():
                  if cap and cap.isOpened(): cap.release(); print(f"Engine: Camera {cam_index} released.")
             try: cv2.destroyAllWindows()
             except Exception: pass
             self.is_running = False


    def start(self):
        if self.is_running: print("Engine: Already running."); return
        print("--- Engine Starting ---"); self.is_running = True
        if 'voice' in self.detectors:
            try: print("Engine: Starting voice detector..."); self.detectors['voice'].start()
            except Exception as e: print(f"ERROR starting voice: {e}")
        if self.visual_detectors_by_cam:
             print("Engine: Activating visual detectors...")
             for detectors_list in self.visual_detectors_by_cam.values():
                  for detector in detectors_list:
                       if hasattr(detector, 'start') and callable(detector.start):
                           try: detector.start()
                           except Exception as e: print(f"ERROR starting {detector.__class__.__name__}: {e}")
             print("Engine: Starting main processing loop thread...")
             self.main_loop_thread = threading.Thread(target=self._run_main_loop, daemon=True)
             self.main_loop_thread.start()
        else: print("Engine: No visual detectors to start main loop.")
        print(f"Engine: Started with active detectors: {list(self.detectors.keys())}")

    def stop(self):
        if not self.is_running and not self.detectors: print("Engine: Already stopped/no detectors."); return
        print("--- Engine Stopping ---"); self.is_running = False
        if 'voice' in self.detectors and hasattr(self.detectors['voice'], 'stop'):
            try: print("Engine: Stopping voice detector..."); self.detectors['voice'].stop()
            except Exception as e: print(f"ERROR stopping voice: {e}")
        if self.main_loop_thread and self.main_loop_thread.is_alive():
            print("Engine: Waiting for main loop thread..."); self.main_loop_thread.join(timeout=2.0)
            if self.main_loop_thread.is_alive(): print("WARN: Main loop thread didn't stop.")
        self.main_loop_thread = None
        print("Engine: Stopping visual detector models...")
        stop_count = 0
        for dtype, det_instance in self.detectors.items():
             if dtype == 'voice': continue
             try:
                 if callable(getattr(det_instance, "stop", None)): det_instance.stop(); stop_count += 1
                 else: print(f"WARN: {dtype} has no stop().")
             except Exception as e: print(f"ERROR stopping {dtype}: {e}")
        print(f"Engine: Stopped {stop_count} visual models.")
        try: cv2.destroyAllWindows(); print("Engine: Closed OpenCV windows.")
        except Exception: pass
        self.capture_devices = {}
        print("Engine: Stop sequence complete.")


    def reload_configuration(self):
        print("--- Reloading Config ---"); self.stop()
        self._load_configuration(); self._initialize_detectors(); self.start()
        print("--- Reload Complete ---")

# --- Integration Test Block ---
if __name__ == '__main__':
    if not _imports_ok: print("Exiting: Import errors."); sys.exit(1)
    print("--- Running Engine Directly (Integration Test) ---")
    current_script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_script_dir))
    config_file_path = os.path.join(project_root, "config.json")
    print(f"Using config file: {config_file_path}")
    if not os.path.exists(config_file_path): print(f"ERROR: Config file not found!"); sys.exit(1)

    engine = Engine(config_path=config_file_path)
    engine.start()

    if not engine.detectors: print("\nWARN: No detectors initialized.")
    else: print(f"\nEngine running: {list(engine.detectors.keys())}. Perform actions...")
    print("Press Ctrl+C in terminal to stop.")
    try:
        # Keep main thread alive
        if engine.main_loop_thread:
             while engine.main_loop_thread.is_alive():
                 engine.main_loop_thread.join(timeout=0.5)
        else: # Keep alive for voice only if no visual loop started
             while engine.is_running: time.sleep(1)
    except KeyboardInterrupt: print("\nCtrl+C detected. Stopping engine...")
    except Exception as main_e: print(f"\nERROR in main test loop: {main_e}"); traceback.print_exc()
    finally: engine.stop(); print("--- Engine Test Finished ---")