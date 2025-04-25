import pyautogui
import time

# --- Keyboard Actions ---

def press_key(key_name):
    """Presses and releases a single key."""
    try:
        print(f"[Action] Pressing key: {key_name}")
        pyautogui.press(key_name)
    except Exception as e:
        print(f"[Action Error] Failed to press key '{key_name}': {e}")

def key_down(key_name):
    """Holds down a key."""
    try:
        print(f"[Action] Holding key down: {key_name}")
        pyautogui.keyDown(key_name)
    except Exception as e:
        print(f"[Action Error] Failed to hold key down '{key_name}': {e}")

def key_up(key_name):
    """Releases a key."""
    try:
        print(f"[Action] Releasing key: {key_name}")
        pyautogui.keyUp(key_name)
    except Exception as e:
        print(f"[Action Error] Failed to release key '{key_name}': {e}")

def write_text(text, interval=0.01):
    """Types out a string of text."""
    try:
        print(f"[Action] Writing text: {text}")
        pyautogui.write(text, interval=interval)
    except Exception as e:
        print(f"[Action Error] Failed to write text: {e}")

def hotkey(*key_names):
    """Presses a key combination (shortcut)."""
    try:
        print(f"[Action] Executing hotkey: {'+'.join(key_names)}")
        pyautogui.hotkey(*key_names)
    except Exception as e:
        print(f"[Action Error] Failed to execute hotkey '{'+'.join(key_names)}': {e}")

# --- Mouse Actions (Add more as needed) ---

def move_mouse_relative(dx, dy, duration=0.1):
    """Moves the mouse relative to its current position."""
    try:
        print(f"[Action] Moving mouse relative by ({dx}, {dy})")
        pyautogui.moveRel(dx, dy, duration=duration)
    except Exception as e:
        print(f"[Action Error] Failed to move mouse relative: {e}")

def mouse_click(button='left', clicks=1, interval=0.1):
     """Performs a mouse click."""
     try:
         print(f"[Action] Clicking mouse button: {button} ({clicks}x)")
         pyautogui.click(button=button, clicks=clicks, interval=interval)
     except Exception as e:
        print(f"[Action Error] Failed to click mouse: {e}")

# --- Add other actions like scroll, drag, etc. ---