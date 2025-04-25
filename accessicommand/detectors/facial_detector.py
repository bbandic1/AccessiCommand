# accessicommand/detectors/facial_detector.py
import cv2
import mediapipe as mp
import time
import math
import threading
import traceback

# --- MediaPipe Setup ---
mp_face_mesh = mp.solutions.face_mesh
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles

# --- Default Configuration Constants ---
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
DEFAULT_CONSEC_FRAMES_HEAD_TILT = 3 # Increased slightly for stability
DEFAULT_BLINK_COOLDOWN = 0.3

# --- Event Name Constants ---
# Momentary Events
LEFT_BLINK_EVENT = "LEFT_BLINK"
RIGHT_BLINK_EVENT = "RIGHT_BLINK"
# Sustained Events (Start/Stop pairs)
MOUTH_OPEN_START_EVENT = "MOUTH_OPEN_START"
MOUTH_OPEN_STOP_EVENT = "MOUTH_OPEN_STOP"
BOTH_EYES_CLOSED_START_EVENT = "BOTH_EYES_CLOSED_START"
BOTH_EYES_CLOSED_STOP_EVENT = "BOTH_EYES_CLOSED_STOP"
EYEBROWS_RAISED_START_EVENT = "EYEBROWS_RAISED_START"
EYEBROWS_RAISED_STOP_EVENT = "EYEBROWS_RAISED_STOP"
HEAD_TILT_LEFT_START_EVENT = "HEAD_TILT_LEFT_START"
HEAD_TILT_LEFT_STOP_EVENT = "HEAD_TILT_LEFT_STOP"
HEAD_TILT_RIGHT_START_EVENT = "HEAD_TILT_RIGHT_START"
HEAD_TILT_RIGHT_STOP_EVENT = "HEAD_TILT_RIGHT_STOP"


class FacialDetector:
    """
    Detects various facial gestures using MediaPipe Face Mesh and emits events
    via a provided handler function.
    """

    # --- Landmark Indices ---
    LEFT_EYE_INDICES = [362, 385, 387, 263, 373, 380]
    RIGHT_EYE_INDICES = [33, 160, 158, 133, 153, 144]
    MOUTH_CORNER_INDICES = [61, 291]
    MOUTH_VERTICAL_INDICES = [13, 14]
    LEFT_EYEBROW_INDICES = [70, 63, 105, 66, 107]
    RIGHT_EYEBROW_INDICES = [336, 296, 334, 293, 300]
    CHIN_INDEX = 152
    FOREHEAD_INDEX = 10
    LANDMARKS_TO_DRAW = LEFT_EYE_INDICES + RIGHT_EYE_INDICES + MOUTH_CORNER_INDICES + MOUTH_VERTICAL_INDICES + LEFT_EYEBROW_INDICES + RIGHT_EYEBROW_INDICES


    def __init__(self, event_handler,
                 camera_index=DEFAULT_CAMERA_INDEX,
                 ear_threshold=DEFAULT_EAR_THRESHOLD,
                 mar_threshold=DEFAULT_MAR_THRESHOLD,
                 err_threshold=DEFAULT_ERR_THRESHOLD,
                 both_eyes_closed_frames=DEFAULT_BOTH_EYES_CLOSED_FRAMES,
                 head_tilt_left_min=DEFAULT_HEAD_TILT_LEFT_MIN,
                 head_tilt_left_max=DEFAULT_HEAD_TILT_LEFT_MAX,
                 head_tilt_right_min=DEFAULT_HEAD_TILT_RIGHT_MIN,
                 head_tilt_right_max=DEFAULT_HEAD_TILT_RIGHT_MAX,
                 consec_frames_mouth=DEFAULT_CONSEC_FRAMES_MOUTH,
                 consec_frames_eyebrow=DEFAULT_CONSEC_FRAMES_EYEBROW,
                 consec_frames_head_tilt=DEFAULT_CONSEC_FRAMES_HEAD_TILT,
                 blink_cooldown=DEFAULT_BLINK_COOLDOWN,
                 show_video=False # Option to show the video feed for debugging
                ):
        self.event_handler = event_handler if callable(event_handler) else self._default_handler
        if not callable(event_handler):
            print("WARN: No valid event_handler provided to FacialDetector. Events will not be emitted.")

        # Store Configuration
        self.camera_index = camera_index
        self.ear_threshold = ear_threshold
        self.mar_threshold = mar_threshold
        self.err_threshold = err_threshold
        self.both_eyes_closed_frames = both_eyes_closed_frames
        self.head_tilt_left_min = head_tilt_left_min
        self.head_tilt_left_max = head_tilt_left_max
        self.head_tilt_right_min = head_tilt_right_min
        self.head_tilt_right_max = head_tilt_right_max
        self.consec_frames_mouth = consec_frames_mouth
        self.consec_frames_eyebrow = consec_frames_eyebrow
        self.consec_frames_head_tilt = consec_frames_head_tilt
        self.blink_cooldown = blink_cooldown
        self.show_video = show_video

        # MediaPipe and Camera Initialization
        self.face_mesh = mp_face_mesh.FaceMesh(
            max_num_faces=1, refine_landmarks=True,
            min_detection_confidence=0.5, min_tracking_confidence=0.5
        )
        self.cap = None

        # State Variables
        self.running = False
        self.thread = None
        self._reset_states() # Initialize states via helper method

        print("--- Facial Detector Initialized ---")

    def _reset_states(self):
        """Resets internal state variables, counters, and timers."""
        self._prev_mouth_open_state = False
        self._prev_eyebrows_raised_state = False
        self._prev_head_tilt_left_state = False
        self._prev_head_tilt_right_state = False
        self._prev_both_eyes_closed_state = False
        self._left_eye_previously_closed = False
        self._right_eye_previously_closed = False
        self._last_left_blink_time = 0
        self._last_right_blink_time = 0
        self._mouth_open_counter = 0
        self._eyebrow_raise_counter = 0
        self._head_tilt_left_counter = 0
        self._head_tilt_right_counter = 0
        self._both_eyes_closed_counter = 0
        print("Facial Detector: Internal states reset.")


    def _default_handler(self, detector_type, event_data):
        pass # No-op

    # --- Calculation Helper Methods ---
    def _calculate_distance(self, p1, p2):
        return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2 + (p1.z - p2.z)**2)

    def _calculate_ear(self, eye_landmarks):
        try:
            v1 = self._calculate_distance(eye_landmarks[1], eye_landmarks[5])
            v2 = self._calculate_distance(eye_landmarks[2], eye_landmarks[4])
            h = self._calculate_distance(eye_landmarks[0], eye_landmarks[3])
            return (v1 + v2) / (2.0 * h) if h != 0 else 1.0
        except IndexError: return 1.0

    def _calculate_mar(self, landmarks):
        try:
            mouth_left = landmarks[self.MOUTH_CORNER_INDICES[0]]
            mouth_right = landmarks[self.MOUTH_CORNER_INDICES[1]]
            lip_upper = landmarks[self.MOUTH_VERTICAL_INDICES[0]]
            lip_lower = landmarks[self.MOUTH_VERTICAL_INDICES[1]]
            vert_dist = self._calculate_distance(lip_upper, lip_lower)
            horz_dist = self._calculate_distance(mouth_left, mouth_right)
            return vert_dist / horz_dist if horz_dist != 0 else 0.0
        except IndexError: return 0.0

    def _calculate_err(self, landmarks, eyebrow_indices, eye_indices):
         try:
             brow_mid = landmarks[eyebrow_indices[2]]
             brow_outer = landmarks[eyebrow_indices[4]]
             eye_top = landmarks[eye_indices[1]]
             vert_dist = abs(brow_mid.y - eye_top.y)
             horz_dist = self._calculate_distance(brow_mid, brow_outer)
             return vert_dist / horz_dist if horz_dist != 0 else 0.0
         except IndexError: return 0.0

    def _calculate_head_tilt(self, landmarks):
        try:
            chin = landmarks[self.CHIN_INDEX]
            forehead = landmarks[self.FOREHEAD_INDEX]
            dx = forehead.x - chin.x
            dy = forehead.y - chin.y
            return math.degrees(math.atan2(dx, -dy))
        except IndexError: return 0.0

    # --- The Main Detection Loop ---
    def _run_detection_loop(self):
        print("Facial Detector: Background detection thread started.")
        frame_width, frame_height = 0, 0

        while self.running:
            if not self.cap or not self.cap.isOpened():
                print("ERROR: Camera not opened in detection loop.")
                time.sleep(1); continue

            ret, frame = self.cap.read()
            if not ret:
                print("WARN: Failed to grab frame from camera."); time.sleep(0.1); continue

            if frame_width == 0: frame_height, frame_width, _ = frame.shape
            frame = cv2.flip(frame, 1)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            rgb_frame.flags.writeable = False
            results = self.face_mesh.process(rgb_frame)

            # Defaults for this frame
            ear_left_val, ear_right_val = 1.0, 1.0
            mar_val, avg_err, head_tilt_angle = 0.0, 0.0, 0.0
            current_time = time.time()
            landmarks = results.multi_face_landmarks[0].landmark if results.multi_face_landmarks else None

            if landmarks:
                # Perform calculations only if landmarks exist
                person_left_eye_points = [landmarks[i] for i in self.LEFT_EYE_INDICES]
                person_right_eye_points = [landmarks[i] for i in self.RIGHT_EYE_INDICES]
                ear_left_val = self._calculate_ear(person_left_eye_points)   # Person L eye / Screen R
                ear_right_val = self._calculate_ear(person_right_eye_points) # Person R eye / Screen L
                mar_val = self._calculate_mar(landmarks)
                err_left = self._calculate_err(landmarks, self.LEFT_EYEBROW_INDICES, self.LEFT_EYE_INDICES)
                err_right = self._calculate_err(landmarks, self.RIGHT_EYEBROW_INDICES, self.RIGHT_EYE_INDICES)
                avg_err = (err_left + err_right) / 2.0
                head_tilt_angle = self._calculate_head_tilt(landmarks)

            # --- State Update & Event Emission (Always run to handle state changes to False) ---

            # --- Blinks (Momentary) ---
            is_left_closed_now = ear_right_val < self.ear_threshold # Person R eye / Screen L
            is_right_closed_now = ear_left_val < self.ear_threshold # Person L eye / Screen R

            if is_left_closed_now and not self._left_eye_previously_closed and \
               current_time - self._last_left_blink_time > self.blink_cooldown and not is_right_closed_now:
                self.event_handler("face", LEFT_BLINK_EVENT) # Person's Right Eye Blinked
                self._last_left_blink_time = current_time
            self._left_eye_previously_closed = is_left_closed_now

            if is_right_closed_now and not self._right_eye_previously_closed and \
               current_time - self._last_right_blink_time > self.blink_cooldown and not is_left_closed_now:
                self.event_handler("face", RIGHT_BLINK_EVENT) # Person's Left Eye Blinked
                self._last_right_blink_time = current_time
            self._right_eye_previously_closed = is_right_closed_now

            # --- Mouth Open (Sustained) ---
            is_mouth_open_now = mar_val > self.mar_threshold
            if is_mouth_open_now: self._mouth_open_counter = min(self.consec_frames_mouth, self._mouth_open_counter + 1)
            else: self._mouth_open_counter = max(0, self._mouth_open_counter - 1)
            mouth_open_state = self._mouth_open_counter >= self.consec_frames_mouth

            if mouth_open_state != self._prev_mouth_open_state:
                event = MOUTH_OPEN_START_EVENT if mouth_open_state else MOUTH_OPEN_STOP_EVENT
                self.event_handler("face", event)
                self._prev_mouth_open_state = mouth_open_state

            # --- Both Eyes Closed (Sustained) ---
            are_both_eyes_closed_now = is_left_closed_now and is_right_closed_now
            if are_both_eyes_closed_now: self._both_eyes_closed_counter = min(self.both_eyes_closed_frames, self._both_eyes_closed_counter + 1)
            else: self._both_eyes_closed_counter = max(0, self._both_eyes_closed_counter - 1)
            both_eyes_closed_state = self._both_eyes_closed_counter >= self.both_eyes_closed_frames

            if both_eyes_closed_state != self._prev_both_eyes_closed_state:
                event = BOTH_EYES_CLOSED_START_EVENT if both_eyes_closed_state else BOTH_EYES_CLOSED_STOP_EVENT
                self.event_handler("face", event)
                self._prev_both_eyes_closed_state = both_eyes_closed_state

            # --- Eyebrows Raised (Sustained) ---
            are_eyebrows_raised_now = avg_err > self.err_threshold
            if are_eyebrows_raised_now: self._eyebrow_raise_counter = min(self.consec_frames_eyebrow, self._eyebrow_raise_counter + 1)
            else: self._eyebrow_raise_counter = max(0, self._eyebrow_raise_counter - 1)
            eyebrows_raised_state = self._eyebrow_raise_counter >= self.consec_frames_eyebrow

            if eyebrows_raised_state != self._prev_eyebrows_raised_state:
                event = EYEBROWS_RAISED_START_EVENT if eyebrows_raised_state else EYEBROWS_RAISED_STOP_EVENT
                self.event_handler("face", event)
                self._prev_eyebrows_raised_state = eyebrows_raised_state

            # --- Head Tilt (Sustained) ---
            is_tilt_left_now = self.head_tilt_left_min >= head_tilt_angle >= self.head_tilt_left_max
            is_tilt_right_now = self.head_tilt_right_min <= head_tilt_angle <= self.head_tilt_right_max

            if is_tilt_left_now: self._head_tilt_left_counter = min(self.consec_frames_head_tilt, self._head_tilt_left_counter + 1); self._head_tilt_right_counter = 0
            elif is_tilt_right_now: self._head_tilt_right_counter = min(self.consec_frames_head_tilt, self._head_tilt_right_counter + 1); self._head_tilt_left_counter = 0
            else: self._head_tilt_left_counter = max(0, self._head_tilt_left_counter - 1); self._head_tilt_right_counter = max(0, self._head_tilt_right_counter - 1)

            head_tilt_left_state = self._head_tilt_left_counter >= self.consec_frames_head_tilt
            head_tilt_right_state = self._head_tilt_right_counter >= self.consec_frames_head_tilt

            if head_tilt_left_state != self._prev_head_tilt_left_state:
                event = HEAD_TILT_LEFT_START_EVENT if head_tilt_left_state else HEAD_TILT_LEFT_STOP_EVENT
                self.event_handler("face", event)
                self._prev_head_tilt_left_state = head_tilt_left_state

            if head_tilt_right_state != self._prev_head_tilt_right_state:
                event = HEAD_TILT_RIGHT_START_EVENT if head_tilt_right_state else HEAD_TILT_RIGHT_STOP_EVENT
                self.event_handler("face", event)
                self._prev_head_tilt_right_state = head_tilt_right_state

            # --- Visualization ---
            if self.show_video:
                # Draw on a copy to avoid modifying the original frame if needed elsewhere
                debug_frame = frame.copy()
                if landmarks:
                    # Draw landmarks
                    mp_drawing.draw_landmarks(
                        image=debug_frame, landmark_list=results.multi_face_landmarks[0],
                        connections=mp_face_mesh.FACEMESH_CONTOURS, # Or specific connections
                        landmark_drawing_spec=None, # Use default
                        connection_drawing_spec=mp_drawing_styles.get_default_face_mesh_contours_style()
                    )
                    # Draw head tilt line (optional)
                    try:
                        chin = landmarks[self.CHIN_INDEX]; forehead = landmarks[self.FOREHEAD_INDEX]
                        cv2.line(debug_frame, (int(chin.x*frame_width), int(chin.y*frame_height)),
                                 (int(forehead.x*frame_width), int(forehead.y*frame_height)), (255, 0, 0), 2)
                    except IndexError: pass

                # Display status text (more compact)
                status_text = f"L_EAR:{ear_right_val:.2f} R_EAR:{ear_left_val:.2f} MAR:{mar_val:.2f} ERR:{avg_err:.2f} TILT:{head_tilt_angle:.1f}"
                cv2.putText(debug_frame, status_text, (10, frame_height - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
                active_states = []
                if mouth_open_state: active_states.append("M_OPEN")
                if both_eyes_closed_state: active_states.append("E_CLOSED")
                if eyebrows_raised_state: active_states.append("EB_RAISED")
                if head_tilt_left_state: active_states.append("T_LEFT")
                if head_tilt_right_state: active_states.append("T_RIGHT")
                state_text = "States: " + (", ".join(active_states) if active_states else "None")
                cv2.putText(debug_frame, state_text, (10, frame_height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

                cv2.imshow('Facial Detector Debug', debug_frame)
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    cv2.destroyWindow('Facial Detector Debug'); self.show_video = False

        # --- End of Loop ---
        print("Facial Detector: Background detection thread finished.")


    def start(self):
        """Initializes camera and starts the detection thread."""
        if self.running: print("Facial Detector: Already running."); return
        print("Facial Detector: Initializing camera...")
        try:
            self.cap = cv2.VideoCapture(self.camera_index)
            if not self.cap.isOpened(): raise IOError(f"Cannot open camera {self.camera_index}")
            self.running = True
            self._reset_states() # Reset states on start
            self.thread = threading.Thread(target=self._run_detection_loop, daemon=True)
            self.thread.start()
            print(f"Facial Detector: Started on camera {self.camera_index}.")
        except Exception as e:
            print(f"ERROR: Failed to start Facial Detector: {e}"); traceback.print_exc()
            if self.cap: self.cap.release(); self.cap = None
            self.running = False

    def stop(self):
        """Stops the detection thread and releases resources."""
        if not self.running: print("Facial Detector: Already stopped."); return
        print("Facial Detector: Stopping...")
        self.running = False
        if self.thread and self.thread.is_alive(): self.thread.join(timeout=1.0)
        if self.cap: self.cap.release(); self.cap = None; print("Facial Detector: Camera released.")
        if self.show_video: # Attempt to close window if it might be open
             try: cv2.destroyWindow('Facial Detector Debug')
             except Exception: pass
        if hasattr(self.face_mesh, 'close'):
             try: self.face_mesh.close()
             except Exception: pass
        print("Facial Detector: Stopped.")

# --- Standalone Test Block ---
if __name__ == '__main__':
    print("--- Running FacialDetector Standalone Test ---")
    def test_event_handler(detector_type, event_data):
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        print(f"{timestamp} - EVENT: Type={detector_type}, Data={event_data}")

    detector = FacialDetector(event_handler=test_event_handler, show_video=True)
    detector.start()
    print("\nFacial Detector running. Perform gestures. Press Ctrl+C to stop.")
    try:
        while detector.running: time.sleep(0.5)
    except KeyboardInterrupt: print("\nCtrl+C detected. Stopping detector...")
    finally: detector.stop(); print("--- Facial Detector Test Finished ---")