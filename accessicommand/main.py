# accessicommand/main.py
import tkinter as tk
import os
import sys
import traceback

# --- Adjust path for imports ---
# Get the absolute path to the project root (FacialGestures/)
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# print("Sys path adjusted in main.py:", sys.path) # Optional debug

# --- Import Core Components ---
try:
    from accessicommand.core.engine import Engine
    from accessicommand.config.manager import ConfigManager
    from accessicommand.ui.main_window import AppGUI
except ImportError as e:
    print(f"ERROR: Failed to import necessary modules in main.py: {e}")
    print("Ensure the script is run correctly and all package components exist.")
    traceback.print_exc()
    sys.exit(1)

if __name__ == "__main__":
    print("--- Starting AccessiCommand Application ---")

    # --- Configuration ---
    # Determine path to config file (assuming it's in project root)
    config_file_path = os.path.join(project_root, "config.json")
    print(f"Using configuration file: {config_file_path}")

    engine = None # Initialize engine variable

    try:
        # --- Initialize Core Components ---
        print("Initializing Config Manager...")
        config_manager = ConfigManager(config_path=config_file_path)

        print("Initializing Engine...")
        # Engine uses the config manager internally
        engine = Engine(config_path=config_file_path)

        # --- Initialize GUI ---
        print("Initializing GUI...")
        root = tk.Tk()
        # Pass the engine and config_manager instances to the GUI
        app_gui = AppGUI(root, engine, config_manager)

        # --- Set window close behavior ---
        # Ensures engine is stopped when window is closed via 'X' button
        root.protocol("WM_DELETE_WINDOW", app_gui.on_close)

        # --- Start GUI Event Loop ---
        print("Starting GUI main loop...")
        root.mainloop() # This blocks until the window is closed

    except Exception as e:
        print("\n--- An Unhandled Error Occurred ---")
        traceback.print_exc()
        print(f"Error details: {e}")
        print("----------------------------------")

    finally:
        # --- Ensure Engine Stops on Exit ---
        # This runs if the mainloop exits or an error occurs
        print("Application exiting. Ensuring engine is stopped...")
        if engine and engine.is_running:
            try:
                engine.stop()
            except Exception as stop_e:
                 print(f"ERROR during final engine stop: {stop_e}")
        print("--- AccessiCommand Finished ---")