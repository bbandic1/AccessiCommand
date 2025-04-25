from . import system_actions

# This dictionary maps user-friendly Action IDs (used in config)
# to the actual functions that perform the actions.
# The UI will likely present these IDs or descriptions to the user.

ACTION_REGISTRY = {
    # Keyboard Press Actions
    "PRESS_SPACE": lambda: system_actions.press_key('space'),
    "PRESS_ENTER": lambda: system_actions.press_key('enter'),
    "PRESS_ESC": lambda: system_actions.press_key('esc'),
    "PRESS_LEFT": lambda: system_actions.press_key('left'),
    "PRESS_RIGHT": lambda: system_actions.press_key('right'),
    "PRESS_UP": lambda: system_actions.press_key('up'),
    "PRESS_DOWN": lambda: system_actions.press_key('down'),
    "PRESS_W": lambda: system_actions.press_key('w'),          # Move forward
    "PRESS_A": lambda: system_actions.press_key('a'),          # Move left
    "PRESS_S": lambda: system_actions.press_key('s'),          # Move backward
    "PRESS_D": lambda: system_actions.press_key('d'),          # Move right
    "PRESS_Q": lambda: system_actions.press_key('q'),          # Secondary action
    "PRESS_E": lambda: system_actions.press_key('e'),          # Interact
    "PRESS_R": lambda: system_actions.press_key('r'),          # Reload
    "PRESS_F": lambda: system_actions.press_key('f'),          # Use or interact
    "PRESS_SHIFT": lambda: system_actions.press_key('shift'),  # Sprint
    "PRESS_CTRL": lambda: system_actions.press_key('ctrl'),    # Crouch
    "PRESS_TAB": lambda: system_actions.press_key('tab'),      # Inventory or map

    "PRESS_CTRL_ALT_DEL": lambda: system_actions.hotkey('ctrl', 'alt', 'delete'),
    "PRESS_ALT_F4": lambda: system_actions.hotkey('alt', 'f4'),
    # Add more common keys and shortcuts

    # Mouse Actions
    "MOUSE_CLICK_LEFT": lambda: system_actions.mouse_click(button='left'),
    "MOUSE_CLICK_RIGHT": lambda: system_actions.mouse_click(button='right'),
    "MOUSE_CLICK_MIDDLE": lambda: system_actions.mouse_click(button='middle'),  # Middle mouse click
    "MOUSE_DBL_CLICK_LEFT": lambda: system_actions.mouse_click(button='left', clicks=2),
    # Add more specific actions (move up, down, etc.) if needed

    # Placeholder for internal actions (like controlling UI via voice later)
    # "UI_OPEN_CONFIG": lambda: print("Internal Action: Open Config Triggered"),
}

def get_action_function(action_id):
    """Retrieves the action function from the registry."""
    return ACTION_REGISTRY.get(action_id)

def get_available_action_ids():
    """Returns a list of all defined action IDs."""
    return list(ACTION_REGISTRY.keys())