import cv2
import mediapipe as mp
import pyautogui
import time
import math
import numpy as np

# Inicijalizacija MediaPipe Face Mesh
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(refine_landmarks=True)

# Inicijalizacija kamere
cap = cv2.VideoCapture(0)

# Landmarkovi
LEFT_EYE_LANDMARKS = [362, 385, 387, 263, 373, 380]
RIGHT_EYE_LANDMARKS = [33, 160, 158, 133, 153, 144]
LIPS_LANDMARKS = [61, 291, 0, 17]  # Gornja i donja usna
MOUTH_INNER_LANDMARKS = [78, 306, 13, 14]  # Unutrašnjost usta

# Promenljive za praćenje stanja
left_eye_closed = False
right_eye_closed = False
mouth_open = False
last_action_time = 0
action_delay = 0.5

# Pragovi (podesite po potrebi)
EAR_THRESHOLD = 0.22
MOUTH_RATIO_THRESHOLD = 2.0  # Veći broj = otvorenija usta
CONSEC_FRAMES = 3

# Brojači
mouth_open_counter = 0

def calculate_ear(eye_points):
    # Izračun EAR za oko
    A = math.dist((eye_points[1].x, eye_points[1].y), (eye_points[5].x, eye_points[5].y))
    B = math.dist((eye_points[2].x, eye_points[2].y), (eye_points[4].x, eye_points[4].y))
    C = math.dist((eye_points[0].x, eye_points[0].y), (eye_points[3].x, eye_points[3].y))
    ear = (A + B) / (2.0 * C)
    return ear

def calculate_mouth_open(outer_mouth, inner_mouth):
    # Izračunaj udaljenost između gornje i donje usne (spolja)
    outer_vertical = math.dist((outer_mouth[0].x, outer_mouth[0].y), 
                             (outer_mouth[1].x, outer_mouth[1].y))
    
    # Izračunaj udaljenost između gornje i donje usne (iznutra)
    inner_vertical = math.dist((inner_mouth[0].x, inner_mouth[0].y), 
                             (inner_mouth[1].x, inner_mouth[1].y))
    
    # Izračunaj horizontalnu udaljenost (širina usta)
    horizontal = math.dist((outer_mouth[2].x, outer_mouth[2].y), 
                          (outer_mouth[3].x, outer_mouth[3].y))
    
    # Omjer vertikalne i horizontalne udaljenosti
    mouth_ratio = (outer_vertical + inner_vertical) / (2 * horizontal)
    return mouth_ratio

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    # Flip slike za prirodniji izgled
    frame = cv2.flip(frame, 1)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb_frame)
    
    if results.multi_face_landmarks:
        landmarks = results.multi_face_landmarks[0].landmark
        
        # Oči
        left_eye_points = [landmarks[i] for i in LEFT_EYE_LANDMARKS]
        right_eye_points = [landmarks[i] for i in RIGHT_EYE_LANDMARKS]
        left_ear = calculate_ear(left_eye_points)
        right_ear = calculate_ear(right_eye_points)
        
        # Usta - koristimo i spoljašnje i unutrašnje landmarkove
        outer_mouth = [landmarks[i] for i in LIPS_LANDMARKS]
        inner_mouth = [landmarks[i] for i in MOUTH_INNER_LANDMARKS]
        mouth_ratio = calculate_mouth_open(outer_mouth, inner_mouth)
        
        # Detekcija otvorenih usta sa histerezom
        if mouth_ratio > MOUTH_RATIO_THRESHOLD:
            mouth_open_counter += 1
        else:
            mouth_open_counter = max(0, mouth_open_counter - 1)
        
        mouth_open = mouth_open_counter >= CONSEC_FRAMES
        
        # Detekcija treptaja oka
        left_eye_closed = left_ear < EAR_THRESHOLD
        right_eye_closed = right_ear < EAR_THRESHOLD
        
        # Prikaz informacija
        cv2.putText(frame, f"Mouth Ratio: {mouth_ratio:.2f}", (10, 90), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(frame, f"Mouth Open: {mouth_open}", (10, 120), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Akcije
        current_time = time.time()
        if current_time - last_action_time > action_delay:
            if left_eye_closed and not right_eye_closed:
                pyautogui.press('left')
                print("LEFT")
                last_action_time = current_time
            elif right_eye_closed and not left_eye_closed:
                pyautogui.press('right')
                print("RIGHT")
                last_action_time = current_time
            elif left_eye_closed and right_eye_closed:
                pyautogui.press('space')
                print("SPACE")
                last_action_time = current_time
            elif mouth_open:
                pyautogui.press('down')
                print("MOUTH OPEN")
                last_action_time = current_time
        
        # Vizuelizacija
        for landmark in LEFT_EYE_LANDMARKS + RIGHT_EYE_LANDMARKS + LIPS_LANDMARKS + MOUTH_INNER_LANDMARKS:
            point = landmarks[landmark]
            x = int(point.x * frame.shape[1])
            y = int(point.y * frame.shape[0])
            color = (0, 255, 0)  # Zelena za normalno stanje
            if landmark in MOUTH_INNER_LANDMARKS and mouth_open:
                color = (0, 0, 255)  # Crvena kada su usta otvorena
            cv2.circle(frame, (x, y), 2, color, -1)
    
    cv2.imshow('Face Controls', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()