# hardcoded_hand_controller.py
import cv2
import mediapipe as mp
import pyautogui
import time
import math

# --- MediaPipe Hands Setup ---
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles

# Initialize Hands - detect only one hand for simplicity and performance
hands = mp_hands.Hands(
    static_image_mode=False,       # Process video stream
    max_num_hands=1,               # Detect only one hand
    min_detection_confidence=0.7,  # Higher confidence needed
    min_tracking_confidence=0.5)

# --- Camera Setup ---
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Error: Cannot open camera")
    exit()

# --- Gesture State & Debouncing ---
# Store the *last stable* detected gesture to avoid flickering actions
current_gesture = "NONE"
last_gesture = "NONE"
gesture_counter = 0
CONSEC_FRAMES_FOR_GESTURE = 5 # Require gesture to be stable for N frames

# --- Hardcoded Actions ---
# Map gesture names to pyautogui actions
GESTURE_ACTIONS = {
    "OPEN_PALM": lambda: pyautogui.press('h'),
    "FIST": lambda: pyautogui.press('l'), # Lowercase L
    "THUMBS_UP": lambda: pyautogui.press('u'),
    "POINTING_INDEX": lambda: pyautogui.press('p'),
    "VICTORY": lambda: pyautogui.press('v'),
    # Add more later if needed
}

# --- Landmark ID Constants (for convenience) ---
WRIST = 0
THUMB_CMC = 1
THUMB_MCP = 2
THUMB_IP = 3
THUMB_TIP = 4
INDEX_MCP = 5
INDEX_PIP = 6
INDEX_DIP = 7
INDEX_TIP = 8
MIDDLE_MCP = 9
MIDDLE_PIP = 10
MIDDLE_DIP = 11
MIDDLE_TIP = 12
RING_MCP = 13
RING_PIP = 14
RING_DIP = 15
RING_TIP = 16
PINKY_MCP = 17
PINKY_PIP = 18
PINKY_DIP = 19
PINKY_TIP = 20

print("Starting Hand Gesture Controller (Hardcoded). Press 'q' to quit.")
print("Actions:")
print("- Open Palm: Press 'h'")
print("- Fist: Press 'l'")
print("- Thumbs Up: Press 'u'")
print("- Pointing Index: Press 'p'")
print("- Victory Sign: Press 'v'")

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            print("WARN: Failed to grab frame, retrying...")
            time.sleep(0.5)
            continue

        # --- Frame Preparation ---
        frame = cv2.flip(frame, 1) # Mirror view
        frame_height, frame_width, _ = frame.shape
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Performance Optimization
        rgb_frame.flags.writeable = False

        # --- Process with MediaPipe Hands ---
        results = hands.process(rgb_frame)

        # Performance Optimization
        rgb_frame.flags.writeable = True
        frame = cv2.cvtColor(rgb_frame, cv2.COLOR_RGB2BGR) # Convert back for drawing

        # --- Gesture Recognition ---
        detected_gesture_this_frame = "NONE" # Reset for this frame

        if results.multi_hand_landmarks:
            # Since max_num_hands=1, we only process the first hand
            hand_landmarks = results.multi_hand_landmarks[0]

            # --- Draw Hand Landmarks (for debugging/visualization) ---
            mp_drawing.draw_landmarks(
                frame,
                hand_landmarks,
                mp_hands.HAND_CONNECTIONS,
                mp_drawing_styles.get_default_hand_landmarks_style(),
                mp_drawing_styles.get_default_hand_connections_style())

            # --- Get Coordinates of Fingertips and relevant joints ---
            # Store landmark coordinates for easier access
            lm = hand_landmarks.landmark
            # Note: Y decreases going up

            # Finger extension checks (Tip Y coordinate compared to PIP/MCP Y coordinate)
            # A simple check: Tip is higher (smaller Y) than the joint below it indicates extension.
            thumb_extended = lm[THUMB_TIP].y < lm[THUMB_IP].y
            index_extended = lm[INDEX_TIP].y < lm[INDEX_PIP].y
            middle_extended = lm[MIDDLE_TIP].y < lm[MIDDLE_PIP].y
            ring_extended = lm[RING_TIP].y < lm[RING_PIP].y
            pinky_extended = lm[PINKY_TIP].y < lm[PINKY_PIP].y

            # Finger flexion checks (Tip Y is lower (larger Y) than the joint)
            # Using PIP as reference for main fingers, IP for thumb
            thumb_flexed = lm[THUMB_TIP].y > lm[THUMB_IP].y
            index_flexed = lm[INDEX_TIP].y > lm[INDEX_PIP].y
            middle_flexed = lm[MIDDLE_TIP].y > lm[MIDDLE_PIP].y
            ring_flexed = lm[RING_TIP].y > lm[RING_PIP].y
            pinky_flexed = lm[PINKY_TIP].y > lm[PINKY_PIP].y


            # --- Gesture Logic ---
            if thumb_extended and index_extended and middle_extended and ring_extended and pinky_extended:
                detected_gesture_this_frame = "OPEN_PALM"
            elif thumb_flexed and index_flexed and middle_flexed and ring_flexed and pinky_flexed:
                 # More robust fist check: Ensure tips are also below MCPs? Maybe not needed yet.
                 # Check if tips are close to palm center (e.g., near middle MCP Y)
                 palm_center_y = lm[MIDDLE_MCP].y
                 tips_near_palm = (lm[INDEX_TIP].y > palm_center_y and
                                   lm[MIDDLE_TIP].y > palm_center_y and
                                   lm[RING_TIP].y > palm_center_y and
                                   lm[PINKY_TIP].y > palm_center_y)
                 if tips_near_palm: # Add this check for better fist detection
                    detected_gesture_this_frame = "FIST"
            elif thumb_extended and index_flexed and middle_flexed and ring_flexed and pinky_flexed:
                 # Thumbs up needs thumb tip significantly higher than other joints
                 if lm[THUMB_TIP].y < lm[INDEX_PIP].y and lm[THUMB_TIP].y < lm[MIDDLE_PIP].y:
                     detected_gesture_this_frame = "THUMBS_UP"
            elif index_extended and middle_flexed and ring_flexed and pinky_flexed:
                 # Pointing: Optionally add check for thumb being flexed or tucked
                 # thumb_tucked = lm[THUMB_TIP].x > lm[THUMB_IP].x (for right hand) - Handedness needed for robust check
                 detected_gesture_this_frame = "POINTING_INDEX"
            elif index_extended and middle_extended and ring_flexed and pinky_flexed:
                 # Victory: Optionally add check for thumb being flexed
                 detected_gesture_this_frame = "VICTORY"

        # --- Debounce Gesture and Trigger Action ---
        if detected_gesture_this_frame == last_gesture:
            gesture_counter += 1
        else:
            # Reset counter if gesture changes or disappears
            gesture_counter = 0
            last_gesture = detected_gesture_this_frame # Update the last seen gesture

        # If a gesture has been stable for enough frames and is different from the *current stable* gesture
        if gesture_counter >= CONSEC_FRAMES_FOR_GESTURE and detected_gesture_this_frame != "NONE" and detected_gesture_this_frame != current_gesture:
            current_gesture = detected_gesture_this_frame # Update the stable gesture
            print(f"Gesture Detected: {current_gesture}")
            # Perform the action associated with the new stable gesture
            action_func = GESTURE_ACTIONS.get(current_gesture)
            if action_func:
                try:
                    action_func()
                except Exception as e:
                    print(f"Error executing action for {current_gesture}: {e}")
            else:
                 print(f"WARN: No action defined for gesture {current_gesture}")

        # If no gesture is detected consistently, reset the stable gesture
        elif gesture_counter == 0 and detected_gesture_this_frame == "NONE" and current_gesture != "NONE":
             print(f"Gesture Lost: {current_gesture} -> NONE")
             current_gesture = "NONE"


        # --- Display Status ---
        cv2.putText(frame, f"Detected: {detected_gesture_this_frame}", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 3) # Black outline
        cv2.putText(frame, f"Detected: {detected_gesture_this_frame}", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2) # White text

        cv2.putText(frame, f"Stable Gesture: {current_gesture}", (10, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 3) # Black outline
        cv2.putText(frame, f"Stable Gesture: {current_gesture}", (10, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0) if current_gesture != "NONE" else (255,255,255), 2) # Green if active


        # --- Display Frame ---
        cv2.imshow('Hand Gesture Controller', frame)

        # --- Exit Condition ---
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            print("'q' pressed, exiting.")
            break

except Exception as e:
    # Catch potential errors during the loop
    print(f"\n--- An Error Occurred in Main Loop ---")
    traceback.print_exc()
    print(f"Error details: {e}")
    print("--------------------------------------")

finally:
    # --- Cleanup ---
    print("\nCleaning up...")
    if 'cap' in locals() and cap.isOpened():
        cap.release()
    cv2.destroyAllWindows()
    if 'hands' in locals() and hasattr(hands, 'close'):
        hands.close() # Close MediaPipe resources
    print("Hand Gesture Controller Finished.")

