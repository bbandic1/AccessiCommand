import cv2
import mediapipe as mp
import pyautogui
import time
import math
import numpy as np

# --- MediaPipe Face Mesh Setup ---
mp_face_mesh = mp.solutions.face_mesh

face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5)

# --- Camera and Screen Setup ---
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Error: Cannot open camera")
    exit()

screen_w, screen_h = pyautogui.size()

# --- Landmark Indices ---
LEFT_EYE_INDICES = [362, 385, 387, 263, 373, 380] # Person's Left Eye
RIGHT_EYE_INDICES = [33, 160, 158, 133, 153, 144]  # Person's Right Eye
MOUTH_CORNER_INDICES = [61, 291]                   # Person's Mouth Corners
MOUTH_VERTICAL_INDICES = [13, 14]                 # Person's Inner Lips Vertical
LEFT_EYEBROW_INDICES = [70, 63, 105, 66, 107]    # Person's Left Eyebrow
RIGHT_EYEBROW_INDICES = [336, 296, 334, 293, 300] # Person's Right Eyebrow
FACE_OVAL_INDICES = [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136, 172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109]  # Face oval indices for head tilt detection

# Combine all indices we want to draw
LANDMARKS_TO_DRAW = LEFT_EYE_INDICES + RIGHT_EYE_INDICES + MOUTH_CORNER_INDICES + MOUTH_VERTICAL_INDICES + LEFT_EYEBROW_INDICES + RIGHT_EYEBROW_INDICES

# --- State Variables ---
left_eye_closed_state = False
right_eye_closed_state = False
mouth_open_state = False
eyebrows_raised_state = False
head_tilt_left_state = False
head_tilt_right_state = False


# --- Blink detection variables ---
left_eye_blinked = False
right_eye_blinked = False
left_eye_previously_closed = False
right_eye_previously_closed = False
blink_cooldown = 0.3  # seconds before detecting another blink
last_left_blink_time = 0
last_right_blink_time = 0

# --- Key tracking variables ---
keys_currently_pressed = set()  # Track which keys are currently being pressed


# --- Thresholds ---
EAR_THRESHOLD = 0.20
MAR_THRESHOLD = 0.35
ERR_THRESHOLD = 1.34  # Eyebrow Raise Ratio threshold (adjust based on testing)
BOTH_EYES_CLOSED_FRAMES = 2  # Number of consecutive frames to detect both eyes closed

# New head tilt thresholds
HEAD_TILT_LEFT_MIN = -100  # Start pressing 'A' when angle is below -100
HEAD_TILT_LEFT_MAX = -160  # Stop pressing 'A' when angle is below -160
HEAD_TILT_RIGHT_MIN = 100  # Start pressing 'D' when angle is above 100
HEAD_TILT_RIGHT_MAX = 160  # Stop pressing 'D' when angle is above 160

CONSEC_FRAMES_BLINK = 2
CONSEC_FRAMES_MOUTH = 3
CONSEC_FRAMES_EYEBROW = 3  # Number of consecutive frames for eyebrow raise detection
CONSEC_FRAMES_HEAD_TILT = 2  # Number of consecutive frames for head tilt detection (reduced for responsiveness)


# --- Counters ---
left_blink_counter = 0
right_blink_counter = 0
mouth_open_counter = 0
eyebrow_raise_counter = 0
head_tilt_left_counter = 0
head_tilt_right_counter = 0
both_eyes_closed_counter = 0  # Counter for both eyes closed

def calculate_distance(p1, p2):
    return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2 + (p1.z - p2.z)**2)

def calculate_ear(eye_landmarks):
    try:
        v1 = calculate_distance(eye_landmarks[1], eye_landmarks[5])
        v2 = calculate_distance(eye_landmarks[2], eye_landmarks[4])
        h = calculate_distance(eye_landmarks[0], eye_landmarks[3])
        if h == 0: return 1.0
        ear = (v1 + v2) / (2.0 * h)
        return ear
    except IndexError:
        return 1.0

def calculate_mar(landmarks, corner_indices, inner_vertical_indices):
    try:
        mouth_left_corner = landmarks[corner_indices[0]]
        mouth_right_corner = landmarks[corner_indices[1]]
        lip_upper_inner = landmarks[inner_vertical_indices[0]]
        lip_lower_inner = landmarks[inner_vertical_indices[1]]
        vertical_dist = calculate_distance(lip_upper_inner, lip_lower_inner)
        horizontal_dist = calculate_distance(mouth_left_corner, mouth_right_corner)
        if horizontal_dist == 0: return 0
        mar = vertical_dist / horizontal_dist
        return mar
    except IndexError:
        return 0

def calculate_err(landmarks, eyebrow_indices, eye_indices):
    """Calculate Eyebrow Raise Ratio (ERR)"""
    try:
        # Get eyebrow points (middle and outer points)
        eyebrow_middle = landmarks[eyebrow_indices[2]]
        eyebrow_outer = landmarks[eyebrow_indices[4]]
        
        # Get corresponding eye points (top of the eye)
        eye_top = landmarks[eye_indices[1]]
        
        # Calculate vertical distance between eyebrow and eye
        vertical_dist = abs(eyebrow_middle.y - eye_top.y)
        
        # Calculate horizontal distance between eyebrow points
        horizontal_dist = calculate_distance(eyebrow_middle, eyebrow_outer)
        
        if horizontal_dist == 0: return 0
        err = vertical_dist / horizontal_dist
        return err
    except IndexError:
        return 0

def calculate_head_tilt(landmarks, frame_width, frame_height):
    """Calculate head tilt angle in degrees"""
    try:
        # Get face oval points (chin and forehead)
        chin = landmarks[152]
        forehead = landmarks[10]
        
        # Convert to pixel coordinates
        chin_x = int(chin.x * frame_width)
        chin_y = int(chin.y * frame_height)
        forehead_x = int(forehead.x * frame_width)
        forehead_y = int(forehead.y * frame_height)
        
        # Calculate the angle between vertical line and face line
        dx = forehead_x - chin_x
        dy = forehead_y - chin_y
        angle = math.degrees(math.atan2(dx, dy))
        
        return angle
    except IndexError:
        return 0

def update_keys(actions_to_perform):
    """
    Update the keys being pressed based on the current actions to perform
    actions_to_perform is a dictionary where keys are the key names and values are booleans
    indicating whether the key should be pressed (True) or released (False)
    """
    global keys_currently_pressed
    
    for key, should_press in actions_to_perform.items():
        if should_press and key not in keys_currently_pressed:
            pyautogui.keyDown(key)
            keys_currently_pressed.add(key)
            print(f"Pressed: {key}")
        elif not should_press and key in keys_currently_pressed:
            pyautogui.keyUp(key)
            keys_currently_pressed.remove(key)
            print(f"Released: {key}")

def perform_shift_key_combo(key):
    """Perform a single shift+key press and release"""
    pyautogui.keyDown(key)
    pyautogui.keyDown('shift')
    pyautogui.keyDown(key)
    time.sleep(0.05)  # Small delay to ensure the key combination is registered
    pyautogui.keyUp(key)
    pyautogui.keyUp('shift')
    print(f"Single press: shift+{key}")

def release_all_keys():
    """Release all keys that are currently pressed"""
    global keys_currently_pressed
    for key in list(keys_currently_pressed):
        pyautogui.keyUp(key)
        print(f"Released: {key}")
    keys_currently_pressed.clear()

print("Starting Facial Controller. Press 'q' to quit.")
print("Blink left eye for 'shift+a', right eye for 'shift+d'.")
print("Hold eyebrows raised for 'j' key.")
print(f"Tilt head left ({HEAD_TILT_LEFT_MIN}° to {HEAD_TILT_LEFT_MAX}°) for 'a' key.")
print(f"Tilt head right ({HEAD_TILT_RIGHT_MIN}° to {HEAD_TILT_RIGHT_MAX}°) for 'd' key.")
print("Open mouth for SPACE key.")
print("You can combine actions (e.g., tilt head AND open mouth).")

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame")
            time.sleep(0.5)
            continue

        frame = cv2.flip(frame, 1)
        frame_height, frame_width, _ = frame.shape
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        rgb_frame.flags.writeable = False
        results = face_mesh.process(rgb_frame)
        rgb_frame.flags.writeable = True

        frame = cv2.cvtColor(rgb_frame, cv2.COLOR_RGB2BGR)

        ear_left_val = 1.0
        ear_right_val = 1.0
        mar_val = 0.0
        err_left_val = 0.0
        err_right_val = 0.0
        head_tilt_angle = 0.0
        
        current_time = time.time()
        
        # Dictionary to track which keys should be pressed or released
        actions = {
            'a': False,
            'd': False,
            'j': False,
            'k': False,  # Changed from 'space' to 'k' for mouth open
            'space': False  # Added for both eyes closed
        }
        
        # Reset blink flags
        left_eye_blinked = False
        right_eye_blinked = False

        if results.multi_face_landmarks:
            landmarks = results.multi_face_landmarks[0].landmark

            person_right_eye_points = [landmarks[i] for i in LEFT_EYE_INDICES]
            person_left_eye_points = [landmarks[i] for i in RIGHT_EYE_INDICES]

            ear_left_val = calculate_ear(person_left_eye_points)
            ear_right_val = calculate_ear(person_right_eye_points)

            # Left eye blink detection (person's right eye)
            if ear_left_val < EAR_THRESHOLD:
                left_blink_counter += 1
                left_eye_closed_state = left_blink_counter >= CONSEC_FRAMES_BLINK
                
                # Detect transition from open to closed for left eye blink
                if left_eye_closed_state and not left_eye_previously_closed and current_time - last_left_blink_time > blink_cooldown:
                    left_eye_blinked = True
                    last_left_blink_time = current_time
                left_eye_previously_closed = left_eye_closed_state
            else:
                left_blink_counter = 0
                left_eye_closed_state = False
                left_eye_previously_closed = False

            # Right eye blink detection (person's left eye)
            if ear_right_val < EAR_THRESHOLD:
                right_blink_counter += 1
                right_eye_closed_state = right_blink_counter >= CONSEC_FRAMES_BLINK
                
                # Detect transition from open to closed for right eye blink
                if right_eye_closed_state and not right_eye_previously_closed and current_time - last_right_blink_time > blink_cooldown:
                    right_eye_blinked = True
                    last_right_blink_time = current_time
                right_eye_previously_closed = right_eye_closed_state
            else:
                right_blink_counter = 0
                right_eye_closed_state = False
                right_eye_previously_closed = False

            # Process detected blinks - only if ONE eye blinks, not both
            if left_eye_blinked and not right_eye_blinked:
                perform_shift_key_combo('a')
            elif right_eye_blinked and not left_eye_blinked:
                perform_shift_key_combo('d')

            # Mouth open detection (press 'k')
            mar_val = calculate_mar(landmarks, MOUTH_CORNER_INDICES, MOUTH_VERTICAL_INDICES)

            if mar_val > MAR_THRESHOLD:
                mouth_open_counter += 1
            else:
                mouth_open_counter = max(0, mouth_open_counter - 1)

            mouth_open_state = mouth_open_counter >= CONSEC_FRAMES_MOUTH
            if mouth_open_state:
                actions['k'] = True  # Changed from 'space' to 'k'

            # Both eyes closed detection (press 'space')
            if ear_left_val < EAR_THRESHOLD and ear_right_val < EAR_THRESHOLD:
                both_eyes_closed_counter += 1
            else:
                both_eyes_closed_counter = max(0, both_eyes_closed_counter - 1)

            both_eyes_closed_state = both_eyes_closed_counter >= BOTH_EYES_CLOSED_FRAMES
            if both_eyes_closed_state:
                actions['space'] = True

            # Eyebrow raise detection
            err_left_val = calculate_err(landmarks, LEFT_EYEBROW_INDICES, RIGHT_EYE_INDICES)
            err_right_val = calculate_err(landmarks, RIGHT_EYEBROW_INDICES, LEFT_EYE_INDICES)
            avg_err = (err_left_val + err_right_val) / 2

            if avg_err > ERR_THRESHOLD:
                eyebrow_raise_counter += 1
            else:
                eyebrow_raise_counter = max(0, eyebrow_raise_counter - 1)

            eyebrows_raised_state = eyebrow_raise_counter >= CONSEC_FRAMES_EYEBROW
            if eyebrows_raised_state:
                actions['j'] = True

            # Head tilt detection with new thresholds
            head_tilt_angle = calculate_head_tilt(landmarks, frame_width, frame_height)
            
            # Check if head tilt is in the left range (-100 to -160)
            if HEAD_TILT_LEFT_MIN >= head_tilt_angle >= HEAD_TILT_LEFT_MAX:
                head_tilt_left_counter += 1
                head_tilt_right_counter = 0
            # Check if head tilt is in the right range (100 to 160)
            elif HEAD_TILT_RIGHT_MIN <= head_tilt_angle <= HEAD_TILT_RIGHT_MAX:
                head_tilt_right_counter += 1
                head_tilt_left_counter = 0
            else:
                head_tilt_left_counter = max(0, head_tilt_left_counter - 1)
                head_tilt_right_counter = max(0, head_tilt_right_counter - 1)
            
            head_tilt_left_state = head_tilt_left_counter >= CONSEC_FRAMES_HEAD_TILT
            head_tilt_right_state = head_tilt_right_counter >= CONSEC_FRAMES_HEAD_TILT
            
            if head_tilt_left_state:
                actions['a'] = True
            elif head_tilt_right_state:
                actions['d'] = True

            # Visualization
            for index in LANDMARKS_TO_DRAW:
                try:
                    point = landmarks[index]
                    x = int(point.x * frame_width)
                    y = int(point.y * frame_height)
                    cv2.circle(frame, (x, y), 2, (0, 255, 0), -1)
                except IndexError:
                    pass

            # Draw head tilt line

            try:
                chin = landmarks[152]
                forehead = landmarks[10]
                chin_x = int(chin.x * frame_width)
                chin_y = int(chin.y * frame_height)
                forehead_x = int(forehead.x * frame_width)
                forehead_y = int(forehead.y * frame_height)
                cv2.line(frame, (chin_x, chin_y), (forehead_x, forehead_y), (255, 0, 0), 2)
            except IndexError:
                pass

        # Update keys based on current actions
        update_keys(actions)

        # Display status
        left_eye_color = (0, 0, 255) if left_eye_closed_state else (0, 255, 0)
        right_eye_color = (0, 0, 255) if right_eye_closed_state else (0, 255, 0)
        mouth_color = (0, 0, 255) if mouth_open_state else (0, 255, 0)
        eyebrow_color = (0, 0, 255) if eyebrows_raised_state else (0, 255, 0)
        head_tilt_left_color = (0, 0, 255) if head_tilt_left_state else (0, 255, 0)
        head_tilt_right_color = (0, 0, 255) if head_tilt_right_state else (0, 255, 0)
        both_eyes_color = (0, 0, 255) if both_eyes_closed_state else (0, 255, 0)

        cv2.putText(frame, f"L EYE: {ear_left_val:.2f} ({'Closed' if left_eye_closed_state else 'Open'})", (10, 30),
                  cv2.FONT_HERSHEY_SIMPLEX, 0.6, left_eye_color, 2)
        cv2.putText(frame, f"R EYE: {ear_right_val:.2f} ({'Closed' if right_eye_closed_state else 'Open'})", (10, 60),
                  cv2.FONT_HERSHEY_SIMPLEX, 0.6, right_eye_color, 2)
        cv2.putText(frame, f"MAR: {mar_val:.2f} ({'Open' if mouth_open_state else 'Closed'})", (10, 90),
                  cv2.FONT_HERSHEY_SIMPLEX, 0.6, mouth_color, 2)
        cv2.putText(frame, f"ERR: {avg_err:.2f} ({'Raised' if eyebrows_raised_state else 'Normal'})", (10, 120),
                  cv2.FONT_HERSHEY_SIMPLEX, 0.6, eyebrow_color, 2)
        cv2.putText(frame, f"Head Tilt: {head_tilt_angle:.1f}° ({'Left' if head_tilt_left_state else 'Right' if head_tilt_right_state else 'Center'})", (10, 150),
                  cv2.FONT_HERSHEY_SIMPLEX, 0.6, head_tilt_left_color if head_tilt_left_state else head_tilt_right_color if head_tilt_right_state else (0, 255, 0), 2)
        cv2.putText(frame, f"Both Eyes: {'Closed' if both_eyes_closed_state else 'Open'}", (10, 180),
                  cv2.FONT_HERSHEY_SIMPLEX, 0.6, both_eyes_color, 2)
        
        # Display active keys
        active_keys_text = "Active Keys: " + ", ".join(keys_currently_pressed) if keys_currently_pressed else "No keys active"
        cv2.putText(frame, active_keys_text, (10, 210),
                  cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        # Display blink feedback
        if current_time - last_left_blink_time < 0.5:
            cv2.putText(frame, "Left eye blink: 'shift+a' pressed", (10, 240),
                      cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 215, 0), 2)
        if current_time - last_right_blink_time < 0.5:
            cv2.putText(frame, "Right eye blink: 'shift+d' pressed", (10, 270),
                      cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 215, 0), 2)

        # Display thresholds for reference
        cv2.putText(frame, f"Head Tilt Left: {HEAD_TILT_LEFT_MIN}° to {HEAD_TILT_LEFT_MAX}° | Right: {HEAD_TILT_RIGHT_MIN}° to {HEAD_TILT_RIGHT_MAX}°", (10, 300),
                  cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        cv2.imshow('Facial Gesture Controller', frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break

except Exception as e:
    print(f"Error occurred: {e}")
finally:
    # Clean up
    release_all_keys()
    cap.release()
    cv2.destroyAllWindows()
