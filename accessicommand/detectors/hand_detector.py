# accessicommand/detectors/hand_detector.py
import cv2
import mediapipe as mp
import time
import math
# REMOVED: import threading
import traceback

# --- MediaPipe Setup ---
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles

# --- Default Configuration Constants ---
DEFAULT_MAX_HANDS = 1
DEFAULT_DETECTION_CONFIDENCE = 0.7
DEFAULT_TRACKING_CONFIDENCE = 0.5
DEFAULT_CONSEC_FRAMES_FOR_GESTURE = 5

# --- Event Name Constants ---
OPEN_PALM_EVENT = "OPEN_PALM"; FIST_EVENT = "FIST"; THUMBS_UP_EVENT = "THUMBS_UP"
POINTING_INDEX_EVENT = "POINTING_INDEX"; VICTORY_EVENT = "VICTORY"
GESTURE_NONE_EVENT = "HAND_GESTURE_NONE"

class HandDetector:
    """ Detects static hand gestures from a frame and emits events. """

    # Landmark IDs
    WRIST = 0; THUMB_CMC = 1; THUMB_MCP = 2; THUMB_IP = 3; THUMB_TIP = 4
    INDEX_MCP = 5; INDEX_PIP = 6; INDEX_DIP = 7; INDEX_TIP = 8
    MIDDLE_MCP = 9; MIDDLE_PIP = 10; MIDDLE_DIP = 11; MIDDLE_TIP = 12
    RING_MCP = 13; RING_PIP = 14; RING_DIP = 15; RING_TIP = 16
    PINKY_MCP = 17; PINKY_PIP = 18; PINKY_DIP = 19; PINKY_TIP = 20

    def __init__(self, event_handler,
                 max_num_hands=DEFAULT_MAX_HANDS,
                 min_detection_confidence=DEFAULT_DETECTION_CONFIDENCE,
                 min_tracking_confidence=DEFAULT_TRACKING_CONFIDENCE,
                 consec_frames_for_gesture=DEFAULT_CONSEC_FRAMES_FOR_GESTURE
                 # REMOVED: camera_index, show_video
                ):
        self.event_handler = event_handler if callable(event_handler) else self._default_handler
        if not callable(event_handler): print("WARN: No valid event_handler for HandDetector.")

        # Store Configuration
        self.max_num_hands = max_num_hands
        self.min_detection_confidence = min_detection_confidence
        self.min_tracking_confidence = min_tracking_confidence
        self.consec_frames_for_gesture = consec_frames_for_gesture

        # MediaPipe Hands Initialization
        self.hands = None # Initialized in start()

        # State Variables
        self.is_active = False
        self._reset_states()

        print("--- Hand Detector Initialized (Configured) ---")

    def _reset_states(self):
        self._current_stable_gesture = GESTURE_NONE_EVENT
        self._last_detected_gesture = GESTURE_NONE_EVENT
        self._gesture_counter = 0

    def _default_handler(self, detector_type, event_data): pass

    def _detect_gesture(self, hand_landmarks):
        """ Determines the static gesture based on landmark positions. """
        lm = hand_landmarks.landmark
        if not lm: return GESTURE_NONE_EVENT
        try:
            thumb_ext = lm[self.THUMB_TIP].y < lm[self.THUMB_IP].y; thumb_flex = lm[self.THUMB_TIP].y > lm[self.THUMB_IP].y
            index_ext = lm[self.INDEX_TIP].y < lm[self.INDEX_PIP].y; index_flex = lm[self.INDEX_TIP].y > lm[self.INDEX_PIP].y
            middle_ext= lm[self.MIDDLE_TIP].y < lm[self.MIDDLE_PIP].y; middle_flex= lm[self.MIDDLE_TIP].y > lm[self.MIDDLE_PIP].y
            ring_ext  = lm[self.RING_TIP].y < lm[self.RING_PIP].y; ring_flex = lm[self.RING_TIP].y > lm[self.RING_PIP].y
            pinky_ext = lm[self.PINKY_TIP].y < lm[self.PINKY_PIP].y; pinky_flex= lm[self.PINKY_TIP].y > lm[self.PINKY_PIP].y

            if thumb_ext and index_flex and middle_flex and ring_flex and pinky_flex and \
               lm[self.THUMB_TIP].y < lm[self.INDEX_PIP].y and lm[self.THUMB_TIP].y < lm[self.MIDDLE_PIP].y: return THUMBS_UP_EVENT
            elif index_ext and middle_ext and ring_flex and pinky_flex: return VICTORY_EVENT
            elif index_ext and middle_flex and ring_flex and pinky_flex: return POINTING_INDEX_EVENT
            elif thumb_ext and index_ext and middle_ext and ring_ext and pinky_ext: return OPEN_PALM_EVENT
            elif thumb_flex and index_flex and middle_flex and ring_flex and pinky_flex:
                 palm_cy = lm[self.MIDDLE_MCP].y
                 tips_near = (lm[self.INDEX_TIP].y > palm_cy and lm[self.MIDDLE_TIP].y > palm_cy and \
                              lm[self.RING_TIP].y > palm_cy and lm[self.PINKY_TIP].y > palm_cy)
                 if tips_near: return FIST_EVENT
            return GESTURE_NONE_EVENT
        except IndexError: print("WARN: Hand landmark index error."); return GESTURE_NONE_EVENT
        except Exception as e: print(f"ERROR: Gesture detection: {e}"); traceback.print_exc(); return GESTURE_NONE_EVENT

    def process_frame(self, frame, frame_timestamp):
        """ Processes a single frame for hand gestures. """
        if not self.is_active or self.hands is None:
            return None # No landmarks to return if inactive

        # Assumes frame is already flipped and in RGB from Engine
        frame.flags.writeable = False
        results = self.hands.process(frame)
        frame.flags.writeable = True

        detected_gesture_this_frame = GESTURE_NONE_EVENT
        hand_landmarks_for_vis = None

        if results.multi_hand_landmarks:
            # Process the first detected hand
            hand_landmarks = results.multi_hand_landmarks[0]
            hand_landmarks_for_vis = hand_landmarks # For visualization return
            detected_gesture_this_frame = self._detect_gesture(hand_landmarks)

        # --- Debounce and Emit Events ---
        if detected_gesture_this_frame == self._last_detected_gesture: self._gesture_counter += 1
        else: self._gesture_counter = 0; self._last_detected_gesture = detected_gesture_this_frame

        is_stable = self._gesture_counter >= self.consec_frames_for_gesture
        new_stable_gesture = detected_gesture_this_frame

        # Emit event ONLY when the stable gesture CHANGES
        if (is_stable and new_stable_gesture != self._current_stable_gesture) or \
           (self._gesture_counter == 0 and detected_gesture_this_frame == GESTURE_NONE_EVENT and self._current_stable_gesture != GESTURE_NONE_EVENT):
            old_stable = self._current_stable_gesture
            self._current_stable_gesture = new_stable_gesture if is_stable else GESTURE_NONE_EVENT
            print(f"Hand Detector: Stable gesture changed: {old_stable} -> {self._current_stable_gesture}")
            try:
                self.event_handler("hand", self._current_stable_gesture)
            except Exception as handler_e: print(f"ERROR: Hand event handler: {handler_e}"); traceback.print_exc()

        # Return landmarks for potential drawing by Engine
        return hand_landmarks_for_vis # Or results.multi_hand_landmarks if multi-hand

    def start(self):
        """Initializes MediaPipe Hands."""
        if self.is_active: print("Hand Detector: Already active."); return
        print("Hand Detector: Initializing MediaPipe Hands...")
        try:
            self.hands = mp_hands.Hands(
                static_image_mode=False, max_num_hands=self.max_num_hands,
                min_detection_confidence=self.min_detection_confidence,
                min_tracking_confidence=self.min_tracking_confidence)
            self._reset_states()
            self.is_active = True
            print("Hand Detector: Started (ready to process frames).")
        except Exception as e:
            print(f"ERROR: Failed to initialize MediaPipe Hands: {e}"); traceback.print_exc()
            self.hands = None; self.is_active = False

    def stop(self):
        """Releases MediaPipe resources."""
        if not self.is_active: print("Hand Detector: Already stopped."); return
        print("Hand Detector: Stopping...")
        self.is_active = False
        if hasattr(self.hands, 'close'):
             try: self.hands.close()
             except Exception as e: print(f"Error closing hands: {e}")
        self.hands = None
        print("Hand Detector: Stopped.")