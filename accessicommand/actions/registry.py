# accessicommand/actions/registry.py
from . import system_actions
import pyautogui # Only needed if passing args directly in lambda, but good practice

# This dictionary maps user-friendly Action IDs (used in config)
# to the actual functions that perform the actions.
ACTION_REGISTRY = {
    # --- Simple Key Presses (Momentary) ---
    "PRESS_SPACE": lambda: system_actions.press_key('space'),
    "PRESS_ENTER": lambda: system_actions.press_key('enter'),
    "PRESS_ESC": lambda: system_actions.press_key('esc'),
    "PRESS_LEFT": lambda: system_actions.press_key('left'),
    "PRESS_RIGHT": lambda: system_actions.press_key('right'),
    "PRESS_UP": lambda: system_actions.press_key('up'),
    "PRESS_DOWN": lambda: system_actions.press_key('down'),
    "PRESS_W": lambda: system_actions.press_key('w'),
    "PRESS_A": lambda: system_actions.press_key('a'),
    "PRESS_S": lambda: system_actions.press_key('s'),
    "PRESS_D": lambda: system_actions.press_key('d'),
    "PRESS_Q": lambda: system_actions.press_key('q'),
    "PRESS_E": lambda: system_actions.press_key('e'),
    "PRESS_R": lambda: system_actions.press_key('r'),
    "PRESS_F": lambda: system_actions.press_key('f'),
    "PRESS_J": lambda: system_actions.press_key('j'), # Added from facial controller example
    "PRESS_K": lambda: system_actions.press_key('k'), # Added from facial controller example
    "PRESS_SHIFT": lambda: system_actions.press_key('shift'),
    "PRESS_CTRL": lambda: system_actions.press_key('ctrl'),
    "PRESS_TAB": lambda: system_actions.press_key('tab'),

    # --- Key Down (Hold) Actions ---
    "PRESS_A_DOWN": lambda: system_actions.key_down('a'),
    "PRESS_D_DOWN": lambda: system_actions.key_down('d'),
    "PRESS_J_DOWN": lambda: system_actions.key_down('j'),
    "PRESS_K_DOWN": lambda: system_actions.key_down('k'),
    "PRESS_SPACE_DOWN": lambda: system_actions.key_down('space'),
    "PRESS_W_DOWN": lambda: system_actions.key_down('w'), # Example for sustained move
    "PRESS_S_DOWN": lambda: system_actions.key_down('s'), # Example for sustained move
    # Add other hold keys as needed

    # --- Key Up (Release) Actions ---
    "PRESS_A_UP": lambda: system_actions.key_up('a'),
    "PRESS_D_UP": lambda: system_actions.key_up('d'),
    "PRESS_J_UP": lambda: system_actions.key_up('j'),
    "PRESS_K_UP": lambda: system_actions.key_up('k'),
    "PRESS_SPACE_UP": lambda: system_actions.key_up('space'),
    "PRESS_W_UP": lambda: system_actions.key_up('w'), # Example for sustained move
    "PRESS_S_UP": lambda: system_actions.key_up('s'), # Example for sustained move
    # Add other release keys

    # --- Key Combos (Momentary) ---
    "PRESS_SHIFT_A_COMBO": lambda: system_actions.hotkey('shift', 'a'),
    "PRESS_SHIFT_D_COMBO": lambda: system_actions.hotkey('shift', 'd'),
    "PRESS_CTRL_ALT_DEL": lambda: system_actions.hotkey('ctrl', 'alt', 'delete'),
    "PRESS_ALT_F4": lambda: system_actions.hotkey('alt', 'f4'),
    # Add more combos

    # --- Mouse Actions ---
    "MOUSE_CLICK_LEFT": lambda: system_actions.mouse_click(button='left'),
    "MOUSE_CLICK_RIGHT": lambda: system_actions.mouse_click(button='right'),
    "MOUSE_CLICK_MIDDLE": lambda: system_actions.mouse_click(button='middle'),
    "MOUSE_DBL_CLICK_LEFT": lambda: system_actions.mouse_click(button='left', clicks=2),
    "SCROLL_UP": lambda: system_actions.scroll_mouse(1), # Scroll amount might need config
    "SCROLL_DOWN": lambda: system_actions.scroll_mouse(-1),# Scroll amount might need config

    # --- Other Actions ---
    "TAKE_SCREENSHOT": lambda: system_actions.take_screenshot(), # Default filename
    # Example with filename:
    # "TAKE_SCREENSHOT_CUSTOM": lambda: system_actions.take_screenshot('my_capture.png'),

    # --- Internal/UI Actions (Placeholders) ---
    # "UI_OPEN_CONFIG": lambda: print("Internal Action: Open Config Triggered"),
}

def get_action_function(action_id):
    """Retrieves the action function from the registry."""
    func = ACTION_REGISTRY.get(action_id)
    if func is None:
        print(f"WARN: Action ID '{action_id}' not found in registry!")
    return func

def get_available_action_ids():
    """Returns a list of all defined action IDs."""
    return list(ACTION_REGISTRY.keys())