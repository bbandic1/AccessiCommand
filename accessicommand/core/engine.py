# accessicommand/detectors/facial_detector.py
import cv2
import mediapipe as mp
import time
import math
# REMOVED: import threading
import traceback

# --- MediaPipe Setup ---
mp_face_mesh = mp.solutions.face_mesh
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles

# --- Default Configuration Constants ---
DEFAULT_EAR_THRESHOLD = 0.20
DEFAULT_MAR_THRESHOLD = 0.35
DEFAULT_ERR_THRESHOLD = 1.34
DEFAULT_BOTH_EYES_CLOSED_FRAMES = 2
DEFAULT_HEAD_TILT_LEFT_MIN = -100
DEFAULT_HEAD_TILT_LEFT_MAX = -160
DEFAULT_HEAD_TILT_RIGHT_MIN = 100
DEFAULT_HEAD_TILT_RIGHT_MAX = 160
DEFAULT_CONSEC_FRAMES_BLINK = 2
DEFAULT_CONSEC_FRAMES_MOUTH = 3
DEFAULT_CONSEC_FRAMES_EYEBROW = 3
DEFAULT_CONSEC_FRAMES_HEAD_TILT = 2
DEFAULT_BLINK_COOLDOWN = 0.3

# --- Event Name Constants ---
LEFT_BLINK_EVENT = "LEFT_BLINK"; RIGHT_BLINK_EVENT = "RIGHT_BLINK"
MOUTH_OPEN_START_EVENT = "MOUTH_OPEN_START"; MOUTH_OPEN_STOP_EVENT = "MOUTH_OPEN_STOP"
BOTH_EYES_CLOSED_START_EVENT = "BOTH_EYES_CLOSED_START"; BOTH_EYES_CLOSED_STOP_EVENT = "BOTH_EYES_CLOSED_STOP"
EYEBROWS_RAISED_START_EVENT = "EYEBROWS_RAISED_START"; EYEBROWS_RAISED_STOP_EVENT = "EYEBROWS_RAISED_STOP"
HEAD_TILT_LEFT_START_EVENT = "HEAD_TILT_LEFT_START"; HEAD_TILT_LEFT_STOP_EVENT = "HEAD_TILT_LEFT_STOP"
HEAD_TILT_RIGHT_START_EVENT = "HEAD_TILT_RIGHT_START"; HEAD_TILT_RIGHT_STOP_EVENT = "HEAD_TILT_RIGHT_STOP"


class FacialDetector:
    """ Detects facial gestures from a provided frame and emits events. """

    # --- Landmark Indices ---
    LEFT_EYE_INDICES = [362, 385, 387, 263, 373, 380]; RIGHT_EYE_INDICES = [33, 160, 158, 133, 153, 144]
    MOUTH_CORNER_INDICES = [61, 291]; MOUTH_VERTICAL_INDICES = [13, 14]
    LEFT_EYEBROW_INDICES = [70, 63, 105, 66, 107]; RIGHT_EYEBROW_INDICES = [336, 296, 334, 293, 300]
    CHIN_INDEX = 152; FOREHEAD_INDEX = 10
    LANDMARKS_TO_DRAW = LEFT_EYE_INDICES + RIGHT_EYE_INDICES + MOUTH_CORNER_INDICES + MOUTH_VERTICAL_INDICES + LEFT_EYEBROW_INDICES + RIGHT_EYEBROW_INDICES

    def __init__(self, event_handler,
                 ear_threshold=DEFAULT_EAR_THRESHOLD,
                 mar_threshold=DEFAULT_MAR_THRESHOLD,
                 err_threshold=DEFAULT_ERR_THRESHOLD,
                 both_eyes_closed_frames=DEFAULT_BOTH_EYES_CLOSED_FRAMES,
                 head_tilt_left_min=DEFAULT_HEAD_TILT_LEFT_MIN,
                 head_tilt_left_max=DEFAULT_HEAD_TILT_LEFT_MAX,
                 head_tilt_right_min=DEFAULT_HEAD_TILT_RIGHT_MIN,
                 head_tilt_right_max=DEFAULT_HEAD_TILT_RIGHT_MAX,
                 consec_frames_blink=DEFAULT_CONSEC_FRAMES_BLINK,
                 consec_frames_mouth=DEFAULT_CONSEC_FRAMES_MOUTH,
                 consec_frames_eyebrow=DEFAULT_CONSEC_FRAMES_EYEBROW,
                 consec_frames_head_tilt=DEFAULT_CONSEC_FRAMES_HEAD_TILT,
                 blink_cooldown=DEFAULT_BLINK_COOLDOWN
                 # REMOVED: camera_index, show_video (Engine handles visualization/camera)
                ):
        self.event_handler = event_handler if callable(event_handler) else self._default_handler
        if not callable(event_handler): print("WARN: No valid event_handler provided to FacialDetector.")

        # Store Configuration
        self.ear_threshold = ear_threshold; self.mar_threshold = mar_threshold; self.err_threshold = err_threshold
        self.both_eyes_closed_frames = both_eyes_closed_frames
        self.head_tilt_left_min = head_tilt_left_min; self.head_tilt_left_max = head_tilt_left_max
        self.head_tilt_right_min = head_tilt_right_min; self.head_tilt_right_max = head_tilt_right_max
        self.consec_frames_blink = consec_frames_blink; self.consec_frames_mouth = consec_frames_mouth
        self.consec_frames_eyebrow = consec_frames_eyebrow; self.consec_frames_head_tilt = consec_frames_head_tilt
        self.blink_cooldown = blink_cooldown

        # MediaPipe Initialization
        self.face_mesh = None # Initialized in start()

        # State Variables
        self.is_active = False # Flag if detector processing is enabled
        self._reset_states()

        print("--- Facial Detector Initialized (Configured) ---")

    def _reset_states(self):
        """Resets internal states."""
        self._prev_mouth_open_state = False; self._prev_eyebrows_raised_state = False
        self._prev_head_tilt_left_state = False; self._prev_head_tilt_right_state = False
        self._prev_both_eyes_closed_state = False; self._left_eye_previously_closed = False
        self._right_eye_previously_closed = False; self._last_left_blink_time = 0
        self._last_right_blink_time = 0; self._mouth_open_counter = 0
        self._eyebrow_raise_counter = 0; self._head_tilt_left_counter = 0
        self._head_tilt_right_counter = 0; self._both_eyes_closed_counter = 0
        self._left_blink_counter = 0; self._right_blink_counter = 0

    def _default_handler(self, detector_type, event_data): pass

    # --- Calculation Methods (Keep as is) ---
    def _calculate_distance(self, p1, p2): return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2 + (p1.z - p2.z)**2)
    def _calculate_ear(self, eye_landmarks):
        try: v1=self._calculate_distance(eye_landmarks[1], eye_landmarks[5]); v2=self._calculate_distance(eye_landmarks[2], eye_landmarks[4]); h=self._calculate_distance(eye_landmarks[0], eye_landmarks[3]); return (v1 + v2) / (2.0 * h) if h!=0 else 1.0
        except IndexError: return 1.0
    def _calculate_mar(self, landmarks):
        try: ml=landmarks[self.MOUTH_CORNER_INDICES[0]]; mr=landmarks[self.MOUTH_CORNER_INDICES[1]]; lu=landmarks[self.MOUTH_VERTICAL_INDICES[0]]; ll=landmarks[self.MOUTH_VERTICAL_INDICES[1]]; vd=self._calculate_distance(lu,ll); hd=self._calculate_distance(ml,mr); return vd/hd if hd!=0 else 0.0
        except IndexError: return 0.0
    def _calculate_err(self, landmarks, eyebrow_indices, eye_indices):
         try: bm=landmarks[eyebrow_indices[2]]; bo=landmarks[eyebrow_indices[4]]; et=landmarks[eye_indices[1]]; vd=abs(bm.y - et.y); hd=self._calculate_distance(bm,bo); return vd/hd if hd!=0 else 0.0
         except IndexError: return 0.0
    def _calculate_head_tilt(self, landmarks, frame_width, frame_height): # Keep pixel version
        try:
            chin=landmarks[self.CHIN_INDEX]; fh=landmarks[self.FOREHEAD_INDEX]
            cx, cy = int(chin.x*frame_width), int(chin.y*frame_height); fx, fy = int(fh.x*frame_width), int(fh.y*frame_height)
            dx=fx-cx; dy=fy-cy
            if dy == 0: return 90.0 if dx>0 else -90.0 if dx<0 else 0.0
            return math.degrees(math.atan2(dx, dy))
        except IndexError: return 0.0

# --- NEW: Process Frame Method ---
    def process_frame(self, frame, frame_timestamp):
        """Processes a single frame to detect gestures and emit events."""
        if not self.is_active or self.face_mesh is None:
            return None

        frame_height, frame_width, _ = frame.shape
        frame.flags.writeable = False
        results = self.face_mesh.process(frame) # Process the RGB frame passed in
        frame.flags.writeable = True

        # Defaults for this frame
        ear_left_val, ear_right_val = 1.0, 1.0
        mar_val, avg_err, head_tilt_angle = 0.0, 0.0, 0.0
        current_time = frame_timestamp
        # --- Get the raw landmark object if available ---
        face_landmarks_object = results.multi_face_landmarks[0] if results.multi_face_landmarks else None
        landmarks = face_landmarks_object.landmark if face_landmarks_object else None
        # ------------------------------------------------

        # Local state vars
        left_eye_closed_state, right_eye_closed_state = False, False
        mouth_open_state, eyebrows_raised_state = False, False
        head_tilt_left_state, head_tilt_right_state = False, False
        both_eyes_closed_state = False
        left_eye_blinked, right_eye_blinked = False, False

        if landmarks: # Proceed only if landmarks were extracted
            # Calculations using the 'landmarks' list
            person_left_eye_points = [landmarks[i] for i in self.LEFT_EYE_INDICES]
            person_right_eye_points = [landmarks[i] for i in self.RIGHT_EYE_INDICES]
            ear_left_val = self._calculate_ear(person_left_eye_points)
            ear_right_val = self._calculate_ear(person_right_eye_points)
            mar_val = self._calculate_mar(landmarks)
            err_left = self._calculate_err(landmarks, self.LEFT_EYEBROW_INDICES, self.LEFT_EYE_INDICES)
            err_right = self._calculate_err(landmarks, self.RIGHT_EYEBROW_INDICES, self.RIGHT_EYE_INDICES)
            avg_err = (err_left + err_right) / 2.0
            head_tilt_angle = self._calculate_head_tilt(landmarks, frame_width, frame_height)

            # State Update & Event Emission logic (keep as is)
            # ... (all the if/else blocks for blinks, mouth, eyes, brows, tilt) ...
            is_left_closed_now = ear_right_val < self.ear_threshold
            if is_left_closed_now: self._left_blink_counter += 1; 
            else: self._left_blink_counter = 0
            left_eye_closed_state = self._left_blink_counter >= self.consec_frames_blink
            if left_eye_closed_state and not self._left_eye_previously_closed and current_time - self._last_left_blink_time > self.blink_cooldown and not is_right_closed_now: left_eye_blinked = True; self._last_left_blink_time = current_time
            self._left_eye_previously_closed = is_left_closed_now

            is_right_closed_now = ear_left_val < self.ear_threshold
            if is_right_closed_now: self._right_blink_counter += 1; 
            else: self._right_blink_counter = 0
            right_eye_closed_state = self._right_blink_counter >= self.consec_frames_blink
            if right_eye_closed_state and not self._right_eye_previously_closed and current_time - self._last_right_blink_time > self.blink_cooldown and not is_left_closed_now: right_eye_blinked = True; self._last_right_blink_time = current_time
            self._right_eye_previously_closed = is_right_closed_now

            is_mouth_open_now = mar_val > self.mar_threshold
            if is_mouth_open_now: self._mouth_open_counter = min(self.consec_frames_mouth, self._mouth_open_counter + 1); 
            else: self._mouth_open_counter = max(0, self._mouth_open_counter - 1)
            mouth_open_state = self._mouth_open_counter >= self.consec_frames_mouth

            are_both_eyes_closed_now = is_left_closed_now and is_right_closed_now
            if are_both_eyes_closed_now: self._both_eyes_closed_counter = min(self.both_eyes_closed_frames, self._both_eyes_closed_counter + 1); 
            else: self._both_eyes_closed_counter = max(0, self._both_eyes_closed_counter - 1)
            both_eyes_closed_state = self._both_eyes_closed_counter >= self.both_eyes_closed_frames

            are_eyebrows_raised_now = avg_err > self.err_threshold
            if are_eyebrows_raised_now: self._eyebrow_raise_counter = min(self.consec_frames_eyebrow, self._eyebrow_raise_counter + 1); 
            else: self._eyebrow_raise_counter = max(0, self._eyebrow_raise_counter - 1)
            eyebrows_raised_state = self._eyebrow_raise_counter >= self.consec_frames_eyebrow

            is_tilt_left_now = self.head_tilt_left_min >= head_tilt_angle >= self.head_tilt_left_max
            is_tilt_right_now = self.head_tilt_right_min <= head_tilt_angle <= self.head_tilt_right_max
            if is_tilt_left_now: self._head_tilt_left_counter = min(self.consec_frames_head_tilt, self._head_tilt_left_counter + 1); self._head_tilt_right_counter = 0
            elif is_tilt_right_now: self._head_tilt_right_counter = min(self.consec_frames_head_tilt, self._head_tilt_right_counter + 1); self._head_tilt_left_counter = 0
            else: self._head_tilt_left_counter = max(0, self._head_tilt_left_counter - 1); self._head_tilt_right_counter = max(0, self._head_tilt_right_counter - 1)
            head_tilt_left_state = self._head_tilt_left_counter >= self.consec_frames_head_tilt
            head_tilt_right_state = self._head_tilt_right_counter >= self.consec_frames_head_tilt


        # --- Event Emission (keep as is) ---
        if left_eye_blinked and not right_eye_blinked: self.event_handler("face", LEFT_BLINK_EVENT)
        if right_eye_blinked and not left_eye_blinked: self.event_handler("face", RIGHT_BLINK_EVENT)
        if mouth_open_state != self._prev_mouth_open_state: self.event_handler("face", MOUTH_OPEN_START_EVENT if mouth_open_state else MOUTH_OPEN_STOP_EVENT); self._prev_mouth_open_state = mouth_open_state
        if both_eyes_closed_state != self._prev_both_eyes_closed_state: self.event_handler("face", BOTH_EYES_CLOSED_START_EVENT if both_eyes_closed_state else BOTH_EYES_CLOSED_STOP_EVENT); self._prev_both_eyes_closed_state = both_eyes_closed_state
        if eyebrows_raised_state != self._prev_eyebrows_raised_state: self.event_handler("face", EYEBROWS_RAISED_START_EVENT if eyebrows_raised_state else EYEBROWS_RAISED_STOP_EVENT); self._prev_eyebrows_raised_state = eyebrows_raised_state
        if head_tilt_left_state != self._prev_head_tilt_left_state: self.event_handler("face", HEAD_TILT_LEFT_START_EVENT if head_tilt_left_state else HEAD_TILT_LEFT_STOP_EVENT); self._prev_head_tilt_left_state = head_tilt_left_state
        if head_tilt_right_state != self._prev_head_tilt_right_state: self.event_handler("face", HEAD_TILT_RIGHT_START_EVENT if head_tilt_right_state else HEAD_TILT_RIGHT_STOP_EVENT); self._prev_head_tilt_right_state = head_tilt_right_state


        # --- Return data needed for visualization by Engine ---
        vis_data = {
            # --- Return the parent object needed for drawing ---
            "landmark_object": face_landmarks_object,
            # ---------------------------------------------------
            "states": { # Send current calculated states
                "left_eye_closed": left_eye_closed_state, "right_eye_closed": right_eye_closed_state,
                "mouth_open": mouth_open_state, "eyebrows_raised": eyebrows_raised_state,
                "head_tilt_left": head_tilt_left_state, "head_tilt_right": head_tilt_right_state,
                "both_eyes_closed": both_eyes_closed_state,
            },
            "values": { # Send calculated values
                "ear_left": ear_left_val, "ear_right": ear_right_val, "mar": mar_val,
                "avg_err": avg_err, "head_tilt_angle": head_tilt_angle,
            }
        }
        return vis_data


    def start(self):
        """Initializes MediaPipe models."""
        if self.is_active: print("Facial Detector: Already active."); return
        print("Facial Detector: Initializing MediaPipe FaceMesh...")
        try:
            # Initialize face mesh here instead of __init__
            self.face_mesh = mp_face_mesh.FaceMesh(
                max_num_faces=1, refine_landmarks=True,
                min_detection_confidence=0.5, min_tracking_confidence=0.5
            )
            self._reset_states() # Reset states when starting
            self.is_active = True
            print("Facial Detector: Started (ready to process frames).")
        except Exception as e:
            print(f"ERROR: Failed to initialize MediaPipe FaceMesh: {e}")
            self.face_mesh = None # Ensure it's None if init fails
            self.is_active = False

    def stop(self):
        """Releases MediaPipe resources."""
        if not self.is_active: print("Facial Detector: Already stopped."); return
        print("Facial Detector: Stopping...")
        self.is_active = False
        if hasattr(self.face_mesh, 'close'):
             try: self.face_mesh.close()
             except Exception as e: print(f"Error closing face_mesh: {e}")
        self.face_mesh = None # Release reference
        print("Facial Detector: Stopped.")