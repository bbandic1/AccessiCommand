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
last_action_time = 0
action_delay = 0.5
key_held = None  # To track which key is currently being held down
shift_held = False  # To track if shift is being held down

# --- Thresholds ---
EAR_THRESHOLD = 0.20
MAR_THRESHOLD = 0.35
ERR_THRESHOLD = 1.4  # Eyebrow Raise Ratio threshold (adjust based on testing)
HEAD_TILT_THRESHOLD = 30  # Degrees threshold for head tilt detection
CONSEC_FRAMES_BLINK = 2
CONSEC_FRAMES_MOUTH = 3
CONSEC_FRAMES_EYEBROW = 3  # Number of consecutive frames for eyebrow raise detection
CONSEC_FRAMES_HEAD_TILT = 5  # Number of consecutive frames for head tilt detection

# --- Counters ---
left_blink_counter = 0
right_blink_counter = 0
mouth_open_counter = 0
eyebrow_raise_counter = 0
head_tilt_left_counter = 0
head_tilt_right_counter = 0

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

def release_key():
    global key_held, shift_held
    if key_held is not None:
        pyautogui.keyUp(key_held)
        key_held = None
    if shift_held:
        pyautogui.keyUp('shift')
        shift_held = False

print("Starting Facial Controller. Press 'q' to quit.")
print("Hold eye closed to keep key pressed.")
print("Tilt head left/right for 'a'/'d' keys.")
print("Blink left/right eye for 'shift+a'/'shift+d'.")

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

    if results.multi_face_landmarks:
        landmarks = results.multi_face_landmarks[0].landmark

        person_right_eye_points = [landmarks[i] for i in LEFT_EYE_INDICES]
        person_left_eye_points = [landmarks[i] for i in RIGHT_EYE_INDICES]

        ear_left_val = calculate_ear(person_left_eye_points)
        ear_right_val = calculate_ear(person_right_eye_points)

        if ear_right_val < EAR_THRESHOLD:
            right_blink_counter += 1
        else:
            right_blink_counter = 0

        if ear_left_val < EAR_THRESHOLD:
            left_blink_counter += 1
        else:
            left_blink_counter = 0

        right_eye_closed_state = right_blink_counter >= CONSEC_FRAMES_BLINK
        left_eye_closed_state = left_blink_counter >= CONSEC_FRAMES_BLINK

        mar_val = calculate_mar(landmarks, MOUTH_CORNER_INDICES, MOUTH_VERTICAL_INDICES)

        if mar_val > MAR_THRESHOLD:
            mouth_open_counter += 1
        else:
            mouth_open_counter = max(0, mouth_open_counter - 1)

        mouth_open_state = mouth_open_counter >= CONSEC_FRAMES_MOUTH

        # Calculate eyebrow raise ratios
        err_left_val = calculate_err(landmarks, LEFT_EYEBROW_INDICES, RIGHT_EYE_INDICES)
        err_right_val = calculate_err(landmarks, RIGHT_EYEBROW_INDICES, LEFT_EYE_INDICES)
        avg_err = (err_left_val + err_right_val) / 2

        if avg_err > ERR_THRESHOLD:
            eyebrow_raise_counter += 1
        else:
            eyebrow_raise_counter = max(0, eyebrow_raise_counter - 1)

        eyebrows_raised_state = eyebrow_raise_counter >= CONSEC_FRAMES_EYEBROW

        # Calculate head tilt
        head_tilt_angle = calculate_head_tilt(landmarks, frame_width, frame_height)
        
        if head_tilt_angle < -HEAD_TILT_THRESHOLD:
            head_tilt_left_counter += 1
            head_tilt_right_counter = max(0, head_tilt_right_counter - 1)
        elif head_tilt_angle > HEAD_TILT_THRESHOLD:
            head_tilt_right_counter += 1
            head_tilt_left_counter = max(0, head_tilt_left_counter - 1)
        else:
            head_tilt_left_counter = max(0, head_tilt_left_counter - 1)
            head_tilt_right_counter = max(0, head_tilt_right_counter - 1)
        
        head_tilt_left_state = head_tilt_left_counter >= CONSEC_FRAMES_HEAD_TILT
        head_tilt_right_state = head_tilt_right_counter >= CONSEC_FRAMES_HEAD_TILT

        # Key press/hold logic
        if head_tilt_left_state and not head_tilt_right_state:
            if key_held != 'a':
                release_key()
                pyautogui.keyDown('a')
                key_held = 'a'
                print("Holding 'a' key (head tilt)")
        elif head_tilt_right_state and not head_tilt_left_state:
            if key_held != 'd':
                release_key()
                pyautogui.keyDown('d')
                key_held = 'd'
                print("Holding 'd' key (head tilt)")
        elif left_eye_closed_state and not right_eye_closed_state:
            if key_held != 'a' or not shift_held:
                release_key()
                pyautogui.keyDown('shift')
                pyautogui.keyDown('a')
                key_held = 'a'
                shift_held = True
                print("Holding 'shift+a' keys")
        elif right_eye_closed_state and not left_eye_closed_state:
            if key_held != 'd' or not shift_held:
                release_key()
                pyautogui.keyDown('shift')
                pyautogui.keyDown('d')
                key_held = 'd'
                shift_held = True
                print("Holding 'shift+d' keys")
        elif eyebrows_raised_state:
            if key_held != 'j':
                release_key()
                pyautogui.keyDown('j')
                key_held = 'j'
                print("Holding 'j' key")
        elif left_eye_closed_state and right_eye_closed_state:
            if key_held != 'k':
                release_key()
                pyautogui.keyDown('k')
                key_held = 'k'
                print("Holding 'k' key")
        elif mouth_open_state:
            if key_held != 'space':
                release_key()
                pyautogui.keyDown('space')
                key_held = 'space'
                print("Holding SPACE key")
        else:
            release_key()

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

    # Display status
    left_eye_color = (0, 0, 255) if left_eye_closed_state else (0, 255, 0)
    right_eye_color = (0, 0, 255) if right_eye_closed_state else (0, 255, 0)
    mouth_color = (0, 0, 255) if mouth_open_state else (0, 255, 0)
    eyebrow_color = (0, 0, 255) if eyebrows_raised_state else (0, 255, 0)
    head_tilt_left_color = (0, 0, 255) if head_tilt_left_state else (0, 255, 0)
    head_tilt_right_color = (0, 0, 255) if head_tilt_right_state else (0, 255, 0)

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
    if key_held:
        cv2.putText(frame, f"Holding: {('shift+' if shift_held else '') + key_held}", (10, 180),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    cv2.imshow('Facial Gesture Controller', frame)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break

# Clean up
release_key()
cap.release()
cv2.destroyAllWindows()