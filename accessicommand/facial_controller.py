import cv2
import mediapipe as mp
import pyautogui
import time
import math

# --- MediaPipe Face Mesh Setup ---
# Removed mp_drawing and mp_drawing_styles as we'll draw manually
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

# Combine all indices we want to draw
LANDMARKS_TO_DRAW = LEFT_EYE_INDICES + RIGHT_EYE_INDICES + MOUTH_CORNER_INDICES + MOUTH_VERTICAL_INDICES

# --- State Variables ---
left_eye_closed_state = False
right_eye_closed_state = False
mouth_open_state = False
last_action_time = 0
action_delay = 0.5

# --- Thresholds ---
EAR_THRESHOLD = 0.20
MAR_THRESHOLD = 0.35
CONSEC_FRAMES_BLINK = 2
CONSEC_FRAMES_MOUTH = 3

# --- Counters ---
left_blink_counter = 0
right_blink_counter = 0
mouth_open_counter = 0

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
        # print("Warning: Index error calculating EAR") # Keep console less noisy
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
        # print("Warning: Index error calculating MAR") # Keep console less noisy
        return 0

print("Starting Facial Controller. Press 'q' to quit.")
print(f"Screen Size: {screen_w}x{screen_h}")
print("Ensure the application you want to control is active.")
print(f"Settings: EAR Threshold={EAR_THRESHOLD}, MAR Threshold={MAR_THRESHOLD}, Delay={action_delay}s")
print("--- TUNING REQUIRED FOR THRESHOLDS! ---")

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

    frame = cv2.cvtColor(rgb_frame, cv2.COLOR_RGB2BGR) # Convert back for drawing

    ear_left_val = 1.0
    ear_right_val = 1.0
    mar_val = 0.0

    if results.multi_face_landmarks:
        landmarks = results.multi_face_landmarks[0].landmark

        # Use the actual landmark indices directly from the constants
        person_right_eye_points = [landmarks[i] for i in LEFT_EYE_INDICES] # Eye on left of screen
        person_left_eye_points = [landmarks[i] for i in RIGHT_EYE_INDICES] # Eye on right of screen

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

        current_time = time.time()
        if current_time - last_action_time > action_delay:
            action_taken = False
            if left_eye_closed_state and not right_eye_closed_state:
                pyautogui.press('left')
                print(f"ACTION @ {current_time:.2f}: Left Wink -> LEFT")
                action_taken = True
            elif right_eye_closed_state and not left_eye_closed_state:
                pyautogui.press('right')
                print(f"ACTION @ {current_time:.2f}: Right Wink -> RIGHT")
                action_taken = True
            elif left_eye_closed_state and right_eye_closed_state:
                pyautogui.press('space')
                print(f"ACTION @ {current_time:.2f}: Blink -> SPACE")
                action_taken = True
            elif mouth_open_state:
                pyautogui.press('down')
                print(f"ACTION @ {current_time:.2f}: Mouth Open -> DOWN")
                action_taken = True

            if action_taken:
                last_action_time = current_time

        # --- Visualization: Draw circles on specific landmarks ---
        for index in LANDMARKS_TO_DRAW:
            try:
                point = landmarks[index]
                # Denormalize coordinates
                x = int(point.x * frame_width)
                y = int(point.y * frame_height)
                # Draw a small green circle
                cv2.circle(frame, (x, y), 2, (0, 255, 0), -1) # -1 fills the circle
            except IndexError:
                 # This shouldn't happen if landmarks were detected, but good practice
                pass


    # --- Display Status Text ----
    # Determine colors based on state
    left_eye_color = (0, 0, 255) if left_eye_closed_state else (0, 255, 0)  # Red if closed, Green if open
    right_eye_color = (0, 0, 255) if right_eye_closed_state else (0, 255, 0) # Red if closed, Green if open
    mouth_color = (0, 0, 255) if mouth_open_state else (0, 255, 0)       # Red if open, Green if closed

    # Display text with dynamic colors
    cv2.putText(frame, f"L EYE: {ear_left_val:.2f} ({'Closed' if left_eye_closed_state else 'Open'})", (10, 30),
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, left_eye_color, 2)
    cv2.putText(frame, f"R EYE: {ear_right_val:.2f} ({'Closed' if right_eye_closed_state else 'Open'})", (10, 60),
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, right_eye_color, 2)
    cv2.putText(frame, f"MAR: {mar_val:.2f} ({'Open' if mouth_open_state else 'Closed'})", (10, 90),
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, mouth_color, 2)

    cv2.imshow('Facial Gesture Controller', frame)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('r'):
        print("Resetting counters (manual)")
        left_blink_counter = 0
        right_blink_counter = 0
        mouth_open_counter = 0
        last_action_time = time.time()


print("Shutting down...")
cap.release()
cv2.destroyAllWindows()
# face_mesh.close() 