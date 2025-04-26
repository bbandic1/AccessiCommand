# accessicommand/main.py
import tkinter as tk
import os, sys, traceback

# Adjust path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path: sys.path.insert(0, project_root)

# Import Core Components
try:
    from accessicommand.core.engine import Engine
    from accessicommand.config.manager import ConfigManager
    from accessicommand.ui.main_window import AppGUI
except ImportError as e: print(f"ERROR importing: {e}"); traceback.print_exc(); sys.exit(1)

# --- Global scope variables (optional, could also pass app_gui via methods) ---
engine = None
root = None

def shutdown_application():
    """Cleans up resources when application exits."""
    global engine, root
    print("Application exiting. Ensuring engine is stopped...")
    if engine and engine.is_running:
        try: engine.stop()
        except Exception as stop_e: print(f"ERROR final stop: {stop_e}")
    if root:
         try:
             if root.winfo_exists(): root.destroy()
         except tk.TclError: pass
    print("--- AccessiCommand Finished ---")

if __name__ == "__main__":
    print("--- Starting AccessiCommand Application ---")
    config_file_path = os.path.join(project_root, "config.json")
    print(f"Using configuration file: {config_file_path}")

    try:
        print("Initializing Config Manager...")
        config_manager = ConfigManager(config_path=config_file_path)

        # --- Create GUI first ---
        print("Initializing GUI...")
        root = tk.Tk()
        # Create AppGUI instance - Engine is None initially
        app_gui = AppGUI(root, None, config_manager)

        # --- Create Engine, passing GUI instance ---
        print("Initializing Engine...")
        engine = Engine(config_path=config_file_path, app_gui_instance=app_gui)

        # --- Give GUI the actual Engine instance ---
        app_gui.engine = engine

        # Set window close behavior
        root.protocol("WM_DELETE_WINDOW", app_gui.on_close) # Use GUI's close method

        # Start GUI main loop
        print("Starting GUI main loop...")
        root.mainloop()

    except Exception as e: print("\n--- Unhandled Error ---"); traceback.print_exc(); print(f"{e}")
    finally:
        # Call the defined shutdown function
        shutdown_application()